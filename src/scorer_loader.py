"""
Carga y caché local de goleadores por partido.

Fuente: TheSportsDB — lookupeventtimeline.php
  - Endpoint: GET /api/v1/json/{key}/lookupeventtimeline.php?id={event_id}
  - Devuelve eventos de línea de tiempo (goles, tarjetas, sustituciones…)
  - Con clave pública (3 / 123) funciona, pero con rate-limit bajo.

Estructura del caché local:
  data/scorers_{competition_id}_{season}.csv
  Columnas:
    match_id       – id_event del partido
    jornada        – número de jornada
    date           – fecha del partido
    local_team     – equipo local
    visitante_team – equipo visitante
    team           – equipo del goleador
    player_name    – nombre del jugador
    minute         – minuto del gol (str, p.ej. "28" o "90+2")
    goal_type      – 'goal' | 'goal_penalty' | 'own_goal'
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

import pandas as pd

_DATA_DIR = Path(__file__).parent.parent / "data"

_GOAL_TYPES = {"goal", "goal_penalty", "own_goal"}

# Mapeo de strType del API a nuestro vocabulario
_TYPE_MAP = {
    "goal":           "goal",
    "Goal":           "goal",
    "goal_penalty":   "goal_penalty",
    "Goal (Penalty)": "goal_penalty",
    "penalty":        "goal_penalty",
    "own_goal":       "own_goal",
    "Own Goal":       "own_goal",
}


def _scorers_csv_path(competition_id: int, season: str) -> Path:
    season_norm = str(season).split("-")[0]
    return _DATA_DIR / f"scorers_{competition_id}_{season_norm}.csv"


def _parse_timeline_events(events: list, match_id: str, jornada, date,
                            local_team: str, visitante_team: str) -> list[dict]:
    """Extrae filas de goles desde los eventos de timeline de un partido."""
    rows = []
    for ev in events:
        raw_type = ev.get("strType", "") or ""
        goal_type = _TYPE_MAP.get(raw_type)
        if goal_type is None:
            continue  # tarjeta, sustitución, etc.

        player_name = (
            ev.get("strPlayer")
            or ev.get("strComment")
            or ev.get("strTimeline", "")  # fallback extremo
        ).strip()
        team = (ev.get("strTeam") or "").strip()
        minute = (ev.get("strTimeline") or ev.get("strTimelineDetail") or "").strip()

        rows.append({
            "match_id":       match_id,
            "jornada":        jornada,
            "date":           date,
            "local_team":     local_team,
            "visitante_team": visitante_team,
            "team":           team,
            "player_name":    player_name,
            "minute":         minute,
            "goal_type":      goal_type,
        })
    return rows


def fetch_scorers(
    competition_id: int,
    season: str,
    df_matches: pd.DataFrame,
    api_key: str = "3",
    verbose: bool = False,
    delay: float = 0.65,
) -> pd.DataFrame:
    """Descarga los goleadores de todos los partidos del DataFrame usando TheSportsDB.

    Sólo llama a la API para partidos que aún no están en el caché.
    Guarda el resultado acumulado en data/scorers_{competition_id}_{season}.csv.

    Args:
        competition_id: ID de competición (p.ej. 2014 para La Liga).
        season:         Temporada ('2025' o '2025-2026').
        df_matches:     DataFrame con columnas id_event, jornada, date,
                        local_team, visitante_team (resultado de load_match_data).
        api_key:        Clave TheSportsDB. Con '3'/'123' funciona con rate-limit bajo.
        verbose:        Imprimir progreso.
        delay:          Segundos entre llamadas a la API.

    Returns:
        DataFrame con todos los goles (filas) de la temporada cacheados.
    """
    import requests

    if "id_event" not in df_matches.columns:
        if verbose:
            print("[scorer_loader] Sin columna id_event, no se pueden obtener goleadores.")
        return pd.DataFrame(columns=[
            "match_id", "jornada", "date", "local_team", "visitante_team",
            "team", "player_name", "minute", "goal_type",
        ])

    csv_path = _scorers_csv_path(competition_id, season)

    # Cargar caché existente
    if csv_path.exists():
        cached = pd.read_csv(csv_path, dtype={"match_id": str})
        already_fetched = set(cached["match_id"].astype(str))
    else:
        cached = pd.DataFrame()
        already_fetched = set()

    base_url = f"https://www.thesportsdb.com/api/v1/json/{api_key}/lookupeventtimeline.php"

    pending = df_matches[
        ~df_matches["id_event"].astype(str).isin(already_fetched)
    ]

    if pending.empty:
        if verbose:
            print("[scorer_loader] Caché al día, no hay partidos nuevos.")
        return cached if not cached.empty else pd.DataFrame(columns=[
            "match_id", "jornada", "date", "local_team", "visitante_team",
            "team", "player_name", "minute", "goal_type",
        ])

    if verbose:
        print(f"[scorer_loader] Descargando timeline de {len(pending)} partidos...")

    new_rows: list[dict] = []
    fetched_ids: set[str] = set()

    for i, (_, match) in enumerate(pending.iterrows(), 1):
        event_id = str(int(float(match["id_event"])))
        home = match.get("local_team", "")
        away = match.get("visitante_team", "")
        jornada = match.get("jornada")
        date = match.get("date")

        if verbose:
            print(f"  [{i}/{len(pending)}] {home} vs {away}          ", end="\r", flush=True)

        try:
            r = requests.get(
                base_url,
                params={"id": event_id},
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=20,
            )
            r.raise_for_status()
            data = r.json()
        except Exception as exc:
            if verbose:
                print(f"\n  [warn] Error en partido {event_id}: {exc}")
            # Marcar como intentado (sin goles) para no reintentar
            fetched_ids.add(event_id)
            if i < len(pending):
                time.sleep(delay)
            continue

        events = data.get("timeline") or []
        rows = _parse_timeline_events(
            events, event_id, jornada, date, home, away
        )
        new_rows.extend(rows)
        fetched_ids.add(event_id)

        if i < len(pending):
            time.sleep(delay)

    if verbose:
        total_goals = len(new_rows)
        print(f"\n[scorer_loader] {total_goals} goles descargados de {len(fetched_ids)} partidos.")

    # Añadir también filas vacías para partidos sin goles (para marcarlos como procesados)
    # Estos partidos tendrán 0 filas pero sabremos que ya se consultaron.
    # Lo indicamos añadiendo la lista de IDs procesados a un "log" dentro del propio CSV
    # con goal_type='_fetched' (fila centinela que filtramos al consultar).
    sentinel_rows = [
        {
            "match_id": eid,
            "jornada": None, "date": None, "local_team": None,
            "visitante_team": None, "team": None,
            "player_name": None, "minute": None, "goal_type": "_fetched",
        }
        for eid in fetched_ids
        if eid not in {r["match_id"] for r in new_rows}
    ]

    all_new = pd.DataFrame(new_rows + sentinel_rows)

    if not cached.empty:
        combined = pd.concat([cached, all_new], ignore_index=True)
    else:
        combined = all_new

    csv_path.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(csv_path, index=False)

    return combined[combined["goal_type"] != "_fetched"].reset_index(drop=True)


def load_scorers(
    competition_id: int,
    season: str,
    df_matches: Optional[pd.DataFrame] = None,
    fetch_real: bool = False,
    verbose: bool = False,
) -> pd.DataFrame:
    """Carga goleadores desde caché local o descarga si no existe/se pide actualizar.

    Args:
        competition_id: ID de competición.
        season:         Temporada.
        df_matches:     DataFrame de partidos (necesario si fetch_real=True o no hay caché).
        fetch_real:     Si True, descarga los partidos que falten en caché.
        verbose:        Imprimir progreso.

    Returns:
        DataFrame de goles reales (sin filas centinela).
        Columnas: match_id, jornada, date, local_team, visitante_team,
                  team, player_name, minute, goal_type.
        DataFrame vacío si no hay datos disponibles.
    """
    csv_path = _scorers_csv_path(competition_id, season)

    if csv_path.exists() and not fetch_real:
        df = pd.read_csv(csv_path, dtype={"match_id": str})
        return df[df["goal_type"] != "_fetched"].reset_index(drop=True)

    if df_matches is not None:
        return fetch_scorers(
            competition_id, season, df_matches,
            verbose=verbose or fetch_real,
        )

    if csv_path.exists():
        df = pd.read_csv(csv_path, dtype={"match_id": str})
        return df[df["goal_type"] != "_fetched"].reset_index(drop=True)

    return pd.DataFrame(columns=[
        "match_id", "jornada", "date", "local_team", "visitante_team",
        "team", "player_name", "minute", "goal_type",
    ])


# ---------------------------------------------------------------------------
# Funciones de consulta sobre el DataFrame de goleadores
# ---------------------------------------------------------------------------

def scorers_for_matchday(scorers_df: pd.DataFrame, matchday: int) -> pd.DataFrame:
    """Filtra los goles de una jornada concreta.

    Returns:
        DataFrame ordenado por (local_team, minute) con los goles de la jornada.
        Excluye own_goals de la lista de goleadores del equipo (los mueve al rival).
    """
    if scorers_df.empty or "jornada" not in scorers_df.columns:
        return pd.DataFrame()
    md = scorers_df[
        (scorers_df["jornada"] == matchday) &
        (scorers_df["goal_type"] != "_fetched")
    ].copy()
    return md.reset_index(drop=True)


def top_scorers_from_events(
    scorers_df: pd.DataFrame,
    n: int = 10,
    competition_wide: bool = True,
    team: Optional[str] = None,
) -> pd.DataFrame:
    """Ranking de goleadores calculado desde los eventos de gol.

    Args:
        scorers_df:        DataFrame completo de goles (load_scorers).
        n:                 Número de jugadores a devolver.
        competition_wide:  Si True, ranking de toda la liga. Si False, filtra por equipo.
        team:              Nombre del equipo (solo si competition_wide=False).

    Returns:
        DataFrame con columnas: player_name, team, goals, penalties.
    """
    if scorers_df.empty:
        return pd.DataFrame(columns=["player_name", "team", "goals", "penalties"])

    df = scorers_df[scorers_df["goal_type"] != "_fetched"].copy()

    # Los own_goals cuentan para el rival, no para el jugador
    df = df[df["goal_type"] != "own_goal"]

    if not competition_wide and team:
        df = df[df["team"].str.lower().str.contains(team.strip().lower(), na=False)]

    if df.empty:
        return pd.DataFrame(columns=["player_name", "team", "goals", "penalties"])

    grouped = (
        df.groupby(["player_name", "team"])
        .agg(
            goals=("goal_type", "count"),
            penalties=("goal_type", lambda x: (x == "goal_penalty").sum()),
        )
        .reset_index()
        .sort_values("goals", ascending=False)
        .head(n)
        .reset_index(drop=True)
    )
    return grouped


def player_goal_streak(scorers_df: pd.DataFrame, player_name: str, df_matches: pd.DataFrame) -> dict:
    """Calcula la racha actual de partidos marcando y la racha máxima histórica.

    Args:
        scorers_df:  DataFrame de goles (load_scorers).
        player_name: Nombre del jugador (búsqueda parcial).
        df_matches:  DataFrame de todos los partidos de la temporada (ordenado por jornada).

    Returns:
        Dict con:
          - racha_actual: número de partidos consecutivos marcando (hasta el último jugado)
          - racha_max:    racha máxima histórica de la temporada
          - sin_marcar:   partidos consecutivos sin marcar (si está en sequía)
          - total_goles:  total de goles del jugador en la temporada
    """
    if scorers_df.empty or df_matches.empty:
        return {"racha_actual": 0, "racha_max": 0, "sin_marcar": 0, "total_goles": 0}

    name_lower = player_name.strip().lower()

    # Partidos donde marcó el jugador (excluye own_goals y sentinelas)
    player_goals = scorers_df[
        (scorers_df["player_name"].str.lower().str.contains(name_lower, na=False)) &
        (scorers_df["goal_type"].isin({"goal", "goal_penalty"}))
    ]
    match_ids_with_goal = set(player_goals["match_id"].astype(str))
    total_goles = len(player_goals)

    # Ordenar partidos de la temporada
    matches = df_matches.copy()
    if "jornada" in matches.columns and matches["jornada"].notna().any():
        matches = matches.sort_values("jornada")
    elif "date" in matches.columns:
        matches = matches.sort_values("date")

    # Para cada partido, ¿marcó?
    scored_per_match = [
        str(int(float(mid))) in match_ids_with_goal
        for mid in matches["id_event"].dropna()
    ]

    # Racha máxima y actual
    racha_max = 0
    current = 0
    for s in scored_per_match:
        if s:
            current += 1
            racha_max = max(racha_max, current)
        else:
            current = 0
    racha_actual = current  # partidos consecutivos marcando al final de la lista

    # Sequía actual (sin marcar al final)
    sin_marcar = 0
    for s in reversed(scored_per_match):
        if not s:
            sin_marcar += 1
        else:
            break

    return {
        "racha_actual": racha_actual,
        "racha_max": racha_max,
        "sin_marcar": sin_marcar if racha_actual == 0 else 0,
        "total_goles": total_goles,
    }
