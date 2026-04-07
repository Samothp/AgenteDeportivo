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

    # Asistencia
    asistencia_promedio = None
    asistencia_maxima = None
    partido_mas_espectadores = None
    if 'espectadores' in df and df['espectadores'].notna().any():
        asistencia_promedio = float(df['espectadores'].mean())
        asistencia_maxima = int(df['espectadores'].max())
        idx = df['espectadores'].idxmax()
        row = df.loc[idx]
        partido_mas_espectadores = f"{row['local_team']} vs {row['visitante_team']}"

    # Estadio más frecuente
    estadio_mas_frecuente = None
    if 'estadio' in df and df['estadio'].notna().any():
        estadio_mas_frecuente = df['estadio'].dropna().mode().iloc[0]

    # Árbitro más frecuente
    arbitro_mas_frecuente = None
    if 'arbitro' in df and df['arbitro'].notna().any():
        arbitro_mas_frecuente = df['arbitro'].dropna().mode().iloc[0]

    # Helper para promedios de columnas opcionales
    def _avg(col: str):
        return float(df[col].mean()) if col in df.columns and df[col].notna().any() else None

    return {
        'partidos_analizados': total_matches,
        'goles_totales': total_goals,
        'goles_promedio_por_partido': average_goals,
        'tarjetas_amarillas': total_yellow,
        'tarjetas_rojas': total_red,
        'posesion_local_promedio': average_possession_local,
        'posesion_visitante_promedio': _avg('posesion_visitante'),
        'asistencia_promedio': asistencia_promedio,
        'asistencia_maxima': asistencia_maxima,
        'partido_mas_espectadores': partido_mas_espectadores,
        'estadio_mas_frecuente': estadio_mas_frecuente,
        'arbitro_mas_frecuente': arbitro_mas_frecuente,
        # Estadísticas técnicas (disponibles con enriquecimiento via lookupeventstats)
        'tiros_local_promedio':                _avg('shots_local'),
        'tiros_visitante_promedio':            _avg('shots_visitante'),
        'tiros_a_puerta_local_promedio':       _avg('shots_on_target_local'),
        'tiros_a_puerta_visitante_promedio':   _avg('shots_on_target_visitante'),
        'corners_local_promedio':              _avg('corners_local'),
        'corners_visitante_promedio':          _avg('corners_visitante'),
        'faltas_local_promedio':               _avg('faltas_local'),
        'faltas_visitante_promedio':           _avg('faltas_visitante'),
        'fueras_de_juego_local_promedio':      _avg('fueras_de_juego_local'),
        'fueras_de_juego_visitante_promedio':  _avg('fueras_de_juego_visitante'),
        'paradas_local_promedio':              _avg('paradas_local'),
        'paradas_visitante_promedio':          _avg('paradas_visitante'),
        'pases_local_promedio':                _avg('pases_local'),
        'pases_visitante_promedio':            _avg('pases_visitante'),
        'precision_pases_local_promedio':      _avg('precision_pases_local'),
        'precision_pases_visitante_promedio':  _avg('precision_pases_visitante'),
        'xg_local_promedio':                   _avg('xg_local'),
        'xg_visitante_promedio':               _avg('xg_visitante'),
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


def compute_team_record(df: pd.DataFrame, team: str) -> Dict:
    """Calcula el historial W/D/L, puntos y racha del equipo.

    Ordena los partidos por jornada (o fecha) y determina para cada uno
    si el equipo ganó, empató o perdió, teniendo en cuenta si jugó de local
    o visitante. Devuelve:
      - victorias, empates, derrotas, puntos
      - racha_actual: string como 'VVEEDD' (últimos 5 partidos, orden cronológico)
      - tabla_resultados: lista de dicts [{jornada, rival, gf, gc, resultado}]
    """
    data = df.copy()

    # Ordenar cronológicamente
    if 'jornada' in data.columns and data['jornada'].notna().any():
        data = data.sort_values('jornada').reset_index(drop=True)
    elif 'date' in data.columns:
        data = data.sort_values('date').reset_index(drop=True)

    team_lower = team.strip().lower()
    results = []

    for _, row in data.iterrows():
        is_home = str(row.get('local_team', '')).lower().find(team_lower) >= 0
        if is_home:
            gf = row['goles_local']
            gc = row['goles_visitante']
            rival = row['visitante_team']
        else:
            gf = row['goles_visitante']
            gc = row['goles_local']
            rival = row['local_team']

        if gf > gc:
            resultado = 'V'
        elif gf == gc:
            resultado = 'E'
        else:
            resultado = 'D'

        results.append({
            'jornada': row.get('jornada'),
            'rival': rival,
            'gf': int(gf),
            'gc': int(gc),
            'local': 'Local' if is_home else 'Visitante',
            'resultado': resultado,
        })

    victorias  = sum(1 for r in results if r['resultado'] == 'V')
    empates    = sum(1 for r in results if r['resultado'] == 'E')
    derrotas   = sum(1 for r in results if r['resultado'] == 'D')
    puntos     = victorias * 3 + empates

    # Racha de los últimos 5 partidos (más reciente a la derecha)
    ultimos = results[-5:]
    racha_actual = ''.join(r['resultado'] for r in ultimos)

    return {
        'victorias': victorias,
        'empates': empates,
        'derrotas': derrotas,
        'puntos': puntos,
        'racha_actual': racha_actual,
        'tabla_resultados': results,
    }


def compute_league_comparison(team_metrics: Dict, league_metrics: Dict) -> List[Dict]:
    """Compara las métricas del equipo con las de la liga completa.

    Devuelve una lista de dicts con: metrica, equipo, liga, diferencia, signo.
    Solo incluye métricas disponibles en ambos contextos.
    """
    METRIC_LABELS = {
        'goles_promedio_por_partido':         'Goles por partido',
        'tiros_local_promedio':               'Tiros totales (local)',
        'tiros_visitante_promedio':           'Tiros totales (visitante)',
        'tiros_a_puerta_local_promedio':      'Tiros a puerta (local)',
        'tiros_a_puerta_visitante_promedio':  'Tiros a puerta (visitante)',
        'xg_local_promedio':                  'xG (local)',
        'xg_visitante_promedio':              'xG (visitante)',
        'posesion_local_promedio':            'Posesión % (local)',
        'posesion_visitante_promedio':        'Posesión % (visitante)',
        'corners_local_promedio':             'Corners (local)',
        'corners_visitante_promedio':         'Corners (visitante)',
        'faltas_local_promedio':              'Faltas (local)',
        'faltas_visitante_promedio':          'Faltas (visitante)',
        'paradas_local_promedio':             'Paradas portero (local)',
        'paradas_visitante_promedio':         'Paradas portero (visitante)',
        'precision_pases_local_promedio':     'Precisión pases % (local)',
        'precision_pases_visitante_promedio': 'Precisión pases % (visitante)',
    }
    rows = []
    for key, label in METRIC_LABELS.items():
        t_val = team_metrics.get(key)
        l_val = league_metrics.get(key)
        if t_val is None or l_val is None:
            continue
        diff = t_val - l_val
        rows.append({
            'metrica': label,
            'equipo': round(t_val, 2),
            'liga': round(l_val, 2),
            'diferencia': round(diff, 2),
            'signo': '+' if diff >= 0 else '',
        })
    return rows
