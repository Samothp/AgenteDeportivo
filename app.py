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
import threading
from datetime import date, datetime
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from src.constants import COMPETITION_NAMES

load_dotenv()

# Punto 13 — modo debug para usuarios técnicos
_BETA_DEBUG: bool = os.getenv("BETA_DEBUG", "").strip().lower() in ("1", "true", "yes")

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
# Punto 14 — Compatibilidad mobile (CSS responsive)
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
    /* En pantallas ≪768 px, colapsar columnas de datos a una sola */
    @media (max-width: 768px) {
        /* Columnas de métricas y tablas */
        div[data-testid="column"] {
            width: 100% !important;
            flex: 1 1 100% !important;
            min-width: 100% !important;
        }
        /* Imágenes al 100% del viewport */
        img {
            max-width: 100% !important;
            height: auto !important;
        }
        /* Sidebar colapsada por defecto en móvil */
        section[data-testid="stSidebar"] {
            min-width: 0 !important;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Punto 15 — Modo oscuro consistente en gráficos
# ---------------------------------------------------------------------------

def _detect_dark_mode() -> bool:
    """Detecta si el dashboard está en modo oscuro.

    Orden de precedencia:
      1. Variable de entorno STREAMLIT_DARK_MODE (1/true/yes → oscuro).
      2. Fichero .streamlit/config.toml → [theme] base = "dark".
      3. Defecto: modo claro.
    """
    env_val = os.getenv("STREAMLIT_DARK_MODE", "").strip().lower()
    if env_val in ("1", "true", "yes"):
        return True
    if env_val in ("0", "false", "no"):
        return False
    try:
        import tomllib  # Python ≥3.11
    except ImportError:
        try:
            import tomli as tomllib  # type: ignore
        except ImportError:
            tomllib = None  # type: ignore
    if tomllib is not None:
        _cfg = Path(".streamlit/config.toml")
        if _cfg.exists():
            try:
                _data = tomllib.loads(_cfg.read_text(encoding="utf-8"))
                if _data.get("theme", {}).get("base") == "dark":
                    return True
            except Exception:
                pass
    return False


_dark_mode = _detect_dark_mode()
try:
    from src.visualizer import set_chart_theme as _set_chart_theme
    _set_chart_theme(dark=_dark_mode)
except Exception:
    pass

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


def _prefetch_team_assets(team_name: str, competition_id: int) -> None:
    """Lanza en segundo plano la descarga del escudo y metadata del equipo.

    Se ejecuta en un hilo daemon para no bloquear el render del dashboard.
    Si el escudo ya está en caché local, no hace ninguna llamada a la API.
    La clave de sesión evita lanzar múltiples hilos para el mismo equipo.
    """
    if not team_name:
        return
    state_key = f"_prefetch_done_{competition_id}_{team_name}"
    if st.session_state.get(state_key):
        return
    st.session_state[state_key] = True

    def _worker():
        try:
            from src.image_fetcher import get_team_assets
            get_team_assets(team_name, competition_id)
        except Exception:
            pass

    t = threading.Thread(target=_worker, daemon=True)
    t.start()


def _run_agent(competition: int, season: str, mode: str, **kwargs) -> tuple[dict, list[str]]:
    """Ejecuta el agente y devuelve (json_payload, image_paths).

    Usa st.session_state para caché dentro de la sesión.
    La caché se invalida automáticamente al cambiar cualquier parámetro.
    """
    import logging as _logging
    _log = _logging.getLogger("AgenteDeportivo.dashboard")
    _log.debug("_run_agent llamado: competition=%r season=%r mode=%r kwargs=%r", competition, season, mode, kwargs)

    # Caché por sesión — invalida si cambia cualquier parámetro
    import hashlib as _hashlib
    _key_data = f"{competition}|{season}|{mode}|{sorted(kwargs.items())!r}"
    _cache_key = "_run_agent_" + _hashlib.md5(_key_data.encode()).hexdigest()
    if _cache_key in st.session_state:
        return st.session_state[_cache_key]

    from src.agent import SportsAgent
    from src.config import AgentConfig
    from src.data_loader import get_db_path

    db_path = get_db_path(competition, season)
    if not db_path.exists():
        raise FileNotFoundError(
            f"No hay DB local para competition={competition} season={season}. "
            "Descarga los datos primero con --fetch-real desde la CLI."
        )

    # Directorio temporal para los gráficos (se reutiliza entre recargas dentro de la sesión)
    tmp_dir = Path(tempfile.mkdtemp(prefix="agente_deportivo_"))

    agent = SportsAgent(AgentConfig(
        data_path=str(db_path),
        fetch_real=False,
        competition_id=competition,
        season=season,
        no_charts=False,
        **kwargs,
    ))
    agent.load_data()
    agent.analyze()

    json_str = agent.generate_json_report()
    image_paths = agent.save_visual_report(str(tmp_dir))

    result = json.loads(json_str), image_paths
    st.session_state[_cache_key] = result
    return result


# ---------------------------------------------------------------------------
# Sidebar
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
    df = pd.DataFrame(data)
    display_df = df.copy()

    # Normaliza porcentajes (0-1 -> 0-100) y aplica formatos/barra según columnas.
    for col in display_df.columns:
        col_norm = str(col).strip().lower()
        if any(tok in col_norm for tok in ("posesion", "posesión", "%", "porcentaje", "pct")):
            num = pd.to_numeric(display_df[col], errors="coerce")
            if num.notna().any() and float(num.max()) <= 1.0:
                display_df[col] = num * 100

    column_cfg = {}
    for col in display_df.columns:
        col_norm = str(col).strip().lower()
        num = pd.to_numeric(display_df[col], errors="coerce")
        if not num.notna().any():
            continue

        is_percentage = any(tok in col_norm for tok in ("posesion", "posesión", "%", "porcentaje", "pct"))
        use_progress = any(tok in col_norm for tok in ("puntos", "pts", "goles", "gol", "posesion", "posesión"))

        if use_progress:
            min_v = float(num.min())
            max_v = float(num.max())
            if max_v > min_v:
                fmt = "%.1f%%" if is_percentage else "%.1f"
                column_cfg[col] = st.column_config.ProgressColumn(
                    label=str(col),
                    min_value=min(0.0, min_v),
                    max_value=max_v,
                    format=fmt,
                )
                continue

        if is_percentage:
            column_cfg[col] = st.column_config.NumberColumn(label=str(col), format="%.1f%%")

    st.dataframe(display_df, use_container_width=True, column_config=column_cfg)


# ---------------------------------------------------------------------------
# 11 — URL params para compartir informes
# ---------------------------------------------------------------------------

def _init_from_url_params() -> None:
    """Pre-rellena st.session_state con los parámetros de la URL (solo en la primera carga).

    Parámetros soportados:
      comp      → ID de competición (int)
      season    → Temporada (YYYY)
      team      → Nombre de equipo (tabs Equipo y Jugador)
      player    → Nombre de jugador
      matchday  → Número de jornada (int)
      match_id  → ID de partido (int)
      t1, t2    → Equipos para el modo Compare
    """
    if st.session_state.get("_url_params_loaded"):
        return
    st.session_state["_url_params_loaded"] = True
    qp = st.query_params
    if "comp" in qp:
        try:
            st.session_state["sidebar_competition"] = int(qp["comp"])
        except ValueError:
            pass
    if "season" in qp:
        st.session_state["sidebar_season"] = str(qp["season"])
    if "team" in qp:
        st.session_state["equipo_team"] = str(qp["team"])
        st.session_state["jugador_team"] = str(qp["team"])
    if "player" in qp:
        st.session_state["jugador_nombre"] = str(qp["player"])
    if "matchday" in qp:
        try:
            st.session_state["jornada_num"] = int(qp["matchday"])
        except ValueError:
            pass
    if "match_id" in qp:
        try:
            st.session_state["partido_id"] = int(qp["match_id"])
        except ValueError:
            pass
    if "t1" in qp:
        st.session_state["compare_t1"] = str(qp["t1"])
    if "t2" in qp:
        st.session_state["compare_t2"] = str(qp["t2"])


def _update_url_params(mode: str, kw: dict, comp: int, seas: str) -> None:
    """Actualiza st.query_params con el estado del informe recién generado."""
    params: dict[str, str] = {
        "comp": str(comp),
        "season": seas,
        "tab": mode.lower(),
    }
    if "team" in kw:
        params["team"] = str(kw["team"])
    if "player" in kw:
        params["player"] = str(kw["player"])
    if "matchday" in kw:
        params["matchday"] = str(kw["matchday"])
    if "match_id" in kw:
        params["match_id"] = str(kw["match_id"])
    if "compare" in kw:
        t1, t2 = kw["compare"]
        params["t1"] = str(t1)
        params["t2"] = str(t2)
    st.query_params.update(params)


_init_from_url_params()

st.sidebar.title("⚽ Agente Deportivo")
st.sidebar.markdown("---")

# 10.5 — Modo multi-liga
use_multi = st.sidebar.checkbox("🔀 Comparar múltiples ligas", value=False)

if use_multi:
    st.sidebar.markdown("**Selecciona hasta 3 competiciones:**")
    _multi_combos: list[tuple[int, str]] = []
    for _i in range(3):
        _c1, _c2 = st.sidebar.columns([3, 2])
        _mc = _c1.selectbox(
            f"Liga {_i + 1}",
            options=list(COMPETITION_NAMES.keys()),
            format_func=lambda x: COMPETITION_NAMES[x],
            key=f"multi_comp_{_i}",
        )
        _ms = _c2.text_input(f"Temp.", value="2024", key=f"multi_season_{_i}")
        _multi_combos.append((_mc, _ms))
    st.sidebar.markdown("---")
    multi_btn = st.sidebar.button("▶ Comparar ligas", use_container_width=True, type="primary")
else:
    competition = st.sidebar.selectbox(
        "Competición",
        options=list(COMPETITION_NAMES.keys()),
        format_func=lambda x: COMPETITION_NAMES[x],
        key="sidebar_competition",
    )
    season = st.sidebar.text_input("Temporada (YYYY)", value="2024", key="sidebar_season")

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

if not use_multi:
    top_n = st.sidebar.slider("Top N en rankings", min_value=3, max_value=20, value=5)
    st.sidebar.markdown("---")
    _show_data_freshness(competition, season)
    st.sidebar.markdown("---")

# ---------------------------------------------------------------------------
# Área principal
# ---------------------------------------------------------------------------

_beta_name = st.session_state.get("beta_user_name", "")
_title_suffix = f" · Bienvenido, {_beta_name}" if _beta_name else ""

# ---------------------------------------------------------------------------
# 10.5 — Modo multi-liga
# ---------------------------------------------------------------------------
if use_multi:
    st.title(f"⚽ Comparativa de Ligas{_title_suffix}")
    if not multi_btn:
        st.info("Selecciona hasta 3 competiciones en el panel lateral y pulsa **▶ Comparar ligas**.")
        st.stop()

    tabs = st.tabs(
        [f"{COMPETITION_NAMES.get(_mc, _mc)} {_ms}" for _mc, _ms in _multi_combos]
    )
    for _tab, (_mc, _ms) in zip(tabs, _multi_combos):
        with _tab:
            try:
                with st.spinner(f"Analizando {COMPETITION_NAMES.get(_mc, _mc)} {_ms}…"):
                    _ml_payload, _ml_imgs = _run_agent(_mc, _ms, "Liga", top_n=5)
                _ml_liga = _ml_payload.get("liga_summary", {})
                if _ml_liga:
                    _show_table(_ml_liga.get("clasificacion", []), "🏆 Clasificación")
                    _ml_metrics = _ml_payload.get("metrics", {})
                    if _ml_metrics:
                        _col1, _col2, _col3 = st.columns(3)
                        _col1.metric("Goles/partido", _ml_metrics.get("goles_a_favor_promedio"))
                        _col2.metric("xG/partido", _ml_metrics.get("xg_equipo_promedio"))
                        _col3.metric("Posesión %", _ml_metrics.get("posesion_equipo_promedio"))
                else:
                    st.warning("No hay datos de liga disponibles.")
            except FileNotFoundError:
                st.warning(
                    f"Sin datos locales para **{COMPETITION_NAMES.get(_mc, _mc)} {_ms}**. "
                    "Descárgalos primero desde la CLI."
                )
            except Exception as _e:
                st.error(f"Error al cargar {COMPETITION_NAMES.get(_mc, _mc)} {_ms}: {_e}")

    # 12.4 — Radar comparativo con medias de todas las ligas seleccionadas
    st.markdown("---")
    st.subheader("🕸️ Radar comparativo de ligas")
    _radar_data: list[dict] = []
    for _mc, _ms in _multi_combos:
        try:
            _ml_payload2, _ = _run_agent(_mc, _ms, "Liga", top_n=5)
            _ml_metrics2 = _ml_payload2.get("metrics", {})
            if _ml_metrics2:
                _radar_data.append({
                    "label": f"{COMPETITION_NAMES.get(_mc, _mc)} {_ms}",
                    "Goles/partido": _ml_metrics2.get("goles_a_favor_promedio") or 0,
                    "xG/partido": _ml_metrics2.get("xg_equipo_promedio") or 0,
                    "Posesión %": (_ml_metrics2.get("posesion_equipo_promedio") or 0) / 100,
                    "Tiros/partido": _ml_metrics2.get("tiros_equipo_promedio") or 0,
                    "Corners/partido": _ml_metrics2.get("corners_equipo_promedio") or 0,
                })
        except Exception:
            pass
    if len(_radar_data) >= 2:
        import tempfile as _tmp
        from src.visualizer import plot_multi_league_radar as _plot_mlr
        _radar_path = str(Path(_tmp.mkdtemp()) / "multi_radar.png")
        _radar_img = _plot_mlr(_radar_data, _radar_path)
        if _radar_img:
            _rc1, _rc2, _rc3 = st.columns([1, 2, 1])
            _rc2.image(_radar_img, use_container_width=True)
    else:
        st.info("Se necesitan al menos 2 ligas con datos para mostrar el radar comparativo.")

    st.stop()

# ---------------------------------------------------------------------------
# Modo normal — Tabs
# ---------------------------------------------------------------------------
st.title(f"⚽ {COMPETITION_NAMES.get(competition, 'Competición')} — {season}{_title_suffix}")

# 9.2 — Verificar datos locales disponibles
db_exists = _get_db_path(competition, season).exists()
if not db_exists:
    st.warning(
        f"⚠️ No hay datos locales para **{COMPETITION_NAMES.get(competition, competition)}** "
        f"temporada **{season}**."
    )
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
            st.success("✅ Datos descargados correctamente.")
            for _k in list(st.session_state.keys()):
                if _k.startswith("_run_agent_"):
                    del st.session_state[_k]
        else:
            st.error("❌ Error al descargar los datos.")
            with st.expander("Ver detalles del error"):
                st.code(result.stderr or result.stdout)
    else:
        st.info(
            "También puedes descargarlos manualmente con:\n"
            f"```\npython -m src.run_agent --fetch-real --competition {competition} --season {season}\n```"
        )
    st.stop()

# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Helpers de visualización
# ---------------------------------------------------------------------------


def _payload_to_excel(p: dict) -> bytes:
    import io
    import pandas as pd
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        written = 0
        for key, val in p.items():
            if isinstance(val, list) and val and isinstance(val[0], dict):
                pd.DataFrame(val).to_excel(writer, sheet_name=key[:31], index=False)
                written += 1
            elif isinstance(val, dict):
                for subkey, subval in val.items():
                    if isinstance(subval, list) and subval and isinstance(subval[0], dict):
                        sheet = f"{key[:15]}_{subkey[:15]}"[:31]
                        pd.DataFrame(subval).to_excel(writer, sheet_name=sheet, index=False)
                        written += 1
        if written == 0:
            pd.DataFrame([p]).to_excel(writer, sheet_name="datos", index=False)
    return output.getvalue()


# ---------------------------------------------------------------------------
# Cotización de mercado — caché local JSON (RoadmapDashboard #8)
# ---------------------------------------------------------------------------

_MV_PATH = Path("data/market_values.json")


def _load_market_values() -> dict:
    """Lee la caché local de valores de mercado."""
    if _MV_PATH.exists():
        try:
            return json.loads(_MV_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_market_value(player_name: str, value: float, currency: str = "EUR") -> None:
    """Persiste o actualiza el valor de mercado de un jugador."""
    mv = _load_market_values()
    mv[player_name] = {
        "valor":      value,
        "moneda":     currency,
        "fuente":     "manual",
        "actualizado": date.today().isoformat(),
    }
    _MV_PATH.parent.mkdir(parents=True, exist_ok=True)
    _MV_PATH.write_text(json.dumps(mv, ensure_ascii=False, indent=2), encoding="utf-8")


def _display_metrics(payload: dict) -> None:
    metrics = payload.get("metrics", {})
    modo = payload.get("modo", "")
    if not metrics:
        return

    st.subheader("📊 Métricas principales")

    if modo == "liga":
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            _metric_row("Goles/partido (liga)", metrics.get("goles_promedio_por_partido"))
            _metric_row("Total goles", metrics.get("goles_totales"))
        with col2:
            _metric_row("Partidos analizados", metrics.get("partidos_analizados"))
            _metric_row("Tarjetas amarillas", metrics.get("total_tarjetas_amarillas"))
        with col3:
            _metric_row("xG promedio/partido", metrics.get("xg_equipo_promedio"))
            _metric_row("Tiros promedio/partido", metrics.get("tiros_equipo_promedio"))
        with col4:
            _metric_row("Posesión % media", metrics.get("posesion_equipo_promedio"))
            _metric_row("Corners promedio/partido", metrics.get("corners_equipo_promedio"))

    elif modo == "equipo":
        rec = payload.get("team_record", {})
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            _metric_row("Victorias", rec.get("victorias"))
            _metric_row("Empates", rec.get("empates"))
            _metric_row("Derrotas", rec.get("derrotas"))
        with col2:
            _metric_row("Puntos", rec.get("puntos"))
            _metric_row("Goles a favor / partido", metrics.get("goles_a_favor_promedio"))
            _metric_row("Goles encajados / partido", metrics.get("goles_concedidos_promedio"))
        with col3:
            _metric_row("xG propio / partido", metrics.get("xg_equipo_promedio"))
            _metric_row("Tiros / partido", metrics.get("tiros_equipo_promedio"))
        with col4:
            _metric_row("Posesión % media", metrics.get("posesion_equipo_promedio"))
            _metric_row("Overperformance xG", metrics.get("overperformance"))

    elif modo == "jugador":
        pp = payload.get("player_profile", {})
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            _metric_row("Partidos jugados", pp.get("appearances"))
            _metric_row("Min. estimados", pp.get("minutos_estimados"))
        with col2:
            _metric_row("Goles", pp.get("goals"))
            _metric_row("Asistencias", pp.get("assists"))
        with col3:
            _metric_row("Goles / 90 min \u2217", pp.get("goles_90"))
            _metric_row("Asistencias / 90 min \u2217", pp.get("asist_90") or pp.get("asistencias_90"))
        with col4:
            _metric_row("G+A / 90 min \u2217", pp.get("ga_90"))
            _metric_row("Tiros a puerta / 90 \u2217", pp.get("sot_90"))

    elif modo in ("jornada", "partido", "compare"):
        # Para estos modos mostramos métricas generales del contexto cargado
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

    else:
        # Fallback genérico
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


def _display_mode_results(payload: dict) -> None:
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
            _show_table(pct)
        _show_table(payload.get("top_scorers", []), "⚽ Top goleadores")
        _show_table(payload.get("highlights", []), "🔥 Partidos destacados")
    elif modo == "jornada":
        ms = payload.get("matchday_summary", {})
        if ms:
            st.subheader(f"⚽ Jornada {ms.get('jornada', '?')}")
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
            _player_thumb = pp.get("thumb_local") or pp.get("cutout_local")
            _player_cols = st.columns([1, 4]) if _player_thumb and Path(_player_thumb).exists() else [None]
            if len(_player_cols) == 2:
                with _player_cols[0]:
                    st.image(_player_thumb, use_container_width=True)
                with _player_cols[1]:
                    st.subheader(f"👤 {pp.get('player_name', '')}")
                    _bio_parts = []
                    if pp.get("nationality"): _bio_parts.append(pp["nationality"])
                    if pp.get("position_full"): _bio_parts.append(pp["position_full"])
                    if pp.get("age"): _bio_parts.append(f"{pp['age']} años")
                    if pp.get("height_cm"): _bio_parts.append(f"{pp['height_cm']} cm")
                    if pp.get("weight_kg"): _bio_parts.append(f"{pp['weight_kg']} kg")
                    if pp.get("jersey"): _bio_parts.append(f"Dorsal #{pp['jersey']}")
                    if _bio_parts:
                        st.caption(" · ".join(_bio_parts))
            else:
                st.subheader(f"👤 {pp.get('player_name', '')}")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Partidos jugados", pp.get("appearances"))
            col2.metric("Goles", pp.get("goals"))
            col3.metric("Asistencias", pp.get("assists"))
            col4.metric("G+A", pp.get("ga"))
            # Bloque per-90
            if pp.get("minutos_estimados", 0) > 0:
                st.markdown("---")
                st.caption("\u2217 Stats per-90 min (estimadas asumiendo 90 min por partido completo)")
                p1, p2, p3, p4 = st.columns(4)
                p1.metric("Goles / 90", pp.get("goles_90"))
                p2.metric("Asistencias / 90", pp.get("asistencias_90"))
                p3.metric("G+A / 90", pp.get("ga_90"))
                p4.metric("Tiros a puerta / 90", pp.get("sot_90"))
            # Cotización de mercado
            st.markdown("---")
            _player_key = pp.get("player_name", "")
            _mv_all = _load_market_values()
            _mv = _mv_all.get(_player_key, {})
            if _mv:
                _currency = _mv.get("moneda", "EUR")
                _valor_num = _mv.get("valor", 0)
                _valor_fmt = f"€ {_valor_num:,.0f}" if _currency == "EUR" else f"{_valor_num:,.0f} {_currency}"
                st.metric("💰 Valor de mercado", _valor_fmt)
                st.caption(
                    f"Fuente: {_mv.get('fuente', 'manual')} · "
                    f"Actualizado: {_mv.get('actualizado', '-')}"
                )
            else:
                st.info("Sin valor de mercado registrado para este jugador.")
            with st.expander("✏️ Establecer / actualizar valor de mercado"):
                _new_val = st.number_input(
                    "Valor de mercado (€)",
                    min_value=0,
                    step=100_000,
                    value=int(_mv.get("valor", 0)),
                    key=f"mv_input_{_player_key}",
                )
                if st.button("💾 Guardar valor", key=f"mv_save_{_player_key}"):
                    if _new_val > 0:
                        _save_market_value(_player_key, float(_new_val), "EUR")
                        st.success(f"Valor de **{_player_key}** actualizado a **€ {_new_val:,.0f}**")
                        st.rerun()
                    else:
                        st.warning("Introduce un valor mayor que 0.")
    elif modo == "compare":
        c = payload.get("compare_data", {})
        if c:
            st.subheader(f"⚔️ {c.get('team1', '')} vs {c.get('team2', '')}")
            _show_table(c.get("h2h", []), "🤝 Enfrentamientos directos (H2H)")
            _show_table(c.get("stats_team1", []), f"📊 Stats {c.get('team1', 'Equipo 1')}")
            _show_table(c.get("stats_team2", []), f"📊 Stats {c.get('team2', 'Equipo 2')}")


def _display_charts(image_paths: list) -> None:
    if not image_paths:
        return
    st.markdown("---")
    st.subheader("📈 Gráficos")
    cols_per_row = 2
    for i in range(0, len(image_paths), cols_per_row):
        row_paths = image_paths[i: i + cols_per_row]
        cols = st.columns(len(row_paths))
        for col, img_path in zip(cols, row_paths):
            if Path(img_path).exists():
                col.image(img_path, use_container_width=True)


def _display_export(payload: dict, kw: dict, mode: str) -> None:
    st.markdown("---")
    _btn_pdf, _btn_excel = st.columns(2)
    if _btn_pdf.button("📄 Generar PDF del informe", use_container_width=True, key=f"pdf_{mode}"):
        with st.spinner("Generando PDF… (puede tardar unos segundos)"):
            try:
                _pdf_dir = Path(tempfile.mkdtemp(prefix="agente_pdf_"))
                _pdf_path = _pdf_dir / "informe.pdf"
                from src.agent import SportsAgent
                from src.config import AgentConfig
                from src.data_loader import get_db_path as _get_db
                _pdf_agent = SportsAgent(AgentConfig(
                    data_path=str(_get_db(competition, season)),
                    fetch_real=False,
                    competition_id=competition,
                    season=season,
                    no_charts=True,
                    **kw,
                ))
                _pdf_agent.load_data()
                _pdf_agent.analyze()
                _pdf_agent.generate_pdf_report(str(_pdf_path))
                st.download_button(
                    label="⬇️ Descargar PDF",
                    data=_pdf_path.read_bytes(),
                    file_name=f"informe_{competition}_{season}.pdf",
                    mime="application/pdf",
                    key=f"dl_pdf_{mode}",
                )
            except ImportError:
                st.warning(
                    "**weasyprint** no está instalado.\n\n"
                    "Instálalo con: `pip install weasyprint`\n\n"
                    "En Linux puede requerir además: `apt-get install libpango-1.0-0`"
                )
            except Exception as _e:
                st.error(f"Error al generar el PDF: {_e}")
    with _btn_excel:
        try:
            _xl_bytes = _payload_to_excel(payload)
            st.download_button(
                label="📊 Descargar Excel",
                data=_xl_bytes,
                file_name=f"informe_{competition}_{season}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                key=f"dl_excel_{mode}",
            )
        except Exception as _e:
            st.error(f"Error al generar el Excel: {_e}")
    if _BETA_DEBUG:
        with st.expander("🗂️ Datos en bruto (JSON)"):
            st.json(payload)


def _tab_run_and_display(mode: str, extra_kw: dict) -> None:
    """Ejecuta el agente para `mode` y renderiza todos los resultados."""
    import hashlib as _hashlib
    kw = {**extra_kw, "top_n": top_n}
    _key_data = f"{competition}|{season}|{mode}|{sorted(kw.items())!r}"
    _cache_key = "_run_agent_" + _hashlib.md5(_key_data.encode()).hexdigest()
    has_cache = _cache_key in st.session_state

    # ── Punto 2: badge de informe desactualizado ─────────────────────────────
    # Guardamos la key del último informe GENERADO (al pulsar el botón).
    # Si la key actual difiere de la guardada → los parámetros cambiaron.
    _last_key_name = f"_last_generated_key_{mode}"
    _last_generated = st.session_state.get(_last_key_name)
    _params_changed = has_cache and _last_generated is not None and _last_generated != _cache_key

    if _params_changed:
        st.warning(
            "⚠️ Los parámetros han cambiado desde el último informe generado. "
            "Pulsa **▶ Actualizar informe** para refrescar los resultados.",
            icon="⚠️",
        )

    btn_label = "🔄 Actualizar informe" if has_cache else "▶ Generar informe"
    run_clicked = st.button(btn_label, key=f"run_{mode}", type="primary", use_container_width=True)

    if not run_clicked and not has_cache:
        st.info("Configura los parámetros y pulsa **▶ Generar informe**.")
        return

    try:
        if run_clicked:
            with st.spinner("Analizando datos..."):
                payload, image_paths = _run_agent(competition, season, mode, **kw)
            # Guardar la key del informe recién generado
            st.session_state[_last_key_name] = _cache_key
            # Punto 11 — actualizar URL params para compartir el informe
            _update_url_params(mode, extra_kw, competition, season)
            # Punto 12 — guardar timestamp del informe generado
            st.session_state[f"_ts_{_cache_key}"] = datetime.now()
        else:
            payload, image_paths = _run_agent(competition, season, mode, **kw)
    except FileNotFoundError as e:
        st.error(str(e))
        return
    except Exception as e:
        import traceback as _tb
        _full_tb = _tb.format_exc()
        _logger.error("Error en _run_agent:\n%s", _full_tb)
        st.error(f"Error al generar el informe: {e}")
        with st.expander("🔍 Traceback completo (para diagnóstico)"):
            st.code(_full_tb)
        return
    _display_metrics(payload)
    # Punto 12 — timestamp del informe
    _ts = st.session_state.get(f"_ts_{_cache_key}")
    if _ts:
        st.caption(f"🕒 Datos analizados el {_ts.strftime('%d/%m/%Y a las %H:%M:%S')}")
    st.markdown("---")

    # Punto 6 — Gráfico de evolución de puntos al inicio del modo Equipo
    # Punto 9 — Radar comparativo al inicio del modo Compare
    _remaining_charts = list(image_paths)
    if payload.get("modo") == "equipo":
        _evo = [p for p in image_paths if "temporal_evolution" in Path(p).name]
        _remaining_charts = [p for p in image_paths if "temporal_evolution" not in Path(p).name]
        if _evo:
            st.subheader("📈 Evolución por jornada")
            st.image(_evo[0], use_container_width=True)
            st.markdown("---")

    elif payload.get("modo") == "compare":
        _radar = [p for p in image_paths if "compare_radar" in Path(p).name]
        _remaining_charts = [p for p in image_paths if "compare_radar" not in Path(p).name]
        if _radar:
            _c = payload.get("compare_data", {})
            _t1 = _c.get("team1", "Equipo 1") if _c else "Equipo 1"
            _t2 = _c.get("team2", "Equipo 2") if _c else "Equipo 2"
            st.subheader(f"📊 Radar comparativo — {_t1} vs {_t2}")
            _rc1, _rc2, _rc3 = st.columns([1, 2, 1])
            _rc2.image(_radar[0], use_container_width=True)
            st.markdown("---")

    _display_mode_results(payload)
    _display_charts(_remaining_charts)
    _display_export(payload, kw, mode)


# ---------------------------------------------------------------------------
# Tabs de modos
# ---------------------------------------------------------------------------
_teams = _list_teams(competition, season)
tab_liga, tab_equipo, tab_jornada, tab_partido, tab_jugador, tab_compare = st.tabs(MODES)

with tab_liga:
    _liga_kw: dict = {}
    use_range = st.checkbox("Filtrar rango de jornadas", key="liga_range")
    if use_range:
        col1, col2 = st.columns(2)
        start = col1.number_input("Desde jornada", min_value=1, max_value=38, value=1, step=1, key="liga_start")
        end = col2.number_input("Hasta jornada", min_value=1, max_value=38, value=19, step=1, key="liga_end")
        _liga_kw["matchday_range"] = (int(start), int(end))
    _tab_run_and_display("Liga", _liga_kw)

with tab_equipo:
    if _teams:
        _eq_team = st.selectbox("Equipo", _teams, key="equipo_team")
    else:
        _eq_team = st.text_input("Equipo (nombre parcial)", key="equipo_team_text")
    _prefetch_team_assets(_eq_team, competition)
    try:
        from src.image_fetcher import get_cached_team_meta as _get_meta
        _tm = _get_meta(_eq_team, competition)
        _badge = _tm.get("badge_local")
        if _badge and Path(_badge).exists():
            _badge_col, _ = st.columns([1, 8])
            _badge_col.image(_badge, width=80)
    except Exception:
        pass
    _tab_run_and_display("Equipo", {"team": _eq_team})

with tab_jornada:
    _jornada = st.number_input("Número de jornada", min_value=1, max_value=38, value=1, step=1, key="jornada_num")
    _tab_run_and_display("Jornada", {"matchday": int(_jornada)})

with tab_partido:
    _match_id = st.number_input("ID del partido (id_event)", min_value=1, value=1, step=1, key="partido_id")
    _tab_run_and_display("Partido", {"match_id": int(_match_id)})

with tab_jugador:
    if _teams:
        _jug_team = st.selectbox("Equipo", _teams, key="jugador_team")
    else:
        _jug_team = st.text_input("Equipo (nombre parcial)", key="jugador_team_text")
    _prefetch_team_assets(_jug_team, competition)
    _jug_player = st.text_input("Jugador (nombre parcial)", key="jugador_nombre")
    try:
        from src.image_fetcher import get_cached_team_meta as _get_meta2
        _tm2 = _get_meta2(_jug_team, competition)
        _badge2 = _tm2.get("badge_local")
        if _badge2 and Path(_badge2).exists():
            _badge_col2, _ = st.columns([1, 8])
            _badge_col2.image(_badge2, width=80)
    except Exception:
        pass
    _tab_run_and_display("Jugador", {"team": _jug_team, "player": _jug_player})

with tab_compare:
    if _teams:
        _cmp_t1 = st.selectbox("Equipo 1", _teams, index=0, key="compare_t1")
        _cmp_t2 = st.selectbox("Equipo 2", _teams, index=min(1, len(_teams) - 1), key="compare_t2")
    else:
        _cmp_t1 = st.text_input("Equipo 1", key="compare_t1_text")
        _cmp_t2 = st.text_input("Equipo 2", key="compare_t2_text")
    _prefetch_team_assets(_cmp_t1, competition)
    _prefetch_team_assets(_cmp_t2, competition)
    try:
        from src.image_fetcher import get_cached_team_meta as _get_meta3
        _bcol1, _bcol2 = st.columns(2)
        _b1 = _get_meta3(_cmp_t1, competition).get("badge_local")
        _b2 = _get_meta3(_cmp_t2, competition).get("badge_local")
        if _b1 and Path(_b1).exists():
            _bcol1.image(_b1, width=80)
        if _b2 and Path(_b2).exists():
            _bcol2.image(_b2, width=80)
    except Exception:
        pass
    _tab_run_and_display("Compare", {"compare": (_cmp_t1, _cmp_t2)})
