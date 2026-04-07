import os
import shutil
from pathlib import Path
from typing import List, Optional

import pandas as pd

from .analysis import (
    compute_league_comparison,
    compute_overall_metrics,
    compute_team_record,
    match_highlights,
    top_defensive_teams,
    top_scoring_teams,
)
from .data_loader import load_match_data
from .visualizer import (
    plot_attendance,
    plot_card_statistics,
    plot_goals_distribution,
    plot_possession_distribution,
    plot_shots_comparison,
    plot_temporal_evolution,
    plot_xg_per_match,
)


class SportsAgent:
    def __init__(self, data_path: str, fetch_real: bool = False, competition_id: Optional[int] = None, season: Optional[str] = None, team: Optional[str] = None, seasons: Optional[List[str]] = None):
        self.data_path = data_path
        self.fetch_real = fetch_real
        self.competition_id = competition_id
        self.season = season
        self.seasons = seasons  # lista de temporadas para análisis multi-temporada
        self.team = team
        self.data: Optional[pd.DataFrame] = None
        self.full_data: Optional[pd.DataFrame] = None  # datos de toda la liga (antes de filtrar)
        self.available_optional_columns: set[str] = set()
        self.metrics: dict = {}
        self.league_metrics: dict = {}  # métricas de la liga completa para comparativa
        self.league_comparison: list = []  # filas de comparativa equipo vs liga
        self.team_record: dict = {}  # historial W/D/L del equipo
        self.top_scorers: Optional[pd.DataFrame] = None
        self.top_defenders: Optional[pd.DataFrame] = None
        self.highlights: Optional[pd.DataFrame] = None

    def load_data(self):
        if self.seasons and len(self.seasons) > 1:
            from .data_loader import load_multiple_seasons
            if self.competition_id is None:
                raise ValueError('--competition es obligatorio con --seasons')
            self.data = load_multiple_seasons(
                self.data_path, self.competition_id, self.seasons, self.fetch_real
            )
        else:
            _season = self.seasons[0] if self.seasons and len(self.seasons) == 1 else self.season
            self.data = load_match_data(self.data_path, self.fetch_real, self.competition_id, _season)
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

    def analyze(self):
        if self.data is None:
            raise ValueError('Datos no cargados. Ejecute load_data() primero.')

        self.filter_by_team()
        self.metrics = compute_overall_metrics(self.data, team=self.team)
        self.top_scorers = top_scoring_teams(self.data)
        self.top_defenders = top_defensive_teams(self.data)
        self.highlights = match_highlights(self.data)
        # Comparativa vs liga si se filtró por equipo
        if self.full_data is not None:
            self.league_metrics = compute_overall_metrics(self.full_data)
            self.league_comparison = compute_league_comparison(self.metrics, self.league_metrics)
        # Historial W/D/L si se filtró por equipo
        if self.team:
            self.team_record = compute_team_record(self.data, self.team)
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

    def generate_report(self, output_path: Optional[str] = None) -> str:
        if not self.metrics:
            raise ValueError('Ejecute analyze() antes de generar el informe.')
        if self.top_scorers is None or self.top_defenders is None or self.highlights is None:
            raise ValueError('Los resultados del análisis no están disponibles. Ejecute analyze() antes de generar el informe.')

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

        _tech = [
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
        tech_lines = [
            f"  {lbl}: {self.metrics[k]:.1f}{'%' if pct else ''}"
            for k, lbl, pct in _tech
            if self.metrics.get(k) is not None
        ]
        if tech_lines:
            report_lines.append('')
            report_lines.append('Estadísticas técnicas promedio')
            report_lines.append('------------------------------')
            report_lines.extend(tech_lines)

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

        report_lines.append('Top equipos con más goles')
        report_lines.extend(self.top_scorers.to_string(index=False).splitlines())
        report_lines.append('')

        report_lines.append('Top equipos con menos goles concedidos')
        report_lines.extend(self.top_defenders.to_string(index=False).splitlines())
        report_lines.append('')

        report_lines.append('Partidos destacados')
        report_lines.extend(self.highlights[['date', 'local_team', 'visitante_team', 'goles_local', 'goles_visitante', 'goles_totales']]
                            .to_string(index=False).splitlines())

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

    def generate_html_report(self, output_path: str, image_folder: Optional[str] = None) -> str:
        if not self.metrics:
            raise ValueError('Ejecute analyze() antes de generar el informe HTML.')
        if self.top_scorers is None or self.top_defenders is None or self.highlights is None:
            raise ValueError('Los resultados del análisis no están disponibles. Ejecute analyze() antes de generar el informe HTML.')

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
        _tech_html = [
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
        for k, lbl, pct in _tech_html:
            val = self.metrics.get(k)
            if val is not None:
                fmt = f'{val:.1f}%' if pct else f'{val:.1f}'
                html.append(f'      <div class="metric"><strong>{lbl}</strong><p>{fmt}</p></div>')

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
                f'    <p><strong>Racha últimos 5:</strong> {racha_badges}</p>',
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

        html.extend([
            '  <div class="section">',
            '    <h2>Equipos con más goles</h2>',
            self.top_scorers.to_html(index=False, classes='dataframe', border=0),
            '  </div>',
            '  <div class="section">',
            '    <h2>Equipos con menos goles concedidos</h2>',
            self.top_defenders.to_html(index=False, classes='dataframe', border=0),
            '  </div>',
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

        report_folder = Path(output_folder)
        report_folder.mkdir(parents=True, exist_ok=True)

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

        return paths
