"""
Carga y cache local de estadisticas de jugadores por temporada.

Fuente: ESPN API (no oficial, sin autenticacion)
  - Endpoint equipos: GET /apis/site/v2/sports/soccer/{league}/teams
  - Endpoint roster:  GET /apis/site/v2/sports/soccer/{league}/teams/{id}/roster
  - Sin limite de peticiones conocido, sin API key necesaria
  - Datos disponibles por jugador: goles, asistencias, apariciones,
    tarjetas amarillas, tarjetas rojas, tiros a puerta

Estructura del cache local:
  data/players_{competition_id}_{season}.csv
  Columnas: player_id, player_name, team, position,
            appearances, goals, assists, yellow_cards, red_cards,
            shots_on_target, goals_assists, season, competition_id
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd
import requests

# Slug de liga en ESPN
_ESPN_LEAGUE = {
    2014: "esp.1",   # La Liga
    2021: "eng.1",   # Premier League
    2002: "ger.1",   # Bundesliga
    2019: "ita.1",   # Serie A
    2015: "fra.1",   # Ligue 1
    2017: "por.1",   # Primeira Liga
}

_ESPN_BASE = "https://site.api.espn.com/apis/site/v2/sports/soccer"
_DATA_DIR = Path(__file__).parent.parent / "data"
_ESPN_STAT_FIELDS = ("totalGoals", "goalAssists", "yellowCards", "redCards", "appearances", "shotsOnTarget")

# Cache en memoria: (league_slug) -> list[{id, name, slug}]
_teams_cache: dict[str, list[dict]] = {}


def _get(url: str, params: dict | None = None) -> dict:
    r = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
    r.raise_for_status()
    return r.json()


def _season_to_year(season: str) -> int:
    s = str(season).strip()
    return int(s.split("-")[0]) if "-" in s else int(s)


def _players_csv_path(competition_id: int, season: str) -> Path:
    year = _season_to_year(season)
    return _DATA_DIR / f"players_{competition_id}_{year}-{year + 1}.csv"


def _get_espn_league(competition_id: int) -> str:
    slug = _ESPN_LEAGUE.get(competition_id)
    if not slug:
        raise ValueError(f"Competicion {competition_id} no soportada para stats de jugadores.")
    return slug


def _find_team_id(team_name: str, league_slug: str) -> Optional[int]:
    """Devuelve el ESPN team_id buscando por nombre parcial."""
    if league_slug not in _teams_cache:
        data = _get(f"{_ESPN_BASE}/{league_slug}/teams")
        raw = data.get("sports", [{}])[0].get("leagues", [{}])[0].get("teams", [])
        _teams_cache[league_slug] = [
            {"id": int(t["team"]["id"]), "name": t["team"]["name"]}
            for t in raw
        ]

    name_lower = team_name.lower()
    for t in _teams_cache[league_slug]:
        t_lower = t["name"].lower()
        if t_lower == name_lower or name_lower in t_lower or t_lower in name_lower:
            return t["id"]
    return None


def _fetch_roster(team_id: int, league_slug: str, team_name: str) -> list[dict]:
    """Descarga el roster de un equipo y extrae las stats."""
    data = _get(f"{_ESPN_BASE}/{league_slug}/teams/{team_id}/roster")
    athletes = data.get("athletes", [])

    rows = []
    for a in athletes:
        stats_block = a.get("statistics", {})
        if not stats_block:
            continue
        cats = stats_block.get("splits", {}).get("categories", [])
        stat_values: dict[str, int] = {}
        for cat in cats:
            for stat in cat.get("stats", []):
                if stat["name"] in _ESPN_STAT_FIELDS:
                    stat_values[stat["name"]] = int(stat.get("value", 0))

        goals = stat_values.get("totalGoals", 0)
        assists = stat_values.get("goalAssists", 0)
        rows.append({
            "player_id": int(a["id"]),
            "player_name": a.get("displayName", ""),
            "team": team_name,
            "position": a.get("position", {}).get("abbreviation", ""),
            "appearances": stat_values.get("appearances", 0),
            "goals": goals,
            "assists": assists,
            "yellow_cards": stat_values.get("yellowCards", 0),
            "red_cards": stat_values.get("redCards", 0),
            "shots_on_target": stat_values.get("shotsOnTarget", 0),
            "goals_assists": goals + assists,
        })
    return rows


def fetch_player_stats(
    team_name: str,
    competition_id: int = 2014,
    season: str = "2025-2026",
    verbose: bool = True,
) -> pd.DataFrame:
    """
    Descarga estadisticas de todos los jugadores de un equipo via ESPN
    y guarda en cache CSV local.

    Args:
        team_name:      Nombre del equipo (busqueda parcial, case-insensitive)
        competition_id: ID de competicion del proyecto (2014 = La Liga)
        season:         Temporada 'YYYY-YYYY' o 'YYYY' (solo para nombrar el cache)
        verbose:        Imprimir progreso en consola
    """
    league_slug = _get_espn_league(competition_id)

    if verbose:
        print(f"Buscando '{team_name}' en ESPN ({league_slug})...")

    team_id = _find_team_id(team_name, league_slug)
    if team_id is None:
        if verbose:
            print(f"  [warn] Equipo '{team_name}' no encontrado en ESPN.")
        return pd.DataFrame()

    if verbose:
        print(f"  ESPN team_id={team_id}. Descargando roster...")

    rows = _fetch_roster(team_id, league_slug, team_name)
    if not rows:
        if verbose:
            print("  [warn] Sin datos de jugadores.")
        return pd.DataFrame()

    season_year = _season_to_year(season)
    df = pd.DataFrame(rows)
    df["season"] = f"{season_year}-{season_year + 1}"
    df["competition_id"] = competition_id

    csv_path = _players_csv_path(competition_id, season)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(csv_path, index=False)

    if verbose:
        print(f"  {len(df)} jugadores guardados en {csv_path.name}")

    return df


def load_player_stats(
    team_name: str,
    competition_id: int = 2014,
    season: str = "2025-2026",
    fetch_real: bool = False,
    verbose: bool = False,
) -> pd.DataFrame:
    """
    Carga estadisticas de jugadores desde cache local o las descarga si no existen.

    Args:
        team_name:      Nombre del equipo
        competition_id: ID de competicion del proyecto
        season:         Temporada 'YYYY-YYYY' o 'YYYY'
        fetch_real:     Si True, fuerza descarga aunque haya cache
        verbose:        Imprimir progreso en consola

    Returns:
        DataFrame con columnas: player_name, goals, assists, yellow_cards,
                                red_cards, appearances, shots_on_target,
                                goals_assists, position
        Incluye todos los jugadores del equipo con estadisticas disponibles.
    """
    csv_path = _players_csv_path(competition_id, season)

    if csv_path.exists() and not fetch_real:
        df = pd.read_csv(csv_path)
        team_lower = team_name.lower()
        mask = df["team"].str.lower().str.contains(team_lower, na=False)
        team_df = df[mask]
        if not team_df.empty:
            return team_df.reset_index(drop=True)

    return fetch_player_stats(team_name, competition_id, season, verbose=verbose or fetch_real)
