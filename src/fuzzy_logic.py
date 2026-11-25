"""Mini-librería de lógica difusa tipo Mamdani (sin dependencias externas, vectorizada con numpy).

- Funciones de pertenencia triangulares y trapezoidales.
- Reglas SI–ENTONCES con conector Y (mínimo) u O (máximo) y peso.
- Implicación por mínimo (recorte), agregación por máximo y defuzzificación por centroide.

Se evita scikit-fuzzy para que la reproducción no dependa de una librería externa poco mantenida.
"""
from dataclasses import dataclass, field

import numpy as np


def trimf(x, a, b, c):
    x = np.asarray(x, dtype=float)
    izq = np.where(b > a, (x - a) / max(b - a, 1e-12), (x >= b).astype(float))
    der = np.where(c > b, (c - x) / max(c - b, 1e-12), (x <= b).astype(float))
    return np.clip(np.minimum(izq, der), 0.0, 1.0)


def trapmf(x, a, b, c, d):
    x = np.asarray(x, dtype=float)
    izq = np.ones_like(x) if b <= a else (x - a) / (b - a)
    der = np.ones_like(x) if d <= c else (d - x) / (d - c)
    return np.clip(np.minimum(np.minimum(izq, 1.0), der), 0.0, 1.0)


_FORMAS = {'tri': trimf, 'trap': trapmf}


class VariableDifusa:
    """Variable lingüística: universo [lo, hi] y términos {nombre: ('tri'|'trap', parámetros)}."""

    def __init__(self, nombre, universo, terminos, puntos=201):
        self.nombre = nombre
        self.lo, self.hi = universo
        self.x = np.linspace(self.lo, self.hi, puntos)
        self.terminos = terminos

    def pertenencia(self, termino, x):
        forma, params = self.terminos[termino]
        return _FORMAS[forma](x, *params)

    def curvas(self):
        return {t: self.pertenencia(t, self.x) for t in self.terminos}


@dataclass
class Regla:
    antecedentes: list                     # [(variable, término), ...]
    consecuentes: dict                     # {variable_salida: término}
    conector: str = 'Y'                    # 'Y' = mínimo, 'O' = máximo
    peso: float = 1.0
    texto: str = field(default='', repr=False)

    def __post_init__(self):
        if not self.texto:
            sep = ' Y ' if self.conector == 'Y' else ' O '
            ant = sep.join(f'{v} es {t}' for v, t in self.antecedentes)
            con = ', '.join(f'{v} es {t}' for v, t in self.consecuentes.items())
            self.texto = f'SI {ant} ENTONCES {con}'


class SistemaMamdani:
    def __init__(self, nombre, entradas, salidas, reglas):
        self.nombre = nombre
        self.entradas = {v.nombre: v for v in entradas}
        self.salidas = {v.nombre: v for v in salidas}
        self.reglas = reglas

    def activaciones(self, **valores):
        """Grado de disparo de cada regla. Entradas escalares o arrays de igual forma."""
        forma = np.broadcast(*[np.asarray(v, dtype=float) for v in valores.values()]).shape
        grados = []
        for r in self.reglas:
            mus = [self.entradas[v].pertenencia(t, np.broadcast_to(np.clip(valores[v], self.entradas[v].lo,
                                                                            self.entradas[v].hi), forma))
                   for v, t in r.antecedentes]
            g = np.minimum.reduce(mus) if r.conector == 'Y' else np.maximum.reduce(mus)
            grados.append(r.peso * np.asarray(g, dtype=float))
        return np.array(grados), forma

    def evaluar(self, **valores):
        """Devuelve {salida: valor nítido} (centroide). Si las entradas son arrays, la salida también."""
        grados, forma = self.activaciones(**valores)
        grados = grados.reshape(len(self.reglas), -1)                      # (R, n)
        resultado = {}
        for nombre, var in self.salidas.items():
            agregado = np.zeros((grados.shape[1], len(var.x)))
            for r, g in zip(self.reglas, grados):
                if nombre in r.consecuentes:
                    mf = var.pertenencia(r.consecuentes[nombre], var.x)    # (U,)
                    agregado = np.maximum(agregado, np.minimum(g[:, None], mf[None, :]))
            masa = agregado.sum(axis=1)
            centro = np.where(masa > 1e-12, (agregado * var.x).sum(axis=1) / np.maximum(masa, 1e-12),
                              (var.lo + var.hi) / 2)
            resultado[nombre] = centro.reshape(forma) if forma else float(centro[0])
        return resultado

    def superficie(self, var_x, var_y, salida, fijas=None, puntos=41):
        """Superficie de control salida(var_x, var_y) con el resto de entradas fijas."""
        fijas = fijas or {}
        X, Y = np.meshgrid(np.linspace(self.entradas[var_x].lo, self.entradas[var_x].hi, puntos),
                           np.linspace(self.entradas[var_y].lo, self.entradas[var_y].hi, puntos))
        valores = {var_x: X, var_y: Y}
        for k, v in self.entradas.items():
            if k not in valores:
                valores[k] = np.full_like(X, fijas.get(k, (v.lo + v.hi) / 2))
        return X, Y, self.evaluar(**valores)[salida]

    def tabla_reglas(self):
        return [r.texto for r in self.reglas]
