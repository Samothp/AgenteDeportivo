import pandas as pd
from pathlib import Path
from typing import Dict, List

REQUIRED_COLUMNS = [
    'date',
    'local_team',
    'visitante_team',
    'goles_local',
    'goles_visitante',
    'posesion_local',
    'posesion_visitante',
    'shots_local',
    'shots_visitante',
    'shots_on_target_local',
    'shots_on_target_visitante',
    'corners_local',
    'corners_visitante',
    'amarillas_local',
    'amarillas_visitante',
    'rojas_local',
    'rojas_visitante',
    'faltas_local',
    'faltas_visitante',
]

COLUMN_ALIASES: Dict[str, str] = {
    'equipo_local': 'local_team',
    'equipo_visitante': 'visitante_team',
    'goles_locales': 'goles_local',
    'goles_visitantes': 'goles_visitante',
    'posesion_local': 'posesion_local',
    'posesion_visitante': 'posesion_visitante',
    'tiros_local': 'shots_local',
    'tiros_visitante': 'shots_visitante',
    'tiros_a_puerta_local': 'shots_on_target_local',
    'tiros_a_puerta_visitante': 'shots_on_target_visitante',
    'corners_local': 'corners_local',
    'corners_visitante': 'corners_visitante',
    'amarillas_local': 'amarillas_local',
    'amarillas_visitante': 'amarillas_visitante',
    'rojas_local': 'rojas_local',
    'rojas_visitante': 'rojas_visitante',
    'faltas_local': 'faltas_local',
    'faltas_visitante': 'faltas_visitante',
}

INTEGER_COLUMNS = [
    'goles_local',
    'goles_visitante',
    'shots_local',
    'shots_visitante',
    'shots_on_target_local',
    'shots_on_target_visitante',
    'corners_local',
    'corners_visitante',
    'amarillas_local',
    'amarillas_visitante',
    'rojas_local',
    'rojas_visitante',
    'faltas_local',
    'faltas_visitante',
]

PERCENT_COLUMNS = ['posesion_local', 'posesion_visitante']


def normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    mapping = {}
    for column in df.columns:
        normalized = column.strip().lower().replace(' ', '_')
        mapping[column] = COLUMN_ALIASES.get(normalized, normalized)
    return df.rename(columns=mapping)


def validate_match_data(df: pd.DataFrame) -> None:
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f'Faltan columnas obligatorias en el dataset: {missing}')


def normalize_numeric_columns(df: pd.DataFrame) -> pd.DataFrame:
    for column in INTEGER_COLUMNS:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors='coerce').fillna(0).astype(int)

    for column in PERCENT_COLUMNS:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors='coerce').fillna(0.0).astype(float)

    return df


def add_derived_metrics(df: pd.DataFrame) -> pd.DataFrame:
    df['goles_totales'] = df['goles_local'] + df['goles_visitante']
    df['diferencia_goles'] = (df['goles_local'] - df['goles_visitante']).abs()
    df['resultado_local'] = df.apply(
        lambda row: 'Victoria' if row['goles_local'] > row['goles_visitante'] else 'Empate' if row['goles_local'] == row['goles_visitante'] else 'Derrota',
        axis=1,
    )
    df['resultado_visitante'] = df.apply(
        lambda row: 'Victoria' if row['goles_visitante'] > row['goles_local'] else 'Empate' if row['goles_visitante'] == row['goles_local'] else 'Derrota',
        axis=1,
    )
    return df


def load_match_data(csv_path: str) -> pd.DataFrame:
    """Carga y prepara datos de partidos desde un archivo CSV."""
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f'No se encontró el archivo: {csv_path}')

    df = pd.read_csv(path)
    df = normalize_column_names(df)
    validate_match_data(df)
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    df = normalize_numeric_columns(df)
    df = add_derived_metrics(df)
    return df
