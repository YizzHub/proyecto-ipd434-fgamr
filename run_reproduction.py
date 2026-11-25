"""Script maestro: ejecuta (o carga) los experimentos y regenera todas las tablas y figuras del informe.

    python run_reproduction.py                    # modo completo (30 semillas E1, 10 en E2/E3) ≈ 1.5 h con 7 procesos
    python run_reproduction.py --modo rapido      # prueba de humo ≈ 5 min (resultados en results/_rapido/)
    python run_reproduction.py --solo-reporte     # regenera tablas/figuras desde results/raw_logs/
    python run_reproduction.py --jobs 4 --experimentos E1

Todo es determinista dado el modo: las semillas de red y de cada algoritmo se derivan de la semilla de la tarea.
"""
import argparse
import platform
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

from src.experiments import cargar_o_ejecutar          # noqa: E402
from src.reporting import generar_reporte              # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--modo', choices=['completo', 'rapido'], default='completo')
    ap.add_argument('--jobs', type=int, default=None, help='procesos en paralelo (por defecto: núcleos − 1)')
    ap.add_argument('--experimentos', nargs='+', default=['E1', 'E2', 'E3'], choices=['E1', 'E2', 'E3'])
    ap.add_argument('--recalcular', action='store_true', help='ignora los CSV crudos existentes')
    ap.add_argument('--solo-reporte', action='store_true', help='no ejecuta; solo regenera tablas y figuras')
    args = ap.parse_args()

    base = RAIZ / 'results' if args.modo == 'completo' else RAIZ / 'results' / '_rapido'
    dir_crudos, dir_tablas, dir_figs = base / 'raw_logs', base / 'tables', base / 'figures'
    print(f'Python {platform.python_version()} · modo {args.modo} · salida {base}')
    t0 = time.time()
    if args.solo_reporte and not (dir_crudos / 'resultados_algoritmos.csv').exists():
        sys.exit(f'No hay resultados crudos en {dir_crudos}. Ejecuta primero sin --solo-reporte.')
    df, df_sel = cargar_o_ejecutar(dir_crudos, args.modo, args.jobs, args.recalcular and not args.solo_reporte,
                                   tuple(args.experimentos))
    generar_reporte(df, df_sel, dir_tablas, dir_figs)
    print(f'Listo en {(time.time() - t0) / 60:.1f} min.')


if __name__ == '__main__':
    main()
