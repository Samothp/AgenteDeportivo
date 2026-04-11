# Roadmap de Mejoras en Reportes

Prioridad dentro de cada bloque: ⭐⭐⭐ impacto alto · ⭐⭐ medio · ⭐ bajo

---

## 🏆 Bloque 1 — Informe de Liga (`/liga`)

- [ ] ⭐⭐⭐ **Equipos en forma / en caída**: sección con top 3 equipos según racha de las últimas 5 jornadas (mejores y peores). Es la pregunta más frecuente del seguidor casual.
- [ ] ⭐⭐⭐ **Top 10 goleadores individuales**: añadir desde `player_loader` al final del informe. Actualmente solo aparecen equipos; los goleadores son el dato más buscado de cualquier liga.
- [ ] ⭐⭐ **Rendimiento local/visitante mejorado**: añadir columnas `W%_L` y `W%_V` (% de partidos ganados) junto a los puntos. Los puntos solos sin el total de partidos no son comparables entre equipos.
- [ ] ⭐⭐ **Conclusiones interpretativas**: reescribir para que aporten juicio, no repitan datos (ej. "Athletic está 9 puntos por encima de su xPts real: sobrerendimiento sostenido"). Actualmente son 5 bullets que duplican lo que ya está arriba.
- [ ] ⭐ **Leyenda de `Efic.` (antes `Over%`)**: añadir una línea explicativa al pie de la tabla técnica. El término es opaco para un lector no técnico.

---

## 🏟️ Bloque 2 — Informe de Equipo (`/equipo`)

- [ ] ⭐⭐⭐ **Ocultar campos vacíos**: eliminar líneas "Asistencia: No disponible" y "Árbitro: No disponible". Generan ruido visual y sensación de informe incompleto.
- [ ] ⭐⭐⭐ **Posesión en métricas básicas**: reemplazar "Posesión local promedio" (es la media global de la liga, no del equipo) por la posesión propia del equipo, que ya se calcula en estadísticas técnicas.
- [ ] ⭐⭐⭐ **Tendencia reciente**: añadir sección que compare el rendimiento de las primeras 15 jornadas vs las últimas 15 (puntos/partido y goles/partido por tramo). Determina si el equipo está mejorando o decayendo.
- [ ] ⭐⭐ **Percentiles con posición ordinal**: cambiar "55% — En la media" por "9.º de 20 equipos". El percentil sin referencia numérica absoluta se lee peor.
- [ ] ⭐⭐ **Eficiencia defensiva**: añadir `goles concedidos / xGA` paralelo al overperformance ofensivo que ya existe. Un equipo puede sobrerendir ofensivamente e infrarendir defensivamente.
- [ ] ⭐⭐ **Comprimir tabla de partidos**: mostrar solo los últimos 10 con nota "histórico completo disponible en el informe HTML". La tabla de 30+ filas ocupa más del 50% del informe sin aportar valor analítico.
- [ ] ⭐ **Ranking de la plantilla en la liga**: indicar si el tope goleador del equipo está en el top 10 de la liga, no solo dentro del equipo.

---

## 📅 Bloque 3 — Informe de Jornada (`/jornada`)

- [ ] ⭐⭐⭐ **Goleadores de la jornada**: sección con quién marcó en cada partido. Es la información más buscada inmediatamente después de una jornada. Requiere datos de jugadores por partido (ver Bloque 6).
- [ ] ⭐⭐⭐ **Recortar la clasificación**: en lugar de los 20 equipos completos (ya disponibles en `/tabla`), mostrar solo top 5 + zona de descenso (3 últimos) con texto "clasificación completa: `/tabla 2014 2025`". Reduce la longitud a la mitad.
- [ ] ⭐⭐ **Sorpresas ampliadas**: mostrar hasta 3 resultados sorpresivos (mayor delta entre resultado real y xG esperado), no solo 1. Un solo caso puede ser trivial.
- [ ] ⭐⭐ **Destacados de la jornada**: añadir mini-sección con equipo de mayor posesión, más tiros, y portero con más paradas. Sin necesidad de datos extra, con los agregados por partido ya existentes.
- [ ] ⭐ **Partido muda (0-0 o sin goles de un lado)**: destacar si se da el caso, con contexto (ej. "cuarto 0-0 consecutivo del equipo").

---

## 👤 Bloque 4 — Informe de Jugador (`/jugador`)

- [ ] ⭐⭐⭐ **Posición en el ranking de la liga**: indicar si el jugador está en el top goleadores/asistentes de toda la competición, no solo de su equipo. Es el dato de contexto más relevante.
- [ ] ⭐⭐⭐ **Racha de marcador**: sección con el número de partidos consecutivos marcando (o sin marcar). Para saber si está en forma o en sequía.
- [ ] ⭐⭐ **Ranking con total de jugadores**: cambiar "#1 goleadores" por "#1 de 18 jugadores con datos". Sin el denominador el puesto no da información.
- [ ] ⭐⭐ **Precisión de tiro**: añadir `tiros a puerta / tiros totales` (si disponible). Para un delantero es tan relevante como el número de goles.
- [ ] ⭐ **Métricas adaptadas por posición**: para defensas y centrocampistas, advertir que goles/asistencias no son métricas representativas y priorizar las que apliquen (recuperaciones, pases progresivos — sujeto a disponibilidad de datos).

---

## ⚽ Bloque 5 — Ficha de Partido (`/partido`)

- [ ] ⭐⭐⭐ **Historial H2H**: añadir últimos 3-5 enfrentamientos directos entre ambos equipos disponibles en el dataset. La lógica ya existe en `compute_compare`; solo hay que reutilizarla.
- [ ] ⭐⭐ **Contexto de tabla en el momento del partido**: mostrar la posición en la clasificación de ambos equipos en la jornada en que se jugó el partido.
- [ ] ⭐⭐ **Análisis interpretativo real**: reemplazar el texto automático ("X dominó la posesión, el xG respaldó el resultado") por interpretación del delta entre lo esperado y lo ocurrido. Ej: "a pesar de igualar el xG, Girona no convirtió sus ocasiones — problema de finalización, no de juego".
- [ ] ⭐ **Tarjetas e incidencias destacadas**: mencionar si hubo expulsados y en qué minuto (si el dato está disponible), dado el impacto que tienen en el resultado.

---

## 🗄️ Bloque 6 — Mejoras al Dataset

- [x] ⭐⭐⭐ **Goleadores por partido**: `src/scorer_loader.py` — caché CSV por temporada desde TheSportsDB timeline API. Funciones: `fetch_scorers`, `load_scorers`, `scorers_for_matchday`, `top_scorers_from_events`, `player_goal_streak`.
- [x] ⭐⭐⭐ **Tiros totales por jugador**: añadido `totalShots` a `_ESPN_STAT_FIELDS` → columna `shots_total` en el CSV de jugadores.
- [ ] ⭐⭐ **xG por jugador**: el xG existe a nivel de partido (equipo), pero no desglosado por jugador. Permitiría calcular el overperformance individual (¿convierte más o menos de lo esperado por sus ocasiones?).
  > 🔒 **Bloqueado**: ninguna API gratuita (TheSportsDB, ESPN) expone xG individual. Requiere Statsbomb/Opta (pago) o scraping de Understat.
- [x] ⭐⭐ **Minutos jugados por partido**: añadido `minutesPlayed` a `_ESPN_STAT_FIELDS` → columna `minutes_played` en el CSV de jugadores.
- [ ] ⭐⭐ **Asistencia al estadio por partido**: el campo `espectadores` existe en el schema pero viene vacío en la mayoría de los datasets. Completarlo habilitaría análisis de impacto del público en el rendimiento.
  > 🔒 **Bloqueado**: `api_client.py` ya captura el campo pero TheSportsDB no lo devuelve para La Liga (siempre null). Sin fuente alternativa gratuita.
- [x] ⭐ **Posición en tabla a cada jornada (snapshot histórico)**: ya disponible via `compute_standings(df, up_to_jornada=N)` en `analysis.py`. Sin cambios necesarios.
- [ ] ⭐ **Árbitro por partido**: el campo existe pero está vacío. Con árbitro se pueden detectar patrones como tarjetas por árbitro o win% con un colegiado concreto.
