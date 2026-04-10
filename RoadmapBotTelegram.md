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

- [ ] **7. Comando `/jugador <comp> <temp> <equipo> <nombre>`**
  El dashboard tiene modo Jugador completo (stats per-90, cotización, foto) pero el bot no lo expone.
  Añadir `cmd_jugador` usando `_run_agent_text(..., team=equipo, player=nombre)` y actualizar `/start` y `/ayuda`.

- [ ] **8. Comando `/tabla <comp> <temp>`**
  Devuelve solo la clasificación en texto formateado (sin generar el informe completo), mucho más rápido.
  Útil para consultas rápidas que no justifican esperar el análisis completo.

- [ ] **9. Comando `/ultima <comp> <temp> <equipo>`**
  Devuelve los últimos 5 resultados del equipo con emojis 🟢 victoria · ⚪ empate · 🔴 derrota.
  Reutiliza `compute_team_form()` de `analysis.py` que ya existe.

- [ ] **10. Comando `/temporadas <comp>`**
  Lista las temporadas disponibles localmente para una competición.
  Evita que el usuario tenga que adivinar qué temporadas hay en la DB.

- [ ] **11. Enviar gráficos como foto adjunta**
  Todos los agentes usan `no_charts=True`: los usuarios solo reciben texto plano.
  Cambiar `/equipo`, `/liga` y `/compare` para generar gráficos en un directorio temporal y enviarlos con `reply_photo()` o `reply_document()` tras el texto de informe.
  Añadir opción para desactivarlo con `/equipo ... --texto` para usuarios que prefieran solo texto.

- [ ] **12. Caché de informes por sesión**
  Si el mismo usuario pide el mismo informe (misma comp+temp+equipo) en menos de 10 minutos, devolver el resultado cacheado en lugar de re-ejecutar el agente.
  Implementar con un dict `{key: (timestamp, resultado)}` limpiado periódicamente.

---

## 🟡 Baja prioridad — Pulido y UX

- [ ] **13. Indicador de typing mientras se genera el informe**
  Actualmente el bot envía "⏳ Generando informe..." y luego nada hasta que termina.
  Usar `await context.bot.send_chat_action(chat_id, ChatAction.TYPING)` en bucle mientras el agente trabaja para que Telegram muestre "escribiendo…" de forma continua.

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
