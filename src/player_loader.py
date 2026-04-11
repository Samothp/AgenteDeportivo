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

import os
from pathlib import Path
from typing import Optional

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

# Slug de liga en ESPN
_ESPN_LEAGUE = {
    2014: "esp.1",          # La Liga
    2021: "eng.1",          # Premier League
    2002: "ger.1",          # Bundesliga
    2019: "ita.1",          # Serie A
    2015: "fra.1",          # Ligue 1       (verificado: 18 equipos)
    2017: "por.1",          # Primeira Liga (verificado: 18 equipos)
    2001: "uefa.champions", # UEFA Champions League (verificado: 36 equipos)
    2146: "uefa.europa",    # UEFA Europa League    (verificado: 36 equipos)
}

# TheSportsDB — fallback cuando ESPN no encuentra el equipo
_TSDB_API_KEY = os.getenv("THESPORTSDB_API_KEY", "3")  # '3' = key pública de prueba
_TSDB_BASE = f"https://www.thesportsdb.com/api/v1/json/{_TSDB_API_KEY}"

_ESPN_BASE = "https://site.api.espn.com/apis/site/v2/sports/soccer"
_DATA_DIR = Path(__file__).parent.parent / "data"
_ESPN_STAT_FIELDS = (
    "totalGoals",
    "goalAssists",
    "yellowCards",
    "redCards",
    "appearances",
    "shotsOnTarget",
    "totalShots",       # tiros totales (a puerta + fuera + bloqueados)
    "minutesPlayed",   # minutos jugados en la temporada
)

# Campos del roster ESPN que capturamos adicionalmente (perfil físico/biográfico)
_ESPN_PROFILE_FIELDS = (
    "height",       # pulgadas → convertir a cm
    "weight",       # libras → convertir a kg
    "age",          # años
    "dateOfBirth",  # 'YYYY-MM-DDTHH:MMZ'
    "jersey",       # número dorsal
    "citizenship",  # nacionalidad en texto (p.ej. 'Spain')
)

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


def _inches_to_cm(inches) -> Optional[float]:
    try:
        return round(float(inches) * 2.54, 1)
    except (TypeError, ValueError):
        return None


def _lbs_to_kg(lbs) -> Optional[float]:
    try:
        return round(float(lbs) * 0.453592, 1)
    except (TypeError, ValueError):
        return None


def _parse_dob(raw: str) -> Optional[str]:
    """Extrae la fecha YYYY-MM-DD de cadenas como '1984-05-27T07:00Z'."""
    if not raw:
        return None
    return str(raw).split("T")[0]


def _fetch_roster(team_id: int, league_slug: str, team_name: str) -> list[dict]:
    """Descarga el roster de un equipo y extrae stats de rendimiento y perfil físico."""
    data = _get(f"{_ESPN_BASE}/{league_slug}/teams/{team_id}/roster")
    athletes = data.get("athletes", [])

    rows = []
    for a in athletes:
        stats_block = a.get("statistics", {})
        if not stats_block:
            continue
        cats = stats_block.get("splits", {}).get("categories", [])
        stat_values: dict[str, float] = {}
        for cat in cats:
            for stat in cat.get("stats", []):
                if stat["name"] in _ESPN_STAT_FIELDS:
                    stat_values[stat["name"]] = int(stat.get("value", 0))

        goals = stat_values.get("totalGoals", 0)
        assists = stat_values.get("goalAssists", 0)
        shots_on_target = stat_values.get("shotsOnTarget", 0)
        shots_total = stat_values.get("totalShots", 0)
        minutes_played = stat_values.get("minutesPlayed", 0)

        # Posición completa (ej. 'Centre-Forward') vs abbreviation (ej. 'CF')
        pos_block = a.get("position") or {}

        rows.append({
            "player_id":      int(a["id"]),
            "player_name":    a.get("displayName", ""),
            "team":           team_name,
            "position":       pos_block.get("abbreviation", ""),
            "position_full":  pos_block.get("displayName") or pos_block.get("name", ""),
            "appearances":    int(stat_values.get("appearances", 0)),
            "goals":          int(goals),
            "assists":        int(assists),
            "yellow_cards":   int(stat_values.get("yellowCards", 0)),
            "red_cards":      int(stat_values.get("redCards", 0)),
            "shots_on_target":int(shots_on_target),
            "shots_total":    int(shots_total),
            "minutes_played": int(minutes_played),
            "goals_assists":  int(goals + assists),
            # Perfil físico/biográfico (ESPN)
            "height_cm":      _inches_to_cm(a.get("height")),
            "weight_kg":      _lbs_to_kg(a.get("weight")),
            "age":            a.get("age"),
            "date_of_birth":  _parse_dob(a.get("dateOfBirth", "")),
            "nationality":    a.get("citizenship") or "",
            "jersey":         a.get("jersey") or "",
            # Imágenes (se rellenan después con TheSportsDB)
            "thumb_url":      "",
            "thumb_local":    "",
            "cutout_url":     "",
            "cutout_local":   "",
            "player_id_tsdb": "",
        })
    return rows


def _fetch_roster_thesportsdb(team_name: str, verbose: bool = False) -> list[dict]:
    """Fallback: obtiene roster desde TheSportsDB cuando ESPN no encuentra el equipo.

    Devuelve filas con nombre y posición del jugador. Las estadísticas
    (goles, asistencias, etc.) se rellenan con 0 porque TheSportsDB no
    expone stats de partidos en su API pública/premium de roster.
    """
    if verbose:
        print(f"  [fallback] Intentando TheSportsDB para '{team_name}'...")

    try:
        r = requests.get(
            f"{_TSDB_BASE}/searchteams.php",
            params={"t": team_name},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=15,
        )
        r.raise_for_status()
        teams = r.json().get("teams") or []
    except Exception as e:
        if verbose:
            print(f"  [fallback] TheSportsDB searchteams falló: {e}")
        return []

    if not teams:
        if verbose:
            print(f"  [fallback] Equipo '{team_name}' no encontrado en TheSportsDB.")
        return []

    team_id = teams[0]["idTeam"]
    canonical_name = teams[0].get("strTeam", team_name)
    if verbose:
        print(f"  [fallback] TheSportsDB team_id={team_id} ({canonical_name}). Descargando roster...")

    try:
        r2 = requests.get(
            f"{_TSDB_BASE}/lookup_all_players.php",
            params={"id": team_id},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=15,
        )
        r2.raise_for_status()
        players = r2.json().get("player") or []
    except Exception as e:
        if verbose:
            print(f"  [fallback] TheSportsDB lookup_all_players falló: {e}")
        return []

    if not players:
        if verbose:
            print("  [fallback] Sin jugadores en TheSportsDB.")
        return []

    if verbose:
        print(f"  [fallback] {len(players)} jugadores obtenidos (sin stats de partido — solo roster).")

    rows = []
    for p in players:
        if p.get("strStatus", "Active") != "Active":
            continue
        rows.append({
            "player_id": int(p.get("idPlayer") or 0),
            "player_name": p.get("strPlayer", ""),
            "team": canonical_name,
            "position": p.get("strPosition", ""),
            "appearances": 0,
            "goals": 0,
            "assists": 0,
            "yellow_cards": 0,
            "red_cards": 0,
            "shots_on_target": 0,
            "goals_assists": 0,
        })
    return rows


def _enrich_with_tsdb_images(df: pd.DataFrame, team_name: str, verbose: bool = False) -> pd.DataFrame:
    """Enriquece el DataFrame de jugadores con URLs e imágenes locales de TheSportsDB.

    Con API key de pago: UNA llamada batch para todos los jugadores.
    Con clave gratuita: usa lookup_all_players (sin imágenes batch) o búsqueda
    individual por nombre (solo para el jugador en foco, no en batch).
    """
    try:
        from .image_fetcher import get_player_images_for_team, get_cached_team_meta
    except ImportError:
        return df

    if verbose:
        print(f"  Enriqueciendo con imágenes TheSportsDB para '{team_name}'...")

    # Obtener team_id_tsdb de la caché para mejorar el fallback
    meta_cached = get_cached_team_meta(team_name, 2014)
    team_id_tsdb = meta_cached.get("team_id_tsdb", "")

    tsdb_players = get_player_images_for_team(team_name, team_id_tsdb=team_id_tsdb, download=True)
    if not tsdb_players:
        if verbose:
            print("  [info] Sin datos de imagen de TheSportsDB para este equipo (clave gratuita).")
        return df

    df = df.copy()
    # Asegurar que existen las columnas de imagen/metadata
    for col in ("thumb_url", "thumb_local", "cutout_url", "cutout_local", "player_id_tsdb",
                "date_born", "position_tsdb"):
        if col not in df.columns:
            df[col] = ""

    for idx, row in df.iterrows():
        name_lower = str(row.get("player_name", "")).lower()
        # Búsqueda exacta primero, luego por apellido
        tsdb = tsdb_players.get(name_lower)
        if tsdb is None:
            parts = name_lower.split()
            last = parts[-1] if parts else ""
            for k, v in tsdb_players.items():
                if last and last in k:
                    tsdb = v
                    break
        if tsdb is None:
            continue
        for col in ("thumb_url", "thumb_local", "cutout_url", "cutout_local",
                    "player_id_tsdb", "date_born", "position_tsdb"):
            val = tsdb.get(col) or ""
            if val:
                df.at[idx, col] = val
        if not df.at[idx, "nationality"] and tsdb.get("nationality"):
            df.at[idx, "nationality"] = tsdb["nationality"]

    if verbose:
        matched = df["thumb_local"].astype(bool).sum()
        print(f"  {matched}/{len(df)} jugadores con foto local.")

    return df


def fetch_player_stats(
    team_name: str,
    competition_id: int = 2014,
    season: str = "2025-2026",
    verbose: bool = True,
    with_images: bool = True,
) -> pd.DataFrame:
    """Descarga estadisticas de todos los jugadores de un equipo via ESPN
    y opcionalmente enriquece con imágenes de TheSportsDB.

    Guarda el resultado en caché CSV local.

    Args:
        team_name:      Nombre del equipo (busqueda parcial, case-insensitive)
        competition_id: ID de competicion del proyecto (2014 = La Liga)
        season:         Temporada 'YYYY-YYYY' o 'YYYY' (solo para nombrar el cache)
        verbose:        Imprimir progreso en consola
        with_images:    Si True, descarga imágenes de jugadores de TheSportsDB
    """
    league_slug = _get_espn_league(competition_id)

    if verbose:
        print(f"Buscando '{team_name}' en ESPN ({league_slug})...")

    team_id = _find_team_id(team_name, league_slug)
    if team_id is None:
        if verbose:
            print(f"  [warn] Equipo '{team_name}' no encontrado en ESPN. Probando fallback TheSportsDB...")
        rows = _fetch_roster_thesportsdb(team_name, verbose=verbose)
        if not rows:
            return pd.DataFrame()
        season_year = _season_to_year(season)
        df = pd.DataFrame(rows)
        df["season"] = f"{season_year}-{season_year + 1}"
        df["competition_id"] = competition_id
        if with_images:
            df = _enrich_with_tsdb_images(df, team_name, verbose=verbose)
        csv_path = _players_csv_path(competition_id, season)
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(csv_path, index=False)
        return df

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

    if with_images:
        df = _enrich_with_tsdb_images(df, team_name, verbose=verbose)

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
