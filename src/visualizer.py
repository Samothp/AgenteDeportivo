from pathlib import Path
from typing import Optional
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
import pandas as pd


# ---------------------------------------------------------------------------
# Punto 15 — Tema de gráficos (claro / oscuro)
# ---------------------------------------------------------------------------

def set_chart_theme(dark: bool = False) -> None:
    """Aplica el estilo de matplotlib y seaborn según el tema del dashboard.

    Llamar una vez al arrancar la app antes de generar cualquier gráfico.
    Los colores base se ajustan para que los gráficos sean coherentes con el
    fondo del dashboard (blanco en modo claro, gris oscuro en modo oscuro).

    Args:
        dark: True para activar el estilo oscuro, False para el claro (defecto).
    """
    if dark:
        plt.style.use("dark_background")
        sns.set(style="darkgrid", palette="muted")
    else:
        plt.style.use("default")
        sns.set(style="whitegrid")


set_chart_theme(dark=False)


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


def plot_temporal_evolution(df: pd.DataFrame, team: Optional[str], output_path: str) -> Optional[str]:
    """Gráfico de línea con la evolución de métricas clave partido a partido.

    Muestra goles, xG y tiros a puerta del equipo a lo largo de la temporada,
    ordenado por jornada (si está disponible) o por fecha.
    En modo multi-temporada (columna 'season' presente), traza una línea por
    temporada con color/trazo distinto.
    Solo se genera cuando se analiza un equipo concreto.
    """
    if team is None:
        return None

    data = df.copy()
    team_lower = team.strip().lower()
    multi_season = 'season' in data.columns and data['season'].nunique() > 1

    # Elegir eje X
    if 'jornada' in data.columns and data['jornada'].notna().any():
        x_col = 'jornada'
        x_label = 'Jornada'
    elif 'date' in data.columns:
        x_col = 'date'
        x_label = 'Fecha'
    else:
        return None

    def _extract(subset: pd.DataFrame):
        """Extrae métricas desde la perspectiva del equipo (local o visitante)."""
        is_h = subset['local_team'].str.lower().str.contains(team_lower, na=False)

        def _col(col_h: str, col_a: str) -> pd.Series:
            if col_h not in subset.columns:
                return pd.Series([None] * len(subset), index=subset.index, dtype=float)
            result = subset[col_a].copy().astype(float)
            result[is_h] = subset.loc[is_h, col_h].astype(float)
            return result

        return (
            _col('goles_local', 'goles_visitante'),
            _col('xg_local', 'xg_visitante'),
            _col('shots_on_target_local', 'shots_on_target_visitante'),
        )

    # Determinar qué métricas hay disponibles (sobre todos los datos)
    all_g, all_xg, all_sot = _extract(data)
    if all_g.isna().all():
        return None

    metrics_cfg = [('Goles', '#2ecc71')]
    if all_xg.notna().any():
        metrics_cfg.append(('xG', '#9b59b6'))
    if all_sot.notna().any():
        metrics_cfg.append(('Tiros a puerta', '#e67e22'))

    nrows = len(metrics_cfg)
    n_per_season = len(data) // (data['season'].nunique() if multi_season else 1)
    fig_width = max(12, n_per_season * 0.4)
    fig, axes = plt.subplots(nrows=nrows, ncols=1, figsize=(fig_width, 3.5 * nrows), sharex=True)
    if nrows == 1:
        axes = [axes]

    title_team = team.title()
    title_suffix = ' (multi-temporada)' if multi_season else ''
    fig.suptitle(f'Evolución por jornada — {title_team}{title_suffix}', fontsize=13, fontweight='bold', y=1.01)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    if multi_season:
        season_list = sorted(data['season'].unique())
        palette = [plt.get_cmap('tab10')(i % 10) for i in range(len(season_list))]
        linestyles = ['-', '--', '-.', ':'] * 3

        for ax, (label, _) in zip(axes, metrics_cfg):
            ax.set_ylabel(label)
            ax.grid(True, alpha=0.3)
            for i, season in enumerate(season_list):
                s_data = data[data['season'] == season].sort_values(x_col).reset_index(drop=True)
                s_g, s_xg, s_sot = _extract(s_data)
                serie = s_g if label == 'Goles' else (s_xg if label == 'xG' else s_sot)
                x_vals = s_data[x_col]
                color = palette[i]
                ls = linestyles[i]
                ax.plot(x_vals, serie, marker='o', linewidth=2, color=color,
                        markersize=5, label=str(season), linestyle=ls)
                valid = serie.dropna()
                if not valid.empty:
                    ax.axhline(valid.mean(), linestyle=':', linewidth=1, color=color, alpha=0.5)
            ax.legend(fontsize=8, loc='upper left', title='Temporada')

        if x_col == 'jornada':
            all_x = sorted(data[x_col].dropna().unique())
            if len(all_x) <= 38:
                axes[-1].set_xticks(all_x)
                axes[-1].set_xticklabels([str(int(v)) for v in all_x], fontsize=8)
    else:
        data = data.sort_values(x_col).reset_index(drop=True)
        x_values = data[x_col]
        num_matches = len(data)
        goles, xg, shots_ot = _extract(data)

        plots = [('Goles', goles, '#2ecc71')]
        if xg.notna().any():
            plots.append(('xG', xg, '#9b59b6'))
        if shots_ot.notna().any():
            plots.append(('Tiros a puerta', shots_ot, '#e67e22'))

        for ax, (label, serie, color) in zip(axes, plots):  # type: ignore[assignment]
            valid = serie.dropna()
            if valid.empty:
                continue
            ax.plot(x_values, serie, marker='o', linewidth=2, color=color, markersize=5, label=label)
            ax.axhline(valid.mean(), linestyle='--', linewidth=1, color=color, alpha=0.5, label=f'Media {valid.mean():.1f}')
            ax.fill_between(x_values, serie.fillna(0), alpha=0.08, color=color)
            ax.set_ylabel(label)
            ax.legend(fontsize=8, loc='upper left')
            ax.grid(True, alpha=0.3)
            if num_matches <= 38 and x_col == 'jornada':
                ax.set_xticks(x_values)
                ax.set_xticklabels([str(int(v)) if pd.notna(v) else '' for v in x_values], fontsize=8)

    axes[-1].set_xlabel(x_label)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    return output_path


def plot_matchday_goals(df: pd.DataFrame, output_path: str) -> Optional[str]:
    """Barras apiladas con los goles local y visitante de cada partido de la jornada."""
    if df.empty:
        return None
    needed = ['local_team', 'visitante_team', 'goles_local', 'goles_visitante']
    if not all(c in df.columns for c in needed):
        return None

    data = df[needed].copy().reset_index(drop=True)
    data['match_label'] = data['local_team'].str[:12] + '\nvs\n' + data['visitante_team'].str[:12]

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(max(8, len(data) * 1.3), 5))
    x = range(len(data))
    ax.bar(x, data['goles_local'], label='Local', color='#2e86de', alpha=0.85)
    ax.bar(x, data['goles_visitante'], bottom=data['goles_local'],
           label='Visitante', color='#e74c3c', alpha=0.85)
    for i, row in data.iterrows():
        total = row['goles_local'] + row['goles_visitante']
        ax.text(i, total + 0.05, str(int(total)), ha='center', va='bottom', fontsize=9, fontweight='bold')
    ax.set_xticks(list(x))
    ax.set_xticklabels(data['match_label'], fontsize=7)
    ax.set_ylabel('Goles')
    ax.set_title('Goles por partido')
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    return output_path


def plot_matchday_xg(df: pd.DataFrame, output_path: str) -> Optional[str]:
    """Barras agrupadas con xG local vs visitante por partido de la jornada."""
    if 'xg_local' not in df.columns or df['xg_local'].isna().all():
        return None
    needed = ['local_team', 'visitante_team', 'xg_local', 'xg_visitante']
    data = df[needed].dropna(subset=['xg_local', 'xg_visitante']).copy().reset_index(drop=True)
    if data.empty:
        return None

    data['match_label'] = data['local_team'].str[:12] + '\nvs\n' + data['visitante_team'].str[:12]

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    x = list(range(len(data)))
    width = 0.4
    fig, ax = plt.subplots(figsize=(max(8, len(data) * 1.3), 5))
    ax.bar([i - width / 2 for i in x], data['xg_local'],
           width=width, label='xG Local', color='#2e86de', alpha=0.85)
    ax.bar([i + width / 2 for i in x], data['xg_visitante'],
           width=width, label='xG Visitante', color='#e74c3c', alpha=0.85)
    ax.set_xticks(x)
    ax.set_xticklabels(data['match_label'], fontsize=7)
    ax.set_ylabel('xG')
    ax.set_title('Goles esperados (xG) por partido de la jornada')
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    return output_path


def plot_match_stats_bar(stats: list, local: str, visitante: str, output_path: str) -> Optional[str]:
    """Barras horizontales enfrentadas al estilo TV (local izquierda, visitante derecha)."""
    import numpy as np

    # Filtrar solo stats numéricas y que ambos tengan valor
    rows = [s for s in stats if s['local'] != '-' and s['visitante'] != '-']
    if not rows:
        return None

    labels   = [r['stat'] for r in rows]
    vals_l   = [float(r['local'])    for r in rows]
    vals_v   = [float(r['visitante']) for r in rows]
    ventajas = [r['ventaja']         for r in rows]

    n = len(labels)
    y = np.arange(n)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(10, max(4, n * 0.45)))

    bar_l = ax.barh(y,  vals_l,  align='center', color='#2e86de', alpha=0.85, label=local)
    bar_v = ax.barh(y, [-v for v in vals_v], align='center', color='#e74c3c', alpha=0.85, label=visitante)

    # Etiquetas de valor
    for i, (vl, vv) in enumerate(zip(vals_l, vals_v)):
        ax.text( vl + max(vals_l) * 0.02, i,  f'{vl:.0f}', va='center', ha='left',  fontsize=8)
        ax.text(-vv - max(vals_v) * 0.02, i,  f'{vv:.0f}', va='center', ha='right', fontsize=8)

    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=8)
    ax.axvline(0, color='black', linewidth=0.8)
    ax.set_xlabel('')
    ax.set_title(f'Estadísticas del partido\n{local}  vs  {visitante}', fontsize=11)

    # Ocultar ticks negativos en el eje X (usando FixedLocator para evitar warning)
    from matplotlib.ticker import FixedLocator, FixedFormatter
    xticks = ax.get_xticks()
    ax.xaxis.set_major_locator(FixedLocator(list(xticks)))
    ax.xaxis.set_major_formatter(FixedFormatter([str(abs(int(t))) for t in xticks]))
    ax.tick_params(axis='x', labelsize=7)

    ax.legend(loc='lower right', fontsize=8)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    return output_path


def plot_match_radar(stats: list, local: str, visitante: str, output_path: str) -> Optional[str]:
    """Radar chart (spider) comparando local vs visitante en métricas clave."""
    import numpy as np

    # Métricas para el radar (máximo 8, ambos deben tener valor)
    RADAR_STATS = [
        'Tiros a puerta', 'xG', 'Posesión %', 'Corners',
        'Precisión pases %', 'Paradas portero',
    ]
    rows = {r['stat']: r for r in stats if r['local'] != '-' and r['visitante'] != '-'}
    selected = [s for s in RADAR_STATS if s in rows]
    if len(selected) < 3:
        return None

    vals_l = [float(rows[s]['local'])    for s in selected]
    vals_v = [float(rows[s]['visitante']) for s in selected]

    # Normalizar 0-1 por stat
    def _norm(vl, vv):
        total = vl + vv
        if total == 0:
            return 0.5, 0.5
        return vl / total, vv / total

    norm_l, norm_v = zip(*[_norm(vl, vv) for vl, vv in zip(vals_l, vals_v)])
    norm_l = list(norm_l) + [norm_l[0]]  # type: ignore[assignment]
    norm_v = list(norm_v) + [norm_v[0]]  # type: ignore[assignment]

    angles = np.linspace(0, 2 * np.pi, len(selected), endpoint=False).tolist()
    angles += angles[:1]

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw={'polar': True})

    ax.plot(angles, norm_l, 'o-', linewidth=2, color='#2e86de', label=local)
    ax.fill(angles, norm_l, alpha=0.2, color='#2e86de')
    ax.plot(angles, norm_v, 'o-', linewidth=2, color='#e74c3c', label=visitante)
    ax.fill(angles, norm_v, alpha=0.2, color='#e74c3c')

    ax.set_thetagrids(np.degrees(angles[:-1]), selected, fontsize=8)  # type: ignore[attr-defined]
    ax.set_ylim(0, 1)
    ax.set_yticklabels([])
    ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1), fontsize=9)
    ax.set_title('Comparativa métricas clave', fontsize=11, pad=15)

    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    return output_path


def plot_league_table(clasificacion: pd.DataFrame, output_path: str) -> Optional[str]:
    """Tabla de clasificación: barras horizontales de puntos por equipo."""
    if clasificacion is None or clasificacion.empty:
        return None
    df = clasificacion.sort_values('PTS', ascending=True)
    fig, ax = plt.subplots(figsize=(8, max(5, len(df) * 0.38)))
    colors = ['#1f77b4' if i >= len(df) - 4 else '#aec7e8' for i in range(len(df))]
    bars = ax.barh(df['Equipo'], df['PTS'], color=colors, edgecolor='white')
    for bar, pts in zip(bars, df['PTS']):
        ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height() / 2,
                str(int(pts)), va='center', fontsize=8)
    ax.set_xlabel('Puntos')
    ax.set_title('Clasificación', fontsize=12)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    return output_path


def plot_goals_per_team(clasificacion: pd.DataFrame, output_path: str) -> Optional[str]:
    """Goles a favor y en contra por equipo (barras agrupadas)."""
    if clasificacion is None or clasificacion.empty:
        return None
    df = clasificacion.sort_values('GF', ascending=True)
    x = range(len(df))
    width = 0.4
    fig, ax = plt.subplots(figsize=(10, max(5, len(df) * 0.4)))
    ax.barh([i + width / 2 for i in x], df['GF'], width, label='Goles a favor', color='#2ecc71')
    ax.barh([i - width / 2 for i in x], df['GC'], width, label='Goles en contra', color='#e74c3c')
    ax.set_yticks(list(x))
    ax.set_yticklabels(df['Equipo'], fontsize=8)
    ax.set_xlabel('Goles')
    ax.set_title('Goles a favor y en contra por equipo', fontsize=12)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    return output_path


def plot_xg_per_team(stats_df: pd.DataFrame, output_path: str) -> Optional[str]:
    """xG medio por partido por equipo."""
    if stats_df is None or stats_df.empty or 'xG' not in stats_df.columns:
        return None
    df = stats_df.dropna(subset=['xG']).sort_values('xG', ascending=True)
    if df.empty:
        return None
    fig, ax = plt.subplots(figsize=(8, max(5, len(df) * 0.38)))
    ax.barh(df['Equipo'], df['xG'], color='#9b59b6', edgecolor='white')
    for i, v in enumerate(df['xG']):
        ax.text(v + 0.01, i, f'{v:.2f}', va='center', fontsize=7)
    ax.set_xlabel('xG medio por partido')
    ax.set_title('Expected Goals (xG) medio por partido', fontsize=12)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    return output_path


def plot_home_away_performance(home_away: pd.DataFrame, output_path: str) -> Optional[str]:
    """Puntos local vs visitante por equipo (barras agrupadas)."""
    if home_away is None or home_away.empty:
        return None
    df = home_away.sort_values('Pts_L', ascending=True)
    x = range(len(df))
    width = 0.4
    fig, ax = plt.subplots(figsize=(10, max(5, len(df) * 0.4)))
    ax.barh([i + width / 2 for i in x], df['Pts_L'], width, label='Puntos como local', color='#3498db')
    ax.barh([i - width / 2 for i in x], df['Pts_V'], width, label='Puntos como visitante', color='#e67e22')
    ax.set_yticks(list(x))
    ax.set_yticklabels(df['Equipo'], fontsize=8)
    ax.set_xlabel('Puntos')
    ax.set_title('Rendimiento local vs visitante', fontsize=12)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    return output_path


def plot_player_bar(profile: dict, output_path: str) -> Optional[str]:
    """Barras comparativas: stats del jugador vs media del equipo (top 5)."""
    comp_df = profile.get('compañeros_goleadores')
    if comp_df is None or comp_df.empty:
        return None
    pj = profile['appearances']
    if pj == 0:
        return None

    player = profile['player_name']
    metrics_labels = ['Goles/PJ', 'Asist/PJ', 'G+A/PJ', 'Tiros/PJ']
    player_vals = [
        profile['goles_por_partido'],
        profile['asistencias_por_partido'],
        profile['ga_por_partido'],
        round(profile['shots_on_target'] / pj, 3),
    ]
    team_pj_mean = max(float(comp_df['PJ'].mean()), 1)
    team_vals = [
        round(float(comp_df['Goles'].mean()) / team_pj_mean, 3),
        round(float(comp_df['Asistencias'].mean()) / team_pj_mean, 3),
        round((float(comp_df['Goles'].mean()) + float(comp_df['Asistencias'].mean())) / team_pj_mean, 3),
        0,
    ]

    x = np.arange(len(metrics_labels))
    width = 0.35
    fig, ax = plt.subplots(figsize=(8, 5))
    bars1 = ax.bar(x - width / 2, player_vals, width, label=player, color='#1f77b4')
    ax.bar(x + width / 2, team_vals, width, label='Media equipo (top 5)', color='#aec7e8')
    for bar in bars1:
        h = bar.get_height()
        if h > 0:
            ax.text(bar.get_x() + bar.get_width() / 2, h + 0.005, f'{h:.2f}', ha='center', va='bottom', fontsize=8)
    ax.set_xticks(x)
    ax.set_xticklabels(metrics_labels, fontsize=9)
    ax.set_ylabel('Por partido')
    ax.set_title(f'{player} — estadísticas por partido vs equipo', fontsize=11)
    ax.legend(fontsize=9)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    return output_path


def plot_player_radar(profile: dict, output_path: str) -> Optional[str]:
    """Radar chart con métricas del jugador normalizadas vs el equipo."""
    comp_df = profile.get('compañeros_goleadores')
    if comp_df is None or comp_df.empty:
        return None
    pj = profile['appearances']
    if pj == 0:
        return None

    player = profile['player_name']
    metrics = ['Goles', 'Asistencias', 'G+A', 'Tiros\na puerta', '% partidos\ncon gol']
    player_vals_raw = [
        float(profile['goals']),
        float(profile['assists']),
        float(profile['ga']),
        float(profile['shots_on_target']),
        float(profile['pct_partidos_con_gol']),
    ]
    team_maxes = [
        max(float(comp_df['Goles'].max()), 1),
        max(float(comp_df['Asistencias'].max()), 1),
        max(float((comp_df['Goles'] + comp_df['Asistencias']).max()), 1),
        max(float(comp_df['Goles'].max()), 1),
        100.0,
    ]
    norm = [min(v / m, 1.0) for v, m in zip(player_vals_raw, team_maxes)]

    N = len(metrics)
    angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
    norm_closed = norm + norm[:1]
    angles_closed = angles + angles[:1]

    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw={'projection': 'polar'})
    ax.plot(angles_closed, norm_closed, 'o-', linewidth=2, color='#1f77b4', label=player)
    ax.fill(angles_closed, norm_closed, alpha=0.25, color='#1f77b4')
    ax.set_thetagrids(np.degrees(angles), metrics, fontsize=9)  # type: ignore[attr-defined]
    ax.set_ylim(0, 1)
    ax.set_yticklabels([])
    ax.set_title(f'Perfil — {player}', fontsize=12, pad=20)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    return output_path


# ── Fase 3: nuevas visualizaciones ───────────────────────────────────────────

def plot_shot_funnel(df: pd.DataFrame, output_path: str, team: Optional[str] = None) -> Optional[str]:
    """Embudo tiros totales → tiros a puerta → goles (local + visitante)."""
    needed = ['shots_local', 'shots_on_target_local', 'goles_local',
              'shots_visitante', 'shots_on_target_visitante', 'goles_visitante']
    if not all(c in df.columns for c in needed):
        return None
    data = df[needed].dropna()
    if data.empty:
        return None

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    tiros_l  = data['shots_local'].mean()
    puerta_l = data['shots_on_target_local'].mean()
    goles_l  = data['goles_local'].mean()
    tiros_v  = data['shots_visitante'].mean()
    puerta_v = data['shots_on_target_visitante'].mean()
    goles_v  = data['goles_visitante'].mean()

    fig, axes = plt.subplots(1, 2, figsize=(11, 6))
    title_suffix = f' \u2014 {team}' if team else ''
    fig.suptitle(f'Embudo de conversi\u00f3n{title_suffix}', fontsize=13, fontweight='bold')

    def _funnel(ax, vals, labels, colors, title):
        max_v = max(vals)
        for i, (v, lbl, c) in enumerate(zip(vals, labels, colors)):
            width = v / max_v
            left = (1 - width) / 2
            ax.barh(i, width, left=left, color=c, height=0.55)
            ax.text(0.5, i, f'{lbl}  {v:.1f}', ha='center', va='center',
                    fontsize=10, fontweight='bold', color='white')
        ax.set_xlim(0, 1)
        ax.set_ylim(-0.5, len(vals) - 0.5)
        ax.invert_yaxis()  # Tiros arriba → Goles abajo
        ax.axis('off')
        ax.set_title(title, fontsize=11, pad=8)

    _funnel(axes[0], [tiros_l, puerta_l, goles_l],
            ['Tiros', 'A puerta', 'Goles'],
            ['#2e86de', '#54a0ff', '#1abc9c'], 'Local')
    _funnel(axes[1], [tiros_v, puerta_v, goles_v],
            ['Tiros', 'A puerta', 'Goles'],
            ['#e74c3c', '#ff6b6b', '#e67e22'], 'Visitante')

    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    return output_path


def plot_cumulative_points(df: pd.DataFrame, output_path: str, top_n: int = 5) -> Optional[str]:
    """Puntos acumulados por jornada para el top-N de equipos."""
    if 'jornada' not in df.columns:
        return None
    data = df.dropna(subset=['jornada', 'local_team', 'visitante_team',
                              'goles_local', 'goles_visitante'])
    if data.empty:
        return None

    jornadas = sorted(data['jornada'].unique())
    from src.analysis import compute_standings
    final_standings = compute_standings(data)
    if final_standings.empty:
        return None
    top_teams = final_standings['Equipo'].head(top_n).tolist()

    cumpts: dict = {t: [] for t in top_teams}
    for t in top_teams:
        acum = 0
        for j in jornadas:
            df_j = data[data['jornada'] == j]
            for _, r in df_j[df_j['local_team'] == t].iterrows():
                if r['goles_local'] > r['goles_visitante']:    acum += 3
                elif r['goles_local'] == r['goles_visitante']: acum += 1
            for _, r in df_j[df_j['visitante_team'] == t].iterrows():
                if r['goles_visitante'] > r['goles_local']:    acum += 3
                elif r['goles_visitante'] == r['goles_local']: acum += 1
            cumpts[t].append(acum)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    palette = sns.color_palette('tab10', top_n)
    fig, ax = plt.subplots(figsize=(12, 6))
    for (team_name, pts), color in zip(cumpts.items(), palette):
        ax.plot(jornadas, pts, marker='o', markersize=3, linewidth=2,
                label=team_name, color=color)
    ax.set_xlabel('Jornada')
    ax.set_ylabel('Puntos acumulados')
    ax.set_title(f'Puntos acumulados por jornada \u2014 Top {top_n}')
    ax.legend(loc='upper left', fontsize=8)
    ax.grid(True, alpha=0.4)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    return output_path


def plot_results_heatmap(df: pd.DataFrame, output_path: str) -> Optional[str]:
    """Matriz de calor de resultados (DIF media de goles) para todos los pares de equipos."""
    needed = ['local_team', 'visitante_team', 'goles_local', 'goles_visitante']
    if not all(c in df.columns for c in needed):
        return None
    data = df[needed].dropna()
    if data.empty:
        return None

    teams = sorted(set(data['local_team']) | set(data['visitante_team']))
    n = len(teams)
    matrix = pd.DataFrame(np.nan, index=teams, columns=teams)
    for _, row in data.iterrows():
        l, v = row['local_team'], row['visitante_team']
        diff = float(row['goles_local']) - float(row['goles_visitante'])
        if pd.isna(matrix.at[l, v]):
            matrix.at[l, v] = diff
        else:
            matrix.at[l, v] = (matrix.at[l, v] + diff) / 2

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    figsize = max(8, n * 0.55)
    fig, ax = plt.subplots(figsize=(figsize, figsize * 0.9))
    sns.heatmap(
        matrix.astype(float), annot=(n <= 20), fmt='.1f',
        cmap='RdYlGn', center=0, linewidths=0.5,
        ax=ax, cbar_kws={'label': 'DIF goles (local \u2212 visitante)'},
        annot_kws={'fontsize': 7},
    )
    ax.set_title('Mapa de calor de resultados\n(DIF media de goles como local)', fontsize=12)
    ax.set_xlabel('Visitante')
    ax.set_ylabel('Local')
    plt.xticks(rotation=45, ha='right', fontsize=7)
    plt.yticks(rotation=0, fontsize=7)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    return output_path


def plot_compare_radar(compare: dict, output_path: str) -> Optional[str]:
    """Radar comparativo entre dos equipos (6 métricas normalizadas 0-1)."""
    labels = compare.get('radar_labels', [])
    vals1  = compare.get('radar_vals1', [])
    vals2  = compare.get('radar_vals2', [])
    if not labels or not vals1 or not vals2:
        return None

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    N = len(labels)
    angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
    v1c = vals1 + vals1[:1]
    v2c = vals2 + vals2[:1]
    ac  = angles + angles[:1]

    fig, ax = plt.subplots(figsize=(7, 7), subplot_kw={'projection': 'polar'})
    ax.plot(ac, v1c, 'o-', linewidth=2, color='#2e86de', label=compare['team1'])
    ax.fill(ac, v1c, alpha=0.18, color='#2e86de')
    ax.plot(ac, v2c, 's-', linewidth=2, color='#e74c3c', label=compare['team2'])
    ax.fill(ac, v2c, alpha=0.18, color='#e74c3c')
    ax.set_thetagrids(np.degrees(angles), labels, fontsize=9)  # type: ignore[attr-defined]
    ax.set_ylim(0, 1)
    ax.set_yticklabels([])
    ax.legend(loc='upper right', bbox_to_anchor=(1.35, 1.1), fontsize=10)
    ax.set_title(f'{compare["team1"]}  vs  {compare["team2"]}', fontsize=12, pad=22)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    return output_path


def plot_multi_league_radar(
    leagues: list[dict],
    output_path: str,
) -> Optional[str]:
    """Radar superpuesto comparando medias de varias ligas.

    Args:
        leagues: Lista de dicts con claves ``label`` (nombre de la liga)
            y los valores numéricos de las métricas a comparar.
            Ejemplo::

                [
                    {"label": "La Liga 2024", "Goles/partido": 2.6, "xG/partido": 2.4, ...},
                    {"label": "Premier 2024", "Goles/partido": 2.9, ...},
                ]
        output_path: Ruta de salida de la imagen PNG.

    Returns:
        Ruta de la imagen generada, o None si hay menos de 2 ligas o métricas.
    """
    import numpy as np

    METRICS = ["Goles/partido", "xG/partido", "Posesión %", "Tiros/partido", "Corners/partido"]

    # Filtrar métricas presentes en todos los registros
    available = [m for m in METRICS if all(m in lg for lg in leagues)]
    if len(available) < 3 or len(leagues) < 2:
        return None

    # Normalizar por el máximo entre ligas (0-1)
    maxima = {m: max(lg[m] for lg in leagues) or 1 for m in available}

    angles = np.linspace(0, 2 * np.pi, len(available), endpoint=False).tolist()
    angles_closed = angles + angles[:1]

    palette = [plt.get_cmap('tab10')(i % 10) for i in range(len(leagues))]

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(7, 7), subplot_kw={'projection': 'polar'})

    for lg, color in zip(leagues, palette):
        vals = [lg[m] / maxima[m] for m in available]
        vals_closed = vals + vals[:1]
        ax.plot(angles_closed, vals_closed, 'o-', linewidth=2, color=color, label=lg['label'])
        ax.fill(angles_closed, vals_closed, alpha=0.12, color=color)

    ax.set_thetagrids(np.degrees(angles), available, fontsize=9)  # type: ignore[attr-defined]
    ax.set_ylim(0, 1)
    ax.set_yticklabels([])
    ax.legend(loc='upper right', bbox_to_anchor=(1.45, 1.15), fontsize=9)
    ax.set_title('Comparativa de ligas — medias', fontsize=12, pad=20)

    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    return output_path
