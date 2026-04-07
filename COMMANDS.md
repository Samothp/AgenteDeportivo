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
--list-teams     Lista los equipos disponibles en la DB y termina
--seasons        Lista de temporadas a combinar (ej. --seasons 2024 2025)
```

## Detección automática del tipo de informe

El agente selecciona el modo según los argumentos:

| Modo | Condición | Descripción |
|------|-----------|-------------|
| **Liga** | solo `--competition` + `--season` | Clasificación, récords, stats de la temporada |
| **Equipo** | `--team` (sin `--player`) | Análisis del equipo: W/D/L, métricas, comparativa vs liga |
| **Jornada** | `--jornada N` | Resultados y estadísticas de una jornada |
| **Partido** | `--match-id ID` | Ficha técnica detallada de un partido |
| **Jugador** | `--team` + `--player` | Perfil individual de un jugador |

---

## Informe de Liga

Panorama completo de una temporada: clasificación, récords, estadísticas por equipo y rendimiento local/visitante.

```bash
python -m src.run_agent --competition 2014 --season 2025 \
  --output reports/laliga.txt --html-output reports/laliga.html --visual reports/laliga
```

Gráficos generados: `league_table.png`, `goals_per_team.png`, `xg_per_team.png`, `home_away_performance.png`

---

## Informe de Equipo

Análisis filtrado por equipo: historial W/D/L, métricas técnicas, comparativa vs liga, top goleadores y asistentes.

```bash
python -m src.run_agent --competition 2014 --season 2025 --team Mallorca \
  --output reports/mallorca.txt --html-output reports/mallorca.html --visual reports/mallorca
```

El filtro usa búsqueda parcial: `Mallorca` localiza `RCD Mallorca`. Usa `--list-teams` para ver nombres exactos.

Gráficos: `goals_distribution.png`, `possession_distribution.png`, `card_summary.png`, `xg_per_match.png`, `shots_comparison.png`, `temporal_evolution.png`

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
