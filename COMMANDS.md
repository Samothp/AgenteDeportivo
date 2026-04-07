# Comandos del Agente Deportivo

Este archivo resume los comandos principales del agente para analizar datos deportivos.

## Uso general

```bash
python -m src.run_agent --data data/example_matches.csv --output reports/informe.txt --visual reports
```

- `--data` : ruta al archivo CSV de partidos
- `--output` : ruta del informe de texto generado
- `--visual` : carpeta donde se guardan los gráficos
- `--clean-reports` : elimina archivos anteriores en la carpeta de reportes antes de generar nuevos

## Generar informe HTML

```bash
python -m src.run_agent --data data/example_matches.csv --output reports/informe.txt --visual reports --html-output reports/informe.html
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

**Recomendado: primero actualiza la DB, luego genera el informe sin API:**

```bash
# 1. Actualizar/construir la DB de La Liga 2025 (solo si hay jornadas nuevas)
python -m src.run_agent --fetch-real --competition 2014 --season 2025

# 2. Generar informes de distintos equipos sin llamar a la API
python -m src.run_agent --competition 2014 --season 2025 --team Mallorca --output reports/mallorca_2025.txt --html-output reports/mallorca_2025.html --visual reports/mallorca_2025
python -m src.run_agent --competition 2014 --season 2025 --team Barcelona --output reports/barcelona_2025.txt --html-output reports/barcelona_2025.html --visual reports/barcelona_2025
```

El filtro busca coincidencias parciales en los nombres de equipo (local y visitante), por lo que
`Mallorca` encontrará partidos de `RCD Mallorca` sin necesidad de escribir el nombre completo.

## Analizar la temporada actual de La Liga

```bash
python scripts/get_current_season.py
```

Este script obtiene la temporada actual de La Liga y guarda los datos en:

- `data/laliga_actual.csv`

La fuente de datos para este flujo es TheSportsDB.

Luego puedes generar un informe completo con:

```bash
python -m src.run_agent --data data/laliga_actual.csv --output reports/laliga_actual_informe.txt --html-output reports/laliga_actual_informe.html --visual reports/laliga_actual
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

Si usas un equipo y no aparece en el informe, revisa el nombre exacto que usa el dataset. El filtro busca coincidencias parciales en `local_team` y `visitante_team`.
