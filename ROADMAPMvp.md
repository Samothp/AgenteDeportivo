# ROADMAP MVP Conversacional — Agente Deportivo

> Fecha: 13 de abril de 2026
> Objetivo: pasar de generador de informes por comandos a asistente conversacional que responda preguntas libres con datos reales (sin alucinaciones).

---

## Fase 1 — MVP Semiestructurado (rápida, bajo riesgo)

### 1) Router de intención + entidades mínimas
- [ ] Definir intenciones v1: `liga`, `equipo`, `jornada`, `partido`, `jugador`, `compare`, `preview`, `help`, `out_of_scope`.
- [ ] Crear parser de entidades v1 para texto libre:
  - [ ] `competition`
  - [ ] `season`
  - [ ] `jornada`
  - [ ] `equipo_local` / `equipo_visitante`
  - [ ] `team`
  - [ ] `player`
- [ ] Añadir normalizador de texto (minúsculas, tildes, espacios, alias de equipos).
- [ ] Implementar fallback cuando falten parámetros obligatorios.

Criterio de hecho:
- [ ] Dada una pregunta como "analiza jornada 31 de la liga 2025" el sistema detecta intención+entidades correctas y ejecuta el flujo.

### 2) Capa de resolución de parámetros (sin inventar datos)
- [ ] Añadir utilidades en `src/data_loader.py`:
  - [ ] resolver equipo por coincidencia parcial con ranking de candidatos.
  - [ ] resolver partido por `jornada + local + visitante` (ya existe lookup base; extender a modo ambiguo).
- [ ] Diseñar mensajes de aclaración:
  - [ ] "No encontré equipo exacto, ¿quisiste decir X o Y?"
  - [ ] "Hay 2 partidos posibles, elige uno."
- [ ] Unificar errores en formato estándar (`code`, `message`, `suggestion`).

Criterio de hecho:
- [ ] Ante entradas ambiguas, el usuario recibe opciones concretas y puede continuar sin reiniciar la conversación.

### 3) Endpoint de chat MVP (API)
- [ ] Crear endpoint `POST /chat/query` en `src/api.py`.
- [ ] Request v1:
  - [ ] `text: str`
  - [ ] `competition: int | null`
  - [ ] `season: str | null`
  - [ ] `session_id: str`
- [ ] Response v1:
  - [ ] `answer: str`
  - [ ] `intent: str`
  - [ ] `entities: dict`
  - [ ] `requires_clarification: bool`
  - [ ] `clarification_options: list[str]`
- [ ] Conectar el router a funciones existentes del agente (sin duplicar lógica).

Criterio de hecho:
- [ ] Una pregunta de texto libre devuelve respuesta o pregunta de aclaración con estructura estable.

### 4) Dashboard: pestaña Chat básica
- [ ] Crear tab "Chat" en `app.py`.
- [ ] Añadir caja de texto + botón "Preguntar".
- [ ] Mostrar historial en sesión (`st.session_state`).
- [ ] Si el backend pide aclaración, renderizar botones de opción rápida.

Criterio de hecho:
- [ ] Desde dashboard se puede mantener una mini conversación de 2-3 turnos sobre el mismo contexto.

### 5) Bot Telegram: comando `/ask`
- [ ] Añadir `/ask <pregunta>` en `bot.py`.
- [ ] Reusar `session_id` por usuario para continuidad.
- [ ] Manejar aclaraciones con respuestas guiadas (texto o botones inline).
- [ ] Limitar spam con cooldown y mensajes de estado (typing).

Criterio de hecho:
- [ ] Usuario pregunta en lenguaje natural y obtiene respuesta útil o aclaración en menos de 2 turnos.

### 6) Guardrails de confianza
- [ ] Bloquear respuestas fuera de dominio deportivo con mensaje claro.
- [ ] Forzar política "si no hay datos, decir que no hay datos".
- [ ] Incluir trazabilidad en logs (`intent`, entidades extraídas, éxito/fallo).

Criterio de hecho:
- [ ] Cero respuestas inventadas en pruebas internas del conjunto MVP.

### 7) Pruebas y métricas Fase 1
- [ ] Crear dataset inicial de 40-60 preguntas reales.
- [ ] Añadir tests:
  - [ ] intención correcta
  - [ ] extracción de entidades
  - [ ] resolución de partido/equipo
  - [ ] fallback de aclaración
- [ ] Definir métricas mínimas:
  - [ ] `intent_accuracy`
  - [ ] `entity_accuracy`
  - [ ] `first_turn_resolution_rate`
  - [ ] latencia p95

Criterio de hecho:
- [ ] `intent_accuracy >= 85%`, `entity_accuracy >= 80%` y p95 aceptable para uso interno.

---

## Fase 2 — Chat Libre Completo (robusto, escalable)

### 8) Memoria conversacional por sesión
- [ ] Persistir contexto por `session_id` (última competición, temporada, equipo, partido, jornada).
- [ ] Resolver referencias anafóricas:
  - [ ] "ese partido"
  - [ ] "el de antes"
  - [ ] "compáralo con..."
- [ ] TTL de sesiones y limpieza automática.

Criterio de hecho:
- [ ] El usuario puede encadenar 5-8 turnos sin repetir parámetros constantemente.

### 9) Orquestador tool-calling
- [ ] Definir contrato de herramientas internas (`tool schema`) para cada tipo de consulta.
- [ ] Implementar orquestador: pregunta -> herramienta -> validación -> respuesta final.
- [ ] Añadir post-procesado de respuesta con formato consistente y breve.

Criterio de hecho:
- [ ] El modelo usa herramientas para datos y no responde desde memoria no verificada.

### 10) Clarificación proactiva y desambiguación avanzada
- [ ] Ranking de candidatos con score para equipos/jugadores/partidos.
- [ ] Preguntas de aclaración auto-generadas cuando score sea bajo.
- [ ] Reintento automático con mejores candidatos antes de fallar.

Criterio de hecho:
- [ ] Reducción de errores por ambigüedad en al menos 30% frente a Fase 1.

### 11) Personalización y UX de respuesta
- [ ] Preferencias por usuario (formato corto/largo, tono, idioma).
- [ ] Respuesta multimodal opcional:
  - [ ] texto
  - [ ] tabla breve
  - [ ] enlace a informe completo
- [ ] Plantillas de respuesta por intención (consistencia en bot y dashboard).

Criterio de hecho:
- [ ] Misma pregunta devuelve respuestas coherentes y legibles en ambos canales.

### 12) Observabilidad y calidad en producción
- [ ] Dashboard interno de métricas conversacionales.
- [ ] Logging estructurado de errores y rutas de fallback.
- [ ] Alertas por degradación (latencia, caída de precisión, aumento de out_of_scope).

Criterio de hecho:
- [ ] Detección temprana de regresiones sin inspección manual de logs.

### 13) Seguridad y límites operativos
- [ ] Hardening de rate limit por usuario/IP/sesión.
- [ ] Sanitización de inputs y límites de longitud.
- [ ] Protección contra prompts maliciosos en entrada libre.

Criterio de hecho:
- [ ] Comportamiento estable bajo carga y entradas adversariales básicas.

### 14) Pruebas E2E y plan de despliegue
- [ ] Añadir tests end-to-end para API, dashboard y bot.
- [ ] Definir estrategia de release gradual:
  - [ ] beta privada
  - [ ] grupo piloto
  - [ ] rollout general
- [ ] Plan de rollback y feature flags.

Criterio de hecho:
- [ ] Release con riesgo controlado y capacidad de revertir en minutos.

---

## Hitos de entrega

- [ ] Hito A (fin Fase 1): chat MVP funcional en API + dashboard + Telegram.
- [ ] Hito B (mitad Fase 2): memoria conversacional y desambiguación avanzada.
- [ ] Hito C (fin Fase 2): chat libre robusto con observabilidad y despliegue gradual.

## Definición de "MVP listo"

- [ ] Responde preguntas semiestructuradas de fútbol con datos reales.
- [ ] Pide aclaración cuando hay ambigüedad (sin romper flujo).
- [ ] Mantiene contexto básico por sesión.
- [ ] Tiene métricas objetivas de calidad y latencia.
- [ ] Está disponible en API, dashboard y bot de Telegram.
