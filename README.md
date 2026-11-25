# F-GAMR: exploración guiada por lógica difusa y selección difusa del frente de Pareto para el enrutamiento multi-objetivo dinámico en SDN

Proyecto aplicado final — **IPD434 Seminario de Soft Computing**, Universidad Técnica Federico Santa María, 2026-2.
Autor: **[NOMBRE COMPLETO]** · Rol USM: **[ROL USM]**

Extensión del artículo:

> H.-A. Tran, C.-S. Duong, T.-D. Bui, V. Tong, H. T. T. Binh, "GAMR: Revolutionizing Multi-Objective Routing in SDN
> Networks With Dynamic Genetic Algorithms," *IEEE Trans. Emerging Topics in Computational Intelligence*, vol. 9,
> no. 4, pp. 3147–3161, 2025, doi: 10.1109/TETCI.2025.3543836. Código original: <https://github.com/meodaiduoi/GAMR>

## Contribución

GAMR enruta simultáneamente N_r solicitudes en una red SDN con un NSGA-II dinámico (memoria PRSM, inicialización
híbrida y parada por hipervolumen). Sin embargo, explora a ciegas: la caminata aleatoria (RSBI) y la mutación eligen
vecinos de forma uniforme. Además, instala la solución del frente que tiene menor solapamiento de enlaces, sin mirar la
QoS que percibe el usuario. **F-GAMR** agrega dos sistemas difusos Mamdani interpretables, que no requieren
entrenamiento:

| Componente | Función |
|---|---|
| **FIS-1** — deseabilidad QoS (10 reglas) | Puntúa cada movimiento u→v según *progreso hacia el servidor, retardo, pérdida y carga medida* y guía RSBI y la mutación con una ruleta `P(v) ∝ w^κ + ε` (κ = 2, ε = 0.01) |
| **FIS-2** — selector de compromiso (6 reglas) | Elige del frente de Pareto la solución con mejor compromiso difuso entre retardo y pérdida |

El resto del algoritmo es idéntico a GAMR. El estudio de ablación (solo FIS-1 / solo FIS-2) aísla el aporte de cada
componente. Los parámetros se calibraron en semillas de validación (500–503), disjuntas de las de evaluación (0–29).
Un controlador difuso de α/p_m, propuesto inicialmente, se probó y se descartó con evidencia
(ver `scripts/calibracion.py`).

## Estructura

```
F-GAMR.ipynb               Notebook principal: narrativa, método, calibración y resultados
run_reproduction.py        Script maestro de 1 comando (experimentos → tablas → figuras)
data/topologies.py         Oxford y Chinanet (Internet Topology Zoo; .gml incluidos)
src/network_model.py       Plano de datos SDN simulado, Ec. 1–6 y 14, QoS medida
src/gamr_original.py       GAMR fiel al paper (Sub-Alg. 1–6, Ec. 12–13)
src/baselines.py           Min-Hop, QoS-Dijkstra, LCP-WAC* (proxy sin LSTM) y NSGA-II (α = 0, sin memoria)
src/fuzzy_logic.py         Mini-librería Mamdani vectorizada (sin dependencias externas)
src/proposed_method.py     F-GAMR (FIS-1 + FIS-2) y modos de ablación
src/metrics_stats.py       Hipervolumen exacto 3D, IGD, Wilcoxon pareado y tablas LaTeX
src/experiments.py         Protocolo experimental paralelo (E1–E3)
src/reporting.py, plots.py Tablas y figuras del informe
scripts/calibracion.py     Calibración en semillas de validación
tests/test_core.py         Pruebas unitarias (pytest)
notebooks/                 Anexo: réplica de GAMR del seminario (con salidas)
results/                   raw_logs/, tables/, figures/, calibracion/, replicacion_seminario/
report_ieee/               Informe IEEEtran (≤ 5 páginas)
presentation/              Diapositivas de la presentación final
```

## Reproducción paso a paso

Se requiere Python 3.10–3.12. Fue probado con Python 3.12.3 en Windows 11.

```bash
# 1. Entorno
python -m venv .venv
.venv\Scripts\activate            # Windows   |   source .venv/bin/activate  (Linux/macOS)
pip install -r requirements.txt

# 2. Pruebas (< 10 s)
python -m pytest -q

# 3. Prueba de humo del pipeline completo (≈ 5 min, resultados en results/_rapido/, sin validez estadística)
python run_reproduction.py --modo rapido

# 4. Experimentos finales: 30 semillas en E1 y 10 en E2/E3 (≈ 1.5 h con 7 procesos)
python run_reproduction.py                 # --jobs N para elegir el número de procesos

# 5. Solo regenerar tablas y figuras desde results/raw_logs/
python run_reproduction.py --solo-reporte

# 6. (Opcional) calibración en semillas de validación (≈ 15 min)
python scripts/calibracion.py
```

El notebook `F-GAMR.ipynb` (con `MODO = 'completo'`) **carga** los resultados de `results/raw_logs/` si existen; si
no existen, ejecuta los experimentos. Hay que abrirlo con el directorio de trabajo en la raíz del repositorio.

### Salidas

| Carpeta | Contenido |
|---|---|
| `results/raw_logs/` | `resultados_algoritmos.csv` (una fila por semilla × intervalo × algoritmo) y `resultados_selectores.csv` |
| `results/tables/` | Tablas media ± std (CSV), pruebas de Wilcoxon, `E1_moo.tex` y `E1_qos.tex` (IEEE) y `resumen_resultados.md` |
| `results/figures/` | Figuras PDF y PNG (300 DPI) de E1–E3 y figuras ilustrativas del notebook |

## Protocolo experimental

| | E1 (principal + ablación) | E2 (escalabilidad) | E3 (desorden β) |
|---|---|---|---|
| Topología | Oxford, Chinanet | Oxford | Chinanet |
| N_s / N_r | 2 / 50 | 2 / {10, 20, 50, 100} | 2 / 100 |
| β | {5 %, 55 %} | 20 % | {0, 5, 20, 55 %} |
| Algoritmos | MH, QoS-Dijkstra, NSGA-II, GAMR, solo FIS-1, solo FIS-2, F-GAMR | MH, QoS-Dijkstra, GAMR, F-GAMR | MH, LCP-WAC*, GAMR, F-GAMR |
| Semillas | 30 | 10 | 10 |

Cada semilla es una secuencia dinámica de 4 intervalos. En cada intervalo todos los algoritmos resuelven la misma
instancia. Las métricas usan los intervalos 2–4 (con la memoria activa) y la QoS se mide en el estado **realizado**
de la red (Δᵗ⁺¹). Las métricas son HV, IGD, tiempo, retardo, pérdida, utilización máxima y satisfacción de ancho de
banda. Se reporta media ± std y Wilcoxon pareado por semilla.

## Limitaciones

- El plano de datos es un modelo fluido (cola M/M/1 acotada más pérdida por desborde), no Mininet/Ryu, así que los
  valores absolutos no son comparables con el paper.
- LCP-WAC* es un proxy sin LSTM.
- Los tiempos son de Python puro.

Detalles en la Sección 15 del notebook.

## Licencia

MIT (ver `LICENSE`).
