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

## IDs de competiciones disponibles

- **2014**: La Liga (España)
- **2021**: Premier League (Inglaterra)
- **2002**: Bundesliga (Alemania)
- **2019**: Serie A (Italia)
- **2015**: Ligue 1 (Francia)
- **2017**: Primeira Liga (Portugal)
- **2001**: UEFA Champions League
- **2146**: UEFA Europa League

Para ver todas las competiciones disponibles, ejecuta:

```python
from src.api_client import FootballDataAPI
api = FootballDataAPI()
competitions = api.get_competitions()
print(competitions)
```

## Script para obtener datos

También puedes usar el script incluido:

```bash
python scripts/fetch_real_data.py
```

Este script obtiene datos de La Liga 2023 y los guarda en `data/laliga_2023.csv`.

Para obtener datos de la **temporada actual**:

```bash
python scripts/get_current_season.py
```

Este script obtiene automáticamente los datos más recientes de La Liga y muestra estadísticas básicas.

## Estado actual del proyecto ✅

**¡El agente deportivo está completamente funcional!**

- ✅ **Datos reales**: Acceso a competiciones europeas con API gratuita
- ✅ **Temporada actual**: Datos de La Liga 2025 (temporada 2025-2026) disponibles
- ✅ **Análisis completo**: Métricas, rankings y visualizaciones automáticas
- ✅ **Informes múltiples**: Texto plano, HTML interactivo y gráficos
- ✅ **Flexibilidad**: Maneja datasets con columnas opcionales

### Último análisis disponible

**La Liga 2025** (temporada actual):
- 300 partidos analizados
- 806 goles totales (promedio 2.69 por partido)
- **FC Barcelona**: Máximo goleador (80 goles)
- **Real Madrid CF**: Menos goles concedidos (28)

## Instalación

1. Crear un entorno virtual (recomendado)
2. Ejecutar:

```bash
pip install -r requirements.txt
```

## Configuración para datos reales

Para usar datos reales de competiciones, necesitas una API key gratuita de Football-Data.org:

1. Regístrate gratis en: https://www.football-data.org/client/register
2. Obtén tu API key
3. Crea un archivo `.env` en la raíz del proyecto:

```
FOOTBALL_DATA_API_KEY=tu_api_key_aqui
```

O configura la variable de entorno:

```bash
# Windows
set FOOTBALL_DATA_API_KEY=tu_api_key_aqui

# Linux/Mac
export FOOTBALL_DATA_API_KEY=tu_api_key_aqui
```

## Uso básico

Ejecuta el agente con el dataset de ejemplo:

```bash
python -m src.run_agent --data data/example_matches.csv --output reports/informe.txt --visual reports
```

Para una guía rápida de comandos, consulta `COMMANDS.md`.

Generar también un informe HTML:

```bash
python -m src.run_agent --data data/example_matches.csv --output reports/informe.txt --visual reports --html-output reports/informe.html
```

**Obtener datos reales de competiciones:**

```bash
# La Liga española (2023)
python -m src.run_agent --fetch-real --competition 2014 --season 2023 --output reports/laliga_2023.txt --html-output reports/laliga_2023.html

# Premier League (2023)
python -m src.run_agent --fetch-real --competition 2021 --season 2023 --output reports/premier_2023.txt --html-output reports/premier_2023.html

# Bundesliga (2023)
python -m src.run_agent --fetch-real --competition 2002 --season 2023 --output reports/bundesliga_2023.txt --html-output reports/bundesliga_2023.html
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
