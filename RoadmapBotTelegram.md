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

- [ ] **3. Persistir el caché de paginación en disco**
  `_page_cache` es un dict en memoria: al reiniciar el bot, los botones ◀/▶ de mensajes anteriores devuelven "sesión expirada".
  Reemplazar con un caché en disco (JSON + TTL de 1 hora) o simplemente deshabilitar los botones de paginación al reiniciar guardando el estado en `data/page_cache.json`.

- [ ] **4. Rate limiting por usuario**
  Sin cooldown, un usuario puede spamear `/liga` o `/equipo` indefinidamente y saturar el servidor con análisis costosos.
  Implementar un decorador `_cooldown(seconds)` que rechace el mismo comando del mismo usuario si no han pasado N segundos desde la última ejecución (estado en `context.user_data`).

- [ ] **5. Completar `/start` — incluir todos los comandos**
  El mensaje de bienvenida no menciona `/suscribir`, `/desuscribir`, `/suscripciones`, `/pdf` ni `/ayuda`.
  Los usuarios nuevos no descubren las funcionalidades de alertas.
  Reescribir `/start` con el listado completo de comandos agrupados por categoría.

- [ ] **6. Inferir temporada actual automáticamente**
  Todos los mensajes de error y ayuda hardcodean `2024` como temporada de ejemplo.
  Calcular la temporada actual en función del mes: si estamos en julio-diciembre → año actual; si enero-junio → año anterior. Usarla en todos los ejemplos de mensajes de error.

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
