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

        for ax, (label, serie, color) in zip(axes, plots):
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
    ax.xaxis.set_major_locator(FixedLocator(xticks))
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
    norm_l = list(norm_l) + [norm_l[0]]
    norm_v = list(norm_v) + [norm_v[0]]

    angles = np.linspace(0, 2 * np.pi, len(selected), endpoint=False).tolist()
    angles += angles[:1]

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw={'polar': True})

    ax.plot(angles, norm_l, 'o-', linewidth=2, color='#2e86de', label=local)
    ax.fill(angles, norm_l, alpha=0.2, color='#2e86de')
    ax.plot(angles, norm_v, 'o-', linewidth=2, color='#e74c3c', label=visitante)
    ax.fill(angles, norm_v, alpha=0.2, color='#e74c3c')

    ax.set_thetagrids(np.degrees(angles[:-1]), selected, fontsize=8)
    ax.set_ylim(0, 1)
    ax.set_yticklabels([])
    ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1), fontsize=9)
    ax.set_title('Comparativa métricas clave', fontsize=11, pad=15)

    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    return output_path
