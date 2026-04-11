"""Bot de Telegram — Agente Deportivo.

Requisitos:
1. Crea un bot con @BotFather en Telegram y obtén el token.
2. Añade el token al archivo .env:
       TELEGRAM_BOT_TOKEN=tu_token_aqui
3. (Opcional) Restringe el acceso a miembros de un grupo específico:
       ALLOWED_GROUP_ID=-1001234567890
   El bot debe ser miembro (o admin) de ese grupo para verificar la membresía.
   Obtén el ID reenviando un mensaje al bot @userinfobot o enviando /getid.
   Si ALLOWED_GROUP_ID no está definido, el bot es público.
4. Asegúrate de tener la DB local descargada para las competiciones que quieras usar.
5. Arranca el bot con:
       python bot.py

Comandos disponibles en el chat:
    /start              — Bienvenida y ayuda
    /ayuda [comando]    — Ayuda general o sintaxis detallada de un comando
    /competiciones      — Lista de IDs de competición disponibles
    /equipos <comp> <temporada>
                        — Equipos disponibles en la DB local
    /liga <comp> <temporada>
                        — Informe completo de la liga
    /equipo <comp> <temporada> <nombre>
                        — Informe de un equipo concreto
    /jornada <comp> <temporada> <N>
                        — Informe de una jornada
    /compare <comp> <temporada> <equipo1> | <equipo2>
                        — Comparativa entre dos equipos

Ejemplos:
    /liga 2014 2024
    /equipo 2014 2024 Mallorca
    /jornada 2014 2024 15
    /compare 2014 2024 Real Madrid | Barcelona
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import sys
import tempfile
import textwrap
from pathlib import Path

from dotenv import load_dotenv

from src.constants import COMPETITION_NAMES
from src.thresholds import CONSECUTIVE_LOSSES_ALERT

load_dotenv()

# ---------------------------------------------------------------------------
# Comprobación de dependencias
# ---------------------------------------------------------------------------

try:
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
    from telegram.constants import ChatAction
    from telegram.ext import (
        Application,
        CallbackQueryHandler,
        CommandHandler,
        ContextTypes,
    )
except ImportError:
    print(
        "ERROR: 'python-telegram-bot' no está instalado.\n"
        "Instálalo con:  pip install 'python-telegram-bot>=20.0'\n"
    )
    sys.exit(1)

# ---------------------------------------------------------------------------
# Configuración de logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    format="%(asctime)s — %(name)s — %(levelname)s — %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("AgenteDeportivo.bot")

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

MAX_MSG_LENGTH = 4000  # Telegram permite hasta 4096 caracteres por mensaje

# Event loop del hilo principal, capturado en post_init para que APScheduler
# pueda enviar corrutinas desde hilos secundarios sin crear un nuevo loop.
_main_loop: asyncio.AbstractEventLoop | None = None

# 10.2 — Archivos de persistencia de suscripciones y estado de alertas
SUBSCRIPTIONS_FILE = Path("data/subscriptions.json")
ALERT_STATE_FILE = Path("data/alert_state.json")
FIRST_USE_FILE = Path("data/first_use.json")  # RoadmapBotTelegram #14
USAGE_LOG_FILE = Path("data/usage_log.jsonl")  # RoadmapBotTelegram #16

# Punto 17 — Si está definida, todos los handlers (excepto /start) responden con este mensaje
BOT_MAINTENANCE_MSG: str = os.getenv("BOT_MAINTENANCE_MSG", "").strip()

# Temporada actual calculada una sola vez al arrancar el bot.
# Julio–diciembre → año actual; enero–junio → año anterior.
def _current_season() -> str:
    from datetime import date
    today = date.today()
    return str(today.year if today.month >= 7 else today.year - 1)

_SEASON_EXAMPLE: str = _current_season()
_SEASON_NEXT: str = str(int(_SEASON_EXAMPLE) + 1)
_SEASON_LABEL: str = f"{_SEASON_EXAMPLE[-2:]}/{_SEASON_NEXT[-2:]}"  # ej. "24/25"

# ---------------------------------------------------------------------------
# Control de acceso por membresía a grupo
# ---------------------------------------------------------------------------

# ID numérico del grupo (negativo: ej. -1001234567890). None = bot público.
_RAW_GROUP_ID = os.getenv("ALLOWED_GROUP_ID", "").strip()
ALLOWED_GROUP_ID: int | None = int(_RAW_GROUP_ID) if _RAW_GROUP_ID else None

# Estados de Telegram que se consideran "miembro activo"
_MEMBER_STATUSES = {"creator", "administrator", "member", "restricted"}


async def _is_group_member(user_id: int, bot) -> bool:
    """Devuelve True si el usuario pertenece al grupo ALLOWED_GROUP_ID."""
    if ALLOWED_GROUP_ID is None:
        return True  # Sin restricción configurada
    try:
        member = await bot.get_chat_member(chat_id=ALLOWED_GROUP_ID, user_id=user_id)
        return member.status in _MEMBER_STATUSES
    except Exception:
        # Si el bot no está en el grupo o la API falla, denegamos por seguridad
        return False


def _require_group_member(handler):
    """Decorador que deniega el handler si el usuario no es miembro del grupo."""
    import functools

    @functools.wraps(handler)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if ALLOWED_GROUP_ID is None:
            return await handler(update, context)
        user = update.effective_user
        if user is None:
            return
        allowed = await _is_group_member(user.id, context.bot)
        if not allowed:
            await update.message.reply_text(
                "⛔ No tienes acceso a este bot.\n"
                "Debes ser miembro del grupo autorizado para usarlo."
            )
            logger.warning(
                "Acceso denegado a user_id=%s username=%s",
                user.id, user.username
            )
            return
        return await handler(update, context)

    return wrapper


def _cooldown(seconds: int):
    """Decorador de rate limiting por usuario. Rechaza el comando si el mismo usuario
    lo volvió a llamar antes de que hayan transcurrido `seconds` segundos."""
    import functools
    import time

    def decorator(handler):
        @functools.wraps(handler)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
            user = update.effective_user
            if user is None:
                return await handler(update, context)
            cd_key = f"_cd_{handler.__name__}"
            last_ts: float = context.user_data.get(cd_key, 0.0)
            elapsed = time.monotonic() - last_ts
            if elapsed < seconds:
                remaining = int(seconds - elapsed) + 1
                await update.message.reply_text(
                    f"⏳ Comando en cooldown. Vuelve a intentarlo en {remaining} segundos."
                )
                return
            context.user_data[cd_key] = time.monotonic()
            return await handler(update, context)

        return wrapper

    return decorator


# ---------------------------------------------------------------------------
# RoadmapBotTelegram #17 — Modo mantenimiento
# ---------------------------------------------------------------------------

def _require_not_maintenance(handler):
    """Decorador que bloquea el handler si BOT_MAINTENANCE_MSG está definido."""
    import functools

    @functools.wraps(handler)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if BOT_MAINTENANCE_MSG:
            await update.message.reply_text(f"🔧 {BOT_MAINTENANCE_MSG}")
            return
        return await handler(update, context)

    return wrapper


# ---------------------------------------------------------------------------
# RoadmapBotTelegram #16 — Logging de uso
# ---------------------------------------------------------------------------

def _log_usage(user_id: int | None, command: str, **kwargs) -> None:
    """Registra el uso de un comando en JSONL (user_id hasheado, sin PII)."""
    import datetime

    uid_hash = (
        hashlib.sha256(str(user_id).encode()).hexdigest()[:12]
        if user_id is not None
        else "anon"
    )
    entry = {
        "ts": datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "cmd": command,
        "uid": uid_hash,
    }
    entry.update({k: v for k, v in kwargs.items() if v is not None})
    try:
        USAGE_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with USAGE_LOG_FILE.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as exc:
        logger.debug("_log_usage error: %s", exc)


# ---------------------------------------------------------------------------
# Helpers del agente
# ---------------------------------------------------------------------------


def _is_first_use(user_id: int) -> bool:
    """Devuelve True si el usuario nunca ha ejecutado /start antes."""
    try:
        if not FIRST_USE_FILE.exists():
            return True
        seen: list = json.loads(FIRST_USE_FILE.read_text(encoding="utf-8"))
        return user_id not in seen
    except Exception:
        return True


def _mark_first_use(user_id: int) -> None:
    """Registra que el usuario ya ha visto la bienvenida."""
    try:
        seen: list = []
        if FIRST_USE_FILE.exists():
            seen = json.loads(FIRST_USE_FILE.read_text(encoding="utf-8"))
        if user_id not in seen:
            seen.append(user_id)
            FIRST_USE_FILE.parent.mkdir(parents=True, exist_ok=True)
            FIRST_USE_FILE.write_text(json.dumps(seen), encoding="utf-8")
    except Exception:
        pass


def _load_subscriptions() -> dict:
    """Carga suscripciones desde disco. Devuelve {} si no existe o está corrupto."""
    if not SUBSCRIPTIONS_FILE.exists():
        return {}
    try:
        return json.loads(SUBSCRIPTIONS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_subscriptions(subs: dict) -> None:
    """Persiste las suscripciones en disco."""
    SUBSCRIPTIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    SUBSCRIPTIONS_FILE.write_text(json.dumps(subs, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_alert_state() -> dict:
    if not ALERT_STATE_FILE.exists():
        return {}
    try:
        return json.loads(ALERT_STATE_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_alert_state(state: dict) -> None:
    ALERT_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    ALERT_STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _run_agent_text(competition: int, season: str, **kwargs) -> str:
    """Crea un agente, lo ejecuta y devuelve el informe de texto."""
    from src.agent import SportsAgent
    from src.config import AgentConfig
    from src.data_loader import get_db_path

    db_path = get_db_path(competition, season)
    if not db_path.exists():
        return (
            f"⚠️ No hay DB local para competition={competition} season={season}.\n\n"
            f"Descarga los datos primero con:\n"
            f"`python -m src.run_agent --fetch-real --competition {competition} --season {season}`"
        )

    try:
        agent = SportsAgent(AgentConfig(
            data_path=str(db_path),
            fetch_real=False,
            competition_id=competition,
            season=season,
            no_charts=True,
            **kwargs,
        ))
        agent.load_data()
        agent.analyze()
        return agent.generate_report()
    except ValueError as exc:
        logger.warning("Error de datos al ejecutar agente: %s", exc)
        return f"⚠️ Error en los datos: {exc}"
    except Exception as exc:
        logger.error("Error inesperado al ejecutar agente: %s", exc, exc_info=True)
        return "❌ Error inesperado al generar el informe. Revisa los logs del servidor."


def _run_agent_with_charts(competition: int, season: str, tmp_dir: str, **kwargs) -> tuple[str, list[str]]:
    """Crea un agente con gráficos, devuelve (texto_informe, [ruta_png, ...])."""
    from src.agent import SportsAgent
    from src.config import AgentConfig
    from src.data_loader import get_db_path

    db_path = get_db_path(competition, season)
    if not db_path.exists():
        return (
            f"⚠️ No hay DB local para competition={competition} season={season}.",
            [],
        )
    try:
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
        text = agent.generate_report()
        image_paths = agent.save_visual_report(output_folder=tmp_dir)
        return text, image_paths
    except Exception as exc:
        logger.error("Error al generar gráficos: %s", exc, exc_info=True)
        return "❌ Error inesperado al generar el informe. Revisa los logs del servidor.", []


def _split_message(text: str, max_len: int = MAX_MSG_LENGTH) -> list[str]:
    """Divide un texto largo en fragmentos que Telegram puede enviar."""
    return textwrap.wrap(text, width=max_len, break_long_words=False, replace_whitespace=False)


class _TypingAction:
    """Context manager asíncrono que mantiene el indicador 'escribiendo…' de Telegram
    mientras se ejecuta un bloque costoso en un hilo separado.

    Uso:
        async with _TypingAction(update, context):
            resultado = await asyncio.to_thread(tarea_lenta)
    """

    def __init__(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE", interval: float = 4.0):
        self._update = update
        self._context = context
        self._interval = interval
        self._task: asyncio.Task | None = None

    async def _loop(self) -> None:
        chat_id = self._update.effective_chat.id
        while True:
            try:
                await self._context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
            except Exception:
                pass
            await asyncio.sleep(self._interval)

    async def __aenter__(self):
        self._task = asyncio.get_running_loop().create_task(self._loop())
        return self

    async def __aexit__(self, *_):
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass


async def _send_report_with_charts(update: Update, text: str, image_paths: list[str]) -> None:
    """Envía el informe paginado y luego las imágenes disponibles como fotos."""
    await _send_paged(update, text)
    for path in image_paths:
        try:
            with open(path, "rb") as f:
                await update.message.reply_photo(photo=f)
        except Exception as exc:
            logger.warning("No se pudo enviar la imagen %s: %s", path, exc)


# ---------------------------------------------------------------------------
# RoadmapBotTelegram #12 — Caché de informes por sesión
# ---------------------------------------------------------------------------

_REPORT_CACHE_TTL = 600  # 10 minutos
_report_cache: dict[str, tuple[float, str]] = {}  # key → (timestamp_monotonic, text)


def _report_cache_key(competition: int, season: str, **kwargs) -> str:
    """Genera una clave única para una solicitud de informe."""
    parts = f"{competition}:{season}:" + ":".join(f"{k}={v}" for k, v in sorted(kwargs.items()))
    return hashlib.md5(parts.encode()).hexdigest()[:16]


def _report_cache_get(key: str) -> str | None:
    """Devuelve el texto cacheado si existe y no ha expirado, o None."""
    import time
    entry = _report_cache.get(key)
    if entry is None:
        return None
    ts, text = entry
    if time.monotonic() - ts > _REPORT_CACHE_TTL:
        del _report_cache[key]
        return None
    return text


def _report_cache_set(key: str, text: str) -> None:
    """Almacena el texto en la caché con timestamp actual."""
    import time
    _report_cache[key] = (time.monotonic(), text)
    # Limpieza oportunista: eliminar entradas expiradas
    now = time.monotonic()
    expired = [k for k, (ts, _) in _report_cache.items() if now - ts > _REPORT_CACHE_TTL]
    for k in expired:
        del _report_cache[k]


# ---------------------------------------------------------------------------
# 12.2 — Paginación con inline keyboards
# ---------------------------------------------------------------------------

# Caché de paginación: persiste en disco con TTL de 1 hora para que los botones
# ◀/▶ sigan funcionando tras reinicios del bot.
PAGE_CACHE_FILE = Path("data/page_cache.json")
_PAGE_CACHE_TTL = 3600  # segundos


def _pc_load() -> dict[str, list[str]]:
    """Carga el caché de paginación desde disco, descartando entradas expiradas."""
    import time
    if not PAGE_CACHE_FILE.exists():
        return {}
    try:
        raw: dict = json.loads(PAGE_CACHE_FILE.read_text(encoding="utf-8"))
        now = time.time()
        return {k: v["pages"] for k, v in raw.items() if now - v.get("ts", 0) < _PAGE_CACHE_TTL}
    except Exception:
        return {}


def _pc_save(cache: dict[str, list[str]]) -> None:
    """Persiste el caché en disco añadiendo timestamp a cada entrada."""
    import time
    try:
        PAGE_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        raw = {k: {"pages": pages, "ts": time.time()} for k, pages in cache.items()}
        PAGE_CACHE_FILE.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


_page_cache: dict[str, list[str]] = _pc_load()


def _cache_pages(text: str) -> str:
    """Almacena las páginas en el caché (memoria + disco) y devuelve la clave."""
    key = hashlib.md5(text.encode()).hexdigest()[:12]
    _page_cache[key] = _split_message(text)
    _pc_save(_page_cache)
    return key


def _page_keyboard(key: str, current: int, total: int) -> InlineKeyboardMarkup:
    """Genera el teclado inline de navegación por páginas."""
    buttons: list[InlineKeyboardButton] = []
    if current > 0:
        buttons.append(InlineKeyboardButton("◀ Anterior", callback_data=f"page:{key}:{current - 1}"))
    buttons.append(InlineKeyboardButton(f"{current + 1}/{total}", callback_data="noop"))
    if current < total - 1:
        buttons.append(InlineKeyboardButton("Siguiente ▶", callback_data=f"page:{key}:{current + 1}"))
    return InlineKeyboardMarkup([buttons])


async def _send_paged(update: Update, text: str) -> None:
    """Envía texto largo con paginación inline; si cabe en un mensaje, lo envía directamente."""
    pages = _split_message(text)
    if len(pages) == 1:
        await update.message.reply_text(f"```\n{pages[0]}\n```", parse_mode="Markdown")
        return
    key = _cache_pages(text)
    await update.message.reply_text(
        f"```\n{pages[0]}\n```",
        parse_mode="Markdown",
        reply_markup=_page_keyboard(key, 0, len(pages)),
    )


@_require_group_member
async def callback_page(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler del callback de botones de paginación."""
    query = update.callback_query
    await query.answer()
    data = query.data or ""
    if data == "noop":
        return
    parts = data.split(":")
    if len(parts) != 3 or parts[0] != "page":
        return
    key, raw_page = parts[1], parts[2]
    try:
        page_num = int(raw_page)
    except ValueError:
        return
    pages = _page_cache.get(key)
    if not pages:
        await query.edit_message_text("⚠️ La sesión de paginación expiró. Vuelve a ejecutar el comando.")
        return
    page_num = max(0, min(page_num, len(pages) - 1))
    await query.edit_message_text(
        f"```\n{pages[page_num]}\n```",
        parse_mode="Markdown",
        reply_markup=_page_keyboard(key, page_num, len(pages)),
    )


def _parse_base(args: tuple[str, ...]) -> tuple[int, str] | str:
    """Parsea competition y season de los argumentos del comando."""
    if len(args) < 2:
        return f"\u274c Faltan parámetros. Ejemplo: `/liga 2014 {_SEASON_EXAMPLE}`"
    try:
        competition = int(args[0])
    except ValueError:
        return f"❌ El ID de competición debe ser un número entero (ej. `2014`)."
    season = args[1]
    return competition, season

# ---------------------------------------------------------------------------
# Handlers de comandos
# ---------------------------------------------------------------------------


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Bienvenida e instrucciones. Primer uso muestra guía extendida."""
    user = update.effective_user
    name = user.first_name if user else "usuario"
    first = _is_first_use(user.id) if user else False
    if user:
        _mark_first_use(user.id)

    text = (
        f"⚽ ¡Hola, {name}\\! Bienvenido a *Agente Deportivo*\n"
        "Bot de análisis avanzado de fútbol\\.\n\n"
        "📊 *Análisis e informes*\n"
        "/competiciones — Lista de IDs de competición\n"
        "/equipos `<comp> <temp>` — Equipos disponibles\n"
        "/temporadas `<comp>` — Temporadas descargadas\n"
        "/tabla `<comp> <temp>` — Clasificación rápida\n"
        "/ultima `<comp> <temp> <equipo>` — Últimos 5 resultados\n"
        "/liga `<comp> <temp>` — Informe completo de liga\n"
        "/equipo `<comp> <temp> <nombre>` — Informe de equipo\n"
        "/jugador `<comp> <temp> <equipo> <nombre>` — Informe de jugador\n"
        "/jornada `<comp> <temp> <N>` — Informe de jornada\n"
        "/compare `<comp> <temp> <eq1> | <eq2>` — Comparativa\n"
        "/pdf `<comp> <temp>` — Descargar informe en PDF\n\n"
        "🔔 *Alertas proactivas*\n"
        "/suscribir `<comp> <temp> <equipo>` — Activar alerta de rachas\n"
        "/suscripciones — Ver tus alertas activas\n"
        "/desuscribir `<comp> <temp> <equipo>` — Cancelar alerta\n\n"
        "📖 *Ayuda*\n"
        "/ayuda — Ayuda general\n"
        "/ayuda `<comando>` — Sintaxis detallada \\(ej\\. `/ayuda liga`\\)\n\n"
        "💡 *Ejemplos rápidos*\n"
        f"`/liga 2014 {_SEASON_EXAMPLE}`\n"
        f"`/equipo 2014 {_SEASON_EXAMPLE} Mallorca`\n"
        f"`/jornada 2014 {_SEASON_EXAMPLE} 15`\n"
        f"`/compare 2014 {_SEASON_EXAMPLE} Real Madrid | Barcelona`"
    )
    await update.message.reply_text(text, parse_mode="MarkdownV2")

    if first:
        # Guía de primeros pasos solo en el primer /start
        guia = (
            "🚀 *Primeros pasos*\n\n"
            "1️⃣ Consulta las competiciones disponibles:\n"
            "   `/competiciones`\n\n"
            "2️⃣ Mira qué temporadas tienes descargadas:\n"
            f"   `/temporadas 2014`\n\n"
            "3️⃣ Obtén la clasificación rápida:\n"
            f"   `/tabla 2014 {_SEASON_EXAMPLE}`\n\n"
            "4️⃣ Genera un informe completo de equipo:\n"
            f"   `/equipo 2014 {_SEASON_EXAMPLE} Mallorca`\n\n"
            "5️⃣ Activa alertas de racha negativa:\n"
            f"   `/suscribir 2014 {_SEASON_EXAMPLE} Mallorca`\n\n"
            "Usa `/ayuda <comando>` para ver la sintaxis completa de cualquier comando\\."
        )
        access_note = ""
        if ALLOWED_GROUP_ID:
            access_note = (
                f"\n\n🔒 *Control de acceso activo*\n"
                f"Solo miembros del grupo autorizado pueden usar este bot\\."
            )
        await update.message.reply_text(guia + access_note, parse_mode="MarkdownV2")


@_require_not_maintenance
@_require_group_member
async def cmd_competiciones(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Lista las competiciones disponibles."""
    lines = ["📋 *Competiciones disponibles:*\n"]
    for cid, name in COMPETITION_NAMES.items():
        lines.append(f"  `{cid}` — {name}")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


@_require_not_maintenance
@_require_group_member
async def cmd_equipos(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/equipos <competition> <season>"""
    result = _parse_base(context.args)
    if isinstance(result, str):
        await update.message.reply_text(result, parse_mode="Markdown")
        return
    competition, season = result

    from src.data_loader import list_available_teams
    teams = list_available_teams(competition, season)
    if not teams:
        await update.message.reply_text(
            f"⚠️ No hay DB local para competition={competition} season={season}.",
            parse_mode="Markdown",
        )
        return

    comp_name = COMPETITION_NAMES.get(competition, str(competition))
    lines = [f"🏆 *{comp_name} {season}* — Equipos disponibles:\n"]
    lines += [f"  • {t}" for t in teams]
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


@_require_not_maintenance
@_require_group_member
@_cooldown(30)
async def cmd_liga(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/liga <competition> <season>"""
    result = _parse_base(context.args)
    if isinstance(result, str):
        await update.message.reply_text(result, parse_mode="Markdown")
        return
    competition, season = result

    _log_usage(update.effective_user.id if update.effective_user else None, "liga", comp=competition, season=season)
    await update.message.reply_text("⏳ Generando informe de liga...")
    solo_texto = "--texto" in (context.args or [])
    _ck = _report_cache_key(competition, season)
    cached = _report_cache_get(_ck)
    if cached:
        await update.message.reply_text("💾 (informe cacheado)")
        await _send_paged(update, cached)
    elif solo_texto:
        async with _TypingAction(update, context):
            text = await asyncio.to_thread(_run_agent_text, competition, season)
        _report_cache_set(_ck, text)
        await _send_paged(update, text)
    else:
        async with _TypingAction(update, context):
            with tempfile.TemporaryDirectory(prefix="agente_liga_") as tmp:
                text, images = await asyncio.to_thread(_run_agent_with_charts, competition, season, tmp)
        _report_cache_set(_ck, text)
        await _send_report_with_charts(update, text, images)


@_require_not_maintenance
@_require_group_member
@_cooldown(30)
async def cmd_equipo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/equipo <competition> <season> <nombre_equipo>"""
    result = _parse_base(context.args)
    if isinstance(result, str):
        await update.message.reply_text(result, parse_mode="Markdown")
        return
    competition, season = result

    if len(context.args) < 3:
        await update.message.reply_text(
            f"\u274c Falta el nombre del equipo. Ejemplo: `/equipo 2014 {_SEASON_EXAMPLE} Mallorca`",
            parse_mode="Markdown",
        )
        return
    team_args = [a for a in context.args[2:] if a != "--texto"]
    team = " ".join(team_args)

    await update.message.reply_text(f"⏳ Generando informe de {team}...")
    _log_usage(update.effective_user.id if update.effective_user else None, "equipo", comp=competition, season=season, team=team)
    solo_texto = "--texto" in (context.args or [])
    _ck = _report_cache_key(competition, season, team=team)
    cached = _report_cache_get(_ck)
    if cached:
        await update.message.reply_text("💾 (informe cacheado)")
        await _send_paged(update, cached)
    elif solo_texto:
        async with _TypingAction(update, context):
            text = await asyncio.to_thread(_run_agent_text, competition, season, team=team)
        _report_cache_set(_ck, text)
        await _send_paged(update, text)
    else:
        async with _TypingAction(update, context):
            with tempfile.TemporaryDirectory(prefix="agente_equipo_") as tmp:
                text, images = await asyncio.to_thread(_run_agent_with_charts, competition, season, tmp, team=team)
        _report_cache_set(_ck, text)
        await _send_report_with_charts(update, text, images)


@_require_not_maintenance
@_require_group_member
@_cooldown(30)
async def cmd_jornada(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/jornada <competition> <season> <N>"""
    result = _parse_base(context.args)
    if isinstance(result, str):
        await update.message.reply_text(result, parse_mode="Markdown")
        return
    competition, season = result

    if len(context.args) < 3:
        await update.message.reply_text(
            f"\u274c Falta el número de jornada. Ejemplo: `/jornada 2014 {_SEASON_EXAMPLE} 15`",
            parse_mode="Markdown",
        )
        return
    try:
        jornada = int(context.args[2])
    except ValueError:
        await update.message.reply_text("❌ El número de jornada debe ser un entero.")
        return

    await update.message.reply_text(f"⏳ Generando informe de la jornada {jornada}...")
    _log_usage(update.effective_user.id if update.effective_user else None, "jornada", comp=competition, season=season, matchday=jornada)
    async with _TypingAction(update, context):
        text = await asyncio.to_thread(_run_agent_text, competition, season, matchday=jornada)
    await _send_paged(update, text)


@_require_not_maintenance
@_require_group_member
@_cooldown(30)
async def cmd_compare(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/compare <competition> <season> <equipo1> | <equipo2>"""
    result = _parse_base(context.args)
    if isinstance(result, str):
        await update.message.reply_text(result, parse_mode="Markdown")
        return
    competition, season = result

    # El resto de los args forman "Equipo1 | Equipo2"
    rest = " ".join(context.args[2:])
    if "|" not in rest:
        await update.message.reply_text(
            f"\u274c Separa los dos equipos con `|`. Ejemplo:\n"
            f"`/compare 2014 {_SEASON_EXAMPLE} Real Madrid | Barcelona`",
            parse_mode="Markdown",
        )
        return
    parts = rest.split("|", 1)
    team1 = parts[0].strip()
    team2 = parts[1].strip()
    if not team1 or not team2:
        await update.message.reply_text("❌ Los nombres de ambos equipos no pueden estar vacíos.")
        return

    await update.message.reply_text(f"⏳ Comparando {team1} vs {team2}...")
    _log_usage(update.effective_user.id if update.effective_user else None, "compare", comp=competition, season=season)
    solo_texto = "--texto" in (context.args or [])
    _ck = _report_cache_key(competition, season, compare=f"{team1}|{team2}")
    cached = _report_cache_get(_ck)
    if cached:
        await update.message.reply_text("💾 (informe cacheado)")
        await _send_paged(update, cached)
    elif solo_texto:
        async with _TypingAction(update, context):
            text = await asyncio.to_thread(_run_agent_text, competition, season, compare=(team1, team2))
        _report_cache_set(_ck, text)
        await _send_paged(update, text)
    else:
        async with _TypingAction(update, context):
            with tempfile.TemporaryDirectory(prefix="agente_compare_") as tmp:
                text, images = await asyncio.to_thread(_run_agent_with_charts, competition, season, tmp, compare=(team1, team2))
        _report_cache_set(_ck, text)
        await _send_report_with_charts(update, text, images)


# ---------------------------------------------------------------------------
# RoadmapBotTelegram #7 — /jugador
# ---------------------------------------------------------------------------

@_require_not_maintenance
@_require_group_member
@_cooldown(30)
async def cmd_jugador(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/jugador <comp> <temp> <equipo> <nombre> — Informe de jugador."""
    result = _parse_base(context.args)
    if isinstance(result, str):
        await update.message.reply_text(result, parse_mode="Markdown")
        return
    competition, season = result

    if len(context.args) < 4:
        await update.message.reply_text(
            f"❌ Uso: `/jugador <comp> <temp> <equipo> <nombre>`\n"
            f"Ejemplo: `/jugador 2014 {_SEASON_EXAMPLE} Mallorca Muriqi`",
            parse_mode="Markdown",
        )
        return

    # El tercer argumento es el equipo, el resto el nombre del jugador.
    # No hay separador explícito, así que el bot toma args[2] como equipo y args[3:] como nombre.
    team = context.args[2]
    player = " ".join(context.args[3:])

    _log_usage(update.effective_user.id if update.effective_user else None, "jugador", comp=competition, season=season, team=team)
    await update.message.reply_text(f"⏳ Buscando informe de {player} ({team})...")
    async with _TypingAction(update, context):
        text = await asyncio.to_thread(_run_agent_text, competition, season, team=team, player=player)
    await _send_paged(update, text)


# ---------------------------------------------------------------------------
# RoadmapBotTelegram #8 — /tabla
# ---------------------------------------------------------------------------

@_require_not_maintenance
@_require_group_member
@_cooldown(15)
async def cmd_tabla(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/tabla <comp> <temp> — Clasificación rápida sin análisis completo."""
    result = _parse_base(context.args)
    if isinstance(result, str):
        await update.message.reply_text(result, parse_mode="Markdown")
        return
    competition, season = result

    _log_usage(update.effective_user.id if update.effective_user else None, "tabla", comp=competition, season=season)

    from src.data_loader import get_db_path, load_match_data
    from src.analysis import compute_liga_summary

    db_path = get_db_path(competition, season)
    if not db_path.exists():
        await update.message.reply_text(
            f"⚠️ No hay DB local para competition={competition} season={season}."
        )
        return

    try:
        df = load_match_data(str(db_path), fetch_real=False, competition_id=competition, season=season)
        summary = compute_liga_summary(df)
        tabla = summary.get("clasificacion", [])
        if not tabla:
            await update.message.reply_text("⚠️ No se pudo obtener la clasificación.")
            return

        comp_name = COMPETITION_NAMES.get(competition, str(competition))
        lines = [f"🏆 *{comp_name} {season}* — Clasificación\n"]
        for row in tabla:
            pos = row.get("pos", row.get("Pos", "?"))
            team = row.get("Equipo", row.get("equipo", "?"))
            pts = row.get("Pts", row.get("pts", "?"))
            gf = row.get("GF", row.get("gf", "?"))
            ga = row.get("GC", row.get("gc", row.get("ga", "?")))
            forma = row.get("Forma", "")
            forma_str = f"  {forma}" if forma else ""
            lines.append(f"`{str(pos).rjust(2)}.` {team} — *{pts}* pts  ({gf}:{ga}){forma_str}")
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    except Exception as exc:
        logger.error("Error en /tabla: %s", exc, exc_info=True)
        await update.message.reply_text("❌ Error al obtener la clasificación.")


# ---------------------------------------------------------------------------
# RoadmapBotTelegram #9 — /ultima
# ---------------------------------------------------------------------------

@_require_not_maintenance
@_require_group_member
async def cmd_ultima(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/ultima <comp> <temp> <equipo> — Últimos 5 resultados del equipo."""
    result = _parse_base(context.args)
    if isinstance(result, str):
        await update.message.reply_text(result, parse_mode="Markdown")
        return
    competition, season = result

    if len(context.args) < 3:
        await update.message.reply_text(
            f"❌ Uso: `/ultima <comp> <temp> <equipo>`\n"
            f"Ejemplo: `/ultima 2014 {_SEASON_EXAMPLE} Mallorca`",
            parse_mode="Markdown",
        )
        return
    team = " ".join(context.args[2:])

    from src.data_loader import get_db_path, load_match_data
    from src.analysis import compute_team_form

    db_path = get_db_path(competition, season)
    if not db_path.exists():
        await update.message.reply_text(
            f"⚠️ No hay DB local para competition={competition} season={season}."
        )
        return

    try:
        df = load_match_data(str(db_path), fetch_real=False, competition_id=competition, season=season)
        forma = compute_team_form(df, team, last_n=5)
        if not forma:
            await update.message.reply_text(f"⚠️ No se encontraron partidos para *{team}*.", parse_mode="Markdown")
            return
        comp_name = COMPETITION_NAMES.get(competition, str(competition))
        text = (
            f"📊 *{team}* — Últimos resultados\n"
            f"({comp_name} {season})\n\n"
            f"{forma}\n\n"
            f"🟢 Victoria · ⚪ Empate · 🔴 Derrota"
        )
        await update.message.reply_text(text, parse_mode="Markdown")
    except Exception as exc:
        logger.error("Error en /ultima: %s", exc, exc_info=True)
        await update.message.reply_text("❌ Error al obtener los resultados.")


# ---------------------------------------------------------------------------
# RoadmapBotTelegram #10 — /temporadas
# ---------------------------------------------------------------------------

@_require_not_maintenance
@_require_group_member
async def cmd_temporadas(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/temporadas <comp> — Lista las temporadas disponibles localmente."""
    if not context.args:
        await update.message.reply_text(
            "❌ Indica el ID de competición. Ejemplo: `/temporadas 2014`",
            parse_mode="Markdown",
        )
        return
    try:
        competition = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ El ID de competición debe ser un número entero.")
        return

    import re as _re
    pattern = _re.compile(rf"^db_{competition}_(\d+)\.csv$")
    seasons = sorted(
        m.group(1) for f in Path("data").iterdir()
        if (m := pattern.match(f.name))
    )
    if not seasons:
        comp_name = COMPETITION_NAMES.get(competition, str(competition))
        await update.message.reply_text(
            f"⚠️ No hay datos locales para *{comp_name}* (ID `{competition}`).\n"
            f"Descarga los datos con:\n"
            f"`python -m src.run_agent --fetch-real --competition {competition} --season <año>`",
            parse_mode="Markdown",
        )
        return

    comp_name = COMPETITION_NAMES.get(competition, str(competition))
    lines = [f"📅 *{comp_name}* — Temporadas disponibles localmente:\n"]
    for s in seasons:
        nxt = str(int(s) + 1)
        lines.append(f"  `{s}` ({s[2:]}/{nxt[2:]})")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


# ---------------------------------------------------------------------------
# RoadmapBotTelegram #15 — /goleadores y /partido
# ---------------------------------------------------------------------------

@_require_not_maintenance
@_require_group_member
@_cooldown(15)
async def cmd_goleadores(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/goleadores <comp> <temp> [N] — Top goleadores de la temporada."""
    result = _parse_base(context.args)
    if isinstance(result, str):
        await update.message.reply_text(result, parse_mode="Markdown")
        return
    competition, season = result

    top_n = 10
    if len(context.args) >= 3:
        try:
            top_n = max(1, min(int(context.args[2]), 25))
        except ValueError:
            pass

    _log_usage(
        update.effective_user.id if update.effective_user else None,
        "goleadores",
        comp=competition,
        season=season,
    )

    from src.player_loader import load_players

    try:
        df = load_players(competition_id=competition, season=season)
        if df is None or df.empty:
            await update.message.reply_text(
                f"⚠️ No hay datos de jugadores para competition={competition} season={season}."
            )
            return

        if "goals" not in df.columns:
            await update.message.reply_text("⚠️ Los datos de jugadores no contienen información de goles.")
            return

        top = (
            df[df["goals"] > 0]
            .sort_values("goals", ascending=False)
            .head(top_n)
            .reset_index(drop=True)
        )

        if top.empty:
            await update.message.reply_text("⚠️ No se encontraron goleadores en esta temporada.")
            return

        comp_name = COMPETITION_NAMES.get(competition, str(competition))
        lines = [f"⚽ *{comp_name} {season}* — Top {len(top)} Goleadores\n"]

        medals = ["🥇", "🥈", "🥉"]
        for i, row in top.iterrows():
            prefix = medals[i] if i < 3 else f"`{i + 1:>2}.`"
            name = row.get("player_name", row.get("name", "?"))
            team = row.get("team", row.get("squad", ""))
            team_str = f" *{team}*" if team else ""
            goals = int(row["goals"])
            assists = int(row.get("assists", 0))
            goals_str = f"{goals} ⚽"
            if assists:
                goals_str += f"  {assists} 🎯"
            lines.append(f"{prefix} {name}{team_str} — {goals_str}")

        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    except Exception as exc:
        logger.error("Error en /goleadores: %s", exc, exc_info=True)
        await update.message.reply_text("❌ Error al obtener los goleadores.")


@_require_not_maintenance
@_require_group_member
@_cooldown(30)
async def cmd_partido(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/partido <comp> <temp> <match_id> — Ficha completa de un partido por su ID."""
    result = _parse_base(context.args)
    if isinstance(result, str):
        await update.message.reply_text(result, parse_mode="Markdown")
        return
    competition, season = result

    if len(context.args) < 3:
        await update.message.reply_text(
            "❌ Indica el ID del partido. Ejemplo:\n"
            f"`/partido 2014 {_SEASON_EXAMPLE} 2279399`",
            parse_mode="Markdown",
        )
        return

    try:
        match_id = int(context.args[2])
    except ValueError:
        await update.message.reply_text("❌ El ID de partido debe ser un número entero.")
        return

    _log_usage(
        update.effective_user.id if update.effective_user else None,
        "partido",
        comp=competition,
        season=season,
        match_id=match_id,
    )

    await update.message.reply_text(f"⏳ Generando ficha del partido {match_id}...")

    async with _TypingAction(update, context):
        text = await asyncio.to_thread(
            _run_agent_text, competition, season, match_id=match_id
        )
    await _send_paged(update, text)


# 9.3 — /ayuda contextual
_AYUDA_GENERAL = (
    "⚽ *Agente Deportivo* — Ayuda\n\n"
    "Usa `/ayuda <comando>` para ver la sintaxis detallada de cada comando:\n\n"
    "  `/ayuda liga`\n"
    "  `/ayuda equipo`\n"
    "  `/ayuda jugador`\n"
    "  `/ayuda tabla`\n"
    "  `/ayuda ultima`\n"
    "  `/ayuda jornada`\n"
    "  `/ayuda compare`\n"
    "  `/ayuda temporadas`\n"
    "  `/ayuda equipos`\n"
    "  `/ayuda competiciones`"
)

_AYUDA_CMDS: dict[str, str] = {
    "liga": (
        "📋 *Comando:* `/liga`\n\n"
        "*Sintaxis:*\n"
        "`/liga <competition\\_id> <temporada>`\n\n"
        "*Parámetros:*\n"
        "  • `competition_id` — ID numérico de la competición (usa `/competiciones` para verlos)\n"
        f"  • `temporada` — Año de inicio de la temporada (ej. `{_SEASON_EXAMPLE}`)\n\n"
        "*Ejemplos:*\n"
        f"`/liga 2014 {_SEASON_EXAMPLE}` — La Liga {_SEASON_LABEL}\n"
        f"`/liga 2021 {_SEASON_EXAMPLE}` — Premier League {_SEASON_LABEL}\n"
        f"`/liga 2002 {str(int(_SEASON_EXAMPLE)-1)}` — Bundesliga {str(int(_SEASON_EXAMPLE)-1)[-2:]}/{_SEASON_EXAMPLE[-2:]}"
    ),
    "equipo": (
        "📋 *Comando:* `/equipo`\n\n"
        "*Sintaxis:*\n"
        "`/equipo <competition\\_id> <temporada> <nombre\\_equipo>`\n\n"
        "*Parámetros:*\n"
        "  • `competition_id` — ID numérico de la competición\n"
        "  • `temporada` — Año de inicio de la temporada\n"
        "  • `nombre_equipo` — Nombre o parte del nombre (no distingue mayúsculas)\n\n"
        "*Ejemplos:*\n"
        f"`/equipo 2014 {_SEASON_EXAMPLE} Mallorca`\n"
        f"`/equipo 2014 {_SEASON_EXAMPLE} Real Madrid`\n"
        f"`/equipo 2021 {_SEASON_EXAMPLE} Arsenal`"
    ),
    "jornada": (
        "📋 *Comando:* `/jornada`\n\n"
        "*Sintaxis:*\n"
        "`/jornada <competition\\_id> <temporada> <número>`\n\n"
        "*Parámetros:*\n"
        "  • `competition_id` — ID numérico de la competición\n"
        "  • `temporada` — Año de inicio de la temporada\n"
        "  • `número` — Número de jornada (entero positivo)\n\n"
        "*Ejemplos:*\n"
        f"`/jornada 2014 {_SEASON_EXAMPLE} 15` — Jornada 15 de La Liga {_SEASON_LABEL}\n"
        f"`/jornada 2021 {str(int(_SEASON_EXAMPLE)-1)} 1` — Primera jornada Premier {str(int(_SEASON_EXAMPLE)-1)[-2:]}/{_SEASON_EXAMPLE[-2:]}"
    ),
    "compare": (
        "📋 *Comando:* `/compare`\n\n"
        "*Sintaxis:*\n"
        "`/compare <competition\\_id> <temporada> <equipo1> | <equipo2>`\n\n"
        "*Parámetros:*\n"
        "  • `competition_id` — ID numérico de la competición\n"
        "  • `temporada` — Año de inicio de la temporada\n"
        "  • `equipo1` y `equipo2` — Separados por `|`\n\n"
        "*Ejemplos:*\n"
        f"`/compare 2014 {_SEASON_EXAMPLE} Real Madrid | Barcelona`\n"
        f"`/compare 2021 {_SEASON_EXAMPLE} Arsenal | Chelsea`"
    ),
    "equipos": (
        "📋 *Comando:* `/equipos`\n\n"
        "*Sintaxis:*\n"
        "`/equipos <competition\\_id> <temporada>`\n\n"
        "*Parámetros:*\n"
        "  • `competition_id` — ID numérico de la competición\n"
        "  • `temporada` — Año de inicio de la temporada\n\n"
        "*Ejemplos:*\n"
        f"`/equipos 2014 {_SEASON_EXAMPLE}` — Todos los equipos de La Liga {_SEASON_LABEL}\n"
        f"`/equipos 2001 {_SEASON_EXAMPLE}` — Equipos de Champions League {_SEASON_LABEL}"
    ),
    "competiciones": (
        "📋 *Comando:* `/competiciones`\n\n"
        "*Sintaxis:*\n"
        "`/competiciones`\n\n"
        "Lista todos los IDs de competición disponibles junto con sus nombres.\n"
        "Sin parámetros adicionales.\n\n"
        "*Ejemplo:*\n"
        "`/competiciones`"
    ),
    "jugador": (
        "📋 *Comando:* `/jugador`\n\n"
        "*Sintaxis:*\n"
        "`/jugador <competition\\_id> <temporada> <equipo> <nombre>`\n\n"
        "*Parámetros:*\n"
        "  • `competition_id` — ID numérico de la competición\n"
        "  • `temporada` — Año de inicio de la temporada\n"
        "  • `equipo` — Nombre del equipo (una sola palabra)\n"
        "  • `nombre` — Nombre del jugador (puede tener espacios)\n\n"
        "*Ejemplos:*\n"
        f"`/jugador 2014 {_SEASON_EXAMPLE} Mallorca Muriqi`\n"
        f"`/jugador 2021 {_SEASON_EXAMPLE} Arsenal Saka`"
    ),
    "tabla": (
        "📋 *Comando:* `/tabla`\n\n"
        "*Sintaxis:*\n"
        "`/tabla <competition\\_id> <temporada>`\n\n"
        "Muestra la clasificación en texto formateado sin ejecutar el análisis completo.\n\n"
        "*Ejemplos:*\n"
        f"`/tabla 2014 {_SEASON_EXAMPLE}` — Clasificación de La Liga {_SEASON_LABEL}\n"
        f"`/tabla 2021 {_SEASON_EXAMPLE}` — Clasificación de Premier League {_SEASON_LABEL}"
    ),
    "ultima": (
        "📋 *Comando:* `/ultima`\n\n"
        "*Sintaxis:*\n"
        "`/ultima <competition\\_id> <temporada> <equipo>`\n\n"
        "Muestra los últimos 5 resultados del equipo con emojis.\n\n"
        "*Ejemplos:*\n"
        f"`/ultima 2014 {_SEASON_EXAMPLE} Mallorca`\n"
        f"`/ultima 2021 {_SEASON_EXAMPLE} Arsenal`"
    ),
    "temporadas": (
        "📋 *Comando:* `/temporadas`\n\n"
        "*Sintaxis:*\n"
        "`/temporadas <competition\\_id>`\n\n"
        "Lista las temporadas disponibles localmente para una competición.\n\n"
        "*Ejemplos:*\n"
        "`/temporadas 2014` — Temporadas descargadas de La Liga\n"
        "`/temporadas 2021` — Temporadas descargadas de Premier League"
    ),
}


@_require_not_maintenance
@_require_group_member
async def cmd_ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/ayuda [comando] — Ayuda general o específica de un comando."""
    if not context.args:
        await update.message.reply_text(_AYUDA_GENERAL, parse_mode="Markdown")
        return

    cmd = context.args[0].lower().lstrip("/")
    texto = _AYUDA_CMDS.get(cmd)
    if texto:
        await update.message.reply_text(texto, parse_mode="Markdown")
    else:
        disponibles = ", ".join(f"`{k}`" for k in _AYUDA_CMDS)
        await update.message.reply_text(
            f"❓ Comando `{cmd}` no reconocido.\n\n"
            f"Comandos con ayuda disponible: {disponibles}",
            parse_mode="Markdown",
        )


# ---------------------------------------------------------------------------
# 10.1 — Exportar informe a PDF
# ---------------------------------------------------------------------------


@_require_not_maintenance
@_require_group_member
@_cooldown(30)
async def cmd_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/pdf <competition> <season> — Genera y envía un PDF del informe de liga."""
    result = _parse_base(context.args)
    if isinstance(result, str):
        await update.message.reply_text(result, parse_mode="Markdown")
        return
    competition, season = result

    await update.message.reply_text("⏳ Generando PDF… puede tardar unos segundos.")
    try:
        from weasyprint import HTML as WeasyprintHTML  # type: ignore  # noqa: F401
    except ImportError:
        await update.message.reply_text(
            "❌ `weasyprint` no está instalado en el servidor.\n"
            "Instálalo con: `pip install weasyprint`",
            parse_mode="Markdown",
        )
        return

    try:
        from src.agent import SportsAgent
        from src.config import AgentConfig
        from src.data_loader import get_db_path

        db_path = get_db_path(competition, season)
        if not db_path.exists():
            await update.message.reply_text(
                f"⚠️ No hay DB local para competition={competition} season={season}."
            )
            return

        with tempfile.TemporaryDirectory(prefix="agente_pdf_") as tmp:
            tmp_path = Path(tmp)
            agent = SportsAgent(AgentConfig(
                data_path=str(db_path),
                fetch_real=False,
                competition_id=competition,
                season=season,
                no_charts=True,
            ))
            agent.load_data()
            agent.analyze()
            pdf_path = str(tmp_path / "informe.pdf")
            agent.generate_pdf_report(pdf_path)
            comp_name = COMPETITION_NAMES.get(competition, str(competition))
            await update.message.reply_document(
                document=open(pdf_path, "rb"),
                filename=f"informe_{competition}_{season}.pdf",
                caption=f"📄 Informe PDF — {comp_name} {season}",
            )
    except Exception as exc:
        logger.error("Error generando PDF: %s", exc, exc_info=True)
        await update.message.reply_text(f"❌ Error al generar el PDF: {exc}")


# ---------------------------------------------------------------------------
# 10.2 — Alertas proactivas: suscripciones
# ---------------------------------------------------------------------------


@_require_not_maintenance
@_require_group_member
async def cmd_suscribir(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/suscribir <competition> <season> <equipo> — Suscríbete a alertas de un equipo."""
    result = _parse_base(context.args)
    if isinstance(result, str):
        await update.message.reply_text(result, parse_mode="Markdown")
        return
    competition, season = result

    if len(context.args) < 3:
        await update.message.reply_text(
            "❌ Falta el nombre del equipo.\n"
            "Ejemplo: `/suscribir 2014 2024 Mallorca`",
            parse_mode="Markdown",
        )
        return
    team = " ".join(context.args[2:])
    chat_id = str(update.effective_chat.id)

    subs = _load_subscriptions()
    user_subs: list = subs.setdefault(chat_id, [])
    entry = {"competition": competition, "season": season, "team": team}
    if entry in user_subs:
        await update.message.reply_text(f"ℹ️ Ya estás suscrito a alertas de *{team}*.", parse_mode="Markdown")
        return
    user_subs.append(entry)
    _save_subscriptions(subs)
    comp_name = COMPETITION_NAMES.get(competition, str(competition))
    await update.message.reply_text(
        f"✅ Suscrito a alertas de *{team}* en {comp_name} {season}.\n\n"
        "Recibirás una notificación si el equipo encadena 3 o más derrotas consecutivas.",
        parse_mode="Markdown",
    )


@_require_not_maintenance
@_require_group_member
async def cmd_suscripciones(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/suscripciones — Lista tus suscripciones de alertas activas."""
    chat_id = str(update.effective_chat.id)
    subs = _load_subscriptions()
    user_subs = subs.get(chat_id, [])
    if not user_subs:
        await update.message.reply_text("ℹ️ No tienes ninguna suscripción activa.")
        return
    lines = ["📋 *Tus suscripciones activas:*\n"]
    for i, s in enumerate(user_subs, 1):
        comp_name = COMPETITION_NAMES.get(s["competition"], str(s["competition"]))
        lines.append(f"  {i}. {s['team']} — {comp_name} {s['season']}")
    lines.append("\nUsa `/desuscribir <comp> <temp> <equipo>` para eliminar una suscripción.")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


@_require_not_maintenance
@_require_group_member
async def cmd_desuscribir(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/desuscribir <competition> <season> <equipo> — Cancela una suscripción de alertas."""
    result = _parse_base(context.args)
    if isinstance(result, str):
        await update.message.reply_text(result, parse_mode="Markdown")
        return
    competition, season = result

    if len(context.args) < 3:
        await update.message.reply_text(
            "❌ Falta el nombre del equipo.\n"
            "Ejemplo: `/desuscribir 2014 2024 Mallorca`",
            parse_mode="Markdown",
        )
        return
    team = " ".join(context.args[2:])
    chat_id = str(update.effective_chat.id)

    subs = _load_subscriptions()
    user_subs: list = subs.get(chat_id, [])
    entry = {"competition": competition, "season": season, "team": team}
    if entry not in user_subs:
        await update.message.reply_text(
            f"ℹ️ No tienes ninguna suscripción para *{team}*.", parse_mode="Markdown"
        )
        return
    user_subs.remove(entry)
    subs[chat_id] = user_subs
    _save_subscriptions(subs)
    await update.message.reply_text(
        f"✅ Suscripción a *{team}* cancelada.", parse_mode="Markdown"
    )


def _check_alerts_sync(bot_token: str) -> None:
    """Comprueba todas las suscripciones y envía alertas si un equipo lleva ≥3 derrotas seguidas."""
    from telegram import Bot

    subs = _load_subscriptions()
    if not subs:
        return

    state = _load_alert_state()
    new_state: dict = {}

    async def _send(chat_id: str, msg: str) -> None:
        bot = Bot(token=bot_token)
        await bot.send_message(chat_id=int(chat_id), text=msg, parse_mode="Markdown")

    for chat_id, user_subs in subs.items():
        for entry in user_subs:
            comp = entry["competition"]
            season = entry["season"]
            team = entry["team"]
            key = f"{chat_id}:{comp}:{season}:{team}"

            try:
                from src.agent import SportsAgent
                from src.config import AgentConfig
                from src.data_loader import get_db_path

                db_path = get_db_path(comp, season)
                if not db_path.exists():
                    continue

                agent = SportsAgent(AgentConfig(
                    data_path=str(db_path),
                    fetch_real=False,
                    competition_id=comp,
                    season=season,
                    no_charts=True,
                    team=team,
                ))
                agent.load_data()
                agent.analyze()

                record = agent.get_team_record() if hasattr(agent, "get_team_record") else None
                if record is None:
                    import json as _json
                    payload = _json.loads(agent.generate_json_report())
                    record = payload.get("team_record", {})

                racha: str = record.get("racha_actual", "")
                # Cuenta derrotas consecutivas al inicio de la racha (ej. "DDDVV" → 3)
                consecutive_losses = 0
                for char in racha:
                    if char.upper() == "D":
                        consecutive_losses += 1
                    else:
                        break

                new_state[key] = consecutive_losses

                if consecutive_losses >= CONSECUTIVE_LOSSES_ALERT and state.get(key, 0) < CONSECUTIVE_LOSSES_ALERT:
                    comp_name = COMPETITION_NAMES.get(comp, str(comp))
                    msg = (
                        f"⚠️ *Alerta de racha negativa*\n\n"
                        f"*{team}* lleva *{consecutive_losses} derrotas consecutivas* "
                        f"en {comp_name} {season}.\n\n"
                        f"Racha reciente: `{racha}`"
                    )
                    if _main_loop is not None and _main_loop.is_running():
                        future = asyncio.run_coroutine_threadsafe(_send(chat_id, msg), _main_loop)
                        future.result(timeout=30)
                    else:
                        asyncio.run(_send(chat_id, msg))
                    logger.info("Alerta enviada a %s: %s lleva %d derrotas", chat_id, team, consecutive_losses)
            except Exception as exc:
                logger.warning("Error comprobando alertas para %s/%s/%s: %s", comp, season, team, exc)

    _save_alert_state(new_state)


# ---------------------------------------------------------------------------
# Error handler global
# ---------------------------------------------------------------------------


async def _error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Captura cualquier excepción no tratada en los handlers y avisa al usuario."""
    logger.error("Excepción no controlada en el bot", exc_info=context.error)
    if isinstance(update, Update) and update.message:
        await update.message.reply_text(
            "❌ Se produjo un error inesperado. Por favor, inténtalo de nuevo más tarde."
        )


# ---------------------------------------------------------------------------
# Punto de entrada
# ---------------------------------------------------------------------------


def main() -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print(
            "ERROR: Variable de entorno TELEGRAM_BOT_TOKEN no definida.\n"
            "Añádela al archivo .env:\n"
            "    TELEGRAM_BOT_TOKEN=tu_token_aqui\n"
            "Obtén un token gratis con @BotFather en Telegram."
        )
        sys.exit(1)

    async def _post_init(app: Application) -> None:  # noqa: F811
        """Captura el event loop del hilo principal para uso desde APScheduler."""
        global _main_loop
        _main_loop = asyncio.get_running_loop()

    application = Application.builder().token(token).post_init(_post_init).build()

    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("ayuda", cmd_ayuda))
    application.add_handler(CommandHandler("competiciones", cmd_competiciones))
    application.add_handler(CommandHandler("equipos", cmd_equipos))
    application.add_handler(CommandHandler("liga", cmd_liga))
    application.add_handler(CommandHandler("equipo", cmd_equipo))
    application.add_handler(CommandHandler("jornada", cmd_jornada))
    application.add_handler(CommandHandler("compare", cmd_compare))

    # 10.1 — PDF
    application.add_handler(CommandHandler("pdf", cmd_pdf))

    # 10.2 — Alertas proactivas
    application.add_handler(CommandHandler("suscribir", cmd_suscribir))
    application.add_handler(CommandHandler("suscripciones", cmd_suscripciones))
    application.add_handler(CommandHandler("desuscribir", cmd_desuscribir))

    # 10.4 — Aliases en inglés
    application.add_handler(CommandHandler("help", cmd_ayuda))
    application.add_handler(CommandHandler("competitions", cmd_competiciones))
    application.add_handler(CommandHandler("teams", cmd_equipos))
    application.add_handler(CommandHandler("league", cmd_liga))
    application.add_handler(CommandHandler("team", cmd_equipo))
    application.add_handler(CommandHandler("matchday", cmd_jornada))

    # RoadmapBotTelegram #7-10 — Nuevos comandos
    application.add_handler(CommandHandler("jugador", cmd_jugador))
    application.add_handler(CommandHandler("tabla", cmd_tabla))
    application.add_handler(CommandHandler("ultima", cmd_ultima))
    application.add_handler(CommandHandler("temporadas", cmd_temporadas))

    # RoadmapBotTelegram #15 — Aliases adicionales + /goleadores + /partido
    application.add_handler(CommandHandler("clasificacion", cmd_tabla))
    application.add_handler(CommandHandler("goleadores", cmd_goleadores))
    application.add_handler(CommandHandler("partido", cmd_partido))

    # 12.2 — Paginación inline
    application.add_handler(CallbackQueryHandler(callback_page, pattern=r"^(page:|noop)"))

    application.add_error_handler(_error_handler)

    # 10.2 — APScheduler: alertas proactivas diarias
    try:
        from apscheduler.schedulers.background import BackgroundScheduler  # type: ignore

        alert_hour = int(os.getenv("ALERT_HOUR", "9"))
        scheduler = BackgroundScheduler()
        scheduler.add_job(_check_alerts_sync, "cron", args=[token], hour=alert_hour)
        scheduler.start()
        logger.info("Scheduler de alertas iniciado (hora=%d)", alert_hour)
    except ImportError:
        logger.warning(
            "APScheduler no instalado — las alertas proactivas están desactivadas. "
            "Instálalo con: pip install apscheduler"
        )

    logger.info("Bot iniciado. Esperando mensajes... (Ctrl+C para detener)")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
