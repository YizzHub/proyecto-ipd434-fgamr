"""Herramientas multi-objetivo (dominancia, crowding, HV, IGD) y estadística para comparar algoritmos.

HV exacto 3D y IGD siguen las Ec. 16–17 de Tran et al. (2025). Para comparar algoritmos en una misma
instancia, los frentes se normalizan en conjunto (ideal/nadir de la unión) y r_ref = (1, 1, 1).
"""
import numpy as np
import pandas as pd
from scipy.stats import wilcoxon


# --------------------------------------------------------------------------- dominancia
def ordenamiento_no_dominado(F, cv=None):
    """Fast non-dominated sorting (Deb et al., 2002) con dominancia con restricciones. Devuelve lista de frentes."""
    F = np.asarray(F, dtype=float)
    n = len(F)
    cv = np.zeros(n) if cv is None else np.asarray(cv, dtype=float)
    pareto = np.all(F[:, None, :] <= F[None, :, :], axis=2) & np.any(F[:, None, :] < F[None, :, :], axis=2)
    fa = cv <= 0
    D = ((fa[:, None] & ~fa[None, :])
         | (~fa[:, None] & ~fa[None, :] & (cv[:, None] < cv[None, :]))
         | (fa[:, None] & fa[None, :] & pareto))
    n_dom = D.sum(axis=0)
    asignado = np.zeros(n, dtype=bool)
    frentes = []
    actual = np.flatnonzero(n_dom == 0)
    while len(actual):
        frentes.append(actual)
        asignado[actual] = True
        n_dom = n_dom - D[actual].sum(axis=0)
        actual = np.flatnonzero((n_dom == 0) & ~asignado)
    return frentes


def distancia_aglomeracion(F):
    """Crowding distance (Ec. 12)."""
    F = np.asarray(F, dtype=float)
    n, m = F.shape
    d = np.zeros(n)
    if n <= 2:
        d[:] = np.inf
        return d
    for j in range(m):
        o = np.argsort(F[:, j], kind='stable')
        fmin, fmax = F[o[0], j], F[o[-1], j]
        d[o[0]] = d[o[-1]] = np.inf
        if fmax > fmin:
            d[o[1:-1]] += (F[o[2:], j] - F[o[:-2], j]) / (fmax - fmin)
    return d


def no_dominados(F):
    F = np.unique(np.asarray(F, dtype=float), axis=0)
    return F[ordenamiento_no_dominado(F)[0]]


# --------------------------------------------------------------------------- indicadores
def hipervolumen(F, ref=(1.0, 1.0, 1.0)):
    """Hipervolumen exacto 3D (minimización): barrido en f3 + área 2D exacta (Ec. 16)."""
    F = np.asarray(F, dtype=float)
    ref = np.asarray(ref, dtype=float)
    F = F[np.all(F < ref, axis=1)]
    if len(F) == 0:
        return 0.0
    F = no_dominados(F)
    F = F[np.argsort(F[:, 2])]
    vol = 0.0
    for i in range(len(F)):
        z_sig = F[i + 1, 2] if i + 1 < len(F) else ref[2]
        h = z_sig - F[i, 2]
        if h <= 0:
            continue
        S = F[:i + 1, :2]
        o = np.argsort(S[:, 0])
        x = S[o, 0]
        y = np.minimum.accumulate(S[o, 1])
        x_sig = np.append(x[1:], ref[0])
        vol += h * np.sum((x_sig - x) * (ref[1] - y))
    return float(vol)


def igd(F_ref, F_aprox):
    """Inverted Generational Distance (Ec. 17)."""
    F_ref, F_aprox = np.asarray(F_ref, float), np.asarray(F_aprox, float)
    d = np.sqrt(((F_ref[:, None, :] - F_aprox[None, :, :]) ** 2).sum(axis=2)).min(axis=1)
    return float(d.mean())


def metricas_conjuntas(frentes):
    """{algoritmo: frente (k×3)} de una MISMA instancia → {algoritmo: (HV, IGD)} con normalización conjunta."""
    U = np.vstack(list(frentes.values()))
    ideal, nadir = U.min(axis=0), U.max(axis=0)
    rango = np.where(nadir - ideal > 1e-12, nadir - ideal, 1.0)
    norm = lambda A: (np.asarray(A) - ideal) / (1.1 * rango)
    F_star = no_dominados(norm(U))
    return {k: (hipervolumen(norm(A)), igd(F_star, norm(A))) for k, A in frentes.items()}


# --------------------------------------------------------------------------- estadística
def por_semilla(df, metricas, claves, desde_intervalo=2):
    """Promedia cada semilla sobre sus intervalos con memoria activa (t ≥ desde_intervalo).

    Cada semilla es una secuencia dinámica independiente → una observación por semilla y algoritmo.
    """
    d = df[df.intervalo >= desde_intervalo]
    return d.groupby(claves + ['algoritmo', 'semilla'], as_index=False)[metricas].mean()


def comparar(df_sem, metrica, referencia, claves, mayor_es_mejor=False):
    """Wilcoxon pareado (por semilla) de cada algoritmo contra `referencia` dentro de cada grupo de `claves`."""
    filas = []
    for grupo, d in df_sem.groupby(claves):
        grupo = grupo if isinstance(grupo, tuple) else (grupo,)
        piv = d.pivot_table(index='semilla', columns='algoritmo', values=metrica)
        if referencia not in piv:
            continue
        for alg in piv.columns:
            if alg == referencia:
                continue
            a, b = piv[alg].dropna(), piv[referencia].dropna()
            idx = a.index.intersection(b.index)
            a, b = a[idx], b[idx]
            dif = a - b
            p = wilcoxon(a, b).pvalue if len(idx) >= 6 and np.any(dif != 0) else np.nan
            mejora = (a.mean() - b.mean()) / abs(b.mean()) * 100 if b.mean() != 0 else np.nan
            filas.append(dict(zip(claves, grupo), algoritmo=alg, referencia=referencia, metrica=metrica,
                              media_alg=a.mean(), media_ref=b.mean(),
                              mejora_pct=mejora if mayor_es_mejor else -mejora,
                              gana=bool((a.mean() > b.mean()) if mayor_es_mejor else (a.mean() < b.mean())),
                              p_valor=p, n=len(idx)))
    return pd.DataFrame(filas)


def tabla_media_std(df_sem, metricas, claves, orden_alg, decimales=None):
    """Tabla 'media ± std' (filas: grupo × algoritmo)."""
    decimales = decimales or {}
    g = df_sem.groupby(claves + ['algoritmo'])[metricas]
    media, std = g.mean(), g.std()
    out = pd.DataFrame(index=media.index)
    for m in metricas:
        k = decimales.get(m, 3)
        out[m] = [f'{a:.{k}f} ± {b:.{k}f}' for a, b in zip(media[m], std[m])]
    out = out.reset_index()
    out['algoritmo'] = pd.Categorical(out['algoritmo'], orden_alg, ordered=True)
    return out.sort_values(claves + ['algoritmo']).set_index(claves + ['algoritmo'])


def tabla_latex(df_sem, metricas, claves, orden_alg, sentido, referencia, nombres=None, decimales=None, caption='',
                label=''):
    """Tabla IEEE: media ± std, mejor en negrita y † si difiere de `referencia` con p < 0.05 (Wilcoxon)."""
    nombres = nombres or {}
    decimales = decimales or {}
    g = df_sem.groupby(claves + ['algoritmo'])[metricas]
    media, std = g.mean(), g.std()
    pvals = {}
    for m in metricas:
        c = comparar(df_sem, m, referencia, claves, mayor_es_mejor=sentido[m] == 'max')
        for _, r in c.iterrows():
            pvals[(tuple(r[k] for k in claves), r['algoritmo'], m)] = r['p_valor']
    cols = 'l' * (len(claves) + 1) + 'c' * len(metricas)
    lineas = [r'\begin{table}[t]', r'\centering', r'\scriptsize', rf'\caption{{{caption}}}', rf'\label{{{label}}}',
              r'\setlength{\tabcolsep}{2.5pt}', rf'\begin{{tabular}}{{{cols}}}', r'\toprule',
              ' & '.join([k.replace('_', r'\_') for k in claves] + ['Alg.'] +
                         [nombres.get(m, m) for m in metricas]) + r' \\', r'\midrule']
    for grupo, _ in df_sem.groupby(claves):
        grupo = grupo if isinstance(grupo, tuple) else (grupo,)
        mejores = {}
        for m in metricas:
            vals = {a: media.loc[grupo + (a,), m] for a in orden_alg if grupo + (a,) in media.index}
            mejores[m] = (max if sentido[m] == 'max' else min)(vals, key=vals.get)
        primera = True
        for a in orden_alg:
            if grupo + (a,) not in media.index:
                continue
            celdas = [str(x) if primera else '' for x in grupo] + [a]
            for m in metricas:
                k = decimales.get(m, 3)
                txt = f'{media.loc[grupo + (a,), m]:.{k}f}$\\pm${std.loc[grupo + (a,), m]:.{k}f}'
                if mejores[m] == a:
                    txt = rf'\textbf{{{txt}}}'
                p = pvals.get((grupo, a, m))
                if p is not None and not np.isnan(p) and p < 0.05:
                    txt += r'$^\dagger$'
                celdas.append(txt)
            lineas.append(' & '.join(celdas) + r' \\')
            primera = False
        lineas.append(r'\midrule')
    lineas[-1] = r'\bottomrule'
    lineas += [r'\end{tabular}', r'\end{table}']
    return '\n'.join(lineas)
