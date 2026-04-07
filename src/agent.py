from pathlib import Path
from typing import Optional

from src.data_loader import load_match_data, summarize_matches


class SportsAgent:
    def __init__(self, data_path: str):
        self.data_path = data_path
        self.data = None

    def load_data(self):
        self.data = load_match_data(self.data_path)
        return self.data

    def generate_summary(self):
        if self.data is None:
            raise ValueError('Datos no cargados. Ejecute load_data() primero.')
        return summarize_matches(self.data)

    def report(self, output_path: Optional[str] = None) -> str:
        summary = self.generate_summary()
        report_text = (
            f"Partidos analizados: {int(summary.loc[0, 'partidos'])}\n"
            f"Goles totales: {int(summary.loc[0, 'goles_totales'])}\n"
            f"Goles promedio por partido: {summary.loc[0, 'promedio_goles']:.2f}\n"
            f"Tarjetas amarillas: {int(summary.loc[0, 'tarjetas_amarillas'])}\n"
            f"Tarjetas rojas: {int(summary.loc[0, 'tarjetas_rojas'])}\n"
        )
        if output_path:
            Path(output_path).write_text(report_text, encoding='utf-8')
        return report_text
