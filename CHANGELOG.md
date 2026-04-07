# Registro de cambios

Todos los cambios importantes de este proyecto se documentarán en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Añadido
- `COMMANDS.md` con un conjunto completo de ejemplos de uso y comandos del agente.
- Soporte para filtrar análisis por equipo usando `--team` en `src/run_agent.py`.
- `CHANGELOG.md` para seguir el historial de cambios del proyecto.
- `scripts/fetch_real_data.py` para descargar datasets reales de partidos desde Football-Data.org.
- `scripts/get_current_season.py` para obtener automáticamente la temporada actual de La Liga.
- `src/api_client.py` para gestionar el acceso a la API de Football-Data.org e importar partidos reales.
- Mejoras en `src/agent.py` para análisis filtrado por equipo y generación de informes.
- Actualizaciones en `README.md` documentando los nuevos comandos, uso de API y soporte de temporada actual.

### Cambiado
- `src/run_agent.py` ahora soporta los parámetros `--team`, `--fetch-real`, `--competition` y `--season`.
- `.gitignore` actualizado para ignorar la salida generada en `reports/`.
- Añadido `.env.example` para la configuración de la clave API.

### Corregido
- El filtrado por equipo ahora funciona con nombres parciales en las columnas `local_team` o `visitante_team`.
- Se agregó una ruta de carga segura para que las columnas opcionales de la API no rompan la generación de informes.
