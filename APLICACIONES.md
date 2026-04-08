# Análisis de Usabilidad Real — Agente Deportivo

Este documento recoge el análisis de los casos de uso reales y potenciales del agente,
para orientar las decisiones de desarrollo futuro.

---

## ¿Qué es hoy el agente?

Una herramienta de análisis de datos deportivos por línea de comandos que genera informes
estáticos (texto plano + HTML + gráficos PNG). Consume datos de TheSportsDB (partidos) y
ESPN API no oficial (estadísticas de jugadores), con caché local incremental en CSV.

---

## Casos de uso reales factibles (hoy)

### 1. Seguimiento personal de un equipo
El uso más natural e inmediato. Un aficionado puede automatizar un informe semanal
tras cada jornada mediante una tarea programada (cron / Tarea de Windows):

```bash
python -m src.run_agent --competition 2014 --season 2025 --team Mallorca \
  --fetch-real --html-output reports/mallorca_j30.html --visual reports/mallorca_j30
```

Genera análisis completo: evolución por jornada, comparativa vs liga,
historial W/D/L, perfil de jugadores clave. **Es el caso de uso más realista hoy.**

---

### 2. Contenido para redes sociales / blog deportivo
Los informes HTML son publicables directamente. Los gráficos PNG se pueden insertar
en artículos o publicaciones. Un creador de contenido puede automatizar análisis
semanales de jornada o de equipo sin conocimientos de programación avanzados,
simplemente ajustando los argumentos del CLI.

Requiere mejorar el diseño visual del HTML (actualmente funcional pero sin estilos avanzados).

---

### 3. Herramienta de aprendizaje de data science deportivo
El proyecto es un pipeline de datos estructurado y bien organizado:
ingestión → transformación → análisis → visualización.

Puede usarse como base para enseñar o aprender análisis deportivo con Python,
ya que cubre todas las fases con código real y datos reales.

---

### 4. Análisis amateur de rivales (scouting básico)
Usando el futuro modo `--compare`, preparar análisis pre-partido:
"¿Cómo juega nuestro próximo rival respecto a la media de la liga?"

Los datos de TheSportsDB son suficientemente fiables para análisis amateur y semi-profesional.
No sustituye a herramientas profesionales (Wyscout, Opta), pero cubre necesidades de
equipos de categorías inferiores o analistas independientes.

---

### 5. Análisis histórico multi-temporada
Ya disponible con `--seasons 2023 2024 2025`. Permite estudiar la evolución de un
equipo a lo largo de varias temporadas:

- ¿Mejoró la defensa este año respecto al anterior?
- ¿Se dispararon los goles concedidos?
- ¿Cómo evolucionó el xG del equipo en 3 temporadas?

Útil para periodistas deportivos, aficionados analíticos y estudios de caso.

---

## Límites actuales (análisis honesto)

| Limitación | Causa | ¿Superable? |
|---|---|---|
| Sin datos en tiempo real | Plan gratuito TheSportsDB | Solo con plan de pago (~$10/mes) |
| Stats de jugadores muy básicas (6 métricas) | ESPN API no oficial | Parcialmente con otras fuentes |
| Solo 6 ligas para stats de jugadores | ESPN slug mapping limitado | Ampliar manualmente |
| Dependencia de dos APIs externas | Sin control sobre cambios de la API | Caché local mitiga el riesgo |
| CLI pura, sin interfaz gráfica | Diseño actual | Mejoras en fases futuras (ver ROADMAP) |
| Sin notificaciones ni automatización nativa | Fuera del alcance actual | Vía cron/tareas externas |

---

## Potencial de evolución futura

Lo que hoy es un CLI puede evolucionar hacia:

### API REST local (FastAPI / Flask)
El núcleo analítico (`analysis.py`, `data_loader.py`) ya está completamente desacoplado
del presentador (`agent.py`, `visualizer.py`). Esto permite exponer los 5 modos como
endpoints HTTP sin reescribir la lógica de análisis:

```
GET /api/league?competition=2014&season=2025
GET /api/team?competition=2014&season=2025&team=Mallorca
GET /api/player?competition=2014&season=2025&team=Mallorca&player=Muriqi
```

### Dashboard web interactivo (Streamlit / Dash)
Reemplazar Matplotlib por Plotly para gráficos interactivos. Añadir selectores de
liga, equipo y jugador. El usuario final no necesitaría conocer el CLI.

### Bot de Telegram / Discord
El agente ya genera texto estructurado. Un bot podría responder comandos como:
`/mallorca jornada 28` y devolver el informe y los gráficos directamente al chat.
Caso de uso muy natural para comunidades de aficionados.

### Integración con LLMs
Los informes de texto estructurado que genera el agente son ideales como contexto
para un LLM. El modelo puede convertirlos en narrativa natural, responder preguntas
sobre el partido o generar análisis editoriales listos para publicar.

Ejemplo de flujo:
```
agente → informe.txt → LLM → "El Mallorca llega a la jornada 28 con 
una racha de 3 victorias consecutivas, siendo el equipo con mayor xG 
en las últimas 5 jornadas..."
```

### Alertas automáticas
Con el TTL de caché y una tarea programada, el sistema podría enviar alertas cuando
el equipo favorito juega un partido, ha actualizado resultados o ha alcanzado un hito
(10 partidos sin perder, máximo goleador de la liga, etc.).

---

## Conclusión

El agente tiene hoy una base técnica sólida y cubreel caso de uso principal
(seguimiento de un equipo en una liga) de forma funcional.

La arquitectura desacoplada lo convierte en un buen candidato para evolucionar hacia
una herramienta web o integrada con mensajería, sin necesidad de reescribir la lógica analítica.

El límite más relevante a corto plazo no es técnico sino de datos: la gratuidad de
la API limita la profundidad del análisis. A medida que el proyecto crezca, valorar
un plan de pago de TheSportsDB o explorar fuentes alternativas (StatsBomb open data,
FBref scraping) puede desbloquear análisis más ricos.
