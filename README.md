# Agente Deportivo

Proyecto para crear un agente de análisis de datasets deportivos, enfocado en partidos recientes de fútbol.

## Objetivo

- Ingerir datos de partidos de fútbol
- Extraer métricas clave (goles, posesión, tiros, faltas, tarjetas)
- Generar informes claros y bien estructurados
- Crear gráficos automáticos para apoyar la interpretación

## Estructura del proyecto

- `src/` — Código fuente del agente, análisis y visualización
- `data/` — Datasets y archivos CSV de partidos
- `reports/` — Informes y gráficos generados por el agente
- `requirements.txt` — Dependencias del proyecto

## Dataset de ejemplo

El CSV de ejemplo `data/example_matches.csv` incluye columnas como:

- `date`
- `local_team`, `visitante_team`
- `goles_local`, `goles_visitante`
- `posesion_local`, `posesion_visitante`
- `shots_local`, `shots_visitante`
- `shots_on_target_local`, `shots_on_target_visitante`
- `corners_local`, `corners_visitante`
- `amarillas_local`, `amarillas_visitante`
- `rojas_local`, `rojas_visitante`
- `faltas_local`, `faltas_visitante`

## Instalación

1. Crear un entorno virtual (recomendado)
2. Ejecutar:

```bash
pip install -r requirements.txt
```

## Uso básico

Ejecuta el agente con el dataset de ejemplo:

```bash
python -m src.run_agent --data data/example_matches.csv --output reports/informe.txt --visual reports
```

Generar también un informe HTML:

```bash
python -m src.run_agent --data data/example_matches.csv --output reports/informe.txt --visual reports --html-output reports/informe.html
```

El comando generará:

- `reports/informe.txt` — informe de texto con métricas y rankings
- `reports/informe.html` — informe HTML con tablas y gráficos
- `reports/goals_distribution.png` — histograma de goles
- `reports/possession_distribution.png` — caja de posesión
- `reports/card_summary.png` — resumen de tarjetas

## Extensión

- Añade tus propios datos en `data/` con el mismo formato
- Amplía `src/analysis.py` con nuevas métricas
- Crea notebooks en `notebooks/` para análisis interactivo
