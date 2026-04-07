import os
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
                'season': event.get('strSeason') or season_label,
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