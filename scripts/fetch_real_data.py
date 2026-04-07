#!/usr/bin/env python3
"""
Script de ejemplo para obtener datos reales de competiciones.
Requiere configurar FOOTBALL_DATA_API_KEY en .env o variable de entorno.
"""

import sys
from pathlib import Path

# Añadir el directorio raíz al path para importar módulos
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from src.api_client import fetch_real_matches

def main():
    # Ejemplos de competiciones
    competitions = {
        'La Liga': 2014,
        'Premier League': 2021,
        'Bundesliga': 2002,
        'Serie A': 2019,
        'Ligue 1': 2015,
    }

    print("Obteniendo datos de La Liga 2025 (temporada actual)...")
    try:
        df = fetch_real_matches(
            competition_id=competitions['La Liga'],
            season='2025',
            output_path='data/laliga_2025.csv'
        )
        print(f"✅ Obtenidos {len(df)} partidos de La Liga 2025")
        print(f"Columnas disponibles: {list(df.columns)}")
        print(f"Primeros 5 partidos:\n{df.head()}")

    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nIntentando con temporada 2024...")
        try:
            df = fetch_real_matches(
                competition_id=competitions['La Liga'],
                season='2024',
                output_path='data/laliga_2024.csv'
            )
            print(f"✅ Obtenidos {len(df)} partidos de La Liga 2024")
            print(f"Columnas disponibles: {list(df.columns)}")
            print(f"Primeros 5 partidos:\n{df.head()}")
        except Exception as e2:
            print(f"❌ Error también con 2024: {e2}")

if __name__ == '__main__':
    main()