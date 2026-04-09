# ROADMAP — Agente Deportivo

Estado actualizado: abril 2026.
Criterio de priorización: impacto real en producto, seguridad y sostenibilidad relativo al esfuerzo de implementación.

---

## Fases completadas

| Fase | Título | Estado |
|------|--------|--------|
| 1 | Fundamentos CLI (`--top-n`, `--no-charts`, caché TTL, rachas, xG) | ? Completada |
| 2 | Nuevos análisis (percentiles, xPts, `--format json`, `--matchday-range`) | ? Completada |
| 3 | Visualizaciones (funnel, puntos acumulados, `--compare`, heatmap) | ? Completada |
| 4 | Fuentes de datos (ESPN UCL/Europa, fallback TheSportsDB) | ? Completada |
| 5 | Narrativa automática (conclusiones por reglas, comparativa intertemporada) | ? Completada |
| 6 | Arquitectura web (FastAPI + Streamlit + Bot Telegram) | ? Completada |

---

## Fase 7 — Seguridad y robustez `[PRÓXIMA]`

Mejoras críticas antes de exponer el proyecto a usuarios externos.
Bajo esfuerzo, impacto alto en seguridad y estabilidad.

| # | Mejora | Descripción | Esfuerzo |
|---|--------|-------------|---------|
| 7.1 | **Fijar versiones en `requirements.txt`** | Añadir versión exacta a cada dependencia para garantizar reproducibilidad. Evita roturas silenciosas por breaking changes en upstream. | Muy bajo |
| 7.2 | **Rate limiting en la API** | Añadir `slowapi` para limitar peticiones por IP (ej. 10/min en endpoints de informe). Evita abuso de la URL pública de ngrok. | Bajo |
| 7.3 | **Log de accesos beta** | Registrar en consola/fichero cada login del dashboard: usuario y timestamp. Permite detectar accesos no autorizados y revocar claves. | Muy bajo |
| 7.4 | **Manejo de errores en el bot Telegram** | Capturar excepciones de red (ESPN/TheSportsDB) y responder con mensajes amigables en lugar de tracebacks. Añadir mensaje de "datos no disponibles localmente". | Bajo |

---

## Fase 8 — Calidad de código `[ALTA PRIORIDAD]`

Inversión en sostenibilidad del proyecto. Sin esto, el código se vuelve frágil a medida que crece.

| # | Mejora | Descripción | Esfuerzo |
|---|--------|-------------|---------|
| 8.1 | **Tests unitarios para `analysis.py`** | Las funciones `compute_standings`, `compute_overall_metrics`, `compute_team_percentiles` son puras y triviales de testear con `pytest` y DataFrames sintéticos. Target: cubrir las 10 funciones principales. | Medio |
| 8.2 | **Tests de integración para la API** | Usar `TestClient` de FastAPI para verificar que los 6 endpoints responden correctamente con datos de prueba. Detecta regresiones antes de cada push. | Medio |
| 8.3 | **CI con GitHub Actions** | Workflow automático en cada push: check de sintaxis Python + ejecución de tests. Gratuito para repositorios públicos. Falla el PR antes de mergear código roto. | Bajo |
| 8.4 | **Centralizar `COMPETITION_NAMES`** | El mismo diccionario existe en `src/api.py`, `app.py` y `bot.py`. Moverlo a `src/constants.py` e importarlo desde allí. Evita desincronización al añadir ligas. | Muy bajo |

---

## Fase 9 — Experiencia de usuario `[MEDIA PRIORIDAD]`

Mejoras de UX que reducen fricción para betas y futuros usuarios.

| # | Mejora | Descripción | Esfuerzo |
|---|--------|-------------|---------|
| 9.1 | **Indicador de frescura de datos en el dashboard** | Leer la columna `fetched_at` del CSV y mostrar "Datos actualizados hace N días" en el sidebar. El usuario sabe sin esfuerzo si los datos son recientes. | Muy bajo |
| 9.2 | **Descarga de datos desde el dashboard** | Si la DB local no existe, mostrar un botón "Descargar datos" que ejecute `--fetch-real` en background con un spinner. El dashboard pasa a ser autónomo sin necesidad de terminal. | Medio |
| 9.3 | **`/ayuda` contextual en el bot Telegram** | Comando `/ayuda <comando>` que muestra la sintaxis exacta y un ejemplo real de cada comando. Reduce abandono en los primeros minutos de uso. | Muy bajo |
| 9.4 | **Expiración configurable de contraseñas beta** | Añadir fecha de expiración opcional por usuario (`claveJuan:Juan García:2026-05-01`). El dashboard bloquea automáticamente accesos caducados. | Bajo |

---

## Fase 10 — Producto avanzado `[BAJA PRIORIDAD]`

Features con alto impacto de producto pero mayor esfuerzo. Para cuando la base esté estabilizada.

| # | Mejora | Descripción | Esfuerzo |
|---|--------|-------------|---------|
| 10.1 | **Exportar análisis a PDF** | Convertir el HTML que ya genera el agente a PDF con `weasyprint`. Sin reescribir nada. Botón "Descargar PDF" en el dashboard y comando `/pdf` en el bot. | Bajo |
| 10.2 | **Alertas proactivas por Telegram** | El bot es reactivo. Con `APScheduler` y un comando `/suscribir 2014 2024 Mallorca`, podría enviar automáticamente avisos de rachas negativas, jornadas disputadas o caída en tabla. | Alto |
| 10.3 | **Caché de gráficos por hash de datos** | Los PNG se regeneran en cada ejecución aunque los datos no cambien. Calcular un hash del DataFrame de entrada y reutilizar el PNG existente si coincide. | Medio |
| 10.4 | **Aliases en inglés para el bot** | Añadir `/league`, `/team`, `/matchday` como alias de los comandos en español. Sin lógica nueva, solo registrar handlers adicionales. Abre el bot a usuarios no hispanohablantes. | Muy bajo |
| 10.5 | **Modo multi-liga en el dashboard** | Permitir comparar el mismo equipo en diferentes ligas/temporadas en una sola vista. Requiere refactorizar el sidebar para soportar selección múltiple. | Alto |

---

## Historial de versiones

| Versión | Fecha | Descripción |
|---------|-------|-------------|
| 1.0 | Abril 2026 | Fases 1-6 completadas: CLI, análisis, visualizaciones, fuentes de datos, narrativa, web |
| 1.1 | Abril 2026 | Beta access gate en dashboard Streamlit (contraseñas individuales por usuario) |
| 1.2 | Abril 2026 | ROADMAP v2: reescritura con fases 7-10 priorizadas por impacto/esfuerzo |
