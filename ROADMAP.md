# ROADMAP — Tipos de Informes

Evolución del sistema de reportes del agente deportivo.  
Estado actual: ✅ implementado · 🔲 pendiente

---

## Tipos de informe planificados

| Tipo       | Argumento CLI           | Estado |
|------------|-------------------------|--------|
| **Equipo** | `--team Mallorca`        | ✅     |
| **Jornada**| `--jornada 10`           | ✅     |
| **Partido**| `--match-id 2279399`     | ✅     |
| **Liga**   | *(ninguno extra)*        | ✅     |
| **Jugador**| `--player "Vedat Muriqi"`| ✅     |

---

## Fase 0 — Reporte Equipo (✅ completado)

Filtro: `--team <nombre>` sobre la DB de partidos + ESPN roster.

### Secciones
- Resumen general: PJ, goles a favor/contra, tarjetas, posesión, asistencia, árbitro
- Estadísticas técnicas promedio (tiros, xG, corners, faltas, paradas, precisión pases)
- Comparativa vs liga (tabla diferencial)
- Historial W/D/L con racha últimos 5
- Partidos destacados (goleadas, empates espectaculares)
- **Top goleadores** del equipo (ESPN)
- **Top asistentes** del equipo (ESPN)

### Gráficos
- `goals_distribution.png` — distribución de goles por partido
- `possession_distribution.png` — caja de posesión local/visitante
- `card_summary.png` — resumen de tarjetas
- `xg_per_match.png` — xG por partido
- `shots_comparison.png` — tiros promedio local vs visitante
- `temporal_evolution.png` — evolución por jornada

---

## Fase 1 — Reporte Liga (✅ completado)

> Commit `(pendiente)` — `feat(liga): reporte de liga con clasificacion, records y graficos`

**Implementado:**
- `compute_liga_summary()` en `analysis.py`
- `plot_league_table()`, `plot_goals_per_team()`, `plot_xg_per_team()`, `plot_home_away_performance()` en `visualizer.py`
- `_generate_liga_report()`, `_generate_liga_html_report()` en `agent.py`
- Modo Liga activado automáticamente cuando no se indica `--team`, `--jornada` ni `--match-id`

<!-- spec original -->

**Propósito:** panorama completo de la temporada en la competición.  
**Filtro:** sin `--team`, sin `--jornada`. Solo `--competition` y `--season`.

### Secciones propuestas
1. **Cabecera**: competición, temporada, jornadas disputadas, partidos totales
2. **Resumen de goles**: totales, promedio por partido, partido más goleador
3. **Tabla de clasificación** (calculada desde la DB): PJ G E P GF GC DIF PTS
4. **Ranking goleadores de la liga** (top 10 por equipo vía ESPN, combinado)
5. **Ranking asistentes de la liga** (top 10 por equipo vía ESPN, combinado)
6. **Estadísticas técnicas por equipo**: tiros, xG, posesión (tabla comparativa)
7. **Récords de la temporada**:
   - Racha de victorias más larga
   - Equipo más goleador / menos goleado
   - Partido con mayor asistencia de público
   - Árbitro con más partidos dirigidos
8. **Top equipos con más goles** (actual `top_scoring_teams`)
9. **Top equipos con menos goles concedidos** (actual `top_defensive_teams`)

### Gráficos nuevos
- `league_table.png` — tabla de clasificación visual (barras horizontales PTS)
- `goals_per_team.png` — goles a favor/contra por equipo (barras apiladas)
- `xg_per_team.png` — xG acumulado por equipo
- `home_away_performance.png` — rendimiento local vs visitante por equipo

### Datos requeridos
- Todos disponibles en `data/db_{competition}_{season}.csv`
- Para rankings de jugadores: ESPN API (todos los equipos, O(20) llamadas)

### CLI
```bash
python -m src.run_agent --competition 2014 --season 2025 \
  --output reports/laliga_2025.txt --html-output reports/laliga_2025.html \
  --visual reports/laliga_2025
```
*(comportamiento actual sin `--team` ya genera informe parcial de liga; esta fase lo enriquece)*

---

## Fase 2 — Reporte Jornada (✅ completado)

> Commit `a0aa3ef` — `feat(jornada): reporte de jornada con resultados, clasificacion acumulada y graficos`

**Implementado:**
- `compute_standings()` y `compute_matchday_summary()` en `analysis.py`
- `plot_matchday_goals()` y `plot_matchday_xg()` en `visualizer.py`
- `filter_by_matchday()`, `_generate_matchday_report()`, `_generate_matchday_html_report()` en `agent.py`
- Argumento `--jornada` en `run_agent.py`

<!-- spec original -->

**Propósito:** análisis de todos los partidos de una jornada concreta.  
**Filtro:** `--jornada <N>` (columna `jornada` en la DB).

### Secciones propuestas
1. **Cabecera**: competición, temporada, nº jornada, fecha(s)
2. **Resultados de la jornada**: tabla local — goles — visitante — resultado
3. **Estadísticas agregadas de la jornada**:
   - Goles totales, promedio, máximo goleador de la jornada
   - Tarjetas totales (amarillas/rojas)
   - Posesión media local vs visitante
4. **Partido más espectacular** (más goles, mayor xG total)
5. **Estadísticas técnicas destacadas**: equipo con más tiros, más posesión, más corners
6. **Tabla de clasificación acumulada** hasta esa jornada
7. **Sorpresa de la jornada**: resultado más inesperado (mayor diferencia xG vs resultado real)

### Gráficos nuevos
- `matchday_results.png` — tabla visual de resultados (heatmap o barras)
- `matchday_goals.png` — goles por partido de la jornada
- `matchday_xg.png` — xG local vs visitante por partido (scatter o barras agrupadas)

### Datos requeridos
- Columna `jornada` ya presente en la DB ✅
- Columna `xg_local` / `xg_visitante` ya presente ✅

### CLI
```bash
python -m src.run_agent --competition 2014 --season 2025 --jornada 15 \
  --output reports/jornada_15.txt --html-output reports/jornada_15.html \
  --visual reports/jornada_15
```

---

## Fase 3 — Reporte Partido � (en progreso)

**Propósito:** ficha técnica completa de un partido específico.  
**Filtro:** `--match-id <id_event>` (columna `id_event` en la DB).

### Secciones propuestas
1. **Cabecera**: fecha, estadio, árbitro, competición, jornada, espectadores
2. **Resultado final** (grande, destacado)
3. **Estadísticas comparativas** (tabla cara a cara):

   | Stat | Local | Visitante |
   |------|-------|-----------|
   | Tiros totales | — | — |
   | Tiros a puerta | — | — |
   | xG | — | — |
   | Posesión % | — | — |
   | Corners | — | — |
   | Faltas | — | — |
   | Fueras de juego | — | — |
   | Paradas portero | — | — |
   | Pases precisos | — | — |
   | Tarjetas amarillas | — | — |
   | Tarjetas rojas | — | — |

4. **Análisis narrativo automático**: texto generado desde las stats ("El equipo local dominó la posesión con un X% pero fue superado en xG…")
5. **Enlace a highlights** (`video_highlights` si disponible)
6. **Contexto en la liga**: posición de ambos equipos antes del partido

### Gráficos nuevos
- `match_radar.png` — radar chart (spider) local vs visitante (6-8 métricas normalizadas)
- `match_stats_bar.png` — barras horizontales enfrentadas (como en TV)

### Datos requeridos
- Todos disponibles en la DB ✅
- Para contexto clasificación: calcular tabla hasta la jornada anterior

### CLI
```bash
python -m src.run_agent --competition 2014 --season 2025 --match-id 2279399 \
  --output reports/partido_2279399.txt --html-output reports/partido_2279399.html \
  --visual reports/partido_2279399
```

---

## Fase 4 — Reporte Jugador ✅ (completado)

> Commit → `feat(jugador): reporte de jugador con perfil, rankings y graficos`

**Implementado:**
- `compute_player_profile()` en `analysis.py`
- `plot_player_bar()` y `plot_player_radar()` en `visualizer.py`
- `_generate_player_report()`, `_generate_player_html_report()` en `agent.py`
- Argumento `--player` en `run_agent.py`
- Modo Jugador activado cuando se combinan `--team` y `--player`

<!-- spec original -->  
**Filtro:** `--player <nombre>` (búsqueda parcial en el CSV de jugadores ESPN).

### Secciones propuestas
1. **Cabecera**: nombre, equipo, posición (en español), temporada
2. **Estadísticas de la temporada**:
   - Partidos jugados
   - Goles / Asistencias / G+A
   - Tiros a puerta
   - Tarjetas amarillas / rojas
3. **Ratios calculados**:
   - Minutos estimados por gol (si disponible)
   - Goles por partido jugado
   - Asistencias por partido jugado
   - % partidas con participación en gol
4. **Comparativa con el equipo**: posición en rankings de goleadores y asistentes
5. **Comparativa con la posición**: vs media de jugadores de su posición en el equipo
6. **Evolución temporal** *(requiere datos por partido — actualmente ESPN solo da totales)*:
   - Acumulado de goles/asistencias por jornada (si se implementa scraping adicional)

### Gráficos nuevos
- `player_radar.png` — radar con métricas normalizadas vs media del equipo
- `player_bar.png` — barra comparativa goles/asistencias vs promedio de posición

### Datos requeridos (actuales)
- `data/players_{competition}_{season}.csv` (ESPN): goals, assists, appearances, shots_on_target, yellow_cards, red_cards ✅
- Datos por partido del jugador: **NO disponibles** en ESPN API pública → se necesita fuente adicional o se omite la evolución temporal

### Limitación conocida
ESPN API solo devuelve totales de temporada, no stats partido a partido. La evolución temporal quedaría **pendiente de fase posterior** si se encuentra fuente alternativa.

### CLI
```bash
python -m src.run_agent --competition 2014 --season 2025 \
  --team Mallorca --player "Vedat Muriqi" \
  --output reports/muriqi.txt --html-output reports/muriqi.html \
  --visual reports/muriqi
```
*(requiere `--team` para cargar el CSV ESPN del equipo correcto)*

---

## Orden de implementación sugerido

| Prioridad | Fase | Complejidad | Valor | Estado |
|-----------|------|-------------|-------|--------|
| 1 | **Jornada** | Baja — datos 100% en DB | Alto — uso frecuente | ✅ |
| 2 | **Partido** | Media — radar chart nuevo | Alto — ficha detallada | ✅ |
| 3 | **Liga** | Media — tabla clasificación + rankings multi-equipo | Alto — visión global | ✅ |
| 4 | **Jugador** | Media — datos ya disponibles (ESPN) | Medio — datos limitados | ✅ |

---

## Cambios transversales requeridos

### `src/run_agent.py`
- Añadir argumentos: `--jornada`, `--match-id`, `--player`
- Lógica de detección del tipo de informe:
  ```
  team + player  → Jugador
  team (solo)    → Equipo        ← actual
  jornada        → Jornada
  match-id       → Partido
  (ninguno)      → Liga
  ```

### `src/analysis.py`
- `compute_league_table(df)` → tabla de clasificación
- `compute_matchday_summary(df, jornada)` → stats de la jornada
- `compute_match_detail(df, match_id)` → ficha de partido (cara a cara)
- `compute_player_profile(df_players, player_name)` → perfil individual

### `src/agent.py`
- Refactorizar `analyze()` y `generate_report()` para delegar a submétodos por tipo
- O crear subclases: `LeagueAgent`, `MatchdayAgent`, `MatchAgent`, `PlayerAgent`

### `src/visualizer.py`
- `plot_league_table(standings)` — barras horizontales PTS
- `plot_match_radar(stats_local, stats_visitante)` — spider chart
- `plot_matchday_results(df_jornada)` — tabla visual
- `plot_player_radar(player_stats, team_avg)` — radar jugador

### `COMMANDS.md`
- Documentar los nuevos argumentos y ejemplos por tipo de informe

---

## Notas de implementación

- **Tipos mutuamente excluyentes**: si se pasa `--match-id`, ignorar `--team` / `--jornada`
- **Validación de argumentos** en `run_agent.py` con mensajes de error claros
- **Caché de datos** de jugadores por equipo (ya existe); para informe Liga necesitará todos los equipos (~20 llamadas ESPN, ~15s)
- **Compatibilidad hacia atrás**: el comportamiento actual con solo `--team` debe seguir igual tras la refactorización
