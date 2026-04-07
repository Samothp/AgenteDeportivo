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
    'shots_off_target_local',
    'shots_off_target_visitante',
    'shots_blocked_local',
    'shots_blocked_visitante',
    'shots_inside_box_local',
    'shots_inside_box_visitante',
    'shots_outside_box_local',
    'shots_outside_box_visitante',
    'corners_local',
    'corners_visitante',
    'fueras_de_juego_local',
    'fueras_de_juego_visitante',
    'amarillas_local',
    'amarillas_visitante',
    'rojas_local',
    'rojas_visitante',
    'faltas_local',
    'faltas_visitante',
    'paradas_local',
    'paradas_visitante',
    'pases_local',
    'pases_visitante',
    'pases_precisos_local',
    'pases_precisos_visitante',
    'precision_pases_local',
    'precision_pases_visitante',
    'xg_local',
    'xg_visitante',
    # Campos del evento base
    'id_event',
    'jornada',
    'espectadores',
    'estadio',
    'ciudad',
    'arbitro',
    'descripcion',
    'video_highlights',
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
    'shots_off_target_local',
    'shots_off_target_visitante',
    'shots_blocked_local',
    'shots_blocked_visitante',
    'shots_inside_box_local',
    'shots_inside_box_visitante',
    'shots_outside_box_local',
    'shots_outside_box_visitante',
    'corners_local',
    'corners_visitante',
    'fueras_de_juego_local',
    'fueras_de_juego_visitante',
    'amarillas_local',
    'amarillas_visitante',
    'rojas_local',
    'rojas_visitante',
    'faltas_local',
    'faltas_visitante',
    'paradas_local',
    'paradas_visitante',
    'pases_local',
    'pases_visitante',
    'pases_precisos_local',
    'pases_precisos_visitante',
    'jornada',
    'espectadores',
]

PERCENT_COLUMNS = [
    'posesion_local',
    'posesion_visitante',
    'precision_pases_local',
    'precision_pases_visitante',
    'xg_local',
    'xg_visitante',
]


def get_db_path(competition_id: int, season: str) -> Path:
    """Retorna la ruta de la base de datos local para una competition+season concreta.

    Ejemplo: competition_id=2014, season='2025' → data/db_2014_2025.csv
    """
    season_norm = str(season).split('-')[0]  # '2025-2026' → '2025'
    return Path(f"data/db_{competition_id}_{season_norm}.csv")


def list_available_teams(competition_id: int, season: str) -> List[str]:
    """Devuelve la lista ordenada de equipos presentes en la DB local.

    Retorna lista vacía si la DB no existe todavía.
    """
    db_path = get_db_path(competition_id, season)
    if not db_path.exists():
        return []
    df = pd.read_csv(db_path, usecols=['local_team', 'visitante_team'])
    teams = pd.concat([df['local_team'], df['visitante_team']]).dropna().unique()
    return sorted(teams.tolist())


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
    """Agrega columnas opcionales faltantes como valores nulos cuando no están disponibles."""
    for col in OPTIONAL_COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA
    return df


def normalize_numeric_columns(df: pd.DataFrame) -> pd.DataFrame:
    for column in INTEGER_COLUMNS:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors='coerce')

    for column in PERCENT_COLUMNS:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors='coerce')

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

    # Cuando se especifica competition+season, usar una DB dedicada por liga y temporada.
    # Esto permite mantener bases de datos separadas y actualizarlas incrementalmente.
    if competition_id and season:
        db_path = get_db_path(competition_id, season)
    else:
        db_path = path

    if fetch_real:
        from .api_client import SportsDBAPI, fetch_real_matches

        # 1. Cargar DB existente (puede estar vacía en el primer uso)
        df_db = pd.read_csv(db_path) if db_path.exists() else pd.DataFrame()

        # 2. Obtener todos los partidos jugados de la temporada (datos base, sin stats)
        print("Consultando partidos de la temporada en la API...")
        _api_failed = False
        try:
            df_api = fetch_real_matches(competition_id or 2014, season or '2023')
        except Exception as exc:
            if not df_db.empty:
                print(f"Error al contactar la API ({exc.__class__.__name__}). Usando DB local.")
                df = df_db
                _api_failed = True
            else:
                raise

        if _api_failed:
            pass  # df ya asignado arriba
        elif df_api.empty:
            if not df_db.empty:
                print("La API devolvió 0 partidos. Usando DB local.")
                df = df_db
            else:
                raise ValueError(
                    "La API devolvió 0 partidos y no hay DB local. "
                    "Puede ser un límite de cuota; intenta de nuevo."
                )
        else:
            # 3. Determinar qué partidos ya tienen stats completas en la DB
            if not df_db.empty and 'id_event' in df_db.columns:
                if 'shots_local' in df_db.columns:
                    # Solo se consideran "con stats" los que tienen shots_local relleno
                    enriched_ids = set(
                        df_db.loc[df_db['shots_local'].notna(), 'id_event'].astype(str)
                    )
                else:
                    enriched_ids = set(df_db['id_event'].astype(str))
            else:
                enriched_ids = set()

            df_to_enrich = df_api[
                ~df_api['id_event'].astype(str).isin(enriched_ids)
            ].copy()

            print(
                f"DB local: {len(enriched_ids)} partidos con stats. "
                f"Nuevos/pendientes: {len(df_to_enrich)}."
            )

            if not df_to_enrich.empty:
                # 4. Enriquecer solo los partidos nuevos o que aún no tienen stats
                print(f"Enriqueciendo {len(df_to_enrich)} partidos con estadísticas detalladas...")
                api = SportsDBAPI()
                df_enriched = api.enrich_with_stats(df_to_enrich)

                # 5. Fusionar en DB: sustituir filas sin stats + añadir nuevas
                if not df_db.empty and 'id_event' in df_db.columns:
                    updated_ids = set(df_enriched['id_event'].astype(str))
                    df_db = df_db[~df_db['id_event'].astype(str).isin(updated_ids)]
                    df_db = pd.concat([df_db, df_enriched], ignore_index=True)
                else:
                    df_db = df_enriched

                db_path.parent.mkdir(parents=True, exist_ok=True)
                df_db.to_csv(db_path, index=False)
                print(f"DB guardada en: {db_path} ({len(df_db)} partidos totales)")
            else:
                print("La DB ya está al día, no hay partidos nuevos ni pendientes.")

            df = df_db

    elif db_path.exists():
        print(f"Cargando datos desde: {db_path}")
        df = pd.read_csv(db_path)
    elif path.exists():
        print(f"Cargando datos desde: {csv_path}")
        df = pd.read_csv(path)
    else:
        raise FileNotFoundError(
            f"No se encontró la base de datos. "
            f"Usa --fetch-real para descargar y construir la DB local."
        )

    df = normalize_column_names(df)
    validate_match_data(df)

    present_optional_columns = [col for col in OPTIONAL_COLUMNS if col in df.columns]
    df.attrs['available_optional_columns'] = present_optional_columns

    df = add_missing_optional_columns(df)  # Agregar columnas opcionales faltantes
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    df = normalize_numeric_columns(df)
    df = add_derived_metrics(df)
    return df