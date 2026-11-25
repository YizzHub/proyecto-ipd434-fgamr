"""Calibración de F-GAMR en semillas de VALIDACIÓN (500–503), disjuntas de las de evaluación (0–29).

Etapa A — controlador difuso adaptativo de α / inmigrantes según la volatilidad ν̂ᵗ (propuesta inicial).
Etapa B — exploración guiada por FIS-1 con κ ∈ {1, 2, 4}.
Etapa C — bases de reglas de FIS-2 evaluadas fuera de línea sobre los frentes guardados en la etapa B.

Uso:  python scripts/calibracion.py [--jobs 7]     (≈ 15 min con 7 procesos)
Salida: results/calibracion/*.csv y un resumen en pantalla.
"""
import argparse
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from data.topologies import cargar_topologia                                    # noqa: E402
from src.fuzzy_logic import VariableDifusa, Regla, SistemaMamdani                # noqa: E402
from src.gamr_original import GAMR                                               # noqa: E402
from src.metrics_stats import metricas_conjuntas                                 # noqa: E402
from src.network_model import RedSDN, evaluar_qos                                # noqa: E402
from src.proposed_method import (FGAMR, ETQ3, atributos_frente, volatilidad_normalizada,  # noqa: E402
                                 aptitud_difusa)

SALIDA = RAIZ / 'results' / 'calibracion'
SEMILLAS = range(500, 504)
ESCENARIOS = [(tp, b) for tp in ('Oxford', 'Chinanet') for b in (0.05, 0.55)]
N_S, N_R, T = 2, 50, 4
ETQ_NU = {'Baja': ('trap', (0, 0, 0.2, 0.35)), 'Media': ('tri', (0.2, 0.4, 0.6)), 'Alta': ('trap', (0.45, 0.65, 1, 1))}


# =========================================================================== Etapa A
def controlador_adaptativo(alpha_c=(0.25, 0.45, 0.65), zeta_c=(0.0, 0.1, 0.25)):
    nu = VariableDifusa('volatilidad', (0, 1), ETQ_NU)
    s = VariableDifusa('estancamiento', (0, 1), {'Baja': ('trap', (0, 0, 0.2, 0.45)), 'Media': ('tri', (0.25, 0.5, 0.75)),
                                                  'Alta': ('trap', (0.55, 0.8, 1, 1))})
    a = VariableDifusa('alpha', (0, 1), {k: ('tri', (c - 0.15, c, c + 0.15)) for k, c in zip(('Bajo', 'Medio', 'Alto'), alpha_c)})
    z = VariableDifusa('zeta', (0, 0.5), {k: ('tri', (max(c - 0.08, 0), c, c + 0.08)) for k, c in zip(('Baja', 'Media', 'Alta'), zeta_c)})
    R = [Regla([('volatilidad', 'Baja')], {'alpha': 'Alto'}), Regla([('volatilidad', 'Media')], {'alpha': 'Medio'}),
         Regla([('volatilidad', 'Alta')], {'alpha': 'Bajo'})]
    tz = {('Baja', 'Baja'): 'Baja', ('Baja', 'Media'): 'Baja', ('Baja', 'Alta'): 'Media', ('Media', 'Baja'): 'Baja',
          ('Media', 'Media'): 'Media', ('Media', 'Alta'): 'Alta', ('Alta', 'Baja'): 'Media', ('Alta', 'Media'): 'Alta',
          ('Alta', 'Alta'): 'Alta'}
    R += [Regla([('volatilidad', x), ('estancamiento', y)], {'zeta': w}) for (x, y), w in tz.items()]
    return SistemaMamdani('adaptativo', [nu, s], [a, z], R)


def estancamiento(hv, ventana=5, pi_min=1e-4, pi_max=5e-2):
    if len(hv) <= ventana:
        return 0.0
    pi = max((hv[-1] - hv[-1 - ventana]) / max(hv[-1 - ventana], 1e-12), pi_min)
    return float(np.clip(1 - np.log10(pi / pi_min) / np.log10(pi_max / pi_min), 0, 1))


class GAMRAdaptativo(GAMR):
    def __init__(self, red, usa_alpha, usa_zeta, **kw):
        super().__init__(red, **kw)
        self.sis, self.ua, self.uz = controlador_adaptativo(), usa_alpha, usa_zeta

    def _nu(self):
        return volatilidad_normalizada(self.red.volatilidad)

    def alpha_intervalo(self):
        return float(self.sis.evaluar(volatilidad=self._nu(), estancamiento=0.0)['alpha']) if self.ua else self.alpha

    def inmigrantes_generacion(self, G, hv):
        return float(self.sis.evaluar(volatilidad=self._nu(), estancamiento=estancamiento(hv))['zeta']) if self.uz else 0.0


def _secuencia(cfg, fabricas, guardar_frentes=()):
    g, _ = cargar_topologia(cfg['topo'])
    red = RedSDN(g, N_S, beta=cfg['beta'], semilla=10_000 + 97 * cfg['s'])
    algos = {k: f(red, i + 1) for i, (k, f) in enumerate(fabricas.items())}
    filas, miembros = [], []
    for t in range(1, T + 1):
        sol = red.generar_solicitudes(N_R, N_S)
        nu = red.volatilidad
        res = {k: a.resolver(sol) for k, a in algos.items()}
        mo = metricas_conjuntas({k: r['frente'] for k, r in res.items()})
        atts = {k: atributos_frente(red, res[k]['evaluador'], res[k]['individuos_frente']) for k in guardar_frentes}
        red.nuevo_intervalo()
        for k, r in res.items():
            filas.append(dict(topo=cfg['topo'], beta=cfg['beta'], s=cfg['s'], t=t, alg=k, HV=mo[k][0], IGD=mo[k][1],
                              tiempo=r['tiempo'], gen=r['generaciones'], alpha=r['alpha'], inm=r['inm_medio'],
                              **evaluar_qos(red, sol, r['rutas'])))
        for k in guardar_frentes:
            for i, q in enumerate(res[k]['individuos_frente']):
                miembros.append(dict(alg=k, topo=cfg['topo'], beta=cfg['beta'], s=cfg['s'], t=t, i=i, nu=nu,
                                     elegido=q.rutas == res[k]['rutas'],
                                     **{f'a_{c}': v[i] for c, v in atts[k].items()},
                                     **{f'r_{c}': v for c, v in evaluar_qos(red, sol, q.rutas).items()}))
    return filas, miembros


def tarea_a(cfg):
    return _secuencia(cfg, {'GAMR': lambda r, s: GAMR(r, semilla=s),
                            'alpha adaptativo': lambda r, s: GAMRAdaptativo(r, True, False, semilla=s),
                            'alpha + inmigrantes': lambda r, s: GAMRAdaptativo(r, True, True, semilla=s),
                            'solo inmigrantes': lambda r, s: GAMRAdaptativo(r, False, True, semilla=s)})


def tarea_b(cfg):
    return _secuencia(cfg, {'GAMR': lambda r, s: GAMR(r, semilla=s),
                            'FIS-1 k=1': lambda r, s: FGAMR(r, usar_fis2=False, kappa=1, semilla=s),
                            'FIS-1 k=2': lambda r, s: FGAMR(r, usar_fis2=False, kappa=2, semilla=s),
                            'FIS-1 k=4': lambda r, s: FGAMR(r, usar_fis2=False, kappa=4, semilla=s)},
                      guardar_frentes=('FIS-1 k=2',))


# =========================================================================== Etapa C
def bases_fis2():
    """Bases de reglas candidatas para FIS-2 (la 'B' es la adoptada en src/proposed_method.py)."""
    apt = lambda: VariableDifusa('aptitud', (0, 1), {'Baja': ('tri', (0, 0, 0.4)), 'Media': ('tri', (0.2, 0.45, 0.7)),
                                                      'Alta': ('tri', (0.5, 0.75, 1)), 'MuyAlta': ('tri', (0.8, 1, 1))})
    ent = lambda: ([VariableDifusa(n, (0, 1), ETQ3) for n in ('delay', 'perdida', 'solapamiento', 'holgura')]
                   + [VariableDifusa('volatilidad', (0, 1), ETQ_NU)])
    base = [Regla([('delay', 'Bajo'), ('perdida', 'Bajo')], {'aptitud': 'MuyAlta'}),
            Regla([('delay', 'Bajo'), ('perdida', 'Medio')], {'aptitud': 'Alta'}),
            Regla([('delay', 'Medio'), ('perdida', 'Bajo')], {'aptitud': 'Alta'}),
            Regla([('delay', 'Medio'), ('perdida', 'Medio')], {'aptitud': 'Media'}),
            Regla([('delay', 'Alto')], {'aptitud': 'Baja'}), Regla([('perdida', 'Alto')], {'aptitud': 'Baja'})]
    reglas = {
        'A (+solapamiento, +volatilidad)': base + [Regla([('solapamiento', 'Alto')], {'aptitud': 'Baja'}),
                                                    Regla([('volatilidad', 'Alta'), ('holgura', 'Bajo')], {'aptitud': 'Baja'})],
        'B (retardo-pérdida, adoptada)': base,
        'C (sesgo a retardo)': base[:2] + [Regla([('delay', 'Medio'), ('perdida', 'Bajo')], {'aptitud': 'Media'})]
                               + base[3:] + [Regla([('solapamiento', 'Alto'), ('holgura', 'Bajo')], {'aptitud': 'Baja'})],
    }
    return {k: SistemaMamdani(k, ent(), [apt()], r) for k, r in reglas.items()}


def etapa_c(frentes):
    mm = lambda x: np.zeros_like(x) if np.ptp(x) < 1e-12 else (x - x.min()) / np.ptp(x)
    sistemas = bases_fis2()
    filas = []
    for k, d in frentes[frentes.t >= 2].groupby(['topo', 'beta', 's', 't']):
        d = d.reset_index(drop=True)
        nu = volatilidad_normalizada(d.nu.iloc[0])
        att = {c: d[f'a_{c}'].values for c in ('delay', 'perdida', 'solapamiento', 'holgura')}
        elec = {'Menor solapamiento (GAMR)': int(d.index[d.elegido][0]),
                'Mínimo delay': int(d.a_delay.idxmin()),
                'FIS-2 final (src)': int(np.lexsort((att['delay'], -np.round(aptitud_difusa(att), 9)))[0])}
        for nombre, sis in sistemas.items():
            a = sis.evaluar(**{c: mm(v) for c, v in att.items()}, volatilidad=np.full(len(d), nu))['aptitud']
            elec[nombre] = int(np.lexsort((att['delay'], -np.round(a, 9)))[0])
        for nombre, i in elec.items():
            filas.append(dict(topo=k[0], beta=k[1], s=k[2], t=k[3], selector=nombre,
                              delay_ms=d.loc[i, 'r_delay_ms'], loss_pct=d.loc[i, 'r_loss_pct']))
    r = pd.DataFrame(filas)
    g = r.groupby(['topo', 'beta', 'selector'])[['delay_ms', 'loss_pct']].mean()
    ref = g.xs('Menor solapamiento (GAMR)', level='selector')
    rel = 100 * (g / ref.reindex(g.index.droplevel('selector')).values - 1)
    return r, rel.round(2)


def _paralelo(fn, jobs):
    cfgs = [dict(topo=tp, beta=b, s=s) for tp, b in ESCENARIOS for s in SEMILLAS]
    F, M = [], []
    with ProcessPoolExecutor(jobs) as ex:
        for f, m in ex.map(fn, cfgs):
            F += f
            M += m
    return pd.DataFrame(F), pd.DataFrame(M)


def resumen(df):
    return df[df.t >= 2].groupby(['topo', 'beta', 'alg'])[['HV', 'IGD', 'tiempo', 'gen', 'alpha', 'delay_ms', 'loss_pct']].mean().round(3)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--jobs', type=int, default=7)
    ap.add_argument('--solo-c', action='store_true', help='rehace solo la etapa C con los frentes ya guardados')
    args = ap.parse_args()
    SALIDA.mkdir(parents=True, exist_ok=True)
    pd.set_option('display.width', 220)
    t0 = time.time()
    if not args.solo_c:
        dfa, _ = _paralelo(tarea_a, args.jobs)
        dfa.to_csv(SALIDA / 'etapaA_controlador_adaptativo.csv', index=False)
        print('Etapa A (controlador α / inmigrantes):\n', resumen(dfa).to_string())
        dfb, frentes = _paralelo(tarea_b, args.jobs)
        dfb.to_csv(SALIDA / 'etapaB_kappa.csv', index=False)
        frentes.to_csv(SALIDA / 'etapaB_frentes_fis1_k2.csv', index=False)
        print('Etapa B (κ de FIS-1):\n', resumen(dfb).to_string())
    frentes = pd.read_csv(SALIDA / 'etapaB_frentes_fis1_k2.csv')
    selc, rel = etapa_c(frentes)
    selc.to_csv(SALIDA / 'etapaC_selectores.csv', index=False)
    print('Etapa C (Δ% vs menor solapamiento):\n', rel.unstack('selector').to_string())
    print(f'Listo en {time.time() - t0:.0f} s')
