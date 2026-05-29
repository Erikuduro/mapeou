import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

from orchestrator import process, ComplexRequestError
from generator_ibge import generate_ibge_map_bytes
from sidra_catalog import find_topic, list_topics
from sidra_api import (
    fetch_series, fetch_ranking_crops_state, fetch_ranking_states_crop,
    parse_year_range, parse_state,
)
from generator_chart import generate_chart, generate_ranking_chart

_KW_RANKING_CROPS = [
    "maiores produções", "maiores producoes", "principais culturas",
    "quais são as maiores", "quais sao as maiores", "top culturas",
    "ranking de culturas", "maior produção do estado", "maior producao do estado",
]
_KW_RANKING_STATES = [
    "top estados", "maiores produtores", "maiores estados", "ranking estados",
    "ranking de estados", "top 10 estados", "quais estados", "quais são os estados",
    "quais sao os estados", "maiores estados produtores",
]

def _detect_chart_type(text: str) -> str:
    lower = text.lower()
    if any(kw in lower for kw in _KW_RANKING_CROPS):
        return "ranking_crops"
    if any(kw in lower for kw in _KW_RANKING_STATES):
        return "ranking_states"
    return "series"


def _parse_single_year(text: str, default: int = 2023) -> int:
    import re
    years = re.findall(r'\b(19[5-9]\d|20[0-2]\d)\b', text)
    return int(years[-1]) if years else default

app = FastAPI(title="MapAIAgent")

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class MapRequest(BaseModel):
    text: str


@app.get("/")
async def index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/generate")
async def generate(req: MapRequest):
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Descreva um município para gerar o mapa.")

    def _run():
        result = process(req.text)
        return generate_ibge_map_bytes(
            result["municipio"],
            result["state_munis"],
            result["states"],
            result.get("sitio_urbano"),
        )

    try:
        pdf_bytes = await run_in_threadpool(_run)
    except ComplexRequestError as exc:
        raise HTTPException(
            status_code=422,
            detail={"type": "complex", "reason": exc.reason, "qgis_tip": exc.qgis_tip},
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="mapa.pdf"'},
    )


class ChartRequest(BaseModel):
    text: str


@app.post("/chart")
async def chart(req: ChartRequest):
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Descreva o dado que deseja visualizar.")

    topic      = find_topic(req.text)
    chart_type = _detect_chart_type(req.text)

    # Só exige topic quando a consulta é série temporal ou ranking de estados
    if topic is None and chart_type == "series":
        temas = " · ".join(list_topics())
        raise HTTPException(
            status_code=404,
            detail=(
                "Tema não encontrado no catálogo SIDRA. "
                "Dados de exportação, preços e comércio exterior estão no COMEX Stat (MDIC), fora do escopo atual. "
                f"Temas disponíveis: {temas}"
            ),
        )
    state      = parse_state(req.text)

    if chart_type == "ranking_crops":
        if state is None:
            raise HTTPException(
                status_code=400,
                detail="Informe o estado para ver as maiores produções. Ex: 'Maiores produções de Pernambuco'",
            )
        ano = _parse_single_year(req.text)
        def _run():
            data = fetch_ranking_crops_state(state, ano)
            return generate_ranking_chart(data)

    elif chart_type == "ranking_states":
        if topic is None:
            raise HTTPException(
                status_code=404,
                detail="Informe a cultura para o ranking. Ex: 'Top estados produtores de banana'",
            )
        ano = _parse_single_year(req.text)
        def _run():
            data = fetch_ranking_states_crop(topic, ano)
            return generate_ranking_chart(data)

    else:
        ano_ini, ano_fim = parse_year_range(req.text)
        def _run():
            series = fetch_series(topic, ano_ini, ano_fim, state)
            return generate_chart(series)

    try:
        pdf_bytes = await run_in_threadpool(_run)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return Response(
        content=pdf_bytes,
        media_type="image/png",
        headers={"Content-Disposition": 'inline; filename="grafico.png"'},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=False)
