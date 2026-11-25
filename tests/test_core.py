"""Pruebas rápidas de las piezas críticas:  python -m pytest -q"""
import random
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from data.topologies import cargar_topologia                                      # noqa: E402
from src.gamr_original import GAMR, eliminar_ciclos, cruce_multipunto, rsbi        # noqa: E402
from src.metrics_stats import hipervolumen, igd, ordenamiento_no_dominado         # noqa: E402
from src.network_model import RedSDN                                               # noqa: E402
from src.proposed_method import FGAMR, FIS1, FIS2, construir_guia, rsbi_guiado    # noqa: E402


@pytest.fixture(scope='module')
def red():
    g, _ = cargar_topologia('Oxford')
    return RedSDN(g, 2, beta=0.2, semilla=1)


def es_camino_valido(red, ruta, h, s):
    return (ruta[0] == h and ruta[-1] == s and len(set(ruta)) == len(ruta)
            and all((ruta[i], ruta[i + 1]) in red.eid for i in range(len(ruta) - 1)))


def test_hipervolumen_contra_monte_carlo():
    rng = np.random.default_rng(0)
    P = rng.random((25, 3)) * 0.9
    m = rng.random((200_000, 3))
    dom = np.zeros(len(m), bool)
    for p in P:
        dom |= np.all(m >= p, axis=1)
    assert abs(hipervolumen(P) - dom.mean()) < 0.01


def test_igd_cero_si_frentes_iguales():
    F = np.array([[0.1, 0.5, 0.3], [0.4, 0.2, 0.1]])
    assert igd(F, F) == 0.0


def test_ordenamiento_no_dominado():
    frentes = ordenamiento_no_dominado(np.array([[1, 2, 3], [2, 1, 3], [2, 2, 4], [3, 3, 5]]))
    assert [list(f) for f in frentes] == [[0, 1], [2], [3]]


def test_eliminar_ciclos():
    assert eliminar_ciclos(('H', 'a', 'b', 'c', 'b', 'd', 'S')) == ('H', 'a', 'b', 'd', 'S')


def test_operadores_producen_caminos_validos(red):
    rnd = random.Random(3)
    h, s = red.hosts[4], red.servidores[0]
    guia = construir_guia(red, [s])
    for _ in range(50):
        p1, p2 = rsbi(red, h, s, rnd), rsbi_guiado(red, h, s, rnd, guia)
        assert es_camino_valido(red, p1, h, s) and es_camino_valido(red, p2, h, s)
        for c in cruce_multipunto(p1, p2, 1.0, rnd):
            assert es_camino_valido(red, c, h, s)


def test_fis_salidas_en_rango():
    w = FIS1.evaluar(progreso=np.array([1.0, 0.0]), retardo=np.array([0.1, 0.9]), perdida=np.array([0.1, 0.9]),
                     carga=np.array([0.05, 0.6]))['deseabilidad']
    assert w[0] > 0.8 > 0.2 > w[1]
    a = FIS2.evaluar(delay=np.array([0.0, 1.0]), perdida=np.array([0.0, 1.0]))['aptitud']
    assert a[0] > a[1]


def test_fgamr_resuelve_y_es_reproducible(red):
    sol = red.generar_solicitudes(8, 2)
    params = dict(G_MAX=15, N=20)
    r1 = FGAMR(red, params=params, semilla=7).resolver(sol)
    r2 = FGAMR(red, params=params, semilla=7).resolver(sol)
    assert r1['rutas'] == r2['rutas']
    for (h, s, _), ruta in zip(sol, r1['rutas']):
        assert es_camino_valido(red, ruta, h, s)
    assert GAMR(red, params=params, semilla=7).resolver(sol)['generaciones'] >= 1
