"""Bot de Telegram — Agente Deportivo.

Requisitos:
1. Crea un bot con @BotFather en Telegram y obtén el token.
2. Añade el token al archivo .env:
       TELEGRAM_BOT_TOKEN=tu_token_aqui
3. Asegúrate de tener la DB local descargada para las competiciones que quieras usar.
4. Arranca el bot con:
       python bot.py

Comandos disponibles en el chat:
    /start              — Bienvenida y ayuda
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

import logging
import os
import sys
import textwrap
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Comprobación de dependencias
# ---------------------------------------------------------------------------

try:
    from telegram import Update
    from telegram.ext import (
        Application,
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

COMPETITION_NAMES = {
    2014: "La Liga (España)",
    2021: "Premier League (Inglaterra)",
    2002: "Bundesliga (Alemania)",
    2019: "Serie A (Italia)",
    2015: "Ligue 1 (Francia)",
    2017: "Primeira Liga (Portugal)",
    2001: "UEFA Champions League",
    2146: "UEFA Europa League",
}

MAX_MSG_LENGTH = 4000  # Telegram permite hasta 4096 caracteres por mensaje

# ---------------------------------------------------------------------------
# Helpers del agente
# ---------------------------------------------------------------------------


def _run_agent_text(competition: int, season: str, **kwargs) -> str:
    """Crea un agente, lo ejecuta y devuelve el informe de texto."""
    from src.agent import SportsAgent
    from src.data_loader import get_db_path

    db_path = get_db_path(competition, season)
    if not db_path.exists():
        return (
            f"⚠️ No hay DB local para competition={competition} season={season}.\n\n"
            f"Descarga los datos primero con:\n"
            f"`python -m src.run_agent --fetch-real --competition {competition} --season {season}`"
        )

    try:
        agent = SportsAgent(
            data_path=str(db_path),
            fetch_real=False,
            competition_id=competition,
            season=season,
            no_charts=True,
            **kwargs,
        )
        agent.load_data()
        agent.analyze()
        return agent.generate_report()
    except ValueError as exc:
        logger.warning("Error de datos al ejecutar agente: %s", exc)
        return f"⚠️ Error en los datos: {exc}"
    except Exception as exc:
        logger.error("Error inesperado al ejecutar agente: %s", exc, exc_info=True)
        return "❌ Error inesperado al generar el informe. Revisa los logs del servidor."


def _split_message(text: str, max_len: int = MAX_MSG_LENGTH) -> list[str]:
    """Divide un texto largo en fragmentos que Telegram puede enviar."""
    return textwrap.wrap(text, width=max_len, break_long_words=False, replace_whitespace=False)


def _parse_base(args: tuple[str, ...]) -> tuple[int, str] | str:
    """Parsea competition y season de los argumentos del comando."""
    if len(args) < 2:
        return "❌ Faltan parámetros. Ejemplo: `/liga 2014 2024`"
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
    """Bienvenida e instrucciones."""
    text = (
        "⚽ *Agente Deportivo* — Bot de análisis de fútbol\n\n"
        "*Comandos disponibles:*\n"
        "/competiciones — Lista de competiciones\n"
        "/equipos `<comp> <temp>` — Equipos en la DB\n"
        "/liga `<comp> <temp>` — Informe de liga\n"
        "/equipo `<comp> <temp> <nombre>` — Informe de equipo\n"
        "/jornada `<comp> <temp> <N>` — Informe de jornada\n"
        "/compare `<comp> <temp> <eq1> | <eq2>` — Comparativa\n\n"
        "*Ejemplo:*\n"
        "`/liga 2014 2024`\n"
        "`/equipo 2014 2024 Mallorca`\n"
        "`/compare 2014 2024 Real Madrid | Barcelona`"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_competiciones(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Lista las competiciones disponibles."""
    lines = ["📋 *Competiciones disponibles:*\n"]
    for cid, name in COMPETITION_NAMES.items():
        lines.append(f"  `{cid}` — {name}")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


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


async def cmd_liga(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/liga <competition> <season>"""
    result = _parse_base(context.args)
    if isinstance(result, str):
        await update.message.reply_text(result, parse_mode="Markdown")
        return
    competition, season = result

    await update.message.reply_text("⏳ Generando informe de liga...")
    text = _run_agent_text(competition, season)
    for fragment in _split_message(text):
        await update.message.reply_text(f"```\n{fragment}\n```", parse_mode="Markdown")


async def cmd_equipo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/equipo <competition> <season> <nombre_equipo>"""
    result = _parse_base(context.args)
    if isinstance(result, str):
        await update.message.reply_text(result, parse_mode="Markdown")
        return
    competition, season = result

    if len(context.args) < 3:
        await update.message.reply_text(
            "❌ Falta el nombre del equipo. Ejemplo: `/equipo 2014 2024 Mallorca`",
            parse_mode="Markdown",
        )
        return
    team = " ".join(context.args[2:])

    await update.message.reply_text(f"⏳ Generando informe de {team}...")
    text = _run_agent_text(competition, season, team=team)
    for fragment in _split_message(text):
        await update.message.reply_text(f"```\n{fragment}\n```", parse_mode="Markdown")


async def cmd_jornada(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/jornada <competition> <season> <N>"""
    result = _parse_base(context.args)
    if isinstance(result, str):
        await update.message.reply_text(result, parse_mode="Markdown")
        return
    competition, season = result

    if len(context.args) < 3:
        await update.message.reply_text(
            "❌ Falta el número de jornada. Ejemplo: `/jornada 2014 2024 15`",
            parse_mode="Markdown",
        )
        return
    try:
        jornada = int(context.args[2])
    except ValueError:
        await update.message.reply_text("❌ El número de jornada debe ser un entero.")
        return

    await update.message.reply_text(f"⏳ Generando informe de la jornada {jornada}...")
    text = _run_agent_text(competition, season, matchday=jornada)
    for fragment in _split_message(text):
        await update.message.reply_text(f"```\n{fragment}\n```", parse_mode="Markdown")


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
            "❌ Separa los dos equipos con `|`. Ejemplo:\n"
            "`/compare 2014 2024 Real Madrid | Barcelona`",
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
    text = _run_agent_text(competition, season, compare=(team1, team2))
    for fragment in _split_message(text):
        await update.message.reply_text(f"```\n{fragment}\n```", parse_mode="Markdown")


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

    application = Application.builder().token(token).build()

    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("competiciones", cmd_competiciones))
    application.add_handler(CommandHandler("equipos", cmd_equipos))
    application.add_handler(CommandHandler("liga", cmd_liga))
    application.add_handler(CommandHandler("equipo", cmd_equipo))
    application.add_handler(CommandHandler("jornada", cmd_jornada))
    application.add_handler(CommandHandler("compare", cmd_compare))
    application.add_error_handler(_error_handler)

    logger.info("Bot iniciado. Esperando mensajes... (Ctrl+C para detener)")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
