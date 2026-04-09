# Comandos del Agente Deportivo

Este archivo resume los comandos principales del agente para analizar datos deportivos.

## Argumentos disponibles

```
--data           Ruta al archivo CSV de partidos (ej. data/example_matches.csv)
--output         Ruta del informe de texto generado
--html-output    Ruta del informe HTML (opcional)
--visual         Carpeta donde se guardan los gráficos
--clean-reports  Elimina archivos anteriores en la carpeta antes de generar nuevos
--fetch-real     Construye/actualiza la DB descargando de la API
--competition    ID de la competición (2014=La Liga, 2021=Premier, etc.)
--season         Temporada en formato YYYY
--team           Equipo para filtrar el análisis (búsqueda parcial)
--jornada        Número de jornada (activa modo Jornada)
--match-id       ID del partido — id_event — (activa modo Partido)
--player         Nombre del jugador (requiere --team, activa modo Jugador)
--compare        Dos equipos a comparar (activa modo Compare)
--list-teams     Lista los equipos disponibles en la DB y termina
--seasons        Lista de temporadas a combinar (ej. --seasons 2022 2023 2024)
--top-n          Número de equipos/jugadores en los rankings (por defecto: 5)
--no-charts      Omitir generación de gráficos (texto rápido)
--format         Formato de salida: text (por defecto) o json
--matchday-range Rango de jornadas a analizar (ej. --matchday-range 10 20)
--refresh-cache  Eliminar el caché local y re-descargar desde la API
--cache-ttl      Días antes de avisar que el caché está desactualizado (por defecto: 7)
```

## Detección automática del tipo de informe

El agente selecciona el modo según los argumentos:

| Modo | Condición | Descripción |
|------|-----------|-------------|
| **Liga** | solo `--competition` + `--season` | Clasificación, xPts, récords, stats de la temporada |
| **Equipo** | `--team` (sin `--player`) | W/D/L, métricas con percentiles, comparativa vs liga, rachas, conclusiones |
| **Jornada** | `--jornada N` | Resultados y estadísticas de una jornada |
| **Partido** | `--match-id ID` | Ficha técnica detallada de un partido |
| **Jugador** | `--team` + `--player` | Perfil individual de un jugador |
| **Compare** | `--compare TEAM1 TEAM2` | Radar, H2H y diferencias entre dos equipos |

---

## Informe de Liga

Panorama completo de una temporada: clasificación, xPts (puntos esperados), récords, estadísticas por equipo y rendimiento local/visitante.

```bash
python -m src.run_agent --competition 2014 --season 2025 \
  --output reports/laliga.txt --html-output reports/laliga.html --visual reports/laliga
```

Gráficos generados: `league_table.png`, `goals_per_team.png`, `xg_per_team.png`, `home_away_performance.png`, `points_evolution.png`

---

## Informe de Equipo

Análisis filtrado por equipo: historial W/D/L, rachas máximas, métricas técnicas con percentiles de liga, comparativa vs liga, overperformance xG, top goleadores y asistentes, y sección de **Conclusiones automáticas** al final.

```bash
python -m src.run_agent --competition 2014 --season 2025 --team Mallorca \
  --output reports/mallorca.txt --html-output reports/mallorca.html --visual reports/mallorca
```

El filtro usa búsqueda parcial: `Mallorca` localiza `RCD Mallorca`. Usa `--list-teams` para ver nombres exactos.

Gráficos: `goals_distribution.png`, `possession_distribution.png`, `card_summary.png`, `xg_per_match.png`, `shots_comparison.png`, `temporal_evolution.png`, `shot_funnel.png`

---

## Informe de Jornada

Resultados, estadísticas agregadas, clasificación acumulada y partido más espectacular de una jornada.

```bash
python -m src.run_agent --competition 2014 --season 2025 --jornada 15 \
  --output reports/jornada_15.txt --html-output reports/jornada_15.html --visual reports/jornada_15
```

Gráficos: `matchday_goals.png`, `matchday_xg.png`

---

## Informe de Partido

Ficha técnica completa: resultado, estadísticas cara a cara, clasificación previa y análisis narrativo.

```bash
python -m src.run_agent --competition 2014 --season 2025 --match-id 2279399 \
  --output reports/partido.txt --html-output reports/partido.html --visual reports/partido
```

Para encontrar el `id_event` de un partido, búscalo en la DB local:

```bash
python -c "import pandas as pd; df=pd.read_csv('data/db_2014_2025.csv'); print(df[['id_event','date','local_team','visitante_team','jornada']].to_string())"
```

Gráficos: `match_stats_bar.png`, `match_radar.png`

---

## Informe de Jugador

Perfil individual de temporada: stats, ratios por partido, ranking en el equipo y gráficos comparativos.
Requiere `--team` para cargar el CSV de jugadores ESPN del equipo correcto.

```bash
python -m src.run_agent --competition 2014 --season 2025 \
  --team Mallorca --player "Vedat Muriqi" \
  --output reports/muriqi.txt --html-output reports/muriqi.html --visual reports/muriqi
```

La búsqueda del jugador es parcial e insensible a mayúsculas. `"muriqi"` y `"Vedat Muriqi"` funcionan igual.

Gráficos: `player_bar.png` (barras jugador vs media equipo), `player_radar.png` (radar 5 métricas normalizadas)

---

## Informe Compare (dos equipos)

Comparati va directa entre dos equipos: radar con todas las métricas, tabla de enfrentamientos H2H en la DB y diferencias absolutas/porcentuales en cada métrica.

```bash
python -m src.run_agent --competition 2014 --season 2025 \
  --compare "Real Madrid" "Barcelona" \
  --output reports/compare.txt --html-output reports/compare.html --visual reports/compare
```

Ambos equipos deben existir en la DB de la misma `--competition` y `--season`.

Gráficos: `compare_radar.png`, `compare_bars.png`

---

## Ver equipos disponibles en la DB local

Antes de generar un informe de equipo, consulta qué nombres exactos usa la DB:

```bash
python -m src.run_agent --list-teams --competition 2014 --season 2025
```

Salida de ejemplo:
```
Equipos disponibles (competition=2014, season=2025):
  Athletic Bilbao
  Atlético Madrid
  Barcelona
  Celta Vigo
  ...
  Villarreal
```

Si la DB no existe aún:
```
No hay DB local para competition=2014 season=2025.
Usa --fetch-real para descargar los datos primero.
```

---

## Opciones de control de salida

### Informes rápidos sin gráficos

`--no-charts` omite toda la generación de imágenes. útil para obtener el texto en menos de 1 segundo:

```bash
python -m src.run_agent --competition 2014 --season 2025 --team Mallorca --no-charts --output reports/mallorca_rapido.txt
```

### Rankings configurables

`--top-n N` controla cuántos equipos/jugadores aparecen en los rankings (por defecto 5):

```bash
# Top 10 goleadores en vez de 5
python -m src.run_agent --competition 2014 --season 2025 --team Mallorca --top-n 10 --output reports/mallorca_top10.txt
```

### Salida JSON

`--format json` serializa todo el análisis a JSON. La extensión `.txt` se transforma automáticamente a `.json`:

```bash
python -m src.run_agent --competition 2014 --season 2025 --team Mallorca --format json --output reports/mallorca.json
```

El JSON incluye todas las métricas, registros, percentiles y datos del informe, listo para integración con otras herramientas.

### Análisis de rango de jornadas

`--matchday-range START END` filtra el dataset a las jornadas indicadas y genera un informe de liga parcial:

```bash
# Primera vuelta (jornadas 1–19)
python -m src.run_agent --competition 2014 --season 2025 --matchday-range 1 19 --output reports/primera_vuelta.txt

# Segunda vuelta
python -m src.run_agent --competition 2014 --season 2025 --matchday-range 20 38 --output reports/segunda_vuelta.txt
```

No es compatible con `--jornada`.

### Análisis multi-temporada con narrativa intertemporada

`--seasons` combina varias temporadas en un solo DataFrame y genera al final del informe la evolución porcentual de las métricas clave entre la primera y la última temporada:

```bash
python -m src.run_agent --competition 2014 --team Barcelona --seasons 2022 2023 2024 \
  --output reports/barca_evolucion.txt
```

Salida esperada al final del informe:
```
Evolución intertemporada  (2022 → 2024)
------------------------------------------------
  Goles a favor/partido              1.70 →   2.67  (+57.1%)  Mejora
  Goles encajados/partido            1.40 →   0.97  (-30.7%)  Mejora
  ...
```

## Base de datos local incremental

El agente mantiene una **DB local por competición y temporada** en `data/db_<competition>_<season>.csv`.
Esto evita re-descargar y re-enriquecer partidos ya conocidos.

### Primera descarga (construye la DB)

```bash
python -m src.run_agent --fetch-real --competition 2014 --season 2025 --output reports/laliga_2025.txt --html-output reports/laliga_2025.html --visual reports/laliga_2025
```

En el primer uso descarga y enriquece **todos** los partidos de la temporada con estadísticas
detalladas (tiros, posesión, xG, etc.) y los guarda en `data/db_2014_2025.csv`.

### Actualización incremental (nuevas jornadas)

El mismo comando en semanas posteriores **solo descarga las jornadas nuevas** y enriquece únicamente
los partidos que aún no tienen stats en la DB:

```bash
python -m src.run_agent --fetch-real --competition 2014 --season 2025 --output reports/laliga_2025.txt --visual reports/laliga_2025
```

Salida esperada cuando ya está al día:
```
DB local: 300 partidos con stats. Nuevos/pendientes: 0.
La DB ya está al día, no hay partidos nuevos ni pendientes.
```

### Informe de equipo sin conexión (desde DB local)

Una vez que la DB existe, **no hace falta `--fetch-real`** para generar el informe de un equipo.
Cero llamadas a la API:

```bash
python -m src.run_agent --competition 2014 --season 2025 --team Mallorca --output reports/mallorca_2025.txt --html-output reports/mallorca_2025.html --visual reports/mallorca_2025
```

- `--fetch-real` : construye/actualiza la DB descargando de la API
- `--competition` : ID de la competición (`2014` = La Liga, `2021` = Premier, etc.)
- `--season` : temporada en formato `YYYY` (se transforma a `YYYY-YYYY+1` internamente)

### Rendimiento aproximado

| Escenario | Llamadas API | Tiempo estimado |
|---|---|---|
| Primer uso (construir DB) | ~301 (base + stats) | ~3-4 min |
| Jornada nueva (+10 partidos) | ~11 | ~10 seg |
| DB ya al día | 1 (verificación) | ~2 seg |
| Informe de equipo (sin `--fetch-real`) | 0 | <1 seg |

Configuración recomendada de API key:

```bash
# Windows
set THESPORTSDB_API_KEY=078593

# Linux/Mac
export THESPORTSDB_API_KEY=078593
```

> Si no defines variable de entorno, el cliente usa la key `078593` por defecto.

## Analizar un equipo específico

Usa `--team` para filtrar los partidos de un equipo concreto.

Primero comprueba los nombres disponibles con `--list-teams`, luego genera el informe:

```bash
# Ver equipos disponibles
python -m src.run_agent --list-teams --competition 2014 --season 2025

# Generar informes de distintos equipos sin llamar a la API
python -m src.run_agent --competition 2014 --season 2025 --team Mallorca --output reports/mallorca_2025.txt --html-output reports/mallorca_2025.html --visual reports/mallorca_2025
python -m src.run_agent --competition 2014 --season 2025 --team Barcelona --output reports/barcelona_2025.txt --html-output reports/barcelona_2025.html --visual reports/barcelona_2025
```

El filtro busca coincidencias parciales en los nombres de equipo (local y visitante), por lo que
`Mallorca` encontrará partidos de `RCD Mallorca` sin necesidad de escribir el nombre completo.

## Analizar la temporada actual de La Liga

```bash
# 1. Construir la DB (solo la primera vez o al inicio de temporada)
python -m src.run_agent --fetch-real --competition 2014 --season 2025

# 2. Ver equipos disponibles
python -m src.run_agent --list-teams --competition 2014 --season 2025

# 3. Generar informe de un equipo
python -m src.run_agent --competition 2014 --season 2025 --team Mallorca --output reports/mallorca.txt --html-output reports/mallorca.html --visual reports/mallorca
```

## Ejemplos rápidos

- Limpiar reportes anteriores antes de generar un nuevo informe:
  ```bash
  python -m src.run_agent --data data/example_matches.csv --output reports/informe.txt --visual reports --html-output reports/informe.html --clean-reports
  ```

- Analizar solo Mallorca en La Liga 2025 (desde DB local, sin API):
  ```bash
  python -m src.run_agent --competition 2014 --season 2025 --team Mallorca --output reports/mallorca_2025.txt --html-output reports/mallorca_2025.html --visual reports/mallorca_2025
  ```

- Analizar La Liga 2024 completa:
  ```bash
  python -m src.run_agent --fetch-real --competition 2014 --season 2024 --output reports/laliga_2024.txt --html-output reports/laliga_2024.html --visual reports/laliga_2024
  ```

- Analizar Premier League 2025:
  ```bash
  python -m src.run_agent --fetch-real --competition 2021 --season 2025 --output reports/premier_2025.txt --html-output reports/premier_2025.html --visual reports/premier_2025
  ```

## Archivos de base de datos generados

Cada combinación de competición y temporada genera un archivo CSV propio en `data/`:

| Archivo | Contenido |
|---|---|
| `data/db_2014_2025.csv` | La Liga temporada 2025-2026 |
| `data/db_2021_2025.csv` | Premier League temporada 2025-2026 |
| `data/db_2014_2024.csv` | La Liga temporada 2024-2025 |

Estos archivos actúan como caché: una vez construidos, los informes de equipo no requieren conexión.

## Nota

El filtro `--team` usa búsqueda parcial. Si no encuentras el equipo, usa `--list-teams` primero
para ver el nombre exacto que usa la DB.

---

## Comandos del bot de Telegram

Arranca el bot con `python bot.py`. Requiere `TELEGRAM_BOT_TOKEN` en `.env`.

### Comandos disponibles

| Comando | Alias en inglés | Descripción |
|---------|-----------------|-------------|
| `/start` | — | Bienvenida e instrucciones |
| `/ayuda [cmd]` | `/help` | Ayuda general o de un comando concreto |
| `/competiciones` | `/competitions` | Lista de IDs de competición |
| `/equipos <comp> <temp>` | `/teams` | Equipos disponibles en la DB local |
| `/liga <comp> <temp>` | `/league` | Informe completo de liga |
| `/equipo <comp> <temp> <nombre>` | `/team` | Informe de un equipo |
| `/jornada <comp> <temp> <N>` | `/matchday` | Informe de una jornada |
| `/compare <comp> <temp> <eq1> \| <eq2>` | — | Comparativa entre dos equipos |
| `/pdf <comp> <temp>` | — | Genera y envía el informe en PDF |
| `/suscribir <comp> <temp> <equipo>` | — | Activa alertas de racha negativa |
| `/suscripciones` | — | Lista tus suscripciones activas |
| `/desuscribir <comp> <temp> <equipo>` | — | Cancela una suscripción |

### Alertas proactivas

Configura la hora de envío en `.env`:

```
ALERT_HOUR=9
```

El bot comprueba diariamente los equipos suscritos y envía un aviso si alguno lleva 3 o más derrotas consecutivas.

### Exportar informe a PDF por bot

```
/pdf 2014 2024
```

Requiere `weasyprint` instalado en el servidor (`pip install weasyprint`). En Linux puede necesitar `apt-get install libpango-1.0-0`.

---

## Dashboard web

Arranca con `streamlit run app.py`.

### Modo multi-liga

Activa el checkbox "🔀 Comparar múltiples ligas" en el sidebar para seleccionar hasta 3 competiciones y temporadas y comparar sus clasificaciones + KPIs en tabs paralelos.

### Exportar a PDF desde el dashboard

Al final de cualquier informe generado, pulsa el botón **📄 Generar PDF del informe**. Si la generación es correcta, aparecerá el botón **⬇️ Descargar PDF**.

Requiere `weasyprint` instalado (`pip install weasyprint`).
