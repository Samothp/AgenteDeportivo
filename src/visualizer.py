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


def plot_attendance(df: pd.DataFrame, output_path: str) -> Optional[str]:
    if 'espectadores' not in df or df['espectadores'].isna().all():
        return None
    data = df[['date', 'local_team', 'visitante_team', 'espectadores']].dropna(subset=['espectadores']).copy()
    if data.empty:
        return None
    data = data.sort_values('date').reset_index(drop=True)
    data['match_label'] = data['local_team'].str[:3] + ' vs ' + data['visitante_team'].str[:3]

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.bar(range(len(data)), data['espectadores'], color='#2e86de')
    ax.set_title('Asistencia por partido')
    ax.set_ylabel('Espectadores')
    ax.set_xlabel('Partido')
    if len(data) <= 20:
        ax.set_xticks(range(len(data)))
        ax.set_xticklabels(data['match_label'], rotation=45, ha='right', fontsize=8)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{int(x):,}'))
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    return output_path


def plot_xg_per_match(df: pd.DataFrame, output_path: str) -> Optional[str]:
    if 'xg_local' not in df.columns or 'xg_visitante' not in df.columns:
        return None
    data = df[['date', 'local_team', 'visitante_team', 'xg_local', 'xg_visitante']].dropna(subset=['xg_local', 'xg_visitante']).copy()
    if data.empty:
        return None

    data = data.sort_values('date').reset_index(drop=True)
    x = list(range(len(data)))

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(12, 5))
    width = 0.4
    ax.bar([i - width / 2 for i in x], data['xg_local'], width=width, label='xG Local', color='#2e86de')
    ax.bar([i + width / 2 for i in x], data['xg_visitante'], width=width, label='xG Visitante', color='#e74c3c')
    ax.set_title('Goles esperados (xG) por partido')
    ax.set_ylabel('xG')
    ax.set_xlabel('Partido')
    ax.legend()
    if len(data) <= 20:
        labels = [f"{r['local_team'][:4]} vs {r['visitante_team'][:4]}" for _, r in data.iterrows()]
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=45, ha='right', fontsize=7)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    return output_path


def plot_shots_comparison(df: pd.DataFrame, output_path: str) -> Optional[str]:
    cols = ['shots_local', 'shots_on_target_local', 'shots_visitante', 'shots_on_target_visitante']
    if not all(c in df.columns for c in cols):
        return None
    data = df[cols].dropna()
    if data.empty:
        return None

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    categories = ['Tiros totales\nLocal', 'Tiros a puerta\nLocal', 'Tiros totales\nVisitante', 'Tiros a puerta\nVisitante']
    values = [
        data['shots_local'].mean(), data['shots_on_target_local'].mean(),
        data['shots_visitante'].mean(), data['shots_on_target_visitante'].mean(),
    ]
    colors = ['#2e86de', '#54a0ff', '#e74c3c', '#ff6b6b']

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(categories, values, color=colors)
    ax.set_title('Tiros promedio por partido (local vs visitante)')
    ax.set_ylabel('Promedio de tiros')
    for i, v in enumerate(values):
        ax.text(i, v + 0.1, f'{v:.1f}', ha='center', fontsize=9)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    return output_path
