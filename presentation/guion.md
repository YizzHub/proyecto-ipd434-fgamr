# Guion oral — F-GAMR

**Duración planificada: 14:00 minutos**, con 1 minuto de margen hasta el máximo de 15 minutos. Preguntas aparte. Los tiempos incluyen las demostraciones; no se necesita ejecutar experimentos.

Abre [la presentación](index.html). Flechas para navegar, **G** para el guion de la diapositiva, **Animación** para pausar movimientos, **Pantalla** para pantalla completa y **PDF** para imprimir todas las diapositivas. El cronómetro se inicia manualmente.

Usa este texto como apoyo: no leas todo literalmente. Prioriza explicar el gráfico y su conclusión. Las animaciones y ejemplos están identificados como didácticos; los resultados provienen de las tablas ejecutadas.

## Distribución del tiempo

| Diapositiva | Tema | Tiempo | Acumulado |
|---|---|---:|---:|
| 1 | Problema y propuesta | 0:35 | 0:35 |
| 2 | Qué es SDN | 1:00 | 1:35 |
| 3 | QoS y utilización | 1:05 | 2:40 |
| 4 | Pareto, HV e IGD | 1:15 | 3:55 |
| 5 | GAMR y parada | 1:05 | 5:00 |
| 6 | Contribución y curso | 0:40 | 5:40 |
| 7 | FIS-1 | 1:05 | 6:45 |
| 8 | FIS-2 | 1:00 | 7:45 |
| 9 | Protocolo experimental | 1:05 | 8:50 |
| 10 | Frente y tiempo | 1:05 | 9:55 |
| 11 | QoS y compromiso | 1:05 | 11:00 |
| 12 | Ablación | 0:55 | 11:55 |
| 13 | Carga y desorden | 1:15 | 13:10 |
| 14 | Conclusiones y límites | 0:50 | **14:00** |

## 1. No basta con la ruta más corta — 35 s

“Una ruta corta puede ser mala si muchas conexiones usan el mismo enlace. Mi proyecto extiende GAMR para incorporar conocimiento sobre la calidad de servicio en dos decisiones: cómo explorar rutas y cuál de las alternativas instalar.

La propuesta se llama F-GAMR y combina algoritmos evolutivos y lógica difusa, dos técnicas del curso. Primero explicaré la red y las métricas; después el método, los resultados y sus límites.”

**Señala:** el enlace compartido de arriba y la alternativa de abajo. El dibujo no es un resultado medido.

## 2. Qué es una red SDN — 60 s

“SDN significa redes definidas por software. Su idea es separar quién decide las rutas de quién reenvía paquetes. Los switches forman el plano de datos: transportan paquetes siguiendo reglas.

El controlador obtiene mediciones y configura los switches. Por encima hay aplicaciones que deciden políticas: ahí se ubicaría F-GAMR. OpenFlow permite comunicar control y datos.

Mi implementación no usa un controlador real: simula estados y rutas en Python. La visión global permite considerar cómo interfieren varias solicitudes simultáneas. El desafío es que la red cambia y las mediciones pueden quedar obsoletas mientras se calcula una decisión.”

**Señala:** los tres planos; diferencia las líneas de control de la circulación de datos.

## 3. Qué medimos en una ruta — 65 s

“QoS es calidad de servicio. Retardo es el tiempo de llegada, en milisegundos, y se suma por enlace. Pérdida es la fracción que no llega: combinamos la supervivencia de cada enlace. Dos enlaces con diez por ciento de pérdida producen diecinueve, no veinte.

La capacidad disponible depende del enlace con menos capacidad residual, después de la carga de fondo.

Ochenta megabits por segundo sobre cien son ochenta por ciento de utilización. Cerca de la saturación aumenta la espera; superar la capacidad provoca pérdida por desborde en el modelo.

GAMR minimiza retardo, pérdida y utilización del cuello de botella conjuntamente. La restricción individual de capacidad no garantiza que todas las solicitudes juntas quepan.”

**Interacción:** mueve la carga de 80 a 110 Mbps; vuelve a 80 antes de imprimir.

## 4. Pareto, HV e IGD — 75 s

“Una solución domina a otra si no es peor en ningún objetivo y es mejor en al menos uno. Las alternativas que nadie domina forman el frente de Pareto. Una puede ser rápida y otra perder menos paquetes.

El gráfico muestra dos objetivos para explicarlo; el experimento tiene tres.

El hipervolumen mide el volumen cubierto hasta una referencia desfavorable. Mayor es mejor. La unión de las regiones se cuenta una sola vez. La referencia y la escala deben ser comparables.

IGD mide distancia: para cada punto del frente de referencia, buscamos la solución encontrada más cercana y promediamos esas distancias. Menor es mejor.

La referencia experimental es la unión no dominada de resultados, no el óptimo verdadero. Estas métricas evalúan el conjunto de opciones, no la configuración finalmente instalada.”

**Interacción:** pulsa HV y después IGD. Añade: “IGD se usa para evaluar; no detiene GAMR”.

## 5. GAMR y su parada — 65 s

“AG significa algoritmo genético. Cada individuo contiene una ruta por solicitud, y esas rutas se evalúan juntas.

GAMR inicia cien configuraciones combinando rutas de memoria y caminatas aleatorias. Alfa vale 0.5 y controla la probabilidad de reutilización. Luego cruza y muta rutas, y NSGA-II conserva calidad y diversidad.

La búsqueda termina si el hipervolumen cambia menos de diez a la menos cuatro respecto de diez generaciones antes, o al llegar a quinientas.

Detener GAMR significa terminar el cálculo del intervalo: se instala una configuración y el tráfico continúa. En el siguiente intervalo se optimiza nuevamente. No certifica un óptimo global.

Abordo dos debilidades: elegir vecinos sin guía QoS y escoger finalmente por menor solapamiento.”

**Señala:** población → operadores → selección → instalación. La curva es conceptual, no una traza experimental.

## 6. Qué aporto y cómo se relaciona con el curso — 40 s

“No reemplazo GAMR ni afirmo inventar la hibridación genético-difusa. Aporto dos sistemas en decisiones concretas.

FIS-1 guía construcción y mutación: P1 pregunta si mejora el frente y reduce tiempo. FIS-2 selecciona la configuración: P2 pregunta si reduce pérdida con un compromiso aceptable.

Memoria, cruce, selección y parada se conservan. La relación con el curso es búsqueda evolutiva más inferencia difusa interpretable, sin entrenamiento.”

## 7. FIS-1: guiar sin prohibir — 65 s

“FIS significa sistema de inferencia difusa. FIS-1 recibe progreso hacia el servidor, retardo, pérdida y carga de fondo. Usa etiquetas graduales, como retardo bajo o carga alta; una pertenencia de 0.7 no es una probabilidad.

Diez reglas Mamdani combinan esas etiquetas y producen una deseabilidad mediante centroide. Por ejemplo: si el salto acerca al servidor y tiene retardo y pérdida bajos, su deseabilidad es muy alta.

Después convertimos las puntuaciones en probabilidades de una ruleta: elevamos a kappa, sumamos epsilon y normalizamos. Kappa aumenta la preferencia; epsilon mantiene toda opción válida posible.

En el experimento usamos kappa dos, calibrado con semillas independientes. También guiamos la mutación considerando los dos enlaces de la inserción.”

**Interacción:** compara κ=1, 2 y 4 y vuelve a 2. Las puntuaciones 0.8, 0.5 y 0.2 son ilustrativas; solo la transformación de ruleta se calcula aquí.

## 8. FIS-2: elegir un compromiso — 60 s

“FIS-2 actúa al finalizar la evolución. Toma retardo y pérdida medios de cada configuración y los normaliza entre mínimo y máximo dentro del frente: el menor valor corresponde a cero y el mayor a uno.

Seis reglas favorecen ambos bajos y penalizan valores altos. La superficie muestra esa política. Elegimos la mayor puntuación; si hay empate, el menor retardo.

No genera nuevas rutas ni optimiza explícitamente la utilización, que puede aumentar. Su puntuación depende de las alternativas disponibles y no garantiza QoS en el estado siguiente.

Para aislar su efecto también aplicamos diferentes selectores sobre exactamente los mismos frentes.”

**Señala:** la normalización y la zona favorable de la superficie.

## 9. Cómo se evaluó — 65 s

“E1 compara el método y sus componentes en dos topologías con treinta semillas y cincuenta solicitudes. E2 aumenta solicitudes en Oxford; E3 aumenta desorden de capacidad en Chinanet, ambos con diez semillas.

Beta controla perturbaciones de capacidad; no es un parámetro del algoritmo ni una medida de tráfico. Con beta cero, las capacidades son fijas e iguales; la carga de fondo todavía cambia.

Todos reciben las mismas solicitudes y estados. La QoS se mide después de evolucionar la red, no solamente donde se optimizó.

Cada semilla aporta una observación: promedio de los intervalos dos a cuatro, descartando el primero. Reportamos media y desviación estándar y usamos Wilcoxon pareado. La calibración usa otras semillas.

LCP-WAC estrella es un proxy histórico, no la LSTM original.”

## 10. Calidad del frente y tiempo — 65 s

“En Chinanet, F-GAMR mejora hipervolumen entre 6.8 y 8.2 por ciento y reduce IGD entre 19.6 y 24.7 por ciento, con significancia en las pruebas pareadas.

En Oxford no hay mejora significativa del frente; IGD incluso empeora en promedio.

En ambas redes baja el tiempo entre 7.3 y 18.3 por ciento. Los segmentos muestran desviación estándar entre semillas, no intervalos de confianza.

El tiempo corresponde a una configuración completa. La mejora es relativa: no demuestra operación en tiempo real.

Frente a NSGA-II también hay mejora de frente y tiempo, pero nuestra pregunta central es qué añade a GAMR.”

**Señala:** Chinanet en HV; luego ambas redes en tiempo. No confundas solapamiento de desviaciones estándar con la prueba pareada.

## 11. Pérdida y compromiso — 65 s

“En E1, F-GAMR reduce pérdida en los cuatro escenarios: entre 2.8 y 6.1 por ciento relativo frente a GAMR.

El ejemplo aclara unidades: pasar de 10.77 a 10.11 por ciento resta 0.66 puntos porcentuales. Dividiendo por la pérdida inicial, la reducción relativa es 6.1 por ciento. No son seis puntos.

El costo es un aumento de retardo entre 0.3 y 1.6 por ciento. Solo Oxford con beta cinco resulta significativo en esa métrica.

Además puede aumentar utilización máxima. La conclusión es un compromiso de QoS, no ganar todas las métricas.”

## 12. Qué aporta cada componente — 55 s

“La ablación retira un componente y observa qué cambia. En este escenario, solo FIS-1 aumenta HV y reduce tiempo significativamente, pero no reduce pérdida. Solo FIS-2 reduce pérdida y no cambia significativamente el frente.

La combinación reúne ambos beneficios. FIS-2 actúa después de la búsqueda, aunque la configuración que deja en memoria puede influir en intervalos posteriores.

Por eso también comparamos selectores sobre los mismos frentes. FIS-2 reduce pérdida a cambio de algo de retardo frente al selector original.

Esta separación explica el resultado mejor que decir que todo mejora.”

**Señala:** las celdas azules; en esta tabla representan diferencias significativas respecto de GAMR.

## 13. Carga y desorden — 75 s

“En E2, las heurísticas se degradan al crecer las solicitudes. Con cien, Min-Hop llega a 24.5 por ciento de pérdida y QoS-Dijkstra a 29.7; los evolutivos quedan alrededor de 14.5.

F-GAMR reduce significativamente pérdida respecto de GAMR con diez, veinte y cincuenta solicitudes, pero no con cien. Aun tarda 10.52 segundos por configuración de cien solicitudes.

En E3, beta cero fija capacidad homogénea, no carga de fondo. El proxy histórico tiene allí la menor media. Con desorden, F-GAMR tiene menores medias que el proxy, sin demostrar significancia frente a él.

Frente a GAMR, la ventaja sí es significativa hasta beta veinte, pero no en cincuenta y cinco. La alta variabilidad y el cambio entre medición y realización limitan la utilidad del selector.”

**Interacción:** muestra brevemente las bandas ±DE. No son intervalos de confianza ni pruebas de significancia.

## 14. Conclusión y límites — 50 s

“Respondo P1: mejora el frente en Chinanet y reduce tiempo, pero no mejora significativamente el frente en Oxford. Respondo P2: reduce pérdida en E1 con un pequeño costo de retardo; el beneficio se debilita con alta carga o cambios fuertes.

La contribución es conocimiento interpretable en dos decisiones, no una mejora universal. Las limitaciones son simulación fluida, proxy sin LSTM, dos topologías y pruebas múltiples sin ajuste.

Probamos un controlador adaptativo de alfa y lo descartamos; no ocultamos el resultado negativo.

El siguiente paso es Mininet con TCP y kappa adaptativo para preservar diversidad. El repositorio contiene código, datos y resultados; debemos verificar su acceso público. Gracias.”

## Preguntas de defensa

### ¿Cuál es la contribución original?
Insertar una guía QoS Mamdani en la construcción y mutación de GAMR y un selector de compromiso al final, con evaluación separada de ambos aportes. Ni GAMR, ni NSGA-II, ni Mamdani son invenciones propias.

### ¿Qué representa un individuo?
Una configuración con una ruta por cada solicitud simultánea. Sus objetivos son promedios del conjunto; no se optimiza cada ruta independientemente.

### ¿Por qué usar lógica difusa y no un predictor neuronal?
Permite reglas interpretables sin entrenamiento ni datos etiquetados. Eso no prueba superioridad frente a redes neuronales: no se comparó con la LSTM original.

### ¿Qué hace Mamdani exactamente?
Convierte valores en pertenencias; combina antecedentes con mínimo, recorta consecuentes, agrega por máximo y calcula centroide. La puntuación difusa se transforma luego en probabilidad de selección en FIS-1.

### ¿Qué hacen α, β, κ y ε?
- **α=0.5:** probabilidad de inicialización apoyada en memoria.
- **β:** desorden del ancho de banda del escenario. Con β>0, perturbación respecto de la capacidad base hasta ±β; con β=0, el simulador usa capacidades iguales y fijas.
- **κ=2:** intensidad de preferencia por puntuaciones altas en la ruleta.
- **ε=0.01:** mantiene probabilidad positiva para vecinos válidos.

### ¿Cuándo se detiene GAMR?
Desde la generación 10 compara HV actual con HV de diez generaciones antes. Si la diferencia absoluta es menor que 10⁻⁴ termina esa búsqueda, o lo hace al máximo de 500. Instala rutas y continúa el tráfico. Se optimiza nuevamente en el siguiente intervalo. IGD no interviene en esa parada.

### ¿Parar antes significa encontrar el óptimo?
No. Significa que el indicador se ha estabilizado según esa ventana y tolerancia. Puede existir una solución mejor no explorada, especialmente si se pierde diversidad.

### ¿HV e IGD tienen unidades de red?
No aquí: se calculan con objetivos normalizados y escalas conjuntas por instancia. HV depende de la referencia; IGD de la escala y del frente de referencia. No son retardo ni pérdida de una ruta.

### ¿Se conoce el verdadero Pareto?
No. La referencia IGD es empírica: no dominados de la unión de resultados evolutivos. Puede favorecer a los métodos incluidos y no certifica cercanía al óptimo verdadero.

### ¿Por qué no minimizar únicamente retardo?
Puede elegir rutas rápidas con más pérdida. Sobre los mismos frentes de GAMR, mínimo retardo reduce retardo 1.3–2.3% pero aumenta pérdida 2.1–3.3% frente a menor solapamiento. FIS-2 explicita otro compromiso.

### ¿FIS-2 domina a las soluciones del mismo frente?
No se debe afirmar eso. En tres escenarios tiene menores medias de retardo y pérdida realizados que el selector llamado punto rodilla. Eso ocurre después de instalar y cambiar la red, y no demuestra dominancia en los tres objetivos del frente.

### ¿Por qué Oxford no mejora en HV e IGD?
Tiene menos alternativas y la guía puede concentrar exploración. En una demostración se observaron 22 rutas iniciales distintas frente a 36. Es una explicación plausible, no una prueba causal general para todas las topologías.

### ¿Qué significa p<0.05?
Bajo la hipótesis nula de la prueba, datos al menos tan extremos serían poco compatibles con ella. No significa 95% de probabilidad de que el método sea mejor. La prueba es pareada por semilla y no se corrigieron comparaciones múltiples.

### ¿Por qué las barras de desviación estándar se solapan si hay significancia?
La desviación estándar refleja variación entre instancias. Wilcoxon evalúa las diferencias dentro de cada par: ambos métodos pueden variar mucho con la misma semilla y aun mostrar una diferencia consistente.

### ¿La desviación estándar es un intervalo de confianza?
No. Describe dispersión entre semillas. Un intervalo de confianza cuantificaría incertidumbre de una estimación y requeriría otro cálculo.

### ¿Es un método de tiempo real?
No está demostrado. Los tiempos son Python y segundos por configuración. Con 100 solicitudes en E2 tarda 10.52 ± 1.87 s; GAMR, 12.92 ± 1.73 s. Hay ahorro relativo, no evidencia de latencia subsegundo.

### ¿Con β=0 el predictor conoce todo?
Solo predice exactamente la capacidad fija en este modelo. La carga de fondo todavía cambia. Además, β=0 usa capacidad homogénea; la comparación con β>0 mezcla ese cambio de homogeneidad con la perturbación temporal. Es una limitación del diseño heredado.

### ¿Qué se simplificó respecto del paper?
Se reemplazó el plano de datos real por un modelo fluido, se usó el objetivo de utilización del código oficial y LCP-WAC* es un proxy sin LSTM. Las cifras no son una réplica directa del rendimiento físico del artículo.

### ¿Qué restricción de ancho de banda se evalúa?
La demanda individual no debe superar el residual mínimo de la ruta, calculado después de carga de fondo. Esa condición no reserva conjuntamente capacidad para todos los flujos; la carga agregada se refleja en utilización, cola y pérdida.

### ¿Qué probarías a continuación?
Más topologías, calibración más amplia y ajuste de comparaciones múltiples; kappa según conectividad; Mininet/Ryu con TCP y medición real de la latencia de decisión e instalación.

## Correspondencia con las pautas

| Criterio de presentación | Evidencia |
|---|---|
| Calidad y contribución | 1, 6, 10–12 |
| Pertinencia para el curso | 4–8: AG, NSGA-II y Mamdani |
| Comprensión técnica | 2–9: contexto, métricas, método y protocolo |
| Análisis crítico | 10–14: no significancia, compromisos, fallos y futuro |
| Claridad y organización | Contexto → método → evaluación → conclusiones |
| Dominio y respuestas | Preguntas de defensa anteriores |
| Uso del tiempo | 14 minutos planificados + 1 de margen |

## Antes de entregar

1. Ensaya con cronómetro; recorta ejemplos antes que conclusiones o limitaciones.
2. Comprueba el acceso público al repositorio; no basta con escribir una URL.
3. Para PDF usa la versión adjunta o **PDF → Guardar como PDF**, todas las páginas, sin encabezados/pies del navegador y con gráficos de fondo. El diseño de impresión es 16:9 y no incluye guion ni controles.
4. Conserva `index.html`, `estilos.css`, `presentacion.js` y la carpeta de resultados en sus posiciones. No requiere internet, CDN ni ejecutar Python para presentar.
5. Los gráficos E1/E2/E3 incorporan las medias y DE redondeadas de las tablas actuales. Si vuelves a ejecutar los experimentos, actualiza los datos de `presentacion.js` y la tabla de ablación de `index.html`, y vuelve a exportar el PDF.

## Fuentes y trazabilidad

- Artículo base: Tran et al. (2025), [DOI](https://doi.org/10.1109/TETCI.2025.3543836).
- Contexto y métodos: referencias completas en [bibliografía del informe](../report_ieee/references.bib).
- E1 frente/tiempo: [E1_moo_media_std.csv](../results/tables/E1_moo_media_std.csv).
- E1 QoS: [E1_qos_media_std.csv](../results/tables/E1_qos_media_std.csv).
- Significancia principal y ablación: [E1_wilcoxon_vs_GAMR_ablacion.csv](../results/tables/E1_wilcoxon_vs_GAMR_ablacion.csv).
- E2: [E2_escalabilidad.csv](../results/tables/E2_escalabilidad.csv).
- E3: [E3_beta.csv](../results/tables/E3_beta.csv).
- Valores relativos y pruebas E2/E3: [resumen_resultados.md](../results/tables/resumen_resultados.md).
