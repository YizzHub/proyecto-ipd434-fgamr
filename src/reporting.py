"""Tablas (CSV + LaTeX), figuras y resumen numérico a partir de los resultados crudos."""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .experiments import ORDEN, EVOLUTIVOS, SELECTORES
from .metrics_stats import por_semilla, comparar, tabla_media_std, tabla_latex
from . import plots

MOO = ['HV', 'IGD', 'tiempo_s', 'generaciones']
QOS = ['delay_ms', 'loss_pct', 'rho_max_pct', 'satisf_bw_pct', 'enlaces_usados_pct']
SENTIDO = dict(HV='max', IGD='min', tiempo_s='min', generaciones='min', delay_ms='min', loss_pct='min',
               rho_max_pct='min', satisf_bw_pct='max', enlaces_usados_pct='max')
NOMBRES_TEX = dict(HV='HV $\\uparrow$', IGD='IGD $\\downarrow$', tiempo_s='Tiempo [s] $\\downarrow$',
                   delay_ms='Retardo [ms] $\\downarrow$', loss_pct='Pérdida [\\%] $\\downarrow$',
                   rho_max_pct='$\\rho_{\\max}$ [\\%] $\\downarrow$', satisf_bw_pct='Satisf. BW [\\%] $\\uparrow$')
DEC = dict(HV=3, IGD=3, tiempo_s=2, generaciones=1, delay_ms=1, loss_pct=2, rho_max_pct=1, satisf_bw_pct=1,
           enlaces_usados_pct=1)


def etiqueta_escenario(d):
    return d.topologia + ' · β=' + (100 * d.beta).round().astype(int).astype(str) + '%'


def preparar(df):
    """Promedio por semilla (t ≥ 2) de cada experimento, con columna 'esc' legible."""
    out = {}
    for exp, d in df.groupby('experimento'):
        metricas = [m for m in MOO + QOS + ['alpha', 'loss_plan_pct', 'delay_plan_ms', 'tam_frente'] if m in d]
        s = por_semilla(d, metricas, ['experimento', 'topologia', 'beta', 'n_s', 'n_r'])
        s['esc'] = etiqueta_escenario(s)
        out[exp] = s
    return out


def tabla_mejoras(df_sem, metricas, referencia, claves):
    filas = [comparar(df_sem, m, referencia, claves, SENTIDO[m] == 'max') for m in metricas]
    t = pd.concat(filas, ignore_index=True)
    t['significativo'] = t.p_valor < 0.05
    return t


def generar_reporte(df, df_sel, dir_tablas: Path, dir_figs: Path, verbose=True):
    """Genera todas las tablas y figuras del informe. Devuelve un dict con los DataFrames clave."""
    plots.estilo()
    dir_tablas.mkdir(parents=True, exist_ok=True)
    dir_figs.mkdir(parents=True, exist_ok=True)
    S = preparar(df)
    out = {'por_semilla': S}

    # ------------------------------------------------------------------ E1
    if 'E1' in S:
        e1 = S['E1']
        esc = sorted(e1.esc.unique(), key=lambda x: (x.split(' ')[0] != 'Oxford', x))
        evo = e1[e1.algoritmo.isin(EVOLUTIVOS)]
        t_moo = tabla_media_std(evo, ['HV', 'IGD', 'tiempo_s', 'generaciones'], ['esc'], ORDEN, DEC)
        t_qos = tabla_media_std(e1, ['delay_ms', 'loss_pct', 'rho_max_pct', 'satisf_bw_pct'], ['esc'], ORDEN, DEC)
        t_moo.to_csv(dir_tablas / 'E1_moo_media_std.csv', encoding='utf-8-sig')
        t_qos.to_csv(dir_tablas / 'E1_qos_media_std.csv', encoding='utf-8-sig')
        mej = pd.concat([tabla_mejoras(e1, MOO[:3] + ['delay_ms', 'loss_pct'], ref, ['esc'])
                         for ref in ('GAMR', 'NSGA-II', 'MH')], ignore_index=True)
        mej = mej[mej.algoritmo == 'F-GAMR'] if len(mej) else mej
        abl = tabla_mejoras(e1, MOO[:3] + ['delay_ms', 'loss_pct'], 'GAMR', ['esc'])
        mej.to_csv(dir_tablas / 'E1_wilcoxon_FGAMR_vs_bases.csv', index=False, encoding='utf-8-sig')
        abl.to_csv(dir_tablas / 'E1_wilcoxon_vs_GAMR_ablacion.csv', index=False, encoding='utf-8-sig')
        (dir_tablas / 'E1_moo.tex').write_text(tabla_latex(
            evo, ['HV', 'IGD', 'tiempo_s'], ['esc'], ORDEN, SENTIDO, 'GAMR', NOMBRES_TEX, DEC,
            caption='E1: calidad del frente y tiempo (media $\\pm$ std, 30 semillas). '
                    '$^\\dagger$: $p<0.05$ vs GAMR (Wilcoxon).', label='tab:e1moo'), encoding='utf-8')
        (dir_tablas / 'E1_qos.tex').write_text(tabla_latex(
            e1, ['delay_ms', 'loss_pct', 'rho_max_pct'], ['esc'], ORDEN, SENTIDO, 'GAMR', NOMBRES_TEX, DEC,
            caption='E1: QoS medida en el estado realizado (media $\\pm$ std, 30 semillas). '
                    '$^\\dagger$: $p<0.05$ vs GAMR (Wilcoxon).', label='tab:e1qos'), encoding='utf-8')
        out.update(E1_moo=t_moo, E1_qos=t_qos, E1_mejoras=mej, E1_ablacion=abl)

        f = plots.fig_cajas(evo, ['HV', 'IGD', 'tiempo_s'], ['HV ↑', 'IGD ↓', 'tiempo [s] ↓'], None, esc, ORDEN)
        plots.guardar(f, dir_figs, 'E1_cajas_moo')
        plt.close(f)
        f = plots.fig_barras(e1, ['delay_ms', 'loss_pct', 'rho_max_pct'],
                             ['retardo realizado [ms] ↓', 'pérdida realizada [%] ↓', 'utilización máx. [%] ↓'], esc, ORDEN)
        plots.guardar(f, dir_figs, 'E1_barras_qos')
        plt.close(f)

    # ------------------------------------------------------------------ selectores (E1, frentes de GAMR)
    if df_sel is not None and len(df_sel):
        ss = por_semilla(df_sel.rename(columns={'selector': 'algoritmo'}), ['delay_ms', 'loss_pct', 'rho_max_pct'],
                         ['topologia', 'beta'])
        ss['esc'] = etiqueta_escenario(ss)
        t_sel = tabla_media_std(ss, ['delay_ms', 'loss_pct', 'rho_max_pct'], ['esc'], SELECTORES, DEC)
        t_sel.to_csv(dir_tablas / 'E1_selectores.csv', encoding='utf-8-sig')
        w_sel = tabla_mejoras(ss, ['delay_ms', 'loss_pct'], 'Menor solapamiento (GAMR)', ['esc'])
        w_sel.to_csv(dir_tablas / 'E1_selectores_wilcoxon.csv', index=False, encoding='utf-8-sig')
        out.update(selectores=t_sel, selectores_wilcoxon=w_sel)

    # ------------------------------------------------------------------ E2
    if 'E2' in S:
        e2 = S['E2']
        t = tabla_media_std(e2, ['delay_ms', 'loss_pct', 'tiempo_s', 'HV'] if 'HV' in e2 else ['delay_ms', 'loss_pct'],
                            ['n_r'], ORDEN, DEC)
        t.to_csv(dir_tablas / 'E2_escalabilidad.csv', encoding='utf-8-sig')
        e2t = e2.copy()
        e2t['tiempo_ms_solicitud'] = 1000 * e2t.tiempo_s / e2t.n_r
        f = plots.fig_lineas(e2t, 'n_r', ['delay_ms', 'loss_pct', 'tiempo_ms_solicitud'],
                             ['retardo [ms] ↓', 'pérdida [%] ↓', 'tiempo por solicitud [ms]'], ORDEN,
                             'solicitudes simultáneas $N_r$', log_x=True)
        plots.guardar(f, dir_figs, 'E2_escalabilidad')
        plt.close(f)
        out.update(E2=t, E2_wilcoxon=tabla_mejoras(e2, ['delay_ms', 'loss_pct', 'tiempo_s'], 'GAMR', ['n_r']))

    # ------------------------------------------------------------------ E3
    if 'E3' in S:
        e3 = S['E3'].copy()
        e3['beta_pct'] = (100 * e3.beta).round().astype(int)
        t = tabla_media_std(e3, ['delay_ms', 'loss_pct', 'rho_max_pct'], ['beta_pct'], ORDEN, DEC)
        t.to_csv(dir_tablas / 'E3_beta.csv', encoding='utf-8-sig')
        f = plots.fig_lineas(e3, 'beta_pct', ['delay_ms', 'loss_pct', 'rho_max_pct'],
                             ['retardo [ms] ↓', 'pérdida [%] ↓', 'utilización máx. [%] ↓'], ORDEN,
                             'desorden del ancho de banda β [%]')
        plots.guardar(f, dir_figs, 'E3_beta')
        plt.close(f)
        out.update(E3=t, E3_wilcoxon=tabla_mejoras(e3, ['delay_ms', 'loss_pct'], 'GAMR', ['beta_pct']))

    (dir_tablas / 'resumen_resultados.md').write_text(resumen_markdown(out), encoding='utf-8')
    if verbose:
        print(f'Tablas en {dir_tablas}\nFiguras en {dir_figs}')
    return out


def resumen_markdown(out):
    """Frases con los números clave (para el informe y la presentación)."""
    L = ['# Resumen de resultados (generado automáticamente)', '']
    if 'E1_ablacion' in out:
        L += ['## E1 — F-GAMR y ablación frente a GAMR original (Δ% medio, p de Wilcoxon pareado, 30 semillas)', '',
              '| escenario | variante | métrica | Δ% (>0 = mejor) | p |', '|---|---|---|---|---|']
        a = out['E1_ablacion']
        for _, r in a[a.algoritmo.str.startswith('F-GAMR')].iterrows():
            L.append(f"| {r.esc} | {r.algoritmo} | {r.metrica} | {r.mejora_pct:+.1f} | {r.p_valor:.2g} |")
        L.append('')
    if 'E1_mejoras' in out:
        L += ['## E1 — F-GAMR frente a las tres líneas base', '', '| escenario | referencia | métrica | Δ% | p |',
              '|---|---|---|---|---|']
        for _, r in out['E1_mejoras'].iterrows():
            L.append(f"| {r.esc} | {r.referencia} | {r.metrica} | {r.mejora_pct:+.1f} | {r.p_valor:.2g} |")
        L.append('')
    for k, titulo, col in (('E2_wilcoxon', 'E2 — escalabilidad (vs GAMR)', 'n_r'),
                           ('E3_wilcoxon', 'E3 — desorden β (vs GAMR)', 'beta_pct')):
        if k in out:
            L += [f'## {titulo}', '', f'| {col} | variante | métrica | Δ% | p |', '|---|---|---|---|---|']
            for _, r in out[k].iterrows():
                L.append(f"| {r[col]} | {r.algoritmo} | {r.metrica} | {r.mejora_pct:+.1f} | {r.p_valor:.2g} |")
            L.append('')
    return '\n'.join(L)
