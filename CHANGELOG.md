# Registro de cambios

Todos los cambios importantes de este proyecto se documentarán en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [3.0.0] — 2026-04-08

### Añadido

**Fase 1 — Fundamentos**
- `--top-n N`: número configurable de equipos/jugadores en todos los rankings (antes hardcoded a 5).
- `--no-charts`: omitir generación de gráficos para obtener informes de texto rápidos.
- TTL de caché: sidecar `.meta.json` junto a cada CSV con `fetched_at`. Nuevo argumento `--refresh-cache` para forzar re-descarga. Nuevo argumento `--cache-ttl N` para configurar el número de días antes de avisar de desactualización (por defecto 7).
- `compute_team_record()` devuelve ahora tres rachas máximas históricas: `racha_sin_perder_max`, `racha_goleadora_max` y `racha_sin_marcar_max`.
- `overperformance` (ratio goles reales / xG): campo en `compute_overall_metrics()`. Columna `Over%` en la tabla de clasificación del modo Liga. Icono contextual en el informe Equipo.

**Fase 2 — Nuevos análisis**
- `compute_team_percentiles()` en `analysis.py`: percentil de cada métrica del equipo sobre el resto de la liga. Barra visual en HTML y valoración textual en el informe Equipo.
- `compute_xpts()` en `analysis.py`: puntos esperados según modelo Poisson sobre xG por partido. Tabla de clasificación alternativa con diferencia `PTS - xPts` en el modo Liga.
- `--format json`: `generate_json_report()` serializa todos los datos del análisis a JSON con encoder personalizado para DataFrames y tipos numpy. La extensión `.txt` se transforma a `.json` automáticamente.
- `--matchday-range START END`: análisis de una franja de jornadas (ej. jornadas 10–20). Reutiliza el pipeline de Liga con título "INFORME DE RANGO".

**Fase 3 — Nuevas visualizaciones**
- `plot_shot_funnel()`: embudo de conversión tiros totales → tiros a puerta → goles para local y visitante.
- `plot_points_evolution()`: línea temporal de puntos acumulados por jornada para el top-N de equipos.
- Modo `--compare TEAM1 TEAM2`: nuevo modo de informe con radar comparativo, tabla H2H de enfrentamientos directos y diferencias en todas las métricas. Texto (`_generate_compare_report`) y HTML (`_generate_compare_html_report`) en `agent.py`. Función `compute_head_to_head()` en `analysis.py`.
- `plot_results_heatmap()`: mapa de calor N×N con resultado medio para cada par local–visitante.

**Fase 4 — Soporte de fuentes de datos**
- `player_loader.py`: mapa `_ESPN_LEAGUE` extendido con `2001: "uefa.champions"` y `2146: "uefa.europa"`.
- `_fetch_roster_thesportsdb()`: fallback a TheSportsDB cuando ESPN no tiene el equipo/liga. Cargado automáticamente si `team_id` es `None` en ESPN.
- Variable de entorno `THESPORTSDB_API_KEY` leída con `python-dotenv` en `player_loader.py`.

**Fase 5 — Narrativa automática**
- `_generate_conclusions()` / `_generate_conclusions_html()` en `agent.py`: bloque "Conclusiones" al final de todos los informes Equipo y Liga. Muestra siempre la forma reciente (últimos 5 partidos), balance global con etiqueta contextual, promedios ofensivo/defensivo, eficiencia xG y percentiles extremos de liga.
- `_generate_interseason_narrative()` en `agent.py`: con `--seasons`, compara métricas clave (GF/GC/xG/tiros/posesión) entre la primera y última temporada con variación porcentual y etiqueta Mejora/Empeora/Sin cambio significativo.

### Cambiado
- `agent.py`: `analyze()` soporta ahora un séptimo modo (`compare`) además de los cinco originales.
- `run_agent.py`: añadidos argumentos `--compare`, `--top-n`, `--no-charts`, `--refresh-cache`, `--cache-ttl`, `--matchday-range` y `--format`.
- `README.md` y `COMMANDS.md` actualizados con todos los nuevos modos, argumentos y ejemplos.
- `ROADMAP.md` actualizado: Fases 1–5 marcadas como completadas.

### Corregido
- Bug en `_generate_conclusions()` modo Liga: `escolta` es una pandas `Series`, comparación `if escolta is not None` en lugar de `if escolta` para evitar `ValueError: The truth value of a Series is ambiguous`.
- `compute_team_record()`: ordenación multi-temporada usa `['season', 'jornada']` para preservar el orden cronológico correcto al combinar varias temporadas con `--seasons`.

---

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
