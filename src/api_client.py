import requests
import pandas as pd
from typing import Optional
from pathlib import Path


import requests
import pandas as pd
from typing import Optional
from pathlib import Path
import os
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()


class FootballDataAPI:
    """Cliente para la API gratuita de Football-Data.org"""

    BASE_URL = "https://api.football-data.org/v4"

    def __init__(self, api_key: Optional[str] = None):
        # Intentar obtener API key del entorno
        self.api_key = api_key or os.getenv('FOOTBALL_DATA_API_KEY')
        if not self.api_key:
            raise ValueError(
                "Se requiere una API key de Football-Data.org. "
                "Regístrate gratis en https://www.football-data.org/client/register "
                "y configura la variable de entorno FOOTBALL_DATA_API_KEY o pásala como parámetro."
            )
        self.headers = {"X-Auth-Token": self.api_key}

    def get_matches(self, competition_id: int = 2014, season: Optional[str] = None) -> pd.DataFrame:
        """
        Obtiene partidos de una competición específica.

        Args:
            competition_id: ID de la competición (2014 = La Liga, 2021 = Premier League, etc.)
            season: Temporada en formato YYYY (ej: '2023')

        Returns:
            DataFrame con los partidos
        """
        url = f"{self.BASE_URL}/competitions/{competition_id}/matches"
        params = {}
        if season:
            params['season'] = season

        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()

        data = response.json()
        matches = data.get('matches', [])

        # Convertir a DataFrame
        df_data = []
        for match in matches:
            df_data.append({
                'date': match['utcDate'],
                'local_team': match['homeTeam']['name'],
                'visitante_team': match['awayTeam']['name'],
                'goles_local': match['score']['fullTime']['home'] or 0,
                'goles_visitante': match['score']['fullTime']['away'] or 0,
                'status': match['status'],
                'competition': data['competition']['name'],
                'season': data.get('filters', {}).get('season', 'unknown')
            })

        df = pd.DataFrame(df_data)
        df['date'] = pd.to_datetime(df['date'])

        # Filtrar solo partidos terminados
        df = df[df['status'] == 'FINISHED'].copy()

        return df

    def get_competitions(self) -> pd.DataFrame:
        """Obtiene lista de competiciones disponibles"""
        url = f"{self.BASE_URL}/competitions"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()

        data = response.json()
        competitions = data.get('competitions', [])

        df_data = []
        for comp in competitions:
            df_data.append({
                'id': comp['id'],
                'name': comp['name'],
                'code': comp['code'],
                'area': comp['area']['name']
            })

        return pd.DataFrame(df_data)


def fetch_real_matches(competition_id: int = 2014, season: str = '2023', output_path: Optional[str] = None) -> pd.DataFrame:
    """
    Función de conveniencia para obtener partidos reales y opcionalmente guardarlos.

    Args:
        competition_id: ID de la competición
        season: Temporada
        output_path: Si se proporciona, guarda el CSV en esta ruta

    Returns:
        DataFrame con los partidos
    """
    try:
        api = FootballDataAPI()
        df = api.get_matches(competition_id, season)
    except ValueError as e:
        print(f"Error de configuración: {e}")
        print("Para usar datos reales, sigue estos pasos:")
        print("1. Regístrate gratis en: https://www.football-data.org/client/register")
        print("2. Obtén tu API key gratuita")
        print("3. Configura la variable de entorno: set FOOTBALL_DATA_API_KEY=tu_api_key")
        print("4. O crea un archivo .env con: FOOTBALL_DATA_API_KEY=tu_api_key")
        raise

    if output_path:
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_file, index=False)
        print(f"Datos guardados en: {output_path}")

    return df


# IDs de competiciones comunes (sin API key requerida):
# 2014: La Liga (España)
# 2021: Premier League (Inglaterra)
# 2002: Bundesliga (Alemania)
# 2019: Serie A (Italia)
# 2015: Ligue 1 (Francia)