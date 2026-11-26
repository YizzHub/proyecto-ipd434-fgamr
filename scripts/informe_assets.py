"""Figuras y tablas compactas del informe IEEE a partir de los resultados del modo completo.

Uso:  python scripts/informe_assets.py      (requiere results/raw_logs/ del modo completo; < 1 min)
Salida: report_ieee/figs/*.pdf y report_ieee/tablas/*.tex
"""
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from src import plots                                                   # noqa: E402
from src.metrics_stats import por_semilla, comparar                    # noqa: E402
from src.proposed_method import FIS1, FIS2                             # noqa: E402
from src.reporting import preparar                                      # noqa: E402

FIGS, TABS = RAIZ / 'report_ieee' / 'figs', RAIZ / 'report_ieee' / 'tablas'
ESC = ['Oxford · β=5%', 'Oxford · β=55%', 'Chinanet · β=5%', 'Chinanet · β=55%']
ESC_TEX = {'Oxford · β=5%': r'Oxford, $\beta{=}5\%$', 'Oxford · β=55%': r'Oxford, $\beta{=}55\%$',
           'Chinanet · β=5%': r'Chinanet, $\beta{=}5\%$', 'Chinanet · β=55%': r'Chinanet, $\beta{=}55\%$'}
EVO = ['NSGA-II', 'GAMR', 'F-GAMR (FIS-1)', 'F-GAMR (FIS-2)', 'F-GAMR']
TODOS = ['MH', 'QoS-Dijkstra'] + EVO
NOMBRE_TEX = {'F-GAMR (FIS-1)': 'solo FIS-1', 'F-GAMR (FIS-2)': 'solo FIS-2', 'F-GAMR': r'\textbf{F-GAMR}',
              'QoS-Dijkstra': 'QoS-Dijkstra'}
CORTO = {'Oxford · β=5%': 'Ox 5%', 'Oxford · β=55%': 'Ox 55%', 'Chinanet · β=5%': 'Ch 5%', 'Chinanet · β=55%': 'Ch 55%'}


def estilo():
    plots.estilo()
    plt.rcParams.update({'font.size': 7, 'axes.titlesize': 7.5, 'xtick.labelsize': 6.5, 'ytick.labelsize': 6.5,
                         'legend.fontsize': 6, 'axes.labelsize': 7, 'lines.linewidth': 1.3})


# =========================================================================== figuras
def fig_fis():
    fig, axes = plt.subplots(1, 2, figsize=(3.5, 1.3), gridspec_kw=dict(wspace=0.45))
    paneles = [(FIS1, 'retardo', 'carga', 'deseabilidad', {'progreso': 1.0, 'perdida': 0.2},
                '(a) FIS-1: deseabilidad $w$', 'retardo $d_e$', 'carga $c_e$'),
               (FIS2, 'delay', 'perdida', 'aptitud', {}, '(b) FIS-2: aptitud', r'retardo $\hat{\mathcal{D}}$',
                r'pérdida $\hat{\mathcal{L}}$')]
    for ax, (sis, x, y, s, fijas, tit, xl, yl) in zip(axes, paneles):
        X, Y, Z = sis.superficie(x, y, s, fijas, puntos=61)
        cs = ax.contourf(X, Y, Z, levels=np.linspace(0, 1, 11), cmap='Blues')
        ax.contour(X, Y, Z, levels=[0.25, 0.5, 0.75], colors='white', linewidths=0.5)
        ax.set_title(tit)
        ax.set_xlabel(xl, labelpad=1)
        ax.set_ylabel(yl, labelpad=1)
        ax.grid(False)
    fig.colorbar(cs, ax=axes, fraction=0.04, pad=0.02, ticks=[0, 0.5, 1])
    fig.savefig(FIGS / 'fis.pdf', bbox_inches='tight')
    plt.close(fig)


def fig_e1(e1):
    evo = e1[e1.algoritmo.isin(EVO)]
    fig, axes = plt.subplots(1, 3, figsize=(7.16, 1.3))
    for ax, (m, tit) in zip(axes, [('HV', 'HV $\\uparrow$'), ('IGD', 'IGD $\\downarrow$'),
                                    ('tiempo_s', 'tiempo por instancia [s] $\\downarrow$')]):
        pos, datos, cols = [], [], []
        for i, esc in enumerate(ESC):
            for k, a in enumerate(EVO):
                pos.append(i * (len(EVO) + 1.2) + k)
                datos.append(evo[(evo.esc == esc) & (evo.algoritmo == a)][m].values)
                cols.append(plots.COLORES[a])
        bp = ax.boxplot(datos, positions=pos, widths=0.75, patch_artist=True, showfliers=False,
                        medianprops=dict(color='#d62728', lw=0.9), whiskerprops=dict(lw=0.6),
                        capprops=dict(lw=0.6), boxprops=dict(lw=0.5))
        for c, col in zip(bp['boxes'], cols):
            c.set_facecolor(col)
        ax.set_xticks([i * (len(EVO) + 1.2) + 2 for i in range(len(ESC))], [CORTO[e] for e in ESC])
        ax.set_title(tit)
    h = [plt.Rectangle((0, 0), 1, 1, fc=plots.COLORES[a]) for a in EVO]
    fig.legend(h, ['NSGA-II', 'GAMR', 'solo FIS-1', 'solo FIS-2', 'F-GAMR'], ncol=5, loc='upper center',
               bbox_to_anchor=(0.5, 1.07), frameon=False)
    fig.tight_layout(w_pad=0.8)
    fig.savefig(FIGS / 'e1_moo.pdf', bbox_inches='tight')
    plt.close(fig)


def fig_resultados(S, sel_w):
    e2, e3 = S['E2'], S['E3'].copy()
    e3['beta_pct'] = (100 * e3.beta).round().astype(int)
    fig, axes = plt.subplots(1, 4, figsize=(7.16, 1.5))

    def lineas(ax, d, x, m, algs, tit, xl, logx=False):
        for a in algs:
            g = d[d.algoritmo == a].groupby(x)[m]
            ax.errorbar(g.mean().index, g.mean().values, yerr=g.std().values, marker='o', ms=2.5, capsize=1.5,
                        lw=1.1, elinewidth=0.5, alpha=0.9, color=plots.COLORES[a] if a != 'MH' else '#9aa7b8',
                        label=a)
        ax.set_title(tit)
        ax.set_xlabel(xl, labelpad=1)
        if logx:
            ax.set_xscale('log')
            ax.set_xticks([10, 20, 50, 100], ['10', '20', '50', '100'])
            ax.minorticks_off()

    lineas(axes[0], e2, 'n_r', 'delay_ms', ['MH', 'QoS-Dijkstra', 'GAMR', 'F-GAMR'], '(a) E2: retardo [ms]',
           'solicitudes $N_r$', True)
    lineas(axes[1], e2, 'n_r', 'loss_pct', ['MH', 'QoS-Dijkstra', 'GAMR', 'F-GAMR'], '(b) E2: pérdida [%]',
           'solicitudes $N_r$', True)
    lineas(axes[2], e3, 'beta_pct', 'loss_pct', ['MH', 'LCP-WAC*', 'GAMR', 'F-GAMR'], '(c) E3: pérdida [%]',
           'desorden $\\beta$ [%]')
    axes[2].set_xticks([0, 5, 20, 55])
    hs, ls = [], []
    for ax in axes[:3]:
        for h, l in zip(*ax.get_legend_handles_labels()):
            if l not in ls:
                hs.append(h)
                ls.append(l)

    ax = axes[3]
    marcas = {'Mínimo delay': ('^', '#7a8699'), 'Punto rodilla': ('D', '#4f8fe8'), 'FIS-2': ('*', '#0b2545')}
    for nombre, (mk, col) in marcas.items():
        d = sel_w[sel_w.algoritmo == nombre]
        x = -d[d.metrica == 'delay_ms'].set_index('esc').mejora_pct
        y = -d[d.metrica == 'loss_pct'].set_index('esc').mejora_pct.reindex(x.index)
        ax.scatter(x, y, marker=mk, s=40 if mk == '*' else 16, color=col, label=nombre, zorder=3)
    ax.axhline(0, color='#888', lw=0.6)
    ax.axvline(0, color='#888', lw=0.6)
    ax.set_title('(d) criterio de selección (E1)')
    ax.set_xlabel('Δ retardo [%]', labelpad=1)
    ax.set_ylabel('Δ pérdida [%]', labelpad=1)
    for h, l in zip(*ax.get_legend_handles_labels()):
        hs.append(h)
        ls.append(l)
    fig.legend(hs, ls, ncol=8, loc='upper center', bbox_to_anchor=(0.5, 1.09), frameon=False, handlelength=1.2,
               columnspacing=0.9)
    fig.tight_layout(w_pad=0.6)
    fig.savefig(FIGS / 'resultados.pdf', bbox_inches='tight')
    plt.close(fig)


# =========================================================================== tablas
def _celda(med, std, dec, negrita, daga):
    txt = f'{med:.{dec}f}{{\\tiny$\\pm${std:.{dec}f}}}'
    if negrita:
        txt = rf'\textbf{{{med:.{dec}f}}}{{\tiny$\pm${std:.{dec}f}}}'
    return txt + (r'$^\dagger$' if daga else '')


def tabla_ancha(e1, algs, metricas, nombres, caption, label):
    """Filas: algoritmos. Columnas: escenario × métrica. Negrita = mejor; † = p<0.05 vs GAMR (Wilcoxon)."""
    g = e1.groupby(['esc', 'algoritmo'])
    med, std = g[[m for m, *_ in metricas]].mean(), g[[m for m, *_ in metricas]].std()
    pv = {}
    for m, _, _, sentido in metricas:
        c = comparar(e1[e1.algoritmo.isin(algs)], m, 'GAMR', ['esc'], sentido == 'max')
        for _, r in c.iterrows():
            pv[(r.esc, r.algoritmo, m)] = r.p_valor
    nm = len(metricas)
    L = [r'\begin{table*}[!t]', r'\centering', rf'\caption{{{caption}}}', rf'\label{{{label}}}', r'\scriptsize',
         r'\setlength{\tabcolsep}{2.2pt}', r'\begin{tabular}{l' + ('|' + 'c' * nm) * len(ESC) + '}', r'\toprule',
         ' & ' + ' & '.join(rf'\multicolumn{{{nm}}}{{c{"|" if i < len(ESC) - 1 else ""}}}{{{ESC_TEX[e]}}}'
                           for i, e in enumerate(ESC)) + r' \\',
         'Algoritmo & ' + ' & '.join([n for _, n, _, _ in metricas] * len(ESC)) + r' \\', r'\midrule']
    for a in algs:
        celdas = [NOMBRE_TEX.get(a, a)]
        for e in ESC:
            for m, _, dec, sentido in metricas:
                vals = med.loc[e][m].reindex(algs)
                mejor = vals.idxmax() if sentido == 'max' else vals.idxmin()
                p = pv.get((e, a, m), np.nan)
                celdas.append(_celda(med.loc[(e, a), m], std.loc[(e, a), m], dec, a == mejor, p < 0.05))
        L.append(' & '.join(celdas) + r' \\')
        if a in ('QoS-Dijkstra', 'GAMR'):
            L.append(r'\midrule')
    L += [r'\bottomrule', r'\end{tabular}', r'\end{table*}']
    return '\n'.join(L)


def main():
    FIGS.mkdir(parents=True, exist_ok=True)
    TABS.mkdir(parents=True, exist_ok=True)
    estilo()
    crudos = RAIZ / 'results' / 'raw_logs'
    df = pd.read_csv(crudos / 'resultados_algoritmos.csv')
    df_sel = pd.read_csv(crudos / 'resultados_selectores.csv')
    S = preparar(df)
    e1 = S['E1']
    ss = por_semilla(df_sel.rename(columns={'selector': 'algoritmo'}), ['delay_ms', 'loss_pct'], ['topologia', 'beta'])
    ss['esc'] = ss.topologia + ' · β=' + (100 * ss.beta).round().astype(int).astype(str) + '%'
    sel_w = pd.concat([comparar(ss, m, 'Menor solapamiento (GAMR)', ['esc']) for m in ('delay_ms', 'loss_pct')])

    fig_fis()
    fig_e1(e1)
    fig_resultados(S, sel_w)
    (TABS / 'e1_moo.tex').write_text(tabla_ancha(
        e1, EVO, [('HV', 'HV', 3, 'max'), ('IGD', 'IGD', 3, 'min'), ('tiempo_s', 't [s]', 2, 'min')],
        None, r'E1 --- Calidad del frente de Pareto y tiempo de c\'omputo por instancia ($N_s{=}2$, $N_r{=}50$; '
              r'media$\pm$desv.\ est.\ sobre 30 semillas). HV$\uparrow$, IGD$\downarrow$, t$\downarrow$. '
              r'\textbf{Negrita}: mejor; $^\dagger$: diferencia con GAMR significativa (Wilcoxon pareado, $p<0.05$).',
        'tab:e1moo'), encoding='utf-8')
    (TABS / 'e1_qos.tex').write_text(tabla_ancha(
        e1, TODOS, [('delay_ms', r'Ret.\,[ms]', 1, 'min'), ('loss_pct', r"P\'erd.\,[\%]", 2, 'min'),
                    ('rho_max_pct', r'$\rho_{\max}$[\%]', 1, 'min')],
        None, r'E1 --- QoS medida en el estado realizado de la red $\Delta^{t+1}$ (media$\pm$desv.\ est., 30 semillas; '
              r'todas las m\'etricas $\downarrow$). \textbf{Negrita}: mejor; $^\dagger$: $p<0.05$ frente a GAMR.',
        'tab:e1qos'), encoding='utf-8')
    print('Listo:', sorted(p.name for p in FIGS.iterdir()), sorted(p.name for p in TABS.iterdir()))


if __name__ == '__main__':
    main()
