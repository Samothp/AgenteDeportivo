from pathlib import Path
from typing import Optional
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd


sns.set(style='whitegrid')


def plot_goals_distribution(df: pd.DataFrame, output_path: str) -> str:
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(10, 5))
    sns.histplot(x=df['goles_totales'], bins=range(0, int(df['goles_totales'].max()) + 2), kde=False, ax=ax)
    ax.set_title('Distribución de goles por partido')
    ax.set_xlabel('Goles totales')
    ax.set_ylabel('Número de partidos')
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    return output_path


def plot_possession_distribution(df: pd.DataFrame, output_path: str) -> Optional[str]:
    if 'posesion_local' not in df or 'posesion_visitante' not in df:
        return None
    possession_df = df[['posesion_local', 'posesion_visitante']].dropna()
    if possession_df.empty:
        return None

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    melted = possession_df.melt(var_name='Equipo', value_name='Posesión')
    fig, ax = plt.subplots(figsize=(10, 5))
    sns.boxplot(x='Equipo', y='Posesión', data=melted, ax=ax)
    ax.set_title('Distribución de posesión local y visitante')
    ax.set_xlabel('Tipo de posesión')
    ax.set_ylabel('Porcentaje')
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    return output_path


def plot_card_statistics(df: pd.DataFrame, output_path: str) -> Optional[str]:
    if not all(col in df for col in ['amarillas_local', 'amarillas_visitante', 'rojas_local', 'rojas_visitante']):
        return None
    if df[['amarillas_local', 'amarillas_visitante', 'rojas_local', 'rojas_visitante']].isna().all().all():
        return None

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    cards = pd.DataFrame({
        'Tarjetas amarillas': df['amarillas_local'].sum(skipna=True) + df['amarillas_visitante'].sum(skipna=True),
        'Tarjetas rojas': df['rojas_local'].sum(skipna=True) + df['rojas_visitante'].sum(skipna=True),
    }, index=[0])
    fig, ax = plt.subplots(figsize=(8, 5))
    cards.T.plot(kind='bar', legend=False, ax=ax, color=['#f1c40f', '#e74c3c'])
    ax.set_title('Resumen de tarjetas en el dataset')
    ax.set_ylabel('Cantidad')
    ax.set_xticklabels(['Tarjetas amarillas', 'Tarjetas rojas'], rotation=0)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    return output_path
