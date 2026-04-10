"""Configuración centralizada para SportsAgent (11.6 — AgentConfig dataclass)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from .thresholds import CACHE_TTL_DAYS_DEFAULT, TOP_N_DEFAULT


@dataclass
class AgentConfig:
    """Agrupa todos los parámetros de configuración de una ejecución de SportsAgent.

    Sustituye los 15 parámetros individuales del antiguo __init__ por un único
    objeto de configuración tipado y con valores por defecto centralizados.
    """

    # Obligatorio
    data_path: str

    # Fuente de datos
    fetch_real: bool = False
    competition_id: Optional[int] = None
    season: Optional[str] = None
    seasons: Optional[List[str]] = None

    # Filtros de análisis
    team: Optional[str] = None
    matchday: Optional[int] = None
    matchday_range: Optional[Tuple[int, int]] = None
    match_id: Optional[int] = None
    player: Optional[str] = None
    compare: Optional[Tuple[str, str]] = None

    # Opciones de presentación
    top_n: int = TOP_N_DEFAULT
    no_charts: bool = False

    # Caché
    refresh_cache: bool = False
    cache_ttl_days: int = CACHE_TTL_DAYS_DEFAULT
