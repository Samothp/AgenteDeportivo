# ROADMAP � Agente Deportivo

Estado actualizado: abril 2026.
Criterio de priorizaci�n: impacto real en producto, seguridad y sostenibilidad relativo al esfuerzo de implementaci�n.

---

## Fases completadas

| Fase | T�tulo | Estado |
|------|--------|--------|
| 1 | Fundamentos CLI (`--top-n`, `--no-charts`, cach� TTL, rachas, xG) | ? Completada |
| 2 | Nuevos an�lisis (percentiles, xPts, `--format json`, `--matchday-range`) | ? Completada |
| 3 | Visualizaciones (funnel, puntos acumulados, `--compare`, heatmap) | ? Completada |
| 4 | Fuentes de datos (ESPN UCL/Europa, fallback TheSportsDB) | ? Completada |
| 5 | Narrativa autom�tica (conclusiones por reglas, comparativa intertemporada) | ? Completada |
| 6 | Arquitectura web (FastAPI + Streamlit + Bot Telegram) | ? Completada |

---

## Fase 7 � Seguridad y robustez `[PR�XIMA]`

Mejoras cr�ticas antes de exponer el proyecto a usuarios externos.
Bajo esfuerzo, impacto alto en seguridad y estabilidad.

| # | Mejora | Descripci�n | Esfuerzo |
|---|--------|-------------|---------|
| 7.1 | **Fijar versiones en `requirements.txt`** | A�adir versi�n exacta a cada dependencia para garantizar reproducibilidad. Evita roturas silenciosas por breaking changes en upstream. | Muy bajo |
| 7.2 | **Rate limiting en la API** | A�adir `slowapi` para limitar peticiones por IP (ej. 10/min en endpoints de informe). Evita abuso de la URL p�blica de ngrok. | Bajo |
| 7.3 | **Log de accesos beta** | Registrar en consola/fichero cada login del dashboard: usuario y timestamp. Permite detectar accesos no autorizados y revocar claves. | Muy bajo |
| 7.4 | **Manejo de errores en el bot Telegram** | Capturar excepciones de red (ESPN/TheSportsDB) y responder con mensajes amigables en lugar de tracebacks. A�adir mensaje de "datos no disponibles localmente". | Bajo |

---

## Fase 8 — Calidad de código ✅ [COMPLETADA]

Inversi�n en sostenibilidad del proyecto. Sin esto, el c�digo se vuelve fr�gil a medida que crece.

| # | Mejora | Descripci�n | Esfuerzo |
|---|--------|-------------|---------|
| 8.1 | **Tests unitarios para `analysis.py`** | Las funciones `compute_standings`, `compute_overall_metrics`, `compute_team_percentiles` son puras y triviales de testear con `pytest` y DataFrames sint�ticos. Target: cubrir las 10 funciones principales. | Medio |
| 8.2 | **Tests de integraci�n para la API** | Usar `TestClient` de FastAPI para verificar que los 6 endpoints responden correctamente con datos de prueba. Detecta regresiones antes de cada push. | Medio |
| 8.3 | **CI con GitHub Actions** | Workflow autom�tico en cada push: check de sintaxis Python + ejecuci�n de tests. Gratuito para repositorios p�blicos. Falla el PR antes de mergear c�digo roto. | Bajo |
| 8.4 | **Centralizar `COMPETITION_NAMES`** | El mismo diccionario existe en `src/api.py`, `app.py` y `bot.py`. Moverlo a `src/constants.py` e importarlo desde all�. Evita desincronizaci�n al a�adir ligas. | Muy bajo |

---

## Fase 9 — Experiencia de usuario ✅ \[COMPLETADA]\n
Mejoras de UX que reducen fricci�n para betas y futuros usuarios.

| # | Mejora | Descripci�n | Esfuerzo |
|---|--------|-------------|---------|
| 9.1 | **Indicador de frescura de datos en el dashboard** | Leer la columna `fetched_at` del CSV y mostrar "Datos actualizados hace N d�as" en el sidebar. El usuario sabe sin esfuerzo si los datos son recientes. | Muy bajo |
| 9.2 | **Descarga de datos desde el dashboard** | Si la DB local no existe, mostrar un bot�n "Descargar datos" que ejecute `--fetch-real` en background con un spinner. El dashboard pasa a ser aut�nomo sin necesidad de terminal. | Medio |
| 9.3 | **`/ayuda` contextual en el bot Telegram** | Comando `/ayuda <comando>` que muestra la sintaxis exacta y un ejemplo real de cada comando. Reduce abandono en los primeros minutos de uso. | Muy bajo |
| 9.4 | **Expiraci�n configurable de contrase�as beta** | A�adir fecha de expiraci�n opcional por usuario (`claveJuan:Juan Garc�a:2026-05-01`). El dashboard bloquea autom�ticamente accesos caducados. | Bajo |

---

## Fase 10 — Producto avanzado `[COMPLETADA]`

Features con alto impacto de producto pero mayor esfuerzo.

| # | Mejora | Descripción | Esfuerzo | Estado |
|---|--------|-------------|----------|--------|
| 10.1 | **Exportar análisis a PDF** | `generate_pdf_report()` en `src/agent.py` + botón dashboard + `/pdf` en bot. | Bajo | ✅ |
| 10.2 | **Alertas proactivas por Telegram** | APScheduler diario; `/suscribir`, `/suscripciones`, `/desuscribir`; alerta si ≥3 derrotas. | Alto | ✅ |
| 10.3 | **Caché de gráficos por hash de datos** | Hash MD5 del DataFrame en `save_visual_report()`; marcador `.chart_cache`. | Medio | ✅ |
| 10.4 | **Aliases en inglés para el bot** | `/league`, `/team`, `/matchday`, `/help`, `/competitions`, `/teams` en `main()`. | Muy bajo | ✅ |
| 10.5 | **Modo multi-liga en el dashboard** | Checkbox sidebar; hasta 3 competiciones en tabs con clasificación + KPIs. | Alto | ✅ |

---

## Historial de versiones

| Versi�n | Fecha | Descripci�n |
|---------|-------|-------------|
| 1.0 | Abril 2026 | Fases 1-6 completadas: CLI, an�lisis, visualizaciones, fuentes de datos, narrativa, web |
| 1.1 | Abril 2026 | Beta access gate en dashboard Streamlit (contrase�as individuales por usuario) |
| 1.2 | Abril 2026 | ROADMAP v2: reescritura con fases 7-10 priorizadas por impacto/esfuerzo |
| 1.3 | Abril 2026 | Fase 7 completada: versiones fijadas, rate limiting API, log beta, errores bot |
