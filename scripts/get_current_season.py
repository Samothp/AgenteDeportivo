#!/usr/bin/env python3
"""
Script para obtener datos de La Liga de la temporada actual.
"""

import sys
from pathlib import Path

# Añadir el directorio raíz al path para importar módulos
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from src.api_client import fetch_real_matches

def main():
    print("🏆 Obteniendo datos de La Liga - Temporada Actual (2025) 🏆")
    print("=" * 60)

    try:
        df = fetch_real_matches(
            competition_id=2014,  # La Liga
            season='2025',
            output_path='data/laliga_actual.csv'
        )

        print(f"✅ Éxito: {len(df)} partidos obtenidos")
        print(f"📊 Goles totales: {df['goles_local'].sum() + df['goles_visitante'].sum()}")
        print(f"📈 Promedio de goles por partido: {(df['goles_local'] + df['goles_visitante']).mean():.2f}")
        print(f"💾 Datos guardados en: data/laliga_actual.csv")

        # Mostrar algunos partidos recientes
        print("\n📅 Últimos 5 partidos:")
        recent_matches = df.sort_values('date', ascending=False).head(5)
        for _, match in recent_matches.iterrows():
            date_str = str(match['date'])[:10] if hasattr(match['date'], '__getitem__') else str(match['date']).split()[0]
            print(f"  {date_str}: {match['local_team']} {match['goles_local']} - {match['goles_visitante']} {match['visitante_team']}")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == '__main__':
    main()