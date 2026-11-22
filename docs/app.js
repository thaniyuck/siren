// SIREN viewer: reads the patient record from the URL fragment and draws it.
// Everything happens on the phone; nothing is sent anywhere.
import { decodeFragment, DecodeError } from "./decode.js";

const SVG = "http://www.w3.org/2000/svg";
const $ = (id) => document.getElementById(id);

const ACVPU_TEXT = {
  A: "Sadar penuh (A)", C: "Bingung baru (C)", V: "Respons suara (V)",
  P: "Respons nyeri (P)", U: "Tidak respons (U)",
};
const ALERT_TEXT = {
  shock_index: "Shock index ≥ 1,0 (curiga syok atau perdarahan)",
  news2_rise: "NEWS2 naik ≥ 2 dalam 60 detik",
  spo2_low: "SpO₂ ≤ 91%",
  rr_high: "Laju napas ≥ 25/menit",
  rr_low: "Laju napas ≤ 8/menit",
  hr_high: "Nadi ≥ 131/menit",
  hr_low: "Nadi ≤ 40/menit",
  sbp_low: "TD sistolik manset ≤ 90 mmHg",
  temp_high: "Suhu ≥ 39,1 °C",
  temp_low: "Suhu ≤ 35,0 °C",
  new_confusion: "Penurunan kesadaran (bukan A)",
  bp_trend: "Model tren PPG meminta TD manset diukur ulang",
};
const ERROR_TEXT = {
  empty: "Halaman ini menampilkan ringkasan pasien SIREN. Pindai QR pada label pasien untuk membukanya.",
  format: "Data di QR tidak lengkap atau rusak. Pindai ulang dari jarak 15 sampai 25 cm dan pastikan seluruh QR masuk ke kamera.",
  checksum: "Data di QR tidak lengkap atau rusak. Pindai ulang dari jarak 15 sampai 25 cm dan pastikan seluruh QR masuk ke kamera.",
  version: "Label ini dibuat dengan format yang lebih baru. Tarik layar ke bawah untuk memuat ulang halaman.",
  browser: "Browser ini terlalu lama untuk membuka data. Buka tautan di Chrome atau Safari versi terbaru.",
};

// NEWS2 score-0 ranges (RCP 2017), drawn as the grey band
const CHARTS = [
  { key: "news2", name: "NEWS2", unit: "", domain: [0, 10], digits: 0, strip: true },
  { key: "hr", name: "Nadi", unit: "/menit", domain: [40, 150], band: [51, 90], digits: 0 },
  { key: "spo2", name: "SpO₂", unit: "%", domain: [85, 100], band: [96, 100], digits: 0 },
  { key: "rr", name: "Laju napas", unit: "/menit", domain: [6, 30], band: [12, 20], digits: 0 },
  { key: "temp", name: "Suhu", unit: "°C", domain: [35, 39], band: [36.1, 38.0], digits: 1 },
  { key: "bp", name: "TD manset", unit: "mmHg", domain: [50, 170], band: [111, 219], digits: 0, cuff: true },
];

const W = 360, H = 92, M = { l: 30, r: 10, t: 6, b: 16 }, STRIP = 12;

const timeFmt = new Intl.DateTimeFormat("id-ID", { hour: "2-digit", minute: "2-digit" });
const dateFmt = new Intl.DateTimeFormat("id-ID", { day: "numeric", month: "short", year: "numeric" });
const hm = (s) => timeFmt.format(new Date(s * 1000));
const num = (v, d = 0) => (v == null ? "–" : v.toLocaleString("id-ID", { minimumFractionDigits: d, maximumFractionDigits: d }));

function el(tag, attrs = {}, parent) {
  const node = document.createElementNS(SVG, tag);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
  if (parent) parent.appendChild(node);
  return node;
}

function setColourTag(node, colour) {
  node.className = `tag ${colour || ""}`;
  node.textContent = colour || "–";
}

// ------------------------------------------------------------------ summary --
function renderSummary(r) {
  $("code").textContent = r.code || "Tanpa kode";
  $("unit").textContent = r.unit ? `Unit ${r.unit}` : "";
  const block = $("colour-block");
  block.className = `colour-block ${r.colour || ""}`;
  $("colour-icon").textContent = { MERAH: "▲", KUNING: "■", HIJAU: "●" }[r.colour] || "";
  $("colour-text").textContent = r.colour || "BELUM ADA DATA";

  $("news2").textContent = r.news2 == null ? "–" : `${num(r.news2)} (${r.news2_measured}/7 parameter)`;
  setColourTag($("worst"), r.worst_colour);
  setColourTag($("start-colour"), r.start_colour);
  const sex = { L: "laki-laki", P: "perempuan" }[r.sex] || "kelamin –";
  $("who").textContent = `${r.age == null ? "usia –" : `${num(r.age)} th`}, ${sex}`;
  $("acvpu").textContent = ACVPU_TEXT[r.acvpu] || "–";
  $("oxygen").textContent = r.on_oxygen ? "Ya, dengan O₂" : "Tidak (udara ruang)";
  $("pain").textContent = r.pain == null ? "–" : `${num(r.pain)}/10`;
  const cuff = r.cuffs.at(-1);
  $("cuff").textContent = cuff ? `${num(cuff.sys)}/${num(cuff.dia)} (${hm(cuff.t)})` : "Belum diukur";
  $("complaint").textContent = r.complaint || "–";

  const when = new Date(r.printed_at * 1000);
  $("asof").textContent =
    `Data sampai pukul ${timeFmt.format(when)}, ${dateFmt.format(when)}`;

  const list = $("alert-list");
  list.replaceChildren();
  for (const a of r.alerts) {
    const li = document.createElement("li");
    li.textContent = ALERT_TEXT[a] || a;
    list.appendChild(li);
  }
  $("alerts").hidden = r.alerts.length === 0;

}

// ------------------------------------------------------------------- charts --
function ticks(t0, t1) {
  const span = (t1 - t0) / 60;
  const every = [5, 10, 15, 30, 60, 120].find((m) => span / m <= 5) || 240;
  const out = [];
  for (let t = Math.ceil(t0 / (every * 60)) * every * 60; t <= t1; t += every * 60) out.push(t);
  return out;
}

function niceDomain(spec, values) {
  let [lo, hi] = spec.domain;
  const vals = values.filter((v) => v != null);
  if (vals.length) {
    lo = Math.min(lo, Math.floor(Math.min(...vals)));
    hi = Math.max(hi, Math.ceil(Math.max(...vals)));
  }
  if (spec.key === "spo2") hi = 100;
  return [lo, hi];
}

function buildChart(spec, r, x, t0, t1) {
  const wrap = document.createElement("div");
  wrap.className = "chart";
  const title = document.createElement("div");
  title.className = "chart-title";
  const name = document.createElement("span");
  name.className = "name";
  name.textContent = spec.unit ? `${spec.name} (${spec.unit})` : spec.name;
  const value = document.createElement("span");
  value.className = "value";
  title.append(name, value);
  wrap.appendChild(title);

  const height = H + (spec.strip ? STRIP + 10 : 0);
  const svg = el("svg", { viewBox: `0 0 ${W} ${height}`, role: "img", "aria-label": `Grafik ${spec.name}` });
  wrap.appendChild(svg);

  const values = spec.cuff ? r.cuffs.flatMap((c) => [c.sys, c.dia]) : r.points.map((p) => p[spec.key]);
  const [lo, hi] = niceDomain(spec, values);
  const plotBottom = H - M.b;
  const y = (v) => M.t + (hi - v) / (hi - lo) * (plotBottom - M.t);

  if (spec.band) {
    const top = y(Math.min(hi, spec.band[1])), bottom = y(Math.max(lo, spec.band[0]));
    if (bottom > top) el("rect", { class: "band", x: M.l, y: top, width: W - M.l - M.r, height: bottom - top }, svg);
  }
  const gridVals = [lo, (lo + hi) / 2, hi];
  for (const g of gridVals) {
    el("line", { class: g === lo ? "axis" : "grid", x1: M.l, x2: W - M.r, y1: y(g), y2: y(g) }, svg);
    const label = el("text", { x: M.l - 4, y: y(g) + 3, "text-anchor": "end" }, svg);
    label.textContent = num(g, spec.digits && g % 1 ? 1 : 0);
  }
  const axisY = spec.strip ? H + STRIP + 8 : H - 3;
  for (const t of ticks(t0, t1)) {
    const label = el("text", { x: x(t), y: axisY, "text-anchor": "middle" }, svg);
    label.textContent = hm(t);
  }

  const mid = r.step_s / 2;
  if (spec.cuff) {
    for (const c of r.cuffs) {
      if (c.sys == null) continue;
      const cx = x(c.t);
      el("line", { class: "cuff", x1: cx, x2: cx, y1: y(c.sys), y2: y(c.dia ?? c.sys) }, svg);
      el("circle", { class: "dot", cx, cy: y(c.sys), r: 4 }, svg);
      if (c.dia != null) el("circle", { class: "dot", cx, cy: y(c.dia), r: 4 }, svg);
      const label = el("text", { class: "cuff-label", x: cx, y: Math.max(9, y(c.sys) - 7), "text-anchor": "middle" }, svg);
      label.textContent = `${c.sys}/${c.dia ?? "–"}`;
    }
  } else {
    let d = "", pen = false;
    const lone = [];
    r.points.forEach((p, i) => {
      const v = p[spec.key];
      if (v == null) { pen = false; return; }
      const px = x(p.t + mid), py = y(v);
      const prevMissing = i === 0 || r.points[i - 1][spec.key] == null;
      const nextMissing = i === r.points.length - 1 || r.points[i + 1][spec.key] == null;
      if (prevMissing && nextMissing) lone.push([px, py]);
      d += `${pen ? "L" : "M"}${px.toFixed(1)},${py.toFixed(1)}`;
      pen = true;
    });
    if (d) el("path", { class: "line", d }, svg);
    for (const [cx, cy] of lone) el("circle", { class: "dot", cx, cy, r: 3 }, svg);
    const last = [...r.points].reverse().find((p) => p[spec.key] != null);
    if (last) el("circle", { class: "dot", cx: x(last.t + mid), cy: y(last[spec.key]), r: 4 }, svg);
  }

  if (spec.strip) {
    const wid = Math.max(1, x(t0 + r.step_s) - x(t0) - 1);
    for (const p of r.points) {
      el("rect", { class: `strip-${p.colour || "none"}`, x: x(p.t), y: H - 6, width: wid, height: STRIP, rx: 2 }, svg);
    }
  }

  const cursor = el("line", { class: "cursor", y1: M.t, y2: spec.strip ? H + STRIP - 4 : plotBottom, visibility: "hidden" }, svg);
  const hit = el("rect", { x: M.l, y: 0, width: W - M.l - M.r, height, fill: "transparent" }, svg);

  function show(i, t) {
    if (i == null) {
      cursor.setAttribute("visibility", "hidden");
      value.textContent = latestText();
      return;
    }
    cursor.setAttribute("x1", x(t));
    cursor.setAttribute("x2", x(t));
    cursor.setAttribute("visibility", "visible");
    value.textContent = valueText(i, t);
  }
  function valueText(i, t) {
    if (spec.cuff) {
      const c = r.cuffs.filter((c) => c.t <= t).at(-1);
      return c ? `${c.sys}/${c.dia ?? "–"} (${hm(c.t)})` : "belum diukur";
    }
    const p = r.points[i];
    const v = num(p[spec.key], spec.digits);
    return spec.strip ? `${v} (${p.colour || "–"})` : v;
  }
  function latestText() {
    if (spec.cuff) {
      const c = r.cuffs.at(-1);
      return c ? `terakhir ${c.sys}/${c.dia ?? "–"}` : "belum diukur";
    }
    const last = [...r.points].reverse().find((p) => p[spec.key] != null);
    if (!last) return "tidak terukur";
    const v = num(last[spec.key], spec.digits);
    return `terakhir ${spec.strip ? `${v} (${last.colour || "–"})` : v}`;
  }
  show(null);
  return { wrap, svg, hit, show };
}

function renderCharts(r) {
  const box = $("charts");
  box.replaceChildren();
  if (!r.points.length && !r.cuffs.length) {
    box.textContent = "Belum ada data tren.";
    return;
  }
  const times = [...r.points.map((p) => p.t), ...r.cuffs.map((c) => c.t)];
  const t0 = Math.min(...times);
  const t1 = Math.max(r.printed_at, ...r.points.map((p) => p.t + r.step_s), ...r.cuffs.map((c) => c.t + 60));
  const x = (t) => M.l + (t - t0) / (t1 - t0 || 1) * (W - M.l - M.r);
  const tOf = (svgX) => t0 + (svgX - M.l) / (W - M.l - M.r) * (t1 - t0);

  const charts = CHARTS.map((spec) => buildChart(spec, r, x, t0, t1));
  charts.forEach((c) => box.appendChild(c.wrap));

  const cursorTime = $("cursor-time");
  function move(evt, svg) {
    const pt = svg.createSVGPoint();
    pt.x = evt.clientX; pt.y = evt.clientY;
    const local = pt.matrixTransform(svg.getScreenCTM().inverse());
    const t = Math.max(t0, Math.min(t1, tOf(local.x)));
    let i = Math.floor((t - r.points[0]?.t) / r.step_s);
    i = Math.max(0, Math.min(r.points.length - 1, Number.isFinite(i) ? i : 0));
    charts.forEach((c) => c.show(r.points.length ? i : null, t));
    cursorTime.textContent = `pukul ${hm(t)}`;
  }
  function leave() {
    charts.forEach((c) => c.show(null));
    cursorTime.textContent = "";
  }
  for (const c of charts) {
    c.hit.addEventListener("pointermove", (e) => move(e, c.svg));
    c.hit.addEventListener("pointerdown", (e) => move(e, c.svg));
    c.hit.addEventListener("pointerleave", leave);
    c.hit.addEventListener("pointercancel", leave);
  }
}

// -------------------------------------------------------------------- table --
function renderTable(r) {
  const table = $("table");
  table.replaceChildren();
  const row = (cells, header = false) => {
    const tr = document.createElement("tr");
    for (const text of cells) {
      const cell = document.createElement(header ? "th" : "td");
      cell.textContent = text;
      tr.appendChild(cell);
    }
    table.appendChild(tr);
  };
  row(["Waktu", "NEWS2", "Kategori", "Nadi", "SpO₂", "RR", "Suhu"], true);
  for (const p of r.points) {
    row([hm(p.t), num(p.news2), p.colour || "–", num(p.hr), num(p.spo2), num(p.rr), num(p.temp, 1)]);
  }
  if (r.cuffs.length) {
    row(["Waktu", "TD manset", "", "", "", "", ""], true);
    for (const c of r.cuffs) row([hm(c.t), `${num(c.sys)}/${num(c.dia)}`, "", "", "", "", ""]);
  }
}

// --------------------------------------------------------------------- main --
async function show() {
  const state = $("state");
  try {
    const record = await decodeFragment(location.hash);
    renderSummary(record);
    renderCharts(record);
    renderTable(record);
    state.hidden = true;
    $("patient").hidden = false;
  } catch (err) {
    console.error(err);
    const code = err instanceof DecodeError ? err.code : "format";
    $("patient").hidden = true;
    state.hidden = false;
    state.classList.toggle("error", code !== "empty");
    state.firstElementChild.textContent = ERROR_TEXT[code] || ERROR_TEXT.format;
  }
}

window.addEventListener("hashchange", show);
show();

if ("serviceWorker" in navigator && (location.protocol === "https:" || location.hostname === "localhost")) {
  navigator.serviceWorker.register("sw.js").catch((e) => console.warn("offline cache unavailable", e));
}
