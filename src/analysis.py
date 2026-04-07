from typing import Dict, List, Optional
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
