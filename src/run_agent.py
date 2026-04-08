import argparse
import sys
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
    parser.add_argument('--jornada', type=int, default=None, help='Número de jornada (genera informe de jornada)')
    parser.add_argument('--match-id', type=int, default=None, dest='match_id', help='ID del partido (id_event) para generar informe de partido')
    parser.add_argument('--player', type=str, default=None, help='Nombre del jugador para informe individual (requiere --team)')
    parser.add_argument('--list-teams', action='store_true', help='Lista los equipos disponibles en la DB local para la competition+season indicada y termina')
    parser.add_argument('--seasons', nargs='+', default=None, metavar='YEAR', help='Lista de temporadas a combinar en un solo análisis (ej. --seasons 2024 2025). Tiene prioridad sobre --season')
    parser.add_argument('--top-n', type=int, default=5, dest='top_n', help='Número de equipos/jugadores en los rankings (por defecto: 5)')
    parser.add_argument('--no-charts', action='store_true', dest='no_charts', help='Omitir la generación de gráficos (modo texto rápido)')
    parser.add_argument('--refresh-cache', action='store_true', dest='refresh_cache', help='Eliminar el caché local y re-descargar desde la API (implica --fetch-real)')
    parser.add_argument('--cache-ttl', type=int, default=7, dest='cache_ttl_days', help='Días antes de avisar que el caché está desactualizado (por defecto: 7)')
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

    # --list-teams: mostrar equipos disponibles y salir
    if args.list_teams:
        from .data_loader import list_available_teams
        teams = list_available_teams(args.competition, args.season)
        if not teams:
            print(f'No hay DB local para competition={args.competition} season={args.season}.')
            print('Usa --fetch-real para descargar los datos primero.')
            sys.exit(1)
        print(f'Equipos disponibles (competition={args.competition}, season={args.season}):')
        for name in teams:
            print(f'  {name}')
        sys.exit(0)

    args.output = ensure_inside_folder(args.output, args.visual)
    if args.html_output:
        args.html_output = ensure_inside_folder(args.html_output, args.visual)

    # --refresh-cache implica --fetch-real
    if args.refresh_cache:
        args.fetch_real = True

    agent = SportsAgent(args.data, args.fetch_real, args.competition, args.season, args.team, seasons=args.seasons, matchday=args.jornada, match_id=args.match_id, player=args.player, top_n=args.top_n, no_charts=args.no_charts, refresh_cache=args.refresh_cache, cache_ttl_days=args.cache_ttl_days)

    if args.clean_reports:
        agent.clean_reports(args.visual)
        print('Reportes anteriores eliminados en:', args.visual)

    agent.load_data()
    agent.analyze()

    report_text = agent.generate_report(output_path=args.output)
    print('Informe de texto generado en:', args.output)

    image_paths = agent.save_visual_report(args.visual)
    if image_paths:
        print('Gráficos generados en:')
        for path in image_paths:
            print('-', path)
    elif args.no_charts:
        print('Gráficos omitidos (--no-charts activo).')

    if args.html_output:
        html_path = agent.generate_html_report(args.html_output, image_folder=args.visual)
        print('Informe HTML generado en:', html_path)


if __name__ == '__main__':
    main()
