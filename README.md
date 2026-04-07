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
from src.api_client import SportsDBAPI
api = SportsDBAPI()
competitions = api.get_competitions()
print(competitions)
```

## Script para obtener datos

> **Nota:** Los scripts de `scripts/` son auxiliares y pueden estar desactualizados.
> El flujo recomendado es usar directamente el CLI con `--fetch-real`.

## Estado actual del proyecto ✅

**¡El agente deportivo está completamente funcional!**

- ✅ **Datos reales**: Acceso a competiciones europeas con API premium
- ✅ **Temporada actual**: Datos de La Liga 2025 (temporada 2025-2026) disponibles
- ✅ **Análisis completo**: Métricas, rankings y visualizaciones automáticas
- ✅ **Informes múltiples**: Texto plano, HTML interactivo y gráficos
- ✅ **Flexibilidad**: Maneja datasets con columnas opcionales
- ✅ **DB local incremental**: Caché por competición/temporada, informes de equipo sin API
- ✅ **18 estadísticas técnicas**: xG, tiros, posesión, corners, pases, paradas, etc.
- ✅ **Evolución temporal**: gráfico de línea por jornada (goles, xG, tiros a puerta)
- ✅ **Comparativa vs liga**: cada métrica del equipo frente a la media de la competición
- ✅ **Listado de equipos**: `--list-teams` muestra los equipos disponibles en la DB local

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

Para usar datos reales de competiciones con TheSportsDB:

1. Puedes usar la key pública de pruebas `123` (limitada)
2. Opcionalmente, crea tu propia API key en: https://www.thesportsdb.com
3. Crea un archivo `.env` en la raíz del proyecto:

```
THESPORTSDB_API_KEY=tu_api_key_aqui
```

O configura la variable de entorno:

```bash
# Windows
set THESPORTSDB_API_KEY=tu_api_key_aqui

# Linux/Mac
export THESPORTSDB_API_KEY=tu_api_key_aqui
```

## Base de datos local y flujo de datos

El agente utiliza una **base de datos local por competición y temporada** (`data/db_<competition>_<season>.csv`).
Este enfoque separa la *actualización de datos* de la *generación de informes*:

1. **`--fetch-real`** — consulta la API, detecta partidos nuevos, enriquece solo los pendientes y actualiza la DB.
2. **Sin `--fetch-real`** — carga directamente la DB local y genera el informe sin ninguna llamada a la API.

### Campos base por partido

- `date`, `local_team`, `visitante_team`, `goles_local`, `goles_visitante`
- `status`, `competition`, `season`, `jornada`
- `estadio`, `ciudad`, `arbitro`, `espectadores`

### Estadísticas técnicas (via `lookupeventstats.php`)

- `shots_local/visitante` — tiros totales, a puerta, fuera, bloqueados, dentro/fuera del área
- `posesion_local/visitante` — porcentaje de posesión
- `xg_local/xg_visitante` — expected goals
- `corners_local/visitante` — córners
- `faltas_local/visitante` — faltas cometidas
- `fueras_de_juego_local/visitante` — fueras de juego
- `amarillas_local/visitante`, `rojas_local/visitante` — tarjetas
- `paradas_local/visitante` — paradas del portero
- `pases_local/visitante`, `pases_precisos_local/visitante`, `precision_pases_local/visitante`

## Uso básico

**Ver qué equipos hay disponibles en la DB:**

```bash
python -m src.run_agent --list-teams --competition 2014 --season 2025
```

**Construir/actualizar la DB de una competición:**

```bash
python -m src.run_agent --fetch-real --competition 2014 --season 2025 --output reports/laliga_2025.txt --html-output reports/laliga_2025.html --visual reports/laliga_2025
```

**Generar informe de equipo desde la DB local (sin API):**

```bash
python -m src.run_agent --competition 2014 --season 2025 --team Mallorca --output reports/mallorca.txt --html-output reports/mallorca.html --visual reports/mallorca
```

El informe incluye automáticamente:
- Gráfico de evolución temporal por jornada (goles, xG, tiros a puerta)
- Tabla comparativa de cada métrica del equipo vs media de la liga

**Usar un dataset CSV externo:**

```bash
python -m src.run_agent --data data/example_matches.csv --output reports/informe.txt --visual reports
```

Para una guía rápida de todos los comandos, consulta `COMMANDS.md`.
También puedes consultar el historial de cambios en `CHANGELOG.md`.

**Obtener datos de otras competiciones:**

```bash
# La Liga 2025
python -m src.run_agent --fetch-real --competition 2014 --season 2025 --output reports/laliga_2025.txt --visual reports/laliga_2025

# Premier League 2025
python -m src.run_agent --fetch-real --competition 2021 --season 2025 --output reports/premier_2025.txt --visual reports/premier_2025

# Bundesliga 2024
python -m src.run_agent --fetch-real --competition 2002 --season 2024 --output reports/bundesliga_2024.txt --visual reports/bundesliga_2024
```

## Extensión

- Añade tus propios datos en `data/` con el mismo formato
- Amplía `src/analysis.py` con nuevas métricas
- Crea notebooks en `notebooks/` para análisis interactivo
