# Comandos del Agente Deportivo

Este archivo resume los comandos principales del agente para analizar datos deportivos.

## Uso general

```bash
python -m src.run_agent --data data/example_matches.csv --output reports/informe.txt --visual reports
```

- `--data` : ruta al archivo CSV de partidos
- `--output` : ruta del informe de texto generado
- `--visual` : carpeta donde se guardan los gráficos

## Generar informe HTML

```bash
python -m src.run_agent --data data/example_matches.csv --output reports/informe.txt --visual reports --html-output reports/informe.html
```

## Obtener datos reales de la API

```bash
python -m src.run_agent --fetch-real --competition 2014 --season 2025 --output reports/laliga_2025.txt --html-output reports/laliga_2025.html --visual reports/laliga_2025
```

- `--fetch-real` : obtén datos desde la API en lugar de usar un CSV local
- `--competition` : ID de la competición (`2014` = La Liga)
- `--season` : temporada en formato `YYYY`

## Analizar un equipo específico

Si quieres analizar la temporada de un equipo concreto, usa `--team`:

```bash
python -m src.run_agent --fetch-real --competition 2014 --season 2025 --team Mallorca --output reports/mallorca_2025.txt --html-output reports/mallorca_2025.html --visual reports/mallorca_2025
```

Este comando:
- obtiene los datos de La Liga 2025
- filtra solo los partidos en los que participa el equipo `Mallorca`
- genera un informe de texto y un informe HTML
- crea gráficos para ese subconjunto de partidos

## Analizar la temporada actual de La Liga

```bash
python scripts/get_current_season.py
```

Este script obtiene la temporada actual de La Liga y guarda los datos en:

- `data/laliga_actual.csv`

Luego puedes generar un informe completo con:

```bash
python -m src.run_agent --data data/laliga_actual.csv --output reports/laliga_actual_informe.txt --html-output reports/laliga_actual_informe.html --visual reports/laliga_actual
```

## Ejemplos rápidos

- Analizar solo Mallorca en La Liga 2025:
  ```bash
  python -m src.run_agent --fetch-real --competition 2014 --season 2025 --team Mallorca --output reports/mallorca_2025.txt --html-output reports/mallorca_2025.html --visual reports/mallorca_2025
  ```

- Analizar La Liga 2024 completa:
  ```bash
  python -m src.run_agent --fetch-real --competition 2014 --season 2024 --output reports/laliga_2024.txt --html-output reports/laliga_2024.html --visual reports/laliga_2024
  ```

- Analizar Premier League 2025:
  ```bash
  python -m src.run_agent --fetch-real --competition 2021 --season 2025 --output reports/premier_2025.txt --html-output reports/premier_2025.html --visual reports/premier_2025
  ```

## Nota

Si usas un equipo y no aparece en el informe, revisa el nombre exacto que usa el dataset. El filtro busca coincidencias parciales en `local_team` y `visitante_team`.
