# Registro de cambios

Todos los cambios importantes de este proyecto se documentarán en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [2.0.0] — 2026-04-08

### Añadido
- **Informe de Liga** (`--competition` + `--season` sin `--team`): clasificación completa, récords de temporada, estadísticas técnicas por equipo y rendimiento local/visitante. Nuevos gráficos: `league_table.png`, `goals_per_team.png`, `xg_per_team.png`, `home_away_performance.png`.
- **Informe de Jornada** (`--jornada N`): resultados, estadísticas agregadas, clasificación acumulada y sorpresa de la jornada (xG vs resultado real). Nuevos gráficos: `matchday_goals.png`, `matchday_xg.png`.
- **Informe de Partido** (`--match-id ID`): ficha técnica detallada con estadísticas cara a cara, clasificación previa de ambos equipos y análisis narrativo automático. Nuevos gráficos: `match_stats_bar.png`, `match_radar.png`.
- **Informe de Jugador** (`--team` + `--player`): perfil individual de temporada con stats, ratios por partido, ranking en el equipo y gráficos comparativos. Nuevos gráficos: `player_bar.png`, `player_radar.png`.
- `compute_liga_summary()` en `analysis.py`: estadísticas completas de liga, récords y rendimiento local/visitante.
- `compute_matchday_summary()` y `compute_standings()` en `analysis.py`: resumen de jornada y tabla de clasificación acumulada.
- `compute_match_detail()` en `analysis.py`: ficha técnica de partido con contexto clasificatorio.
- `compute_player_profile()` en `analysis.py`: perfil de jugador con ratios, ranking en el equipo y top compañeros.
- `plot_league_table()`, `plot_goals_per_team()`, `plot_xg_per_team()`, `plot_home_away_performance()` en `visualizer.py`.
- `plot_matchday_goals()`, `plot_matchday_xg()` en `visualizer.py`.
- `plot_match_stats_bar()`, `plot_match_radar()` en `visualizer.py`.
- `plot_player_bar()`, `plot_player_radar()` en `visualizer.py`.
- Argumentos `--jornada`, `--match-id` y `--player` en `run_agent.py`.
- Métodos `_generate_liga_report/html`, `_generate_matchday_report/html`, `_generate_match_report/html`, `_generate_player_report/html` en `agent.py`.

### Cambiado
- `agent.py`: la función `analyze()` detecta automáticamente el modo (Liga/Equipo/Jornada/Partido/Jugador) según los argumentos y delega en submétodos especializados.
- `visualizer.py`: añadido `import numpy as np` necesario para los nuevos gráficos de jugador.
- `README.md` y `COMMANDS.md` actualizados con todos los nuevos tipos de informe y argumentos CLI.
- Eliminado `ROADMAP.md` al estar el proyecto completamente implementado.

## [Unreleased]

### Añadido
- `COMMANDS.md` con un conjunto completo de ejemplos de uso y comandos del agente.
- Soporte para filtrar análisis por equipo usando `--team` en `src/run_agent.py`.
- `CHANGELOG.md` para seguir el historial de cambios del proyecto.
- `scripts/fetch_real_data.py` para descargar datasets reales de partidos desde TheSportsDB.
- `scripts/get_current_season.py` para obtener automáticamente la temporada actual de La Liga.
- `src/api_client.py` para gestionar el acceso a la API de TheSportsDB e importar partidos reales.
- Mejoras en `src/agent.py` para análisis filtrado por equipo y generación de informes.
- Actualizaciones en `README.md` documentando los nuevos comandos, uso de API y soporte de temporada actual.

### Cambiado
- `src/run_agent.py` ahora soporta los parámetros `--team`, `--fetch-real`, `--competition` y `--season`.
- Migración de proveedor de datos reales desde Football-Data.org a TheSportsDB.
- `src/api_client.py` ahora usa `THESPORTSDB_API_KEY` y toma `123` como clave pública por defecto.
- Documentación actualizada para reflejar TheSportsDB y el mapeo de IDs legacy de competición.
- `.gitignore` actualizado para ignorar la salida generada en `reports/`.
- Añadido `.env.example` para la configuración de la clave API.

### Corregido
- El filtrado por equipo ahora funciona con nombres parciales en las columnas `local_team` o `visitante_team`.
- Se agregó una ruta de carga segura para que las columnas opcionales de la API no rompan la generación de informes.
