"""image_fetcher.py — Descarga y caché local de imágenes deportivas.

Fuentes principales:
  - TheSportsDB (https://www.thesportsdb.com/api/v1/json)
  - ESPN CDN    (https://a.espncdn.com/i/teamlogos/soccer/500/{id}.png)

Estructura de caché local:
  data/images/teams/{competition_id}/{slug}.png    → escudo de equipo
  data/images/players/{player_id}.{ext}            → foto de jugador
  data/images/players/{player_id}_cutout.{ext}     → recorte (fondo transparente)
  data/images/stadiums/{slug}.jpg                  → foto del estadio
  data/teams_meta.json                             → metadata completa de equipos
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Optional

import requests
from dotenv import load_dotenv

load_dotenv()

_logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).parent.parent / "data"
_IMAGES_DIR = _DATA_DIR / "images"
_TEAMS_META_PATH = _DATA_DIR / "teams_meta.json"

_TSDB_KEY = os.getenv("THESPORTSDB_API_KEY", "3")
_TSDB_BASE = f"https://www.thesportsdb.com/api/v1/json/{_TSDB_KEY}"

_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; AgenteDeportivo/1.0)"}
_TIMEOUT = 15
_MAX_IMAGE_KB = 800


# ---------------------------------------------------------------------------
# Utilidades internas
# ---------------------------------------------------------------------------

def _slugify(name: str) -> str:
    """Convierte nombre a slug seguro para usar como nombre de archivo."""
    return re.sub(r"[^\w]", "_", name.lower()).strip("_")


def _load_meta() -> dict:
    """Carga el JSON de metadata de equipos desde disco."""
    if _TEAMS_META_PATH.exists():
        try:
            return json.loads(_TEAMS_META_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_meta(meta: dict) -> None:
    _TEAMS_META_PATH.parent.mkdir(parents=True, exist_ok=True)
    _TEAMS_META_PATH.write_text(
        json.dumps(meta, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Descarga de imágenes
# ---------------------------------------------------------------------------

def download_image(url: str, local_path: Path) -> Optional[str]:
    """Descarga una imagen de la URL indicada y la guarda en local_path.

    Si el archivo ya existe y no está vacío, lo devuelve directamente sin
    volver a descargar.

    Returns:
        Ruta local como str si tiene éxito, None si la URL está vacía o
        la descarga falla.
    """
    if not url or url.strip() in ("", "null"):
        return None
    if local_path.exists() and local_path.stat().st_size > 0:
        return str(local_path)

    try:
        r = requests.get(url, headers=_HEADERS, timeout=_TIMEOUT, stream=True)
        r.raise_for_status()
        content = b""
        for chunk in r.iter_content(chunk_size=8192):
            content += chunk
            if len(content) > _MAX_IMAGE_KB * 1024:
                _logger.debug("Imagen demasiado grande (>%d KB): %s", _MAX_IMAGE_KB, url)
                return None
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_bytes(content)
        _logger.debug("Imagen guardada: %s", local_path)
        return str(local_path)
    except Exception as exc:
        _logger.debug("Error descargando %s: %s", url, exc)
        return None


# ---------------------------------------------------------------------------
# API de equipos
# ---------------------------------------------------------------------------

def get_team_assets(
    team_name: str,
    competition_id: int = 2014,
    download: bool = True,
    delay: float = 0.5,
) -> dict:
    """Obtiene metadata e imágenes de un equipo desde TheSportsDB.

    Consulta TheSportsDB ``searchteams.php`` y opcionalmente ``lookupvenue.php``
    para obtener la foto del estadio.  Guarda todo en ``data/teams_meta.json``
    para evitar consultas repetidas.

    Args:
        team_name:      Nombre del equipo (puede ser parcial).
        competition_id: ID de competición del proyecto (para organizar imágenes).
        download:       Si True, descarga las imágenes localmente.
        delay:          Pausa en segundos entre llamadas a la API.

    Returns:
        dict con:
          team_name, badge_url, badge_local, stadium, stadium_thumb_url,
          stadium_local, venue_id, capacity, colour1, colour2,
          description_es, formed_year, team_id_tsdb, espn_id
    """
    meta = _load_meta()
    cache_key = f"{competition_id}:{_slugify(team_name)}"
    entry = meta.get(cache_key, {})

    # Si ya tenemos el badge descargado y existe el archivo, devolver
    badge_local = entry.get("badge_local")
    if entry and badge_local and Path(badge_local).exists():
        return entry

    try:
        r = requests.get(
            f"{_TSDB_BASE}/searchteams.php",
            params={"t": team_name},
            headers=_HEADERS,
            timeout=_TIMEOUT,
        )
        r.raise_for_status()
        teams = r.json().get("teams") or []
    except Exception as exc:
        _logger.warning("TheSportsDB searchteams falló para '%s': %s", team_name, exc)
        return entry or {}

    if not teams:
        _logger.debug("TheSportsDB no encontró el equipo '%s'", team_name)
        return entry or {}

    t = teams[0]
    venue_id = t.get("idVenue") or ""

    entry.update({
        "team_name":     t.get("strTeam", team_name),
        "badge_url":     t.get("strBadge") or "",
        "badge_local":   None,
        "stadium":       t.get("strStadium") or "",
        "stadium_thumb_url": "",
        "stadium_local": None,
        "venue_id":      venue_id,
        "capacity":      int(t.get("intStadiumCapacity") or 0) or None,
        "colour1":       t.get("strColour1") or "",
        "colour2":       t.get("strColour2") or "",
        "description_es": (t.get("strDescriptionES") or "")[:600],
        "formed_year":   t.get("intFormedYear") or "",
        "team_id_tsdb":  t.get("idTeam") or "",
        "espn_id":       t.get("idESPN") or "",
    })

    # Foto del estadio via lookupvenue
    if venue_id:
        try:
            time.sleep(delay)
            vr = requests.get(
                f"{_TSDB_BASE}/lookupvenue.php",
                params={"id": venue_id},
                headers=_HEADERS,
                timeout=_TIMEOUT,
            )
            vr.raise_for_status()
            venues = vr.json().get("venues") or []
            if venues:
                entry["stadium_thumb_url"] = venues[0].get("strThumb") or ""
        except Exception as exc:
            _logger.debug("lookupvenue falló (venue_id=%s): %s", venue_id, exc)

    if download:
        # Escudo del equipo
        badge_url = entry.get("badge_url", "")
        if badge_url:
            ext = Path(badge_url.split("?")[0]).suffix or ".png"
            badge_path = _IMAGES_DIR / "teams" / str(competition_id) / f"{_slugify(team_name)}{ext}"
            entry["badge_local"] = download_image(badge_url, badge_path)

        # Foto del estadio
        stadium_url = entry.get("stadium_thumb_url", "")
        if stadium_url:
            ext2 = Path(stadium_url.split("?")[0]).suffix or ".jpg"
            stadium_path = _IMAGES_DIR / "stadiums" / f"{_slugify(entry.get('stadium', team_name))}{ext2}"
            entry["stadium_local"] = download_image(stadium_url, stadium_path)

    meta[cache_key] = entry
    _save_meta(meta)
    return entry


def prefetch_league_assets(
    competition_id: int,
    team_names: list[str],
    delay: float = 1.2,
) -> dict[str, dict]:
    """Descarga en batch los escudos de todos los equipos de una liga.

    Incluye pausa ``delay`` entre llamadas para respetar los rate limits de
    TheSportsDB (máx. ~60 req/min con clave pública).

    Args:
        competition_id: ID de competición del proyecto.
        team_names:     Lista de nombres de equipo.
        delay:          Pausa en segundos entre peticiones (default 1.2 s).

    Returns:
        dict keyed by team_name → assets dict
    """
    results: dict[str, dict] = {}
    total = len(team_names)
    for i, name in enumerate(team_names, 1):
        _logger.info("[%d/%d] Descargando assets de equipo: %s", i, total, name)
        results[name] = get_team_assets(name, competition_id, download=True, delay=0.4)
        if i < total:
            time.sleep(delay)
    return results


# ---------------------------------------------------------------------------
# API de jugadores
# ---------------------------------------------------------------------------

def get_player_images_for_team(
    team_name: str,
    team_id_tsdb: str = "",
    download: bool = True,
) -> dict[str, dict]:
    """Obtiene URLs e imágenes de los jugadores de un equipo desde TheSportsDB.

    Estrategia:
      1. Con API key de pago: ``searchplayers.php?t=TEAM`` devuelve todos los
         jugadores con fotos en UNA sola llamada.
      2. Con clave gratuita ("3"): ese endpoint devuelve vacío. En ese caso usa
         ``lookup_all_players.php?id=TEAM_ID`` para obtener la lista de IDs, y
         luego hace búsquedas individuales con ``searchplayers.php?p=NAME`` solo
         para los activos (los resultados se cachean en disco).

    Args:
        team_name:    Nombre del equipo.
        team_id_tsdb: ID del equipo en TheSportsDB (opcional, se resuelve si no se pasa).
        download:     Si True, descarga las imágenes localmente.

    Returns:
        dict keyed by ``player_name.lower()`` → {
            player_id_tsdb, thumb_url, thumb_local,
            cutout_url, cutout_local, nationality, date_born, position_tsdb
        }
    """
    result: dict[str, dict] = {}

    # ── Intento 1: búsqueda batch (funciona con API key de pago) ─────────────
    try:
        r = requests.get(
            f"{_TSDB_BASE}/searchplayers.php",
            params={"t": team_name},
            headers=_HEADERS,
            timeout=20,
        )
        r.raise_for_status()
        players = r.json().get("player") or []
    except Exception as exc:
        _logger.debug("searchplayers?t= falló para '%s': %s", team_name, exc)
        players = []

    # ── Intento 2: lookup_all_players (clave gratuita) ───────────────────────
    if not players:
        tid = team_id_tsdb
        if not tid:
            # Intentar obtener el team_id desde la caché de equipos
            meta = _load_meta()
            cache_key = f"2014:{_slugify(team_name)}"  # competition_id ignorado aquí
            for k, v in meta.items():
                if _slugify(team_name) in k:
                    tid = v.get("team_id_tsdb", "")
                    break
        if tid:
            try:
                r2 = requests.get(
                    f"{_TSDB_BASE}/lookup_all_players.php",
                    params={"id": tid},
                    headers=_HEADERS,
                    timeout=20,
                )
                r2.raise_for_status()
                players = r2.json().get("player") or []
                # lookup_all_players no da thumbs → marcar para búsqueda individual
                for p in players:
                    p["_needs_individual_lookup"] = True
            except Exception as exc:
                _logger.debug("lookup_all_players falló para team_id=%s: %s", tid, exc)

    for p in players:
        if p.get("strStatus", "Active") not in ("Active", ""):
            continue

        pid = str(p.get("idPlayer") or "")
        name = p.get("strPlayer") or ""
        if not name:
            continue

        thumb_url = p.get("strThumb") or ""
        cutout_url = p.get("strCutout") or ""

        # Si no hay thumb y la fuente es lookup_all_players, buscar individualmente
        if not thumb_url and p.get("_needs_individual_lookup") and pid:
            try:
                ri = requests.get(
                    f"{_TSDB_BASE}/lookupplayer.php",
                    params={"id": pid},
                    headers=_HEADERS,
                    timeout=10,
                )
                ri.raise_for_status()
                pdata = (ri.json().get("players") or [{}])[0]
                thumb_url  = pdata.get("strThumb") or ""
                cutout_url = pdata.get("strCutout") or ""
                time.sleep(0.3)
            except Exception:
                pass

        player_info: dict = {
            "player_id_tsdb": pid,
            "thumb_url":      thumb_url,
            "thumb_local":    None,
            "cutout_url":     cutout_url,
            "cutout_local":   None,
            "nationality":    p.get("strNationality") or "",
            "date_born":      p.get("dateBorn") or "",
            "position_tsdb":  p.get("strPosition") or "",
        }

        if download and pid:
            if thumb_url:
                ext = Path(thumb_url.split("?")[0]).suffix or ".jpg"
                thumb_path = _IMAGES_DIR / "players" / f"{pid}{ext}"
                player_info["thumb_local"] = download_image(thumb_url, thumb_path)
            if cutout_url:
                ext2 = Path(cutout_url.split("?")[0]).suffix or ".png"
                cutout_path = _IMAGES_DIR / "players" / f"{pid}_cutout{ext2}"
                player_info["cutout_local"] = download_image(cutout_url, cutout_path)

        result[name.lower()] = player_info

    return result


def get_player_image_by_name(
    player_name: str,
    download: bool = True,
) -> dict:
    """Obtiene imagen de UN jugador buscando por nombre (funciona con clave gratuita).

    Usa ``searchplayers.php?p=NAME``.

    Returns:
        dict con: player_id_tsdb, thumb_url, thumb_local, cutout_url, cutout_local,
                  nationality, date_born, position_tsdb
    """
    try:
        r = requests.get(
            f"{_TSDB_BASE}/searchplayers.php",
            params={"p": player_name},
            headers=_HEADERS,
            timeout=15,
        )
        r.raise_for_status()
        players = r.json().get("player") or []
    except Exception as exc:
        _logger.debug("searchplayers?p= falló para '%s': %s", player_name, exc)
        return {}

    if not players:
        return {}

    p = players[0]
    pid = str(p.get("idPlayer") or "")
    thumb_url  = p.get("strThumb") or ""
    cutout_url = p.get("strCutout") or ""

    result: dict = {
        "player_id_tsdb": pid,
        "thumb_url":      thumb_url,
        "thumb_local":    None,
        "cutout_url":     cutout_url,
        "cutout_local":   None,
        "nationality":    p.get("strNationality") or "",
        "date_born":      p.get("dateBorn") or "",
        "position_tsdb":  p.get("strPosition") or "",
    }

    if download and pid:
        if thumb_url:
            ext = Path(thumb_url.split("?")[0]).suffix or ".jpg"
            thumb_path = _IMAGES_DIR / "players" / f"{pid}{ext}"
            result["thumb_local"] = download_image(thumb_url, thumb_path)
        if cutout_url:
            ext2 = Path(cutout_url.split("?")[0]).suffix or ".png"
            cutout_path = _IMAGES_DIR / "players" / f"{pid}_cutout{ext2}"
            result["cutout_local"] = download_image(cutout_url, cutout_path)

    return result


# ---------------------------------------------------------------------------
# Acceso rápido (helpers sin argumentos complejos)
# ---------------------------------------------------------------------------

def get_team_badge_local(team_name: str, competition_id: int = 2014) -> Optional[str]:
    """Devuelve la ruta local del escudo de un equipo, descargándolo si hace falta."""
    assets = get_team_assets(team_name, competition_id)
    return assets.get("badge_local")


def get_player_thumb_local(player_id_tsdb: str) -> Optional[str]:
    """Devuelve la ruta local de la foto de un jugador si ya está descargada."""
    for ext in (".jpg", ".jpeg", ".png"):
        p = _IMAGES_DIR / "players" / f"{player_id_tsdb}{ext}"
        if p.exists() and p.stat().st_size > 0:
            return str(p)
    return None


def get_cached_team_meta(team_name: str, competition_id: int = 2014) -> dict:
    """Lee la metadata de un equipo desde la caché local sin hacer llamadas a la API."""
    meta = _load_meta()
    return meta.get(f"{competition_id}:{_slugify(team_name)}", {})
