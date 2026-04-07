#!/usr/bin/env python3
"""
Actualiza la DB local para una competición y temporada concretas.

Uso:
    python scripts/fetch_real_data.py [competition_id] [season]

Ejemplos:
    python scripts/fetch_real_data.py          # La Liga 2025 (por defecto)
    python scripts/fetch_real_data.py 2014 2024
    python scripts/fetch_real_data.py 2021 2025  # Premier League

IDs de competición frecuentes:
    2014 = La Liga
    2021 = Premier League
    2002 = Bundesliga
    2019 = Serie A
    2015 = Ligue 1

Para generar informes completos usa el CLI principal:
    python -m src.run_agent --fetch-real --competition 2014 --season 2025 --team Mallorca ...
"""

import sys
from pathlib import Path

root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from src.data_loader import get_db_path, load_match_data


def main():
    competition_id = int(sys.argv[1]) if len(sys.argv) > 1 else 2014
    season = sys.argv[2] if len(sys.argv) > 2 else '2025'

    db_path = get_db_path(competition_id, season)
    print(f"Actualizando DB: competition={competition_id}, season={season}")
    print(f"Destino: {db_path}")

    df = load_match_data('data/matches.csv', fetch_real=True, competition_id=competition_id, season=season)
    print(f"DB actualizada: {len(df)} partidos en {db_path}")


if __name__ == '__main__':
    main()
