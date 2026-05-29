"""
Cliente SIDRA: busca séries históricas do IBGE e cacheia localmente.
Suporta nível nacional (N1) e por estado (N3).
"""
import json
import re
from pathlib import Path

import requests

CACHE_DIR = Path(__file__).parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)

SIDRA_BASE = "https://servicodados.ibge.gov.br/api/v3/agregados"

# Códigos IBGE dos estados (N3)
UF_CODES: dict[str, tuple[str, int]] = {
    # sigla → (nome, código IBGE)
    "AC": ("Acre", 12),
    "AL": ("Alagoas", 27),
    "AM": ("Amazonas", 13),
    "AP": ("Amapá", 16),
    "BA": ("Bahia", 29),
    "CE": ("Ceará", 23),
    "DF": ("Distrito Federal", 53),
    "ES": ("Espírito Santo", 32),
    "GO": ("Goiás", 52),
    "MA": ("Maranhão", 21),
    "MG": ("Minas Gerais", 31),
    "MS": ("Mato Grosso do Sul", 50),
    "MT": ("Mato Grosso", 51),
    "PA": ("Pará", 15),
    "PB": ("Paraíba", 25),
    "PE": ("Pernambuco", 26),
    "PI": ("Piauí", 22),
    "PR": ("Paraná", 41),
    "RJ": ("Rio de Janeiro", 33),
    "RN": ("Rio Grande do Norte", 24),
    "RO": ("Rondônia", 11),
    "RR": ("Roraima", 14),
    "RS": ("Rio Grande do Sul", 43),
    "SC": ("Santa Catarina", 42),
    "SE": ("Sergipe", 28),
    "SP": ("São Paulo", 35),
    "TO": ("Tocantins", 17),
}

# Mapa de nomes por extenso → sigla
_NOME_TO_UF: dict[str, str] = {
    nome.lower(): uf for uf, (nome, _) in UF_CODES.items()
}
# Aliases comuns
_ALIASES: dict[str, str] = {
    "minas": "MG",
    "sao paulo": "SP",
    "são paulo": "SP",
    "rio de janeiro": "RJ",
    "rio grande do sul": "RS",
    "rio grande do norte": "RN",
    "mato grosso do sul": "MS",
    "mato grosso": "MT",
    "espirito santo": "ES",
    "espírito santo": "ES",
    "maranhao": "MA",
    "maranhão": "MA",
    "para": "PA",
    "pará": "PA",
    "parana": "PR",
    "paraná": "PR",
    "paraiba": "PB",
    "paraíba": "PB",
    "pernambuco": "PE",
    "bahia": "BA",
    "ceara": "CE",
    "ceará": "CE",
    "goias": "GO",
    "goiás": "GO",
    "amazonas": "AM",
    "tocantins": "TO",
    "sergipe": "SE",
    "alagoas": "AL",
    "piaui": "PI",
    "piauí": "PI",
    "rondonia": "RO",
    "rondônia": "RO",
    "roraima": "RR",
    "amapa": "AP",
    "amapá": "AP",
    "acre": "AC",
    "distrito federal": "DF",
    "brasilia": "DF",
    "brasília": "DF",
}


def parse_state(text: str) -> tuple[str, int, str] | None:
    """
    Tenta extrair estado do texto.
    Retorna (uf_sigla, ibge_code, nome) ou None se nacional.
    """
    lower = text.lower()

    # Tenta sigla de 2 letras (ex: PE, SP)
    match = re.search(r'\b([A-Z]{2})\b', text)
    if match:
        uf = match.group(1).upper()
        if uf in UF_CODES:
            nome, code = UF_CODES[uf]
            return uf, code, nome

    # Tenta nome por extenso (aliases primeiro, depois nome completo)
    for alias, uf in _ALIASES.items():
        if alias in lower:
            nome, code = UF_CODES[uf]
            return uf, code, nome

    for nome_lower, uf in _NOME_TO_UF.items():
        if nome_lower in lower:
            nome, code = UF_CODES[uf]
            return uf, code, nome

    return None


def _cache_path(topic_id: str, ano_ini: int, ano_fim: int, uf: str | None) -> Path:
    suffix = f"_{uf}" if uf else "_BR"
    return CACHE_DIR / f"sidra_{topic_id}{suffix}_{ano_ini}_{ano_fim}.json"


def _build_url(topic: dict, anos: list[int], ibge_code: int | None) -> str:
    periodos = "|".join(str(a) for a in anos)
    variavel = topic["variavel"]

    if ibge_code:
        # Nível estadual: usa tabela/classificacao/categoria padrão
        tabela  = topic["tabela"]
        classif = topic.get("classificacao")
        categ   = topic.get("categoria")
        localidades = f"N3[{ibge_code}]"
    else:
        # Nível nacional: prefere tabela_n1 se disponível
        tabela  = topic.get("tabela_n1", topic["tabela"])
        classif = topic.get("classificacao_n1", topic.get("classificacao"))
        categ   = topic.get("categoria_n1", topic.get("categoria"))
        localidades = "N1[all]"

    url = f"{SIDRA_BASE}/{tabela}/periodos/{periodos}/variaveis/{variavel}?localidades={localidades}"
    if classif and categ:
        url += f"&classificacao={classif}[{categ}]"
    return url


def fetch_series(
    topic: dict,
    ano_ini: int = 1990,
    ano_fim: int = 2024,
    state: tuple[str, int, str] | None = None,
) -> dict:
    """
    Retorna {'anos': [...], 'valores': [...], 'unidade': str, 'titulo': str}.
    state = (uf_sigla, ibge_code, nome) ou None para Brasil.
    """
    uf_sigla  = state[0] if state else None
    ibge_code = state[1] if state else None
    uf_nome   = state[2] if state else None

    cache_file = _cache_path(topic["id"], ano_ini, ano_fim, uf_sigla)
    if cache_file.exists():
        cached = json.loads(cache_file.read_text(encoding="utf-8"))
        if cached.get("valores"):
            return cached
        cache_file.unlink(missing_ok=True)

    anos = list(range(ano_ini, ano_fim + 1))
    url  = _build_url(topic, anos, ibge_code)

    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    serie_raw: dict = data[0]["resultados"][0]["series"][0]["serie"]

    anos_out   = []
    values_out = []
    for ano in anos:
        val = serie_raw.get(str(ano))
        if val and val not in ("-", "...", "X", ""):
            try:
                anos_out.append(ano)
                values_out.append(float(val))
            except ValueError:
                pass

    # Título com estado ou Brasil
    base_titulo = topic["titulo"].replace(" — Brasil", "")
    if uf_nome:
        titulo = f"{base_titulo} — {uf_nome}"
    else:
        titulo = topic["titulo"]

    result = {
        "anos":    anos_out,
        "valores": values_out,
        "unidade": topic["unidade"],
        "titulo":  titulo,
        "tipo":    topic.get("tipo", "bar"),
    }

    cache_file.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    return result


def fetch_ranking_crops_state(state: tuple, ano: int = 2023) -> dict:
    """
    Retorna as maiores produções agrícolas de um estado em um dado ano.
    Usa tabela 5457 com classificacao=782[all] no nível N3.
    """
    uf_sigla, ibge_code, uf_nome = state
    cache_file = CACHE_DIR / f"sidra_ranking_crops_{uf_sigla}_{ano}.json"
    if cache_file.exists():
        cached = json.loads(cache_file.read_text(encoding="utf-8"))
        if cached.get("itens"):
            return cached
        cache_file.unlink(missing_ok=True)

    url = (
        f"{SIDRA_BASE}/5457/periodos/{ano}/variaveis/214"
        f"?localidades=N3[{ibge_code}]&classificacao=782[all]"
    )
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    culturas = []
    for res in data[0]["resultados"]:
        cat_nome = list(res["classificacoes"][0]["categoria"].values())[0]
        val = res["series"][0]["serie"].get(str(ano), "")
        try:
            v = float(val)
            if v > 0:
                culturas.append({"nome": cat_nome, "valor": v})
        except (ValueError, TypeError):
            pass

    culturas.sort(key=lambda x: x["valor"], reverse=True)

    result = {
        "tipo":   "ranking_crops",
        "titulo": f"Maiores Produções Agrícolas — {uf_nome} ({ano})",
        "subtitulo": f"Fonte: IBGE — SIDRA (PAM)  ·  Unidade: Toneladas  ·  Ano: {ano}",
        "itens":  culturas,
        "unidade": "Toneladas",
        "uf_nome": uf_nome,
        "ano": ano,
    }
    cache_file.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    return result


def fetch_ranking_states_crop(topic: dict, ano: int = 2023, top_n: int = 10) -> dict:
    """
    Retorna o ranking dos estados por produção de um tema específico.
    Usa os parâmetros do próprio catálogo (tabela/variavel/classificacao/categoria).
    """
    cache_file = CACHE_DIR / f"sidra_ranking_states_{topic['id']}_{ano}.json"
    if cache_file.exists():
        cached = json.loads(cache_file.read_text(encoding="utf-8"))
        if cached.get("itens"):  # descarta cache vazio
            return cached
        cache_file.unlink(missing_ok=True)

    tabela  = topic["tabela"]
    variavel = topic["variavel"]
    classif = topic.get("classificacao")
    categ   = topic.get("categoria")

    url_estados = (
        f"{SIDRA_BASE}/{tabela}/periodos/{ano}/variaveis/{variavel}"
        f"?localidades=N3[all]"
    )
    if classif and categ:
        url_estados += f"&classificacao={classif}[{categ}]"

    resp = requests.get(url_estados, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    estados = []
    for s in data[0]["resultados"][0]["series"]:
        val = s["serie"].get(str(ano), "")
        try:
            v = float(val)
            if v > 0:
                estados.append({"nome": s["localidade"]["nome"], "valor": v})
        except (ValueError, TypeError):
            pass
    estados.sort(key=lambda x: x["valor"], reverse=True)

    # Total nacional: usa tabela_n1 se disponível
    tabela_n1  = topic.get("tabela_n1", tabela)
    classif_n1 = topic.get("classificacao_n1", classif)
    categ_n1   = topic.get("categoria_n1", categ)
    variavel_n1 = variavel

    url_nacional = (
        f"{SIDRA_BASE}/{tabela_n1}/periodos/{ano}/variaveis/{variavel_n1}"
        f"?localidades=N1[all]"
    )
    if classif_n1 and categ_n1:
        url_nacional += f"&classificacao={classif_n1}[{categ_n1}]"

    nacional = 0.0
    try:
        r2 = requests.get(url_nacional, timeout=30)
        nacional = float(
            r2.json()[0]["resultados"][0]["series"][0]["serie"].get(str(ano), 0)
        )
    except Exception:
        # Fallback: soma dos estados
        nacional = sum(e["valor"] for e in estados)

    crop_nome = topic["titulo"].replace(" — Brasil", "")
    unidade   = topic["unidade"]
    result = {
        "tipo":           "ranking_states",
        "titulo":         f"Top {top_n} Estados Produtores — {crop_nome} ({ano})",
        "subtitulo":      f"Fonte: IBGE — SIDRA  ·  Unidade: {unidade}  ·  Ano: {ano}",
        "itens":          estados[:top_n],
        "total_nacional": nacional,
        "unidade":        unidade,
        "ano":            ano,
    }
    cache_file.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    return result


def parse_year_range(text: str) -> tuple[int, int]:
    """Extrai intervalo de anos do texto. Padrão: 1990-2024."""
    years = re.findall(r'\b(19[5-9]\d|20[0-2]\d)\b', text)
    if len(years) >= 2:
        return int(years[0]), int(years[-1])
    if len(years) == 1:
        return int(years[0]), 2024
    return 1990, 2024
