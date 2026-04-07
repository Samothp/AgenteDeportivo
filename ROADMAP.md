# Hoja de ruta — Agente Deportivo

## Prioridad Alta

### ✅ 1. Evolución temporal por jornada
**Estado:** Completado  
**Objetivo:** Añadir gráficos de línea que muestren la evolución de las métricas clave (goles, xG, tiros, posesión) partido a partido a lo largo de la temporada.  
**Cambios previstos:**
- `visualizer.py` → `plot_temporal_evolution(df, team, output_path)`
- `agent.py` → incluir el nuevo gráfico en informe visual y HTML
- El eje X es la jornada (`jornada`), el eje Y la métrica seleccionada

---

### ✅ 2. Comparativa equipo vs media de la liga
**Estado:** Completado  
**Objetivo:** Contextualizar las métricas del equipo frente a la media de todos los equipos de la competición. Sin contexto, un "12.3 tiros de media" no significa nada.  
**Cambios previstos:**
- `agent.py` → conservar `self.full_data` antes de filtrar por equipo
- `analysis.py` → `compute_comparison_metrics(team_df, league_df)`
- Informe texto y HTML → sección "vs Liga" con diferencia +/- por métrica

---

## Prioridad Media

### ✅ 3. Listado de equipos disponibles (`--list-teams`)
**Estado:** Completado  
**Objetivo:** Mostrar qué equipos hay en la DB para una competición y temporada dadas, evitando errores de tipeo al usar `--team`.  
**Cambios previstos:**
- `run_agent.py` → argumento `--list-teams` que solo imprime los equipos y termina
- `data_loader.py` → función `list_available_teams(competition_id, season)`

---

### ✅ 4. Resultados W/D/L y racha actual del equipo
**Estado:** Completado  
**Objetivo:** Lo más básico del fútbol: victorias, empates, derrotas, y cuál es la racha de los últimos N partidos. Actualmente no figura en ningún informe.  
**Cambios previstos:**
- `analysis.py` → `compute_team_record(df, team)` con W/D/L, puntos, racha últimos 5
- Informe texto y HTML → sección "Rendimiento" con tabla de resultados cronológica

---

## Prioridad Baja

### ✅ 5. Soporte multi-temporada en un solo reporte
**Estado:** Completado  
**Objetivo:** Comparar el rendimiento de un equipo entre temporadas distintas (ej. Mallorca 24-25 vs 25-26).  
**Cambios previstos:**
- `run_agent.py` → `--seasons 2024 2025` (lista de temporadas)
- `data_loader.py` → cargar y unir múltiples DBs
- Gráficos con distinción por temporada (color/trazo diferente)

---

### ✅ 6. Deprecar/actualizar `scripts/`
**Estado:** Completado  
**Objetivo:** Los scripts `fetch_real_data.py` y `get_current_season.py` escriben en CSVs planos que ya no son el formato de la DB local. Generan confusión.  
**Cambios previstos:**
- Reescribir para que usen `load_match_data()` con `fetch_real=True`
- O eliminarlos si ya no aportan valor frente al CLI principal
