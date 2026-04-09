"""Tests de integración para src/api.py (FastAPI).

Usa TestClient de Starlette para hacer peticiones HTTP reales contra la app
sin necesidad de levantar un servidor. No requiere la DB local: los endpoints
de informe devuelven 404 si no existe, lo que también se verifica.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from src.api import app
from src.constants import COMPETITION_NAMES

client = TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# GET / — health check
# ---------------------------------------------------------------------------

class TestHealthCheck:
    def test_status_ok(self):
        r = client.get("/")
        assert r.status_code == 200

    def test_version_presente(self):
        r = client.get("/")
        assert r.json()["version"] == "3.0.0"

    def test_competitions_presentes(self):
        r = client.get("/")
        data = r.json()
        assert "competitions" in data
        # Verifica que contiene las mismas ligas que constants.py
        for cid in COMPETITION_NAMES:
            assert str(cid) in {str(k) for k in data["competitions"]}


# ---------------------------------------------------------------------------
# GET /teams — lista de equipos
# ---------------------------------------------------------------------------

class TestListTeams:
    def test_sin_db_devuelve_404(self):
        r = client.get("/teams", params={"competition": 9999, "season": "1900"})
        assert r.status_code == 404

    def test_mensaje_error_informativo(self):
        r = client.get("/teams", params={"competition": 9999, "season": "1900"})
        assert "9999" in r.json()["detail"]


# ---------------------------------------------------------------------------
# POST /report/* — todos devuelven 404 sin DB local
# ---------------------------------------------------------------------------

class TestReportEndpoints:
    """Sin DB local, todos los endpoints de informe deben devolver 404
    con un mensaje que explica cómo descargar los datos."""

    _COMPETITION = 9999
    _SEASON = "1900"

    def _base(self) -> dict:
        return {"competition": self._COMPETITION, "season": self._SEASON, "top_n": 5}

    def test_liga_sin_db(self):
        r = client.post("/report/liga", json=self._base())
        assert r.status_code == 404

    def test_equipo_sin_db(self):
        body = {**self._base(), "team": "TestEquipo"}
        r = client.post("/report/equipo", json=body)
        assert r.status_code == 404

    def test_jornada_sin_db(self):
        body = {**self._base(), "jornada": 1}
        r = client.post("/report/jornada", json=body)
        assert r.status_code == 404

    def test_partido_sin_db(self):
        body = {**self._base(), "match_id": 1}
        r = client.post("/report/partido", json=body)
        assert r.status_code == 404

    def test_jugador_sin_db(self):
        body = {**self._base(), "team": "TestEquipo", "player": "TestJugador"}
        r = client.post("/report/jugador", json=body)
        assert r.status_code == 404

    def test_compare_sin_db(self):
        body = {**self._base(), "team1": "Alpha", "team2": "Beta"}
        r = client.post("/report/compare", json=body)
        assert r.status_code == 404

    def test_detalle_error_incluye_fetch_real(self):
        r = client.post("/report/liga", json=self._base())
        assert "fetch-real" in r.json()["detail"]


# ---------------------------------------------------------------------------
# Validación de esquemas — campos obligatorios
# ---------------------------------------------------------------------------

class TestSchemaValidation:
    def test_equipo_sin_team_da_422(self):
        body = {"competition": 2014, "season": "2024", "top_n": 5}
        r = client.post("/report/equipo", json=body)
        assert r.status_code == 422

    def test_jornada_sin_jornada_da_422(self):
        body = {"competition": 2014, "season": "2024", "top_n": 5}
        r = client.post("/report/jornada", json=body)
        assert r.status_code == 422

    def test_top_n_fuera_de_rango_da_422(self):
        body = {"competition": 2014, "season": "2024", "top_n": 999}
        r = client.post("/report/liga", json=body)
        assert r.status_code == 422

    def test_compare_sin_team2_da_422(self):
        body = {"competition": 2014, "season": "2024", "top_n": 5, "team1": "Alpha"}
        r = client.post("/report/compare", json=body)
        assert r.status_code == 422
