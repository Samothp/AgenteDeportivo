"""Tests unitarios para src/analysis.py.

Todas las funciones bajo test son puras (entrada → salida sin efectos laterales),
por lo que no requieren mocks ni fixtures complejas.
"""

from __future__ import annotations

import pandas as pd
import pytest

from src.analysis import (
    compute_overall_metrics,
    compute_standings,
    compute_team_record,
    compute_compare,
    compute_league_comparison,
    compute_xpts,
)


# ---------------------------------------------------------------------------
# Fixtures compartidas
# ---------------------------------------------------------------------------

def _make_df() -> pd.DataFrame:
    """DataFrame mínimo con 4 partidos entre 3 equipos."""
    return pd.DataFrame({
        "jornada":           [1,        1,        2,        2],
        "local_team":        ["Alpha",  "Beta",   "Alpha",  "Gamma"],
        "visitante_team":    ["Beta",   "Gamma",  "Gamma",  "Beta"],
        "goles_local":       [2,        1,        0,        3],
        "goles_visitante":   [1,        1,        0,        0],
        "goles_totales":     [3,        2,        0,        3],
        "amarillas_local":   [1,        0,        2,        1],
        "amarillas_visitante":[0,       1,        0,        2],
        "rojas_local":       [0,        0,        0,        0],
        "rojas_visitante":   [0,        0,        0,        0],
        "xg_local":          [1.8,      0.9,      0.5,      2.5],
        "xg_visitante":      [0.7,      0.8,      0.6,      0.3],
        "posesion_local":    [55.0,     48.0,     50.0,     60.0],
        "posesion_visitante":[45.0,     52.0,     50.0,     40.0],
    })


def _team_df(df: pd.DataFrame, team: str) -> pd.DataFrame:
    """Filtra el df a los partidos donde 'team' participa (como lo hace SportsAgent)."""
    return df[
        (df["local_team"] == team) | (df["visitante_team"] == team)
    ].copy()


# ---------------------------------------------------------------------------
# compute_overall_metrics
# ---------------------------------------------------------------------------

class TestComputeOverallMetrics:
    def test_basic_counts(self):
        df = _make_df()
        m = compute_overall_metrics(df)
        assert m["partidos_analizados"] == 4
        assert m["goles_totales"] == 8
        assert abs(m["goles_promedio_por_partido"] - 2.0) < 1e-6

    def test_tarjetas(self):
        df = _make_df()
        m = compute_overall_metrics(df)
        assert m["tarjetas_amarillas"] == 7   # 1+0+0+1+2+0+1+2
        assert m["tarjetas_rojas"] == 0

    def test_perspectiva_equipo_goles(self):
        df = _make_df()
        # compute_overall_metrics espera df pre-filtrado por equipo (como SportsAgent)
        m = compute_overall_metrics(_team_df(df, "Alpha"), team="Alpha")
        # Alpha: J1 local 2-1 (GF=2 GC=1), J2 local 0-0 (GF=0 GC=0)
        assert m["goles_a_favor"] == 2
        assert m["goles_en_contra"] == 1

    def test_sin_datos_opcionales(self):
        """Con un DataFrame mínimo (sin columnas opcionales) no debe fallar."""
        df = pd.DataFrame({
            "local_team":      ["A"],
            "visitante_team":  ["B"],
            "goles_local":     [1],
            "goles_visitante": [0],
            "goles_totales":   [1],
        })
        m = compute_overall_metrics(df)
        assert m["partidos_analizados"] == 1
        assert m["tarjetas_amarillas"] is None
        assert m["tarjetas_rojas"] is None

    def test_posesion_promedio(self):
        df = _make_df()
        m = compute_overall_metrics(df)
        expected = (55.0 + 48.0 + 50.0 + 60.0) / 4
        assert abs(m["posesion_local_promedio"] - expected) < 1e-6


# ---------------------------------------------------------------------------
# compute_standings
# ---------------------------------------------------------------------------

class TestComputeStandings:
    def test_orden_por_puntos(self):
        df = _make_df()
        st = compute_standings(df)
        # Gamma: G1E2D0 → 5 pts | Alpha: G1E1D0 → 4 pts | Beta: G0E1D2 → 1 pt
        assert st.iloc[0]["Equipo"] == "Gamma"
        assert st.iloc[0]["PTS"] == 5
        assert st.iloc[1]["Equipo"] == "Alpha"
        assert st.iloc[1]["PTS"] == 4
        assert st.iloc[2]["Equipo"] == "Beta"

    def test_columnas_obligatorias(self):
        df = _make_df()
        st = compute_standings(df)
        for col in ["Pos", "Equipo", "PJ", "G", "E", "P", "GF", "GC", "DIF", "PTS"]:
            assert col in st.columns

    def test_up_to_jornada(self):
        df = _make_df()
        st = compute_standings(df, up_to_jornada=1)
        # Solo jornada 1: Alpha gana, Beta empata con Gamma
        alpha_row = st[st["Equipo"] == "Alpha"].iloc[0]
        assert alpha_row["PJ"] == 1
        assert alpha_row["G"] == 1

    def test_df_vacio(self):
        df = pd.DataFrame(columns=_make_df().columns)
        st = compute_standings(df)
        assert len(st) == 0

    def test_posicion_incremental(self):
        df = _make_df()
        st = compute_standings(df)
        assert list(st["Pos"]) == list(range(1, len(st) + 1))


# ---------------------------------------------------------------------------
# compute_team_record
# ---------------------------------------------------------------------------

class TestComputeTeamRecord:
    def test_alpha_record(self):
        df = _make_df()
        # compute_team_record espera df pre-filtrado por equipo (como SportsAgent)
        rec = compute_team_record(_team_df(df, "Alpha"), "Alpha")
        assert rec["victorias"] == 1
        assert rec["empates"] == 1
        assert rec["derrotas"] == 0
        assert rec["puntos"] == 4

    def test_racha_actual(self):
        df = _make_df()
        rec = compute_team_record(_team_df(df, "Alpha"), "Alpha")
        # J1: V, J2: E → racha "VE"
        assert rec["racha_actual"] == "VE"

    def test_rachas_maximas(self):
        df = _make_df()
        rec = compute_team_record(_team_df(df, "Alpha"), "Alpha")
        assert rec["racha_sin_perder_max"] == 2   # 2 partidos sin perder
        assert rec["racha_goleadora_max"] == 1    # solo marcó en J1
        assert rec["racha_sin_marcar_max"] == 1   # J2: 0-0

    def test_tabla_resultados_longitud(self):
        df = _make_df()
        rec = compute_team_record(_team_df(df, "Alpha"), "Alpha")
        assert len(rec["tabla_resultados"]) == 2

    def test_equipo_inexistente(self):
        df = _make_df()
        # df filtrado por equipo inexistente → vacío → todo a cero
        rec = compute_team_record(_team_df(df, "Inexistente"), "Inexistente")
        assert rec["victorias"] == 0
        assert rec["puntos"] == 0


# ---------------------------------------------------------------------------
# compute_compare
# ---------------------------------------------------------------------------

class TestComputeCompare:
    def test_keys_presentes(self):
        df = _make_df()
        result = compute_compare("Alpha", "Gamma", df)
        for key in ["team1", "team2", "metrics1", "metrics2", "record1", "record2", "h2h"]:
            assert key in result

    def test_h2h_alpha_gamma(self):
        df = _make_df()
        result = compute_compare("Alpha", "Gamma", df)
        # Solo 1 partido directo: J2 Alpha 0-0 Gamma
        assert result["h2h_summary"]["pj"] == 1
        assert result["h2h_summary"]["draws"] == 1


# ---------------------------------------------------------------------------
# compute_league_comparison
# ---------------------------------------------------------------------------

class TestComputeLeagueComparison:
    def test_resultado_es_lista(self):
        team_m = {"goles_a_favor_promedio": 2.0, "goles_concedidos_promedio": 1.0}
        league_m = {"goles_por_equipo_promedio": 1.5}
        result = compute_league_comparison(team_m, league_m)
        assert isinstance(result, list)

    def test_sin_metricas_comunes(self):
        result = compute_league_comparison({}, {})
        assert result == []


# ---------------------------------------------------------------------------
# compute_xpts
# ---------------------------------------------------------------------------

class TestComputeXpts:
    def test_columnas_resultado(self):
        df = _make_df()
        xpts = compute_xpts(df)
        assert "Equipo" in xpts.columns
        assert "xPts" in xpts.columns  # columna real: xPts (no xPTS)

    def test_equipos_en_resultado(self):
        df = _make_df()
        xpts = compute_xpts(df)
        equipos = set(xpts["Equipo"].tolist())
        assert "Alpha" in equipos
        assert "Beta" in equipos
        assert "Gamma" in equipos

    def test_xpts_no_negativos(self):
        df = _make_df()
        xpts = compute_xpts(df)
        assert (xpts["xPts"] >= 0).all()
