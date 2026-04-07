import os
import shutil
from pathlib import Path
from typing import List, Optional

import pandas as pd

from .analysis import (
    compute_overall_metrics,
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
    plot_xg_per_match,
)


class SportsAgent:
    def __init__(self, data_path: str, fetch_real: bool = False, competition_id: Optional[int] = None, season: Optional[str] = None, team: Optional[str] = None):
        self.data_path = data_path
        self.fetch_real = fetch_real
        self.competition_id = competition_id
        self.season = season
        self.team = team
        self.data: Optional[pd.DataFrame] = None
        self.available_optional_columns: set[str] = set()
        self.metrics: dict = {}
        self.top_scorers: Optional[pd.DataFrame] = None
        self.top_defenders: Optional[pd.DataFrame] = None
        self.highlights: Optional[pd.DataFrame] = None

    def load_data(self):
        self.data = load_match_data(self.data_path, self.fetch_real, self.competition_id, self.season)
        if self.data is not None and isinstance(self.data, pd.DataFrame):
            self.available_optional_columns = set(self.data.attrs.get('available_optional_columns', []))
        return self.data

    def filter_by_team(self):
        if self.team and self.data is not None:
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
        self.metrics = compute_overall_metrics(self.data)
        self.top_scorers = top_scoring_teams(self.data)
        self.top_defenders = top_defensive_teams(self.data)
        self.highlights = match_highlights(self.data)
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
        report_lines.append(f"Partidos analizados: {self.metrics['partidos_analizados']}")
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
            f'      <div class="metric"><strong>Partidos analizados</strong><p>{self.metrics["partidos_analizados"]}</p></div>',
            f'      <div class="metric"><strong>Goles totales</strong><p>{self.metrics["goles_totales"]}</p></div>',
            f'      <div class="metric"><strong>Goles promedio</strong><p>{self.metrics["goles_promedio_por_partido"]:.2f}</p></div>',
            f'      <div class="metric"><strong>Tarjetas amarillas</strong><p>{self.format_html_metric("tarjetas_amarillas")}</p></div>',
            f'      <div class="metric"><strong>Tarjetas rojas</strong><p>{self.format_html_metric("tarjetas_rojas")}</p></div>',
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

        return paths
