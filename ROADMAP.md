# ROADMAP — Agente Deportivo

Mejoras ordenadas por prioridad. Cada fase debe completarse antes de avanzar a la siguiente.
Estado actualizado: abril 2026.

---

## Fase 1 — Fundamentos `[✅ COMPLETADA]`

Mejoras que no cambian la arquitectura pero aumentan la calidad y utilidad de lo que ya existe.
Todas son cambios acotados, de bajo riesgo y alto retorno inmediato.

| # | Mejora | Descripción | Estado |
|---|--------|-------------|--------|
| 1.1 | **`--top-n N`** | Número configurable de equipos/jugadores en todos los rankings (actualmente hardcoded a 5) | ✅ Completado |
| 1.2 | **`--no-charts`** | Omitir generación de gráficos para informes rápidos de solo texto | ✅ Completado |
| 1.3 | **TTL de caché + `--refresh-cache`** | Añadir columna `fetched_at` al CSV. Si los datos tienen más de N días, re-descargar con `--refresh-cache`. Crítico para temporada en curso | ✅ Completado |
| 1.4 | **Rachas máximas históricas** | `compute_team_record` calcula últimos 5 partidos. Añadir: racha sin perder más larga, racha goleadora más larga y racha sin marcar | ✅ Completado |
| 1.5 | **Ratio xG vs goles reales (eficiencia)** | Calcular `overperformance = goles_reales / xG` en modo Equipo y modo Liga. Si >1.2 el equipo sobrerendimiento; si <0.8 infrarrendimiento. Datos ya disponibles en la DB | ✅ Completado |

---

## Fase 2 — Nuevos análisis `[PRÓXIMO]`

Añaden capacidad analítica real sin cambiar la estructura de informes existente.

| # | Mejora | Descripción | Estado |
|---|--------|-------------|--------|
| 2.1 | **Percentiles de liga (modo Equipo)** | Para cada métrica mostrar "percentil X de la liga" además de la comparativa simple. Ej: "Tiros a puerta: 14.2 (percentil 87)". Requiere nueva función `compute_team_percentiles()` | ⬜ Pendiente |
| 2.2 | **Puntos esperados — xPts** | Calcular qué puntos merece cada equipo según sus xG por partido. Tabla de clasificación alternativa en modo Liga | ⬜ Pendiente |
| 2.3 | **`--format json`** | Salida en JSON además de texto/HTML. Permite encadenar el agente con otras herramientas o futuros frontends. Refactorizar `generate_report()` para devolver `dict` | ⬜ Pendiente |
| 2.4 | **`--matchday-range START END`** | Análisis de una franja de jornadas (ej. jornadas 10-20). Actualmente solo se puede analizar una jornada exacta o toda la temporada | ⬜ Pendiente |

---

## Fase 3 — Nuevas visualizaciones `[PLANIFICADO]`

Gráficos que añaden valor informativo con datos que ya se tienen en la DB.

| # | Mejora | Descripción | Estado |
|---|--------|-------------|--------|
| 3.1 | **Shot conversion funnel** | Embudo: tiros totales → tiros a puerta → goles, por equipo o local/visitante. Datos disponibles, solo falta el gráfico | ⬜ Pendiente |
| 3.2 | **Puntos acumulados por jornada (modo Liga)** | Línea temporal para el top-N de equipos mostrando cómo se fue formando la clasificación jornada a jornada | ⬜ Pendiente |
| 3.3 | **Modo `--compare` (dos equipos)** | Nuevo modo: `--compare "Real Madrid" "FC Barcelona"`. Genera radar comparativo, tabla H2H de partidos directos en la DB y diferencias en todas las métricas | ⬜ Pendiente |
| 3.4 | **Mapa de calor de resultados** | Matriz N×N con colores verde/rojo/amarillo para cada par local-visitante. Visual para detectar patrones de dominio entre equipos en una liga | ⬜ Pendiente |

---

## Fase 4 — Soporte de fuentes de datos `[PLANIFICADO]`

| # | Mejora | Descripción | Estado |
|---|--------|-------------|--------|
| 4.1 | **ESPN para UCL / Europa League** | Añadir `"uefa.champions"` y `"uefa.europa"` al dict `_ESPN_LEAGUE` en `player_loader.py`. Actualmente falla silenciosamente con competiciones 2001 y 2146 | ⬜ Pendiente |
| 4.2 | **Fallback TheSportsDB para jugadores** | Si ESPN no tiene el equipo/liga, intentar obtener stats de jugadores desde TheSportsDB como segunda fuente | ⬜ Pendiente |
| 4.3 | **Verificar Primeira Liga / Ligue 1** | Confirmar que los slugs ESPN para competiciones 2017 y 2015 funcionan correctamente (posibles fallos silenciosos no detectados) | ⬜ Pendiente |

---

## Fase 5 — Narrativa automática `[FUTURO]`

Enriquecimiento de los informes con insights generados por reglas, sin necesidad de LLM.

| # | Mejora | Descripción | Estado |
|---|--------|-------------|--------|
| 5.1 | **Sección "Conclusiones" con reglas** | Bloque de insights al final de cada informe: racha positiva/negativa, ataque por encima de media, portero rendimiento, eficiencia ofensiva, etc. Solo condicionales sobre `metrics` ya calculados | ⬜ Pendiente |
| 5.2 | **Narrativa comparativa intertemporada** | Con `--seasons`, generar texto como "En 2024-2025 el equipo mejoró un 23% en tiros a puerta respecto a 2023-2024". Usa datos multi-temporada que ya se procesan | ⬜ Pendiente |

---

## Fase 6 — Evolución arquitectural `[LARGO PLAZO]`

Requieren cambios estructurales significativos. Dependen del crecimiento del proyecto.

| # | Mejora | Descripción | Estado |
|---|--------|-------------|--------|
| 6.1 | **API REST local (FastAPI)** | Exponer los 5 modos como endpoints HTTP. El núcleo analítico ya está desacoplado. Permite integración con cualquier frontend | ⬜ Pendiente |
| 6.2 | **Dashboard Streamlit** | UI web interactiva sobre el mismo motor. Selectores de liga/equipo/jugador, gráficos interactivos con Plotly en lugar de Matplotlib | ⬜ Pendiente |
| 6.3 | **Bot Telegram / Discord** | Responde comandos como `/mallorca jornada 28` generando el informe y enviándolo como imagen al chat | ⬜ Pendiente |

---

## Historial de cambios

| Versión | Fecha | Descripción |
|---------|-------|-------------|
| 1.0 | Abril 2026 | Creación del roadmap inicial |
| 1.1 | Abril 2026 | `--top-n N`: rankings configurables en todos los modos |
| 1.2 | Abril 2026 | `--no-charts`: omitir gráficos, cortocircuitando `save_visual_report` |
| 1.3 | Abril 2026 | TTL de caché: sidecar `.meta.json` con `fetched_at`, `--refresh-cache`, `--cache-ttl N` |
| 1.4 | Abril 2026 | Rachas máximas: sin perder, goleadora y sin marcar en `compute_team_record` |
| 1.5 | Abril 2026 | Ratio xG/goles: `overperformance` en modo Equipo y columna `Over%` en modo Liga |
