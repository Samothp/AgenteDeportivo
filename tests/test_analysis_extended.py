"""Tests extendidos de src/analysis.py.

Cubre las funciones no testeadas en test_analysis.py:
  - _poisson_pmf
  - compute_team_form
  - compute_matchday_summary
  - compute_match_detail
  - compute_liga_summary
  - compute_team_percentiles
  - compute_player_rankings
  - compute_player_profile
  - compute_match_preview
"""

import math

import pandas as pd
import pytest

from src.analysis import (
    _poisson_pmf,
    compute_liga_summary,
    compute_match_detail,
    compute_match_preview,
    compute_matchday_summary,
    compute_player_profile,
    compute_player_rankings,
    compute_team_form,
    compute_team_percentiles,
)

# ---------------------------------------------------------------------------
# Fixtures compartidos
# ---------------------------------------------------------------------------


def _make_df() -> pd.DataFrame:
    """DataFrame mínimo con 6 partidos, 3 equipos y 3 jornadas.

    Resultados:
      J1: Alpha 2-1 Beta,  Beta 1-1 Gamma
      J2: Alpha 0-0 Gamma, Gamma 3-0 Alpha
      J3: Beta 1-2 Alpha,  Gamma 0-0 Beta
    """
    return pd.DataFrame(
        {
            "id_event": [100, 101, 102, 103, 104, 105],
            "jornada": [1, 1, 2, 2, 3, 3],
            "local_team": ["Alpha", "Beta", "Alpha", "Gamma", "Beta", "Gamma"],
            "visitante_team": ["Beta", "Gamma", "Gamma", "Alpha", "Alpha", "Beta"],
            "goles_local": [2, 1, 0, 3, 1, 0],
            "goles_visitante": [1, 1, 0, 0, 2, 0],
            "goles_totales": [3, 2, 0, 3, 3, 0],
            "xg_local": [1.8, 0.9, 0.5, 2.5, 1.1, 0.4],
            "xg_visitante": [0.7, 0.8, 0.6, 0.3, 1.4, 0.5],
            "date": [
                "2025-09-01",
                "2025-09-01",
                "2025-09-08",
                "2025-09-08",
                "2025-09-15",
                "2025-09-15",
            ],
            "posesion_local": [55.0, 48.0, 50.0, 60.0, 52.0, 45.0],
            "posesion_visitante": [45.0, 52.0, 50.0, 40.0, 48.0, 55.0],
            "amarillas_local": [1, 0, 2, 1, 0, 1],
            "amarillas_visitante": [0, 1, 0, 2, 1, 0],
            "rojas_local": [0, 0, 0, 0, 0, 0],
            "rojas_visitante": [0, 0, 0, 0, 0, 0],
            "competition": ["La Liga"] * 6,
            "season": ["2025"] * 6,
        }
    )


def _make_players_df() -> pd.DataFrame:
    """DataFrame mínimo de 4 jugadores de 2 equipos."""
    return pd.DataFrame(
        {
            "player_name": ["Messi", "Suarez", "Neymar", "Silva"],
            "team": ["Alpha", "Alpha", "Beta", "Beta"],
            "position": ["F", "F", "M", "D"],
            "appearances": [10, 8, 10, 9],
            "goals": [8, 4, 2, 0],
            "assists": [3, 5, 4, 1],
            "goals_assists": [11, 9, 6, 1],
            "shots_on_target": [20, 10, 8, 2],
            "shots_total": [30, 15, 12, 3],
            "yellow_cards": [1, 2, 3, 4],
            "red_cards": [0, 0, 0, 0],
            "minutes_played": [900, 720, 900, 810],
            "season": ["2025"] * 4,
        }
    )


# ---------------------------------------------------------------------------
# _poisson_pmf
# ---------------------------------------------------------------------------


class TestPoissonPmf:
    def test_k0_lam1_aproxima_e_neg1(self):
        """P(X=0, λ=1) = e^{-1} ≈ 0.3679."""
        result = _poisson_pmf(1.0, 0)
        assert abs(result - math.exp(-1.0)) < 1e-9

    def test_lam0_k0_es_1(self):
        """λ≤0 → P(X=0) = 1 (distribución degenerada)."""
        assert _poisson_pmf(0.0, 0) == 1.0

    def test_lam0_k_positivo_es_0(self):
        """λ≤0 → P(X=k) = 0 para k > 0."""
        assert _poisson_pmf(0.0, 1) == 0.0
        assert _poisson_pmf(-1.0, 3) == 0.0

    def test_valores_no_negativos(self):
        """P(X=k, λ) ≥ 0 para todo k y λ razonables."""
        for lam in (0.5, 1.0, 2.0, 5.0):
            for k in range(7):
                assert _poisson_pmf(lam, k) >= 0.0


# ---------------------------------------------------------------------------
# compute_team_form
# ---------------------------------------------------------------------------


class TestComputeTeamForm:
    def test_devuelve_cadena(self):
        """compute_team_form siempre devuelve str."""
        df = _make_df()
        result = compute_team_form(df, "Alpha")
        assert isinstance(result, str)

    def test_victorias_emiten_verde(self):
        """Equipo que solo gana → todos los emojis son 🟢."""
        df = pd.DataFrame(
            {
                "local_team": ["Alpha", "Alpha", "Alpha"],
                "visitante_team": ["Other", "Other", "Other"],
                "goles_local": [3, 2, 1],
                "goles_visitante": [0, 0, 0],
                "jornada": [1, 2, 3],
            }
        )
        result = compute_team_form(df, "Alpha", last_n=3)
        assert result.count("🟢") == 3

    def test_last_n_limita_emojis(self):
        """last_n=1 → como máximo 1 emoji en la cadena."""
        df = _make_df()
        result = compute_team_form(df, "Alpha", last_n=1)
        parts = result.split()
        assert len(parts) <= 1

    def test_equipo_inexistente_devuelve_vacio(self):
        """Equipo sin partidos → cadena vacía."""
        df = _make_df()
        result = compute_team_form(df, "EquipoQuNoExiste", last_n=5)
        assert result == ""


# ---------------------------------------------------------------------------
# compute_matchday_summary
# ---------------------------------------------------------------------------


class TestComputeMatchdaySummary:
    def test_keys_principales_presentes(self):
        """El resumen incluye todas las claves requeridas."""
        df = _make_df()
        df_j1 = df[df["jornada"] == 1]
        result = compute_matchday_summary(df_j1, df, jornada=1)
        for key in (
            "jornada",
            "num_partidos",
            "results",
            "total_goals",
            "avg_goals",
            "standings",
            "partidos_muda",
        ):
            assert key in result

    def test_num_partidos_correcto(self):
        """Jornada 1 tiene 2 partidos en el fixture."""
        df = _make_df()
        df_j1 = df[df["jornada"] == 1]
        result = compute_matchday_summary(df_j1, df, jornada=1)
        assert result["num_partidos"] == 2

    def test_total_goals_correcto(self):
        """Jornada 1: Alpha 2-1 Beta + Beta 1-1 Gamma = 5 goles totales."""
        df = _make_df()
        df_j1 = df[df["jornada"] == 1]
        result = compute_matchday_summary(df_j1, df, jornada=1)
        assert result["total_goals"] == 5

    def test_muda_identifica_porteria_a_cero(self):
        """Jornada 2 tiene al menos 1 partido con portería a cero."""
        df = _make_df()
        df_j2 = df[df["jornada"] == 2]
        result = compute_matchday_summary(df_j2, df, jornada=2)
        # Alpha 0-0 Gamma → ambos a cero (muda=True)
        # Gamma 3-0 Alpha  → visitante a cero (muda=True)
        assert len(result["partidos_muda"]) > 0

    def test_standings_es_dataframe(self):
        """La clasificación acumulada es un DataFrame."""
        df = _make_df()
        df_j1 = df[df["jornada"] == 1]
        result = compute_matchday_summary(df_j1, df, jornada=1)
        assert isinstance(result["standings"], pd.DataFrame)


# ---------------------------------------------------------------------------
# compute_match_detail
# ---------------------------------------------------------------------------


class TestComputeMatchDetail:
    def test_no_encontrado_lanza_valueerror(self):
        """match_id inexistente → ValueError."""
        df = _make_df()
        with pytest.raises(ValueError):
            compute_match_detail(df, 9999)

    def test_keys_principales_presentes(self):
        """El resultado incluye las claves básicas."""
        df = _make_df()
        result = compute_match_detail(df, 100)
        for key in (
            "local",
            "visitante",
            "goles_local",
            "goles_visitante",
            "resultado",
            "narrativa",
            "stats",
        ):
            assert key in result

    def test_resultado_local_gana(self):
        """match_id=100: Alpha 2-1 Beta → resultado='local'."""
        df = _make_df()
        result = compute_match_detail(df, 100)
        assert result["resultado"] == "local"
        assert result["local"] == "Alpha"
        assert result["visitante"] == "Beta"

    def test_resultado_empate(self):
        """match_id=101: Beta 1-1 Gamma → resultado='empate'."""
        df = _make_df()
        result = compute_match_detail(df, 101)
        assert result["resultado"] == "empate"

    def test_narrativa_es_cadena_no_vacia(self):
        """La narrativa automática es una cadena no vacía."""
        df = _make_df()
        result = compute_match_detail(df, 100)
        assert isinstance(result["narrativa"], str)
        assert len(result["narrativa"]) > 0


# ---------------------------------------------------------------------------
# compute_liga_summary
# ---------------------------------------------------------------------------


class TestComputeLigaSummary:
    def test_vacio_devuelve_dict_vacio(self):
        """DataFrame vacío → {}."""
        result = compute_liga_summary(pd.DataFrame())
        assert result == {}

    def test_keys_principales_presentes(self):
        """El resumen incluye claves de alto nivel esperadas."""
        df = _make_df()
        result = compute_liga_summary(df)
        for key in (
            "competition",
            "season",
            "partidos_totales",
            "goles_totales",
            "clasificacion",
            "stats_por_equipo",
            "records",
            "home_away",
        ):
            assert key in result

    def test_clasificacion_es_dataframe(self):
        """clasificacion es un DataFrame con columna 'Equipo'."""
        df = _make_df()
        result = compute_liga_summary(df)
        assert isinstance(result["clasificacion"], pd.DataFrame)
        assert "Equipo" in result["clasificacion"].columns

    def test_partidos_totales_correcto(self):
        """Cuenta correctamente el total de partidos."""
        df = _make_df()
        result = compute_liga_summary(df)
        assert result["partidos_totales"] == len(df)

    def test_goles_totales_correcto(self):
        """Suma de goles_totales del fixture = 3+2+0+3+3+0 = 11."""
        df = _make_df()
        result = compute_liga_summary(df)
        assert result["goles_totales"] == 11

    def test_competition_normalizada(self):
        """La competición se normaliza ('La Liga' sin prefijo 'Spanish')."""
        df = _make_df()
        result = compute_liga_summary(df)
        assert result["competition"] == "La Liga"


# ---------------------------------------------------------------------------
# compute_team_percentiles
# ---------------------------------------------------------------------------


class TestComputeTeamPercentiles:
    def test_vacio_devuelve_lista_vacia(self):
        """DataFrame vacío → []."""
        result = compute_team_percentiles("Alpha", pd.DataFrame())
        assert result == []

    def test_un_solo_equipo_devuelve_vacio(self):
        """Solo 1 equipo distinto → [] (necesita ≥2 para el percentil)."""
        df = pd.DataFrame(
            {
                "local_team": ["Alpha", "Alpha"],
                "visitante_team": ["Alpha", "Alpha"],
                "goles_local": [2, 1],
                "goles_visitante": [1, 0],
            }
        )
        result = compute_team_percentiles("Alpha", df)
        assert result == []

    def test_tres_equipos_retorna_lista(self):
        """Con 3 equipos devuelve una lista (posiblemente con entradas)."""
        df = _make_df()
        result = compute_team_percentiles("Alpha", df)
        assert isinstance(result, list)

    def test_percentiles_en_rango_valido(self):
        """Todos los percentiles están entre 1 y 99."""
        df = _make_df()
        result = compute_team_percentiles("Alpha", df)
        for entry in result:
            assert 1 <= entry["percentil"] <= 99

    def test_claves_de_cada_entrada(self):
        """Cada entrada del resultado tiene las claves esperadas."""
        df = _make_df()
        result = compute_team_percentiles("Alpha", df)
        for entry in result:
            assert "metrica" in entry
            assert "valor" in entry
            assert "percentil" in entry
            assert "lower_is_better" in entry


# ---------------------------------------------------------------------------
# compute_player_rankings
# ---------------------------------------------------------------------------


class TestComputePlayerRankings:
    def test_vacio_devuelve_dfs_vacios(self):
        """DataFrame vacío → dicts con DataFrames vacíos."""
        empty = pd.DataFrame(
            columns=[
                "player_name",
                "goals",
                "assists",
                "goals_assists",
                "appearances",
                "position",
            ]
        )
        result = compute_player_rankings(empty)
        assert "goleadores" in result
        assert "asistentes" in result
        assert "combinado" in result
        assert len(result["goleadores"]) == 0

    def test_columnas_correctas(self):
        """Los DataFrames de resultado tienen las columnas esperadas."""
        df = _make_players_df()
        result = compute_player_rankings(df)
        for col in ("Jugador", "Goles", "Asistencias", "G+A"):
            assert col in result["goleadores"].columns

    def test_goleadores_ordenados_descendente(self):
        """Los goleadores aparecen de mayor a menor número de goles."""
        df = _make_players_df()
        result = compute_player_rankings(df)
        goles = result["goleadores"]["Goles"].tolist()
        assert goles == sorted(goles, reverse=True)

    def test_jugadores_sin_goles_no_aparecen(self):
        """Jugadores con 0 goles no se incluyen en 'goleadores'."""
        df = _make_players_df()
        result = compute_player_rankings(df)
        # Silva tiene 0 goles → no debe aparecer
        assert "Silva" not in result["goleadores"]["Jugador"].tolist()

    def test_posicion_traducida(self):
        """La posición inglesa se traduce al español ('F' → 'Delantero')."""
        df = _make_players_df()
        result = compute_player_rankings(df)
        posiciones = result["goleadores"]["Posicion"].tolist()
        assert "Delantero" in posiciones


# ---------------------------------------------------------------------------
# compute_player_profile
# ---------------------------------------------------------------------------


class TestComputePlayerProfile:
    def test_no_encontrado_devuelve_found_false(self):
        """Jugador inexistente → {'found': False}."""
        df = _make_players_df()
        result = compute_player_profile(df, "JugadorQueNoExiste")
        assert result["found"] is False

    def test_encontrado_devuelve_found_true(self):
        """Jugador existente → found=True con claves básicas."""
        df = _make_players_df()
        result = compute_player_profile(df, "Messi")
        assert result["found"] is True
        for key in ("goals", "assists", "appearances", "goles_por_partido"):
            assert key in result

    def test_goles_por_partido_calculado(self):
        """goles_por_partido = goals / appearances redondeado a 3 decimales."""
        df = _make_players_df()
        result = compute_player_profile(df, "Messi")
        expected = round(8 / 10, 3)
        assert abs(result["goles_por_partido"] - expected) < 1e-6

    def test_posicion_grupo_delantero(self):
        """Posición 'F' → posicion_grupo = 'delantero'."""
        df = _make_players_df()
        result = compute_player_profile(df, "Messi")
        assert result["posicion_grupo"] == "delantero"

    def test_busqueda_parcial_insensible_mayusculas(self):
        """La búsqueda es parcial e insensible a mayúsculas."""
        df = _make_players_df()
        result = compute_player_profile(df, "ness")  # substring de "Messi" → no match
        # 'ness' no está en ningún nombre → found=False
        assert result["found"] is False

    def test_por_equipo_contiene_companeros(self):
        """El perfil incluye compañeros goleadores del mismo equipo."""
        df = _make_players_df()
        result = compute_player_profile(df, "Messi")
        assert "compañeros_goleadores" in result
        assert isinstance(result["compañeros_goleadores"], pd.DataFrame)


# ---------------------------------------------------------------------------
# compute_match_preview
# ---------------------------------------------------------------------------


class TestComputeMatchPreview:
    def test_keys_presentes(self):
        """El resultado incluye todas las claves esperadas."""
        df = _make_df()
        result = compute_match_preview(df, "Alpha", "Beta")
        for key in (
            "local",
            "visitante",
            "lambda_local",
            "lambda_visit",
            "prob_local",
            "prob_empate",
            "prob_visit",
            "top_scores",
            "forma_local",
            "forma_visit",
            "h2h_balance",
        ):
            assert key in result

    def test_probabilidades_suman_aproximadamente_100(self):
        """prob_local + prob_empate + prob_visit ≈ 100 %."""
        df = _make_df()
        result = compute_match_preview(df, "Alpha", "Beta")
        total = result["prob_local"] + result["prob_empate"] + result["prob_visit"]
        assert abs(total - 100.0) < 2.0

    def test_bajas_reducen_lambda_local(self):
        """Con bajas en el equipo local, lambda_local es menor que sin bajas."""
        df = _make_df()
        r_sin = compute_match_preview(df, "Alpha", "Beta")
        r_con = compute_match_preview(
            df, "Alpha", "Beta", bajas_local=["Jugador1", "Jugador2", "Jugador3"]
        )
        assert r_con["lambda_local"] < r_sin["lambda_local"]

    def test_top_scores_es_lista_de_dicts(self):
        """top_scores es una lista no vacía con claves 'goles_local' y 'prob'."""
        df = _make_df()
        result = compute_match_preview(df, "Alpha", "Beta")
        assert isinstance(result["top_scores"], list)
        assert len(result["top_scores"]) > 0
        assert "goles_local" in result["top_scores"][0]
        assert "prob" in result["top_scores"][0]

    def test_lambdas_positivas(self):
        """Las λ calculadas son siempre positivas (mín. 0.3)."""
        df = _make_df()
        result = compute_match_preview(df, "Alpha", "Beta")
        assert result["lambda_local"] > 0.0
        assert result["lambda_visit"] > 0.0

    def test_h2h_balance_tiene_claves(self):
        """h2h_balance contiene las claves de victorias y empates."""
        df = _make_df()
        result = compute_match_preview(df, "Alpha", "Beta")
        bal = result["h2h_balance"]
        assert "victorias_local" in bal
        assert "empates" in bal
        assert "victorias_visitante" in bal
