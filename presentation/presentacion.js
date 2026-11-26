"use strict";

const slides = [...document.querySelectorAll(".slide")];
const select = document.querySelector("#slide-select");
const previous = document.querySelector("#prev");
const next = document.querySelector("#next");
const notesPanel = document.querySelector("#notes-panel");
const notesButton = document.querySelector("#notes");
const status = document.querySelector("#status");
let current = 0;
let statusTimeout;

function notify(message) {
  status.textContent = message;
  clearTimeout(statusTimeout);
  statusTimeout = setTimeout(() => { status.textContent = ""; }, 7000);
}

slides.forEach((slide, index) => {
  const option = document.createElement("option");
  option.value = String(index);
  option.textContent = `${String(index + 1).padStart(2, "0")} · ${slide.dataset.title}`;
  select.append(option);
});

function updateNotes() {
  const slide = slides[current];
  document.querySelector("#notes-title").textContent = `${current + 1}. ${slide.dataset.title} · ${slide.dataset.seconds} s`;
  document.querySelector("#notes-body").innerHTML = slide.querySelector(".speaker-notes").innerHTML;
}

function showSlide(index) {
  current = Math.max(0, Math.min(slides.length - 1, index));
  slides.forEach((slide, i) => {
    slide.classList.toggle("active", i === current);
    slide.setAttribute("aria-hidden", String(i !== current));
  });
  select.value = String(current);
  previous.disabled = current === 0;
  next.disabled = current === slides.length - 1;
  document.querySelector("#counter").textContent = `${String(current + 1).padStart(2, "0")} / ${slides.length}`;
  document.querySelector("#section-title").textContent = slides[current].dataset.title;
  document.querySelector("#progress").style.width = `${(current + 1) / slides.length * 100}%`;
  document.title = `${current + 1} · ${slides[current].dataset.title} | F-GAMR`;
  updateNotes();
}

function navigate(index) {
  const bounded = Math.max(0, Math.min(slides.length - 1, index));
  if (location.hash !== `#${bounded + 1}`) location.hash = String(bounded + 1);
  showSlide(bounded);
  window.scrollTo({ top: 0, behavior: "instant" });
}

function readHash() {
  const value = Number(location.hash.slice(1));
  showSlide(Number.isInteger(value) && value >= 1 && value <= slides.length ? value - 1 : 0);
}

function toggleNotes(force) {
  const open = force === undefined ? notesPanel.hidden : force;
  notesPanel.hidden = !open;
  notesButton.setAttribute("aria-expanded", String(open));
  if (open) document.querySelector("#close-notes").focus();
  else notesButton.focus();
}

previous.addEventListener("click", () => navigate(current - 1));
next.addEventListener("click", () => navigate(current + 1));
select.addEventListener("change", () => navigate(Number(select.value)));
window.addEventListener("hashchange", readHash);
notesButton.addEventListener("click", () => toggleNotes());
document.querySelector("#close-notes").addEventListener("click", () => toggleNotes(false));
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && !notesPanel.hidden) {
    toggleNotes(false);
    return;
  }
  if (event.ctrlKey || event.metaKey || event.altKey ||
      event.target.closest("input, select, textarea, button, a, [contenteditable=true]")) return;
  if (["ArrowRight", "PageDown", " "].includes(event.key)) {
    event.preventDefault();
    navigate(current + 1);
  } else if (["ArrowLeft", "PageUp"].includes(event.key)) {
    event.preventDefault();
    navigate(current - 1);
  } else if (event.key === "Home" || event.key === "End") {
    event.preventDefault();
    navigate(event.key === "Home" ? 0 : slides.length - 1);
  } else if (event.key.toLowerCase() === "g") {
    toggleNotes();
  }
});
document.querySelector("#fullscreen").addEventListener("click", async () => {
  try {
    if (document.fullscreenElement) await document.exitFullscreen();
    else if (document.documentElement.requestFullscreen) await document.documentElement.requestFullscreen();
    else notify("Este navegador no permite pantalla completa. Usa su opción de pantalla completa.");
  } catch (error) {
    console.error("No se pudo cambiar a pantalla completa:", error);
    notify("No se pudo activar pantalla completa. Usa F11 o la opción del navegador.");
  }
});
document.querySelector("#print").addEventListener("click", () => {
  notify("Guardar como PDF: todas las diapositivas, sin encabezados del navegador y con gráficos de fondo.");
  window.print();
});
const motionButton = document.querySelector("#motion");
motionButton.addEventListener("click", () => {
  const paused = document.body.classList.toggle("no-motion");
  motionButton.setAttribute("aria-pressed", String(paused));
  motionButton.textContent = paused ? "Sin animación" : "Animación";
});

let elapsed = 0;
let timerStarted = null;
function timerSeconds() {
  return Math.floor((elapsed + (timerStarted === null ? 0 : performance.now() - timerStarted)) / 1000);
}
function renderTimer() {
  const seconds = timerSeconds();
  document.querySelector("#timer").textContent = `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;
  document.querySelector("#timer-toggle").style.borderColor = seconds >= 900 ? "var(--navy)" : "";
}
document.querySelector("#timer-toggle").addEventListener("click", () => {
  if (timerStarted === null) timerStarted = performance.now();
  else {
    elapsed += performance.now() - timerStarted;
    timerStarted = null;
  }
  document.querySelector("#timer-toggle").setAttribute("aria-pressed", String(timerStarted !== null));
  renderTimer();
});
document.querySelector("#timer-reset").addEventListener("click", () => {
  elapsed = 0;
  timerStarted = null;
  document.querySelector("#timer-toggle").setAttribute("aria-pressed", "false");
  renderTimer();
});
setInterval(renderTimer, 500);

const paretoTexts = {
  pareto: "<strong>Pareto = alternativas no dominadas.</strong><p>Nadie mejora todos sus objetivos a la vez. Después hay que elegir una configuración.</p>",
  hv: "<strong>HV: mayor volumen cubierto = mejor.</strong><p>La unión sombreada se cuenta una sola vez. La referencia debe ser común para comparar frentes.</p>",
  igd: "<strong>IGD: menor distancia = mejor.</strong><p>Para cada punto de referencia, tomar la distancia a la solución encontrada más cercana y promediar.</p>"
};
document.querySelectorAll("[data-pareto]").forEach((button) => {
  button.addEventListener("click", () => {
    const mode = button.dataset.pareto;
    document.querySelector("#hv-area").toggleAttribute("hidden", mode !== "hv");
    document.querySelector("#igd-lines").toggleAttribute("hidden", mode !== "igd");
    document.querySelector("#pareto-explanation").innerHTML = paretoTexts[mode];
    document.querySelectorAll("[data-pareto]").forEach((item) => item.setAttribute("aria-pressed", String(item === button)));
  });
});

function updateLoad() {
  const load = Number(document.querySelector("#load").value);
  document.querySelector("#load-value").textContent = `${load} Mbps`;
  document.querySelector("#utilization").textContent = `Utilización ρ = ${load}%`;
  document.querySelector("#load-fill").style.width = `${Math.min(load, 100)}%`;
  document.querySelector(".load-demo").classList.toggle("overloaded", load >= 100);
  document.querySelector("#load-message").textContent = load > 100
    ? `Demanda supera capacidad en ${load - 100} Mbps: el modelo incorpora pérdida por desborde.`
    : load === 100
      ? "Saturación: sin margen libre. El modelo acota el retardo de cola."
      : "Menos margen libre; la cola crece al acercarse al 100%.";
}
document.querySelector("#load").addEventListener("input", updateLoad);
function updateRoulette() {
  const kappa = Number(document.querySelector("#kappa").value);
  const desirabilities = [0.8, 0.5, 0.2];
  const weights = desirabilities.map((w) => w ** kappa + 0.01);
  const sum = weights.reduce((a, b) => a + b, 0);
  document.querySelector("#kappa-value").textContent = String(kappa);
  document.querySelector("#roulette-bars").innerHTML = weights.map((weight, i) => {
    const probability = weight / sum * 100;
    return `<div class="roulette-row"><span>w=${desirabilities[i]}</span><div class="roulette-track"><div class="roulette-bar" style="width:${probability}%"></div></div><strong>${probability.toFixed(1)}%</strong></div>`;
  }).join("");
}
document.querySelector("#kappa").addEventListener("input", updateRoulette);
document.querySelector("#show-spread").addEventListener("change", (event) => {
  document.querySelectorAll(".band").forEach((band) => { band.style.display = event.target.checked ? "block" : "none"; });
});

const SVG_NS = "http://www.w3.org/2000/svg";
function svgElement(parent, tag, attributes, text) {
  const element = document.createElementNS(SVG_NS, tag);
  Object.entries(attributes).forEach(([name, value]) => element.setAttribute(name, String(value)));
  if (text !== undefined) element.textContent = text;
  parent.append(element);
  return element;
}
const colors = { GAMR: "#52677f", "F-GAMR": "#1256bd", MH: "#8599ac", "QoS-Dijkstra": "#438eac", "LCP-WAC*": "#438eac" };

// Valores redondeados publicados en results/tables; no son datos simulados de las demostraciones.
const scenarios = [
  { label: "Oxford · 5%", hv: [[0.687, 0.061], [0.697, 0.073]], time: [[6.14, 1.58], [5.12, 1.31]], loss: [[12.85, 3.45], [12.38, 3.56]] },
  { label: "Oxford · 55%", hv: [[0.694, 0.066], [0.698, 0.065]], time: [[6.05, 1.40], [4.94, 1.26]], loss: [[13.34, 3.79], [12.97, 3.90]] },
  { label: "Chinanet · 5%", hv: [[0.679, 0.060], [0.734, 0.055]], time: [[7.44, 1.69], [6.87, 1.67]], loss: [[10.77, 3.92], [10.11, 4.01]] },
  { label: "Chinanet · 55%", hv: [[0.678, 0.048], [0.724, 0.046]], time: [[7.68, 1.70], [7.13, 1.83]], loss: [[11.26, 3.99], [10.66, 4.09]] }
];

function comparisonChart(id, metric, min, max, ticks, decimals) {
  const svg = document.querySelector(id);
  const left = 140, right = 545;
  const scale = (value) => left + (value - min) / (max - min) * (right - left);
  ["GAMR", "F-GAMR"].forEach((name, i) => {
    svgElement(svg, "circle", { cx: 170 + i * 155, cy: 17, r: 5, fill: colors[name] });
    svgElement(svg, "text", { x: 181 + i * 155, y: 22, class: "legend-label" }, name);
  });
  ticks.forEach((value) => {
    const x = scale(value);
    svgElement(svg, "line", { x1: x, x2: x, y1: 40, y2: 298, class: "chart-grid" });
    svgElement(svg, "text", { x, y: 324, "text-anchor": "middle", class: "chart-label" }, String(value));
  });
  scenarios.forEach((scenario, row) => {
    const y = 66 + row * 64;
    svgElement(svg, "text", { x: 128, y: y + 14, "text-anchor": "end", class: "chart-label" }, scenario.label);
    scenario[metric].forEach(([mean, std], i) => {
      const cy = y + i * 23;
      const color = colors[i === 0 ? "GAMR" : "F-GAMR"];
      const start = scale(mean - std), end = scale(mean + std);
      svgElement(svg, "line", { x1: start, x2: end, y1: cy, y2: cy, stroke: color, class: "errorbar" });
      [start, end].forEach((x) => svgElement(svg, "line", { x1: x, x2: x, y1: cy - 5, y2: cy + 5, stroke: color, class: "errorbar" }));
      svgElement(svg, "circle", { cx: scale(mean), cy, r: 5, fill: color });
      svgElement(svg, "text", { x: scale(mean) + 8, y: cy - 7, fill: color, class: "chart-value" }, mean.toFixed(decimals));
    });
  });
}

const scaleSeries = [
  { name: "MH", values: [[12.45, 2.56], [12.72, 2.33], [14.80, 5.08], [24.46, 10.53]] },
  { name: "QoS-Dijkstra", values: [[15.06, 3.92], [15.15, 5.18], [18.17, 8.57], [29.74, 15.08]] },
  { name: "GAMR", values: [[13.20, 2.82], [12.81, 2.60], [13.17, 2.80], [14.62, 4.38]] },
  { name: "F-GAMR", values: [[12.03, 2.80], [12.15, 2.79], [12.78, 2.87], [14.47, 4.33]] }
];
const betaSeries = [
  { name: "LCP-WAC*", values: [[10.12, 4.44], [16.26, 10.66], [16.74, 10.27], [20.21, 9.97]] },
  { name: "GAMR", values: [[10.83, 4.17], [15.53, 11.31], [15.90, 11.02], [19.26, 10.92]] },
  { name: "F-GAMR", values: [[10.35, 4.28], [14.95, 11.46], [15.40, 11.09], [18.99, 10.95]] }
];

function lineChart(id, xs, series, maxY) {
  const svg = document.querySelector(id);
  const x = (value) => 53 + (value - xs[0]) / (xs.at(-1) - xs[0]) * 478;
  const y = (value) => 258 - value / maxY * 201;
  series.forEach(({ name }, i) => {
    svgElement(svg, "line", { x1: 22 + i * 139, x2: 40 + i * 139, y1: 18, y2: 18, stroke: colors[name], "stroke-width": 3, "stroke-dasharray": name === "GAMR" ? "5 3" : "" });
    svgElement(svg, "text", { x: 46 + i * 139, y: 23, class: "legend-label" }, name);
  });
  for (let tick = 0; tick <= maxY; tick += 10) {
    svgElement(svg, "line", { x1: 53, x2: 531, y1: y(tick), y2: y(tick), class: "chart-grid" });
    svgElement(svg, "text", { x: 43, y: y(tick) + 4, "text-anchor": "end", class: "chart-label" }, String(tick));
  }
  xs.forEach((value) => svgElement(svg, "text", { x: x(value), y: 281, "text-anchor": "middle", class: "chart-label" }, String(value)));
  series.forEach(({ name, values }) => {
    const upper = values.map(([mean, std], i) => `${x(xs[i])},${y(Math.min(maxY, mean + std))}`);
    const lower = values.map(([mean, std], i) => `${x(xs[i])},${y(Math.max(0, mean - std))}`).reverse();
    svgElement(svg, "polygon", { points: [...upper, ...lower].join(" "), fill: colors[name], class: "band", style: "display:none" });
    svgElement(svg, "polyline", {
      points: values.map(([mean], i) => `${x(xs[i])},${y(mean)}`).join(" "),
      fill: "none", stroke: colors[name], "stroke-width": name === "F-GAMR" ? 3.5 : 2,
      "stroke-dasharray": name === "GAMR" ? "6 4" : name === "MH" ? "2 3" : ""
    });
    values.forEach(([mean], i) => svgElement(svg, "circle", { cx: x(xs[i]), cy: y(mean), r: name === "F-GAMR" ? 4.5 : 3, fill: colors[name] }));
  });
  svgElement(svg, "text", { x: 53, y: 47, class: "chart-label" }, "Pérdida [%]");
  svgElement(svg, "text", { x: 292, y: 311, "text-anchor": "middle", class: "chart-label" }, id === "#beta-results" ? "Desorden de capacidad β [%]" : "Solicitudes simultáneas Nᵣ");
}

comparisonChart("#hv-results", "hv", 0.5, 0.85, [0.5, 0.6, 0.7, 0.8], 3);
comparisonChart("#time-results", "time", 0, 11, [0, 2, 4, 6, 8, 10], 2);
comparisonChart("#loss-results", "loss", 0, 20, [0, 5, 10, 15, 20], 2);
lineChart("#scale-results", [10, 20, 50, 100], scaleSeries, 50);
lineChart("#beta-results", [0, 5, 20, 55], betaSeries, 35);
updateLoad();
updateRoulette();
readHash();

window.addEventListener("beforeprint", () => {
  slides.forEach((slide) => slide.removeAttribute("aria-hidden"));
});
window.addEventListener("afterprint", () => showSlide(current));
