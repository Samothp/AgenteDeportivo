# ROADMAP ï¿½ Agente Deportivo

Estado actualizado: abril 2026.
Criterio de priorizaciï¿½n: impacto real en producto, seguridad y sostenibilidad relativo al esfuerzo de implementaciï¿½n.

---

## Fases completadas

| Fase | Tï¿½tulo | Estado |
|------|--------|--------|
| 1 | Fundamentos CLI (`--top-n`, `--no-charts`, cachï¿½ TTL, rachas, xG) | ? Completada |
| 2 | Nuevos anï¿½lisis (percentiles, xPts, `--format json`, `--matchday-range`) | ? Completada |
| 3 | Visualizaciones (funnel, puntos acumulados, `--compare`, heatmap) | ? Completada |
| 4 | Fuentes de datos (ESPN UCL/Europa, fallback TheSportsDB) | ? Completada |
| 5 | Narrativa automï¿½tica (conclusiones por reglas, comparativa intertemporada) | ? Completada |
| 6 | Arquitectura web (FastAPI + Streamlit + Bot Telegram) | ? Completada |

---

## Fase 7 ï¿½ Seguridad y robustez `[PRï¿½XIMA]`

Mejoras crï¿½ticas antes de exponer el proyecto a usuarios externos.
Bajo esfuerzo, impacto alto en seguridad y estabilidad.

| # | Mejora | Descripciï¿½n | Esfuerzo |
|---|--------|-------------|---------|
| 7.1 | **Fijar versiones en `requirements.txt`** | Aï¿½adir versiï¿½n exacta a cada dependencia para garantizar reproducibilidad. Evita roturas silenciosas por breaking changes en upstream. | Muy bajo |
| 7.2 | **Rate limiting en la API** | Aï¿½adir `slowapi` para limitar peticiones por IP (ej. 10/min en endpoints de informe). Evita abuso de la URL pï¿½blica de ngrok. | Bajo |
| 7.3 | **Log de accesos beta** | Registrar en consola/fichero cada login del dashboard: usuario y timestamp. Permite detectar accesos no autorizados y revocar claves. | Muy bajo |
| 7.4 | **Manejo de errores en el bot Telegram** | Capturar excepciones de red (ESPN/TheSportsDB) y responder con mensajes amigables en lugar de tracebacks. Aï¿½adir mensaje de "datos no disponibles localmente". | Bajo |

---

## Fase 8 â€” Calidad de cÃ³digo âœ… [COMPLETADA]

Inversiï¿½n en sostenibilidad del proyecto. Sin esto, el cï¿½digo se vuelve frï¿½gil a medida que crece.

| # | Mejora | Descripciï¿½n | Esfuerzo |
|---|--------|-------------|---------|
| 8.1 | **Tests unitarios para `analysis.py`** | Las funciones `compute_standings`, `compute_overall_metrics`, `compute_team_percentiles` son puras y triviales de testear con `pytest` y DataFrames sintï¿½ticos. Target: cubrir las 10 funciones principales. | Medio |
| 8.2 | **Tests de integraciï¿½n para la API** | Usar `TestClient` de FastAPI para verificar que los 6 endpoints responden correctamente con datos de prueba. Detecta regresiones antes de cada push. | Medio |
| 8.3 | **CI con GitHub Actions** | Workflow automï¿½tico en cada push: check de sintaxis Python + ejecuciï¿½n de tests. Gratuito para repositorios pï¿½blicos. Falla el PR antes de mergear cï¿½digo roto. | Bajo |
| 8.4 | **Centralizar `COMPETITION_NAMES`** | El mismo diccionario existe en `src/api.py`, `app.py` y `bot.py`. Moverlo a `src/constants.py` e importarlo desde allï¿½. Evita desincronizaciï¿½n al aï¿½adir ligas. | Muy bajo |

---

## Fase 9 â€” Experiencia de usuario âœ… \[COMPLETADA]\n
Mejoras de UX que reducen fricciï¿½n para betas y futuros usuarios.

| # | Mejora | Descripciï¿½n | Esfuerzo |
|---|--------|-------------|---------|
| 9.1 | **Indicador de frescura de datos en el dashboard** | Leer la columna `fetched_at` del CSV y mostrar "Datos actualizados hace N dï¿½as" en el sidebar. El usuario sabe sin esfuerzo si los datos son recientes. | Muy bajo |
| 9.2 | **Descarga de datos desde el dashboard** | Si la DB local no existe, mostrar un botï¿½n "Descargar datos" que ejecute `--fetch-real` en background con un spinner. El dashboard pasa a ser autï¿½nomo sin necesidad de terminal. | Medio |
| 9.3 | **`/ayuda` contextual en el bot Telegram** | Comando `/ayuda <comando>` que muestra la sintaxis exacta y un ejemplo real de cada comando. Reduce abandono en los primeros minutos de uso. | Muy bajo |
| 9.4 | **Expiraciï¿½n configurable de contraseï¿½as beta** | Aï¿½adir fecha de expiraciï¿½n opcional por usuario (`claveJuan:Juan Garcï¿½a:2026-05-01`). El dashboard bloquea automï¿½ticamente accesos caducados. | Bajo |

---

## Fase 10 â€” Producto avanzado `[COMPLETADA]`

Features con alto impacto de producto pero mayor esfuerzo.

| # | Mejora | DescripciÃ³n | Esfuerzo | Estado |
|---|--------|-------------|----------|--------|
| 10.1 | **Exportar anÃ¡lisis a PDF** | `generate_pdf_report()` en `src/agent.py` + botÃ³n dashboard + `/pdf` en bot. | Bajo | âœ… |
| 10.2 | **Alertas proactivas por Telegram** | APScheduler diario; `/suscribir`, `/suscripciones`, `/desuscribir`; alerta si â‰¥3 derrotas. | Alto | âœ… |
| 10.3 | **CachÃ© de grÃ¡ficos por hash de datos** | Hash MD5 del DataFrame en `save_visual_report()`; marcador `.chart_cache`. | Medio | âœ… |
| 10.4 | **Aliases en inglÃ©s para el bot** | `/league`, `/team`, `/matchday`, `/help`, `/competitions`, `/teams` en `main()`. | Muy bajo | âœ… |
| 10.5 | **Modo multi-liga en el dashboard** | Checkbox sidebar; hasta 3 competiciones en tabs con clasificaciÃ³n + KPIs. | Alto | âœ… |


## Fase 11 â€” Calidad interna y fiabilidad [PROXIMA]

Refactorizaciones y mejoras de robustez identificadas tras el analisis post-Fase 10.
Enfocadas en mantenibilidad a largo plazo y reduccion de deuda tecnica critica.

| # | Mejora | Descripcion | Esfuerzo | Prioridad |
|---|--------|-------------|----------|-----------|
| 11.1 | **Retry exponencial en el cliente API** | Sustituir el time.sleep() manual de api_client.py por tenacity (@retry con backoff exponencial, 3 intentos). Cubre 429 y errores de red transitorios. | Muy bajo | Alta | ✅ |
| 11.2 | **Linting y type checking en CI** | Anadir 
uff (linting) y mypy (tipos) al workflow de GitHub Actions. Sin linting, los type hints son decorativos y los errores de estilo pasan desapercibidos. | Muy bajo | Alta |
| 11.3 | **src/thresholds.py — constantes centralizadas** | Extraer todos los magic numbers dispersos a un unico modulo importable. | Muy bajo | Alta | ✅ |
| 11.4 | **Coverage report en CI** | Anadir pytest --cov=src --cov-report=term-missing al workflow. | Muy bajo | Media | ✅ |
| 11.5 | **Validacion post-carga del DataFrame** | _warn_missing_optional() emite warnings si xg, posesion o shots estan vacias tras la carga. | Bajo | Media | ✅ |
| 11.6 | **AgentConfig dataclass** | Sustituir los 15 parametros de SportsAgent.__init__ por un @dataclass AgentConfig en src/config.py. Todos los puntos de instanciacion actualizados. | Medio | Media | ✅ |

---

## Fase 12 â€” Producto II [BAJA PRIORIDAD]

Mejoras de producto para cuando la deuda tecnica de Fase 11 este resuelta.

| # | Mejora | Descripcion | Esfuerzo | Prioridad |
|---|--------|-------------|----------|-----------|
| 12.1 | **Templates Jinja2 para los informes HTML** | Sustituir los metodos _generate_*_html_report() (150-250 lineas de f-strings cada uno) por plantillas .html.j2 renderizadas con Jinja2. Permite personalizar el diseno sin tocar la logica. | Alto | Media |
| 12.2 | **Paginacion en el bot Telegram** | Usar inline keyboards para paginar resultados largos (clasificaciones, listas de equipos) en lugar de fragmentar el texto en mensajes. Mejor UX movil. | Medio | Media |
| 12.3 | **Autenticacion en la API REST** | Header X-API-Key verificado contra .env. Actualmente solo hay rate limiting por IP; cualquiera con la URL ngrok puede usar la API sin restriccion. | Bajo | Alta |
| 12.4 | **Radar comparativo en modo multi-liga** | En el modo multi-liga del dashboard, anadir un grafico de radar superpuesto con las medias de cada liga (goles, xG, posesion, defensa). Complementa las tabs con clasificacion. | Bajo | Baja |
| 12.5 | **Exportar a Excel desde el dashboard** | Boton st.download_button con df.to_excel() junto al boton PDF. Util para usuarios que quieren manipular los datos fuera del dashboard. | Muy bajo | Baja |

---

---

## Historial de versiones

| Versiï¿½n | Fecha | Descripciï¿½n |
|---------|-------|-------------|
| 1.0 | Abril 2026 | Fases 1-6 completadas: CLI, anï¿½lisis, visualizaciones, fuentes de datos, narrativa, web |
| 1.1 | Abril 2026 | Beta access gate en dashboard Streamlit (contraseï¿½as individuales por usuario) |
| 1.2 | Abril 2026 | ROADMAP v2: reescritura con fases 7-10 priorizadas por impacto/esfuerzo |
| 1.3 | Abril 2026 | Fase 7 completada: versiones fijadas, rate limiting API, log beta, errores bot |

