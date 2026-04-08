from typing import Dict, List, Optional
import numpy as np
import pandas as pd


def compute_overall_metrics(df: pd.DataFrame, team: Optional[str] = None) -> Dict[str, object]:
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

    # Perspectiva del equipo: goles a favor/en contra y tarjetas propias
    goles_a_favor = None
    goles_en_contra = None
    goles_a_favor_promedio = None
    goles_concedidos_promedio = None
    tarjetas_amarillas_equipo = None
    tarjetas_rojas_equipo = None
    team_tech: Dict[str, float] = {}
    if team:
        team_lower = team.strip().lower()
        is_home = df['local_team'].str.lower().str.contains(team_lower, na=False)
        gf = df['goles_local'].where(is_home, df['goles_visitante']).astype(float)
        gc = df['goles_visitante'].where(is_home, df['goles_local']).astype(float)
        goles_a_favor = int(gf.sum())
        goles_en_contra = int(gc.sum())
        goles_a_favor_promedio = float(gf.mean())
        goles_concedidos_promedio = float(gc.mean())
        if yellow_available:
            am_eq = df['amarillas_local'].where(is_home, df['amarillas_visitante'])
            tarjetas_amarillas_equipo = int(am_eq.sum(skipna=True))
        if red_available:
            ro_eq = df['rojas_local'].where(is_home, df['rojas_visitante'])
            tarjetas_rojas_equipo = int(ro_eq.sum(skipna=True))

        # Estadísticas técnicas desde la perspectiva del equipo
        TECH_PAIRS = [
            ('shots_local',              'shots_visitante',              'tiros'),
            ('shots_on_target_local',    'shots_on_target_visitante',    'tiros_a_puerta'),
            ('corners_local',            'corners_visitante',            'corners'),
            ('faltas_local',             'faltas_visitante',             'faltas'),
            ('fueras_de_juego_local',    'fueras_de_juego_visitante',    'fueras_de_juego'),
            ('paradas_local',            'paradas_visitante',            'paradas'),
            ('precision_pases_local',    'precision_pases_visitante',    'precision_pases'),
            ('xg_local',                 'xg_visitante',                 'xg'),
            ('posesion_local',           'posesion_visitante',           'posesion'),
        ]
        team_tech: Dict[str, float] = {}
        for col_h, col_a, prefix in TECH_PAIRS:
            if col_h in df.columns and col_a in df.columns:
                eq = df[col_h].where(is_home, df[col_a]).astype(float)
                rv = df[col_a].where(is_home, df[col_h]).astype(float)
                # Total combinado
                if eq.notna().any():
                    team_tech[f'{prefix}_equipo_promedio'] = float(eq.mean())
                if rv.notna().any():
                    team_tech[f'{prefix}_rival_promedio'] = float(rv.mean())
                # Desglose local vs visitante
                eq_home  = df.loc[is_home,  col_h].astype(float)
                eq_away  = df.loc[~is_home, col_a].astype(float)
                rv_home  = df.loc[is_home,  col_a].astype(float)
                rv_away  = df.loc[~is_home, col_h].astype(float)
                if eq_home.notna().any():
                    team_tech[f'{prefix}_equipo_local_promedio']     = float(eq_home.mean())
                if eq_away.notna().any():
                    team_tech[f'{prefix}_equipo_visitante_promedio'] = float(eq_away.mean())
                if rv_home.notna().any():
                    team_tech[f'{prefix}_rival_local_promedio']      = float(rv_home.mean())
                if rv_away.notna().any():
                    team_tech[f'{prefix}_rival_visitante_promedio']  = float(rv_away.mean())

    # Media de goles por equipo por partido en la liga (para comparativa)
    goles_por_equipo_promedio = float(df['goles_totales'].mean()) / 2.0 if total_matches > 0 else None

    # Medias de liga por equipo para cada stat técnica (promedio local + visitante / 2)
    TECH_PAIRS_LIGA = [
        ('shots_local',              'shots_visitante',              'tiros'),
        ('shots_on_target_local',    'shots_on_target_visitante',    'tiros_a_puerta'),
        ('corners_local',            'corners_visitante',            'corners'),
        ('faltas_local',             'faltas_visitante',             'faltas'),
        ('fueras_de_juego_local',    'fueras_de_juego_visitante',    'fueras_de_juego'),
        ('paradas_local',            'paradas_visitante',            'paradas'),
        ('precision_pases_local',    'precision_pases_visitante',    'precision_pases'),
        ('xg_local',                 'xg_visitante',                 'xg'),
        ('posesion_local',           'posesion_visitante',           'posesion'),
    ]
    liga_tech: Dict[str, float] = {}
    for col_h, col_a, prefix in TECH_PAIRS_LIGA:
        h_avg = _avg(col_h)
        a_avg = _avg(col_a)
        if h_avg is not None and a_avg is not None:
            liga_tech[f'{prefix}_liga_promedio'] = (h_avg + a_avg) / 2.0

    # Eficiencia ofensiva: ratio goles reales / xG esperados
    overperformance = None
    overperformance_desc = None
    if team and goles_a_favor is not None:
        xg_prom = team_tech.get('xg_equipo_promedio')
        if xg_prom is not None and xg_prom > 0 and total_matches > 0:
            total_xg = xg_prom * total_matches
            overperformance = round(goles_a_favor / total_xg, 2)
            if overperformance > 1.2:
                overperformance_desc = 'sobrerendimiento (convierte más de lo esperado)'
            elif overperformance < 0.8:
                overperformance_desc = 'infrarendimiento (convierte menos de lo esperado)'
            else:
                overperformance_desc = 'rendimiento esperado'

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
        # Perspectiva del equipo (sólo cuando se filtra por equipo)
        'goles_a_favor':               goles_a_favor,
        'goles_en_contra':             goles_en_contra,
        'goles_a_favor_promedio':      goles_a_favor_promedio,
        'goles_concedidos_promedio':   goles_concedidos_promedio,
        'tarjetas_amarillas_equipo':   tarjetas_amarillas_equipo,
        'tarjetas_rojas_equipo':       tarjetas_rojas_equipo,
        # stats técnicas perspectiva equipo (sólo con filtro de equipo)
        **team_tech,
        # Eficiencia ofensiva
        'overperformance':      overperformance,
        'overperformance_desc': overperformance_desc,
        # Referencia de liga para comparativa
        'goles_por_equipo_promedio':   goles_por_equipo_promedio,
        **liga_tech,
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


def _max_streak(results: list, condition_fn) -> int:
    """Calcula la racha máxima consecutiva de partidos que cumplen condition_fn(r)."""
    max_streak = current = 0
    for r in results:
        if condition_fn(r):
            current += 1
            max_streak = max(max_streak, current)
        else:
            current = 0
    return max_streak


def compute_team_record(df: pd.DataFrame, team: str) -> Dict:
    """Calcula el historial W/D/L, puntos y rachas del equipo.

    Ordena los partidos por jornada (o fecha) y determina para cada uno
    si el equipo ganó, empató o perdió, teniendo en cuenta si jugó de local
    o visitante. Devuelve:
      - victorias, empates, derrotas, puntos
      - racha_actual: string como 'VVEEDD' (últimos 5 partidos, orden cronológico)
      - racha_sin_perder_max: racha consecutiva más larga sin derrota (V o E)
      - racha_goleadora_max: racha consecutiva más larga marcando al menos 1 gol
      - racha_sin_marcar_max: racha consecutiva más larga sin marcar ningún gol
      - tabla_resultados: lista de dicts [{jornada, rival, gf, gc, resultado}]
    """
    data = df.copy()

    # Ordenar cronológicamente (en multi-temporada, primero por season)
    has_season = 'season' in data.columns and data['season'].notna().any()
    has_jornada = 'jornada' in data.columns and data['jornada'].notna().any()
    if has_season and has_jornada:
        data = data.sort_values(['season', 'jornada']).reset_index(drop=True)
    elif has_jornada:
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
            'season': row.get('season'),
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

    # Rachas máximas históricas
    racha_sin_perder_max = _max_streak(results, lambda r: r['resultado'] in ('V', 'E'))
    racha_goleadora_max  = _max_streak(results, lambda r: r['gf'] > 0)
    racha_sin_marcar_max = _max_streak(results, lambda r: r['gf'] == 0)

    return {
        'victorias': victorias,
        'empates': empates,
        'derrotas': derrotas,
        'puntos': puntos,
        'racha_actual': racha_actual,
        'racha_sin_perder_max': racha_sin_perder_max,
        'racha_goleadora_max': racha_goleadora_max,
        'racha_sin_marcar_max': racha_sin_marcar_max,
        'tabla_resultados': results,
    }


def compute_team_percentiles(team: str, df_full: pd.DataFrame) -> List[Dict]:
    """Calcula el percentil del equipo en cada métrica clave respecto al resto de la liga.

    Para cada equipo de la liga calcula el valor promedio de:
    goles a favor, goles en contra, xG, tiros, posesión y overperformance.
    Luego indica en qué percentil está el equipo analizado.

    Para métricas donde menos es mejor (goles en contra, faltas) el percentil
    se invierte: percentil 90 = mejor que el 90% de la liga en esa métrica.

    Returns:
        Lista de dicts con: metrica, valor, percentil, n_equipos, lower_is_better.
    """
    if df_full.empty:
        return []

    teams = sorted(
        set(df_full['local_team'].dropna().unique()) |
        set(df_full['visitante_team'].dropna().unique())
    )
    n = len(teams)
    if n < 2:
        return []

    team_lower = team.strip().lower()

    def _team_stats(t: str) -> Dict:
        df_l = df_full[df_full['local_team'] == t]
        df_v = df_full[df_full['visitante_team'] == t]
        pj_l = len(df_l)
        pj_v = len(df_v)
        pj = pj_l + pj_v
        if pj == 0:
            return {}

        gf = float(df_l['goles_local'].sum() + df_v['goles_visitante'].sum())
        gc = float(df_l['goles_visitante'].sum() + df_v['goles_local'].sum())

        def _wavg(col_l: str, col_v: str) -> Optional[float]:
            if col_l not in df_full.columns:
                return None
            vals_l = df_l[col_l].dropna()
            vals_v = df_v[col_v].dropna() if col_v in df_full.columns else pd.Series([], dtype=float)
            total = len(vals_l) + len(vals_v)
            if total == 0:
                return None
            return float((vals_l.sum() + vals_v.sum()) / total)

        xg   = _wavg('xg_local', 'xg_visitante')
        shots = _wavg('shots_local', 'shots_visitante')
        pos  = _wavg('posesion_local', 'posesion_visitante')

        gf_pp = gf / pj
        gc_pp = gc / pj
        over = round(gf / (xg * pj), 2) if xg and xg > 0 else None

        return {
            'gf_pp':  gf_pp,
            'gc_pp':  gc_pp,
            'xg':     xg,
            'shots':  shots,
            'pos':    pos,
            'over':   over,
        }

    # Construir tabla con stats de todos los equipos
    all_stats: Dict[str, Dict] = {}
    target_name = None
    for t in teams:
        s = _team_stats(t)
        if not s:
            continue
        all_stats[t] = s
        if t.lower().find(team_lower) >= 0 or team_lower in t.lower():
            target_name = t

    if target_name is None or target_name not in all_stats:
        return []

    target = all_stats[target_name]

    def _percentile(metric: str, lower_is_better: bool) -> Optional[int]:
        values = [v[metric] for v in all_stats.values() if v.get(metric) is not None]
        my_val = target.get(metric)
        if my_val is None or len(values) < 2:
            return None
        arr = np.array(values, dtype=float)
        if lower_is_better:
            pct = int(round((np.sum(arr >= my_val) / len(arr)) * 100))
        else:
            pct = int(round((np.sum(arr <= my_val) / len(arr)) * 100))
        return max(1, min(99, pct))

    METRICS = [
        ('gf_pp',  'Goles a favor / partido',  False),
        ('gc_pp',  'Goles en contra / partido', True),
        ('xg',     'xG propio (prom.)',          False),
        ('shots',  'Tiros propios (prom.)',       False),
        ('pos',    'Posesión % (prom.)',          False),
        ('over',   'Eficiencia (goles/xG)',       False),
    ]

    result = []
    for key, label, lib in METRICS:
        val = target.get(key)
        pct = _percentile(key, lib)
        if val is None or pct is None:
            continue
        result.append({
            'metrica':         label,
            'valor':           round(val, 2),
            'percentil':       pct,
            'n_equipos':       n,
            'lower_is_better': lib,
        })
    return result


def compute_league_comparison(team_metrics: Dict, league_metrics: Dict) -> List[Dict]:
    """Compara las métricas del equipo con las de la liga completa.

    Devuelve una lista de dicts con: metrica, equipo, liga, diferencia, signo.
    Solo incluye métricas disponibles en ambos contextos.
    """
    rows: List[Dict] = []

    def _row(label: str, t_val: float, l_val: float) -> Dict:
        diff = t_val - l_val
        return {'metrica': label, 'equipo': round(t_val, 2), 'liga': round(l_val, 2),
                'diferencia': round(diff, 2), 'signo': '+' if diff >= 0 else ''}

    # Goles desde la perspectiva del equipo vs media de la liga por equipo
    liga_goles_ref = league_metrics.get('goles_por_equipo_promedio')
    if team_metrics.get('goles_a_favor_promedio') is not None and liga_goles_ref is not None:
        rows.append(_row('Goles a favor por partido', team_metrics['goles_a_favor_promedio'], liga_goles_ref))
    if team_metrics.get('goles_concedidos_promedio') is not None and liga_goles_ref is not None:
        rows.append(_row('Goles en contra por partido', team_metrics['goles_concedidos_promedio'], liga_goles_ref))

    # Stats técnicas desde perspectiva del equipo vs referencia de liga
    TEAM_TECH_LABELS = {
        'tiros':           'Tiros propios (prom.)',
        'tiros_a_puerta':  'Tiros a puerta propios (prom.)',
        'xg':              'xG propio (prom.)',
        'posesion':        'Posesión propia % (prom.)',
        'corners':         'Corners propios (prom.)',
        'faltas':          'Faltas propias (prom.)',
        'paradas':         'Paradas portero propio (prom.)',
        'precision_pases': 'Precisión pases propia % (prom.)',
    }
    for prefix, label in TEAM_TECH_LABELS.items():
        t_val = team_metrics.get(f'{prefix}_equipo_promedio')
        l_val = league_metrics.get(f'{prefix}_liga_promedio')
        if t_val is not None and l_val is not None:
            rows.append(_row(label, t_val, l_val))

    METRIC_LABELS = {
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
    # Solo incluir métricas local/visitante si no hay perspectiva de equipo (informe sin filtro)
    if not any(team_metrics.get(f'{p}_equipo_promedio') for p in ['tiros', 'xg', 'posesion']):
        for key, label in METRIC_LABELS.items():
            t_val = team_metrics.get(key)
            l_val = league_metrics.get(key)
            if t_val is None or l_val is None:
                continue
            rows.append(_row(label, t_val, l_val))
    return rows


_POS_ES = {
    'F':  'Delantero',
    'M':  'Centrocampista',
    'D':  'Defensa',
    'G':  'Portero',
    'GK': 'Portero',
    'FW': 'Delantero',
    'MF': 'Centrocampista',
    'DF': 'Defensa',
}


def compute_player_rankings(df_players: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    """Genera rankings de jugadores a partir del DataFrame de stats.

    Args:
        df_players: DataFrame de load_player_stats() con columnas
                    player_name, goals, assists, yellow_cards, red_cards,
                    appearances, shots_on_target, goals_assists, position.

    Returns:
        Dict con claves:
          'goleadores'   -> top jugadores por goles (desc)
          'asistentes'   -> top jugadores por asistencias (desc)
          'combinado'    -> top jugadores por goles+asistencias (desc)
        Cada DataFrame tiene columnas: Jugador, Posicion, PJ, Goles, Asistencias, G+A
        Solo incluye jugadores con al menos 1 aportacion relevante.
    """
    if df_players.empty:
        empty = pd.DataFrame(columns=['Jugador', 'Posicion', 'PJ', 'Goles', 'Asistencias', 'G+A'])
        return {'goleadores': empty, 'asistentes': empty, 'combinado': empty}

    def _translate_pos(pos: str) -> str:
        return _POS_ES.get(str(pos).strip().upper(), str(pos))

    def _fmt(df: pd.DataFrame, sort_col: str, min_val: int = 1) -> pd.DataFrame:
        sub = df[df[sort_col] >= min_val].copy()
        sub = sub.sort_values([sort_col, 'goals_assists'], ascending=[False, False])
        out = pd.DataFrame({
            'Jugador':     sub['player_name'].values,
            'Posicion':    [_translate_pos(p) for p in sub['position'].values],
            'PJ':          sub['appearances'].values,
            'Goles':       sub['goals'].values,
            'Asistencias': sub['assists'].values,
            'G+A':         sub['goals_assists'].values,
        })
        return out.reset_index(drop=True)

    return {
        'goleadores': _fmt(df_players, 'goals', min_val=1),
        'asistentes': _fmt(df_players, 'assists', min_val=1),
        'combinado':  _fmt(df_players, 'goals_assists', min_val=1),
    }


def compute_standings(df: pd.DataFrame, up_to_jornada: Optional[int] = None) -> pd.DataFrame:
    """Tabla de clasificación calculada desde la DB de partidos.

    Args:
        df: DataFrame completo de partidos (toda la liga).
        up_to_jornada: Si se indica, solo incluye partidos con jornada <= N.

    Returns:
        DataFrame con columnas: Pos, Equipo, PJ, G, E, P, GF, GC, DIF, PTS
        Ordenado por PTS desc, DIF desc, GF desc.
    """
    data = df.copy()
    if up_to_jornada is not None and 'jornada' in data.columns:
        data = data[data['jornada'] <= up_to_jornada]

    teams = sorted(
        set(data['local_team'].dropna().unique()) |
        set(data['visitante_team'].dropna().unique())
    )
    rows = []
    for team in teams:
        home = data[data['local_team'] == team]
        away = data[data['visitante_team'] == team]
        pj = len(home) + len(away)
        if pj == 0:
            continue
        gf = int(home['goles_local'].sum()) + int(away['goles_visitante'].sum())
        gc = int(home['goles_visitante'].sum()) + int(away['goles_local'].sum())
        g  = int((home['goles_local'] > home['goles_visitante']).sum()) + \
             int((away['goles_visitante'] > away['goles_local']).sum())
        e  = int((home['goles_local'] == home['goles_visitante']).sum()) + \
             int((away['goles_visitante'] == away['goles_local']).sum())
        p  = pj - g - e
        pts = g * 3 + e
        rows.append({
            'Equipo': team, 'PJ': pj, 'G': g, 'E': e, 'P': p,
            'GF': gf, 'GC': gc, 'DIF': gf - gc, 'PTS': pts,
        })

    if not rows:
        return pd.DataFrame(columns=['Pos', 'Equipo', 'PJ', 'G', 'E', 'P', 'GF', 'GC', 'DIF', 'PTS'])

    df_out = pd.DataFrame(rows)
    df_out = df_out.sort_values(['PTS', 'DIF', 'GF'], ascending=[False, False, False])
    df_out.insert(0, 'Pos', range(1, len(df_out) + 1))
    return df_out.reset_index(drop=True)


def compute_matchday_summary(df_jornada: pd.DataFrame, df_all: pd.DataFrame, jornada: int) -> Dict:
    """Genera el resumen completo de una jornada concreta.

    Args:
        df_jornada: Partidos filtrados para la jornada indicada.
        df_all: Todos los partidos de la temporada (para clasificación acumulada).
        jornada: Número de jornada.

    Returns:
        Dict con claves: jornada, num_partidos, results, total_goals, avg_goals,
        total_yellow, total_red, avg_possession_local, avg_possession_visitante,
        most_exciting, xg_surprise, standings.
    """
    results = []
    sort_data = df_jornada.sort_values('local_team') if 'local_team' in df_jornada.columns else df_jornada
    for _, row in sort_data.iterrows():
        gl = int(row['goles_local'])
        gv = int(row['goles_visitante'])
        if gl > gv:
            res = 'L'
        elif gl == gv:
            res = 'E'
        else:
            res = 'V'
        results.append({
            'local':           row['local_team'],
            'goles_local':     gl,
            'goles_visitante': gv,
            'visitante':       row['visitante_team'],
            'resultado':       res,
            'goles_totales':   gl + gv,
        })

    total_goals = sum(r['goles_totales'] for r in results)
    avg_goals   = round(total_goals / len(results), 2) if results else 0.0
    most_exciting = max(results, key=lambda r: r['goles_totales']) if results else None

    # Tarjetas
    total_yellow = None
    total_red    = None
    if 'amarillas_local' in df_jornada.columns and df_jornada['amarillas_local'].notna().any():
        total_yellow = int(
            df_jornada['amarillas_local'].sum(skipna=True) +
            df_jornada['amarillas_visitante'].sum(skipna=True)
        )
    if 'rojas_local' in df_jornada.columns and df_jornada['rojas_local'].notna().any():
        total_red = int(
            df_jornada['rojas_local'].sum(skipna=True) +
            df_jornada['rojas_visitante'].sum(skipna=True)
        )

    # Posesión media
    avg_possession_local     = None
    avg_possession_visitante = None
    if 'posesion_local' in df_jornada.columns and df_jornada['posesion_local'].notna().any():
        avg_possession_local     = round(float(df_jornada['posesion_local'].mean()), 1)
        avg_possession_visitante = round(float(df_jornada['posesion_visitante'].mean()), 1)

    # Sorpresa de la jornada: partido donde el resultado contradice más al xG esperado
    xg_surprise = None
    if 'xg_local' in df_jornada.columns and df_jornada['xg_local'].notna().any():
        xg_cols = ['local_team', 'visitante_team', 'goles_local', 'goles_visitante', 'xg_local', 'xg_visitante']
        xg_data = df_jornada[xg_cols].dropna(subset=['xg_local', 'xg_visitante']).copy()
        if not xg_data.empty:
            xg_data['xg_winner'] = (xg_data['xg_local'] - xg_data['xg_visitante']).apply(
                lambda x: 'L' if x > 0.3 else ('V' if x < -0.3 else 'E')
            )
            xg_data['real_winner'] = xg_data.apply(
                lambda r: 'L' if r['goles_local'] > r['goles_visitante']
                          else ('V' if r['goles_local'] < r['goles_visitante'] else 'E'),
                axis=1,
            )
            surprised = xg_data[xg_data['xg_winner'] != xg_data['real_winner']].copy()
            if not surprised.empty:
                surprised['margin'] = (surprised['xg_local'] - surprised['xg_visitante']).abs()
                row_s = surprised.sort_values('margin', ascending=False).iloc[0]
                xg_surprise = {
                    'local':           row_s['local_team'],
                    'visitante':       row_s['visitante_team'],
                    'goles_local':     int(row_s['goles_local']),
                    'goles_visitante': int(row_s['goles_visitante']),
                    'xg_local':        round(float(row_s['xg_local']), 2),
                    'xg_visitante':    round(float(row_s['xg_visitante']), 2),
                }

    # Clasificación acumulada hasta esta jornada
    standings = compute_standings(df_all, up_to_jornada=jornada)

    return {
        'jornada':                  jornada,
        'num_partidos':             len(results),
        'results':                  results,
        'total_goals':              total_goals,
        'avg_goals':                avg_goals,
        'total_yellow':             total_yellow,
        'total_red':                total_red,
        'avg_possession_local':     avg_possession_local,
        'avg_possession_visitante': avg_possession_visitante,
        'most_exciting':            most_exciting,
        'xg_surprise':              xg_surprise,
        'standings':                standings,
    }


_COMPETITION_NAME_MAP = {
    'spanish la liga':          'La Liga',
    'spanish primera division': 'La Liga',
    'primera division':         'La Liga',
    'english premier league':   'Premier League',
    'german bundesliga':        'Bundesliga',
    'italian serie a':          'Serie A',
    'french ligue 1':           'Ligue 1',
    'dutch eredivisie':         'Eredivisie',
    'portuguese primeira liga': 'Primeira Liga',
    'uefa champions league':    'Champions League',
    'uefa europa league':       'Europa League',
}

def _normalize_competition(name: str) -> str:
    """Devuelve el nombre normalizado de la competición (sin prefijo de país)."""
    key = name.strip().lower()
    return _COMPETITION_NAME_MAP.get(key, name)


def compute_match_detail(df: pd.DataFrame, match_id: int) -> Dict:
    """Ficha técnica completa de un partido específico.

    Args:
        df: DataFrame completo con todos los partidos.
        match_id: Valor de la columna id_event.

    Returns:
        Dict con todos los datos del partido y análisis narrativo automático.
        Claves principales: local, visitante, goles_local, goles_visitante,
        resultado, fecha, jornada, estadio, arbitro, espectadores, competition,
        season, video_highlights, stats (lista de dicts comparativos),
        narrativa, contexto_local (pos en tabla), contexto_visitante.
        Lanza ValueError si el match_id no existe.
    """
    matches = df[df['id_event'] == match_id]
    if matches.empty:
        raise ValueError(f'No se encontró el partido con id_event={match_id}')
    row = matches.iloc[0]

    def _val(col: str):
        v = row.get(col)
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return None
        return v

    def _int(col: str) -> Optional[int]:
        v = _val(col)
        return int(v) if v is not None else None

    def _float(col: str) -> Optional[float]:
        v = _val(col)
        return round(float(v), 1) if v is not None else None

    gl = int(row['goles_local'])
    gv = int(row['goles_visitante'])
    local     = str(row['local_team'])
    visitante = str(row['visitante_team'])

    if gl > gv:
        resultado = 'local'
    elif gl < gv:
        resultado = 'visitante'
    else:
        resultado = 'empate'

    # Tabla de stats cara a cara
    STAT_DEFS = [
        ('Tiros totales',         'shots_local',              'shots_visitante'),
        ('Tiros a puerta',        'shots_on_target_local',    'shots_on_target_visitante'),
        ('Tiros fuera',           'shots_off_target_local',   'shots_off_target_visitante'),
        ('Tiros bloqueados',      'shots_blocked_local',      'shots_blocked_visitante'),
        ('xG',                    'xg_local',                 'xg_visitante'),
        ('Posesión %',            'posesion_local',           'posesion_visitante'),
        ('Corners',               'corners_local',            'corners_visitante'),
        ('Faltas',                'faltas_local',             'faltas_visitante'),
        ('Fueras de juego',       'fueras_de_juego_local',    'fueras_de_juego_visitante'),
        ('Paradas portero',       'paradas_local',            'paradas_visitante'),
        ('Pases',                 'pases_local',              'pases_visitante'),
        ('Pases precisos',        'pases_precisos_local',     'pases_precisos_visitante'),
        ('Precisión pases %',     'precision_pases_local',    'precision_pases_visitante'),
        ('Tarjetas amarillas',    'amarillas_local',          'amarillas_visitante'),
        ('Tarjetas rojas',        'rojas_local',              'rojas_visitante'),
    ]
    stats = []
    for label, col_l, col_v in STAT_DEFS:
        vl = _val(col_l)
        vv = _val(col_v)
        if vl is None and vv is None:
            continue
        vl_disp = f'{float(vl):.0f}' if vl is not None else '-'
        vv_disp = f'{float(vv):.0f}' if vv is not None else '-'
        # Ventaja: quién es mayor (para posesión y precisión pases, mayor = mejor local/visit)
        if vl is not None and vv is not None:
            vl_f, vv_f = float(vl), float(vv)
            if label in ('Faltas', 'Fueras de juego'):
                advantage = 'local' if vl_f < vv_f else ('visitante' if vv_f < vl_f else 'equal')
            else:
                advantage = 'local' if vl_f > vv_f else ('visitante' if vv_f > vl_f else 'equal')
        else:
            advantage = 'equal'
        stats.append({'stat': label, 'local': vl_disp, 'visitante': vv_disp, 'ventaja': advantage})

    # Análisis narrativo automático
    frases = []
    pos_l = _float('posesion_local')
    pos_v = _float('posesion_visitante')
    if pos_l is not None:
        dom = local if pos_l >= 50 else visitante
        frases.append(f'{dom} dominó la posesión ({pos_l:.0f}% vs {pos_v:.0f}%).')

    xg_l = _float('xg_local')
    xg_v = _float('xg_visitante')
    if xg_l is not None and xg_v is not None:
        if gl > gv and xg_l < xg_v:
            frases.append(
                f'{local} ganó pese a generar menos peligro según el xG'
                f' ({xg_l} vs {xg_v}), una victoria algo sorprendente.'
            )
        elif gl < gv and xg_l > xg_v:
            frases.append(
                f'{visitante} ganó pese a generar menos peligro según el xG'
                f' ({xg_v} vs {xg_l}), un resultado inesperado.'
            )
        else:
            frases.append(
                f'El xG respaldó el resultado: {local} {xg_l} — {xg_v} {visitante}.'
            )

    shots_l = _int('shots_on_target_local')
    shots_v = _int('shots_on_target_visitante')
    if shots_l is not None and shots_v is not None:
        if shots_l > shots_v:
            frases.append(f'{local} fue más peligroso con {shots_l} tiros a puerta frente a {shots_v}.')
        elif shots_v > shots_l:
            frases.append(f'{visitante} fue más incisivo con {shots_v} tiros a puerta frente a {shots_l}.')

    par_l = _int('paradas_local')
    par_v = _int('paradas_visitante')
    if par_l is not None and par_l >= 6:
        frases.append(f'El portero de {local} realizó {par_l} paradas clave.')
    if par_v is not None and par_v >= 6:
        frases.append(f'El portero de {visitante} realizó {par_v} paradas clave.')

    if not frases:
        frases.append('Partido sin datos técnicos suficientes para el análisis narrativo.')

    narrativa = ' '.join(frases)

    # Contexto en la liga (posición antes del partido = clasificación hasta jornada - 1)
    jornada_num = _int('jornada')
    contexto_local     = None
    contexto_visitante = None
    if jornada_num is not None and jornada_num > 1:
        standings_prev = compute_standings(df, up_to_jornada=jornada_num - 1)
        if not standings_prev.empty:
            row_l = standings_prev[standings_prev['Equipo'] == local]
            row_v = standings_prev[standings_prev['Equipo'] == visitante]
            if not row_l.empty:
                r = row_l.iloc[0]
                contexto_local = {
                    'pos': int(r['Pos']), 'pts': int(r['PTS']),
                    'pj': int(r['PJ']), 'gf': int(r['GF']), 'gc': int(r['GC']),
                }
            if not row_v.empty:
                r = row_v.iloc[0]
                contexto_visitante = {
                    'pos': int(r['Pos']), 'pts': int(r['PTS']),
                    'pj': int(r['PJ']), 'gf': int(r['GF']), 'gc': int(r['GC']),
                }

    return {
        'match_id':          match_id,
        'local':             local,
        'visitante':         visitante,
        'goles_local':       gl,
        'goles_visitante':   gv,
        'resultado':         resultado,
        'fecha':             str(_val('date') or '-'),
        'jornada':           jornada_num,
        'estadio':           str(_val('estadio') or '-'),
        'arbitro':           str(_val('arbitro') or '-'),
        'espectadores':      _int('espectadores'),
        'competition':       _normalize_competition(str(_val('competition') or '-')),
        'season':            str(_val('season') or '-'),
        'video_highlights':  _val('video_highlights'),
        'stats':             stats,
        'narrativa':         narrativa,
        'contexto_local':    contexto_local,
        'contexto_visitante': contexto_visitante,
    }


def compute_xpts(df: pd.DataFrame) -> pd.DataFrame:
    """Clasificación alternativa basada en puntos esperados (xPts) via modelo Poisson.

    Para cada partido con datos de xG estima P(victoria local), P(empate) y
    P(victoria visitante) usando distribuciones de Poisson independientes e
    iid, y calcula los xPts que debería haber obtenido cada equipo.

    Returns:
        DataFrame con columnas: Pos, Equipo, PJ, xPts, PTS, Diff
        Ordenado por xPts descendente. Vacío si no hay datos xG disponibles.
    """
    MAX_G = 8
    k_arr = np.arange(MAX_G + 1, dtype=float)
    log_fact = np.zeros(MAX_G + 1)
    for i in range(1, MAX_G + 1):
        log_fact[i] = log_fact[i - 1] + np.log(i)

    def _pmf(lam: float) -> np.ndarray:
        if lam <= 0:
            p = np.zeros(MAX_G + 1)
            p[0] = 1.0
            return p
        log_p = -lam + k_arr * np.log(lam) - log_fact
        return np.exp(np.clip(log_p, -700, 700))

    def _match_xpts(xg_l: float, xg_v: float):
        P = np.outer(_pmf(xg_l), _pmf(xg_v))  # P[i,j] = P(local=i)·P(visita=j)
        p_home = float(np.tril(P, -1).sum())   # i > j → local gana
        p_draw  = float(np.trace(P))
        p_away  = float(np.triu(P, 1).sum())   # j > i → visitante gana
        return 3 * p_home + p_draw, 3 * p_away + p_draw

    teams = sorted(set(df['local_team'].dropna()) | set(df['visitante_team'].dropna()))
    xpts_map: Dict[str, float] = {t: 0.0 for t in teams}
    pts_map:  Dict[str, int]   = {t: 0   for t in teams}
    pj_map:   Dict[str, int]   = {t: 0   for t in teams}

    for _, row in df.iterrows():
        local = row.get('local_team')
        away  = row.get('visitante_team')
        xg_l  = row.get('xg_local')
        xg_v  = row.get('xg_visitante')
        if pd.isna(local) or pd.isna(away) or pd.isna(xg_l) or pd.isna(xg_v):
            continue
        try:
            xg_l_f, xg_v_f = float(xg_l), float(xg_v)
        except (TypeError, ValueError):
            continue
        if xg_l_f < 0 or xg_v_f < 0:
            continue

        xp_l, xp_v = _match_xpts(xg_l_f, xg_v_f)
        xpts_map[local] += xp_l
        xpts_map[away]  += xp_v
        pj_map[local]   += 1
        pj_map[away]    += 1

        try:
            gl = int(row.get('goles_local', 0) or 0)
            gv = int(row.get('goles_visitante', 0) or 0)
        except (TypeError, ValueError):
            gl, gv = 0, 0
        if gl > gv:
            pts_map[local] += 3
        elif gl == gv:
            pts_map[local] += 1
            pts_map[away]  += 1
        else:
            pts_map[away] += 3

    rows_xpts = [
        {
            'Equipo': t,
            'PJ':     pj_map[t],
            'xPts':   round(xpts_map[t], 1),
            'PTS':    pts_map[t],
            'Diff':   round(pts_map[t] - xpts_map[t], 1),
        }
        for t in teams if pj_map[t] > 0
    ]
    if not rows_xpts:
        return pd.DataFrame(columns=['Pos', 'Equipo', 'PJ', 'xPts', 'PTS', 'Diff'])

    df_xpts = pd.DataFrame(rows_xpts).sort_values('xPts', ascending=False).reset_index(drop=True)
    df_xpts.insert(0, 'Pos', range(1, len(df_xpts) + 1))
    return df_xpts


def compute_liga_summary(df: pd.DataFrame) -> Dict:
    """Resumen completo de una temporada de liga.

    Genera toda la información necesaria para el informe de Liga:
    clasificación, récords, estadísticas técnicas por equipo y globales.

    Returns:
        Dict con:
          competition, season, jornadas, partidos_totales,
          goles_totales, goles_promedio, partido_mas_goleador,
          clasificacion (DataFrame),
          stats_por_equipo (DataFrame),
          records (dict),
          home_away (DataFrame),
    """
    if df.empty:
        return {}

    competition = _normalize_competition(str(df['competition'].iloc[0]) if 'competition' in df.columns else '-')
    season = str(df['season'].iloc[0]) if 'season' in df.columns else '-'
    jornadas = int(df['jornada'].nunique()) if 'jornada' in df.columns and df['jornada'].notna().any() else 0
    partidos_totales = len(df)
    goles_totales = int(df['goles_totales'].sum())
    goles_promedio = round(float(df['goles_totales'].mean()), 2)

    # Partido más goleador
    idx_max = df['goles_totales'].idxmax()
    partido_mas_goleador = {
        'local':     str(df.at[idx_max, 'local_team'])       if 'local_team'      in df.columns else '-',
        'visitante': str(df.at[idx_max, 'visitante_team'])   if 'visitante_team'  in df.columns else '-',
        'goles_l':   int(df['goles_local'].at[idx_max])      if 'goles_local'     in df.columns else 0,  # type: ignore[arg-type]
        'goles_v':   int(df['goles_visitante'].at[idx_max])  if 'goles_visitante' in df.columns else 0,  # type: ignore[arg-type]
        'total':     int(df['goles_totales'].at[idx_max]),                                                 # type: ignore[arg-type]
        'jornada':   df.at[idx_max, 'jornada']               if 'jornada'         in df.columns else '-',
    }

    # Clasificación
    clasificacion = compute_standings(df)

    # Estadísticas técnicas por equipo (promedio de columnas disponibles)
    num_cols = {
        'shots_local':       'Tiros (L)',
        'shots_visitante':   'Tiros (V)',
        'xg_local':          'xG (L)',
        'xg_visitante':      'xG (V)',
        'posesion_local':    'Pos% (L)',
        'posesion_visitante':'Pos% (V)',
        'corners_local':     'Corners (L)',
        'corners_visitante': 'Corners (V)',
    }
    # Stats por equipo como local
    teams = sorted(set(df['local_team'].dropna()) | set(df['visitante_team'].dropna()))
    rows_stats = []
    for team in teams:
        df_l = df[df['local_team'] == team]
        df_v = df[df['visitante_team'] == team]
        pj_l = len(df_l)
        pj_v = len(df_v)

        def avg_col(d, col):
            if col in d.columns and d[col].notna().any():
                return round(float(d[col].mean()), 1)
            return None

        gf = (df_l['goles_local'].sum() if 'goles_local' in df_l.columns else 0) + \
             (df_v['goles_visitante'].sum() if 'goles_visitante' in df_v.columns else 0)
        gc = (df_l['goles_visitante'].sum() if 'goles_visitante' in df_l.columns else 0) + \
             (df_v['goles_local'].sum() if 'goles_local' in df_v.columns else 0)

        xg_l = avg_col(df_l, 'xg_local')
        xg_v = avg_col(df_v, 'xg_visitante')
        xg = round((xg_l or 0) * pj_l / max(pj_l + pj_v, 1) +
                   (xg_v or 0) * pj_v / max(pj_l + pj_v, 1), 2) if (xg_l or xg_v) else None

        pj_total = pj_l + pj_v
        total_xg_equipo = xg * pj_total if xg is not None and pj_total > 0 else None
        over = round(int(gf) / total_xg_equipo, 2) if total_xg_equipo and total_xg_equipo > 0 else None

        pos_l = avg_col(df_l, 'posesion_local')
        pos_v = avg_col(df_v, 'posesion_visitante')
        pos = round((pos_l or 0) * pj_l / max(pj_l + pj_v, 1) +
                    (pos_v or 0) * pj_v / max(pj_l + pj_v, 1), 1) if (pos_l or pos_v) else None

        shots_l = avg_col(df_l, 'shots_local')
        shots_v = avg_col(df_v, 'shots_visitante')
        shots = round((shots_l or 0) * pj_l / max(pj_l + pj_v, 1) +
                      (shots_v or 0) * pj_v / max(pj_l + pj_v, 1), 1) if (shots_l or shots_v) else None

        rows_stats.append({
            'Equipo': team,
            'PJ':     pj_l + pj_v,
            'GF':     int(gf),
            'GC':     int(gc),
            'xG':     xg,
            'Over%':  over,
            'Pos%':   pos,
            'Tiros':  shots,
        })
    stats_por_equipo = pd.DataFrame(rows_stats).sort_values('GF', ascending=False).reset_index(drop=True)

    # Récords
    equipo_mas_goleador = str(clasificacion.loc[clasificacion['GF'].idxmax(), 'Equipo']) if not clasificacion.empty else '-'
    equipo_menos_goleado = str(clasificacion.loc[clasificacion['GC'].idxmin(), 'Equipo']) if not clasificacion.empty else '-'

    partido_max_asist = None
    if 'espectadores' in df.columns and df['espectadores'].notna().any():
        idx_a = df['espectadores'].idxmax()
        partido_max_asist = {
            'local':        str(df.at[idx_a, 'local_team'])    if 'local_team'     in df.columns else '-',
            'visitante':    str(df.at[idx_a, 'visitante_team'])if 'visitante_team' in df.columns else '-',
            'espectadores': int(df['espectadores'].at[idx_a]),  # type: ignore[arg-type]
            'estadio':      str(df.at[idx_a, 'estadio'])       if 'estadio'        in df.columns else '-',
        }

    arbitro_top = None
    if 'arbitro' in df.columns and df['arbitro'].notna().any():
        arb_counts = df['arbitro'].value_counts()
        arbitro_top = {'nombre': str(arb_counts.index[0]), 'partidos': int(arb_counts.iloc[0])}

    # Racha máxima de victorias por equipo
    def max_racha(team_name: str) -> int:
        df_t = df[(df['local_team'] == team_name) | (df['visitante_team'] == team_name)]
        if 'jornada' in df_t.columns:
            df_t = df_t.sort_values('jornada')
        resultados = []
        for _, r in df_t.iterrows():
            if r['local_team'] == team_name:
                if r['goles_local'] > r['goles_visitante']:
                    resultados.append('V')
                else:
                    resultados.append('X')
            else:
                if r['goles_visitante'] > r['goles_local']:
                    resultados.append('V')
                else:
                    resultados.append('X')
        racha = max_r = 0
        for r in resultados:
            racha = racha + 1 if r == 'V' else 0
            max_r = max(max_r, racha)
        return max_r

    equipo_mejor_racha = max((teams), key=lambda t: max_racha(t)) if teams else '-'
    mejor_racha_n = max_racha(equipo_mejor_racha) if equipo_mejor_racha != '-' else 0

    records = {
        'equipo_mas_goleador':   equipo_mas_goleador,
        'equipo_menos_goleado':  equipo_menos_goleado,
        'partido_max_asistencia': partido_max_asist,
        'arbitro_top':           arbitro_top,
        'equipo_mejor_racha':    equipo_mejor_racha,
        'mejor_racha_victorias': mejor_racha_n,
    }

    # Rendimiento local vs visitante por equipo
    home_away_rows = []
    for team in teams:
        df_l = df[df['local_team'] == team]
        df_v = df[df['visitante_team'] == team]
        def wdl(d, is_local):
            if is_local:
                w = (d['goles_local'] > d['goles_visitante']).sum()
                e = (d['goles_local'] == d['goles_visitante']).sum()
                l = (d['goles_local'] < d['goles_visitante']).sum()
            else:
                w = (d['goles_visitante'] > d['goles_local']).sum()
                e = (d['goles_visitante'] == d['goles_local']).sum()
                l = (d['goles_visitante'] < d['goles_local']).sum()
            return int(w), int(e), int(l)
        wl, el, ll = wdl(df_l, True)
        wv, ev, lv = wdl(df_v, False)
        pts_l = wl * 3 + el
        pts_v = wv * 3 + ev
        home_away_rows.append({
            'Equipo':  team,
            'PJ_L':    len(df_l), 'W_L': wl, 'E_L': el, 'D_L': ll, 'Pts_L': pts_l,
            'PJ_V':    len(df_v), 'W_V': wv, 'E_V': ev, 'D_V': lv, 'Pts_V': pts_v,
        })
    home_away = pd.DataFrame(home_away_rows).sort_values('Pts_L', ascending=False).reset_index(drop=True)

    # Clasificación alternativa por xPts
    xpts_standings = compute_xpts(df)

    return {
        'competition':          competition,
        'season':               season,
        'jornadas':             jornadas,
        'partidos_totales':     partidos_totales,
        'goles_totales':        goles_totales,
        'goles_promedio':       goles_promedio,
        'partido_mas_goleador': partido_mas_goleador,
        'clasificacion':        clasificacion,
        'stats_por_equipo':     stats_por_equipo,
        'records':              records,
        'home_away':            home_away,
        'xpts_standings':       xpts_standings,
    }


def compute_player_profile(df_players: pd.DataFrame, player_name: str, top_n: int = 5) -> Dict:
    """Perfil de rendimiento individual de un jugador.

    Busca al jugador por nombre (insensible a mayúsculas, coincidencia parcial).
    Devuelve sus stats de temporada, ratios calculados y posición en el ranking
    del equipo (goleadores y asistentes).

    Returns:
        Dict con:
          found (bool), player_name, team, position, season,
          appearances, goals, assists, ga, shots_on_target,
          yellow_cards, red_cards,
          goles_por_partido, asistencias_por_partido, ga_por_partido,
          ranking_goles (int, posición dentro del equipo),
          ranking_asistencias (int),
          compañeros_goleadores (DataFrame top 5 del equipo),
          compañeros_asistentes (DataFrame top 5 del equipo),
          pct_partidos_con_gol (float),
          pct_partidos_con_ga (float),
    """
    if df_players.empty:
        return {'found': False}

    mask = df_players['player_name'].str.contains(player_name, case=False, na=False)
    matches = df_players[mask]
    if matches.empty:
        return {'found': False, 'player_name': player_name}

    # Si hay varias coincidencias, tomamos la de más apariciones
    row = matches.sort_values('appearances', ascending=False).iloc[0]

    pj         = int(row.get('appearances', 0))
    goals      = int(row.get('goals', 0))
    assists    = int(row.get('assists', 0))
    ga         = int(row.get('goals_assists', goals + assists))
    sot        = int(row.get('shots_on_target', 0))
    yellows    = int(row.get('yellow_cards', 0))
    reds       = int(row.get('red_cards', 0))
    team       = str(row.get('team', '-'))
    position   = str(row.get('position', '-'))
    season     = str(row.get('season', '-'))

    goles_pp  = round(goals / pj, 3) if pj > 0 else 0.0
    asist_pp  = round(assists / pj, 3) if pj > 0 else 0.0
    ga_pp     = round(ga / pj, 3) if pj > 0 else 0.0
    pct_gol   = round(goals / pj * 100, 1) if pj > 0 else 0.0
    pct_ga    = round(ga / pj * 100, 1) if pj > 0 else 0.0

    # Rankings dentro del equipo (mismo equipo, sin contar al propio jugador primero)
    df_team = df_players[df_players['team'] == team].copy()

    def _rank(df: pd.DataFrame, col: str, val: int) -> int:
        ranked = df.sort_values(col, ascending=False).reset_index(drop=True)
        for i, r in ranked.iterrows():
            if r['player_name'] == row['player_name']:
                return int(i) + 1
        return -1

    ranking_goles     = _rank(df_team, 'goals', goals)
    ranking_asistencias = _rank(df_team, 'assists', assists)

    def _translate_pos(pos: str) -> str:
        return _POS_ES.get(str(pos).strip().upper(), str(pos))

    def _top_n(df: pd.DataFrame, col: str) -> pd.DataFrame:
        top = df.sort_values(col, ascending=False).head(top_n)
        return pd.DataFrame({
            'Jugador':     top['player_name'].values,
            'Pos':         [_translate_pos(p) for p in top['position'].values],
            'PJ':          top['appearances'].values,
            'Goles':       top['goals'].values,
            'Asistencias': top['assists'].values,
        }).reset_index(drop=True)

    compañeros_goleadores  = _top_n(df_team, 'goals')
    compañeros_asistentes  = _top_n(df_team, 'assists')

    return {
        'found':                    True,
        'player_name':              str(row['player_name']),
        'team':                     team,
        'position':                 _translate_pos(position),
        'season':                   season,
        'appearances':              pj,
        'goals':                    goals,
        'assists':                  assists,
        'ga':                       ga,
        'shots_on_target':          sot,
        'yellow_cards':             yellows,
        'red_cards':                reds,
        'goles_por_partido':        goles_pp,
        'asistencias_por_partido':  asist_pp,
        'ga_por_partido':           ga_pp,
        'pct_partidos_con_gol':     pct_gol,
        'pct_partidos_con_ga':      pct_ga,
        'ranking_goles':            ranking_goles,
        'ranking_asistencias':      ranking_asistencias,
        'compañeros_goleadores':    compañeros_goleadores,
        'compañeros_asistentes':    compañeros_asistentes,
    }
