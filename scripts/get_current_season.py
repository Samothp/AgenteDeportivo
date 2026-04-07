#!/usr/bin/env python3
"""
Actualiza la DB local de La Liga para la temporada actual (2025).

Atajo equivalente a:
    python scripts/fetch_real_data.py 2014 2025

Para generar informes completos usa el CLI principal:
    python -m src.run_agent --fetch-real --competition 2014 --season 2025 --team <Equipo> ...
"""

import sys
from pathlib import Path

root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from src.data_loader import get_db_path, load_match_data


def main():
    competition_id = 2014  # La Liga
    season = '2025'

    db_path = get_db_path(competition_id, season)
    print(f"Actualizando DB de La Liga {season}")
    print(f"Destino: {db_path}")

    df = load_match_data('data/matches.csv', fetch_real=True, competition_id=competition_id, season=season)
    print(f"DB actualizada: {len(df)} partidos en {db_path}")


if __name__ == '__main__':
    main()
