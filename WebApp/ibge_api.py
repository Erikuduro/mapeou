"""
IBGE data client.
- Localidades REST API → municipality/state metadata
- GeoFTP Brasil → full shapefiles (downloaded once, cached per-state as GeoJSON)
"""
import io
import json
import os
import re
import tempfile
import unicodedata
import zipfile

import geopandas as gpd
import requests
from shapely.geometry import Polygon

LOCALIDADES  = "https://servicodados.ibge.gov.br/api/v1/localidades"
# Per-state URL (~5-15 MB each) — avoids loading the 200 MB Brazil-wide file into RAM
_UF_MUNIS_URL = (
    "https://geoftp.ibge.gov.br/organizacao_do_territorio"
    "/malhas_territoriais/malhas_municipais/municipio_2022"
    "/UFs/{uf}/{uf}_Municipios_2022.zip"
)
BR_UF_URL = (
    "https://geoftp.ibge.gov.br/organizacao_do_territorio"
    "/malhas_territoriais/malhas_municipais/municipio_2022"
    "/Brasil/BR/BR_UF_2022.zip"
)
CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")
HEADERS   = {"User-Agent": "MapAIAgent/1.0 (contaclaudecode@gmail.com)"}

os.makedirs(CACHE_DIR, exist_ok=True)

# ── constants ─────────────────────────────────────────────────────────────────

UF_SIGLAS = {
    'AC','AL','AP','AM','BA','CE','DF','ES','GO','MA',
    'MT','MS','MG','PA','PB','PR','PE','PI','RJ','RN',
    'RS','RO','RR','SC','SP','SE','TO',
}

UF_NOME_SIGLA = {
    'acre':'AC','alagoas':'AL','amapa':'AP','amazonas':'AM',
    'bahia':'BA','ceara':'CE','distrito federal':'DF',
    'espirito santo':'ES','goias':'GO','maranhao':'MA',
    'mato grosso':'MT','mato grosso do sul':'MS','minas gerais':'MG',
    'para':'PA','paraiba':'PB','parana':'PR','pernambuco':'PE',
    'piaui':'PI','rio de janeiro':'RJ','rio grande do norte':'RN',
    'rio grande do sul':'RS','rondonia':'RO','roraima':'RR',
    'santa catarina':'SC','sao paulo':'SP','sergipe':'SE','tocantins':'TO',
}

REGIAO_CODE_SIGLA = {'1':'N','2':'NE','3':'SE','4':'S','5':'CO'}

UF_REGIAO_SIGLA = {
    'AC':'N','AM':'N','AP':'N','PA':'N','RO':'N','RR':'N','TO':'N',
    'AL':'NE','BA':'NE','CE':'NE','MA':'NE','PB':'NE','PE':'NE',
    'PI':'NE','RN':'NE','SE':'NE',
    'DF':'CO','GO':'CO','MS':'CO','MT':'CO',
    'ES':'SE','MG':'SE','RJ':'SE','SP':'SE',
    'PR':'S','RS':'S','SC':'S',
}

MUNI_LIST_CACHE = os.path.join(os.path.dirname(__file__), "cache", "municipios_list.json")

_PREFIXES = [
    r'^(gere?|crie?|fa[çc]a?|mostre?|quero|me\s+mostre?)\s+(um?\s+)?mapa\s+(do\s+munic[ií]pio\s+de|do|da|de|dos|das)\s+',
    r'^mapa\s+(do\s+munic[ií]pio\s+de|do|da|de|dos|das)\s+',
    r'^munic[ií]pio\s+(de|do|da)\s+',
    r'^(gerar?|criar?)\s+mapa\s+(do|da|de)\s+',
    r'^mapa\s*:\s*',
]


# ── internal helpers ──────────────────────────────────────────────────────────

def _norm(s: str) -> str:
    s = unicodedata.normalize('NFD', s.lower().strip())
    return ''.join(c for c in s if unicodedata.category(c) != 'Mn')


def _clean(text: str) -> str:
    t = text.strip()
    changed = True
    while changed:
        changed = False
        for p in _PREFIXES:
            n = re.sub(p, '', t, flags=re.IGNORECASE).strip()
            if n != t:
                t = n
                changed = True
    return t


def _get_json(url: str, timeout: int = 60):
    r = requests.get(url, headers=HEADERS, timeout=timeout)
    r.raise_for_status()
    return r.json()


def _get_all_municipios() -> list:
    """Return the full IBGE municipalities list, cached locally."""
    if os.path.exists(MUNI_LIST_CACHE):
        with open(MUNI_LIST_CACHE, encoding='utf-8') as f:
            return json.load(f)
    data = _get_json(f"{LOCALIDADES}/municipios")
    with open(MUNI_LIST_CACHE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)
    return data


def _shp_from_zip_bytes(raw: bytes) -> gpd.GeoDataFrame:
    with tempfile.TemporaryDirectory() as tmp:
        with zipfile.ZipFile(io.BytesIO(raw)) as zf:
            zf.extractall(tmp)
        shp = next(
            (os.path.join(tmp, f) for f in os.listdir(tmp) if f.endswith(".shp")),
            None,
        )
        if shp is None:
            raise ValueError("Shapefile não encontrado no ZIP.")
        gdf = gpd.read_file(shp)
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4674")
    return gdf.to_crs("EPSG:4326")


def _norm_cols(gdf: gpd.GeoDataFrame, mapping: dict) -> gpd.GeoDataFrame:
    """Rename columns case-insensitively."""
    upper_map = {c.upper(): c for c in gdf.columns}
    rename = {upper_map[k]: v for k, v in mapping.items() if k in upper_map}
    return gdf.rename(columns=rename)


# ── public API ────────────────────────────────────────────────────────────────

def parse_text(text: str) -> tuple[str, str | None]:
    t = _clean(text)
    m = re.match(r'^(.+?)[\s,\-–(]+([A-Za-z]{2})\s*\)?\s*$', t)
    if m and m.group(2).upper() in UF_SIGLAS:
        return m.group(1).strip().rstrip(',- '), m.group(2).upper()
    t_n = _norm(t)
    for nome, sigla in UF_NOME_SIGLA.items():
        if t_n.endswith(nome):
            prefix = t[:-(len(nome))].strip().rstrip(',- ').strip()
            if prefix:
                return prefix, sigla
    return t, None


def find_municipio(name: str, uf: str | None = None) -> dict:
    all_m = _get_all_municipios()
    n = _norm(name)
    exact   = [m for m in all_m if _norm(m['nome']) == n]
    partial = [m for m in all_m if n in _norm(m['nome'])] if not exact else []
    candidates = exact or partial
    if uf:
        filtered = [
            m for m in candidates
            if m['microrregiao']['mesorregiao']['UF']['sigla'] == uf
        ]
        candidates = filtered or candidates
    if not candidates:
        hint = f" em {uf}" if uf else ""
        raise ValueError(
            f"Município '{name}' não encontrado{hint}. "
            "Use o formato 'Nome, UF' (ex: Garanhuns, PE)."
        )
    m   = candidates[0]
    uf_ = m['microrregiao']['mesorregiao']['UF']
    reg = uf_['regiao']
    return {
        'id':           m['id'],
        'nome':         m['nome'],
        'uf_id':        uf_['id'],
        'uf_sigla':     uf_['sigla'],
        'uf_nome':      uf_['nome'],
        'regiao_id':    reg['id'],
        'regiao_sigla': reg['sigla'],
        'regiao_nome':  reg['nome'],
    }


def get_state_municipios(uf_sigla: str) -> gpd.GeoDataFrame:
    """GeoDataFrame: codarea (7-digit str), nome, geometry.
    Downloads only the requested state's shapefile (~5-15 MB) on first use.
    """
    cache = os.path.join(CACHE_DIR, f"munis_{uf_sigla}.geojson")
    if os.path.exists(cache):
        return gpd.read_file(cache)

    url = _UF_MUNIS_URL.format(uf=uf_sigla)
    print(f"Baixando malhas municipais de {uf_sigla}...")
    r = requests.get(url, headers=HEADERS, timeout=180, stream=True)
    r.raise_for_status()
    raw = b"".join(chunk for chunk in r.iter_content(65536) if chunk)

    gdf = _shp_from_zip_bytes(raw)
    gdf = _norm_cols(gdf, {'CD_MUN': 'codarea', 'NM_MUN': 'nome'})
    gdf['codarea'] = gdf['codarea'].astype(str)
    state_gdf = gdf[['codarea', 'nome', 'geometry']].copy()
    state_gdf.to_file(cache, driver="GeoJSON")
    return state_gdf


def get_states() -> gpd.GeoDataFrame:
    """GeoDataFrame: codarea (2-digit str), sigla, nome, regiao (sigla), geometry."""
    cache = os.path.join(CACHE_DIR, "estados.geojson")
    if os.path.exists(cache):
        return gpd.read_file(cache)

    print("Baixando BR_UF_2022.zip do IBGE (~13MB)...")
    r = requests.get(BR_UF_URL, headers=HEADERS, timeout=120, stream=True)
    r.raise_for_status()
    raw = b"".join(chunk for chunk in r.iter_content(65536) if chunk)

    gdf = _shp_from_zip_bytes(raw)
    gdf = _norm_cols(gdf, {
        'CD_UF':    'codarea',
        'SIGLA_UF': 'sigla',
        'NM_UF':    'nome',
        'CD_REGIAO':'regiao_code',
    })
    gdf['codarea'] = gdf['codarea'].astype(str)
    if 'regiao_code' in gdf.columns:
        gdf['regiao'] = gdf['regiao_code'].astype(str).map(REGIAO_CODE_SIGLA)

    # Fallback: build regiao from UF sigla if not extracted from shapefile
    if 'regiao' not in gdf.columns and 'sigla' in gdf.columns:
        gdf['regiao'] = gdf['sigla'].map(UF_REGIAO_SIGLA)

    keep = [c for c in ['codarea','sigla','nome','regiao','geometry'] if c in gdf.columns]
    gdf = gdf[keep]
    gdf.to_file(cache, driver="GeoJSON")
    return gdf


# ── Sítio Urbano (census sectors) ────────────────────────────────────────────

GEOFTP_SETORES = (
    "https://geoftp.ibge.gov.br/organizacao_do_territorio"
    "/malhas_territoriais/malhas_de_setores_censitarios__divisoes_intramunicipais"
    "/censo_2022"
)

_REGIAO_DIR = {
    'N':'norte','NE':'nordeste','SE':'sudeste','S':'sul','CO':'centro_oeste'
}


def get_sitio_urbano(muni_id: int, uf_sigla: str, regiao_sigla: str) -> gpd.GeoDataFrame | None:
    """
    Download IBGE 2022 census sectors for the state, filter urban sectors for the
    given municipality, dissolve into a single polygon.
    Returns GeoDataFrame or None if unavailable.
    """
    cache = os.path.join(CACHE_DIR, f"urbano_{muni_id}.geojson")

    if os.path.exists(cache):
        gdf = gpd.read_file(cache)
        return gdf if not gdf.empty else None

    uf_lower  = uf_sigla.lower()
    reg_dir   = _REGIAO_DIR.get(regiao_sigla, regiao_sigla.lower())
    url = (
        f"{GEOFTP_SETORES}/{reg_dir}/{uf_lower}"
        f"/{uf_lower}_setores_censitarios_2022.zip"
    )

    try:
        r = requests.get(url, headers=HEADERS, timeout=300, stream=True)
        r.raise_for_status()
        raw = b"".join(chunk for chunk in r.iter_content(65536) if chunk)
        gdf = _shp_from_zip_bytes(raw)

        # Find municipality code column
        cols_up = {c.upper(): c for c in gdf.columns}
        setor_col = cols_up.get('CD_SETOR') or cols_up.get('CD_SETOR_2') or None
        mun_col   = cols_up.get('CD_MUN') or None

        muni_str = str(muni_id)
        if setor_col:
            gdf = gdf[gdf[setor_col].astype(str).str.startswith(muni_str)]
        elif mun_col:
            gdf = gdf[gdf[mun_col].astype(str) == muni_str]

        # Filter urban sectors (TIPO_SETOR 1-4 = urban/peri-urban in IBGE 2022)
        tipo_col = cols_up.get('TIPO_SETOR') or cols_up.get('TIPO') or None
        if tipo_col and not gdf.empty:
            urban_types = {1, 2, 3, 4, '1', '2', '3', '4'}
            gdf = gdf[gdf[tipo_col].isin(urban_types)]

        if gdf.empty:
            raise ValueError("No urban sectors found")

        dissolved = gdf.dissolve()[['geometry']].reset_index(drop=True)
        dissolved.to_file(cache, driver='GeoJSON')
        return dissolved

    except Exception:
        # Save empty marker so we don't retry every request
        empty = gpd.GeoDataFrame({'geometry': gpd.GeoSeries([], crs='EPSG:4326')})
        empty.to_file(cache, driver='GeoJSON')
        return None


# ── Water bodies (Overpass API) ───────────────────────────────────────────────

_OVERPASS_URL = "https://overpass-api.de/api/interpreter"

_WATER_QUERY = """
[out:json][timeout:60];
(
  way["natural"="water"]({bbox});
  relation["natural"="water"]({bbox});
  way["waterway"="riverbank"]({bbox});
  relation["waterway"="riverbank"]({bbox});
  way["water"="river"]({bbox});
  way["water"="lake"]({bbox});
  way["water"="reservoir"]({bbox});
  relation["water"="reservoir"]({bbox});
  relation["waterway"="riverbank"]({bbox});
);
out geom;
"""

NE_COUNTRIES_URL = (
    "https://naciscdn.org/naturalearth/50m/cultural/ne_50m_admin_0_countries.zip"
)


def _parse_overpass_geoms(data: dict) -> list:
    geoms = []
    for elem in data.get('elements', []):
        if elem['type'] == 'way' and 'geometry' in elem:
            coords = [(n['lon'], n['lat']) for n in elem['geometry']]
            if len(coords) >= 4 and coords[0] == coords[-1]:
                try:
                    p = Polygon(coords)
                    if p.is_valid and p.area > 1e-10:
                        geoms.append(p)
                except Exception:
                    pass
        elif elem['type'] == 'relation':
            for member in elem.get('members', []):
                if member.get('role') == 'outer' and 'geometry' in member:
                    coords = [(n['lon'], n['lat']) for n in member['geometry']]
                    if len(coords) >= 4:
                        try:
                            p = Polygon(coords)
                            if p.is_valid and p.area > 1e-10:
                                geoms.append(p)
                        except Exception:
                            pass
    return geoms


def get_water_bodies(muni_id: int,
                     xmin: float, ymin: float,
                     xmax: float, ymax: float) -> 'gpd.GeoDataFrame | None':
    """
    Download water polygons from Overpass API for the municipality's map extent.
    Returns GeoDataFrame (EPSG:4326) or None if unavailable.
    Cached per municipality ID.
    """
    cache = os.path.join(CACHE_DIR, f"water_{muni_id}.geojson")
    if os.path.exists(cache):
        gdf = gpd.read_file(cache)
        return gdf if not gdf.empty else None

    bbox = f"{ymin:.4f},{xmin:.4f},{ymax:.4f},{xmax:.4f}"
    query = _WATER_QUERY.format(bbox=bbox)

    try:
        r = requests.post(_OVERPASS_URL, data={'data': query},
                          headers=HEADERS, timeout=60)
        r.raise_for_status()
        geoms = _parse_overpass_geoms(r.json())

        if not geoms:
            raise ValueError("no water geometries")

        gdf = gpd.GeoDataFrame(geometry=geoms, crs='EPSG:4326')
        gdf = gdf[gdf.geometry.is_valid].copy()
        gdf.to_file(cache, driver='GeoJSON')
        return gdf

    except Exception:
        empty = gpd.GeoDataFrame({'geometry': gpd.GeoSeries([], crs='EPSG:4326')})
        empty.to_file(cache, driver='GeoJSON')
        return None


def get_countries() -> 'gpd.GeoDataFrame | None':
    """
    Download Natural Earth 50m country boundaries (cached globally).
    Returns GeoDataFrame with columns: name, iso_a2, geometry (EPSG:4326).
    """
    cache = os.path.join(CACHE_DIR, "ne_countries.geojson")
    if os.path.exists(cache):
        return gpd.read_file(cache)

    try:
        print("Baixando Natural Earth countries (~500KB)...")
        r = requests.get(NE_COUNTRIES_URL, headers=HEADERS, timeout=120, stream=True)
        r.raise_for_status()
        raw = b"".join(chunk for chunk in r.iter_content(65536) if chunk)
        gdf = _shp_from_zip_bytes(raw)

        # Normalise column names to lowercase
        gdf.columns = [c.lower() for c in gdf.columns]
        keep = [c for c in ['name', 'iso_a2', 'geometry'] if c in gdf.columns]
        gdf = gdf[keep].copy()
        gdf.to_file(cache, driver='GeoJSON')
        return gdf
    except Exception:
        return None
