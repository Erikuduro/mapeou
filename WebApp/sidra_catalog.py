"""
Catálogo de temas SIDRA.

Cada entrada pode ter dois conjuntos de parâmetros:
  - tabela / classificacao / categoria  → usado para N3 (estado) via tabela 5457
  - tabela_n1 / classificacao_n1 / categoria_n1  → usado para N1 (Brasil)

Se não houver tabela_n1, usa-se o mesmo tabela/classificacao/categoria em N1.
"""

CATALOG = [
    # ── PECUÁRIA — PRODUÇÃO ANIMAL ────────────────────────────────────────
    {
        "id": "leite",
        "keywords": ["leite", "produção de leite", "litros de leite"],
        "titulo": "Produção de Leite — Brasil",
        "tabela": 74, "variavel": 106, "classificacao": 80, "categoria": 2682,
        "unidade": "Mil litros", "tipo": "bar",
    },
    {
        "id": "ovos_galinha",
        "keywords": ["ovos de galinha", "ovos", "produção de ovos"],
        "titulo": "Produção de Ovos de Galinha — Brasil",
        "tabela": 74, "variavel": 106, "classificacao": 80, "categoria": 2685,
        "unidade": "Mil dúzias", "tipo": "bar",
    },
    {
        "id": "mel",
        "keywords": ["mel", "produção de mel", "mel de abelha", "apicultura"],
        "titulo": "Produção de Mel de Abelha — Brasil",
        "tabela": 74, "variavel": 106, "classificacao": 80, "categoria": 2687,
        "unidade": "Quilogramas", "tipo": "bar",
    },
    # ── PECUÁRIA — REBANHOS ───────────────────────────────────────────────
    {
        "id": "rebanho_bovino",
        "keywords": ["rebanho bovino", "gado bovino", "bovinos", "cabeças de gado", "efetivo bovino"],
        "titulo": "Efetivo do Rebanho Bovino — Brasil",
        "tabela": 3939, "variavel": 105, "classificacao": 79, "categoria": 2670,
        "unidade": "Cabeças", "tipo": "line",
    },
    {
        "id": "rebanho_suino",
        "keywords": ["rebanho suíno", "suínos", "porcos", "suino"],
        "titulo": "Efetivo do Rebanho Suíno — Brasil",
        "tabela": 3939, "variavel": 105, "classificacao": 79, "categoria": 32794,
        "unidade": "Cabeças", "tipo": "line",
    },
    {
        "id": "rebanho_ovino",
        "keywords": ["rebanho ovino", "ovinos", "ovelhas"],
        "titulo": "Efetivo do Rebanho Ovino — Brasil",
        "tabela": 3939, "variavel": 105, "classificacao": 79, "categoria": 2677,
        "unidade": "Cabeças", "tipo": "line",
    },
    {
        "id": "rebanho_caprino",
        "keywords": ["rebanho caprino", "caprinos", "cabras", "bodes"],
        "titulo": "Efetivo do Rebanho Caprino — Brasil",
        "tabela": 3939, "variavel": 105, "classificacao": 79, "categoria": 2681,
        "unidade": "Cabeças", "tipo": "line",
    },
    {
        "id": "galinaceos",
        "keywords": ["galináceos", "galinaceos", "galinhas", "frangos", "aves"],
        "titulo": "Efetivo de Galináceos — Brasil",
        "tabela": 3939, "variavel": 105, "classificacao": 79, "categoria": 32796,
        "unidade": "Cabeças", "tipo": "bar",
    },
    # ── LAVOURAS TEMPORÁRIAS ──────────────────────────────────────────────
    # N3 (estado): tabela 5457, classificacao 782  — IDs prefixados com 40xxx
    # N1 (Brasil): tabela 1612, classificacao 81  — IDs antigos 2xxx
    {
        "id": "soja",
        "keywords": ["soja", "produção de soja", "grão de soja"],
        "titulo": "Produção de Soja — Brasil",
        "tabela": 5457, "variavel": 214, "classificacao": 782, "categoria": 40124,
        "tabela_n1": 1612, "classificacao_n1": 81, "categoria_n1": 2713,
        "unidade": "Toneladas", "tipo": "bar",
    },
    {
        "id": "milho",
        "keywords": ["milho", "produção de milho", "grão de milho"],
        "titulo": "Produção de Milho — Brasil",
        "tabela": 5457, "variavel": 214, "classificacao": 782, "categoria": 40122,
        "tabela_n1": 1612, "classificacao_n1": 81, "categoria_n1": 2711,
        "unidade": "Toneladas", "tipo": "bar",
    },
    {
        "id": "cana",
        "keywords": ["cana", "cana-de-açúcar", "cana de açúcar", "cana de acucar", "cana açúcar"],
        "titulo": "Produção de Cana-de-Açúcar — Brasil",
        "tabela": 5457, "variavel": 214, "classificacao": 782, "categoria": 40106,
        "tabela_n1": 1612, "classificacao_n1": 81, "categoria_n1": 2696,
        "unidade": "Toneladas", "tipo": "bar",
    },
    {
        "id": "arroz",
        "keywords": ["arroz", "produção de arroz"],
        "titulo": "Produção de Arroz — Brasil",
        "tabela": 5457, "variavel": 214, "classificacao": 782, "categoria": 40102,
        "tabela_n1": 1612, "classificacao_n1": 81, "categoria_n1": 2692,
        "unidade": "Toneladas", "tipo": "bar",
    },
    {
        "id": "feijao",
        "keywords": ["feijão", "feijao", "produção de feijão"],
        "titulo": "Produção de Feijão — Brasil",
        "tabela": 5457, "variavel": 214, "classificacao": 782, "categoria": 40112,
        "tabela_n1": 1612, "classificacao_n1": 81, "categoria_n1": 2702,
        "unidade": "Toneladas", "tipo": "bar",
    },
    {
        "id": "trigo",
        "keywords": ["trigo", "produção de trigo"],
        "titulo": "Produção de Trigo — Brasil",
        "tabela": 5457, "variavel": 214, "classificacao": 782, "categoria": 40127,
        "tabela_n1": 1612, "classificacao_n1": 81, "categoria_n1": 2716,
        "unidade": "Toneladas", "tipo": "bar",
    },
    {
        "id": "algodao",
        "keywords": ["algodão", "algodao", "produção de algodão", "cotonicultura"],
        "titulo": "Produção de Algodão — Brasil",
        "tabela": 5457, "variavel": 214, "classificacao": 782, "categoria": 40099,
        "tabela_n1": 1612, "classificacao_n1": 81, "categoria_n1": 2689,
        "unidade": "Toneladas", "tipo": "bar",
    },
    {
        "id": "mandioca",
        "keywords": ["mandioca", "produção de mandioca", "macaxeira", "aipim"],
        "titulo": "Produção de Mandioca — Brasil",
        "tabela": 5457, "variavel": 214, "classificacao": 782, "categoria": 40119,
        "tabela_n1": 1612, "classificacao_n1": 81, "categoria_n1": 2708,
        "unidade": "Toneladas", "tipo": "bar",
    },
    # ── LAVOURAS PERMANENTES ──────────────────────────────────────────────
    # N1: tabela 1613, classificacao 82  (categorias DIFERENTES das da 5457)
    # N3: tabela 5457, classificacao 782
    {
        "id": "cafe",
        "keywords": ["café", "cafe", "produção de café", "cafeicultura"],
        "titulo": "Produção de Café — Brasil",
        "tabela": 5457, "variavel": 214, "classificacao": 782, "categoria": 40139,
        "tabela_n1": 1613, "classificacao_n1": 82, "categoria_n1": 2723,
        "unidade": "Toneladas", "tipo": "bar",
    },
    {
        "id": "banana",
        "keywords": ["banana", "produção de banana"],
        "titulo": "Produção de Banana — Brasil",
        "tabela": 5457, "variavel": 214, "classificacao": 782, "categoria": 40136,
        "tabela_n1": 1613, "classificacao_n1": 82, "categoria_n1": 2720,
        "unidade": "Toneladas", "tipo": "bar",
    },
    {
        "id": "cacau",
        "keywords": ["cacau", "produção de cacau", "chocolate"],
        "titulo": "Produção de Cacau — Brasil",
        "tabela": 5457, "variavel": 214, "classificacao": 782, "categoria": 40138,
        "tabela_n1": 1613, "classificacao_n1": 82, "categoria_n1": 2722,
        "unidade": "Toneladas", "tipo": "bar",
    },
    {
        "id": "uva",
        "keywords": ["uva", "produção de uva", "viticultura", "vinho"],
        "titulo": "Produção de Uva — Brasil",
        "tabela": 5457, "variavel": 214, "classificacao": 782, "categoria": 40274,
        "tabela_n1": 1613, "classificacao_n1": 82, "categoria_n1": 2748,
        "unidade": "Toneladas", "tipo": "bar",
    },
    {
        "id": "laranja",
        "keywords": ["laranja", "produção de laranja", "citros"],
        "titulo": "Produção de Laranja — Brasil",
        "tabela": 5457, "variavel": 214, "classificacao": 782, "categoria": 40151,
        "tabela_n1": 1613, "classificacao_n1": 82, "categoria_n1": 2733,
        "unidade": "Toneladas", "tipo": "bar",
    },
    {
        "id": "castanha_caju",
        "keywords": ["castanha de caju", "caju", "cajueiro"],
        "titulo": "Produção de Castanha de Caju — Brasil",
        "tabela": 5457, "variavel": 214, "classificacao": 782, "categoria": 40143,
        "tabela_n1": 1613, "classificacao_n1": 82, "categoria_n1": 2725,
        "unidade": "Toneladas", "tipo": "bar",
    },
    {
        "id": "sisal",
        "keywords": ["sisal", "agave", "fibra de sisal"],
        "titulo": "Produção de Sisal — Brasil",
        "tabela": 5457, "variavel": 214, "classificacao": 782, "categoria": 40270,
        "tabela_n1": 1613, "classificacao_n1": 82, "categoria_n1": 2744,
        "unidade": "Toneladas", "tipo": "bar",
    },
    # ── FRUTICULTURA ──────────────────────────────────────────────────────
    {
        "id": "manga",
        "keywords": ["manga", "produção de manga"],
        "titulo": "Produção de Manga — Brasil",
        "tabela": 5457, "variavel": 214, "classificacao": 782, "categoria": 40262,
        "tabela_n1": 1613, "classificacao_n1": 82, "categoria_n1": 2737,
        "unidade": "Toneladas", "tipo": "bar",
    },
    {
        "id": "mamao",
        "keywords": ["mamão", "mamao", "produção de mamão", "papaya"],
        "titulo": "Produção de Mamão — Brasil",
        "tabela": 5457, "variavel": 214, "classificacao": 782, "categoria": 40261,
        "tabela_n1": 1613, "classificacao_n1": 82, "categoria_n1": 2736,
        "unidade": "Toneladas", "tipo": "bar",
    },
    {
        "id": "maracuja",
        "keywords": ["maracujá", "maracuja", "produção de maracujá", "maracujazeiro"],
        "titulo": "Produção de Maracujá — Brasil",
        "tabela": 5457, "variavel": 214, "classificacao": 782, "categoria": 40263,
        "tabela_n1": 1613, "classificacao_n1": 82, "categoria_n1": 2738,
        "unidade": "Toneladas", "tipo": "bar",
    },
    {
        "id": "goiaba",
        "keywords": ["goiaba", "produção de goiaba", "goiabeira"],
        "titulo": "Produção de Goiaba — Brasil",
        "tabela": 5457, "variavel": 214, "classificacao": 782, "categoria": 40149,
        "tabela_n1": 1613, "classificacao_n1": 82, "categoria_n1": 2731,
        "unidade": "Toneladas", "tipo": "bar",
    },
    {
        "id": "abacate",
        "keywords": ["abacate", "produção de abacate", "abacateiro"],
        "titulo": "Produção de Abacate — Brasil",
        "tabela": 5457, "variavel": 214, "classificacao": 782, "categoria": 40129,
        "tabela_n1": 1613, "classificacao_n1": 82, "categoria_n1": 2717,
        "unidade": "Toneladas", "tipo": "bar",
    },
    {
        "id": "coco",
        "keywords": ["coco", "coco-da-baía", "coco da baia", "produção de coco", "coqueiro"],
        "titulo": "Produção de Coco-da-Baía — Brasil",
        "tabela": 5457, "variavel": 214, "classificacao": 782, "categoria": 40145,
        "tabela_n1": 1613, "classificacao_n1": 82, "categoria_n1": 2727,
        "unidade": "Toneladas", "tipo": "bar",
    },
    {
        "id": "limao",
        "keywords": ["limão", "limao", "produção de limão", "limoeiro"],
        "titulo": "Produção de Limão — Brasil",
        "tabela": 5457, "variavel": 214, "classificacao": 782, "categoria": 40152,
        "tabela_n1": 1613, "classificacao_n1": 82, "categoria_n1": 2734,
        "unidade": "Toneladas", "tipo": "bar",
    },
    {
        "id": "tangerina",
        "keywords": ["tangerina", "mexerica", "bergamota", "ponkan"],
        "titulo": "Produção de Tangerina — Brasil",
        "tabela": 5457, "variavel": 214, "classificacao": 782, "categoria": 40271,
        "tabela_n1": 1613, "classificacao_n1": 82, "categoria_n1": 2745,
        "unidade": "Toneladas", "tipo": "bar",
    },
    {
        "id": "maca",
        "keywords": ["maçã", "maca", "produção de maçã"],
        "titulo": "Produção de Maçã — Brasil",
        "tabela": 5457, "variavel": 214, "classificacao": 782, "categoria": 40260,
        "tabela_n1": 1613, "classificacao_n1": 82, "categoria_n1": 2735,
        "unidade": "Toneladas", "tipo": "bar",
    },
    {
        "id": "pessego",
        "keywords": ["pêssego", "pessego", "produção de pêssego"],
        "titulo": "Produção de Pêssego — Brasil",
        "tabela": 5457, "variavel": 214, "classificacao": 782, "categoria": 40268,
        "tabela_n1": 1613, "classificacao_n1": 82, "categoria_n1": 2742,
        "unidade": "Toneladas", "tipo": "bar",
    },
    {
        "id": "figo",
        "keywords": ["figo", "produção de figo", "figueira"],
        "titulo": "Produção de Figo — Brasil",
        "tabela": 5457, "variavel": 214, "classificacao": 782, "categoria": 40148,
        "tabela_n1": 1613, "classificacao_n1": 82, "categoria_n1": 2730,
        "unidade": "Toneladas", "tipo": "bar",
    },
    # ── FRUTICULTURA TEMPORÁRIA (tabela 1612 para N1) ─────────────────────
    {
        "id": "abacaxi",
        "keywords": ["abacaxi", "produção de abacaxi", "ananás", "ananas"],
        "titulo": "Produção de Abacaxi — Brasil",
        "tabela": 5457, "variavel": 214, "classificacao": 782, "categoria": 40092,
        "tabela_n1": 1612, "classificacao_n1": 81, "categoria_n1": 2688,
        "unidade": "Toneladas", "tipo": "bar",
    },
    {
        "id": "melancia",
        "keywords": ["melancia", "produção de melancia"],
        "titulo": "Produção de Melancia — Brasil",
        "tabela": 5457, "variavel": 214, "classificacao": 782, "categoria": 40120,
        "tabela_n1": 1612, "classificacao_n1": 81, "categoria_n1": 2709,
        "unidade": "Toneladas", "tipo": "bar",
    },
    {
        "id": "melao",
        "keywords": ["melão", "melao", "produção de melão"],
        "titulo": "Produção de Melão — Brasil",
        "tabela": 5457, "variavel": 214, "classificacao": 782, "categoria": 40121,
        "tabela_n1": 1612, "classificacao_n1": 81, "categoria_n1": 2710,
        "unidade": "Toneladas", "tipo": "bar",
    },
]


def find_topic(text: str) -> dict | None:
    lower = text.lower()
    entries = []
    for entry in CATALOG:
        for kw in entry["keywords"]:
            if kw in lower:
                entries.append((len(kw), entry))
                break
    if not entries:
        return None
    entries.sort(key=lambda x: x[0], reverse=True)
    return entries[0][1]


def list_topics() -> list[str]:
    return [e["titulo"] for e in CATALOG]
