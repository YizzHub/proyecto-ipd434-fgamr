"""Motor de experimentos: cada tarea = (configuración, semilla) → secuencia dinámica de T intervalos.

Protocolo por intervalo t (idéntico para todos los algoritmos de la tarea):
  1. el monitoreo mide el estado Δᵗ y llegan N_r solicitudes nuevas;
  2. cada algoritmo calcula sus rutas sobre Δᵗ (HV/IGD se calculan con normalización conjunta de los EAs);
  3. las rutas quedan instaladas mientras la red evoluciona a Δᵗ⁺¹ (Ec. 14 con el β del escenario);
  4. la QoS se mide sobre el estado REALIZADO Δᵗ⁺¹ (también se guarda la QoS planificada sobre Δᵗ).
Los algoritmos no consumen el generador aleatorio de la red → todos ven las mismas solicitudes y estados.
El intervalo 1 tiene la memoria vacía (GAMR ≡ NSGA-II); las estadísticas usan t ≥ 2.
"""
import os
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np
import pandas as pd

from data.topologies import cargar_topologia
from .baselines import NSGA2, MinHop, QoSDijkstra, LCPWACProxy
from .gamr_original import GAMR
from .metrics_stats import metricas_conjuntas
from .network_model import RedSDN, evaluar_qos, solapamiento
from .proposed_method import FGAMR, elegir_fis2, atributos_frente

FABRICAS = {
    'MH': lambda red, sem, p: MinHop(red),
    'QoS-Dijkstra': lambda red, sem, p: QoSDijkstra(red),
    'LCP-WAC*': lambda red, sem, p: LCPWACProxy(red),
    'NSGA-II': lambda red, sem, p: NSGA2(red, params=p, semilla=sem + 1),
    'GAMR': lambda red, sem, p: GAMR(red, params=p, semilla=sem + 2),
    'F-GAMR (FIS-1)': lambda red, sem, p: FGAMR(red, usar_fis2=False, params=p, semilla=sem + 3),
    'F-GAMR (FIS-2)': lambda red, sem, p: FGAMR(red, usar_fis1=False, params=p, semilla=sem + 4),
    'F-GAMR': lambda red, sem, p: FGAMR(red, params=p, semilla=sem + 5),
}
EVOLUTIVOS = ['NSGA-II', 'GAMR', 'F-GAMR (FIS-1)', 'F-GAMR (FIS-2)', 'F-GAMR']
ORDEN = ['MH', 'QoS-Dijkstra', 'LCP-WAC*'] + EVOLUTIVOS
SELECTORES = ['Menor solapamiento (GAMR)', 'Mínimo delay', 'Punto rodilla', 'FIS-2']


def configuraciones(modo='completo'):
    """Lista de tareas (dict) de los tres experimentos."""
    if modo == 'rapido':
        sem_e1, sem_e23, T, gmax = range(2), range(1), 3, 100
    else:
        sem_e1, sem_e23, T, gmax = range(30), range(10), 4, 500
    params = dict(G_MAX=gmax)
    tareas = []
    # E1 — comparación principal + ablación (30 semillas; 2 servidores para que haya congestión)
    for topo in ('Oxford', 'Chinanet'):
        for beta in (0.05, 0.55):
            for s in sem_e1:
                tareas.append(dict(experimento='E1', topologia=topo, beta=beta, n_s=2, n_r=50, T=T, semilla=s,
                                   params=params, selectores=True,
                                   algoritmos=['MH', 'QoS-Dijkstra'] + EVOLUTIVOS))
    # E2 — escalabilidad en N_r (Oxford, 2 servidores, β = 20 %)
    for n_r in (10, 20, 50, 100):
        for s in sem_e23:
            tareas.append(dict(experimento='E2', topologia='Oxford', beta=0.20, n_s=2, n_r=n_r, T=T, semilla=s,
                               params=params, selectores=False,
                               algoritmos=['MH', 'QoS-Dijkstra', 'GAMR', 'F-GAMR']))
    # E3 — barrido de desorden β (Chinanet, 2 servidores, 100 solicitudes)
    for beta in (0.0, 0.05, 0.20, 0.55):
        for s in sem_e23:
            tareas.append(dict(experimento='E3', topologia='Chinanet', beta=beta, n_s=2, n_r=100, T=T, semilla=s,
                               params=params, selectores=False,
                               algoritmos=['MH', 'LCP-WAC*', 'GAMR', 'F-GAMR']))
    return tareas


def _selectores(red, res):
    """Elige con cada criterio sobre el MISMO frente final de GAMR (análisis post-hoc, no altera la memoria)."""
    ev, ind = res['evaluador'], res['individuos_frente']
    att = atributos_frente(red, ev, ind)
    F = np.column_stack([att['delay'], att['perdida'], 1 - att['holgura']])
    rango = np.where(np.ptp(F, axis=0) > 1e-12, np.ptp(F, axis=0), 1.0)
    rodilla = int(np.argmin(np.linalg.norm((F - F.min(axis=0)) / rango, axis=1)))
    return {'Menor solapamiento (GAMR)': res['rutas'],
            'Mínimo delay': ind[int(np.lexsort((att['perdida'], att['delay']))[0])].rutas,
            'Punto rodilla': ind[rodilla].rutas,
            'FIS-2': elegir_fis2(red, ev, ind)[0].rutas}


def ejecutar_tarea(cfg):
    """Ejecuta una semilla de una configuración. Devuelve (filas_algoritmos, filas_selectores)."""
    g, _ = cargar_topologia(cfg['topologia'])
    red = RedSDN(g, cfg['n_s'], beta=cfg['beta'], semilla=10_000 + 97 * cfg['semilla'])
    algos = {a: FABRICAS[a](red, 1000 * cfg['semilla'], cfg['params']) for a in cfg['algoritmos']}
    clave = {k: cfg[k] for k in ('experimento', 'topologia', 'beta', 'n_s', 'n_r', 'semilla')}
    filas, filas_sel = [], []
    for t in range(1, cfg['T'] + 1):
        sol = red.generar_solicitudes(cfg['n_r'], cfg['n_s'])
        nu = red.volatilidad
        res = {a: alg.resolver(sol) for a, alg in algos.items()}
        evos = [a for a in res if 'frente' in res[a]]
        mo = metricas_conjuntas({a: res[a]['frente'] for a in evos}) if len(evos) > 1 else {}
        planificada = {a: evaluar_qos(red, sol, r['rutas']) for a, r in res.items()}
        sel = _selectores(red, res['GAMR']) if cfg['selectores'] and 'GAMR' in res else {}

        red.nuevo_intervalo()                                     # la red evoluciona con las rutas instaladas
        for a, r in res.items():
            fila = dict(clave, intervalo=t, algoritmo=a, volatilidad=nu, tiempo_s=r['tiempo'],
                        **evaluar_qos(red, sol, r['rutas']),
                        delay_plan_ms=planificada[a]['delay_ms'], loss_plan_pct=planificada[a]['loss_pct'])
            if a in mo:
                fila.update(HV=mo[a][0], IGD=mo[a][1], generaciones=r['generaciones'], alpha=r['alpha'],
                            pm_medio=r['pm_medio'], tam_frente=len(r['frente']), solapamiento=r['solapamiento'],
                            uso_memoria=r['uso_memoria'])
            filas.append(fila)
        for nombre, rutas in sel.items():
            filas_sel.append(dict(clave, intervalo=t, selector=nombre, **evaluar_qos(red, sol, rutas)))
    return filas, filas_sel


def ejecutar(tareas, n_jobs=None, progreso=True):
    """Ejecuta las tareas en paralelo (procesos). Devuelve (df_algoritmos, df_selectores)."""
    n_jobs = n_jobs or max(1, (os.cpu_count() or 2) - 1)
    filas, filas_sel = [], []
    t0 = time.time()
    if n_jobs == 1:
        for i, cfg in enumerate(tareas, 1):
            f, fs = ejecutar_tarea(cfg)
            filas += f
            filas_sel += fs
            if progreso:
                print(f'\r  {i}/{len(tareas)} tareas · {time.time() - t0:.0f} s', end='', flush=True)
    else:
        with ProcessPoolExecutor(max_workers=n_jobs) as pool:
            futuros = [pool.submit(ejecutar_tarea, cfg) for cfg in tareas]
            for i, fut in enumerate(as_completed(futuros), 1):
                f, fs = fut.result()
                filas += f
                filas_sel += fs
                if progreso:
                    print(f'\r  {i}/{len(tareas)} tareas · {time.time() - t0:.0f} s', end='', flush=True)
    if progreso:
        print()
    orden = ['experimento', 'topologia', 'beta', 'n_s', 'n_r', 'semilla', 'intervalo']
    df = pd.DataFrame(filas).sort_values(orden + ['algoritmo']).reset_index(drop=True)
    df_sel = pd.DataFrame(filas_sel)
    if len(df_sel):
        df_sel = df_sel.sort_values(orden + ['selector']).reset_index(drop=True)
    return df, df_sel


def cargar_o_ejecutar(dir_crudos, modo='completo', n_jobs=None, recalcular=False, experimentos=('E1', 'E2', 'E3')):
    """Carga los CSV crudos si existen; si no (o si recalcular=True), ejecuta y los guarda."""
    dir_crudos.mkdir(parents=True, exist_ok=True)
    ruta, ruta_sel = dir_crudos / 'resultados_algoritmos.csv', dir_crudos / 'resultados_selectores.csv'
    if ruta.exists() and not recalcular:
        df = pd.read_csv(ruta)
        df_sel = pd.read_csv(ruta_sel) if ruta_sel.exists() else pd.DataFrame()
        print(f'Resultados cargados de {ruta} ({len(df)} filas).')
        return df, df_sel
    tareas = [c for c in configuraciones(modo) if c['experimento'] in experimentos]
    print(f'Ejecutando {len(tareas)} tareas en modo {modo}...')
    df, df_sel = ejecutar(tareas, n_jobs)
    df.to_csv(ruta, index=False)
    df_sel.to_csv(ruta_sel, index=False)
    return df, df_sel
