"""Constantes numéricas centralizadas del proyecto.

Todas las reglas de negocio expresadas como números se definen aquí para
evitar magic numbers dispersos en analysis.py, agent.py y bot.py.
"""

# ---------------------------------------------------------------------------
# Overperformance xG (ratio goles reales / xG)
# ---------------------------------------------------------------------------

#: El equipo convierte significativamente más de lo esperado por xG.
OVERPERFORMANCE_EXCELLENT: float = 1.2

#: El equipo convierte significativamente menos de lo esperado por xG.
OVERPERFORMANCE_POOR: float = 0.8

# ---------------------------------------------------------------------------
# Rachas y forma reciente
# ---------------------------------------------------------------------------

#: Número de partidos considerados "forma reciente".
RECENT_FORM_MATCHES: int = 5

#: Derrotas consecutivas para emitir una alerta proactiva (Fase 10.2 / 11.3).
CONSECUTIVE_LOSSES_ALERT: int = 3

#: Victorias/derrotas consecutivas recientes para calificar el estado de forma.
FORM_STREAK_THRESHOLD: int = 3

#: Umbral de goles por partido para calificar al ataque como prolífico.
HIGH_SCORING_THRESHOLD: float = 3.0

# ---------------------------------------------------------------------------
# Caché y TTL
# ---------------------------------------------------------------------------

#: Días por defecto antes de avisar que el caché está desactualizado.
CACHE_TTL_DAYS_DEFAULT: int = 7

# ---------------------------------------------------------------------------
# Rankings y paginación
# ---------------------------------------------------------------------------

#: Valor por defecto de top-N en rankings de equipos y jugadores.
TOP_N_DEFAULT: int = 5

# ---------------------------------------------------------------------------
# Estadísticas de liga (umbrales mínimos de partidos)
# ---------------------------------------------------------------------------

#: Mínimo de partidos para calcular percentiles de liga con significancia.
MIN_MATCHES_PERCENTILE: int = 3

#: Mínimo de partidos para incluir un equipo en el ranking de eficiencia.
MIN_MATCHES_RANKING: int = 5

# ---------------------------------------------------------------------------
# Posesión
# ---------------------------------------------------------------------------

#: Porcentaje de posesión mínimo para considerar a un equipo dominador.
POSSESSION_DOMINANT_THRESHOLD: float = 50.0
