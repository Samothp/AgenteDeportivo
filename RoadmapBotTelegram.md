# Roadmap del Bot de Telegram — Agente Deportivo

> Última revisión: 10 de abril de 2026

---

## 🔴 Alta prioridad — Bugs críticos y riesgos en producción

- [x] **1. Eliminar código duplicado de control de acceso** ✅
  `ALLOWED_GROUP_ID`, `_MEMBER_STATUSES`, `_is_group_member()` y `_require_group_member()` estaban definidos **dos veces** en `bot.py`.
  Se eliminó el primer bloque duplicado, dejando únicamente la definición canónica con su sección de encabezado.

- [x] **2. Corregir `asyncio.run()` dentro de `_check_alerts_sync`** ✅
  Se añadió `_main_loop: asyncio.AbstractEventLoop | None = None` a nivel de módulo y un callback `post_init` que captura el event loop del hilo principal al arrancar la aplicación.
  En `_check_alerts_sync`, `asyncio.run(_send(...))` se reemplazó por `asyncio.run_coroutine_threadsafe(_send(...), _main_loop).result(timeout=30)` para enviar alertas de forma segura desde el hilo de APScheduler.

- [x] **3. Persistir el caché de paginación en disco** ✅
  `_page_cache` ya no es un dict en memoria efímero. Se añadieron `PAGE_CACHE_FILE`, `_pc_load()` y `_pc_save()`. Al arrancar el bot se cargan las entradas válidas del fichero `data/page_cache.json` (TTL 1 hora). Cada vez que se almacena un nuevo resultado paginado, se persiste en disco. Los botones ◀/▶ de mensajes anteriores siguen funcionando tras reinicios.

- [x] **4. Rate limiting por usuario** ✅
  Nuevo decorador `_cooldown(seconds)` que usa `context.user_data` para registrar el último uso por comando. Si el mismo usuario reejuta el comando antes de que pasen `seconds` segundos, recibe un mensaje con el tiempo restante. Aplicado con `@_cooldown(30)` a los comandos costosos: `/liga`, `/equipo`, `/jornada`, `/compare` y `/pdf`.

- [x] **5. Completar `/start` \u2014 incluir todos los comandos** ✅
  Reescrito con saludo personalizado por nombre de usuario y tres secciones agrupadas: *Análisis e informes* (`/liga`, `/equipo`, `/jornada`, `/compare`, `/pdf`), *Alertas proactivas* (`/suscribir`, `/suscripciones`, `/desuscribir`) y *Ayuda*. Migrado a `MarkdownV2` para compatibilidad con el API de Telegram.

- [x] **6. Inferir temporada actual automáticamente** ✅
  Nueva función `_current_season()` que calcula el año de inicio de la temporada en función del mes: julio\u2013diciembre → año en curso; enero\u2013junio → año anterior. Se calculan `_SEASON_EXAMPLE` (ej. `"2025"`), `_SEASON_NEXT` (`"2026"`) y `_SEASON_LABEL` (`"25/26"`) una sola vez al arrancar el bot. Todos los mensajes de error y los ejemplos de `/start`, `/ayuda` y `_parse_base` usan ahora estas constantes dinámicas.

---

## 🟠 Media prioridad — Nuevas funcionalidades

- [x] **7. Comando `/jugador <comp> <temp> <equipo> <nombre>`** ✅
  Nuevo handler `cmd_jugador` decorado con `@_require_group_member` y `@_cooldown(30)`. Llama a `_run_agent_text(..., team=equipo, player=nombre)` y devuelve el informe paginado. Registrado como `/jugador`. Añadido a `/start`, `/ayuda` y `_AYUDA_CMDS`.

- [x] **8. Comando `/tabla <comp> <temp>`** ✅
  Nuevo handler `cmd_tabla` con `@_cooldown(15)`. Carga el CSV directamente con `load_match_data` + `compute_liga_summary`, formatea la clasificación con posición, puntos, marcador y forma reciente. Mucho más rápido que `/liga` para consultas rápidas.

- [x] **9. Comando `/ultima <comp> <temp> <equipo>`** ✅
  Handler `cmd_ultima` que carga el CSV y llama a `compute_team_form(df, team, last_n=5)` de `analysis.py`. Responde con la cadena de emojis y la leyenda.

- [x] **10. Comando `/temporadas <comp>`** ✅
  Handler `cmd_temporadas` que escanea `data/` buscando ficheros `db_<comp>_<año>.csv` con regex y muestra las temporadas encontradas con su etiqueta (ej. `2025` → `25/26`). Si no hay ninguna, sugiere el comando de descarga.

- [x] **11. Enviar gráficos como foto adjunta** ✅
  Nueva función `_run_agent_with_charts(comp, season, tmp_dir, **kwargs)` que crea el agente con `no_charts=False` y llama a `save_visual_report(tmp_dir)`. Helper `_send_report_with_charts(update, text, images)` que envía el texto paginado y después cada PNG con `reply_photo()`. Los comandos `/liga`, `/equipo` y `/compare` usan gráficos por defecto y aceptan `--texto` para modo solo texto.

- [x] **12. Caché de informes por sesión** ✅
  Dict en memoria `_report_cache: dict[str, (ts, text)]` con TTL de 10 minutos. Funciones `_report_cache_key`, `_report_cache_get` (con limpieza oportunista de expiradas) y `_report_cache_set`. Si el mismo usuario \u2014o cualquiera\u2014 pide el mismo informe (misma comp+temp+equipo) antes de 10 minutos, el bot responde con el texto cacheado directamente, indicando 💾 (informe cacheado). Aplicado a `/liga`, `/equipo` y `/compare`.

---

## 🟡 Baja prioridad — Pulido y UX

- [x] **13. Indicador de typing mientras se genera el informe** ✅
  Nuevo context manager `_TypingAction(update, context)` que envía `ChatAction.TYPING` cada 4 segundos en un `asyncio.Task` paralelo. Todos los handlers pesados (`/liga`, `/equipo`, `/jornada`, `/compare`, `/jugador`) envuelven la llamada al agente con `async with _TypingAction(...)` y la ejecutan en un hilo con `asyncio.to_thread()` para no bloquear el event loop.

- [ ] **14. Mensaje de bienvenida personalizado al primer uso**
  Al recibir `/start`, si el usuario nunca ha interactuado, mostrar además una pequeña guía de primeros pasos y confirmar si tiene acceso (cuando `ALLOWED_GROUP_ID` está activo).

- [ ] **15. Aliases adicionales en español natural**
  Añadir `/clasificacion` como alias de `/tabla`, `/partido` para consultar un partido por ID, y `/goleadores` para el top de goleadores de una liga rápidamente.

- [ ] **16. Logging de uso por comando**
  Registrar en un fichero CSV/JSON qué comandos se usan más, por qué usuarios y con qué competiciones.
  Sin datos personales (solo user_id hasheado). Permite tomar decisiones de producto basadas en uso real.

- [ ] **17. Mensaje de mantenimiento configurable**
  Variable de entorno `BOT_MAINTENANCE_MSG`: si está definida, todos los handlers (excepto `/start`) responden con ese mensaje.
  Permite anunciar cierres planificados sin apagar el bot.
