### Resultados de la réplica (modo COMPLETO)

**GAMR vs NSGA-II (intervalos con memoria, Exp. 3)** — paper: HV +3.4 a 22.8 %, IGD −33 a 86 %, tiempo −14.4 % vs NSGA-II
- Chinanet: HV 0.694 vs 0.691 (+0.5 %), IGD 0.0410 vs 0.0420 (-2.3 %), tiempo 2.18 s vs 2.46 s (-11.2 %), generaciones 63 vs 68
- Oxford: HV 0.670 vs 0.673 (-0.4 %), IGD 0.0384 vs 0.0347 (+10.5 %), tiempo 1.09 s vs 1.33 s (-17.7 %), generaciones 36 vs 45

**Escenario crítico N_s=2, N_r=100 (Exp. 4)** — paper (Oxford): delay MH 118.91 / LCP-WAC 105.64 / GAMR 76.92 ms
- Chinanet: delay MH 285.9 / LCP-WAC* 278.2 / GAMR 272.9 ms (GAMR -4.6 % vs MH); pérdida MH 24.5 / LCP-WAC* 24.1 / GAMR 24.5 %
- Oxford: delay MH 413.6 / LCP-WAC* 350.9 / GAMR 348.1 ms (GAMR -15.8 % vs MH); pérdida MH 19.3 / LCP-WAC* 17.5 / GAMR 16.2 %

**Robustez a β (Exp. 5, Chinanet)** — paper: con β=55 % pérdida MH 88.4 % / LCP-WAC 76.4 % vs GAMR ~15 %
- β=0 %: delay MH 244.6 / LCP-WAC* 210.4 / GAMR 215.9 ms; pérdida MH 9.8 / LCP-WAC* 8.5 / GAMR 9.1 %
- β=5 %: delay MH 229.8 / LCP-WAC* 218.3 / GAMR 215.8 ms; pérdida MH 18.8 / LCP-WAC* 18.0 / GAMR 18.9 %
- β=20 %: delay MH 230.9 / LCP-WAC* 221.8 / GAMR 217.8 ms; pérdida MH 18.3 / LCP-WAC* 17.5 / GAMR 18.3 %
- β=55 %: delay MH 249.0 / LCP-WAC* 248.0 / GAMR 230.3 ms; pérdida MH 18.5 / LCP-WAC* 18.3 / GAMR 18.1 %

**Sensibilidad a α (Exp. 6)**: mejor HV con α=0.25 (0.698); menor tiempo con α=1.0 (0.66 s); α=0.5 → HV 0.695, 1.06 s