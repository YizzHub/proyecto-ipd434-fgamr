"""GAMR original (Tran et al., IEEE TETCI 2025): Sub-Algoritmos 1–6, parada temprana (Ec. 13) y elección final.

Implementación fiel al texto del paper (no al código público, que difiere; ver README). La clase expone tres
"hooks" que F-GAMR sobrescribe sin tocar el resto del algoritmo:

    alpha_intervalo()            → α usado en la inicialización híbrida (GAMR: 0.5 fijo)
    pm_generacion(G, hv_hist)    → p_m de la generación G (GAMR: 0.1 fijo)
    seleccionar_solucion(...)    → solución del frente que se instala (GAMR: menor solapamiento de enlaces)
"""
import random
import time
from collections import deque

import numpy as np

from .metrics_stats import ordenamiento_no_dominado, distancia_aglomeracion, hipervolumen
from .network_model import Evaluador, MODELO, solapamiento

# Tabla III del paper (TOL_HV: tolerancia numérica para ΔHV = 0 con objetivos continuos)
PARAM_GAMR = dict(N=100, G_MAX=500, G_PRE=10, PC=0.8, PM=0.1, ALPHA=0.5, TORNEO=2, TOL_HV=1e-4)


# =========================================================================== operadores sobre grafos
def eliminar_ciclos(ruta):
    """Sub-Alg. 4: elimina todo sub-camino entre dos apariciones del mismo nodo (una pasada, O(|p|))."""
    salida, pos = [], {}
    for v in ruta:
        if v in pos:
            k = pos[v]
            for w in salida[k + 1:]:
                del pos[w]
            del salida[k + 1:]
        else:
            pos[v] = len(salida)
            salida.append(v)
    return tuple(salida)


def rsbi(red, h, s, rnd):
    """RSBI (exploración): caminata aleatoria sin revisitas de h a s, con backtracking."""
    ruta, visitados = [h], {h}
    while ruta[-1] != s:
        u = ruta[-1]
        candidatos = [v for v in red.adj[u] if v not in visitados and (v == s or red.tipo[v] == 'switch')]
        if candidatos:
            v = rnd.choice(candidatos)
            ruta.append(v)
            visitados.add(v)
        else:
            ruta.pop()
            if not ruta:
                raise RuntimeError(f'No existe camino {h}->{s}')
    return tuple(ruta)


def bfs_predecesores(red, origen):
    """Árbol BFS (camino más corto en saltos) desde un host, avanzando solo por switches."""
    pred, cola = {origen: None}, deque([origen])
    while cola:
        u = cola.popleft()
        for v in red.adj[u]:
            if v not in pred and red.tipo[v] == 'switch':
                pred[v] = u
                cola.append(v)
    return pred


def psbi(ruta_memoria, h, camino_bfs, rnd):
    """PSBI (explotación): ruta previa al mismo servidor + BFS desde el nuevo host hasta un switch λ de ella."""
    i = rnd.randrange(1, len(ruta_memoria) - 1)
    q = camino_bfs(h, ruta_memoria[i])
    return eliminar_ciclos(tuple(q) + tuple(ruta_memoria[i + 1:]))


def cruce_multipunto(p1, p2, pc, rnd):
    """Sub-Alg. 2 sobre un segmento génico: intercambia las colas en un nodo común λ ∈ Ω."""
    en_p2 = set(p2[1:-1])
    omega = [v for v in p1[1:-1] if v in en_p2]
    if omega and rnd.random() <= pc:
        lam = rnd.choice(omega)
        i, j = p1.index(lam), p2.index(lam)
        return eliminar_ciclos(p1[:i] + p2[j:]), eliminar_ciclos(p2[:j] + p1[i:])
    return p1, p2


def mutacion_insercion(p, vecinos_comunes, pm, rnd):
    """Sub-Alg. 3: inserta un switch λ̃ ∈ γ adyacente a dos nodos consecutivos λ1, λ2."""
    i = rnd.randrange(len(p) - 1)
    gamma = vecinos_comunes[(p[i], p[i + 1])]
    if gamma and rnd.random() <= pm:
        return eliminar_ciclos(p[:i + 1] + (rnd.choice(gamma),) + p[i + 1:])
    return p


# =========================================================================== algoritmo
class Individuo:
    __slots__ = ('rutas', 'F', 'cv', 'rango', 'crowd')

    def __init__(self, rutas, F, cv):
        self.rutas, self.F, self.cv = rutas, F, cv
        self.rango, self.crowd = 0, 0.0


class GAMR:
    """GAMR original. Con usar_memoria=False (α = 0, sin PRSM) es el NSGA-II estándar de la línea base 2."""

    nombre = 'GAMR'

    def __init__(self, red, params=None, usar_memoria=True, alpha=None, semilla=0, modo_u=None, nombre=None):
        self.red = red
        self.p = dict(PARAM_GAMR)
        self.p.update(params or {})
        self.usar_memoria = usar_memoria
        self.alpha = (self.p['ALPHA'] if alpha is None else alpha) if usar_memoria else 0.0
        self.rnd = random.Random(semilla)
        self.modo_u = modo_u or MODELO['MODO_U']
        if nombre:
            self.nombre = nombre
        self.memoria = {}          # PRSM 𝓜: servidor → ruta óptima previa (Sub-Alg. 6)
        self._pred_bfs = {}
        self.pm_actual = self.p['PM']

    # ------------------------------------------------------------------ hooks (F-GAMR los sobrescribe)
    def alpha_intervalo(self):
        return self.alpha

    def pm_generacion(self, G, hv_hist):
        return self.p['PM']

    def inmigrantes_generacion(self, G, hv_hist):
        """Fracción ζ de la descendencia reemplazada por individuos nuevos (GAMR: 0)."""
        return 0.0

    def _preparar(self, solicitudes):
        """Hook al inicio de cada instancia (F-GAMR precalcula aquí la guía difusa sobre el estado medido)."""

    def seleccionar_solucion(self, frente, ev):
        """Fase 3.7: solución factible con menor solapamiento de enlaces (empate → menor delay)."""
        candidatos = [q for q in frente if q.cv <= 0] or frente
        return min(candidatos, key=lambda q: (solapamiento(self.red, ev, q.rutas), q.F[0]))

    # ------------------------------------------------------------------ utilidades
    def _camino_bfs(self, h, destino):
        pred = self._pred_bfs.get(h)
        if pred is None:
            pred = self._pred_bfs[h] = bfs_predecesores(self.red, h)
        camino = [destino]
        while camino[-1] != h:
            camino.append(pred[camino[-1]])
        return camino[::-1]

    def _nuevo(self, rutas, ev):
        F, cv = ev.evaluar(rutas)
        return Individuo(rutas, F, cv)

    # ------------------------------------------------------------------ Sub-Alg. 1: inicialización híbrida
    def inicializar_poblacion(self, solicitudes, ev, alpha, n=None):
        P = []
        for _ in range(self.p['N'] if n is None else n):
            rutas = []
            for h, s, _b in solicitudes:
                if alpha > 0 and self.rnd.random() <= alpha and s in self.memoria:
                    rutas.append(psbi(self.memoria[s], h, self._camino_bfs, self.rnd))
                else:
                    rutas.append(self._rsbi(h, s))
            P.append(self._nuevo(rutas, ev))
        return P

    def _rsbi(self, h, s):
        """Hook de exploración: RSBI uniforme (F-GAMR lo reemplaza por una caminata guiada por FIS-1)."""
        return rsbi(self.red, h, s, self.rnd)

    def _mutar(self, p, pm):
        """Hook de mutación: inserción con λ̃ uniforme en γ (F-GAMR lo guía con FIS-1)."""
        return mutacion_insercion(p, self.red.vecinos_comunes, pm, self.rnd)

    def _torneo(self, P):
        mejor = P[self.rnd.randrange(len(P))]
        for _ in range(self.p['TORNEO'] - 1):
            otro = P[self.rnd.randrange(len(P))]
            if otro.rango < mejor.rango or (otro.rango == mejor.rango and otro.crowd > mejor.crowd):
                mejor = otro
        return mejor

    # ------------------------------------------------------------------ Sub-Alg. 2 + 3 + 4: descendencia
    def generar_descendencia(self, P, ev, inmigrantes=()):
        pc, pm, rnd = self.p['PC'], self.pm_actual, self.rnd
        O = list(inmigrantes)
        while len(O) < self.p['N']:
            a, b = self._torneo(P), self._torneo(P)
            h1, h2 = [], []
            for p1, p2 in zip(a.rutas, b.rutas):
                c1, c2 = cruce_multipunto(p1, p2, pc, rnd)
                h1.append(self._mutar(c1, pm))
                h2.append(self._mutar(c2, pm))
            O.append(self._nuevo(h1, ev))
            O.append(self._nuevo(h2, ev))
        return O[:self.p['N']]

    # ------------------------------------------------------------------ Sub-Alg. 5: selección NSGA-II
    def seleccionar(self, Q, N):
        F = np.array([q.F for q in Q])
        cv = np.array([q.cv for q in Q])
        elegidos = []
        for r, frente in enumerate(ordenamiento_no_dominado(F, cv)):
            cd = distancia_aglomeracion(F[frente])
            for idx, d in zip(frente, cd):
                Q[idx].rango, Q[idx].crowd = r, d
            if len(elegidos) + len(frente) <= N:
                elegidos.extend(frente)
            else:
                orden = np.argsort(-cd, kind='stable')
                elegidos.extend(frente[orden[:N - len(elegidos)]])
                break
        return [Q[i] for i in elegidos]

    # ------------------------------------------------------------------ Ec. 13: parada temprana
    @staticmethod
    def _hv_poblacion(P, escala):
        frente = [q for q in P if q.rango == 0]
        factibles = [q for q in frente if q.cv <= 0]
        return hipervolumen(np.array([q.F for q in (factibles or frente)]) / escala)

    def epsilon(self, G, hv_hist):
        if G < self.p['G_PRE']:
            return 1.0
        delta = hv_hist[G] - hv_hist[G - self.p['G_PRE']]
        if abs(delta) < self.p['TOL_HV']:
            delta = 0.0
        return (self.p['G_MAX'] - G) * delta

    # ------------------------------------------------------------------ Sub-Alg. 6: memoria PRSM
    def actualizar_memoria(self, solicitudes, rutas):
        for (_h, s, _b), r in zip(solicitudes, rutas):
            self.memoria[s] = r

    # ------------------------------------------------------------------ ciclo principal (Fase 3)
    def resolver(self, solicitudes, escala=None):
        t0 = time.perf_counter()
        ev = Evaluador(self.red, solicitudes, self.modo_u)
        N, G_MAX = self.p['N'], self.p['G_MAX']
        alpha = self.alpha_intervalo() if self.usar_memoria else 0.0
        uso_memoria = alpha > 0 and any(s in self.memoria for _, s, _ in solicitudes)
        self._preparar(solicitudes)

        P = self.seleccionar(self.inicializar_poblacion(solicitudes, ev, alpha), N)
        if escala is None:
            escala = np.array([1.1 * max(q.F[0] for q in P), 1.0, 1.0])
        hv_hist = [self._hv_poblacion(P, escala)]
        traza_pm, traza_inm = [], []
        G = 0
        for G in range(1, G_MAX + 1):
            self.pm_actual = self.pm_generacion(G, hv_hist)
            zeta = self.inmigrantes_generacion(G, hv_hist)
            traza_pm.append(self.pm_actual)
            traza_inm.append(zeta)
            n_inm = int(round(zeta * N))
            inm = self.inicializar_poblacion(solicitudes, ev, alpha, n_inm) if n_inm else ()
            O = self.generar_descendencia(P, ev, inm)
            P = self.seleccionar(P + O, N)
            hv_hist.append(self._hv_poblacion(P, escala))
            if self.epsilon(G, hv_hist) == 0:
                break

        frente = [q for q in P if q.rango == 0]
        elegida = self.seleccionar_solucion(frente, ev)
        tiempo = time.perf_counter() - t0
        if self.usar_memoria:
            self.actualizar_memoria(solicitudes, elegida.rutas)
        factibles = [q for q in frente if q.cv <= 0] or frente
        return dict(nombre=self.nombre, rutas=elegida.rutas, F=elegida.F, cv=elegida.cv,
                    solapamiento=solapamiento(self.red, ev, elegida.rutas),
                    frente=np.unique(np.array([q.F for q in factibles]), axis=0), individuos_frente=factibles,
                    evaluador=ev, generaciones=G, tiempo=tiempo, hv_hist=np.array(hv_hist), escala=escala,
                    alpha=alpha, pm_medio=float(np.mean(traza_pm)) if traza_pm else self.p['PM'],
                    inm_medio=float(np.mean(traza_inm)) if traza_inm else 0.0,
                    traza_pm=np.array(traza_pm), traza_inm=np.array(traza_inm), uso_memoria=uso_memoria)
