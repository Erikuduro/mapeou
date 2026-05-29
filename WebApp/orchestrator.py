"""Route user text to the IBGE cartographic map generator."""
import re

from ibge_api import (
    parse_text, find_municipio,
    get_state_municipios, get_states,
    get_sitio_urbano,
)

# Each entry: search_key → (label_exibido, dica_qgis)
# Termos compostos ANTES das raízes — a primeira chave que der match vence.
_COMPLEX_KEYWORDS = {
    "bacia hidrográfica": ("bacia hidrográfica",
                           "No QGIS: baixe os limites de bacias hidrográficas da ANA via plugin QuickOSM."),
    "bacia hidrografica": ("bacia hidrográfica",
                           "No QGIS: baixe os limites de bacias hidrográficas da ANA via plugin QuickOSM."),
    "hidrográfic":        ("hidrografia",
                           "No QGIS: use o plugin QuickOSM filtrando por 'waterway'."),
    "hidrografia":        ("hidrografia",
                           "No QGIS: use o plugin QuickOSM filtrando por 'waterway'."),
    "bacia":              ("bacia hidrográfica",
                           "No QGIS: baixe os limites de bacias hidrográficas da ANA via plugin QuickOSM."),
    "afluente":         ("afluentes / rede hídrica",
                         "No QGIS: use o plugin QuickOSM filtrando por 'waterway'."),
    "nascente":         ("nascentes",
                         "No QGIS: use o plugin QuickOSM filtrando por 'waterway=spring'."),
    "manancial":        ("mananciais",
                         "No QGIS: use o plugin QuickOSM filtrando por 'waterway'."),
    "rio ":             ("rios / cursos d'água",
                         "No QGIS: use o plugin QuickOSM filtrando por 'waterway=river'."),
    "shapefile":        ("shapefile",
                         "No QGIS: Camada → Adicionar Camada Vetorial."),
    "curvas de nível":  ("curvas de nível",
                         "No QGIS: Raster → Extração → Curvas de Nível após carregar um MDT."),
    "cotas":            ("cotas altimétricas",
                         "No QGIS: Raster → Extração → Curvas de Nível após carregar um MDT."),
    "elevação":         ("dados de elevação",
                         "No QGIS: use o plugin SRTM Downloader para dados de elevação."),
    "topografia":       ("topografia",
                         "No QGIS: use o plugin SRTM Downloader para dados topográficos."),
    "roteamento":       ("roteamento / rotas",
                         "No QGIS: use o plugin ORS Tools para análise de rotas."),
    "buffer":           ("buffer / zona de influência",
                         "No QGIS: Vetor → Geoprocessamento → Buffer."),
    "análise espacial": ("análise espacial",
                         "No QGIS: menu Vetor → Geoprocessamento."),
    "geoprocessamento": ("geoprocessamento",
                         "No QGIS: menu Vetor → Geoprocessamento."),
    "georreferenci":    ("georreferenciamento",
                         "No QGIS: Raster → Georreferenciador."),
    "simbologia":       ("simbologia / estilos",
                         "No QGIS: clique duplo na camada → aba Simbologia."),
    "routing":          ("routing / directions",
                         "In QGIS: use the ORS Tools plugin for routing."),
    "contour":          ("contour lines",
                         "In QGIS: Raster → Extraction → Contour after loading a DEM."),
    "elevation":        ("elevation data",
                         "In QGIS: use the SRTM Downloader plugin."),
    "symbology":        ("symbology / styles",
                         "In QGIS: double-click a layer → Symbology tab."),
    "hydrography":      ("hydrography / watersheds",
                         "In QGIS: use the QuickOSM plugin filtering by 'waterway'."),
    "watershed":        ("watershed / drainage basin",
                         "In QGIS: use the QuickOSM plugin filtering by 'waterway'."),
}


class ComplexRequestError(Exception):
    def __init__(self, reason: str, qgis_tip: str):
        self.reason = reason
        self.qgis_tip = qgis_tip
        super().__init__(reason)


def _check_complexity(text: str):
    lower = text.lower()
    for kw, (label, tip) in _COMPLEX_KEYWORDS.items():
        if kw in lower:
            return (
                f"'{label}' indica uma necessidade além do mapa cartográfico automático.",
                tip,
            )
    return None


def process(user_text: str) -> dict:
    complexity = _check_complexity(user_text)
    if complexity:
        raise ComplexRequestError(reason=complexity[0], qgis_tip=complexity[1])

    name, uf = parse_text(user_text)
    if not name:
        raise ValueError("Não foi possível identificar um município na descrição.")

    municipio    = find_municipio(name, uf)
    state_munis  = get_state_municipios(municipio['uf_sigla'])
    states       = get_states()
    sitio_urbano = get_sitio_urbano(
        municipio['id'],
        municipio['uf_sigla'],
        municipio['regiao_sigla'],
    )

    return {
        "type":         "ibge",
        "municipio":    municipio,
        "state_munis":  state_munis,
        "states":       states,
        "sitio_urbano": sitio_urbano,
    }
