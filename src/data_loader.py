import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional

# Columnas obligatorias (deben estar presentes)
REQUIRED_COLUMNS = [
    'date',
    'local_team',
    'visitante_team',
    'goles_local',
    'goles_visitante',
]

# Columnas opcionales (se agregan con valores por defecto si faltan)
OPTIONAL_COLUMNS = [
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

# Todas las columnas esperadas
ALL_COLUMNS = REQUIRED_COLUMNS + OPTIONAL_COLUMNS

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


def add_missing_optional_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Agrega columnas opcionales faltantes con valores por defecto."""
    for col in OPTIONAL_COLUMNS:
        if col not in df.columns:
            if 'posesion' in col:
                df[col] = 50.0  # Valor por defecto para posesión
            elif any(keyword in col for keyword in ['amarillas', 'rojas', 'faltas', 'shots', 'corners']):
                df[col] = 0  # Valor por defecto para estadísticas numéricas
            else:
                df[col] = 0  # Valor por defecto general
    return df


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


def load_match_data(csv_path: str, fetch_real: bool = False, competition_id: Optional[int] = None, season: Optional[str] = None) -> pd.DataFrame:
    """
    Carga datos de partidos desde un archivo CSV o API real.

    Args:
        csv_path: Ruta al archivo CSV
        fetch_real: Si True, intenta obtener datos reales de la API
        competition_id: ID de competición para datos reales
        season: Temporada para datos reales

    Returns:
        DataFrame con los datos preparados
    """
    path = Path(csv_path)

    if fetch_real or not path.exists():
        if fetch_real:
            print("Obteniendo datos reales de la API...")
            from .api_client import fetch_real_matches
            df = fetch_real_matches(competition_id or 2014, season or '2023')
            # Guardar para uso futuro
            path.parent.mkdir(parents=True, exist_ok=True)
            df.to_csv(path, index=False)
            print(f"Datos guardados en: {csv_path}")
        else:
            raise FileNotFoundError(f'No se encontró el archivo: {csv_path}. Usa fetch_real=True para obtener datos reales.')
    else:
        print(f"Cargando datos desde: {csv_path}")
        df = pd.read_csv(path)

    df = normalize_column_names(df)
    validate_match_data(df)
    df = add_missing_optional_columns(df)  # Agregar columnas opcionales faltantes
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    df = normalize_numeric_columns(df)
    df = add_derived_metrics(df)
    return df