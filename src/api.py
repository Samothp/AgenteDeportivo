"""API REST local — Agente Deportivo (FastAPI).

Arrancar con:
    uvicorn src.api:app --reload --port 8000

Documentación interactiva (Swagger UI):
    http://localhost:8000/docs

Documentación alternativa (ReDoc):
    http://localhost:8000/redoc
"""

from __future__ import annotations

import json
import logging
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from .agent import SportsAgent
from .config import AgentConfig
from .constants import COMPETITION_NAMES
from .data_loader import get_db_path, list_available_teams

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    format="%(asctime)s — %(name)s — %(levelname)s — %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("AgenteDeportivo.api")

# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------

limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])

# ---------------------------------------------------------------------------
# Aplicación
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Agente Deportivo API",
    description=(
        "API REST para análisis de partidos de fútbol. "
        "Expone los 6 modos del agente como endpoints HTTP. "
        "Los datos deben estar previamente descargados en la DB local "
        "(`data/db_{competition}_{season}.csv`) usando `--fetch-real` desde la CLI."
    ),
    version="3.0.0",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

# ---------------------------------------------------------------------------
# Schemas de entrada (Pydantic)
# ---------------------------------------------------------------------------


class BaseRequest(BaseModel):
    competition: int = Field(2014, description="ID de competición (2014=La Liga, 2021=Premier…)")
    season: str = Field("2024", description="Temporada en formato YYYY")
    top_n: int = Field(5, ge=1, le=50, description="Número de entradas en los rankings")


class LigaRequest(BaseRequest):
    matchday_range: Optional[List[int]] = Field(
        None,
        min_length=2,
        max_length=2,
        description="Rango de jornadas [inicio, fin]. Ej: [1, 19]",
    )


class EquipoRequest(BaseRequest):
    team: str = Field(..., description="Nombre parcial del equipo (ej. 'Mallorca')")
    seasons: Optional[List[str]] = Field(
        None,
        description="Lista de temporadas para análisis multi-temporada (ej. ['2022','2023','2024'])",
    )


class JornadaRequest(BaseRequest):
    jornada: int = Field(..., ge=1, description="Número de jornada")


class PartidoRequest(BaseRequest):
    match_id: int = Field(..., description="ID del partido (id_event en la DB local)")


class JugadorRequest(BaseRequest):
    team: str = Field(..., description="Nombre parcial del equipo")
    player: str = Field(..., description="Nombre parcial del jugador")


class CompareRequest(BaseRequest):
    team1: str = Field(..., description="Primer equipo")
    team2: str = Field(..., description="Segundo equipo")


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------


def _check_db(competition: int, season: str) -> None:
    """Lanza HTTP 404 si no existe la DB local para la competition+season."""
    db_path = get_db_path(competition, season)
    if not db_path.exists():
        raise HTTPException(
            status_code=404,
            detail=(
                f"No hay DB local para competition={competition} season={season}. "
                "Descarga los datos primero con: "
                f"python -m src.run_agent --fetch-real --competition {competition} --season {season}"
            ),
        )


def _build_agent(req: BaseRequest, **kwargs) -> SportsAgent:
    """Construye un SportsAgent válido a partir del request base."""
    _check_db(req.competition, req.season)
    db_path = get_db_path(req.competition, req.season)
    return SportsAgent(AgentConfig(
        data_path=str(db_path),
        fetch_real=False,
        competition_id=req.competition,
        season=req.season,
        top_n=req.top_n,
        no_charts=True,
        **kwargs,
    ))


def _run(agent: SportsAgent) -> JSONResponse:
    """Carga datos, analiza y devuelve el resultado como JSON."""
    agent.load_data()
    agent.analyze()
    json_str = agent.generate_json_report()
    return JSONResponse(content=json.loads(json_str))


# ---------------------------------------------------------------------------
# Endpoints de información
# ---------------------------------------------------------------------------


@app.get("/", summary="Health check", tags=["Info"])
@limiter.exempt
def root():
    """Comprueba que la API está activa y devuelve las competiciones disponibles."""
    return {"status": "ok", "version": "3.0.0", "competitions": COMPETITION_NAMES}


@app.get("/teams", summary="Listar equipos disponibles en la DB local", tags=["Info"])
@limiter.limit("30/minute")
def list_teams(request: Request,
    competition: int = Query(2014, description="ID de competición"),
    season: str = Query("2024", description="Temporada en formato YYYY"),
):
    """Devuelve los equipos presentes en la DB local para una competition+season."""
    _check_db(competition, season)
    teams = list_available_teams(competition, season)
    return {"competition": competition, "season": season, "teams": teams}


# ---------------------------------------------------------------------------
# Endpoints de informes
# ---------------------------------------------------------------------------


@app.post("/report/liga", summary="Informe de Liga completo", tags=["Informes"])
@limiter.limit("10/minute")
def report_liga(request: Request, req: LigaRequest):
    """
    Genera un informe completo de la temporada:
    clasificación, xPts, récords, estadísticas por equipo y rendimiento local/visitante.
    """
    matchday_range = tuple(req.matchday_range) if req.matchday_range else None
    agent = _build_agent(req, matchday_range=matchday_range)
    return _run(agent)


@app.post("/report/equipo", summary="Informe de Equipo", tags=["Informes"])
@limiter.limit("10/minute")
def report_equipo(request: Request, req: EquipoRequest):
    """
    Genera un informe de un equipo concreto:
    W/D/L, rachas, métricas con percentiles de liga, overperformance xG y conclusiones.
    """
    agent = _build_agent(req, team=req.team, seasons=req.seasons)
    return _run(agent)


@app.post("/report/jornada", summary="Informe de Jornada", tags=["Informes"])
@limiter.limit("10/minute")
def report_jornada(request: Request, req: JornadaRequest):
    """
    Genera el resumen de una jornada: resultados, estadísticas y clasificación acumulada.
    """
    agent = _build_agent(req, matchday=req.jornada)
    return _run(agent)


@app.post("/report/partido", summary="Informe de Partido", tags=["Informes"])
@limiter.limit("10/minute")
def report_partido(request: Request, req: PartidoRequest):
    """
    Genera la ficha técnica de un partido concreto (estadísticas cara a cara).
    Obtén el `match_id` consultando la DB local.
    """
    agent = _build_agent(req, match_id=req.match_id)
    return _run(agent)


@app.post("/report/jugador", summary="Informe de Jugador", tags=["Informes"])
@limiter.limit("10/minute")
def report_jugador(request: Request, req: JugadorRequest):
    """
    Genera el perfil de temporada de un jugador: stats, ratios y ranking en el equipo.
    """
    agent = _build_agent(req, team=req.team, player=req.player)
    return _run(agent)


@app.post("/report/compare", summary="Comparativa entre dos equipos", tags=["Informes"])
@limiter.limit("10/minute")
def report_compare(request: Request, req: CompareRequest):
    """
    Compara dos equipos de la misma competition+season:
    diferencias en todas las métricas y enfrentamientos H2H en la DB.
    """
    agent = _build_agent(req, compare=(req.team1, req.team2))
    return _run(agent)
