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
from datetime import date
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

# Contraseñas válidas: clave → (nombre del usuario, fecha_expiración | None)
# Formato en BETA_PASSWORDS: "pass1:Nombre1,pass2:Nombre2:2026-06-01"
# La fecha de expiración es opcional; sin fecha, el acceso no expira.
_DEFAULT_BETA_USERS: dict[str, tuple[str, date | None]] = {
    "betauser1": ("Beta User 1", None),
    "betauser2": ("Beta User 2", None),
}


def _parse_expiry(raw: str) -> date | None:
    """Parsea una fecha YYYY-MM-DD; devuelve None si es inválida."""
    try:
        return date.fromisoformat(raw.strip())
    except (ValueError, AttributeError):
        return None


def _load_beta_users() -> dict[str, tuple[str, date | None]]:
    """Carga usuarios beta desde BETA_PASSWORDS en formato 'pass:Nombre[:YYYY-MM-DD]'."""
    raw = os.getenv("BETA_PASSWORDS", "")
    if not raw:
        return _DEFAULT_BETA_USERS
    users: dict[str, tuple[str, date | None]] = {}
    for entry in raw.split(","):
        parts = [p.strip() for p in entry.strip().split(":")]
        if len(parts) >= 2:
            pwd, name = parts[0], parts[1]
            expiry = _parse_expiry(parts[2]) if len(parts) >= 3 else None
            users[pwd] = (name, expiry)
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
            name, expiry = beta_users[pwd]
            # 9.4 — Verificar expiración
            if expiry is not None and date.today() > expiry:
                _logger.warning(
                    "Beta login rechazado por expiración: usuario='%s' expiró=%s", name, expiry
                )
                st.error(
                    f"Tu acceso beta expiró el **{expiry}**. "
                    "Contacta al administrador para renovarlo."
                )
            else:
                st.session_state["beta_authenticated"] = True
                st.session_state["beta_user_name"] = name
                _logger.info("Beta login exitoso: usuario='%s'", name)
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

# 9.1 — Indicador de frescura de datos
def _show_data_freshness(competition: int, season: str) -> None:
    """Muestra en el sidebar la antigüedad del caché local."""
    from src.data_loader import get_cache_age_days, get_db_path
    db = get_db_path(competition, season)
    if not db.exists():
        st.sidebar.warning("⚠️ Sin datos locales")
        return
    age = get_cache_age_days(competition, season)
    if age is None:
        st.sidebar.info("🗂️ DB local disponible (fecha desconocida)")
    elif age < 1:
        st.sidebar.success("✅ Datos de hoy")
    elif age < 7:
        st.sidebar.success(f"✅ Datos de hace {int(age)} día(s)")
    elif age < 30:
        st.sidebar.warning(f"⚠️ Datos de hace {int(age)} días (considera actualizar)")
    else:
        st.sidebar.error(f"❌ Datos de hace {int(age)} días (muy desactualizados)")

_show_data_freshness(competition, season)
st.sidebar.markdown("---")
run_btn = st.sidebar.button("▶ Generar informe", use_container_width=True)

# ---------------------------------------------------------------------------
# Área principal
# ---------------------------------------------------------------------------

_beta_name = st.session_state.get("beta_user_name", "")
_title_suffix = f" · Bienvenido, {_beta_name}" if _beta_name else ""
st.title(f"⚽ {COMPETITION_NAMES.get(competition, 'Competición')} — {season}{_title_suffix}")

if not run_btn:
    db_exists = _get_db_path(competition, season).exists()
    if not db_exists:
        st.warning(
            f"⚠️ No hay datos locales para **{COMPETITION_NAMES.get(competition, competition)}** "
            f"temporada **{season}**."
        )
        # 9.2 — Botón para descargar datos directamente desde el dashboard
        if st.button("⬇️ Descargar datos ahora", type="primary"):
            import subprocess, sys
            with st.spinner(
                f"Descargando datos de {COMPETITION_NAMES.get(competition, competition)} {season}... "
                "Esto puede tardar 1-3 minutos."
            ):
                result = subprocess.run(
                    [
                        sys.executable, "-m", "src.run_agent",
                        "--fetch-real",
                        "--competition", str(competition),
                        "--season", season,
                        "--no-charts",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=300,
                )
            if result.returncode == 0:
                st.success("✅ Datos descargados correctamente. Pulsa **▶ Generar informe** para continuar.")
                st.cache_data.clear()
            else:
                st.error("❌ Error al descargar los datos.")
                with st.expander("Ver detalles del error"):
                    st.code(result.stderr or result.stdout)
        else:
            st.info(
                "También puedes descargarlos manualmente con:\n"
                f"```\npython -m src.run_agent --fetch-real --competition {competition} --season {season}\n```"
            )
    else:
        st.info(
            "Configura los parámetros en el panel lateral y pulsa **▶ Generar informe**."
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
