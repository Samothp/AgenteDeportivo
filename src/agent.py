from pathlib import Path
from typing import List, Optional

from .analysis import (
    compute_overall_metrics,
    match_highlights,
    top_defensive_teams,
    top_scoring_teams,
)
from .data_loader import load_match_data
from .visualizer import (
    plot_card_statistics,
    plot_goals_distribution,
    plot_possession_distribution,
)


from pathlib import Path
from typing import List, Optional

from .analysis import (
    compute_overall_metrics,
    match_highlights,
    top_defensive_teams,
    top_scoring_teams,
)
from .data_loader import load_match_data
from .visualizer import (
    plot_card_statistics,
    plot_goals_distribution,
    plot_possession_distribution,
)


class SportsAgent:
    def __init__(self, data_path: str, fetch_real: bool = False, competition_id: Optional[int] = None, season: Optional[str] = None):
        self.data_path = data_path
        self.fetch_real = fetch_real
        self.competition_id = competition_id
        self.season = season
        self.data = None
        self.metrics = {}
        self.top_scorers = None
        self.top_defenders = None
        self.highlights = None

    def load_data(self):
        self.data = load_match_data(self.data_path, self.fetch_real, self.competition_id, self.season)
        return self.data

    def analyze(self):
        if self.data is None:
            raise ValueError('Datos no cargados. Ejecute load_data() primero.')

        self.metrics = compute_overall_metrics(self.data)
        self.top_scorers = top_scoring_teams(self.data)
        self.top_defenders = top_defensive_teams(self.data)
        self.highlights = match_highlights(self.data)
        return self.metrics

    def generate_report(self, output_path: Optional[str] = None) -> str:
        if not self.metrics:
            raise ValueError('Ejecute analyze() antes de generar el informe.')

        report_lines: List[str] = []
        report_lines.append('INFORME DE ANÁLISIS DE PARTIDOS')
        report_lines.append('--------------------------------')
        report_lines.append(f"Partidos analizados: {self.metrics['partidos_analizados']}")
        report_lines.append(f"Goles totales: {self.metrics['goles_totales']}")
        report_lines.append(f"Goles promedio por partido: {self.metrics['goles_promedio_por_partido']:.2f}")
        report_lines.append(f"Tarjetas amarillas: {self.metrics['tarjetas_amarillas']}")
        report_lines.append(f"Tarjetas rojas: {self.metrics['tarjetas_rojas']}")
        report_lines.append(f"Posesión local promedio: {self.metrics['posesion_local_promedio']:.1f}%")
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

    def generate_html_report(self, output_path: str, image_folder: Optional[str] = None) -> str:
        if not self.metrics:
            raise ValueError('Ejecute analyze() antes de generar el informe HTML.')

        report_file = Path(output_path)
        report_file.parent.mkdir(parents=True, exist_ok=True)

        image_folder_path = Path(image_folder) if image_folder else report_file.parent
        image_folder_path.mkdir(parents=True, exist_ok=True)

        images = self.save_visual_report(str(image_folder_path))
        relative_images = [Path(img).name for img in images]

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
            f'      <div class="metric"><strong>Tarjetas amarillas</strong><p>{self.metrics["tarjetas_amarillas"]}</p></div>',
            f'      <div class="metric"><strong>Tarjetas rojas</strong><p>{self.metrics["tarjetas_rojas"]}</p></div>',
            f'      <div class="metric"><strong>Posesión local promedio</strong><p>{self.metrics["posesion_local_promedio"]:.1f}%</p></div>',
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
            self.highlights[['date', 'local_team', 'visitante_team', 'goles_local', 'goles_visitante', 'goles_totales']]
                .to_html(index=False, classes='dataframe', border=0),
            '  </div>',
            '  <div class="section">',
            '    <h2>Gráficos</h2>',
        ]

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

        paths = [
            plot_goals_distribution(self.data, str(report_folder / 'goals_distribution.png')),
            plot_possession_distribution(self.data, str(report_folder / 'possession_distribution.png')),
            plot_card_statistics(self.data, str(report_folder / 'card_summary.png')),
        ]

        return paths
