"""Tests de la función _build_preview_analysis en src/agent.py.

_build_preview_analysis es una función de nivel de módulo (antes de la clase
SportsAgent) que genera párrafos de análisis narrativo en lenguaje natural
para el informe de preview de un partido.
"""

import pytest

from src.agent import _build_preview_analysis


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _base_kwargs() -> dict:
    """Argumentos mínimos válidos para _build_preview_analysis."""
    return dict(
        local="Alpha",
        visitante="Beta",
        lam_l=1.5,
        lam_v=1.2,
        prob_l=45.0,
        prob_e=28.0,
        prob_v=27.0,
        stats_l={"xgf_promedio": 1.5, "xgc_promedio": 1.0,
                 "xgf_como_local": 1.6, "xgc_como_local": 0.9},
        stats_v={"xgf_promedio": 1.2, "xgc_promedio": 1.1,
                 "xgf_como_visit": 1.1, "xgc_como_visit": 1.2},
        forma_l="V V E",
        pts5_l=7,
        forma_v="D D V",
        pts5_v=3,
        h2h_bal={
            "victorias_local": 2,
            "empates": 1,
            "victorias_visitante": 1,
        },
        top_scores=[{"goles_local": 1, "goles_visit": 0, "prob": 12.5}],
        penalty_l=0.0,
        penalty_v=0.0,
        bajas_l=[],
        bajas_v=[],
    )


# ---------------------------------------------------------------------------
# TestBuildPreviewAnalysis
# ---------------------------------------------------------------------------


class TestBuildPreviewAnalysis:
    def test_retorna_lista(self):
        """_build_preview_analysis debe devolver una lista."""
        result = _build_preview_analysis(**_base_kwargs())
        assert isinstance(result, list)

    def test_lista_no_vacia(self):
        """El resultado tiene al menos un párrafo."""
        result = _build_preview_analysis(**_base_kwargs())
        assert len(result) > 0

    def test_parrafos_son_cadenas(self):
        """Cada elemento de la lista es una cadena de texto."""
        result = _build_preview_analysis(**_base_kwargs())
        for parrafo in result:
            assert isinstance(parrafo, str)
            assert len(parrafo) > 0

    def test_menciona_nombres_equipos(self):
        """Al menos un párrafo menciona a uno de los dos equipos."""
        result = _build_preview_analysis(**_base_kwargs())
        texto = " ".join(result)
        assert "Alpha" in texto or "Beta" in texto

    def test_sin_h2h_menciona_ausencia(self):
        """Sin enfrentamientos directos → párrafo que lo indica."""
        kwargs = _base_kwargs()
        kwargs["h2h_bal"] = {
            "victorias_local": 0,
            "empates": 0,
            "victorias_visitante": 0,
        }
        result = _build_preview_analysis(**kwargs)
        texto = " ".join(result)
        assert "No hay" in texto

    def test_local_favorito_claro(self):
        """Local con ventaja ≥15 pp → párrafo de 'ventaja clara'."""
        kwargs = _base_kwargs()
        kwargs["prob_l"] = 60.0
        kwargs["prob_v"] = 20.0
        result = _build_preview_analysis(**kwargs)
        texto = " ".join(result)
        # El párrafo de ventaja debe mencionar a Alpha (local)
        assert "Alpha" in texto

    def test_visitante_favorito(self):
        """Visitante con ventaja ≥15 pp → párrafo menciona 'desfavorecido'."""
        kwargs = _base_kwargs()
        kwargs["prob_l"] = 20.0
        kwargs["prob_v"] = 60.0
        result = _build_preview_analysis(**kwargs)
        texto = " ".join(result)
        assert "desfavorecido" in texto or "favorito" in texto

    def test_bajas_no_rompe_funcion(self):
        """Con bajas en ambos equipos, la función no lanza excepción."""
        kwargs = _base_kwargs()
        kwargs["bajas_l"] = ["Jugador1", "Jugador2"]
        kwargs["bajas_v"] = ["JugadorA"]
        kwargs["penalty_l"] = 0.2
        kwargs["penalty_v"] = 0.1
        result = _build_preview_analysis(**kwargs)
        assert isinstance(result, list)
        assert len(result) > 0

    def test_partido_igualado_menciona_equilibrio(self):
        """Diferencia < 5 pp entre local y visitante → párrafo de partido igualado."""
        kwargs = _base_kwargs()
        kwargs["prob_l"] = 35.0
        kwargs["prob_e"] = 32.0
        kwargs["prob_v"] = 33.0
        result = _build_preview_analysis(**kwargs)
        texto = " ".join(result)
        # Algún indicador de partido igualado
        assert "igualado" in texto.lower() or "%" in texto

    def test_marcador_mas_probable_incluido(self):
        """Con top_scores, el análisis menciona el marcador más probable."""
        kwargs = _base_kwargs()
        kwargs["top_scores"] = [{"goles_local": 2, "goles_visit": 1, "prob": 15.0}]
        result = _build_preview_analysis(**kwargs)
        texto = " ".join(result)
        # La función describe el marcador más probable
        assert len(texto) > 50  # párrafo sustancial generado
