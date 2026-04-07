import argparse
from pathlib import Path

from .agent import SportsAgent


def parse_args():
    parser = argparse.ArgumentParser(description='Ejecuta el agente de análisis deportivo')
    parser.add_argument('--data', required=True, help='Ruta al archivo CSV de partidos')
    parser.add_argument('--output', default='reports/report.txt', help='Ruta de salida para el informe de texto')
    parser.add_argument('--html-output', default=None, help='Ruta de salida para el informe HTML')
    parser.add_argument('--visual', default='reports', help='Carpeta de salida para gráficos')
    return parser.parse_args()


def main():
    args = parse_args()
    agent = SportsAgent(args.data)
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
