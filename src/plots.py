"""Figuras de publicación (paleta azul consistente con la presentación)."""
import matplotlib
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np

COLORES = {'MH': '#d9dde3', 'QoS-Dijkstra': '#aab4c3', 'LCP-WAC*': '#7a8699',
           'NSGA-II': '#c6dbf5', 'GAMR': '#8fb8ea', 'F-GAMR (FIS-1)': '#4f8fe8', 'F-GAMR (FIS-2)': '#2f6fd0',
           'F-GAMR': '#0b2545'}
CORTO = {'QoS-Dijkstra': 'QoS-Dijk.', 'F-GAMR (FIS-1)': 'solo FIS-1', 'F-GAMR (FIS-2)': 'solo FIS-2'}


def estilo():
    plt.rcParams.update({'figure.dpi': 100, 'savefig.dpi': 300, 'axes.grid': True, 'grid.alpha': 0.3,
                         'font.size': 9, 'axes.titlesize': 9, 'axes.titleweight': 'bold', 'axes.spines.top': False,
                         'axes.spines.right': False, 'legend.fontsize': 7, 'legend.frameon': False})


def guardar(fig, carpeta, nombre):
    carpeta.mkdir(parents=True, exist_ok=True)
    fig.savefig(carpeta / f'{nombre}.pdf', bbox_inches='tight')
    fig.savefig(carpeta / f'{nombre}.png', bbox_inches='tight')


# --------------------------------------------------------------------------- sistemas difusos
def fig_pertenencia(sistema, variables=None, ncols=3):
    vars_ = {**sistema.entradas, **sistema.salidas}
    variables = variables or list(vars_)
    nfil = int(np.ceil(len(variables) / ncols))
    fig, axes = plt.subplots(nfil, ncols, figsize=(3.2 * ncols, 2.0 * nfil), squeeze=False)
    tonos = ['#c6dbf5', '#8fb8ea', '#4f8fe8', '#1565d8', '#0b2545']
    for ax, nombre in zip(axes.flat, variables):
        v = vars_[nombre]
        for k, (t, y) in enumerate(v.curvas().items()):
            ax.plot(v.x, y, lw=2, color=tonos[min(k * max(1, 4 // max(1, len(v.terminos) - 1)), 4)], label=t)
            ax.fill_between(v.x, y, alpha=0.08, color=tonos[min(k * 2, 4)])
        ax.set_title(nombre + (' (salida)' if nombre in sistema.salidas else ''))
        ax.set_ylim(0, 1.05)
        ax.legend(loc='upper center', ncol=len(v.terminos), bbox_to_anchor=(0.5, -0.18))
    for ax in list(axes.flat)[len(variables):]:
        ax.axis('off')
    fig.tight_layout()
    return fig


def fig_superficies(paneles):
    """paneles: lista de (sistema, var_x, var_y, salida, fijas, titulo)."""
    fig = plt.figure(figsize=(4.2 * len(paneles), 3.4))
    for k, (sis, x, y, s, fijas, titulo) in enumerate(paneles, start=1):
        ax = fig.add_subplot(1, len(paneles), k, projection='3d')
        X, Y, Z = sis.superficie(x, y, s, fijas)
        ax.plot_surface(X, Y, Z, cmap='Blues', edgecolor='none', alpha=0.95)
        ax.set_xlabel(x, fontsize=7)
        ax.set_ylabel(y, fontsize=7)
        ax.set_zlabel(s, fontsize=7)
        ax.tick_params(labelsize=6)
        ax.set_title(titulo, fontsize=8)
        ax.view_init(28, -130)
    fig.tight_layout()
    return fig


def fig_guia(red, guia, servidor, pos, titulo=''):
    """Deseabilidad de FIS-1 de cada movimiento hacia `servidor` dibujada sobre la topología."""
    fig, ax = plt.subplots(figsize=(6, 4.2))
    Gs = red.G.subgraph(red.switches)
    nx.draw_networkx_edges(Gs, pos, ax=ax, edge_color='#e3e8ef', width=6)
    cmap = matplotlib.colormaps['Blues']
    for u in red.switches:
        cands, _, w = guia[(u, servidor)]
        for v, wv in zip(cands, w):
            if v in pos:
                ax.annotate('', xy=pos[v], xytext=pos[u],
                            arrowprops=dict(arrowstyle='-|>', color=cmap(0.25 + 0.75 * wv), lw=0.6 + 3 * wv,
                                            shrinkA=7, shrinkB=7, connectionstyle='arc3,rad=0.12'))
    sw_srv = red.adj[servidor][0]
    nx.draw_networkx_nodes(Gs, pos, ax=ax, node_size=110, node_color='#8fb8ea')
    nx.draw_networkx_nodes(Gs, pos, nodelist=[sw_srv], ax=ax, node_size=320, node_color='#d62728', node_shape='*')
    nx.draw_networkx_labels(Gs, pos, ax=ax, font_size=5)
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(0, 1))
    fig.colorbar(sm, ax=ax, fraction=0.04, label='deseabilidad w (FIS-1)')
    ax.set_title(titulo or f'Guía difusa hacia {servidor} (★)')
    ax.axis('off')
    return fig


# --------------------------------------------------------------------------- resultados
def fig_cajas(df_sem, metricas, titulos, filas, columnas, orden, mejor=None):
    """Boxplots por semilla: una fila por métrica y una columna por escenario (columnas = valores de 'esc')."""
    fig, axes = plt.subplots(len(metricas), len(columnas), figsize=(2.6 * len(columnas), 2.1 * len(metricas)),
                             squeeze=False, sharey='row')
    for i, (m, tit) in enumerate(zip(metricas, titulos)):
        for j, esc in enumerate(columnas):
            ax = axes[i, j]
            d = df_sem[df_sem.esc == esc]
            algs = [a for a in orden if a in set(d.algoritmo)]
            datos = [d[d.algoritmo == a][m].values for a in algs]
            bp = ax.boxplot(datos, patch_artist=True, widths=0.6, showfliers=False,
                            medianprops=dict(color='#d62728', lw=1.2))
            for caja, a in zip(bp['boxes'], algs):
                caja.set_facecolor(COLORES[a])
            ax.set_xticks(range(1, len(algs) + 1), [CORTO.get(a, a) for a in algs], rotation=35, ha='right', fontsize=6.5)
            if i == 0:
                ax.set_title(esc)
            if j == 0:
                ax.set_ylabel(tit)
    fig.tight_layout()
    return fig


def _corto_esc(esc):
    topo, beta = esc.split(' · ')
    return f"{topo[:2]}·{beta.replace('β=', 'β ')}"


def fig_barras(df_sem, metricas, titulos, columnas, orden):
    """Barras media ± std por escenario."""
    fig, axes = plt.subplots(1, len(metricas), figsize=(4.3 * len(metricas), 2.7), squeeze=False)
    for ax, m, tit in zip(axes[0], metricas, titulos):
        x = np.arange(len(columnas))
        algs = [a for a in orden if a in set(df_sem.algoritmo)]
        ancho = 0.85 / len(algs)
        for k, a in enumerate(algs):
            g = df_sem[df_sem.algoritmo == a].groupby('esc')[m]
            med, std = g.mean().reindex(columnas), g.std().reindex(columnas)
            ax.bar(x + (k - (len(algs) - 1) / 2) * ancho, med, ancho, yerr=std, capsize=1.2, color=COLORES[a],
                   edgecolor='white', lw=0.3, label=a, error_kw=dict(lw=0.5, ecolor='#555'))
        ax.set_xticks(x, [_corto_esc(c) for c in columnas], fontsize=7)
        ax.set_title(tit)
        lo = df_sem.groupby(['esc', 'algoritmo'])[m].mean().min()
        ax.set_ylim(bottom=max(0, lo * 0.8))
    fig.legend(*axes[0, 0].get_legend_handles_labels(), ncol=len(orden), loc='upper center',
               bbox_to_anchor=(0.5, 1.06), fontsize=7)
    fig.tight_layout()
    return fig


def fig_lineas(df_sem, x, metricas, titulos, orden, etiqueta_x, log_x=False):
    fig, axes = plt.subplots(1, len(metricas), figsize=(3.2 * len(metricas), 2.5), squeeze=False)
    for ax, m, tit in zip(axes[0], metricas, titulos):
        for a in [a for a in orden if a in set(df_sem.algoritmo)]:
            g = df_sem[df_sem.algoritmo == a].groupby(x)[m]
            med, std = g.mean(), g.std()
            ax.errorbar(med.index, med.values, yerr=std.values, marker='o', ms=4, capsize=2, lw=1.6,
                        color=COLORES[a] if a != 'MH' else '#9aa7b8', label=a)
        ax.set_xlabel(etiqueta_x)
        ax.set_title(tit)
        if log_x:
            ax.set_xscale('log')
            ax.set_xticks(sorted(df_sem[x].unique()), [str(v) for v in sorted(df_sem[x].unique())])
    axes[0, 0].legend()
    fig.tight_layout()
    return fig


def fig_convergencia(resultados, titulo=''):
    """resultados: {nombre: dict de resolver()} de una misma instancia con escala común."""
    fig, ax = plt.subplots(figsize=(4.6, 2.8))
    for nombre, r in resultados.items():
        ax.plot(r['hv_hist'], color=COLORES.get(nombre, '#333'), lw=1.8, label=f"{nombre} (G={r['generaciones']}, "
                                                                                f"{r['tiempo']:.1f} s)")
        ax.axvline(r['generaciones'], color=COLORES.get(nombre, '#333'), ls=':', lw=1)
    ax.set_xlabel('generación G')
    ax.set_ylabel('$HV_G$ (escala común)')
    ax.set_title(titulo)
    ax.legend()
    fig.tight_layout()
    return fig


def fig_frente_seleccion(F, elegidos, titulo=''):
    """Frente (retardo vs pérdida) y la solución que instala cada criterio."""
    fig, ax = plt.subplots(figsize=(4.4, 3.0))
    ax.scatter(F[:, 0], 100 * F[:, 1], s=14, color='#c6dbf5', edgecolor='#8fb8ea', label='frente F¹ (GAMR)')
    marcas = {'Menor solapamiento (GAMR)': ('s', '#8fb8ea'), 'Mínimo delay': ('^', '#7a8699'),
              'Punto rodilla': ('D', '#4f8fe8'), 'FIS-2': ('*', '#0b2545')}
    for nombre, i in elegidos.items():
        m, c = marcas.get(nombre, ('o', 'k'))
        ax.scatter(F[i, 0], 100 * F[i, 1], s=120 if m == '*' else 50, marker=m, color=c, edgecolor='white', zorder=3,
                   label=nombre)
    ax.set_xlabel('retardo medio planificado [ms]')
    ax.set_ylabel('pérdida media planificada [%]')
    ax.set_title(titulo)
    ax.legend(fontsize=6.5)
    fig.tight_layout()
    return fig
