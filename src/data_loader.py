import pandas as pd
from pathlib import Path


def load_match_data(csv_path: str) -> pd.DataFrame:
    """Carga datos de partidos desde un archivo CSV."""
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"No se encontró el archivo: {csv_path}")

    df = pd.read_csv(path)
    return df


def summarize_matches(df: pd.DataFrame) -> pd.DataFrame:
    """Genera un resumen básico de los datos de partidos."""
    summary = {
        'partidos': len(df),
        'goles_totales': int(df.get('goles_local', 0).sum() + df.get('goles_visitante', 0).sum()),
        'promedio_goles': float((df.get('goles_local', 0) + df.get('goles_visitante', 0)).mean()),
        'tarjetas_amarillas': int(df.get('amarillas_local', 0).sum() + df.get('amarillas_visitante', 0).sum()),
        'tarjetas_rojas': int(df.get('rojas_local', 0).sum() + df.get('rojas_visitante', 0).sum()),
    }
    return pd.DataFrame([summary])
