import json
import os
import shutil
from pathlib import Path
from typing import List, Optional

import numpy as np
import pandas as pd

from .analysis import (
    compute_compare,
    compute_league_comparison,
    compute_liga_summary,
    compute_match_detail,
    compute_matchday_summary,
    compute_overall_metrics,
    compute_player_profile,
    compute_player_rankings,
    compute_standings,
    compute_team_percentiles,
    compute_team_record,
    match_highlights,
    top_defensive_teams,
    top_scoring_teams,
)
from .data_loader import load_match_data
from .player_loader import load_player_stats
from .visualizer import (
    plot_attendance,
    plot_card_statistics,
    plot_compare_radar,
    plot_cumulative_points,
    plot_goals_distribution,
    plot_goals_per_team,
    plot_home_away_performance,
    plot_league_table,
    plot_match_radar,
    plot_match_stats_bar,
    plot_matchday_goals,
    plot_matchday_xg,
    plot_player_bar,
    plot_player_radar,
    plot_possession_distribution,
    plot_results_heatmap,
    plot_shot_funnel,
    plot_shots_comparison,
    plot_temporal_evolution,
    plot_xg_per_match,
    plot_xg_per_team,
)


class SportsAgent:
    def __init__(self, data_path: str, fetch_real: bool = False, competition_id: Optional[int] = None, season: Optional[str] = None, team: Optional[str] = None, seasons: Optional[List[str]] = None, matchday: Optional[int] = None, match_id: Optional[int] = None, player: Optional[str] = None, top_n: int = 5, no_charts: bool = False, refresh_cache: bool = False, cache_ttl_days: int = 7, matchday_range: Optional[tuple] = None, compare: Optional[tuple] = None):
        self.data_path = data_path
        self.fetch_real = fetch_real
        self.competition_id = competition_id
        self.season = season
        self.seasons = seasons
        self.team = team
        self.matchday = matchday
        self.matchday_range = matchday_range  # tuple (start, end) o None
        self.match_id = match_id
        self.player = player
        self.top_n = top_n
        self.no_charts = no_charts
        self.refresh_cache = refresh_cache
        self.cache_ttl_days = cache_ttl_days
        self.data: Optional[pd.DataFrame] = None
        self.full_data: Optional[pd.DataFrame] = None
        self.available_optional_columns: set[str] = set()
        self.metrics: dict = {}
        self.league_metrics: dict = {}
        self.league_comparison: list = []
        self.league_percentiles: list = []
        self.team_record: dict = {}
        self.top_scorers: Optional[pd.DataFrame] = None
        self.top_defenders: Optional[pd.DataFrame] = None
        self.highlights: Optional[pd.DataFrame] = None
        self.player_rankings: dict = {}
        self.matchday_summary: dict = {}
        self.match_detail: dict = {}  # ficha técnica del partido (solo modo Partido)
        self.liga_summary: dict = {}  # resumen completo de liga (solo modo Liga)
        self.player_profile: dict = {}  # perfil del jugador (solo modo Jugador)
        self.player_rankings_raw: Optional[pd.DataFrame] = None  # CSV jugadores cargado
        self.compare: Optional[tuple] = compare  # (team1, team2) para modo --compare
        self.compare_data: dict = {}  # resultado de compute_compare()

    def load_data(self):
        if self.seasons and len(self.seasons) > 1:
            from .data_loader import load_multiple_seasons
            if self.competition_id is None:
                raise ValueError('--competition es obligatorio con --seasons')
            self.data = load_multiple_seasons(
                self.data_path, self.competition_id, self.seasons, self.fetch_real,
                refresh_cache=self.refresh_cache, cache_ttl_days=self.cache_ttl_days,
            )
        else:
            _season = self.seasons[0] if self.seasons and len(self.seasons) == 1 else self.season
            self.data = load_match_data(
                self.data_path, self.fetch_real, self.competition_id, _season,
                refresh_cache=self.refresh_cache, cache_ttl_days=self.cache_ttl_days,
            )
        if self.data is not None and isinstance(self.data, pd.DataFrame):
            self.available_optional_columns = set(self.data.attrs.get('available_optional_columns', []))
        return self.data

    def filter_by_team(self):
        if self.team and self.data is not None:
            # Guardar datos completos de la liga ANTES de filtrar
            self.full_data = self.data.copy()
            team_name = self.team.strip().lower()
            filtered = self.data[
                self.data['local_team'].str.lower().str.contains(team_name, na=False) |
                self.data['visitante_team'].str.lower().str.contains(team_name, na=False)
            ].copy()
            if filtered.empty:
                raise ValueError(f'No se encontraron partidos para el equipo: {self.team}')
            self.data = filtered
            if hasattr(self.data, 'attrs'):
                self.available_optional_columns = set(self.data.attrs.get('available_optional_columns', []))

    def filter_by_matchday(self):
        if self.matchday is not None and self.data is not None:
            self.full_data = self.data.copy()
            filtered = self.data[self.data['jornada'] == self.matchday].copy()
            if filtered.empty:
                raise ValueError(f'No se encontraron partidos para la jornada: {self.matchday}')
            self.data = filtered

    def filter_by_matchday_range(self):
        if self.matchday_range is not None and self.data is not None:
            start, end = self.matchday_range
            self.full_data = self.data.copy()
            filtered = self.data[
                self.data['jornada'].between(start, end)
            ].copy()
            if filtered.empty:
                raise ValueError(f'No se encontraron partidos entre las jornadas {start} y {end}')
            self.data = filtered

    def analyze(self):
        if self.data is None:
            raise ValueError('Datos no cargados. Ejecute load_data() primero.')

        # Modo Compare: --compare TEAM1 TEAM2
        if self.compare is not None:
            team1, team2 = self.compare
            self.compare_data = compute_compare(team1, team2, self.data)
            # metrics mínimas para no romper generate_report
            self.metrics = {'partidos_analizados': len(self.data)}
            self.top_scorers = top_scoring_teams(self.data, n=self.top_n)
            self.top_defenders = top_defensive_teams(self.data, n=self.top_n)
            self.highlights = match_highlights(self.data, n=self.top_n)
            return self.metrics

        # Modo Partido: ficha técnica de un partido específico
        if self.match_id is not None:
            self.match_detail = compute_match_detail(self.data, self.match_id)
            # Rellenar metrics mínimas para no romper generate_report/save_visual_report
            match_row = self.data[self.data['id_event'] == self.match_id]
            self.metrics = compute_overall_metrics(match_row)
            self.top_scorers = top_scoring_teams(match_row, n=self.top_n)
            self.top_defenders = top_defensive_teams(match_row, n=self.top_n)
            self.highlights = match_highlights(match_row, n=self.top_n)
            return self.metrics

        # Modo Jornada: filtrar por número de jornada y generar resumen
        if self.matchday is not None:
            self.filter_by_matchday()
            self.matchday_summary = compute_matchday_summary(self.data, self.full_data if self.full_data is not None else self.data, self.matchday)
            self.metrics = compute_overall_metrics(self.data)
            self.top_scorers = top_scoring_teams(self.data, n=self.top_n)
            self.top_defenders = top_defensive_teams(self.data, n=self.top_n)
            self.highlights = match_highlights(self.data, n=self.top_n)
            return self.metrics

        # Modo Rango de jornadas: --matchday-range START END
        if self.matchday_range is not None:
            self.filter_by_matchday_range()
            # Reutiliza el pipeline de liga restringido al rango de jornadas
            self.liga_summary = compute_liga_summary(self.data)
            self.metrics = compute_overall_metrics(self.data)
            self.top_scorers = top_scoring_teams(self.data, n=self.top_n)
            self.top_defenders = top_defensive_teams(self.data, n=self.top_n)
            self.highlights = match_highlights(self.data, n=self.top_n)
            return self.metrics

        # Modo Jugador: --team + --player
        if self.team and self.player:
            df_players = load_player_stats(
                self.team,
                competition_id=self.competition_id or 2014,
                season=self.season or '2025-2026',
                fetch_real=self.fetch_real,
                verbose=self.fetch_real,
            )
            self.player_rankings_raw = df_players
            self.player_profile = compute_player_profile(df_players, self.player, top_n=self.top_n)
            self.player_rankings = compute_player_rankings(df_players)
            self.filter_by_team()
            self.metrics = compute_overall_metrics(self.data, team=self.team)
            self.top_scorers = top_scoring_teams(self.data, n=self.top_n)
            self.top_defenders = top_defensive_teams(self.data, n=self.top_n)
            self.highlights = match_highlights(self.data, n=self.top_n)
            return self.metrics

        # Modo Liga: sin equipo ni jornada → panorama completo de la temporada
        if not self.team:
            self.liga_summary = compute_liga_summary(self.data)
            self.metrics = compute_overall_metrics(self.data)
            self.top_scorers = top_scoring_teams(self.data, n=self.top_n)
            self.top_defenders = top_defensive_teams(self.data, n=self.top_n)
            self.highlights = match_highlights(self.data, n=self.top_n)
            return self.metrics

        # Modo Equipo: filtrar por equipo
        self.filter_by_team()
        self.metrics = compute_overall_metrics(self.data, team=self.team)
        self.top_scorers = top_scoring_teams(self.data, n=self.top_n)
        self.top_defenders = top_defensive_teams(self.data, n=self.top_n)
        self.highlights = match_highlights(self.data, n=self.top_n)
        # Comparativa vs liga si se filtró por equipo
        if self.full_data is not None:
            self.league_metrics = compute_overall_metrics(self.full_data)
            self.league_comparison = compute_league_comparison(self.metrics, self.league_metrics)
            self.league_percentiles = compute_team_percentiles(self.team, self.full_data)
        # Historial W/D/L si se filtró por equipo
        if self.team:
            self.team_record = compute_team_record(self.data, self.team)
        # Rankings de jugadores si se filtró por equipo
        if self.team:
            df_players = load_player_stats(
                self.team,
                competition_id=self.competition_id or 2014,
                season=self.season or '2025-2026',
                fetch_real=self.fetch_real,
                verbose=self.fetch_real,
            )
            self.player_rankings = compute_player_rankings(df_players)
        return self.metrics


    def format_metric(self, key: str, label: str, is_percent: bool = False) -> str:
        value = self.metrics.get(key)
        if value is None:
            return f"{label}: No disponible para este dataset"
        if is_percent:
            return f"{label}: {value:.1f}%"
        return f"{label}: {value}"

    def format_html_metric(self, key: str) -> str:
        value = self.metrics.get(key)
        return f"{value:.1f}%" if value is not None and isinstance(value, float) else (str(value) if value is not None else 'No disponible')

    # ------------------------------------------------------------------
    # Fase 5.1 — Narrativa automática por reglas
    # ------------------------------------------------------------------

    def _generate_conclusions(self) -> List[str]:
        """Genera un bloque de conclusiones textuales basado en reglas sobre las métricas calculadas.

        Aplica en: modo Equipo (con team_record y league_percentiles)
                   modo Liga  (con liga_summary)
        Retorna lista de strings (líneas) lista para insertar en el informe.
        """
        lines: List[str] = []

        # ── Modo equipo ──────────────────────────────────────────────
        if self.team and self.team_record:
            rec = self.team_record
            m = self.metrics

            # Racha actual — siempre se muestra
            racha = rec.get('racha_actual', '')
            ultimos = list(racha[-5:]) if racha else []
            if ultimos:
                victorias_recientes = ultimos.count('V')
                empates_recientes   = ultimos.count('E')
                derrotas_recientes  = ultimos.count('D')
                forma_str = ' '.join(ultimos)
                if victorias_recientes >= 4:
                    lines.append(f'  ✅ Gran momento de forma: {victorias_recientes}V en los últimos {len(ultimos)} partidos ({forma_str}).')
                elif victorias_recientes >= 3:
                    lines.append(f'  ✅ Buen estado de forma: {victorias_recientes}V en los últimos {len(ultimos)} partidos ({forma_str}).')
                elif derrotas_recientes >= 4:
                    lines.append(f'  ⚠️  Racha negativa: {derrotas_recientes}D en los últimos {len(ultimos)} partidos ({forma_str}).')
                elif derrotas_recientes >= 3:
                    lines.append(f'  ⚠️  Momento difícil: {derrotas_recientes}D en los últimos {len(ultimos)} partidos ({forma_str}).')
                elif victorias_recientes >= 2:
                    lines.append(f'  🔄 Forma reciente aceptable: {victorias_recientes}V-{empates_recientes}E-{derrotas_recientes}D en los últimos {len(ultimos)} ({forma_str}).')
                else:
                    lines.append(f'  📋 Últimos {len(ultimos)} partidos: {forma_str} ({victorias_recientes}V-{empates_recientes}E-{derrotas_recientes}D).')

            # Balance global
            v = rec.get('victorias', 0)
            e = rec.get('empates', 0)
            d = rec.get('derrotas', 0)
            pts = rec.get('puntos', 0)
            total = v + e + d
            if total > 0:
                pct_victorias = v / total * 100
                if pct_victorias >= 55:
                    lines.append(f'  🏆 Excelente rendimiento global: {pct_victorias:.0f}% de victorias ({v}V/{e}E/{d}D, {pts} pts).')
                elif pct_victorias >= 40:
                    lines.append(f'  📊 Rendimiento sólido: {v}V/{e}E/{d}D — {pts} puntos en {total} partidos.')
                elif pct_victorias >= 25:
                    lines.append(f'  📊 Rendimiento medio: {v}V/{e}E/{d}D — {pts} puntos en {total} partidos.')
                else:
                    lines.append(f'  ⚠️  Bajo rendimiento: solo {pct_victorias:.0f}% victorias ({v}V/{e}E/{d}D, {pts} pts).')

            # Racha máxima sin perder
            rsm = rec.get('racha_sin_perder_max', 0)
            if rsm >= 5:
                lines.append(f'  🏅 Racha más larga sin perder: {rsm} partidos consecutivos.')

            # Ofensiva
            gf_p = m.get('goles_a_favor_promedio')
            gc_p = m.get('goles_concedidos_promedio')
            if gf_p is not None:
                if gf_p >= 2.0:
                    lines.append(f'  ⚽ Ataque destacado: {gf_p:.2f} goles/partido.')
                elif gf_p >= 1.5:
                    lines.append(f'  ⚽ Ataque por encima de la media: {gf_p:.2f} goles/partido.')
                elif gf_p < 1.0:
                    lines.append(f'  ⚠️  Ataque pobre: solo {gf_p:.2f} goles/partido.')
                else:
                    lines.append(f'  📊 Promedio ofensivo: {gf_p:.2f} goles anotados por partido.')

            # Defensiva
            if gc_p is not None:
                if gc_p < 1.0:
                    lines.append(f'  🛡️  Defensa muy sólida: solo {gc_p:.2f} goles encajados/partido.')
                elif gc_p <= 1.4:
                    lines.append(f'  🛡️  Defensa sólida: {gc_p:.2f} goles encajados/partido.')
                elif gc_p >= 2.0:
                    lines.append(f'  ⚠️  Defensa vulnerable: {gc_p:.2f} goles encajados/partido.')
                else:
                    lines.append(f'  📊 Promedio defensivo: {gc_p:.2f} goles encajados por partido.')

            # Eficiencia ofensiva (overperformance xG)
            over = m.get('overperformance')
            if over is not None:
                if over >= 1.2:
                    lines.append(f'  🎯 Muy eficiente en ataque: ratio goles/xG = {over:.2f} (convierte más de lo esperado).')
                elif over <= 0.75:
                    lines.append(f'  📉 Baja eficiencia ofensiva: ratio goles/xG = {over:.2f} (convierte menos de lo esperado).')

            # Percentiles de liga
            for p in self.league_percentiles:
                pct = p['percentil']
                met = p['metrica']
                if pct >= 90:
                    lines.append(f'  🏆 Top 10% de la liga en {met} (percentil {pct}).')
                elif pct <= 10:
                    lines.append(f'  ⚠️  Bottom 10% de la liga en {met} (percentil {pct}).')

        # ── Modo liga ────────────────────────────────────────────────
        elif self.liga_summary:
            s = self.liga_summary
            clf = s.get('clasificacion')
            if clf is not None and not clf.empty:
                lider = clf.iloc[0]
                escolta = clf.iloc[1] if len(clf) > 1 else None
                dif_pts = int(lider['PTS']) - (int(escolta['PTS']) if escolta is not None else 0)
                lines.append(f'  🏆 Líder: {lider["Equipo"]} con {int(lider["PTS"])} puntos'
                              + (f', {dif_pts} por encima del segundo.' if escolta is not None else '.'))

                # Equipos en zona de riesgo de descenso
                n = len(clf)
                if n >= 3:
                    descenso = clf.tail(3)['Equipo'].tolist()
                    lines.append(f'  ⚠️  Zona de descenso: {", ".join(descenso)}.')

            # Máximos goleadores (equipos)
            r = s.get('records', {})
            if r.get('equipo_mas_goleador'):
                lines.append(f'  ⚽ Equipo más goleador: {r["equipo_mas_goleador"]}.')
            if r.get('equipo_menos_goleado'):
                lines.append(f'  🛡️  Equipo menos goleado: {r["equipo_menos_goleado"]}.')
            if r.get('equipo_mejor_racha') and r.get('mejor_racha_victorias', 0) >= 5:
                lines.append(f'  🔥 Mejor racha de la temporada: {r["equipo_mejor_racha"]} '
                              f'con {r["mejor_racha_victorias"]} victorias consecutivas.')

            # Goles por partido
            gpp = s.get('goles_promedio')
            if gpp is not None:
                try:
                    gpp_f = float(gpp)
                    if gpp_f >= 3.0:
                        lines.append(f'  📊 Temporada muy goleadora: {gpp_f:.2f} goles/partido de media.')
                    elif gpp_f < 2.0:
                        lines.append(f'  📊 Temporada defensiva: solo {gpp_f:.2f} goles/partido de media.')
                except (ValueError, TypeError):
                    pass

        if not lines:
            return []

        header = ['', 'Conclusiones', '------------']
        return header + lines + ['']

    def _generate_conclusions_html(self) -> str:
        """Versión HTML de las conclusiones (para incrustar en los informes HTML)."""
        text_lines = self._generate_conclusions()
        if not text_lines:
            return ''

        items = [l for l in text_lines if l.startswith('  ')]
        if not items:
            return ''

        html_items = ''.join(f'    <li>{line.strip()}</li>\n' for line in items)
        return (
            '  <h2>Conclusiones</h2>\n'
            '  <div style="background:white;border-radius:8px;padding:16px 20px;'
            'box-shadow:0 2px 8px rgba(0,0,0,0.08);margin-bottom:24px;">\n'
            '  <ul style="line-height:2;margin:0;padding-left:20px;">\n'
            f'{html_items}'
            '  </ul></div>\n'
        )

    # ------------------------------------------------------------------
    # Fase 5.2 — Narrativa comparativa intertemporada
    # ------------------------------------------------------------------

    def _generate_interseason_narrative(self) -> List[str]:
        """Genera comparativas de métricas entre temporadas cuando se usa --seasons con 2+.

        Requiere que self.data contenga una columna 'season' y que self.seasons tenga ≥2 entradas.
        Retorna lista de líneas lista para insertar en el informe.
        """
        if not self.seasons or len(self.seasons) < 2 or self.data is None:
            return []
        if 'season' not in self.data.columns:
            return []

        seasons_sorted = sorted(self.seasons, key=lambda s: int(str(s).split('-')[0]))
        if len(seasons_sorted) < 2:
            return []

        def _metrics_for_season(s: str) -> dict:
            mask = self.data['season'].astype(str).str.startswith(str(s))
            sub = self.data[mask]
            if sub.empty:
                return {}
            return compute_overall_metrics(sub, team=self.team)

        first_season = str(seasons_sorted[0])
        last_season  = str(seasons_sorted[-1])
        m_old = _metrics_for_season(first_season)
        m_new = _metrics_for_season(last_season)

        if not m_old or not m_new:
            return []

        COMPARE_METRICS = [
            ('goles_a_favor_promedio',          'Goles a favor/partido',      True),
            ('goles_concedidos_promedio',        'Goles encajados/partido',    False),
            ('xg_equipo_promedio',               'xG/partido',                 True),
            ('tiros_equipo_promedio',            'Tiros/partido',              True),
            ('tiros_a_puerta_equipo_promedio',   'Tiros a puerta/partido',     True),
            ('posesion_equipo_promedio',         'Posesión (%)',               True),
            ('goles_promedio_por_partido',       'Goles/partido (liga)',       True),
        ]

        lines: List[str] = ['', f'Evolución intertemporada  ({first_season} → {last_season})',
                            '-' * 48]
        found_any = False
        for key, label, higher_is_better in COMPARE_METRICS:
            v_old = m_old.get(key)
            v_new = m_new.get(key)
            if v_old is None or v_new is None:
                continue
            try:
                v_old_f = float(v_old)
                v_new_f = float(v_new)
            except (ValueError, TypeError):
                continue
            if v_old_f == 0:
                continue
            pct = (v_new_f - v_old_f) / abs(v_old_f) * 100
            if abs(pct) < 2:
                direction = 'Sin cambio significativo'
                sign = ' '
            elif (pct > 0) == higher_is_better:
                direction = 'Mejora'
                sign = '+'
            else:
                direction = 'Empeora'
                sign = '+' if pct > 0 else ''
            lines.append(f'  {label:<32} {v_old_f:>6.2f} → {v_new_f:>6.2f}  ({sign}{pct:+.1f}%)  {direction}')
            found_any = True

        if not found_any:
            return []

        lines.append('')
        return lines

    def _generate_compare_report(self, output_path: Optional[str] = None) -> str:
        """Informe de texto para el modo Compare (dos equipos)."""
        c = self.compare_data
        team1 = c.get('team1', '?')
        team2 = c.get('team2', '?')
        m1 = c.get('metrics1', {})
        m2 = c.get('metrics2', {})
        r1 = c.get('record1', {})
        r2 = c.get('record2', {})
        h2h = c.get('h2h', [])
        hs = c.get('h2h_summary', {})

        title = f'COMPARATIVA — {team1}  vs  {team2}'
        lines: List[str] = [title, '=' * len(title), '']

        # Métricas globales
        lines.append(f'{"Métrica":<30} {team1:>22} {team2:>22}')
        lines.append(f'{"-"*30} {"-"*22} {"-"*22}')
        for key, label in [
            ('goles_a_favor_promedio', 'Goles a favor / partido'),
            ('goles_concedidos_promedio', 'Goles encajados / partido'),
            ('xg_equipo_promedio', 'xG / partido'),
            ('tiros_equipo_promedio', 'Tiros / partido'),
            ('posesion_equipo_promedio', 'Posesión media (%)'),
            ('tiros_a_puerta_equipo_promedio', 'Tiros a puerta / partido'),
        ]:
            v1 = m1.get(key)
            v2 = m2.get(key)
            s1 = f'{v1:.2f}' if v1 is not None else '-'
            s2 = f'{v2:.2f}' if v2 is not None else '-'
            lines.append(f'  {label:<28} {s1:>22} {s2:>22}')
        lines.append('')

        # Historial (W/D/L)
        lines.append(f'{"Historial":<30} {team1:>22} {team2:>22}')
        lines.append(f'{"-"*30} {"-"*22} {"-"*22}')
        pj1 = len(r1.get('tabla_resultados', []))
        pj2 = len(r2.get('tabla_resultados', []))
        gf1 = sum(x['gf'] for x in r1.get('tabla_resultados', []))
        gc1 = sum(x['gc'] for x in r1.get('tabla_resultados', []))
        gf2 = sum(x['gf'] for x in r2.get('tabla_resultados', []))
        gc2 = sum(x['gc'] for x in r2.get('tabla_resultados', []))
        dif1 = gf1 - gc1
        dif2 = gf2 - gc2
        for key, label in [('victorias', 'Victorias'), ('empates', 'Empates'), ('derrotas', 'Derrotas'), ('puntos', 'Puntos')]:
            v1 = r1.get(key, '-')
            v2 = r2.get(key, '-')
            lines.append(f'  {label:<28} {str(v1):>22} {str(v2):>22}')
        lines.append(f'  {"Partidos":<28} {str(pj1):>22} {str(pj2):>22}')
        lines.append(f'  {"Goles a favor (GF)":<28} {str(gf1):>22} {str(gf2):>22}')
        lines.append(f'  {"Goles en contra (GC)":<28} {str(gc1):>22} {str(gc2):>22}')
        dif1_str = f'+{dif1}' if dif1 > 0 else str(dif1)
        dif2_str = f'+{dif2}' if dif2 > 0 else str(dif2)
        lines.append(f'  {"Diferencia de goles":<28} {dif1_str:>22} {dif2_str:>22}')
        lines.append('')

        # Cara a cara H2H
        lines.append(f'Enfrentamientos directos ({hs.get("pj", 0)} partidos)')
        lines.append('-' * 40)
        lines.append(
            f'  Victorias {team1}: {hs.get("wins1", 0)}  |  '
            f'Empates: {hs.get("draws", 0)}  |  '
            f'Victorias {team2}: {hs.get("wins2", 0)}'
        )
        lines.append(f'  Goles {team1}: {hs.get("gf1", 0)}  —  Goles {team2}: {hs.get("gf2", 0)}')
        lines.append('')
        if h2h:
            lines.append(f'  {"Jornada":>7}  {"Local":<20} {"Result":>8}  {"Visitante":<20}')
            lines.append(f'  {"-------":>7}  {"-"*20} {"------":>8}  {"-"*20}')
            for m in h2h[-10:]:  # últimos 10
                jor = str(m.get('jornada', '?'))
                loc = m.get('local', '?')
                vis = m.get('visitante', '?')
                res = f'{m.get("goles_local", "?")} - {m.get("goles_visitante", "?")}'
                lines.append(f'  {jor:>7}  {loc:<20} {res:>8}  {vis:<20}')

        report_text = '\n'.join(lines)
        if output_path:
            out = Path(output_path)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(report_text, encoding='utf-8')
        return report_text

    def _generate_compare_html_report(self, output_path: str, image_folder: Optional[str] = None) -> str:
        """Informe HTML para el modo Compare (dos equipos)."""
        c = self.compare_data
        team1 = c.get('team1', '?')
        team2 = c.get('team2', '?')
        m1 = c.get('metrics1', {})
        m2 = c.get('metrics2', {})
        r1 = c.get('record1', {})
        r2 = c.get('record2', {})
        h2h = c.get('h2h', [])
        hs = c.get('h2h_summary', {})

        report_file = Path(output_path)
        report_file.parent.mkdir(parents=True, exist_ok=True)
        image_folder_path = Path(image_folder) if image_folder else report_file.parent
        image_folder_path.mkdir(parents=True, exist_ok=True)
        images = self.save_visual_report(str(image_folder_path))
        relative_images = [
            Path(os.path.relpath(img, start=report_file.parent)).as_posix()
            for img in images if img
        ]

        def fmt(v):
            if v is None:
                return '-'
            try:
                return f'{float(v):.2f}'
            except (ValueError, TypeError):
                return str(v)

        metric_rows = [
            ('goles_a_favor_promedio', 'Goles / partido'),
            ('goles_concedidos_promedio', 'Goles encajados / p'),
            ('xg_equipo_promedio', 'xG / partido'),
            ('tiros_equipo_promedio', 'Tiros / partido'),
            ('posesion_equipo_promedio', 'Posesión (%)'),
            ('tiros_a_puerta_equipo_promedio', 'Tiros a ptas / p'),
        ]
        record_rows = [('victorias', 'Victorias'), ('empates', 'Empates'), ('derrotas', 'Derrotas'), ('puntos', 'Puntos')]

        def better(v1, v2, higher_is_better=True):
            """Retorna (bold1, bold2) css class."""
            try:
                f1, f2 = float(v1), float(v2)
                if f1 == f2:
                    return '', ''
                if higher_is_better:
                    return ('font-weight:bold;color:#27ae60', '') if f1 > f2 else ('', 'font-weight:bold;color:#27ae60')
                else:
                    return ('font-weight:bold;color:#27ae60', '') if f1 < f2 else ('', 'font-weight:bold;color:#27ae60')
            except (ValueError, TypeError):
                return '', ''

        html = [
            '<!DOCTYPE html>',
            '<html lang="es">',
            '<head>',
            '  <meta charset="UTF-8">',
            '  <meta name="viewport" content="width=device-width, initial-scale=1.0">',
            f'  <title>Comparativa: {team1} vs {team2}</title>',
            '  <style>',
            '    body { font-family: Arial, sans-serif; margin: 24px; background: #f7f8fb; color: #222; }',
            '    h2 { color: #2c7bb6; border-bottom: 2px solid #d0e4f7; padding-bottom: 4px; }',
            '    .header-box { background: linear-gradient(135deg, #2e86de 0%, #e74c3c 100%);',
            '      color: white; border-radius: 12px; padding: 20px 28px; margin-bottom: 24px; }',
            '    .header-box h1 { color: white; margin: 0; }',
            '    table { width: 100%; border-collapse: collapse; margin: 12px 0 24px 0; font-size: 0.92em; }',
            '    th, td { padding: 8px 12px; border: 1px solid #d7dbe3; text-align: center; }',
            '    th { background: #e4efff; }',
            '    th.t1 { background: #dbeafe; color: #1e40af; }',
            '    th.t2 { background: #fee2e2; color: #991b1b; }',
            '    td.left { text-align: left; }',
            '    img { max-width: 100%; border-radius: 8px; margin: 8px 0; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }',
            '  </style>',
            '</head>',
            '<body>',
            '  <div class="header-box">',
            f'    <h1>{team1}  vs  {team2}</h1>',
            f'    <p>Comparativa de rendimiento en la temporada</p>',
            '  </div>',

            # Métricas
            '  <h2>Métricas de rendimiento</h2>',
            '  <table>',
            f'    <thead><tr><th class="left">Métrica</th><th class="t1">{team1}</th><th class="t2">{team2}</th></tr></thead>',
            '    <tbody>',
        ]
        low_is_better = {'goles_concedidos_promedio'}
        for key, label in metric_rows:
            v1 = m1.get(key)
            v2 = m2.get(key)
            s1 = fmt(v1)
            s2 = fmt(v2)
            hib = key not in low_is_better
            b1, b2 = better(v1, v2, hib)
            html.append(f'      <tr><td class="left">{label}</td>'
                        f'<td style="{b1}">{s1}</td>'
                        f'<td style="{b2}">{s2}</td></tr>')
        html.append('    </tbody></table>')

        # Historial
        html.extend([
            '  <h2>Historial de la temporada</h2>',
            '  <table>',
            f'    <thead><tr><th class="left">Historial</th><th class="t1">{team1}</th><th class="t2">{team2}</th></tr></thead>',
            '    <tbody>',
        ])
        for key, label in record_rows:
            v1 = r1.get(key, '-')
            v2 = r2.get(key, '-')
            b1, b2 = better(v1, v2)
            html.append(f'      <tr><td class="left">{label}</td>'
                        f'<td style="{b1}">{v1}</td>'
                        f'<td style="{b2}">{v2}</td></tr>')
        pj1 = len(r1.get('tabla_resultados', []))
        pj2 = len(r2.get('tabla_resultados', []))
        gf1_tot = sum(x['gf'] for x in r1.get('tabla_resultados', []))
        gc1_tot = sum(x['gc'] for x in r1.get('tabla_resultados', []))
        gf2_tot = sum(x['gf'] for x in r2.get('tabla_resultados', []))
        gc2_tot = sum(x['gc'] for x in r2.get('tabla_resultados', []))
        dif1_tot = gf1_tot - gc1_tot
        dif2_tot = gf2_tot - gc2_tot
        dif1_str = f'+{dif1_tot}' if dif1_tot > 0 else str(dif1_tot)
        dif2_str = f'+{dif2_tot}' if dif2_tot > 0 else str(dif2_tot)
        b1pj, b2pj = better(pj1, pj2)
        b1gf, b2gf = better(gf1_tot, gf2_tot)
        b1gc, b2gc = better(gc1_tot, gc2_tot, higher_is_better=False)
        b1dif, b2dif = better(dif1_tot, dif2_tot)
        html.append(f'      <tr><td class="left">Partidos</td><td style="{b1pj}">{pj1}</td><td style="{b2pj}">{pj2}</td></tr>')
        html.append(f'      <tr><td class="left">Goles a favor (GF)</td><td style="{b1gf}">{gf1_tot}</td><td style="{b2gf}">{gf2_tot}</td></tr>')
        html.append(f'      <tr><td class="left">Goles en contra (GC)</td><td style="{b1gc}">{gc1_tot}</td><td style="{b2gc}">{gc2_tot}</td></tr>')
        html.append(f'      <tr><td class="left">Diferencia de goles</td><td style="{b1dif}">{dif1_str}</td><td style="{b2dif}">{dif2_str}</td></tr>')
        html.append('    </tbody></table>')

        # H2H
        html.extend([
            f'  <h2>Cara a cara ({hs.get("pj", 0)} partidos)</h2>',
            '  <table>',
            '    <tbody>',
            f'      <tr><td class="left">Victorias {team1}</td><td colspan="2" class="t1">{hs.get("wins1", 0)}</td></tr>',
            f'      <tr><td class="left">Empates</td><td colspan="2">{hs.get("draws", 0)}</td></tr>',
            f'      <tr><td class="left">Victorias {team2}</td><td colspan="2" class="t2">{hs.get("wins2", 0)}</td></tr>',
            f'      <tr><td class="left">Goles {team1} / {team2}</td><td>{hs.get("gf1", 0)}</td><td>{hs.get("gf2", 0)}</td></tr>',
            '    </tbody></table>',
        ])
        if h2h:
            html.extend([
                '  <table>',
                '    <thead><tr><th>Jornada</th><th>Local</th><th>Resultado</th><th>Visitante</th></tr></thead>',
                '    <tbody>',
            ])
            for m in h2h[-10:]:
                jor = m.get('jornada', '?')
                loc = m.get('local', '?')
                vis = m.get('visitante', '?')
                res = f'{m.get("goles_local", "?")} - {m.get("goles_visitante", "?")}'
                html.append(f'      <tr><td>{jor}</td><td>{loc}</td><td>{res}</td><td>{vis}</td></tr>')
            html.append('    </tbody></table>')

        # Gráfico radar
        if relative_images:
            html.extend(['  <h2>Radar comparativo</h2>', '  <div>'])
            for img in relative_images:
                html.append(f'    <img src="{img}" alt="Radar comparativo">')
            html.append('  </div>')

        html.extend(['</body>', '</html>'])
        content = '\n'.join(html)
        report_file.write_text(content, encoding='utf-8')
        return output_path

    def _generate_liga_report(self, output_path: Optional[str] = None) -> str:
        """Informe de texto para el modo Liga."""
        s = self.liga_summary
        lines: List[str] = []

        if self.matchday_range:
            rng_label = f'Jornadas {self.matchday_range[0]}–{self.matchday_range[1]}'
            title = f'INFORME DE RANGO — {s["competition"]}  |  Temporada {s["season"]}  |  {rng_label}'
        else:
            title = f'INFORME DE LIGA — {s["competition"]}  |  Temporada {s["season"]}'
        lines.append(title)
        lines.append('=' * len(title))
        lines.append(f'Jornadas disputadas: {s["jornadas"]}   |   Partidos totales: {s["partidos_totales"]}')
        lines.append(f'Goles totales: {s["goles_totales"]}   |   Promedio por partido: {s["goles_promedio"]}')
        pmg = s['partido_mas_goleador']
        lines.append(
            f'Partido más goleador: {pmg["local"]} {pmg["goles_l"]}-{pmg["goles_v"]} {pmg["visitante"]}'
            f'  ({pmg["total"]} goles, jornada {pmg["jornada"]})'
        )
        lines.append('')

        # Récords
        r = s['records']
        lines.append('Récords de la temporada')
        lines.append('-----------------------')
        lines.append(f'  Equipo más goleador:      {r["equipo_mas_goleador"]}')
        lines.append(f'  Equipo menos goleado:     {r["equipo_menos_goleado"]}')
        lines.append(f'  Mejor racha de victorias: {r["equipo_mejor_racha"]} ({r["mejor_racha_victorias"]} victorias consecutivas)')
        if r['arbitro_top']:
            lines.append(f'  Árbitro más activo:       {r["arbitro_top"]["nombre"]} ({r["arbitro_top"]["partidos"]} partidos)')
        if r['partido_max_asistencia']:
            pa = r['partido_max_asistencia']
            lines.append(f'  Mayor asistencia:         {pa["local"]} vs {pa["visitante"]} — {pa["espectadores"]:,} espectadores ({pa["estadio"]})')
        lines.append('')

        # Clasificación
        lines.append('Clasificación')
        lines.append('-------------')
        clf = s['clasificacion']
        lines.append(f'  {"Pos":>3}  {"Equipo":<25} {"PJ":>3} {"G":>3} {"E":>3} {"P":>3} {"GF":>3} {"GC":>3} {"DIF":>4} {"PTS":>4}')
        lines.append(f'  {"---":>3}  {"-"*25} {"--":>3} {"--":>3} {"--":>3} {"--":>3} {"--":>3} {"--":>3} {"----":>4} {"----":>4}')
        for _, row in clf.iterrows():
            dif = f'+{int(row["DIF"])}' if row['DIF'] > 0 else str(int(row['DIF']))
            lines.append(
                f'  {int(row["Pos"]):>3}  {row["Equipo"]:<25} {int(row["PJ"]):>3} {int(row["G"]):>3}'
                f' {int(row["E"]):>3} {int(row["P"]):>3} {int(row["GF"]):>3} {int(row["GC"]):>3}'
                f' {dif:>4} {int(row["PTS"]):>4}'
            )
        lines.append('')

        # Top goleadores / defensas
        lines.append('Top equipos goleadores')
        lines.append('----------------------')
        if self.top_scorers is not None:
            for _, row in self.top_scorers.iterrows():
                lines.append(f'  {row.iloc[0]:<25}  {int(row.iloc[1])} goles')
        lines.append('')

        lines.append('Top equipos menos goleados')
        lines.append('--------------------------')
        if self.top_defenders is not None:
            for _, row in self.top_defenders.iterrows():
                lines.append(f'  {row.iloc[0]:<25}  {int(row.iloc[1])} goles encajados')
        lines.append('')

        # Estadísticas técnicas por equipo
        lines.append('Estadísticas técnicas por equipo')
        lines.append('--------------------------------')
        st = s['stats_por_equipo']
        lines.append(f'  {"Equipo":<25} {"GF":>4} {"GC":>4} {"xG":>5} {"Over%":>6} {"Pos%":>5} {"Tiros":>6}')
        lines.append(f'  {"-"*25} {"--":>4} {"--":>4} {"---":>5} {"-----":>6} {"----":>5} {"-----":>6}')
        for _, row in st.iterrows():
            xg   = f'{row["xG"]:.2f}' if pd.notna(row.get('xG')) and row.get('xG') is not None else '-'
            over = f'{row["Over%"]:.2f}' if pd.notna(row.get('Over%')) and row.get('Over%') is not None else '-'
            pos  = f'{row["Pos%"]:.1f}' if pd.notna(row.get('Pos%')) and row.get('Pos%') is not None else '-'
            tirs = f'{row["Tiros"]:.1f}' if pd.notna(row.get('Tiros')) and row.get('Tiros') is not None else '-'
            lines.append(f'  {row["Equipo"]:<25} {int(row["GF"]):>4} {int(row["GC"]):>4} {xg:>5} {over:>6} {pos:>5} {tirs:>6}')
        lines.append('')

        # Clasificación por puntos esperados (xPts)
        xpts = s.get('xpts_standings')
        if xpts is not None and not xpts.empty:
            lines.append('Clasificación por puntos esperados (xPts)')
            lines.append('------------------------------------------')
            lines.append(f'  {"Pos":>3}  {"Equipo":<25} {"PJ":>3} {"xPts":>6} {"PTS":>4} {"Dif":>5}')
            lines.append(f'  {"---":>3}  {"-"*25} {"--":>3} {"----":>6} {"---":>4} {"---":>5}')
            for _, row in xpts.iterrows():
                diff = row['Diff']
                diff_str = f'+{diff:.1f}' if diff > 0 else f'{diff:.1f}'
                lines.append(
                    f'  {int(row["Pos"]):>3}  {row["Equipo"]:<25} {int(row["PJ"]):>3}'
                    f' {row["xPts"]:>6.1f} {int(row["PTS"]):>4} {diff_str:>5}'
                )
            lines.append('')

        # Rendimiento local/visitante
        lines.append('Rendimiento local vs visitante')
        lines.append('------------------------------')
        ha = s['home_away']
        lines.append(f'  {"Equipo":<25} {"PJ_L":>5} {"Pts_L":>6}  {"PJ_V":>5} {"Pts_V":>6}')
        lines.append(f'  {"-"*25} {"----":>5} {"-----":>6}  {"----":>5} {"-----":>6}')
        for _, row in ha.iterrows():
            lines.append(
                f'  {row["Equipo"]:<25} {int(row["PJ_L"]):>5} {int(row["Pts_L"]):>6}'
                f'  {int(row["PJ_V"]):>5} {int(row["Pts_V"]):>6}'
            )

        # 5.1 Conclusiones automáticas (modo liga)
        lines.extend(self._generate_conclusions())

        # 5.2 Narrativa intertemporada (si --seasons)
        lines.extend(self._generate_interseason_narrative())

        report_text = '\n'.join(lines)
        if output_path:
            out = Path(output_path)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(report_text, encoding='utf-8')
        return report_text

    def _generate_liga_html_report(self, output_path: str, image_folder: Optional[str] = None) -> str:
        """Informe HTML para el modo Liga."""
        s = self.liga_summary
        report_file = Path(output_path)
        report_file.parent.mkdir(parents=True, exist_ok=True)

        image_folder_path = Path(image_folder) if image_folder else report_file.parent
        image_folder_path.mkdir(parents=True, exist_ok=True)
        images = self.save_visual_report(str(image_folder_path))
        relative_images = [
            Path(os.path.relpath(img, start=report_file.parent)).as_posix()
            for img in images if img
        ]

        pmg = s['partido_mas_goleador']
        r = s['records']

        html = [
            '<!DOCTYPE html>',
            '<html lang="es">',
            '<head>',
            '  <meta charset="UTF-8">',
            '  <meta name="viewport" content="width=device-width, initial-scale=1.0">',
            f'  <title>{s["competition"]} {s["season"]}</title>',
            '  <style>',
            '    body { font-family: Arial, sans-serif; margin: 24px; background: #f7f8fb; color: #222; }',
            '    h1 { color: #1f4e79; } h2 { color: #2c7bb6; border-bottom: 2px solid #d0e4f7; padding-bottom: 4px; }',
            '    .header-box { background: #1f4e79; color: white; border-radius: 12px;',
            '      padding: 20px 28px; margin-bottom: 24px; }',
            '    .header-box h1 { color: white; margin: 0 0 8px 0; }',
            '    .kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; margin-bottom: 24px; }',
            '    .kpi { background: white; padding: 16px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); text-align:center; }',
            '    .kpi .val { font-size: 1.8em; font-weight: bold; color: #1f4e79; }',
            '    .kpi .lbl { font-size: 0.85em; color: #666; margin-top: 4px; }',
            '    table { width: 100%; border-collapse: collapse; margin: 12px 0 24px 0; font-size: 0.9em; }',
            '    th, td { padding: 7px 10px; border: 1px solid #d7dbe3; text-align: center; }',
            '    th { background: #e4efff; }',
            '    td.left { text-align: left; }',
            '    tr.ucl td { background: #cce5ff; }',
            '    tr.uel td { background: #d4edda; }',
            '    tr.uecl td { background: #e8f5e9; }',
            '    tr.descenso td { background: #fde8e8; }',
            '    .zona-badge { font-size: 0.7em; vertical-align: middle; margin-left: 4px; opacity: 0.7; }',
            '    .records { background: white; padding: 16px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }',
            '    .records ul { margin: 0; padding-left: 20px; line-height: 1.8; }',
            '    img { max-width: 100%; border-radius: 8px; margin: 8px 0; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }',
            '    .charts { display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 16px; }',
            '  </style>',
            '</head>',
            '<body>',
            f'  <div class="header-box">',
            *(
                [f'    <h1>{s["competition"]} — {s["season"]} &nbsp;<small style="font-size:0.6em;opacity:0.85">Jornadas {self.matchday_range[0]}–{self.matchday_range[1]}</small></h1>']
                if self.matchday_range else
                [f'    <h1>{s["competition"]} — {s["season"]}</h1>']
            ),
            f'    <p>Jornadas: {s["jornadas"]} &nbsp;|&nbsp; Partidos: {s["partidos_totales"]}</p>',
            '  </div>',

            # KPIs
            '  <div class="kpi-grid">',
            f'    <div class="kpi"><div class="val">{s["goles_totales"]}</div><div class="lbl">Goles totales</div></div>',
            f'    <div class="kpi"><div class="val">{s["goles_promedio"]}</div><div class="lbl">Goles por partido</div></div>',
            f'    <div class="kpi"><div class="val">{pmg["local"]} {pmg["goles_l"]}-{pmg["goles_v"]} {pmg["visitante"]}</div><div class="lbl">Partido más goleador</div></div>',
            f'    <div class="kpi"><div class="val">{r["equipo_mas_goleador"]}</div><div class="lbl">Equipo más goleador</div></div>',
            f'    <div class="kpi"><div class="val">{r["equipo_menos_goleado"]}</div><div class="lbl">Menos goleado</div></div>',
            '  </div>',

            # Récords
            '  <h2>Récords de la temporada</h2>',
            '  <div class="records"><ul>',
            f'    <li><strong>Mejor racha:</strong> {r["equipo_mejor_racha"]} — {r["mejor_racha_victorias"]} victorias consecutivas</li>',
        ]
        if r['arbitro_top']:
            html.append(f'    <li><strong>Árbitro más activo:</strong> {r["arbitro_top"]["nombre"]} ({r["arbitro_top"]["partidos"]} partidos)</li>')
        if r['partido_max_asistencia']:
            pa = r['partido_max_asistencia']
            html.append(f'    <li><strong>Mayor asistencia:</strong> {pa["local"]} vs {pa["visitante"]} — {pa["espectadores"]:,} espectadores ({pa["estadio"]})</li>')
        html.extend(['  </ul></div>'])

        # Clasificación
        clf = s['clasificacion']
        total_teams = len(clf)
        html.extend([
            '  <h2>Clasificación</h2>',
            '  <table>',
            '    <thead><tr><th>Pos</th><th class="left">Equipo</th><th>PJ</th><th>G</th><th>E</th><th>P</th><th>GF</th><th>GC</th><th>DIF</th><th>PTS</th></tr></thead>',
            '    <tbody>',
        ])
        for _, row in clf.iterrows():
            pos = int(row['Pos'])
            dif = f'+{int(row["DIF"])}' if row['DIF'] > 0 else str(int(row['DIF']))
            if pos <= 4:
                tr_class = ' class="ucl"'
                badge = ' <span class="zona-badge" title="Champions League">🏦</span>'
            elif pos <= 6:
                tr_class = ' class="uel"'
                badge = ' <span class="zona-badge" title="Europa League">🌟</span>'
            elif pos == 7:
                tr_class = ' class="uecl"'
                badge = ' <span class="zona-badge" title="Conference League">🌿</span>'
            elif pos >= total_teams - 2:
                tr_class = ' class="descenso"'
                badge = ' <span class="zona-badge" title="Descenso">⬇️</span>'
            else:
                tr_class = ''
                badge = ''
            html.append(
                f'      <tr{tr_class}><td>{pos}</td>'
                f'<td class="left"><strong>{row["Equipo"]}</strong>{badge}</td>'
                f'<td>{int(row["PJ"])}</td><td>{int(row["G"])}</td><td>{int(row["E"])}</td><td>{int(row["P"])}</td>'
                f'<td>{int(row["GF"])}</td><td>{int(row["GC"])}</td><td>{dif}</td><td><strong>{int(row["PTS"])}</strong></td></tr>'
            )
        html.extend(['    </tbody>', '  </table>'])

        # Stats técnicas por equipo
        st = s['stats_por_equipo']
        html.extend([
            '  <h2>Estadísticas técnicas por equipo</h2>',
            '  <table>',
            '    <thead><tr><th class="left">Equipo</th><th>GF</th><th>GC</th><th>xG medio</th><th>Over%</th><th>Posesión %</th><th>Tiros/partido</th></tr></thead>',
            '    <tbody>',
        ])
        for _, row in st.iterrows():
            xg  = f'{row["xG"]:.2f}' if pd.notna(row.get('xG')) and row.get('xG') is not None else '-'
            over = f'{row["Over%"]:.2f}' if pd.notna(row.get('Over%')) and row.get('Over%') is not None else '-'
            pos = f'{row["Pos%"]:.1f}' if pd.notna(row.get('Pos%')) and row.get('Pos%') is not None else '-'
            tir = f'{row["Tiros"]:.1f}' if pd.notna(row.get('Tiros')) and row.get('Tiros') is not None else '-'
            over_val = row.get('Over%')
            over_color = ''
            if pd.notna(over_val) and over_val is not None:
                over_color = ' style="color:#27ae60;font-weight:bold"' if over_val > 1.2 else (' style="color:#e74c3c;font-weight:bold"' if over_val < 0.8 else '')
            html.append(
                f'      <tr><td class="left">{row["Equipo"]}</td>'
                f'<td>{int(row["GF"])}</td><td>{int(row["GC"])}</td>'
                f'<td>{xg}</td><td{over_color}>{over}</td><td>{pos}</td><td>{tir}</td></tr>'
            )
        html.extend(['    </tbody>', '  </table>'])

        # Clasificación por puntos esperados (xPts)
        xpts = s.get('xpts_standings')
        if xpts is not None and not xpts.empty:
            html.extend([
                '  <h2>Clasificación por puntos esperados <small style="color:#666;font-size:0.6em">(modelo Poisson sobre xG)</small></h2>',
                '  <p style="color:#666;font-size:0.85em;margin-top:-8px">Diferencia positiva = equipo puntúa más de lo que sus xG sugieren (suerte/eficiencia). Diferencia negativa = infrarendimiento.</p>',
                '  <table>',
                '    <thead><tr><th>Pos</th><th class="left">Equipo</th><th>PJ</th><th>xPts</th><th>PTS reales</th><th>Diferencia</th></tr></thead>',
                '    <tbody>',
            ])
            for _, row in xpts.iterrows():
                diff = row['Diff']
                if diff > 2:
                    diff_color = ' style="color:#27ae60;font-weight:bold"'
                    diff_str = f'+{diff:.1f}'
                elif diff < -2:
                    diff_color = ' style="color:#e74c3c;font-weight:bold"'
                    diff_str = f'{diff:.1f}'
                else:
                    diff_color = ' style="color:#666"'
                    diff_str = f'+{diff:.1f}' if diff >= 0 else f'{diff:.1f}'
                html.append(
                    f'      <tr><td>{int(row["Pos"])}</td>'
                    f'<td class="left">{row["Equipo"]}</td>'
                    f'<td>{int(row["PJ"])}</td>'
                    f'<td><strong>{row["xPts"]:.1f}</strong></td>'
                    f'<td>{int(row["PTS"])}</td>'
                    f'<td{diff_color}>{diff_str}</td></tr>'
                )
            html.extend(['    </tbody>', '  </table>'])

        # Rendimiento local/visitante
        ha = s['home_away']
        html.extend([
            '  <h2>Rendimiento local vs visitante</h2>',
            '  <table>',
            '    <thead><tr><th class="left">Equipo</th><th>PJ Local</th><th>Pts Local</th><th>PJ Visit.</th><th>Pts Visit.</th></tr></thead>',
            '    <tbody>',
        ])
        for _, row in ha.iterrows():
            html.append(
                f'      <tr><td class="left">{row["Equipo"]}</td>'
                f'<td>{int(row["PJ_L"])}</td><td><strong>{int(row["Pts_L"])}</strong></td>'
                f'<td>{int(row["PJ_V"])}</td><td><strong>{int(row["Pts_V"])}</strong></td></tr>'
            )
        html.extend(['    </tbody>', '  </table>'])

        if relative_images:
            html.extend(['  <h2>Gráficos</h2>', '  <div class="charts">'])
            for img in relative_images:
                html.append(f'    <img src="{img}" alt="Gráfico de liga">')
            html.append('  </div>')

        conclusions_html = self._generate_conclusions_html()
        if conclusions_html:
            html.append(conclusions_html)

        interseason = self._generate_interseason_narrative()
        if interseason:
            html.append('  <h2>Evolución intertemporada</h2>')
            html.append('  <div style="background:white;border-radius:8px;padding:16px 20px;'
                        'box-shadow:0 2px 8px rgba(0,0,0,0.08);margin-bottom:24px;">')
            html.append('  <pre style="font-family:monospace;font-size:0.88em;margin:0;">')
            html.append('\n'.join(interseason))
            html.append('  </pre></div>')

        html.extend(['</body>', '</html>'])
        report_file.write_text('\n'.join(html), encoding='utf-8')
        return str(report_file)

    def _generate_match_report(self, output_path: Optional[str] = None) -> str:
        """Informe de texto para el modo Partido."""
        m = self.match_detail
        lines: List[str] = []
        title = f'FICHA DEL PARTIDO — {m["local"]} vs {m["visitante"]}'
        lines.append(title)
        lines.append('=' * len(title))
        lines.append(f'Fecha:       {m["fecha"]}')
        if m['jornada']:
            lines.append(f'Jornada:     {m["jornada"]}')
        lines.append(f'Competición: {m["competition"]}  |  Temporada: {m["season"]}')
        if m['estadio'] != '-':
            lines.append(f'Estadio:     {m["estadio"]}')
        if m['arbitro'] != '-':
            lines.append(f'Árbitro:     {m["arbitro"]}')
        if m['espectadores']:
            lines.append(f'Espectadores: {m["espectadores"]:,}')
        lines.append('')

        resultado_str = (
            'Victoria local' if m['resultado'] == 'local'
            else 'Victoria visitante' if m['resultado'] == 'visitante'
            else 'Empate'
        )
        lines.append(f'  {m["local"]:<25}  {m["goles_local"]:>2}  -  {m["goles_visitante"]:<2}  {m["visitante"]}')
        lines.append(f'  Resultado: {resultado_str}')
        lines.append('')

        # Contexto en la liga
        cl = m.get('contexto_local')
        cv = m.get('contexto_visitante')
        if cl or cv:
            lines.append('Contexto (clasificación antes del partido)')
            lines.append('------------------------------------------')
            if cl:
                lines.append(
                    f'  {m["local"]:<25}  Pos {cl["pos"]:>2} | {cl["pts"]} pts | '
                    f'{cl["pj"]} PJ | {cl["gf"]} GF {cl["gc"]} GC'
                )
            if cv:
                lines.append(
                    f'  {m["visitante"]:<25}  Pos {cv["pos"]:>2} | {cv["pts"]} pts | '
                    f'{cv["pj"]} PJ | {cv["gf"]} GF {cv["gc"]} GC'
                )
            lines.append('')

        if m['stats']:
            lines.append('Estadísticas cara a cara')
            lines.append('------------------------')
            lines.append(f'  {"Estadística":^22} {"Local":>8}  {"Visitante":>9}')
            lines.append(f'  {"-"*22} {"-"*8}  {"-"*9}')
            for s in m['stats']:
                lines.append(f'  {s["stat"]:^22} {s["local"]:>8}  {s["visitante"]:>9}')
            lines.append('')

        lines.append('Análisis')
        lines.append('--------')
        lines.append(f'  {m["narrativa"]}')
        lines.append('')

        if m.get('video_highlights'):
            lines.append(f'Highlights: {m["video_highlights"]}')

        report_text = '\n'.join(lines)
        if output_path:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(report_text, encoding='utf-8')
        return report_text

    def _generate_match_html_report(self, output_path: str, image_folder: Optional[str] = None) -> str:
        """Informe HTML para el modo Partido."""
        m = self.match_detail
        report_file = Path(output_path)
        report_file.parent.mkdir(parents=True, exist_ok=True)

        image_folder_path = Path(image_folder) if image_folder else report_file.parent
        image_folder_path.mkdir(parents=True, exist_ok=True)
        images = self.save_visual_report(str(image_folder_path))
        relative_images = [
            Path(os.path.relpath(img, start=report_file.parent)).as_posix()
            for img in images if img
        ]

        resultado_str = (
            'Victoria local' if m['resultado'] == 'local'
            else 'Victoria visitante' if m['resultado'] == 'visitante'
            else 'Empate'
        )
        color_res = '#27ae60' if m['resultado'] == 'local' else ('#e74c3c' if m['resultado'] == 'visitante' else '#f39c12')

        html = [
            '<!DOCTYPE html>',
            '<html lang="es">',
            '<head>',
            '  <meta charset="UTF-8">',
            '  <meta name="viewport" content="width=device-width, initial-scale=1.0">',
            f'  <title>{m["local"]} vs {m["visitante"]}</title>',
            '  <style>',
            '    body { font-family: Arial, sans-serif; margin: 24px; background: #f7f8fb; color: #222; }',
            '    h1, h2 { color: #1f4e79; }',
            '    .section { margin-bottom: 24px; }',
            '    .scoreboard { text-align: center; background: white; border-radius: 12px;',
            '      padding: 24px; box-shadow: 0 2px 12px rgba(0,0,0,0.1); margin-bottom: 24px; }',
            '    .score { font-size: 3em; font-weight: bold; color: #1f4e79; }',
            '    .teams { font-size: 1.3em; margin-bottom: 8px; }',
            '    .result-badge { display: inline-block; padding: 4px 16px; border-radius: 20px;',
            f'      background: {color_res}; color: white; font-weight: bold; margin-top: 8px; }}',
            '    .metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; }',
            '    .metric { background: white; padding: 16px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }',
            '    table { width: 100%; border-collapse: collapse; margin-top: 12px; }',
            '    th, td { padding: 8px 10px; border: 1px solid #d7dbe3; text-align: center; }',
            '    th { background: #e4efff; }',
            '    td.stat-name { text-align: center; font-weight: bold; }',
            '    .adv-local { background: #d4edfa; }',
            '    .adv-visit { background: #fde8e8; }',
            '    .narrativa { background: white; padding: 16px; border-radius: 8px;',
            '      box-shadow: 0 2px 8px rgba(0,0,0,0.08); font-style: italic; line-height: 1.6; }',
            '    img { max-width: 100%; border-radius: 8px; margin-top: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }',
            '  </style>',
            '</head>',
            '<body>',
            '  <div class="scoreboard">',
            f'    <div class="teams"><strong>{m["local"]}</strong> vs <strong>{m["visitante"]}</strong></div>',
            f'    <div class="score">{m["goles_local"]} — {m["goles_visitante"]}</div>',
            f'    <div class="result-badge">{resultado_str}</div>',
            '  </div>',
            '  <div class="section">',
            '    <h2>Datos del partido</h2>',
            '    <div class="metrics">',
            f'      <div class="metric"><strong>Fecha</strong><p>{m["fecha"][:10]}</p></div>',
        ]
        if m['jornada']:
            html.append(f'      <div class="metric"><strong>Jornada</strong><p>{m["jornada"]}</p></div>')
        html.append(f'      <div class="metric"><strong>Competición</strong><p>{m["competition"]}</p></div>')
        html.append(f'      <div class="metric"><strong>Temporada</strong><p>{m["season"]}</p></div>')
        if m['estadio'] != '-':
            html.append(f'      <div class="metric"><strong>Estadio</strong><p>{m["estadio"]}</p></div>')
        if m['arbitro'] != '-':
            html.append(f'      <div class="metric"><strong>Árbitro</strong><p>{m["arbitro"]}</p></div>')
        if m['espectadores']:
            html.append(f'      <div class="metric"><strong>Espectadores</strong><p>{m["espectadores"]:,}</p></div>')
        html.extend(['    </div>', '  </div>'])

        # Contexto clasificatorio
        cl = m.get('contexto_local')
        cv = m.get('contexto_visitante')
        if cl or cv:
            html.extend([
                '  <div class="section">',
                '    <h2>Clasificación previa</h2>',
                '    <table>',
                '      <thead><tr><th>Equipo</th><th>Pos</th><th>PJ</th><th>PTS</th><th>GF</th><th>GC</th></tr></thead>',
                '      <tbody>',
            ])
            if cl:
                html.append(
                    f'        <tr><td class="adv-local"><strong>{m["local"]}</strong></td>'
                    f'<td>{cl["pos"]}</td><td>{cl["pj"]}</td>'
                    f'<td><strong>{cl["pts"]}</strong></td><td>{cl["gf"]}</td><td>{cl["gc"]}</td></tr>'
                )
            if cv:
                html.append(
                    f'        <tr><td class="adv-visit"><strong>{m["visitante"]}</strong></td>'
                    f'<td>{cv["pos"]}</td><td>{cv["pj"]}</td>'
                    f'<td><strong>{cv["pts"]}</strong></td><td>{cv["gf"]}</td><td>{cv["gc"]}</td></tr>'
                )
            html.extend(['      </tbody>', '    </table>', '  </div>'])

        # Stats cara a cara
        if m['stats']:
            html.extend([
                '  <div class="section">',
                '    <h2>Estadísticas cara a cara</h2>',
                '    <table>',
                f'      <thead><tr><th>{m["local"]}</th><th class="stat-name">Estadística</th><th>{m["visitante"]}</th></tr></thead>',
                '      <tbody>',
            ])
            for s in m['stats']:
                css = 'adv-local' if s['ventaja'] == 'local' else ('adv-visit' if s['ventaja'] == 'visitante' else '')
                css_l = f' class="{css}"' if s['ventaja'] == 'local' else ''
                css_v = f' class="{css}"' if s['ventaja'] == 'visitante' else ''
                html.append(
                    f'        <tr>'
                    f'<td{css_l}><strong>{s["local"]}</strong></td>'
                    f'<td class="stat-name">{s["stat"]}</td>'
                    f'<td{css_v}><strong>{s["visitante"]}</strong></td>'
                    f'</tr>'
                )
            html.extend(['      </tbody>', '    </table>', '  </div>'])

        # Narrativa
        html.extend([
            '  <div class="section">',
            '    <h2>Análisis del partido</h2>',
            f'    <p class="narrativa">{m["narrativa"]}</p>',
            '  </div>',
        ])

        if m.get('video_highlights'):
            html.extend([
                '  <div class="section">',
                '    <h2>Highlights</h2>',
                f'    <p><a href="{m["video_highlights"]}" target="_blank">Ver highlights del partido</a></p>',
                '  </div>',
            ])

        if relative_images:
            html.extend(['  <div class="section">', '    <h2>Gráficos</h2>'])
            for img in relative_images:
                html.append(f'    <img src="{img}" alt="Gráfico del partido">')
            html.append('  </div>')

        html.extend(['</body>', '</html>'])
        report_file.write_text('\n'.join(html), encoding='utf-8')
        return str(report_file)

    def _generate_matchday_report(self, output_path: Optional[str] = None) -> str:
        """Informe de texto para el modo Jornada."""
        s = self.matchday_summary
        lines: List[str] = []
        lines.append(f'INFORME DE JORNADA {s["jornada"]}')
        lines.append('=' * 35)
        if self.season:
            lines.append(f'Temporada: {self.season}')
        lines.append(f'Partidos disputados: {s["num_partidos"]}')
        lines.append('')

        res_label = {'L': 'Victoria local', 'E': 'Empate', 'V': 'Victoria visitante'}
        lines.append('Resultados')
        lines.append('----------')
        for r in s['results']:
            label = res_label.get(r['resultado'], '')
            lines.append(
                f"  {r['local']:<22}  {r['goles_local']:>2} - {r['goles_visitante']:<2}"
                f"  {r['visitante']:<22}  ({label})"
            )
        lines.append('')

        lines.append('Estadísticas de la jornada')
        lines.append('--------------------------')
        lines.append(f"  Goles totales: {s['total_goals']}")
        lines.append(f"  Goles por partido: {s['avg_goals']:.2f}")
        if s['total_yellow'] is not None:
            lines.append(f"  Tarjetas amarillas: {s['total_yellow']}")
        if s['total_red'] is not None:
            lines.append(f"  Tarjetas rojas: {s['total_red']}")
        if s['avg_possession_local'] is not None:
            lines.append(f"  Posesión media local: {s['avg_possession_local']:.1f}%")
            lines.append(f"  Posesión media visitante: {s['avg_possession_visitante']:.1f}%")
        lines.append('')

        if s['most_exciting']:
            m = s['most_exciting']
            lines.append('Partido más espectacular')
            lines.append('------------------------')
            lines.append(
                f"  {m['local']} {m['goles_local']} - {m['goles_visitante']} {m['visitante']}"
                f"  ({m['goles_totales']} goles)"
            )
            lines.append('')

        if s['xg_surprise']:
            sx = s['xg_surprise']
            lines.append('Sorpresa de la jornada (resultado vs xG esperado)')
            lines.append('-------------------------------------------------')
            lines.append(
                f"  {sx['local']} {sx['goles_local']} - {sx['goles_visitante']} {sx['visitante']}"
            )
            lines.append(
                f"  xG: {sx['local'][:15]} {sx['xg_local']} | {sx['xg_visitante']} {sx['visitante'][:15]}"
            )
            lines.append('')

        if not s['standings'].empty:
            lines.append(f"Clasificación tras la jornada {s['jornada']}")
            lines.append('-' * 40)
            lines.extend(s['standings'].to_string(index=False).splitlines())
            lines.append('')

        report_text = '\n'.join(lines)
        if output_path:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(report_text, encoding='utf-8')
        return report_text

    def _generate_matchday_html_report(self, output_path: str, image_folder: Optional[str] = None) -> str:
        """Informe HTML para el modo Jornada."""
        s = self.matchday_summary
        report_file = Path(output_path)
        report_file.parent.mkdir(parents=True, exist_ok=True)

        image_folder_path = Path(image_folder) if image_folder else report_file.parent
        image_folder_path.mkdir(parents=True, exist_ok=True)
        images = self.save_visual_report(str(image_folder_path))
        relative_images = [
            Path(os.path.relpath(img, start=report_file.parent)).as_posix()
            for img in images if img
        ]

        res_bg    = {'L': '#d4edda', 'E': '#fff3cd', 'V': '#f8d7da'}
        res_label = {'L': 'Victoria local', 'E': 'Empate', 'V': 'Victoria visitante'}

        html = [
            '<!DOCTYPE html>',
            '<html lang="es">',
            '<head>',
            '  <meta charset="UTF-8">',
            '  <meta name="viewport" content="width=device-width, initial-scale=1.0">',
            f'  <title>Jornada {s["jornada"]}</title>',
            '  <style>',
            '    body { font-family: Arial, sans-serif; margin: 24px; background: #f7f8fb; color: #222; }',
            '    h1, h2 { color: #1f4e79; }',
            '    .section { margin-bottom: 24px; }',
            '    .metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; }',
            '    .metric { background: white; padding: 16px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }',
            '    table { width: 100%; border-collapse: collapse; margin-top: 12px; }',
            '    th, td { padding: 8px 10px; border: 1px solid #d7dbe3; text-align: left; }',
            '    th { background: #e4efff; }',
            '    .score { font-size: 1.2em; font-weight: bold; text-align: center; }',
            '    img { max-width: 100%; border-radius: 8px; margin-top: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }',
            '  </style>',
            '</head>',
            '<body>',
            f'  <h1>Jornada {s["jornada"]}</h1>',
        ]

        if self.season:
            html.append(
                f'  <p><strong>Temporada:</strong> {self.season}'
                f' &nbsp; <strong>Partidos disputados:</strong> {s["num_partidos"]}</p>'
            )

        # Tarjetas de estadísticas
        html.extend([
            '  <div class="section">',
            '    <h2>Estadísticas de la jornada</h2>',
            '    <div class="metrics">',
            f'      <div class="metric"><strong>Goles totales</strong>'
            f'<p style="font-size:1.4em;font-weight:bold">{s["total_goals"]}</p></div>',
            f'      <div class="metric"><strong>Goles por partido</strong>'
            f'<p style="font-size:1.4em;font-weight:bold">{s["avg_goals"]:.2f}</p></div>',
        ])
        if s['total_yellow'] is not None:
            html.append(
                f'      <div class="metric"><strong>Tarjetas amarillas</strong>'
                f'<p style="font-size:1.4em;font-weight:bold">{s["total_yellow"]}</p></div>'
            )
        if s['total_red'] is not None:
            html.append(
                f'      <div class="metric"><strong>Tarjetas rojas</strong>'
                f'<p style="font-size:1.4em;font-weight:bold">{s["total_red"]}</p></div>'
            )
        if s['avg_possession_local'] is not None:
            html.append(
                f'      <div class="metric"><strong>Posesión media local</strong>'
                f'<p>{s["avg_possession_local"]:.1f}%</p></div>'
            )
            html.append(
                f'      <div class="metric"><strong>Posesión media visitante</strong>'
                f'<p>{s["avg_possession_visitante"]:.1f}%</p></div>'
            )
        html.extend(['    </div>', '  </div>'])

        # Tabla de resultados
        html.extend([
            '  <div class="section">',
            '    <h2>Resultados</h2>',
            '    <table>',
            '      <thead><tr>'
            '<th>Local</th><th class="score">Marcador</th><th>Visitante</th><th>Tipo</th>'
            '</tr></thead>',
            '      <tbody>',
        ])
        for r in s['results']:
            bg    = res_bg.get(r['resultado'], 'white')
            label = res_label.get(r['resultado'], '')
            html.append(
                f'        <tr style="background:{bg}">'
                f'<td><strong>{r["local"]}</strong></td>'
                f'<td class="score">{r["goles_local"]} - {r["goles_visitante"]}</td>'
                f'<td><strong>{r["visitante"]}</strong></td>'
                f'<td>{label}</td>'
                f'</tr>'
            )
        html.extend(['      </tbody>', '    </table>', '  </div>'])

        # Datos destacados
        if s['most_exciting'] or s['xg_surprise']:
            html.extend(['  <div class="section">', '    <h2>Datos destacados</h2>'])
            if s['most_exciting']:
                m = s['most_exciting']
                html.append(
                    f'    <p><strong>Partido más espectacular:</strong> '
                    f'{m["local"]} <strong>{m["goles_local"]} - {m["goles_visitante"]}</strong>'
                    f' {m["visitante"]} <em>({m["goles_totales"]} goles)</em></p>'
                )
            if s['xg_surprise']:
                sx = s['xg_surprise']
                html.append(
                    f'    <p><strong>Sorpresa de la jornada (resultado vs xG):</strong> '
                    f'{sx["local"]} <strong>{sx["goles_local"]} - {sx["goles_visitante"]}</strong>'
                    f' {sx["visitante"]} &mdash; xG esperado: {sx["local"][:15]}'
                    f' <em>{sx["xg_local"]}</em> - <em>{sx["xg_visitante"]}</em>'
                    f' {sx["visitante"][:15]}</p>'
                )
            html.append('  </div>')

        # Clasificación acumulada
        if not s['standings'].empty:
            html.extend([
                '  <div class="section">',
                f'    <h2>Clasificación tras la jornada {s["jornada"]}</h2>',
                s['standings'].to_html(index=False, classes='dataframe', border=0),
                '  </div>',
            ])

        # Gráficos
        if relative_images:
            html.extend(['  <div class="section">', '    <h2>Gráficos</h2>'])
            jornada_num = s['jornada']
            for img in relative_images:
                html.append(f'    <img src="{img}" alt="Gráfico jornada {jornada_num}">')
            html.append('  </div>')

        html.extend(['</body>', '</html>'])
        report_file.write_text('\n'.join(html), encoding='utf-8')
        return str(report_file)

    def _generate_player_report(self, output_path: Optional[str] = None) -> str:
        """Informe de texto para el modo Jugador."""
        p = self.player_profile
        lines: List[str] = []

        if not p.get('found'):
            msg = f'No se encontró al jugador: {self.player}'
            if output_path:
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                Path(output_path).write_text(msg, encoding='utf-8')
            return msg

        title = f'INFORME DE JUGADOR — {p["player_name"]}  |  {p["team"]}'
        lines.append(title)
        lines.append('=' * len(title))
        lines.append(f'Posición:    {p["position"]}')
        lines.append(f'Temporada:   {p["season"]}')
        lines.append('')

        lines.append('Estadísticas de temporada')
        lines.append('-------------------------')
        lines.append(f'  Partidos jugados:     {p["appearances"]}')
        lines.append(f'  Goles:                {p["goals"]}')
        lines.append(f'  Asistencias:          {p["assists"]}')
        lines.append(f'  Goles + Asistencias:  {p["ga"]}')
        lines.append(f'  Tiros a puerta:       {p["shots_on_target"]}')
        lines.append(f'  Tarjetas amarillas:   {p["yellow_cards"]}')
        lines.append(f'  Tarjetas rojas:       {p["red_cards"]}')
        lines.append('')

        lines.append('Rendimiento por partido')
        lines.append('-----------------------')
        lines.append(f'  Goles/PJ:             {p["goles_por_partido"]:.3f}')
        lines.append(f'  Asistencias/PJ:       {p["asistencias_por_partido"]:.3f}')
        lines.append(f'  G+A/PJ:               {p["ga_por_partido"]:.3f}')
        lines.append(f'  % partidos con gol:   {p["pct_partidos_con_gol"]:.1f}%')
        lines.append(f'  % partidos con G+A:   {p["pct_partidos_con_ga"]:.1f}%')
        lines.append('')

        lines.append('Ranking en el equipo')
        lines.append('--------------------')
        lines.append(f'  Pos. goleadores:      #{p["ranking_goles"]}')
        lines.append(f'  Pos. asistentes:      #{p["ranking_asistencias"]}')
        lines.append('')

        top_g = p.get('compañeros_goleadores')
        if top_g is not None and not top_g.empty:
            lines.append('Top 5 goleadores del equipo')
            lines.extend(top_g.to_string(index=False).splitlines())
            lines.append('')

        top_a = p.get('compañeros_asistentes')
        if top_a is not None and not top_a.empty:
            lines.append('Top 5 asistentes del equipo')
            lines.extend(top_a.to_string(index=False).splitlines())
            lines.append('')

        report_text = '\n'.join(lines)
        if output_path:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            Path(output_path).write_text(report_text, encoding='utf-8')
        return report_text

    def _generate_player_html_report(self, output_path: str, image_folder: Optional[str] = None) -> str:
        """Informe HTML para el modo Jugador."""
        p = self.player_profile
        report_file = Path(output_path)
        report_file.parent.mkdir(parents=True, exist_ok=True)

        if not p.get('found'):
            report_file.write_text(f'<p>No se encontró al jugador: {self.player}</p>', encoding='utf-8')
            return str(report_file)

        image_folder_path = Path(image_folder) if image_folder else report_file.parent
        image_folder_path.mkdir(parents=True, exist_ok=True)
        images = self.save_visual_report(str(image_folder_path))
        relative_images = [
            Path(os.path.relpath(img, start=report_file.parent)).as_posix()
            for img in images if img
        ]

        top_g = p.get('compañeros_goleadores')
        top_a = p.get('compañeros_asistentes')

        html = [
            '<!DOCTYPE html>',
            '<html lang="es">',
            '<head>',
            '  <meta charset="UTF-8">',
            '  <meta name="viewport" content="width=device-width, initial-scale=1.0">',
            f'  <title>{p["player_name"]} — {p["team"]}</title>',
            '  <style>',
            '    body { font-family: Arial, sans-serif; margin: 24px; background: #f7f8fb; color: #222; }',
            '    h1 { color: #1f4e79; } h2 { color: #2c7bb6; border-bottom: 2px solid #d0e4f7; padding-bottom: 4px; }',
            '    .header-box { background: #1f4e79; color: white; border-radius: 12px; padding: 20px 28px; margin-bottom: 24px; }',
            '    .header-box h1 { color: white; margin: 0 0 8px 0; }',
            '    .kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 12px; margin-bottom: 24px; }',
            '    .kpi { background: white; padding: 16px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); text-align: center; }',
            '    .kpi .val { font-size: 2em; font-weight: bold; color: #1f4e79; }',
            '    .kpi .lbl { font-size: 0.82em; color: #666; margin-top: 4px; }',
            '    .rank-badge { display: inline-block; background: #e4efff; border-radius: 20px; padding: 3px 14px; font-weight: bold; color: #1f4e79; margin: 4px; }',
            '    table { width: 100%; border-collapse: collapse; margin: 10px 0 20px 0; font-size: 0.9em; }',
            '    th, td { padding: 7px 10px; border: 1px solid #d7dbe3; text-align: center; }',
            '    th { background: #e4efff; }',
            '    td.left { text-align: left; }',
            '    img { max-width: 100%; border-radius: 8px; margin: 8px 0; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }',
            '    .charts { display: grid; grid-template-columns: repeat(auto-fit, minmax(380px, 1fr)); gap: 16px; }',
            '  </style>',
            '</head>',
            '<body>',
            f'  <div class="header-box">',
            f'    <h1>{p["player_name"]}</h1>',
            f'    <p>{p["team"]} &nbsp;|&nbsp; {p["position"]} &nbsp;|&nbsp; Temporada {p["season"]}</p>',
            '  </div>',

            '  <div class="kpi-grid">',
            f'    <div class="kpi"><div class="val">{p["appearances"]}</div><div class="lbl">PJ</div></div>',
            f'    <div class="kpi"><div class="val">{p["goals"]}</div><div class="lbl">Goles</div></div>',
            f'    <div class="kpi"><div class="val">{p["assists"]}</div><div class="lbl">Asistencias</div></div>',
            f'    <div class="kpi"><div class="val">{p["ga"]}</div><div class="lbl">G+A</div></div>',
            f'    <div class="kpi"><div class="val">{p["shots_on_target"]}</div><div class="lbl">Tiros a puerta</div></div>',
            f'    <div class="kpi"><div class="val">{p["yellow_cards"]}</div><div class="lbl">Amarillas</div></div>',
            f'    <div class="kpi"><div class="val">{p["red_cards"]}</div><div class="lbl">Rojas</div></div>',
            '  </div>',

            '  <h2>Rendimiento por partido</h2>',
            '  <div class="kpi-grid">',
            f'    <div class="kpi"><div class="val">{p["goles_por_partido"]:.2f}</div><div class="lbl">Goles/PJ</div></div>',
            f'    <div class="kpi"><div class="val">{p["asistencias_por_partido"]:.2f}</div><div class="lbl">Asist/PJ</div></div>',
            f'    <div class="kpi"><div class="val">{p["ga_por_partido"]:.2f}</div><div class="lbl">G+A/PJ</div></div>',
            f'    <div class="kpi"><div class="val">{p["pct_partidos_con_gol"]:.0f}%</div><div class="lbl">% con gol</div></div>',
            f'    <div class="kpi"><div class="val">{p["pct_partidos_con_ga"]:.0f}%</div><div class="lbl">% con G+A</div></div>',
            '  </div>',

            '  <h2>Ranking en el equipo</h2>',
            f'  <p><span class="rank-badge">#{p["ranking_goles"]} goleador</span>'
            f' <span class="rank-badge">#{p["ranking_asistencias"]} asistente</span></p>',
        ]

        if top_g is not None and not top_g.empty:
            html.extend([
                '  <h2>Top 5 goleadores del equipo</h2>',
                top_g.to_html(index=False, classes='dataframe', border=0),
            ])
        if top_a is not None and not top_a.empty:
            html.extend([
                '  <h2>Top 5 asistentes del equipo</h2>',
                top_a.to_html(index=False, classes='dataframe', border=0),
            ])

        if relative_images:
            html.extend(['  <h2>Gráficos</h2>', '  <div class="charts">'])
            for img in relative_images:
                html.append(f'    <img src="{img}" alt="Gráfico de jugador">')
            html.append('  </div>')

        html.extend(['</body>', '</html>'])
        report_file.write_text('\n'.join(html), encoding='utf-8')
        return str(report_file)

    def generate_report(self, output_path: Optional[str] = None) -> str:
        if not self.metrics:
            raise ValueError('Ejecute analyze() antes de generar el informe.')
        if self.top_scorers is None or self.top_defenders is None or self.highlights is None:
            raise ValueError('Los resultados del análisis no están disponibles. Ejecute analyze() antes de generar el informe.')

        if self.match_id is not None and self.match_detail:
            return self._generate_match_report(output_path)

        if self.compare is not None and self.compare_data:
            return self._generate_compare_report(output_path)

        if self.matchday is not None and self.matchday_summary:
            return self._generate_matchday_report(output_path)

        if self.player_profile:
            return self._generate_player_report(output_path)

        if self.liga_summary:
            return self._generate_liga_report(output_path)

        report_lines: List[str] = []
        report_lines.append('INFORME DE ANÁLISIS DE PARTIDOS')
        report_lines.append('--------------------------------')
        if self.seasons and len(self.seasons) > 1:
            report_lines.append(f"Temporadas: {', '.join(str(s) for s in self.seasons)}")
        elif self.season:
            report_lines.append(f"Temporada: {self.season}")
        report_lines.append(f"Partidos analizados: {self.metrics['partidos_analizados']}")
        if self.metrics.get('goles_a_favor') is not None:
            report_lines.append(f"Goles a favor: {self.metrics['goles_a_favor']}")
            report_lines.append(f"Goles en contra: {self.metrics['goles_en_contra']}")
            report_lines.append(f"Promedio goles a favor: {self.metrics['goles_a_favor_promedio']:.2f}")
            report_lines.append(f"Promedio goles en contra: {self.metrics['goles_concedidos_promedio']:.2f}")
            report_lines.append(self.format_metric('tarjetas_amarillas_equipo', 'Tarjetas amarillas'))
            report_lines.append(self.format_metric('tarjetas_rojas_equipo', 'Tarjetas rojas'))
        else:
            report_lines.append(f"Goles totales: {self.metrics['goles_totales']}")
            report_lines.append(f"Goles promedio por partido: {self.metrics['goles_promedio_por_partido']:.2f}")
            report_lines.append(self.format_metric('tarjetas_amarillas', 'Tarjetas amarillas'))
            report_lines.append(self.format_metric('tarjetas_rojas', 'Tarjetas rojas'))
        report_lines.append(self.format_metric('posesion_local_promedio', 'Posesión local promedio', is_percent=True))
        report_lines.append(self.format_metric('asistencia_promedio', 'Asistencia promedio'))
        if self.metrics.get('asistencia_maxima') is not None:
            report_lines.append(f"Asistencia máxima: {self.metrics['asistencia_maxima']:,} ({self.metrics.get('partido_mas_espectadores', '')})")
        report_lines.append(self.format_metric('estadio_mas_frecuente', 'Estadio más frecuente'))
        report_lines.append(self.format_metric('arbitro_mas_frecuente', 'Árbitro más frecuente'))

        _tech_equipo = [
            ('tiros_equipo_promedio',        'Tiros propios promedio',               False),
            ('tiros_rival_promedio',         'Tiros rival promedio',                 False),
            ('tiros_a_puerta_equipo_promedio','Tiros a puerta propios promedio',     False),
            ('tiros_a_puerta_rival_promedio','Tiros a puerta rival promedio',        False),
            ('xg_equipo_promedio',           'xG propio promedio',                  False),
            ('xg_rival_promedio',            'xG rival promedio',                   False),
            ('posesion_equipo_promedio',     'Posesión propia promedio',             True),
            ('posesion_rival_promedio',      'Posesión rival promedio',              True),
            ('corners_equipo_promedio',      'Corners propios promedio',            False),
            ('corners_rival_promedio',       'Corners rival promedio',              False),
            ('faltas_equipo_promedio',       'Faltas propias promedio',             False),
            ('faltas_rival_promedio',        'Faltas rival promedio',               False),
            ('fueras_de_juego_equipo_promedio','Fueras de juego propios promedio',  False),
            ('fueras_de_juego_rival_promedio','Fueras de juego rival promedio',     False),
            ('paradas_equipo_promedio',      'Paradas portero propio promedio',     False),
            ('paradas_rival_promedio',       'Paradas portero rival promedio',      False),
            ('precision_pases_equipo_promedio','Precisión pases propia',            True),
            ('precision_pases_rival_promedio','Precisión pases rival',             True),
        ]
        _tech_liga = [
            ('tiros_local_promedio',               'Tiros locales promedio',               False),
            ('tiros_visitante_promedio',           'Tiros visitante promedio',             False),
            ('tiros_a_puerta_local_promedio',      'Tiros a puerta local promedio',        False),
            ('tiros_a_puerta_visitante_promedio',  'Tiros a puerta visitante promedio',    False),
            ('xg_local_promedio',                  'xG local promedio',                   False),
            ('xg_visitante_promedio',              'xG visitante promedio',               False),
            ('posesion_local_promedio',            'Posesión local promedio',              True),
            ('posesion_visitante_promedio',        'Posesión visitante promedio',          True),
            ('corners_local_promedio',             'Corners local promedio',              False),
            ('corners_visitante_promedio',         'Corners visitante promedio',          False),
            ('faltas_local_promedio',              'Faltas local promedio',               False),
            ('faltas_visitante_promedio',          'Faltas visitante promedio',           False),
            ('fueras_de_juego_local_promedio',     'Fueras de juego local promedio',      False),
            ('fueras_de_juego_visitante_promedio', 'Fueras de juego visitante promedio',  False),
            ('paradas_local_promedio',             'Paradas portero local promedio',      False),
            ('paradas_visitante_promedio',         'Paradas portero visitante promedio',  False),
            ('precision_pases_local_promedio',     'Precisión pases local',               True),
            ('precision_pases_visitante_promedio', 'Precisión pases visitante',           True),
        ]
        _tech = _tech_equipo if self.metrics.get('tiros_equipo_promedio') is not None else _tech_liga

        def _fmt_tech_line(k: str, lbl: str, pct: bool) -> Optional[str]:
            val = self.metrics.get(k)
            if val is None:
                return None
            suffix = '%' if pct else ''
            # Si es una métrica de perspectiva de equipo, añadir desglose local/visitante
            if k.endswith('_equipo_promedio'):
                prefix = k[: -len('_equipo_promedio')]
                loc = self.metrics.get(f'{prefix}_equipo_local_promedio')
                vis = self.metrics.get(f'{prefix}_equipo_visitante_promedio')
                if loc is not None and vis is not None:
                    return f"  {lbl}: {val:.1f}{suffix}  (local: {loc:.1f}{suffix} | visitante: {vis:.1f}{suffix})"
            elif k.endswith('_rival_promedio'):
                prefix = k[: -len('_rival_promedio')]
                loc = self.metrics.get(f'{prefix}_rival_local_promedio')
                vis = self.metrics.get(f'{prefix}_rival_visitante_promedio')
                if loc is not None and vis is not None:
                    return f"  {lbl}: {val:.1f}{suffix}  (local rival: {loc:.1f}{suffix} | visitante rival: {vis:.1f}{suffix})"
            return f"  {lbl}: {val:.1f}{suffix}"

        tech_lines = [
            line for k, lbl, pct in _tech
            for line in [_fmt_tech_line(k, lbl, pct)]
            if line is not None
        ]
        if tech_lines:
            report_lines.append('')
            report_lines.append('Estadísticas técnicas promedio')
            report_lines.append('------------------------------')
            report_lines.extend(tech_lines)
            over = self.metrics.get('overperformance')
            over_desc = self.metrics.get('overperformance_desc')
            if over is not None:
                report_lines.append(f"  Eficiencia ofensiva (goles/xG): {over:.2f}  →  {over_desc}")

        # Comparativa vs liga
        if self.league_comparison:
            report_lines.append('')
            report_lines.append('Comparativa vs media de la liga')
            report_lines.append('-------------------------------')
            for row in self.league_comparison:
                report_lines.append(
                    f"  {row['metrica']}: {row['equipo']} "
                    f"(liga: {row['liga']}, "
                    f"dif: {row['signo']}{row['diferencia']})"
                )

        # Percentiles de liga
        if self.league_percentiles:
            report_lines.append('')
            report_lines.append('Percentiles en la liga')
            report_lines.append('----------------------')
            n_eq = self.league_percentiles[0]['n_equipos']
            report_lines.append(f'  (Posici\u00f3n relativa del equipo respecto a los {n_eq} equipos de la liga)')
            report_lines.append(f'  {"M\u00e9trica":<32} {"Valor":>7}  {"Percentil":>9}  Valoraci\u00f3n')
            report_lines.append(f'  {"-"*32} {"-"*7}  {"-"*9}  ----------')
            for p in self.league_percentiles:
                pct = p["percentil"]
                if pct >= 80:
                    rating = "Excelente"
                elif pct >= 60:
                    rating = "Por encima de la media"
                elif pct >= 40:
                    rating = "En la media"
                else:
                    rating = "Por debajo de la media"
                report_lines.append(
                    f'  {p["metrica"]:<32} {p["valor"]:>7.2f}  {pct:>8}%  {rating}'
                )

        # Rendimiento W/D/L del equipo
        if self.team_record:
            rec = self.team_record
            racha_display = ' '.join(list(rec['racha_actual']))
            report_lines.append('')
            report_lines.append('Rendimiento del equipo')
            report_lines.append('----------------------')
            report_lines.append(
                f"  Victorias: {rec['victorias']}  |  Empates: {rec['empates']}  |  "
                f"Derrotas: {rec['derrotas']}  |  Puntos: {rec['puntos']}"
            )
            report_lines.append(f"  Racha últimos 5: {racha_display}")
            report_lines.append(
                f"  Racha sin perder (máx.): {rec['racha_sin_perder_max']} partidos  |  "
                f"Racha goleadora (máx.): {rec['racha_goleadora_max']} partidos  |  "
                f"Racha sin marcar (máx.): {rec['racha_sin_marcar_max']} partidos"
            )
            report_lines.append('')
            show_season_col = any(r.get('season') for r in rec['tabla_resultados'])
            if show_season_col:
                report_lines.append(
                    f"  {'Temp':<6} {'Jornada':<8} {'Rival':<25} {'GF':>3} {'GC':>3} {'Local/Visit':<12} Res"
                )
                report_lines.append(f"  {'-'*6} {'-'*8} {'-'*25} {'-'*3} {'-'*3} {'-'*12} ---")
            else:
                report_lines.append(
                    f"  {'Jornada':<8} {'Rival':<25} {'GF':>3} {'GC':>3} {'Local/Visit':<12} Res"
                )
                report_lines.append(f"  {'-'*8} {'-'*25} {'-'*3} {'-'*3} {'-'*12} ---")
            for r in rec['tabla_resultados']:
                jornada_str = str(r['jornada']) if r['jornada'] is not None else '-'
                if show_season_col:
                    season_str = str(r.get('season', '-')) if r.get('season') else '-'
                    report_lines.append(
                        f"  {season_str:<6} {jornada_str:<8} {str(r['rival']):<25} {r['gf']:>3} {r['gc']:>3} "
                        f"{r['local']:<12} {r['resultado']}"
                    )
                else:
                    report_lines.append(
                        f"  {jornada_str:<8} {str(r['rival']):<25} {r['gf']:>3} {r['gc']:>3} "
                        f"{r['local']:<12} {r['resultado']}"
                    )

        report_lines.append('')

        if self.team and self.player_rankings:
            goleadores = self.player_rankings.get('goleadores', pd.DataFrame())
            asistentes = self.player_rankings.get('asistentes', pd.DataFrame())
            if not goleadores.empty:
                report_lines.append('Top goleadores')
                report_lines.extend(goleadores.to_string(index=False).splitlines())
            else:
                report_lines.append('Top goleadores: sin datos disponibles')
            report_lines.append('')
            if not asistentes.empty:
                report_lines.append('Top asistentes')
                report_lines.extend(asistentes.to_string(index=False).splitlines())
            else:
                report_lines.append('Top asistentes: sin datos disponibles')
        else:
            report_lines.append('Top equipos con más goles')
            report_lines.extend(self.top_scorers.to_string(index=False).splitlines())
            report_lines.append('')
            report_lines.append('Top equipos con menos goles concedidos')
            report_lines.extend(self.top_defenders.to_string(index=False).splitlines())
        report_lines.append('')

        report_lines.append('Partidos destacados')
        report_lines.extend(self.highlights[['date', 'local_team', 'visitante_team', 'goles_local', 'goles_visitante', 'goles_totales']]
                            .to_string(index=False).splitlines())

        # 5.1 Conclusiones automáticas (modo equipo)
        report_lines.extend(self._generate_conclusions())

        # 5.2 Narrativa intertemporada (si --seasons)
        report_lines.extend(self._generate_interseason_narrative())

        report_text = '\n'.join(report_lines)
        if output_path:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(report_text, encoding='utf-8')

        return report_text

    def clean_reports(self, output_folder: str = 'reports') -> None:
        report_folder = Path(output_folder)
        if not report_folder.exists():
            return
        if report_folder.is_file():
            raise ValueError(f'El camino de reportes debe ser una carpeta, no un archivo: {output_folder}')

        for item in report_folder.iterdir():
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)

    def generate_json_report(self, output_path: Optional[str] = None) -> str:
        """Serializa todo el análisis a JSON estructurado.

        Convierte DataFrames a listas de registros y tipos numpy a tipos
        Python nativos. El JSON refleja el mismo modo que genera_report().
        """
        if not self.metrics:
            raise ValueError('Ejecute analyze() antes de generar el informe.')

        def _df_to_list(df) -> list:
            if df is None or (hasattr(df, 'empty') and df.empty):
                return []
            return [
                {k: (None if (isinstance(v, float) and np.isnan(v)) else
                     int(v) if isinstance(v, (np.integer,)) else
                     float(v) if isinstance(v, (np.floating,)) else v)
                 for k, v in row.items()}
                for row in df.to_dict(orient='records')
            ]

        def _clean(obj):
            if isinstance(obj, pd.DataFrame):
                return _df_to_list(obj)
            if isinstance(obj, dict):
                return {k: _clean(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [_clean(i) for i in obj]
            if isinstance(obj, (np.integer,)):
                return int(obj)
            if isinstance(obj, (np.floating,)):
                return None if np.isnan(obj) else float(obj)
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            return obj

        # Modo
        if self.match_id is not None and self.match_detail:
            modo = 'partido'
        elif self.matchday is not None and self.matchday_summary:
            modo = 'jornada'
        elif self.player_profile:
            modo = 'jugador'
        elif self.liga_summary:
            modo = 'liga'
        else:
            modo = 'equipo'

        payload: dict = {
            'modo':              modo,
            'metrics':           _clean(self.metrics),
            'league_comparison': self.league_comparison,
            'league_percentiles': self.league_percentiles,
            'team_record':       _clean(self.team_record),
            'top_scorers':       _df_to_list(self.top_scorers),
            'top_defenders':     _df_to_list(self.top_defenders),
            'highlights':        _df_to_list(self.highlights),
        }

        if self.liga_summary:
            ls = {k: v for k, v in self.liga_summary.items()}
            for df_key in ('clasificacion', 'stats_por_equipo', 'home_away', 'xpts_standings'):
                ls[df_key] = _df_to_list(ls.get(df_key))
            payload['liga_summary'] = _clean(ls)

        if self.match_detail:
            payload['match_detail'] = _clean(self.match_detail)

        if self.matchday_summary:
            payload['matchday_summary'] = _clean(self.matchday_summary)

        if self.player_profile:
            payload['player_profile'] = _clean(self.player_profile)

        if self.player_rankings:
            payload['player_rankings'] = _clean(self.player_rankings)

        json_str = json.dumps(payload, ensure_ascii=False, indent=2, default=str)

        if output_path:
            out = Path(output_path)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json_str, encoding='utf-8')

        return json_str

    def generate_html_report(self, output_path: str, image_folder: Optional[str] = None) -> str:
        if not self.metrics:
            raise ValueError('Ejecute analyze() antes de generar el informe HTML.')
        if self.top_scorers is None or self.top_defenders is None or self.highlights is None:
            raise ValueError('Los resultados del análisis no están disponibles. Ejecute analyze() antes de generar el informe HTML.')

        if self.match_id is not None and self.match_detail:
            return self._generate_match_html_report(output_path, image_folder=image_folder)

        if self.compare is not None and self.compare_data:
            return self._generate_compare_html_report(output_path, image_folder=image_folder)

        if self.matchday is not None and self.matchday_summary:
            return self._generate_matchday_html_report(output_path, image_folder=image_folder)

        if self.player_profile:
            return self._generate_player_html_report(output_path, image_folder=image_folder)

        if self.liga_summary:
            return self._generate_liga_html_report(output_path, image_folder=image_folder)

        report_file = Path(output_path)
        report_file.parent.mkdir(parents=True, exist_ok=True)

        image_folder_path = Path(image_folder) if image_folder else report_file.parent
        image_folder_path.mkdir(parents=True, exist_ok=True)

        images = self.save_visual_report(str(image_folder_path))
        relative_images = [Path(os.path.relpath(img, start=report_file.parent)).as_posix() for img in images if img]

        html = [
            '<!DOCTYPE html>',
            '<html lang="es">',
            '<head>',
            '  <meta charset="UTF-8">',
            '  <meta name="viewport" content="width=device-width, initial-scale=1.0">',
            '  <title>Informe Deportivo</title>',
            '  <style>',
            '    body { font-family: Arial, sans-serif; margin: 24px; background: #f7f8fb; color: #222; }',
            '    h1, h2 { color: #1f4e79; }',
            '    .section { margin-bottom: 24px; }',
            '    .metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; }',
            '    .metric { background: white; padding: 16px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }',
            '    table { width: 100%; border-collapse: collapse; margin-top: 12px; }',
            '    th, td { padding: 8px 10px; border: 1px solid #d7dbe3; text-align: left; }',
            '    th { background: #e4efff; }',
            '    img { max-width: 100%; border-radius: 8px; margin-top: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }',
            '  </style>',
            '</head>',
            '<body>',
            '  <h1>Informe Deportivo</h1>',
            '  <div class="section">',
            '    <h2>Resumen general</h2>',
            '    <div class="metrics">',
            *([
                f'      <div class="metric"><strong>Temporadas</strong><p>{", ".join(str(s) for s in self.seasons)}</p></div>'
            ] if self.seasons and len(self.seasons) > 1 else (
                [f'      <div class="metric"><strong>Temporada</strong><p>{self.season}</p></div>']
                if self.season else []
            )),
            f'      <div class="metric"><strong>Partidos analizados</strong><p>{self.metrics["partidos_analizados"]}</p></div>',
            *(
                [
                    f'      <div class="metric"><strong>Goles a favor</strong><p>{self.metrics["goles_a_favor"]}</p></div>',
                    f'      <div class="metric"><strong>Goles en contra</strong><p>{self.metrics["goles_en_contra"]}</p></div>',
                    f'      <div class="metric"><strong>Prom. a favor</strong><p>{self.metrics["goles_a_favor_promedio"]:.2f}</p></div>',
                    f'      <div class="metric"><strong>Prom. en contra</strong><p>{self.metrics["goles_concedidos_promedio"]:.2f}</p></div>',
                    f'      <div class="metric"><strong>Tarjetas amarillas</strong><p>{self.format_html_metric("tarjetas_amarillas_equipo")}</p></div>',
                    f'      <div class="metric"><strong>Tarjetas rojas</strong><p>{self.format_html_metric("tarjetas_rojas_equipo")}</p></div>',
                ] if self.metrics.get('goles_a_favor') is not None else [
                    f'      <div class="metric"><strong>Goles totales</strong><p>{self.metrics["goles_totales"]}</p></div>',
                    f'      <div class="metric"><strong>Goles promedio</strong><p>{self.metrics["goles_promedio_por_partido"]:.2f}</p></div>',
                    f'      <div class="metric"><strong>Tarjetas amarillas</strong><p>{self.format_html_metric("tarjetas_amarillas")}</p></div>',
                    f'      <div class="metric"><strong>Tarjetas rojas</strong><p>{self.format_html_metric("tarjetas_rojas")}</p></div>',
                ]
            ),
        ]

        if self.metrics.get('posesion_local_promedio') is not None:
            html.append(f'      <div class="metric"><strong>Posesión local promedio</strong><p>{self.metrics["posesion_local_promedio"]:.1f}%</p></div>')
        else:
            html.append('      <div class="metric"><strong>Posesión local promedio</strong><p>No disponible</p></div>')

        if self.metrics.get('asistencia_promedio') is not None:
            html.append(f'      <div class="metric"><strong>Asistencia promedio</strong><p>{self.metrics["asistencia_promedio"]:,.0f}</p></div>')
        if self.metrics.get('asistencia_maxima') is not None:
            html.append(f'      <div class="metric"><strong>Asistencia máxima</strong><p>{self.metrics["asistencia_maxima"]:,}<br><small>{self.metrics.get("partido_mas_espectadores","")}</small></p></div>')
        if self.metrics.get('estadio_mas_frecuente') is not None:
            html.append(f'      <div class="metric"><strong>Estadio más frecuente</strong><p>{self.metrics["estadio_mas_frecuente"]}</p></div>')
        if self.metrics.get('arbitro_mas_frecuente') is not None:
            html.append(f'      <div class="metric"><strong>Árbitro más frecuente</strong><p>{self.metrics["arbitro_mas_frecuente"]}</p></div>')

        # Métricas técnicas en el grid
        _tech_html_equipo = [
            ('tiros_equipo_promedio',          'Tiros propios (prom.)',          False),
            ('tiros_rival_promedio',           'Tiros rival (prom.)',            False),
            ('tiros_a_puerta_equipo_promedio', 'Tiros a puerta propios (prom.)', False),
            ('tiros_a_puerta_rival_promedio',  'Tiros a puerta rival (prom.)',   False),
            ('xg_equipo_promedio',             'xG propio (prom.)',             False),
            ('xg_rival_promedio',              'xG rival (prom.)',              False),
            ('corners_equipo_promedio',        'Corners propios (prom.)',       False),
            ('corners_rival_promedio',         'Corners rival (prom.)',         False),
            ('faltas_equipo_promedio',         'Faltas propias (prom.)',        False),
            ('faltas_rival_promedio',          'Faltas rival (prom.)',          False),
            ('paradas_equipo_promedio',        'Paradas portero propio (prom.)',False),
            ('paradas_rival_promedio',         'Paradas portero rival (prom.)', False),
            ('precision_pases_equipo_promedio','Precisión pases propia',        True),
            ('precision_pases_rival_promedio', 'Precisión pases rival',         True),
        ]
        _tech_html_liga = [
            ('tiros_local_promedio',              'Tiros locales (prom.)',         False),
            ('tiros_visitante_promedio',          'Tiros visitante (prom.)',       False),
            ('tiros_a_puerta_local_promedio',     'Tiros a puerta local (prom.)',  False),
            ('tiros_a_puerta_visitante_promedio', 'Tiros a puerta visit. (prom.)', False),
            ('xg_local_promedio',                'xG local promedio',             False),
            ('xg_visitante_promedio',            'xG visitante promedio',         False),
            ('corners_local_promedio',           'Corners local (prom.)',         False),
            ('corners_visitante_promedio',       'Corners visitante (prom.)',     False),
            ('faltas_local_promedio',            'Faltas local (prom.)',          False),
            ('faltas_visitante_promedio',        'Faltas visitante (prom.)',      False),
            ('paradas_local_promedio',           'Paradas portero local (prom.)', False),
            ('paradas_visitante_promedio',       'Paradas portero visit.(prom.)', False),
            ('precision_pases_local_promedio',   'Precisión pases local',         True),
            ('precision_pases_visitante_promedio', 'Precisión pases visitante',   True),
        ]
        _tech_html = _tech_html_equipo if self.metrics.get('tiros_equipo_promedio') is not None else _tech_html_liga
        for k, lbl, pct in _tech_html:
            val = self.metrics.get(k)
            if val is None:
                continue
            fmt_total = f'{val:.1f}%' if pct else f'{val:.1f}'
            suffix = '%' if pct else ''
            # Desglose local/visitante para métricas de perspectiva de equipo
            split_html = ''
            if k.endswith('_equipo_promedio'):
                prefix_k = k[: -len('_equipo_promedio')]
                loc = self.metrics.get(f'{prefix_k}_equipo_local_promedio')
                vis = self.metrics.get(f'{prefix_k}_equipo_visitante_promedio')
                if loc is not None and vis is not None:
                    split_html = (
                        f'<small style="color:#555;display:block;margin-top:4px">'
                        f'Local: {loc:.1f}{suffix} &nbsp;|&nbsp; Visit.: {vis:.1f}{suffix}'
                        f'</small>'
                    )
            elif k.endswith('_rival_promedio'):
                prefix_k = k[: -len('_rival_promedio')]
                loc = self.metrics.get(f'{prefix_k}_rival_local_promedio')
                vis = self.metrics.get(f'{prefix_k}_rival_visitante_promedio')
                if loc is not None and vis is not None:
                    split_html = (
                        f'<small style="color:#555;display:block;margin-top:4px">'
                        f'Local rival: {loc:.1f}{suffix} &nbsp;|&nbsp; Visit. rival: {vis:.1f}{suffix}'
                        f'</small>'
                    )
            html.append(f'      <div class="metric"><strong>{lbl}</strong><p>{fmt_total}{split_html}</p></div>')

        # Eficiencia ofensiva xG
        over = self.metrics.get('overperformance')
        over_desc = self.metrics.get('overperformance_desc')
        if over is not None:
            color = '#27ae60' if over > 1.2 else ('#e74c3c' if over < 0.8 else '#f39c12')
            html.append(
                f'      <div class="metric"><strong>Eficiencia ofensiva (goles/xG)</strong>'
                f'<p style="color:{color};font-size:1.3em;font-weight:bold">{over:.2f}</p>'
                f'<small style="color:#555">{over_desc}</small></div>'
            )

        html.extend([
            '    </div>',
            '  </div>',
        ])

        # Sección comparativa vs liga en HTML
        if self.league_comparison:
            html.extend([
                '  <div class="section">',
                '    <h2>Comparativa vs media de La Liga</h2>',
                '    <table>',
                '      <thead><tr><th>Métrica</th><th>Equipo</th><th>Liga</th><th>Diferencia</th></tr></thead>',
                '      <tbody>',
            ])
            for row in self.league_comparison:
                signo = row['signo']
                diff = row['diferencia']
                color = '#27ae60' if diff >= 0 else '#e74c3c'
                html.append(
                    f'        <tr>'
                    f'<td>{row["metrica"]}</td>'
                    f'<td>{row["equipo"]}</td>'
                    f'<td>{row["liga"]}</td>'
                    f'<td style="color:{color};font-weight:bold">{signo}{diff}</td>'
                    f'</tr>'
                )
            html.extend(['      </tbody>', '    </table>', '  </div>'])

        # Sección Percentiles de liga en HTML
        if self.league_percentiles:
            n_eq = self.league_percentiles[0]['n_equipos']
            html.extend([
                '  <div class="section">',
                f'    <h2>Percentiles en la liga <small style="color:#666;font-size:0.6em">({n_eq} equipos)</small></h2>',
                '    <table>',
                '      <thead><tr><th>Métrica</th><th>Valor</th><th>Percentil</th><th>Valoración</th></tr></thead>',
                '      <tbody>',
            ])
            for p in self.league_percentiles:
                pct = p['percentil']
                if pct >= 80:
                    bar_color = '#27ae60'
                    rating = 'Excelente'
                elif pct >= 60:
                    bar_color = '#2e86de'
                    rating = 'Por encima de la media'
                elif pct >= 40:
                    bar_color = '#f39c12'
                    rating = 'En la media'
                else:
                    bar_color = '#e74c3c'
                    rating = 'Por debajo de la media'
                bar_html = (
                    f'<div style="background:#eee;border-radius:4px;height:10px;width:120px;display:inline-block;vertical-align:middle">'
                    f'<div style="background:{bar_color};width:{pct}%;height:100%;border-radius:4px"></div></div>'
                    f' <span style="color:{bar_color};font-weight:bold">{pct}%</span>'
                )
                html.append(
                    f'        <tr>'
                    f'<td>{p["metrica"]}</td>'
                    f'<td>{p["valor"]:.2f}</td>'
                    f'<td>{bar_html}</td>'
                    f'<td style="color:{bar_color}">{rating}</td>'
                    f'</tr>'
                )
            html.extend(['      </tbody>', '    </table>', '  </div>'])

        # Sección Rendimiento W/D/L en HTML
        if self.team_record:
            rec = self.team_record
            badge_colors = {'V': '#27ae60', 'E': '#f39c12', 'D': '#e74c3c'}
            racha_badges = ''
            for r_char in rec['racha_actual']:
                color = badge_colors.get(r_char, '#888')
                racha_badges += (
                    f'<span style="display:inline-block;width:28px;height:28px;line-height:28px;'
                    f'text-align:center;border-radius:50%;background:{color};color:white;'
                    f'font-weight:bold;margin:2px">{r_char}</span>'
                )
            res_bg = {'V': '#d4edda', 'E': '#fff3cd', 'D': '#f8d7da'}
            html.extend([
                '  <div class="section">',
                '    <h2>Rendimiento del equipo</h2>',
                '    <div class="metrics">',
                f'      <div class="metric"><strong>Victorias</strong><p style="color:#27ae60;font-size:1.4em;font-weight:bold">{rec["victorias"]}</p></div>',
                f'      <div class="metric"><strong>Empates</strong><p style="color:#f39c12;font-size:1.4em;font-weight:bold">{rec["empates"]}</p></div>',
                f'      <div class="metric"><strong>Derrotas</strong><p style="color:#e74c3c;font-size:1.4em;font-weight:bold">{rec["derrotas"]}</p></div>',
                f'      <div class="metric"><strong>Puntos</strong><p style="font-size:1.4em;font-weight:bold">{rec["puntos"]}</p></div>',
                '    </div>',
                f'    <p><strong>Racha últimos 5:</strong> {racha_badges}</p>'
                f'    <p>'
                f'      <strong>Racha sin perder (máx.):</strong> {rec["racha_sin_perder_max"]} partidos &nbsp;&nbsp;|&nbsp;&nbsp;'
                f'      <strong>Racha goleadora (máx.):</strong> {rec["racha_goleadora_max"]} partidos &nbsp;&nbsp;|&nbsp;&nbsp;'
                f'      <strong>Racha sin marcar (máx.):</strong> {rec["racha_sin_marcar_max"]} partidos'
                f'    </p>',
                '    <table>',
            ])
            show_season_col = any(r.get('season') for r in rec['tabla_resultados'])
            thead_cols = '<th>Temporada</th>' if show_season_col else ''
            html.extend([
                f'      <thead><tr>{thead_cols}<th>Jornada</th><th>Rival</th><th>GF</th><th>GC</th><th>Local/Visitante</th><th>Resultado</th></tr></thead>',
                '      <tbody>',
            ])
            for r in rec['tabla_resultados']:
                jornada_str = str(r['jornada']) if r['jornada'] is not None else '-'
                bg = res_bg.get(r['resultado'], 'white')
                season_td = f'<td>{r.get("season", "-")}</td>' if show_season_col else ''
                html.append(
                    f'        <tr style="background:{bg}">'
                    f'{season_td}'
                    f'<td>{jornada_str}</td>'
                    f'<td>{r["rival"]}</td>'
                    f'<td>{r["gf"]}</td>'
                    f'<td>{r["gc"]}</td>'
                    f'<td>{r["local"]}</td>'
                    f'<td><strong>{r["resultado"]}</strong></td>'
                    f'</tr>'
                )
            html.extend(['      </tbody>', '    </table>', '  </div>'])

        if self.team and self.player_rankings:
            goleadores = self.player_rankings.get('goleadores', pd.DataFrame())
            asistentes = self.player_rankings.get('asistentes', pd.DataFrame())
            html.extend(['  <div class="section">', '    <h2>Top goleadores</h2>'])
            if not goleadores.empty:
                html.append(goleadores.to_html(index=False, classes='dataframe', border=0))
            else:
                html.append('    <p>Sin datos disponibles.</p>')
            html.extend(['  </div>', '  <div class="section">', '    <h2>Top asistentes</h2>'])
            if not asistentes.empty:
                html.append(asistentes.to_html(index=False, classes='dataframe', border=0))
            else:
                html.append('    <p>Sin datos disponibles.</p>')
            html.append('  </div>')
        else:
            html.extend([
                '  <div class="section">',
                '    <h2>Equipos con más goles</h2>',
                self.top_scorers.to_html(index=False, classes='dataframe', border=0),
                '  </div>',
                '  <div class="section">',
                '    <h2>Equipos con menos goles concedidos</h2>',
                self.top_defenders.to_html(index=False, classes='dataframe', border=0),
                '  </div>',
            ])
        html.extend([
            '  <div class="section">',
            '    <h2>Partidos destacados</h2>',
        ])

        highlights_cols = ['date', 'local_team', 'visitante_team', 'goles_local', 'goles_visitante', 'goles_totales']
        if 'jornada' in self.highlights.columns:
            highlights_cols.insert(0, 'jornada')
        if 'estadio' in self.highlights.columns:
            highlights_cols.append('estadio')
        html.append(self.highlights[highlights_cols].to_html(index=False, classes='dataframe', border=0))

        # Sección de vídeos destacados
        if 'video_highlights' in self.highlights.columns:
            videos = self.highlights[['local_team', 'visitante_team', 'video_highlights']].dropna(subset=['video_highlights'])
            if not videos.empty:
                html.append('  <div class="section">')
                html.append('    <h2>Vídeos destacados</h2>')
                for _, row in videos.iterrows():
                    html.append(f'    <p><a href="{row["video_highlights"]}" target="_blank">{row["local_team"]} vs {row["visitante_team"]}</a></p>')
                html.append('  </div>')

        html.extend([
            '  </div>',
        ])

        html.extend([
            '  <div class="section">',
            '    <h2>Gráficos</h2>',
        ])

        for image_name in relative_images:
            html.append(f'    <img src="{image_name}" alt="{image_name}">')

        conclusions_html = self._generate_conclusions_html()
        if conclusions_html:
            html.append(conclusions_html)

        interseason = self._generate_interseason_narrative()
        if interseason:
            html.append('  <h2>Evolución intertemporada</h2>')
            html.append('  <div style="background:white;border-radius:8px;padding:16px 20px;'
                        'box-shadow:0 2px 8px rgba(0,0,0,0.08);margin-bottom:24px;">')
            html.append('  <pre style="font-family:monospace;font-size:0.88em;margin:0;">')
            html.append('\n'.join(interseason))
            html.append('  </pre></div>')

        html.extend([
          '  </div>',
          '</body>',
          '</html>',
        ])

        report_file.write_text('\n'.join(html), encoding='utf-8')
        return str(report_file)

    def save_visual_report(self, output_folder: str = 'reports') -> List[str]:
        if self.data is None:
            raise ValueError('No hay datos cargados. Ejecute load_data() primero.')

        if self.no_charts:
            return []

        report_folder = Path(output_folder)
        report_folder.mkdir(parents=True, exist_ok=True)

        # Modo Compare: radar comparativo entre dos equipos
        if self.compare is not None and self.compare_data:
            paths = []
            radar_path = plot_compare_radar(self.compare_data, str(report_folder / 'compare_radar.png'))
            if radar_path:
                paths.append(radar_path)
            return paths

        # Modo Partido: gráficos de estadísticas cara a cara
        if self.match_id is not None:
            paths = []
            bar_path = plot_match_stats_bar(
                self.match_detail['stats'],
                self.match_detail['local'],
                self.match_detail['visitante'],
                str(report_folder / 'match_stats_bar.png'),
            )
            if bar_path:
                paths.append(bar_path)
            radar_path = plot_match_radar(
                self.match_detail['stats'],
                self.match_detail['local'],
                self.match_detail['visitante'],
                str(report_folder / 'match_radar.png'),
            )
            if radar_path:
                paths.append(radar_path)
            return paths

        # Modo Jornada: solo gráficos de la jornada
        if self.matchday is not None:
            paths = []
            goals_path = plot_matchday_goals(self.data, str(report_folder / 'matchday_goals.png'))
            if goals_path:
                paths.append(goals_path)
            xg_path = plot_matchday_xg(self.data, str(report_folder / 'matchday_xg.png'))
            if xg_path:
                paths.append(xg_path)
            return paths

        # Modo Jugador: barras + radar del jugador
        if self.player_profile and self.player_profile.get('found'):
            paths = []
            bar_path = plot_player_bar(self.player_profile, str(report_folder / 'player_bar.png'))
            if bar_path:
                paths.append(bar_path)
            radar_path = plot_player_radar(self.player_profile, str(report_folder / 'player_radar.png'))
            if radar_path:
                paths.append(radar_path)
            return paths

        # Modo Liga: gráficos de clasificación, goles y rendimiento
        if self.liga_summary:
            paths = []
            lt = plot_league_table(self.liga_summary['clasificacion'], str(report_folder / 'league_table.png'))
            if lt: paths.append(lt)
            gpt = plot_goals_per_team(self.liga_summary['clasificacion'], str(report_folder / 'goals_per_team.png'))
            if gpt: paths.append(gpt)
            xgt = plot_xg_per_team(self.liga_summary['stats_por_equipo'], str(report_folder / 'xg_per_team.png'))
            if xgt: paths.append(xgt)
            hap = plot_home_away_performance(self.liga_summary['home_away'], str(report_folder / 'home_away_performance.png'))
            if hap: paths.append(hap)
            # 3.2 Puntos acumulados por jornada
            cup = plot_cumulative_points(self.data, str(report_folder / 'cumulative_points.png'), top_n=self.top_n)
            if cup: paths.append(cup)
            # 3.4 Mapa de calor de resultados
            hmap = plot_results_heatmap(self.data, str(report_folder / 'results_heatmap.png'))
            if hmap: paths.append(hmap)
            return paths

        paths = []

        goals_path = plot_goals_distribution(self.data, str(report_folder / 'goals_distribution.png'))
        if goals_path:
            paths.append(goals_path)

        possession_path = plot_possession_distribution(self.data, str(report_folder / 'possession_distribution.png'))
        if possession_path:
            paths.append(possession_path)

        card_path = plot_card_statistics(self.data, str(report_folder / 'card_summary.png'))
        if card_path:
            paths.append(card_path)

        attendance_path = plot_attendance(self.data, str(report_folder / 'attendance.png'))
        if attendance_path:
            paths.append(attendance_path)

        xg_path = plot_xg_per_match(self.data, str(report_folder / 'xg_per_match.png'))
        if xg_path:
            paths.append(xg_path)

        shots_path = plot_shots_comparison(self.data, str(report_folder / 'shots_comparison.png'))
        if shots_path:
            paths.append(shots_path)

        evolution_path = plot_temporal_evolution(self.data, self.team, str(report_folder / 'temporal_evolution.png'))
        if evolution_path:
            paths.append(evolution_path)

        # 3.1 Embudo de conversión de tiros
        funnel_path = plot_shot_funnel(self.data, str(report_folder / 'shot_funnel.png'), team=self.team)
        if funnel_path:
            paths.append(funnel_path)

        return paths
