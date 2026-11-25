"""F-GAMR: GAMR con exploración guiada por lógica difusa (FIS-1) y selección difusa del frente de Pareto (FIS-2).

Contribución propia sobre Tran et al. (2025):

FIS-1  Deseabilidad QoS de movimientos (Mamdani, 10 reglas) → ataca la debilidad 4 (exploración ciega).
    Para cada movimiento u → v de una ruta hacia el servidor S, con el estado MEDIDO del intervalo:
        progreso  π = (h_S(u) − h_S(v) + 1) / 2 ∈ {0, ½, 1}   (aleja / mismo nivel / acerca; h_S = saltos a S)
        retardo   d = delay_e / 100 ms,  pérdida  l = loss_e / 10 %,  carga  c = ρ_e (carga de fondo medida)
    salida: deseabilidad w ∈ [0, 1].
    · RSBI guiada: la caminata aleatoria elige v con probabilidad ∝ w^κ + ε (κ = 2, ε = 0.01) en vez de
      uniforme; conserva el backtracking y la aleatoriedad (exploración dirigida, no voraz).
    · Mutación guiada: λ̃ ∈ γ se elige con probabilidad ∝ q(λ₁, λ̃)·q(λ̃, λ₂), con q = w a progreso neutro.

FIS-2  Selector difuso de compromiso del frente F¹ (Mamdani, 6 reglas) → ataca la debilidad 2.
    entradas por solución (min–max dentro del frente): retardo medio y pérdida media planificados;
    salida: aptitud ∈ [0, 1]; se instala argmax (empate → menor retardo). Sustituye al criterio de
    "menor solapamiento de enlaces" de GAMR, que ignora la QoS que percibe el usuario.

Calibración (semillas de validación 500–503, disjuntas de la evaluación 0–29; ver scripts/calibracion.py):
    · κ ∈ {1, 2, 4} → κ = 2 maximiza el HV medio.
    · FIS-2 con entradas adicionales (solapamiento, holgura, volatilidad ν̂ᵗ) no mejoró la QoS realizada
      → se adopta la base parsimoniosa de 6 reglas.
    · Un controlador difuso de α/p_m según ν̂ᵗ (propuesta inicial) redujo el HV hasta 19 % → descartado.

Variantes de ablación: usar_fis1 / usar_fis2. El resto (memoria PRSM, α = 0.5, cruce, selección NSGA-II,
parada Ec. 13) es idéntico a GAMR.
"""
from collections import deque

import numpy as np

from .fuzzy_logic import VariableDifusa, Regla, SistemaMamdani
from .gamr_original import GAMR, eliminar_ciclos
from .network_model import solapamiento

KAPPA = 2.0          # codicia de la ruleta difusa (calibrado)
EPS_GUIA = 0.01      # piso de probabilidad: ningún movimiento válido queda prohibido
NU_MAX = 0.6         # ν bruto ≈ 0.12 (β ≤ 5 %), 0.18 (β = 20 %), 0.45 (β = 55 %) → ν̂ = min(1, ν / 0.6)

ETQ3 = {'Bajo': ('trap', (0.0, 0.0, 0.2, 0.5)), 'Medio': ('tri', (0.2, 0.5, 0.8)), 'Alto': ('trap', (0.5, 0.8, 1.0, 1.0))}


# =========================================================================== FIS-1: deseabilidad QoS
def construir_fis1():
    prog = VariableDifusa('progreso', (0, 1), {'Aleja': ('trap', (0.0, 0.0, 0.1, 0.4)),
                                               'Neutro': ('tri', (0.2, 0.5, 0.8)),
                                               'Acerca': ('trap', (0.6, 0.9, 1.0, 1.0))})
    ret = VariableDifusa('retardo', (0, 1), ETQ3)
    per = VariableDifusa('perdida', (0, 1), ETQ3)
    car = VariableDifusa('carga', (0, 1), {'Baja': ('trap', (0.0, 0.0, 0.1, 0.25)), 'Media': ('tri', (0.1, 0.3, 0.5)),
                                           'Alta': ('trap', (0.35, 0.6, 1.0, 1.0))})
    w = VariableDifusa('deseabilidad', (0, 1), {'MuyBaja': ('tri', (0.0, 0.05, 0.2)), 'Baja': ('tri', (0.1, 0.25, 0.4)),
                                                'Media': ('tri', (0.35, 0.5, 0.65)), 'Alta': ('tri', (0.6, 0.75, 0.9)),
                                                'MuyAlta': ('tri', (0.8, 0.95, 1.0))})
    R = [
        Regla([('progreso', 'Acerca'), ('retardo', 'Bajo'), ('perdida', 'Bajo')], {'deseabilidad': 'MuyAlta'}),
        Regla([('progreso', 'Acerca'), ('carga', 'Baja')], {'deseabilidad': 'Alta'}),
        Regla([('progreso', 'Acerca'), ('retardo', 'Medio')], {'deseabilidad': 'Alta'}),
        Regla([('progreso', 'Acerca'), ('retardo', 'Alto')], {'deseabilidad': 'Media'}),
        Regla([('progreso', 'Acerca'), ('perdida', 'Alto')], {'deseabilidad': 'Media'}),
        Regla([('progreso', 'Neutro'), ('retardo', 'Bajo'), ('perdida', 'Bajo')], {'deseabilidad': 'Media'}),
        Regla([('progreso', 'Neutro'), ('retardo', 'Alto')], {'deseabilidad': 'Baja'}),
        Regla([('progreso', 'Aleja'), ('retardo', 'Bajo'), ('carga', 'Baja')], {'deseabilidad': 'Baja'}),
        Regla([('progreso', 'Aleja')], {'deseabilidad': 'MuyBaja'}),
        Regla([('carga', 'Alta')], {'deseabilidad': 'Baja'}),
    ]
    return SistemaMamdani('FIS-1', [prog, ret, per, car], [w], R)


# =========================================================================== FIS-2: selector del frente
def construir_fis2():
    ent = [VariableDifusa(n, (0, 1), ETQ3) for n in ('delay', 'perdida')]
    apt = VariableDifusa('aptitud', (0, 1), {'Baja': ('tri', (0.0, 0.0, 0.4)), 'Media': ('tri', (0.2, 0.45, 0.7)),
                                              'Alta': ('tri', (0.5, 0.75, 1.0)), 'MuyAlta': ('tri', (0.8, 1.0, 1.0))})
    R = [
        Regla([('delay', 'Bajo'), ('perdida', 'Bajo')], {'aptitud': 'MuyAlta'}),
        Regla([('delay', 'Bajo'), ('perdida', 'Medio')], {'aptitud': 'Alta'}),
        Regla([('delay', 'Medio'), ('perdida', 'Bajo')], {'aptitud': 'Alta'}),
        Regla([('delay', 'Medio'), ('perdida', 'Medio')], {'aptitud': 'Media'}),
        Regla([('delay', 'Alto')], {'aptitud': 'Baja'}),
        Regla([('perdida', 'Alto')], {'aptitud': 'Baja'}),
    ]
    return SistemaMamdani('FIS-2', ent, [apt], R)


FIS1 = construir_fis1()
FIS2 = construir_fis2()


def volatilidad_normalizada(nu):
    return float(np.clip(nu / NU_MAX, 0.0, 1.0))


# --------------------------------------------------------------------------- guía de FIS-1
def _saltos_hacia(red, s):
    """h_S(v): saltos desde cada switch al servidor S (BFS sobre switches)."""
    dist, cola = {s: 0}, deque([s])
    while cola:
        u = cola.popleft()
        for v in red.adj[u]:
            if v not in dist and red.tipo[v] == 'switch':
                dist[v] = dist[u] + 1
                cola.append(v)
    return dist


def atributos_enlace(red):
    """Retardo, pérdida y carga normalizados por arista (enlaces de acceso: 0)."""
    core = red.es_core
    return (np.where(core, red.delay / 100.0, 0.0), np.where(core, red.loss / 0.10, 0.0),
            np.where(core, red.bg / red.bw, 0.0))


def construir_guia(red, servidores, kappa=KAPPA):
    """Precalcula, para cada (nodo, servidor), los movimientos válidos y sus pesos w^κ + ε (vectorizado)."""
    ret, per, car = atributos_enlace(red)
    claves, cands, tam, P, E = [], [], [], [], []
    for s in servidores:
        h = _saltos_hacia(red, s)
        for u in list(h) + red.hosts:
            if u == s:
                continue
            hu = h[u] if u in h else h[red.adj[u][0]] + 1
            vs = [v for v in red.adj[u] if v == s or red.tipo[v] == 'switch']
            claves.append((u, s))
            cands.append(tuple(vs))
            tam.append(len(vs))
            for v in vs:
                P.append((hu - h[v] + 1) / 2.0)
                E.append(red.eid[(u, v)])
    E = np.array(E)
    w = np.atleast_1d(FIS1.evaluar(progreso=np.clip(np.array(P), 0, 1), retardo=np.clip(ret[E], 0, 1),
                                   perdida=np.clip(per[E], 0, 1), carga=np.clip(car[E], 0, 1))['deseabilidad'])
    pesos = w ** kappa + EPS_GUIA
    guia, i = {}, 0
    for k, c, n in zip(claves, cands, tam):
        guia[k] = (c, pesos[i:i + n], w[i:i + n])
        i += n
    return guia


def calidad_enlaces(red, kappa=KAPPA):
    """q_e = deseabilidad de FIS-1 con progreso neutro (para la mutación guiada)."""
    ret, per, car = atributos_enlace(red)
    q = np.atleast_1d(FIS1.evaluar(progreso=np.full(red.E, 0.5), retardo=np.clip(ret, 0, 1),
                                   perdida=np.clip(per, 0, 1), carga=np.clip(car, 0, 1))['deseabilidad'])
    return q ** kappa + EPS_GUIA


def rsbi_guiado(red, h, s, rnd, guia):
    """RSBI con ruleta difusa: misma caminata sin revisitas + backtracking, pero no uniforme."""
    ruta, visitados = [h], {h}
    while ruta[-1] != s:
        cands, pesos, _ = guia[(ruta[-1], s)]
        idx = [i for i, v in enumerate(cands) if v not in visitados]
        if idx:
            v = cands[rnd.choices(idx, weights=[pesos[i] for i in idx])[0]]
            ruta.append(v)
            visitados.add(v)
        else:
            ruta.pop()
            if not ruta:
                raise RuntimeError(f'No existe camino {h}->{s}')
    return tuple(ruta)


def mutacion_guiada(red, p, pm, rnd, q):
    """Inserción de λ̃ ∈ γ con probabilidad ∝ q(λ₁, λ̃)·q(λ̃, λ₂)."""
    i = rnd.randrange(len(p) - 1)
    gamma = red.vecinos_comunes[(p[i], p[i + 1])]
    if gamma and rnd.random() <= pm:
        pesos = [q[red.eid[(p[i], g)]] * q[red.eid[(g, p[i + 1])]] for g in gamma]
        return eliminar_ciclos(p[:i + 1] + (rnd.choices(gamma, weights=pesos)[0],) + p[i + 1:])
    return p


# --------------------------------------------------------------------------- FIS-2
def atributos_frente(red, ev, individuos):
    """Criterios del frente: delay, pérdida, solapamiento de enlaces y holgura de capacidad (1 − f₃)."""
    F = np.array([q.F for q in individuos])
    sol = np.array([solapamiento(red, ev, q.rutas) for q in individuos], dtype=float)
    return dict(delay=F[:, 0], perdida=F[:, 1], solapamiento=sol, holgura=1.0 - F[:, 2])


def _minmax(x):
    rango = x.max() - x.min()
    return np.zeros_like(x) if rango < 1e-12 else (x - x.min()) / rango


def aptitud_difusa(atributos):
    """Aptitud de FIS-2 de cada solución del frente (retardo y pérdida normalizados dentro del frente)."""
    return np.atleast_1d(FIS2.evaluar(delay=_minmax(atributos['delay']),
                                      perdida=_minmax(atributos['perdida']))['aptitud'])


def elegir_fis2(red, ev, individuos):
    att = atributos_frente(red, ev, individuos)
    apt = aptitud_difusa(att)
    orden = np.lexsort((att['delay'], -np.round(apt, 9)))     # mayor aptitud; empate → menor delay
    return individuos[orden[0]], apt


# =========================================================================== algoritmo
class FGAMR(GAMR):
    """F-GAMR completo (FIS-1 + FIS-2) o sus variantes de ablación."""

    nombre = 'F-GAMR'

    def __init__(self, red, usar_fis1=True, usar_fis2=True, nombre=None, kappa=KAPPA, **kw):
        super().__init__(red, usar_memoria=True, **kw)
        self.usar_fis1, self.usar_fis2, self.kappa = usar_fis1, usar_fis2, kappa
        if nombre:
            self.nombre = nombre
        elif usar_fis1 and not usar_fis2:
            self.nombre = 'F-GAMR (FIS-1)'
        elif usar_fis2 and not usar_fis1:
            self.nombre = 'F-GAMR (FIS-2)'
        self._guia, self._q = None, None

    def _preparar(self, solicitudes):
        if self.usar_fis1:
            self._guia = construir_guia(self.red, sorted({s for _, s, _ in solicitudes}), self.kappa)
            self._q = calidad_enlaces(self.red, self.kappa)

    def _rsbi(self, h, s):
        if not self.usar_fis1:
            return super()._rsbi(h, s)
        return rsbi_guiado(self.red, h, s, self.rnd, self._guia)

    def _mutar(self, p, pm):
        if not self.usar_fis1:
            return super()._mutar(p, pm)
        return mutacion_guiada(self.red, p, pm, self.rnd, self._q)

    def seleccionar_solucion(self, frente, ev):
        if not self.usar_fis2:
            return super().seleccionar_solucion(frente, ev)
        candidatos = [q for q in frente if q.cv <= 0] or frente
        return elegir_fis2(self.red, ev, candidatos)[0]
