import argparse
from pathlib import Path

from .agent import SportsAgent


def parse_args():
    parser = argparse.ArgumentParser(description='Ejecuta el agente de análisis deportivo')
    parser.add_argument('--data', default='data/matches.csv', help='Ruta al archivo CSV de partidos')
    parser.add_argument('--output', default='reports/report.txt', help='Ruta de salida para el informe de texto')
    parser.add_argument('--html-output', default=None, help='Ruta de salida para el informe HTML')
    parser.add_argument('--visual', default='reports', help='Carpeta de salida para gráficos')
    parser.add_argument('--clean-reports', action='store_true', help='Eliminar reportes e imágenes previas en la carpeta de salida antes de generar nuevos archivos')
    parser.add_argument('--fetch-real', action='store_true', help='Obtener datos reales de la API en lugar de usar CSV local')
    parser.add_argument('--competition', type=int, default=2014, help='ID de competición para datos reales (2014=La Liga, 2021=Premier League)')
    parser.add_argument('--season', default='2023', help='Temporada para datos reales (formato YYYY)')
    parser.add_argument('--team', default=None, help='Equipo para filtrar el análisis (ej. Mallorca)')
    return parser.parse_args()


def ensure_inside_folder(file_path: str, folder_path: str) -> str:
    output = Path(file_path)
    folder = Path(folder_path)

    if output.is_absolute() and output.parent == folder:
        return str(output)
    if not output.is_absolute() and output.parent == folder:
        return str(output)

    if output.parent == folder.parent or output.parent == Path('.') or output.parent == Path('reports'):
        return str(folder / output.name)

    return str(output)


def main():
    args = parse_args()
    args.output = ensure_inside_folder(args.output, args.visual)
    if args.html_output:
        args.html_output = ensure_inside_folder(args.html_output, args.visual)

    agent = SportsAgent(args.data, args.fetch_real, args.competition, args.season, args.team)

    if args.clean_reports:
        agent.clean_reports(args.visual)
        print('Reportes anteriores eliminados en:', args.visual)

    agent.load_data()
    agent.analyze()

    report_text = agent.generate_report(output_path=args.output)
    print('Informe de texto generado en:', args.output)

    image_paths = agent.save_visual_report(args.visual)
    print('Gráficos generados en:')
    for path in image_paths:
        print('-', path)

    if args.html_output:
        html_path = agent.generate_html_report(args.html_output, image_folder=args.visual)
        print('Informe HTML generado en:', html_path)


if __name__ == '__main__':
    main()
