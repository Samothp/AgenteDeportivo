"""Dashboard web — Agente Deportivo (Streamlit).

Arrancar con:
    streamlit run app.py

Requisitos: streamlit (incluido en requirements.txt)
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from src.constants import COMPETITION_NAMES

load_dotenv()

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    format="%(asctime)s — %(name)s — %(levelname)s — %(message)s",
    level=logging.INFO,
)
_logger = logging.getLogger("AgenteDeportivo.dashboard")

# ---------------------------------------------------------------------------
# Configuración de página
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Agente Deportivo",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Beta access — password gate
# ---------------------------------------------------------------------------

# Contraseñas válidas: clave → nombre del usuario (para el saludo)
# Añade o elimina entradas para gestionar el acceso a la beta.
# Puedes sobreescribir con la variable de entorno BETA_PASSWORDS
# en formato "pass1:Nombre1,pass2:Nombre2"
_DEFAULT_BETA_USERS: dict[str, str] = {
    "betauser1": "Beta User 1",
    "betauser2": "Beta User 2",
}

def _load_beta_users() -> dict[str, str]:
    raw = os.getenv("BETA_PASSWORDS", "")
    if not raw:
        return _DEFAULT_BETA_USERS
    users: dict[str, str] = {}
    for entry in raw.split(","):
        entry = entry.strip()
        if ":" in entry:
            pwd, name = entry.split(":", 1)
            users[pwd.strip()] = name.strip()
    return users or _DEFAULT_BETA_USERS

def _check_beta_access() -> None:
    """Muestra pantalla de login hasta que el usuario introduzca una clave válida."""
    if st.session_state.get("beta_authenticated"):
        return

    st.title("⚽ Agente Deportivo — Acceso Beta")
    st.info("Introduce tu contraseña de acceso a la beta para continuar.")

    with st.form("beta_login"):
        pwd = st.text_input("Contraseña", type="password", placeholder="••••••••")
        submitted = st.form_submit_button("Entrar")

    if submitted:
        beta_users = _load_beta_users()
        if pwd in beta_users:
            st.session_state["beta_authenticated"] = True
            st.session_state["beta_user_name"] = beta_users[pwd]
            _logger.info("Beta login exitoso: usuario='%s'", beta_users[pwd])
            st.rerun()
        else:
            _logger.warning("Beta login fallido: contraseña incorrecta (IP desconocida)")
            st.error("Contraseña incorrecta. Contacta al administrador para obtener acceso.")

    st.stop()

_check_beta_access()

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

MODES = ["Liga", "Equipo", "Jornada", "Partido", "Jugador", "Compare"]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_db_path(competition: int, season: str) -> Path:
    from src.data_loader import get_db_path
    return get_db_path(competition, season)


def _list_teams(competition: int, season: str) -> list[str]:
    from src.data_loader import list_available_teams
    return list_available_teams(competition, season)


@st.cache_data(show_spinner=False)
def _run_agent(competition: int, season: str, mode: str, **kwargs) -> tuple[dict, list[str]]:
    """Ejecuta el agente y devuelve (json_payload, image_paths).

    Cachea el resultado por (competition, season, mode, kwargs hashables).
    La caché se invalida automáticamente al cambiar cualquier parámetro.
    """
    from src.agent import SportsAgent
    from src.data_loader import get_db_path

    db_path = get_db_path(competition, season)
    if not db_path.exists():
        raise FileNotFoundError(
            f"No hay DB local para competition={competition} season={season}. "
            "Descarga los datos primero con --fetch-real desde la CLI."
        )

    # Directorio temporal para los gráficos (se reutiliza entre recargas dentro de la sesión)
    tmp_dir = Path(tempfile.mkdtemp(prefix="agente_deportivo_"))

    agent = SportsAgent(
        data_path=str(db_path),
        fetch_real=False,
        competition_id=competition,
        season=season,
        no_charts=False,
        **kwargs,
    )
    agent.load_data()
    agent.analyze()

    json_str = agent.generate_json_report()
    image_paths = agent.save_visual_report(str(tmp_dir))

    return json.loads(json_str), image_paths


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

st.sidebar.title("⚽ Agente Deportivo")
st.sidebar.markdown("---")

competition = st.sidebar.selectbox(
    "Competición",
    options=list(COMPETITION_NAMES.keys()),
    format_func=lambda x: COMPETITION_NAMES[x],
)
season = st.sidebar.text_input("Temporada (YYYY)", value="2024")
mode = st.sidebar.radio("Modo de informe", MODES)

st.sidebar.markdown("---")

# Inputs adicionales según el modo
extra_kwargs: dict = {}

if mode == "Equipo":
    teams = _list_teams(competition, season)
    if teams:
        team = st.sidebar.selectbox("Equipo", teams)
    else:
        team = st.sidebar.text_input("Equipo (nombre parcial)")
    extra_kwargs["team"] = team

elif mode == "Jornada":
    jornada = st.sidebar.number_input("Número de jornada", min_value=1, max_value=38, value=1, step=1)
    extra_kwargs["matchday"] = int(jornada)

elif mode == "Partido":
    match_id = st.sidebar.number_input("ID del partido (id_event)", min_value=1, value=1, step=1)
    extra_kwargs["match_id"] = int(match_id)

elif mode == "Jugador":
    teams = _list_teams(competition, season)
    if teams:
        team = st.sidebar.selectbox("Equipo", teams)
    else:
        team = st.sidebar.text_input("Equipo (nombre parcial)")
    player = st.sidebar.text_input("Jugador (nombre parcial)")
    extra_kwargs["team"] = team
    extra_kwargs["player"] = player

elif mode == "Compare":
    teams = _list_teams(competition, season)
    if teams:
        team1 = st.sidebar.selectbox("Equipo 1", teams, index=0)
        team2 = st.sidebar.selectbox("Equipo 2", teams, index=min(1, len(teams) - 1))
    else:
        team1 = st.sidebar.text_input("Equipo 1")
        team2 = st.sidebar.text_input("Equipo 2")
    extra_kwargs["compare"] = (team1, team2)

elif mode == "Liga":
    use_range = st.sidebar.checkbox("Filtrar rango de jornadas")
    if use_range:
        col1, col2 = st.sidebar.columns(2)
        start = col1.number_input("Desde", min_value=1, max_value=38, value=1, step=1)
        end = col2.number_input("Hasta", min_value=1, max_value=38, value=19, step=1)
        extra_kwargs["matchday_range"] = (int(start), int(end))

top_n = st.sidebar.slider("Top N en rankings", min_value=3, max_value=20, value=5)
extra_kwargs["top_n"] = top_n

st.sidebar.markdown("---")
run_btn = st.sidebar.button("▶ Generar informe", use_container_width=True)

# ---------------------------------------------------------------------------
# Área principal
# ---------------------------------------------------------------------------

_beta_name = st.session_state.get("beta_user_name", "")
_title_suffix = f" · Bienvenido, {_beta_name}" if _beta_name else ""
st.title(f"⚽ {COMPETITION_NAMES.get(competition, 'Competición')} — {season}{_title_suffix}")

if not run_btn:
    st.info(
        "Configura los parámetros en el panel lateral y pulsa **▶ Generar informe**.\n\n"
        "**Requisito previo**: la DB local debe existir (`data/db_{competition}_{season}.csv`). "
        "Si no existe, descárgala con:\n"
        "```\npython -m src.run_agent --fetch-real --competition <ID> --season <YYYY>\n```"
    )
    st.stop()

# ---------------------------------------------------------------------------
# Ejecución del agente
# ---------------------------------------------------------------------------

try:
    with st.spinner("Analizando datos..."):
        payload, image_paths = _run_agent(competition, season, mode, **extra_kwargs)
except FileNotFoundError as e:
    st.error(str(e))
    st.stop()
except Exception as e:
    st.error(f"Error al generar el informe: {e}")
    st.stop()

# ---------------------------------------------------------------------------
# Mostrar resultados
# ---------------------------------------------------------------------------


def _metric_row(label: str, value, delta=None):
    """Muestra una métrica con formato."""
    if value is None:
        return
    if isinstance(value, float):
        value = f"{value:.2f}"
    st.metric(label=label, value=value, delta=delta)


def _show_table(data: list, title: str = ""):
    """Muestra una lista de dicts como tabla."""
    if not data:
        return
    if title:
        st.subheader(title)
    import pandas as pd
    st.dataframe(pd.DataFrame(data), use_container_width=True)


# ── Métricas generales ──────────────────────────────────────────────────────
metrics = payload.get("metrics", {})
if metrics:
    st.subheader("📊 Métricas principales")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        _metric_row("Goles a favor / partido", metrics.get("goles_a_favor_promedio"))
        _metric_row("Total goles a favor", metrics.get("total_goles_a_favor"))
    with col2:
        _metric_row("Goles encajados / partido", metrics.get("goles_concedidos_promedio"))
        _metric_row("Total goles encajados", metrics.get("total_goles_concedidos"))
    with col3:
        _metric_row("xG propio / partido", metrics.get("xg_equipo_promedio"))
        _metric_row("Tiros / partido", metrics.get("tiros_equipo_promedio"))
    with col4:
        _metric_row("Posesión % media", metrics.get("posesion_equipo_promedio"))
        _metric_row("Overperformance xG", metrics.get("overperformance"))

# ── Contenido específico por modo ───────────────────────────────────────────
modo = payload.get("modo", "")

if modo == "liga":
    liga = payload.get("liga_summary", {})
    if liga:
        _show_table(liga.get("clasificacion", []), "🏆 Clasificación")
        st.markdown("---")
        _show_table(liga.get("xpts_standings", []), "📐 Clasificación por xPts (puntos esperados)")
        st.markdown("---")
        _show_table(liga.get("stats_por_equipo", []), "📈 Estadísticas técnicas por equipo")
        st.markdown("---")
        _show_table(liga.get("home_away", []), "🏠 Rendimiento local vs visitante")

elif modo == "equipo":
    rec = payload.get("team_record", {})
    if rec:
        st.subheader("📋 Historial")
        cols = st.columns(5)
        cols[0].metric("Victorias", rec.get("victorias"))
        cols[1].metric("Empates", rec.get("empates"))
        cols[2].metric("Derrotas", rec.get("derrotas"))
        cols[3].metric("Puntos", rec.get("puntos"))
        cols[4].metric("Forma reciente", rec.get("racha_actual"))

    pct = payload.get("league_percentiles", [])
    if pct:
        st.subheader("📊 Percentiles de liga")
        import pandas as pd
        df_pct = pd.DataFrame(pct)
        st.dataframe(df_pct, use_container_width=True)

    _show_table(payload.get("top_scorers", []), "⚽ Top goleadores")
    _show_table(payload.get("highlights", []), "🔥 Partidos destacados")

elif modo == "jornada":
    ms = payload.get("matchday_summary", {})
    if ms:
        st.subheader(f"⚽ Jornada {ms.get('jornada', '')}")
        _show_table(ms.get("matches", []), "Resultados")
        _show_table(ms.get("standings", []), "🏆 Clasificación tras la jornada")

elif modo == "partido":
    md = payload.get("match_detail", {})
    if md:
        local = md.get("local", "Local")
        visitante = md.get("visitante", "Visitante")
        goles_local = md.get("goles_local", "?")
        goles_visitante = md.get("goles_visitante", "?")
        st.subheader(f"🏟️ {local} {goles_local} — {goles_visitante} {visitante}")
        _show_table(md.get("stats", []), "📊 Estadísticas del partido")

elif modo == "jugador":
    pp = payload.get("player_profile", {})
    if pp:
        st.subheader(f"👤 {pp.get('nombre', '')}")
        col1, col2, col3 = st.columns(3)
        col1.metric("Partidos jugados", pp.get("pj"))
        col2.metric("Goles", pp.get("goles"))
        col3.metric("Asistencias", pp.get("asistencias"))

elif modo == "compare":
    c = payload.get("compare_data", {})
    if c:
        st.subheader(f"⚔️ {c.get('team1', '')} vs {c.get('team2', '')}")
        _show_table(c.get("h2h", []), "🤝 Enfrentamientos directos (H2H)")

# ── Gráficos ────────────────────────────────────────────────────────────────
if image_paths:
    st.markdown("---")
    st.subheader("📈 Gráficos")
    cols_per_row = 2
    for i in range(0, len(image_paths), cols_per_row):
        row_paths = image_paths[i: i + cols_per_row]
        cols = st.columns(len(row_paths))
        for col, img_path in zip(cols, row_paths):
            if Path(img_path).exists():
                col.image(img_path, use_container_width=True)

# ── Datos en bruto (expandible) ─────────────────────────────────────────────
with st.expander("🗂️ Datos en bruto (JSON)"):
    st.json(payload)
