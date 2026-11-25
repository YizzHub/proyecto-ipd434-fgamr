"""Modelo del plano de datos SDN y de la función multi-objetivo de GAMR (Tran et al., 2025, Sec. III).

- RedSDN: topología + hosts + servidores, atributos de enlace (Tabla II) y ancho de banda dinámico (Ec. 14).
- Evaluador: f(Φ) = {delay medio, pérdida media, 1 − U} (Ec. 1–5) y violación de ℬₖ ≥ Bₖ (Ec. 6).
- evaluar_qos: métricas de red "medidas" de una configuración de rutas instalada.

El plano de datos real (Mininet + Ryu) se reemplaza por un modelo fluido: la carga de cada enlace es la
carga de fondo más la demanda de los flujos que lo atraviesan; la congestión agrega retardo de cola
(M/M/1 acotada) y pérdida por desborde.
"""
import numpy as np
import networkx as nx

# Tabla II del paper
TABLA_II = dict(DELAY_MS=(5.0, 100.0),
                LOSS_PCT=(0.1, 0.5, 1, 2, 3, 4, 5, 7, 9, 10),
                BW_MBPS=(30.0, 200.0))

# Supuestos del modelo fluido (el paper no los especifica; idénticos a la réplica del seminario)
MODELO = dict(B_REQ_MBPS=(0.5, 3.0),   # demanda por solicitud Bₖ
              BG_UTIL=(0.0, 0.3),      # carga de fondo como fracción de bw_e
              TAU_MS=10.0,             # escala del retardo de cola
              Q_MAX=20.0,              # cota del factor de cola ρ/(1−ρ)
              MODO_U='codigo')         # objetivo 3: versión del código oficial (ver Evaluador)


class RedSDN:
    """Plano de datos simulado. Cada llamada a nuevo_intervalo() avanza la red de Δᵗ a Δᵗ⁺¹."""

    def __init__(self, G_sw, n_servidores, beta=0.2, semilla=0):
        self.beta = beta
        rng_enlaces = np.random.default_rng(semilla)        # atributos estáticos (Tabla II)
        rng_servid = np.random.default_rng(semilla + 1)     # ubicación de servidores
        self.rng = np.random.default_rng(semilla + 2)       # dinámica por intervalo y solicitudes

        self.switches = sorted(G_sw.nodes(), key=lambda v: int(v[1:]))
        G = nx.Graph()
        G.add_nodes_from(self.switches, tipo='switch')
        G.add_edges_from(G_sw.edges())
        self.hosts = []
        for i, m in enumerate(self.switches):
            h = f'H{i + 1}'
            G.add_node(h, tipo='host')
            G.add_edge(h, m)
            self.hosts.append(h)
        orden = rng_servid.permutation(len(self.switches))
        self.servidores = []
        for j in range(n_servidores):
            s = f'S{j + 1}'
            G.add_node(s, tipo='servidor')
            G.add_edge(s, self.switches[orden[j % len(orden)]])
            self.servidores.append(s)
        self.G = G
        self.tipo = nx.get_node_attributes(G, 'tipo')
        self.adj = {v: sorted(G.neighbors(v)) for v in G.nodes()}

        self.aristas = [tuple(e) for e in G.edges()]
        self.E = len(self.aristas)
        self.eid = {}
        for i, (u, v) in enumerate(self.aristas):
            self.eid[(u, v)] = i
            self.eid[(v, u)] = i
        self.es_core = np.array([self.tipo[u] == 'switch' and self.tipo[v] == 'switch' for u, v in self.aristas])
        nc = int(self.es_core.sum())

        # Atributos de la Tabla II, en orden canónico para que no dependan de N_s
        orden_core = sorted((i for i in range(self.E) if self.es_core[i]), key=lambda i: tuple(sorted(self.aristas[i])))
        self.delay = np.zeros(self.E)
        self.loss = np.zeros(self.E)
        self.bw_base = np.full(self.E, 1e9)        # enlaces de acceso: capacidad "infinita"
        self.delay[orden_core] = rng_enlaces.uniform(*TABLA_II['DELAY_MS'], nc)
        self.loss[orden_core] = rng_enlaces.choice(TABLA_II['LOSS_PCT'], nc) / 100.0
        self.bw_base[orden_core] = rng_enlaces.uniform(*TABLA_II['BW_MBPS'], nc)

        self.vecinos_comunes = {}                  # γ de la mutación por inserción (Sub-Alg. 3)
        for u, v in self.aristas:
            comunes = sorted(w for w in set(self.adj[u]) & set(self.adj[v]) if self.tipo[w] == 'switch')
            self.vecinos_comunes[(u, v)] = comunes
            self.vecinos_comunes[(v, u)] = comunes

        self.t = 0
        self.historial = []      # [(bw, carga_fondo)] por intervalo (lo usa el predictor de LCP-WAC*)
        self.volatilidad = 0.0   # νᵗ: cambio relativo del ancho de banda residual entre Δᵗ⁻¹ y Δᵗ
        self.nuevo_intervalo()

    def residual(self, bw=None, bg=None):
        bw = self.bw if bw is None else bw
        bg = self.bg if bg is None else bg
        return np.maximum(bw - bg, 0.0)

    def nuevo_intervalo(self):
        """Re-muestrea el ancho de banda (Ec. 14) y la carga de fondo, y mide la volatilidad νᵗ."""
        core = self.es_core
        bw = self.bw_base.copy()
        if self.beta == 0:
            bw[core] = self.bw_base[core].mean()
        else:
            b = self.bw_base[core]
            bw[core] = b + self.rng.uniform(-self.beta * b, self.beta * b)
        bg = np.zeros(self.E)
        bg[core] = self.rng.uniform(*MODELO['BG_UTIL'], int(core.sum())) * bw[core]
        if self.historial:
            r_prev = self.residual(*self.historial[-1])[core]
            r_act = self.residual(bw, bg)[core]
            self.volatilidad = float(np.mean(np.abs(r_act - r_prev) / np.maximum(r_prev, 1e-9)))
        self.bw, self.bg = bw, bg
        self.t += 1
        self.historial.append((bw.copy(), bg.copy()))

    def generar_solicitudes(self, n_r, n_s=None):
        """Rᵗ = {(Hᵢ, Sⱼ, Bₖ)}: N_r solicitudes simultáneas hacia los primeros n_s servidores."""
        n_s = n_s or len(self.servidores)
        hosts = self.rng.choice(self.hosts, n_r)
        servs = self.rng.choice(self.servidores[:n_s], n_r)
        B = self.rng.uniform(*MODELO['B_REQ_MBPS'], n_r)
        return [(str(h), str(s), float(b)) for h, s, b in zip(hosts, servs, B)]


class Evaluador:
    """f(Φᵗ) (Ec. 1–5) y violación de la restricción de ancho de banda (Ec. 6) sobre el estado actual de la red.

    Objetivo 3 (MODO_U):
      'paper'   → 1 − min_{e∈ℰ} ρₑ (Ec. 4 literal; degenera: casi constante, ver réplica Exp. 2)
      'codigo'  → (1/N_r) Σₖ max_{e∈pₖ} ρₑ (código oficial: utilización del cuello de botella de cada ruta)
      'media'   → 1 − ρ̄ (utilización media de la red)
      'activos' → 1 − min ρₑ sobre los enlaces usados
    """

    def __init__(self, red, solicitudes, modo_u=None):
        self.red = red
        self.modo_u = modo_u or MODELO['MODO_U']
        self.B = np.array([b for _, _, b in solicitudes])
        self.nr = len(solicitudes)
        self.residual = red.residual()
        self.core = red.es_core
        self.ln_ok = np.log1p(-red.loss)
        self._cache = {}

    def ids(self, ruta):
        """Ruta (tupla de nodos) → índices de aristas (cacheado)."""
        c = self._cache.get(ruta)
        if c is None:
            eid = self.red.eid
            c = np.fromiter((eid[(ruta[i], ruta[i + 1])] for i in range(len(ruta) - 1)), dtype=np.int64,
                            count=len(ruta) - 1)
            self._cache[ruta] = c
        return c

    def evaluar(self, rutas, detalle=False):
        red = self.red
        ids = [self.ids(r) for r in rutas]
        largos = np.fromiter((len(x) for x in ids), dtype=np.int64, count=self.nr)
        cat = np.concatenate(ids)
        off = np.zeros(self.nr, dtype=np.int64)
        off[1:] = np.cumsum(largos)[:-1]

        carga = red.bg + np.bincount(cat, weights=np.repeat(self.B, largos), minlength=red.E)
        rho = carga / red.bw
        cola = np.where(rho < 1, rho / np.maximum(1 - rho, 1e-9), np.inf)
        d_ef = red.delay + MODELO['TAU_MS'] * np.minimum(cola, MODELO['Q_MAX'])
        desborde = np.clip(1 - 1 / np.maximum(rho, 1e-12), 0, 1)
        ln_ok = self.ln_ok + np.log(np.maximum(1 - desborde, 1e-12))

        D = np.add.reduceat(d_ef[cat], off)                        # Ec. 2
        L = 1 - np.exp(np.add.reduceat(ln_ok[cat], off))           # Ec. 3
        Bk = np.minimum.reduceat(self.residual[cat], off)          # Ec. 1
        cv = float(np.sum(np.maximum(0.0, self.B - Bk) / self.B))  # Ec. 6 (violación normalizada)

        rho_c = np.minimum(rho, 1.0)
        rho_max_ruta = np.maximum.reduceat(rho_c[cat], off)
        if self.modo_u == 'codigo':
            f3 = rho_max_ruta.mean()
        elif self.modo_u == 'paper':
            f3 = 1.0 - rho_c[self.core].min()
        elif self.modo_u == 'activos':
            usados = np.zeros(red.E, dtype=bool)
            usados[cat] = True
            usados &= self.core
            f3 = 1.0 - (rho_c[usados].min() if usados.any() else 0.0)
        else:
            f3 = 1.0 - rho_c[self.core].mean()
        F = np.array([D.mean(), L.mean(), f3])                     # Ec. 5 / 11
        if detalle:
            return F, cv, dict(D=D, L=L, Bk=Bk, rho=rho, cat=cat, off=off, rho_max_ruta=rho_max_ruta)
        return F, cv


def solapamiento(red, ev, rutas):
    """Σₑ max(0, #flujos en e − 1) sobre el núcleo: criterio de elección final de GAMR (menor solapamiento)."""
    cat = np.concatenate([ev.ids(r) for r in rutas])
    cat = cat[red.es_core[cat]]
    return int(np.maximum(np.bincount(cat, minlength=red.E) - 1, 0).sum())


def evaluar_qos(red, solicitudes, rutas):
    """Métricas de red de una configuración instalada, sobre el estado ACTUAL de `red`."""
    ev = Evaluador(red, solicitudes, 'codigo')
    _, _, det = ev.evaluar(rutas, detalle=True)
    rho_c = det['rho'][red.es_core]
    usados = np.zeros(red.E, dtype=bool)
    usados[det['cat']] = True
    rho_max_flujo = np.maximum.reduceat(det['rho'][det['cat']], det['off'])
    return dict(delay_ms=float(det['D'].mean()),
                loss_pct=100 * float(det['L'].mean()),
                util_pct=100 * float(np.minimum(rho_c, 1).mean()),
                rho_max_pct=100 * float(np.minimum(rho_c, 1).max()),
                enlaces_usados_pct=100 * float(usados[red.es_core].mean()),
                enlaces_saturados=int((rho_c >= 1).sum()),
                satisf_bw_pct=100 * float(np.mean(rho_max_flujo <= 1.0)),
                saltos=float(np.mean([len(r) - 3 for r in rutas])))
