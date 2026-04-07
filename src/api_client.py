import os
import time
from pathlib import Path
from typing import Optional

import pandas as pd
import requests
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()


class SportsDBAPI:
    """Cliente para TheSportsDB (https://www.thesportsdb.com)."""

    BASE_URL = "https://www.thesportsdb.com/api/v1/json"

    # Compatibilidad con IDs históricos usados por el proyecto.
    COMPETITION_MAP = {
        2014: 4335,  # La Liga
        2021: 4328,  # Premier League
        2002: 4331,  # Bundesliga
        2019: 4332,  # Serie A
        2015: 4334,  # Ligue 1
        2017: 4344,  # Primeira Liga
    }

    # Mapeo de nombres de estadísticas de la API a columnas del DataFrame.
    STAT_MAP = {
        'Shots on Goal':    ('shots_on_target_local',       'shots_on_target_visitante'),
        'Shots off Goal':   ('shots_off_target_local',      'shots_off_target_visitante'),
        'Total Shots':      ('shots_local',                 'shots_visitante'),
        'Blocked Shots':    ('shots_blocked_local',         'shots_blocked_visitante'),
        'Shots insidebox':  ('shots_inside_box_local',      'shots_inside_box_visitante'),
        'Shots outsidebox': ('shots_outside_box_local',     'shots_outside_box_visitante'),
        'Fouls':            ('faltas_local',                'faltas_visitante'),
        'Corner Kicks':     ('corners_local',               'corners_visitante'),
        'Offsides':         ('fueras_de_juego_local',       'fueras_de_juego_visitante'),
        'Ball Possession':  ('posesion_local',              'posesion_visitante'),
        'Yellow Cards':     ('amarillas_local',             'amarillas_visitante'),
        'Red Cards':        ('rojas_local',                 'rojas_visitante'),
        'Goalkeeper Saves': ('paradas_local',               'paradas_visitante'),
        'Total passes':     ('pases_local',                 'pases_visitante'),
        'Passes accurate':  ('pases_precisos_local',        'pases_precisos_visitante'),
        'Passes %':         ('precision_pases_local',       'precision_pases_visitante'),
        'expected_goals':   ('xg_local',                   'xg_visitante'),
    }

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = (
            api_key
            or os.getenv('THESPORTSDB_API_KEY')
            or os.getenv('SPORTSDB_API_KEY')
            or '078593'
        )

    def _get_json(self, endpoint: str, params: dict) -> dict:
        url = f"{self.BASE_URL}/{self.api_key}/{endpoint}"
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()

    def _resolve_league_id(self, competition_id: int) -> int:
        return self.COMPETITION_MAP.get(competition_id, competition_id)

    def _season_to_range(self, season: Optional[str]) -> str:
        # Acepta "2025" y lo convierte a "2025-2026" para TheSportsDB.
        if not season:
            return '2025-2026'
        season = str(season).strip()
        if '-' in season:
            return season
        try:
            start_year = int(season)
        except ValueError:
            return season
        return f"{start_year}-{start_year + 1}"

    def _extract_scored_rows(self, events: list, league_id: int, season_label: str) -> list:
        rows = []
        for event in events:
            home_score = event.get('intHomeScore')
            away_score = event.get('intAwayScore')

            # Solo partidos jugados (con marcador disponible).
            if home_score is None or away_score is None:
                continue

            rows.append({
                'date': event.get('strTimestamp') or event.get('dateEvent'),
                'local_team': event.get('strHomeTeam'),
                'visitante_team': event.get('strAwayTeam'),
                'goles_local': int(home_score),
                'goles_visitante': int(away_score),
                'status': event.get('strStatus') or 'FINISHED',
                'competition': event.get('strLeague') or str(league_id),
                'id_event': event.get('idEvent'),
                'season': event.get('strSeason') or season_label,
                # Campos adicionales disponibles en el evento base
                'jornada': event.get('intRound'),
                'espectadores': event.get('intSpectators'),
                'estadio': event.get('strVenue') or None,
                'ciudad': event.get('strCity') or None,
                'arbitro': event.get('strOfficial') or None,
                'descripcion': event.get('strDescriptionEN') or None,
                'video_highlights': event.get('strVideo') or None,
            })
        return rows

    def _get_eventsseason_rows(self, league_id: int, season_label: str) -> list:
        params = {
            'id': league_id,
            's': season_label,
        }

        data = self._get_json('eventsseason.php', params)
        events = data.get('events') or []
        return self._extract_scored_rows(events, league_id, season_label)

    def _get_events_by_round_rows(self, league_id: int, season_label: str, max_round: int = 38) -> list:
        all_rows = []
        for round_number in range(1, max_round + 1):
            params = {
                'id': league_id,
                'r': round_number,
                's': season_label,
            }

            try:
                data = self._get_json('eventsround.php', params)
            except requests.HTTPError as error:
                status_code = error.response.status_code if error.response is not None else None
                if status_code == 429:
                    # Con límites de cuota devolvemos lo recuperado hasta el momento.
                    break
                raise

            events = data.get('events') or []
            all_rows.extend(self._extract_scored_rows(events, league_id, season_label))

        # Deduplicar por fecha/equipos/marcador para evitar repetidos entre endpoints.
        seen = set()
        unique_rows = []
        for row in all_rows:
            key = (
                str(row.get('date')),
                row.get('local_team'),
                row.get('visitante_team'),
                row.get('goles_local'),
                row.get('goles_visitante'),
            )
            if key in seen:
                continue
            seen.add(key)
            unique_rows.append(row)
        return unique_rows

    def get_matches(self, competition_id: int = 2014, season: Optional[str] = None) -> pd.DataFrame:
        """
        Obtiene partidos de una competición usando TheSportsDB.

        Args:
            competition_id: ID de competición (admite IDs legacy del proyecto o idLeague de TheSportsDB)
            season: Temporada en formato YYYY o YYYY-YYYY

        Returns:
            DataFrame con estructura homogénea para el agente
        """
        league_id = self._resolve_league_id(competition_id)
        season_label = self._season_to_range(season)
        rows = []

        try:
            rows = self._get_eventsseason_rows(league_id, season_label)
        except requests.HTTPError as error:
            status_code = error.response.status_code if error.response is not None else None
            if status_code != 429:
                raise

        # Con key pública 123 evitamos expansión por jornadas para no agotar cuota.
        can_expand_rounds = self.api_key not in ('123',)
        if can_expand_rounds:
            try:
                round_rows = self._get_events_by_round_rows(league_id, season_label)
                if len(round_rows) > len(rows):
                    rows = round_rows
            except requests.HTTPError:
                pass

        df = pd.DataFrame(rows)
        if df.empty:
            return pd.DataFrame(
                columns=[
                    'date', 'local_team', 'visitante_team', 'goles_local',
                    'goles_visitante', 'status', 'competition', 'season'
                ]
            )

        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        return df

    def _fetch_event_stats(self, event_id: str) -> dict:
        """Obtiene estadísticas detalladas de un evento. Retorna {} si no hay datos."""
        for _attempt in range(2):
            try:
                data = self._get_json('lookupeventstats.php', {'id': event_id})
                break
            except requests.HTTPError as exc:
                code = exc.response.status_code if exc.response is not None else None
                if code == 429:
                    print("\n  Límite alcanzado, esperando 60s...")
                    time.sleep(60)
                    continue
                return {}
        else:
            return {}

        result = {}
        for stat in (data.get('eventstats') or []):
            stat_name = stat.get('strStat', '')
            if stat_name not in self.STAT_MAP:
                continue
            col_home, col_away = self.STAT_MAP[stat_name]
            try:
                result[col_home] = float(stat['intHome']) if stat['intHome'] is not None else None
                result[col_away] = float(stat['intAway']) if stat['intAway'] is not None else None
            except (ValueError, TypeError):
                pass
        return result

    def enrich_with_stats(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Enriquece el DataFrame con estadísticas detalladas por partido (lookupeventstats.php).
        - Solo consulta partidos sin stats previas: si shots_local ya está relleno, se salta.
        - Pausa 0.65s entre llamadas (~92 req/min, bajo el límite premium de 100/min).
        - En 429 espera 60s y reintenta.
        Funciona para cualquier volumen: 30 jornadas, 38, copas, amistosos, etc.
        """
        if 'id_event' not in df.columns:
            return df

        df = df.copy()

        has_id = df['id_event'].notna()
        needs_stats = has_id
        if 'shots_local' in df.columns:
            needs_stats = has_id & df['shots_local'].isna()

        pending = df[needs_stats].index.tolist()
        total = len(pending)

        if total == 0:
            print("Estadísticas detalladas ya en caché.")
            return df

        print(f"Enriqueciendo {total} partidos con estadísticas detalladas...")

        for i, idx in enumerate(pending, 1):
            event_id = str(int(float(df.at[idx, 'id_event'])))
            home = df.at[idx, 'local_team']
            away = df.at[idx, 'visitante_team']
            print(f"  [{i}/{total}] {home} vs {away}          ", end='\r', flush=True)

            stats = self._fetch_event_stats(event_id)
            for col, val in stats.items():
                df.at[idx, col] = val

            if i < total:
                time.sleep(0.65)

        print(f"\nEnriquecimiento completado: {total} partidos procesados.")
        return df

    def get_competitions(self) -> pd.DataFrame:
        """Obtiene ligas disponibles en TheSportsDB (solo fútbol/soccer)."""
        url = f"{self.BASE_URL}/{self.api_key}/all_leagues.php"
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        data = response.json()
        leagues = data.get('leagues') or []

        rows = []
        for league in leagues:
            sport = league.get('strSport')
            if sport and sport.lower() not in {'soccer', 'football'}:
                continue
            rows.append({
                'id': int(league.get('idLeague')) if str(league.get('idLeague', '')).isdigit() else league.get('idLeague'),
                'name': league.get('strLeague'),
                'sport': sport,
                'alternate': league.get('strLeagueAlternate'),
            })

        return pd.DataFrame(rows)


def fetch_real_matches(competition_id: int = 2014, season: str = '2023', output_path: Optional[str] = None) -> pd.DataFrame:
    """
    Función de conveniencia para obtener partidos reales y opcionalmente guardarlos.

    Args:
        competition_id: ID de la competición (legacy o idLeague de TheSportsDB)
        season: Temporada (YYYY o YYYY-YYYY)
        output_path: Si se proporciona, guarda el CSV en esta ruta

    Returns:
        DataFrame con los partidos
    """
    api = SportsDBAPI()
    df = api.get_matches(competition_id, season)

    if output_path:
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_file, index=False)
        print(f"Datos guardados en: {output_path}")

    return df


# IDs legacy soportados por compatibilidad:
# 2014: La Liga (4335 en TheSportsDB)
# 2021: Premier League (4328 en TheSportsDB)
# 2002: Bundesliga (4331 en TheSportsDB)
# 2019: Serie A (4332 en TheSportsDB)
# 2015: Ligue 1 (4334 en TheSportsDB)

# Alias para compatibilidad con código/documentación previa.
FootballDataAPI = SportsDBAPI