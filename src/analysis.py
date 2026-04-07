from typing import Dict, List
import pandas as pd


def compute_overall_metrics(df: pd.DataFrame) -> Dict[str, object]:
    total_matches = len(df)
    total_goals = int(df['goles_totales'].sum())
    average_goals = float(df['goles_totales'].mean())

    yellow_available = (
        'amarillas_local' in df and
        'amarillas_visitante' in df and
        df[['amarillas_local', 'amarillas_visitante']].notna().any().any()
    )
    total_yellow = int(df['amarillas_local'].sum(skipna=True) + df['amarillas_visitante'].sum(skipna=True)) if yellow_available else None

    red_available = (
        'rojas_local' in df and
        'rojas_visitante' in df and
        df[['rojas_local', 'rojas_visitante']].notna().any().any()
    )
    total_red = int(df['rojas_local'].sum(skipna=True) + df['rojas_visitante'].sum(skipna=True)) if red_available else None

    average_possession_local = None
    if 'posesion_local' in df and df['posesion_local'].notna().any():
        average_possession_local = float(df['posesion_local'].mean())

    return {
        'partidos_analizados': total_matches,
        'goles_totales': total_goals,
        'goles_promedio_por_partido': average_goals,
        'tarjetas_amarillas': total_yellow,
        'tarjetas_rojas': total_red,
        'posesion_local_promedio': average_possession_local,
    }


def top_scoring_teams(df: pd.DataFrame, n: int = 5) -> pd.DataFrame:
    local_goals = df.groupby('local_team')['goles_local'].sum()
    visitante_goals = df.groupby('visitante_team')['goles_visitante'].sum()
    total_goals = local_goals.add(visitante_goals, fill_value=0).sort_values(ascending=False)

    return total_goals.head(n).reset_index(name='goles_anotados')


def top_defensive_teams(df: pd.DataFrame, n: int = 5) -> pd.DataFrame:
    local_conceded = df.groupby('local_team')['goles_visitante'].sum()
    visitante_conceded = df.groupby('visitante_team')['goles_local'].sum()
    total_conceded = local_conceded.add(visitante_conceded, fill_value=0).sort_values()

    return total_conceded.head(n).reset_index(name='goles_concedidos')


def match_highlights(df: pd.DataFrame, n: int = 5) -> pd.DataFrame:
    highlights = df.copy()
    highlights['margen_victoria'] = (highlights['goles_local'] - highlights['goles_visitante']).abs()
    return highlights.sort_values(['goles_totales', 'margen_victoria'], ascending=[False, False]).head(n)
