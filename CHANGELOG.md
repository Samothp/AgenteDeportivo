# Registro de cambios

Todos los cambios importantes de este proyecto se documentarán en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Añadido

- **Restricción de acceso al bot por membresía a grupo de Telegram**: nuevo mecanismo de control de acceso opcional. Si se define la variable de entorno `ALLOWED_GROUP_ID`, todos los comandos del bot (excepto `/start`) verifican que el usuario es miembro activo del grupo indicado usando `get_chat_member`. Los usuarios no autorizados reciben un mensaje `⛔ No tienes acceso…` y el intento queda registrado en el log. Cuando `ALLOWED_GROUP_ID` está vacío, el bot funciona sin restricciones como antes. Se añade `ALLOWED_GROUP_ID` al fichero `.env.example`.
- **Prefetch de escudos al seleccionar equipo (RoadmapDashboard #10)**: nueva función `_prefetch_team_assets(team_name, competition_id)` en `app.py`. Cuando el usuario cambia el selector de equipo en los tabs Equipo, Jugador y Compare, se lanza un hilo daemon que llama a `get_team_assets()` en segundo plano. El escudo queda en caché local antes de que el usuario pulse el botón de generar informe. Se evitan hilos duplicados con una clave en `st.session_state`.
- **URL params para compartir informes (RoadmapDashboard #11)**: `st.query_params` se actualiza automáticamente cada vez que se genera un informe, serializando `comp`, `season`, `tab`, y según el modo: `team`, `player`, `matchday`, `match_id`, `t1`/`t2`. Al abrir el dashboard con esos parámetros en la URL, `_init_from_url_params()` pre-rellena los widgets (competición, temporada, equipo, jugador, jornada, etc.) en la primera carga. Se añade `key="sidebar_competition"` y `key="sidebar_season"` a los widgets del sidebar para que sean hidratables desde `st.session_state`.
- **Timestamp del informe en el área principal (RoadmapDashboard #12)**: al generar un informe se guarda `datetime.now()` en `st.session_state`. Justo debajo de las métricas aparece `🕒 Datos analizados el DD/MM/YYYY a las HH:MM:SS` como `st.caption`. El timestamp solo se muestra si hay un informe generado (no en el estado inicial de bienvenida).

### Cambiado

- **`_display_metrics` adaptada al modo activo (RoadmapDashboard #3)**: la función ya no muestra siempre las mismas 8 métricas. Ahora despacha un conjunto diferente según `payload["modo"]`:
  - **liga**: goles/partido en liga, total goles, xG/tiros/posesión promedio y corners/partido.
  - **equipo**: victorias/empates/derrotas, puntos, goles a favor y encajados por partido, xG, posesión y overperformance.
  - **jugador**: partidos jugados, minutos, goles, asistencias, goles/90 y asistencias/90 (calculados si hay minutos disponibles).
  - **jornada / partido / compare**: métricas genéricas del equipo de contexto (goles, xG, posesión, overperformance).
- **Radar visual al inicio del modo Compare (RoadmapDashboard #9)**: en `_tab_run_and_display`, para modo compare, el fichero `compare_radar.png` (ya generado por `plot_compare_radar`) se extrae de `image_paths` y se muestra centrado en 3 columnas con título `📊 Radar comparativo — Equipo1 vs Equipo2`, antes de las tablas H2H. Se añaden también tablas `stats_team1`/`stats_team2` en `_display_mode_results` si están en el payload.
- **Cotización de mercado en modo Jugador (RoadmapDashboard #8)**: nueva caché local `data/market_values.json`. Funciones `_load_market_values()` y `_save_market_value()` en `app.py`. En el perfil de jugador se muestra el valor registrado (formateado como `€ X.XXX.XXX`) con fuente y fecha de actualización, y un expander `✏️ Establecer / actualizar valor de mercado` con `st.number_input` para que el operador edite manualmente el dato sin depender de scraping externo.
- **Stats per-90 en modo Jugador (RoadmapDashboard #7)**: nueva función en `compute_player_profile` que calcula `minutos_estimados` (appearances × 90), `goles_90`, `asistencias_90`, `ga_90` y `sot_90`. En `app.py`, `_display_metrics` (modo jugador) ahora usa las claves reales del payload (`appearances/goals/assists`) en lugar de las alias erróneas (`pj/goles/asistencias`), y col3/col4 muestran directamente las stats per-90. `_display_mode_results` corrige asimismo `nombre`→`player_name` y añade una fila de 4 métricas per-90 con nota al pie sobre la estimación.
- **Evolución temporal prominente en modo Equipo (RoadmapDashboard #6)**: en `_tab_run_and_display`, para modo equipo, el gráfico `temporal_evolution.png` (ya generado por `plot_temporal_evolution`) se extrae de `image_paths` y se muestra en una sección destacada `📈 Evolución por jornada` antes de las tablas, con `use_container_width=True`. El resto de gráficos sigue apareciendo al final como hasta ahora.
- **Forma reciente en clasificación de liga (RoadmapDashboard #5)**: nueva función `compute_team_form(df, team, last_n=5)` en `analysis.py`. Devuelve los últimos 5 resultados de cada equipo como emojis (🟢 victoria · ⚪ empate · 🔴 derrota). La columna `Forma` se añade automáticamente al DataFrame `clasificacion` dentro de `compute_liga_summary()` y fluye sin cambios al payload JSON y a la tabla del dashboard.
- **Tablas con `column_config` y barras de progreso (RoadmapDashboard #4)**: `_show_table()` ahora aplica `st.column_config` automáticamente sobre tablas de listas de diccionarios.
  - Barras de progreso para columnas de puntos, goles y posesión (detección por nombre de columna).
  - Formato de porcentajes consistente (`%.1f%%`) y normalización automática cuando los datos vienen en escala 0–1.
  - Unificación de renderizado en percentiles de liga usando `_show_table()` para mantener formato y UX homogénea.

---

## [5.0.0] — 2026-04-10

### Añadido

**Fase 12 — Producto II**

- **12.1 — Templates Jinja2 para informes HTML**: creado `src/templates/` con 6 plantillas `.html.j2` (`base`, `liga`, `compare`, `match`, `matchday`, `player`). Los 5 métodos `_generate_*_html_report()` (>200 líneas de f-strings c/u) sustituidos por versiones de ~40 líneas que preparan un contexto y llaman a `_render_template()`. Nuevo classmétodo `_get_jinja_env()` con caché en `SportsAgent`. Autoescape activado para seguridad XSS; las cadenas HTML pre-generadas se pasan con el filtro `| safe`.
- **12.2 — Paginación con inline keyboards en el bot Telegram**: nuevo sistema `_page_cache` (dict MD5 → lista de páginas). Funciones `_cache_pages()`, `_page_keyboard()` y `_send_paged()`. Nuevo handler `callback_page()` registrado con `CallbackQueryHandler` para manejar callbacks `page:<key>:<n>` y `noop`. Los comandos `/liga`, `/equipo`, `/jornada` y `/compare` usan `_send_paged()` en lugar de fragmentar el texto en múltiples mensajes.
- **12.3 — Autenticación X-API-Key en la API REST**: nueva dependencia `_require_api_key()` con `Depends(Header(...))` aplicada a todos los endpoints `/report/*`. La variable `API_REST_KEY` en `.env` activa la autenticación; si no está definida, la API funciona en modo desarrollo sin restricciones. Los endpoints públicos `/` y `/teams` no requieren clave. Añadida instrucción en `.env.example`.
- **12.4 — Radar comparativo en modo multi-liga**: nueva función `plot_multi_league_radar(leagues, output_path)` en `visualizer.py`. Normaliza cada métrica 0–1 sobre el máximo entre ligas y dibuja polígonos polares superpuestos con paleta `tab10`. En el dashboard, tras las tabs de clasificación, se muestra una sección de radar comparativo entre las ligas seleccionadas.
- **12.5 — Exportar a Excel desde el dashboard**: nueva función `_payload_to_excel(payload)` en `app.py` que convierte las secciones del payload JSON en hojas de un workbook `openpyxl`. El botón PDF se acompaña ahora de un `st.download_button` para descargar el Excel directamente desde el navegador.

### Dependencias añadidas

- `jinja2==3.1.6` — motor de plantillas HTML
- `openpyxl==3.1.5` — generación de Excel desde el dashboard

---

## [4.0.0] — 2026-04-09

### Añadido

**Fase 10 — Producto avanzado**

- **10.1 — Exportar a PDF**: método `generate_pdf_report()` en `src/agent.py` usando `weasyprint`. Genera primero el HTML y lo convierte a PDF. Botón "Generar PDF" en el dashboard con descarga directa (`st.download_button`). Comando `/pdf <comp> <season>` en el bot que envía el archivo como documento Telegram.
- **10.2 — Alertas proactivas Telegram**: nuevos comandos `/suscribir`, `/suscripciones` y `/desuscribir`. Las suscripciones se persisten en `data/subscriptions.json`. `APScheduler BackgroundScheduler` con job diario (hora configurable con `ALERT_HOUR` en `.env`) que detecta equipos con ≥3 derrotas consecutivas y notifica automáticamente. Estado previo en `data/alert_state.json` para no reenviar la misma alerta.
- **10.3 — Caché de gráficos por hash**: función `_df_hash()` en `src/agent.py` calcula un MD5 estable del DataFrame con `pd.util.hash_pandas_object`. En `save_visual_report()`, si existe `.chart_cache` con el mismo hash, se devuelven los PNG existentes sin regenerarlos.
- **10.4 — Aliases en inglés para el bot**: `/help`, `/competitions`, `/teams`, `/league`, `/team`, `/matchday` registrados como `CommandHandler` adicionales en `main()`.
- **10.5 — Modo multi-liga en el dashboard**: checkbox "🔀 Comparar múltiples ligas" en el sidebar. Al activarse, muestra 3 filas (competición + temporada) y un botón "▶ Comparar ligas". El área principal muestra un `st.tabs` con clasificación y KPIs por competición.

### Dependencias añadidas

- `weasyprint==63.1` — conversión HTML → PDF
- `apscheduler==3.11.0` — scheduler de alertas proactivas

---

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
