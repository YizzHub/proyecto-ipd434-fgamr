"""Topologías reales del Internet Topology Zoo usadas por GAMR (Tran et al., 2025): Oxford y Chinanet.

Los archivos .gml oficiales vienen incluidos en esta carpeta. Si faltan, se descargan del mirror
oficial del Topology Zoo; sin conexión se usa un grafo sintético conexo del mismo tamaño.
"""
from functools import lru_cache
from pathlib import Path
import urllib.request

import networkx as nx
import pandas as pd

DIR_DATOS = Path(__file__).resolve().parent
URLS_ZOO = ['https://raw.githubusercontent.com/mroughan/InternetTopologyZoo/master/gml/{}.gml',
            'http://www.topology-zoo.org/files/{}.gml']
TAMANO_PAPER = {'Oxford': (19, 26), 'Chinanet': (44, 66)}   # (nodos, enlaces) reportados / respaldo sintético


@lru_cache(maxsize=None)
def cargar_topologia(nombre: str, semilla: int = 2025):
    """Devuelve (grafo de switches con nodos 'M1'..'Mn', fuente). Cacheado por proceso."""
    ruta = DIR_DATOS / f'{nombre}.gml'
    if not ruta.exists():
        for url in URLS_ZOO:
            try:
                urllib.request.urlretrieve(url.format(nombre), ruta)
                break
            except Exception:
                continue
    if ruta.exists():
        g = nx.Graph(nx.read_gml(ruta, label='id'))
        fuente = 'Topology Zoo'
    else:
        n, m = TAMANO_PAPER[nombre]
        k = 0
        while True:
            g = nx.gnm_random_graph(n, m, seed=semilla + k)
            if nx.is_connected(g):
                break
            k += 1
        fuente = 'sintético (sin conexión)'
    g.remove_edges_from(list(nx.selfloop_edges(g)))
    g = g.subgraph(max(nx.connected_components(g), key=len)).copy()
    mapeo = {v: f'M{i + 1}' for i, v in enumerate(sorted(g.nodes()))}
    return nx.relabel_nodes(g, mapeo), fuente


def resumen_topologias(nombres=('Oxford', 'Chinanet')) -> pd.DataFrame:
    filas = []
    for nombre in nombres:
        g, fuente = cargar_topologia(nombre)
        grados = [d for _, d in g.degree()]
        filas.append(dict(topologia=nombre, fuente=fuente, switches=g.number_of_nodes(), enlaces=g.number_of_edges(),
                          grado_medio=round(sum(grados) / len(grados), 2), diametro=nx.diameter(g),
                          triangulos=sum(nx.triangles(g).values()) // 3))
    return pd.DataFrame(filas).set_index('topologia')
