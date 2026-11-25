"""Líneas base: Min-Hop, QoS-Dijkstra, LCP-WAC* (proxy) y NSGA-II estándar (α = 0, sin memoria)."""
import time

import networkx as nx
import numpy as np

from .gamr_original import GAMR


class NSGA2(GAMR):
    """Línea base evolutiva clásica: mismos operadores y parada que GAMR, pero α = 0 y sin memoria PRSM."""

    nombre = 'NSGA-II'

    def __init__(self, red, **kw):
        super().__init__(red, usar_memoria=False, **kw)


class MinHop:
    """Camino más corto en saltos (BFS), independiente del estado de la red."""

    nombre = 'MH'

    def __init__(self, red, **_):
        self.red, self._cache = red, {}

    def resolver(self, solicitudes):
        t0 = time.perf_counter()
        rutas = []
        for h, s, _b in solicitudes:
            if (h, s) not in self._cache:
                self._cache[(h, s)] = tuple(nx.shortest_path(self.red.G, h, s))
            rutas.append(self._cache[(h, s)])
        return dict(nombre=self.nombre, rutas=rutas, tiempo=time.perf_counter() - t0)


class QoSDijkstra:
    """Enrutamiento QoS clásico: mínimo retardo sobre los enlaces con residual ≥ Bₖ (camino restringido).

    Cada solicitud se resuelve por separado (no considera la carga que agregan las demás).
    """

    nombre = 'QoS-Dijkstra'

    def __init__(self, red, **_):
        self.red = red

    def resolver(self, solicitudes):
        t0 = time.perf_counter()
        red = self.red
        residual = red.residual()
        peso_base = np.where(red.es_core, red.delay, 1e-3)
        rutas = []
        for h, s, b in solicitudes:
            def peso(u, v, _d, b=b):
                i = red.eid[(u, v)]
                return None if residual[i] < b else peso_base[i]
            try:
                ruta = nx.dijkstra_path(red.G, h, s, weight=peso)
            except nx.NetworkXNoPath:
                ruta = nx.dijkstra_path(red.G, h, s, weight=lambda u, v, d: peso_base[red.eid[(u, v)]])
            rutas.append(tuple(ruta))
        return dict(nombre=self.nombre, rutas=rutas, tiempo=time.perf_counter() - t0)


class LCPWACProxy:
    """Proxy de LCP-WAC (Hoang et al., 2023) SIN LSTM: costo ponderado sobre una predicción histórica (EWMA)
    del estado de los enlaces, con enrutamiento secuencial consciente de la carga ya asignada."""

    nombre = 'LCP-WAC*'

    def __init__(self, red, pesos=(1 / 3, 1 / 3, 1 / 3), suavizado=0.5, **_):
        self.red, self.pesos, self.a = red, pesos, suavizado

    def _prediccion(self):
        hist = self.red.historial
        pasado = hist[:-1] if len(hist) > 1 else hist[-1:]
        bw_hat, bg_hat = pasado[0][0].copy(), pasado[0][1].copy()
        for bw, bg in pasado[1:]:
            bw_hat = self.a * bw + (1 - self.a) * bw_hat
            bg_hat = self.a * bg + (1 - self.a) * bg_hat
        return bw_hat, bg_hat

    def resolver(self, solicitudes):
        t0 = time.perf_counter()
        red, (w1, w2, w3) = self.red, self.pesos
        bw_hat, carga = self._prediccion()
        base = w2 * red.loss / 0.10 + w3 * red.delay / 100.0
        rutas = []
        for h, s, b in solicitudes:
            costo = w1 * np.minimum((carga + b) / bw_hat, 2.0) + base + 1e-3
            costo[~red.es_core] = 1e-3
            ruta = tuple(nx.dijkstra_path(red.G, h, s, weight=lambda u, v, d: costo[red.eid[(u, v)]]))
            for i in range(len(ruta) - 1):
                carga[red.eid[(ruta[i], ruta[i + 1])]] += b
            rutas.append(ruta)
        return dict(nombre=self.nombre, rutas=rutas, tiempo=time.perf_counter() - t0)
