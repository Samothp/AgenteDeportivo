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

- ✅ **Datos reales**: Acceso a competiciones europeas con API premium (TheSportsDB)
- ✅ **Temporada actual**: Datos de La Liga 2025 (temporada 2025-2026) disponibles
- ✅ **Análisis completo**: Métricas, rankings y visualizaciones automáticas
- ✅ **Informes múltiples**: Texto plano, HTML interactivo, JSON y gráficos
- ✅ **Flexibilidad**: Maneja datasets con columnas opcionales
- ✅ **DB local incremental**: Caché por competición/temporada con TTL configurable
- ✅ **18 estadísticas técnicas**: xG, tiros, posesión, corners, pases, paradas, etc.
- ✅ **Evolución temporal**: gráfico de línea por jornada (goles, xG, tiros a puerta)
- ✅ **Comparativa vs liga**: cada métrica del equipo frente a la media de la competición
- ✅ **Percentiles de liga**: percentil de cada métrica del equipo sobre el resto de equipos
- ✅ **xPts (puntos esperados)**: modelo Poisson sobre xG, clasificación alternativa en modo Liga
- ✅ **Eficiencia ofensiva**: ratio `goles reales / xG` (overperformance) en todos los modos
- ✅ **Rachas máximas**: sin perder, goleadora y sin marcar en el historial del equipo
- ✅ **Conclusiones automáticas**: bloque de insights basado en reglas al final de cada informe
- ✅ **Narrativa intertemporada**: con `--seasons`, evolución % de métricas entre temporadas
- ✅ **Listado de equipos**: `--list-teams` muestra los equipos disponibles en la DB local
- ✅ **6 tipos de informe**: Liga, Equipo, Jornada, Partido, Jugador y Compare
- ✅ **Exportación a PDF**: botón en el dashboard y comando `/pdf` en el bot (requiere `weasyprint`)
- ✅ **Modo multi-liga en el dashboard**: compara hasta 3 competiciones simultáneamente en tabs
- ✅ **Alertas proactivas Telegram**: `/suscribir` para recibir avisos de rachas negativas (≥3 derrotas)
- ✅ **Caché de gráficos por hash**: los PNG se reutilizan si los datos no cambian (hash MD5)
- ✅ **Bot bilingüe**: comandos en inglés (`/league`, `/team`, `/matchday`, `/help`, `/competitions`, `/teams`)

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

## Tipos de informe

El agente detecta automáticamente el tipo de informe según los argumentos proporcionados:

| Tipo | Argumentos necesarios | Descripción |
|------|----------------------|-------------|
| **Liga** | solo `--competition` y `--season` | Clasificación, xPts, récords y stats de toda la temporada |
| **Equipo** | `--team <nombre>` | W/D/L, métricas con percentiles, comparativa vs liga, rachas, conclusiones |
| **Jornada** | `--jornada <N>` | Todos los resultados y estadísticas de una jornada concreta |
| **Partido** | `--match-id <id>` | Ficha técnica detallada y estadísticas cara a cara de un partido |
| **Jugador** | `--team <nombre>` + `--player <nombre>` | Perfil individual: stats, ratios, ranking y gráficos comparativos |
| **Compare** | `--compare TEAM1 TEAM2` | Radar comparativo, H2H y diferencias en todas las métricas entre dos equipos |

## Uso básico

**Ver qué equipos hay disponibles en la DB:**

```bash
python -m src.run_agent --list-teams --competition 2014 --season 2025
```

**Informe de liga completo:**

```bash
python -m src.run_agent --competition 2014 --season 2025 --output reports/laliga.txt --html-output reports/laliga.html --visual reports/laliga
```

**Informe de equipo desde la DB local (sin API):**

```bash
python -m src.run_agent --competition 2014 --season 2025 --team Mallorca --output reports/mallorca.txt --html-output reports/mallorca.html --visual reports/mallorca
```

**Informe de jornada:**

```bash
python -m src.run_agent --competition 2014 --season 2025 --jornada 15 --output reports/jornada_15.txt --html-output reports/jornada_15.html --visual reports/jornada_15
```

**Ficha de un partido concreto:**

```bash
python -m src.run_agent --competition 2014 --season 2025 --match-id 2279399 --output reports/partido.txt --html-output reports/partido.html --visual reports/partido
```

**Perfil de un jugador:**

```bash
python -m src.run_agent --competition 2014 --season 2025 --team Mallorca --player "Vedat Muriqi" --output reports/muriqi.txt --html-output reports/muriqi.html --visual reports/muriqi
```

**Comparativa entre dos equipos:**

```bash
python -m src.run_agent --competition 2014 --season 2025 --compare "Real Madrid" "Barcelona" --output reports/compare.txt --html-output reports/compare.html
```

**Análisis de un rango de jornadas:**

```bash
python -m src.run_agent --competition 2014 --season 2025 --matchday-range 1 17 --output reports/primera_vuelta.txt
```

**Análisis multi-temporada con narrativa intertemporada:**

```bash
python -m src.run_agent --competition 2014 --team Barcelona --seasons 2022 2023 2024 --output reports/barca_evolucion.txt
```

**Informe rápido sin gráficos (solo texto):**

```bash
python -m src.run_agent --competition 2014 --season 2025 --team Mallorca --no-charts --output reports/mallorca_rapido.txt
```

**Salida en formato JSON:**

```bash
python -m src.run_agent --competition 2014 --season 2025 --team Mallorca --format json --output reports/mallorca.json
```

**Construir/actualizar la DB de una competición:**

```bash
python -m src.run_agent --fetch-real --competition 2014 --season 2025 --output reports/laliga_2025.txt --html-output reports/laliga_2025.html --visual reports/laliga_2025
```

Para una guía completa de todos los comandos y flags, consulta `COMMANDS.md`.
Para el historial de cambios, consulta `CHANGELOG.md`.

**Obtener datos de otras competiciones:**

```bash
# La Liga 2025
python -m src.run_agent --fetch-real --competition 2014 --season 2025 --output reports/laliga_2025.txt --visual reports/laliga_2025

# Premier League 2025
python -m src.run_agent --fetch-real --competition 2021 --season 2025 --output reports/premier_2025.txt --visual reports/premier_2025

# Bundesliga 2024
python -m src.run_agent --fetch-real --competition 2002 --season 2024 --output reports/bundesliga_2024.txt --visual reports/bundesliga_2024

# UEFA Champions League 2025
python -m src.run_agent --fetch-real --competition 2001 --season 2025 --output reports/ucl_2025.txt --visual reports/ucl_2025
```

## Extensión

- Añade tus propios datos en `data/` con el mismo formato
- Amplía `src/analysis.py` con nuevas métricas
- Amplía `src/visualizer.py` con nuevos tipos de gráficos
- Amplía `src/agent.py` añadiendo nuevos modos de análisis

## Dashboard web

Arranca el dashboard con:

```bash
streamlit run app.py
```

Funcionalidades destacadas:
- Selector de competición, temporada y modo de informe en el sidebar
- **Indicador de frescura** de datos (antigüedad del caché local)
- **Descarga de datos** directamente desde el dashboard (sin terminal)
- **Modo multi-liga**: checkbox "Comparar múltiples ligas" → hasta 3 competiciones en tabs paralelos
- **Exportar a PDF**: botón al final del informe; descarga directa desde el navegador

## Bot de Telegram

Arranca el bot con:

```bash
python bot.py
```

Requiere `TELEGRAM_BOT_TOKEN` en el archivo `.env`.

### Comandos principales

| Comando | Descripción |
|---------|-------------|
| `/start` | Bienvenida e instrucciones |
| `/ayuda [cmd]` | Ayuda general o de un comando específico |
| `/competiciones` | Lista de IDs de competición disponibles |
| `/equipos <comp> <temp>` | Equipos disponibles en la DB local |
| `/liga <comp> <temp>` | Informe completo de liga |
| `/equipo <comp> <temp> <nombre>` | Informe de un equipo |
| `/jornada <comp> <temp> <N>` | Informe de una jornada |
| `/compare <comp> <temp> <eq1> \| <eq2>` | Comparativa entre dos equipos |
| `/pdf <comp> <temp>` | Genera y envía el informe en PDF |
| `/suscribir <comp> <temp> <equipo>` | Activa alertas de racha negativa para un equipo |
| `/suscripciones` | Lista tus suscripciones activas |
| `/desuscribir <comp> <temp> <equipo>` | Cancela una suscripción |

### Aliases en inglés

`/help`, `/competitions`, `/teams`, `/league`, `/team`, `/matchday` son alias directos de sus equivalentes en español.
