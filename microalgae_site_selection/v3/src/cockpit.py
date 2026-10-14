"""Self-contained decision cockpit (HTML + inline Plotly + the JS port of the engine)."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from plotly.offline import get_plotlyjs

HERE = Path(__file__).resolve().parent

TEMPLATE = r"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>DHA Decision Cockpit</title>
<style>
:root{--bg1:#000E38;--bg2:#060216;--bg3:#2E0133;--ink:#FFFFFF;--ink2:#D5D2DA;--muted:#B6B3BA;--grid:#3A3550;
--blue:#3987e5;--mag:#d55181;--vio:#9085e9;--panel:rgba(255,255,255,.05);--border:#E7E3EA33}
*{box-sizing:border-box}body{margin:0;font-family:Montserrat,Segoe UI,Arial,sans-serif;color:var(--ink);
background:linear-gradient(160deg,var(--bg1),var(--bg2) 55%,var(--bg3));min-height:100vh}
header{padding:20px 24px 4px}h1{margin:0;font-size:24px}h2{font-size:15px;margin:0 0 8px;color:var(--ink2);font-weight:600}
.sub{color:var(--ink2);font-size:13px;margin-top:4px}.warn{color:#fff;background:#8C2F7855;border:1px solid var(--mag);
border-radius:6px;padding:6px 10px;font-size:12px;margin:6px 0;display:none}
.grid{display:grid;grid-template-columns:340px 1fr;gap:16px;padding:12px 24px 24px}
.panel{background:var(--panel);border:1px solid var(--border);border-radius:10px;padding:14px}
label{display:block;font-size:12.5px;color:var(--ink2);margin:10px 0 3px}
input[type=range]{width:100%}.val{float:right;color:var(--ink);font-weight:600}
select{width:100%;background:#0B0630;color:var(--ink);border:1px solid var(--border);border-radius:6px;padding:4px}
.chk{display:inline-block;margin:2px 8px 2px 0;font-size:12.5px;color:var(--ink)}
table{width:100%;border-collapse:collapse;font-size:12.5px}th,td{padding:6px 6px;border-bottom:1px solid var(--grid);text-align:right}
th:first-child,td:first-child{text-align:left}th{color:var(--ink2);font-weight:600}
tr.best td{background:#3987e522;font-weight:700}.pill{font-size:11px;padding:2px 6px;border-radius:10px;border:1px solid var(--border)}
.kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:12px}
.kpi{background:var(--panel);border:1px solid var(--border);border-radius:8px;padding:10px}.kpi b{display:block;font-size:20px}
.kpi span{font-size:11.5px;color:var(--ink2)}.charts{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:12px}
.foot{font-size:11px;color:var(--muted);padding:0 24px 24px}
@media(max-width:900px){.grid{grid-template-columns:1fr}.charts{grid-template-columns:1fr}.kpis{grid-template-columns:1fr 1fr}}
</style></head><body>
<header><h1>Painel de decisão — nova capacidade de DHA de microalgas</h1>
<div class="sub">Recalcula VPL, TIR, utilização, preço mínimo e a melhor sequência a cada ajuste. Os controles exploram premissas;
<b>não são previsões da Corbion</b>. Demanda padrão = PREMISSAS (nenhum contrato público para a nova capacidade).</div>
<div class="warn" id="warn"></div></header>
<div class="grid">
<div class="panel">
<h2>Controles principais</h2>
<label>(i) Volume contratado firme para a nova capacidade (t SKU/ano, a partir de __CSY__)<span class="val" id="v_ct"></span></label>
<input type="range" id="ct" min="0" max="25000" step="500">
<label>Parcela asiática do volume contratado<span class="val" id="v_as"></span></label>
<input type="range" id="as" min="0" max="1" step="0.05">
<label>(ii) Preço líquido realizado (US$/kg DHA)<span class="val" id="v_pr"></span></label>
<input type="range" id="pr" min="8" max="60" step="0.5">
<label>(iii) Capex incremental de Orindiúva, módulo 1 (US$ mi, base 2026)<span class="val" id="v_cx"></span></label>
<input type="range" id="cx" min="20" max="250" step="1">
<h2 style="margin-top:16px">Demanda não contratada</h2>
<label>Cenário de ponderação do pipeline</label>
<select id="sc"><option value="stress">stress</option><option value="base" selected>base</option><option value="upside">upside</option></select>
<label><input type="checkbox" id="pipe" checked> incluir pipeline e potencial ponderados (senão: só contratos)</label>
<h2 style="margin-top:16px">Filtros de mercado (afetam o cálculo)</h2>
<div id="apps"></div><label>Países</label><div id="ctrs"></div>
<label>Ano de leitura dos KPIs</label><select id="yr"></select>
<div class="sub" style="margin-top:12px">Faixas justificadas: preço __PLO__–__PHI__ US$/kg DHA (A040); capex __CLO__–__CHI__ US$ mi
(±60% do módulo estimado); contrato até o potencial total do arquivo de demanda. Fora disso aparece alerta de extrapolação.</div>
</div>
<div>
<div class="kpis" id="kpis"></div>
<div class="panel"><h2>Alternativas (VPL nominal em USD; TIR do fluxo com valor terminal)</h2><table id="tbl"></table>
<div class="sub" id="seq"></div></div>
<div class="charts">
<div class="panel"><h2>Fronteira de decisão (ΔVPL, US$ mi; linha branca = 0)</h2>
<select id="fm"><option value="G_ORI_TH_NOW">2ª unidade: G (Orindiúva + Tailândia já) − A1 (só Orindiúva)</option>
<option value="C_TH_NSN">Qual site recebe a única unidade: C (Nakhon Sawan) − A1 (Orindiúva)</option></select>
<div class="sub">Na comparação G − A1 o capex de Orindiúva se cancela (está nas duas); ele move a comparação C − A1.</div>
<div id="fr" style="height:340px"></div></div>
<div class="panel"><h2>Demanda ativa por status (t SKU/ano)</h2><div id="dm" style="height:360px"></div></div>
</div></div></div>
<div class="foot" id="foot"></div>
<script>__PLOTLY__</script>
<script>__ENGINE__</script>
<script>
const DATA = __DATA__;
const E = DHAEngine;
const $ = id => document.getElementById(id);
const fmt = (v, d=0) => v === null || v === undefined || isNaN(v) ? "—" : v.toLocaleString("pt-BR", {minimumFractionDigits:d, maximumFractionDigits:d});
const pct = v => v === null || v === undefined ? "—" : (100*v).toFixed(1) + "%";
const apps = [...new Set(DATA.demand.map(r => r.application))], ctrs = [...new Set(DATA.demand.map(r => r.country))];
$("apps").innerHTML = apps.map(a => `<span class="chk"><input type="checkbox" class="fa" value="${a}" checked> ${DATA.app_label[a]||a}</span>`).join("");
$("ctrs").innerHTML = ctrs.map(a => `<span class="chk"><input type="checkbox" class="fc" value="${a}" checked> ${a}</span>`).join("");
DATA.years.forEach(y => { const o = document.createElement("option"); o.value = y; o.text = y; if (y === 2032) o.selected = true; $("yr").appendChild(o); });
$("ct").value = 0; $("as").value = 0.5; $("pr").value = DATA.p.price_dha; const CX0 = Math.round(DATA.capex_ori_base/1e6); $("cx").value = CX0;
function state() {
  return { ct: +$("ct").value, as: +$("as").value, pr: +$("pr").value, cx: +$("cx").value, sc: $("sc").value, pipe: $("pipe").checked,
    fa: [...document.querySelectorAll(".fa:checked")].map(e => e.value), fc: [...document.querySelectorAll(".fc:checked")].map(e => e.value), yr: +$("yr").value };
}
function params(s, overrides) {
  const p = JSON.parse(JSON.stringify(DATA.p));
  const w = s.pipe ? DATA.p.scenario_weights[s.sc] : {contracted: 1, qualified_pipeline: 0, unqualified_potential: 0};
  const rows = DATA.demand.filter(r => s.fa.indexOf(r.application) >= 0 && s.fc.indexOf(r.country) >= 0);
  let d = E.weightedDemand(rows, w, p.regions, DATA.years, null);
  const o = Object.assign({ct: s.ct, as: s.as}, overrides || {});
  if (o.ct > 0) d = E.addContracted(d, o.ct, o.as, DATA.mix, p.asia_regions, DATA.contract_start);
  p.demand = d; p.price_dha = o.pr !== undefined ? o.pr : s.pr;
  p.capex_override = s.cx === CX0 ? {} : {BR_ORI_EXP: s.cx * 1e6};
  return p;
}
function warn(s) {
  const w = [];
  if (s.pr < DATA.bounds.price[0] || s.pr > DATA.bounds.price[1]) w.push(`Preço ${s.pr} fora da faixa justificada ${DATA.bounds.price.join("–")} US$/kg DHA: EXTRAPOLAÇÃO.`);
  if (s.cx < DATA.bounds.capex[0] || s.cx > DATA.bounds.capex[1]) w.push(`Capex ${s.cx} fora da faixa ${DATA.bounds.capex.map(v=>v.toFixed(0)).join("–")} US$ mi: EXTRAPOLAÇÃO.`);
  if (s.ct > DATA.bounds.contract_max) w.push(`Contrato de ${fmt(s.ct)} t acima do potencial total do arquivo de demanda em ${DATA.contract_start} (${fmt(DATA.bounds.contract_max)} t): EXTRAPOLAÇÃO.`);
  if (!s.pipe && s.ct === 0) w.push("Sem contratos e sem pipeline: nenhuma alternativa tem demanda; esperar (VPL 0) é a única leitura possível.");
  $("warn").style.display = w.length ? "block" : "none"; $("warn").innerHTML = w.join("<br>");
}
let frTimer = null;
function render() {
  const s = state();
  $("v_ct").textContent = fmt(s.ct) + " t"; $("v_as").textContent = Math.round(100*s.as) + "%";
  $("v_pr").textContent = "US$ " + s.pr.toFixed(1); $("v_cx").textContent = "US$ " + (s.cx === CX0 ? (DATA.capex_ori_base/1e6).toFixed(1) + " mi (modelo)" : s.cx + " mi");
  warn(s);
  const p = params(s);
  const res = {}; DATA.order.forEach(k => res[k] = E.runAlternative(p, DATA.alts[k]));
  const iy = DATA.years.indexOf(s.yr);
  const ranked = DATA.seq.slice().sort((a, b) => res[b].npv - res[a].npv);
  const best = res[ranked[0]].npv > 0 ? ranked[0] : null;
  const msps = {}; ["A1_ORI", "C_TH_NSN", "G_ORI_TH_NOW"].forEach(k => msps[k] = E.msp(p, DATA.alts[k]));
  let html = "<tr><th>Alternativa</th><th>VPL</th><th>VPL s/ VT</th><th>TIR</th><th>Utiliz. " + s.yr + "</th><th>Não absorvida " + s.yr + " (t)</th><th>Preço mínimo (MSP; A1, C, G)</th><th>Payback desc. (≤2035)</th><th>Unidades</th></tr>";
  DATA.order.forEach(k => {
    const r = res[k];
    html += `<tr class="${k===best?'best':''}"><td>${DATA.alts[k].label}</td><td>${fmt(r.npv/1e6,1)}</td><td>${fmt(r.npv_ex_tv/1e6,1)}</td><td>${pct(r.irr)}</td>
      <td>${pct(r.utilisation[iy])}</td><td>${fmt(r.capacity_t[iy]-r.sold_t[iy])}</td><td>${msps[k] ? "US$ " + msps[k].toFixed(1) : "—"}</td>
      <td>${r.disc_payback || "—"}</td><td><span class="pill">${r.units.map(u => u.id.replace("BR_ORI_EXP","ORI").replace("TH_NSN","NSN") + "@" + u.online).join(", ") || "nenhuma"}</span></td></tr>`;
  });
  $("tbl").innerHTML = html;
  const g = res.G_ORI_TH_NOW.npv - res.A1_ORI.npv, f = res.F_ORI_THEN_TH.npv - res.A1_ORI.npv;
  $("seq").innerHTML = `Melhor sequência entre ${DATA.seq.map(k=>k.split("_")[0]).join(", ")}: <b>${best ? DATA.alts[best].label : "nenhuma com VPL > 0 → esperar/qualificar demanda"}</b>.
    ΔVPL da 2ª unidade já (G−A1): <b>US$ ${fmt(g/1e6,1)} mi</b>; condicionada a gatilho (F−A1): US$ ${fmt(f/1e6,1)} mi.
    A diversificação entra apenas via fluxo (sem prêmio narrativo); ver resilience_stress.csv para o cenário de parada.`;
  const a1 = res.A1_ORI;
  $("kpis").innerHTML = [
    ["VPL A1 Orindiúva", "US$ " + fmt(a1.npv/1e6,1) + " mi"], ["Utilização A1 em " + s.yr, pct(a1.utilisation[iy])],
    ["MSP A1 (VPL=0)", msps.A1_ORI ? "US$ " + msps.A1_ORI.toFixed(1) + "/kg DHA" : "—"],
    ["ΔVPL G − A1", "US$ " + fmt(g/1e6,1) + " mi"]].map(([a,b]) => `<div class="kpi"><span>${a}</span><b>${b}</b></div>`).join("");
  demandChart(s);
  clearTimeout(frTimer); frTimer = setTimeout(() => frontier(s), 120);
  $("foot").innerHTML = `Cenário ativo: <b>${s.pipe ? s.sc : "só contratos"}</b> · demanda: ${DATA.demand_origin} (${DATA.demand_source}) · pesos do pipeline A110/A111 ·
    preço A040 (fonte S015, faixa de óleo de peixe conflitante) · capex por módulo A020–A031 · açúcar S017/S018 · impostos S022/S024 (parecer pendente) ·
    gerado em ${DATA.generated} com o motor v${DATA.version}. Dados e premissas: assumptions.csv, evidence_registry.csv.`;
}
function frontier(s) {
  const z = [], vols = DATA.frontier.vols, prices = DATA.frontier.prices;
  vols.forEach(v => { const row = []; prices.forEach(pr => {
    const p = params(s, {ct: v, as: 1.0, pr: pr});
    row.push((E.runAlternative(p, DATA.alts[$("fm").value]).npv - E.runAlternative(p, DATA.alts.A1_ORI).npv) / 1e6); });
    z.push(row); });
  const m = Math.max(...z.flat().map(Math.abs));
  Plotly.react("fr", [{type: "heatmap", x: prices, y: vols, z: z, zmin: -m, zmax: m, colorscale: [[0, "#3987e5"], [0.5, "#3a3550"], [1, "#d55181"]],
      colorbar: {title: {text: "US$ mi", font: {color: "#D5D2DA"}}, tickfont: {color: "#D5D2DA"}}, hovertemplate: "preço %{x} US$/kg DHA<br>Ásia contratada %{y} t<br>ΔVPL %{z:.1f} US$ mi<extra></extra>"},
    {type: "contour", x: prices, y: vols, z: z, contours: {start: 0, end: 0, size: 1, coloring: "none"}, line: {color: "#FFFFFF", width: 3}, showscale: false, hoverinfo: "skip"},
    {type: "scatter", x: [s.pr], y: [s.ct * s.as], mode: "markers", marker: {size: 12, color: "#FFFFFF", symbol: "x"}, name: "posição atual", hoverinfo: "skip"}],
    {paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)", font: {color: "#D5D2DA", size: 11}, margin: {l: 60, r: 10, t: 10, b: 45}, showlegend: false,
     xaxis: {title: "preço líquido (US$/kg DHA)", gridcolor: "#3A3550"}, yaxis: {title: "volume asiático contratado (t/ano)", gridcolor: "#3A3550"}}, {displayModeBar: false, responsive: true});
}
function demandChart(s) {
  const rows = DATA.demand.filter(r => s.fa.indexOf(r.application) >= 0 && s.fc.indexOf(r.country) >= 0);
  const ys = DATA.years.filter(y => y >= 2028), traces = [];
  const col = {contracted: "#3987e5", qualified_pipeline: "#9085e9", unqualified_potential: "#B6B3BA"};
  const nm = {contracted: "contratado (arquivo)", qualified_pipeline: "pipeline qualificado (não firme)", unqualified_potential: "potencial não qualificado"};
  ["contracted", "qualified_pipeline", "unqualified_potential"].forEach(st => {
    traces.push({type: "bar", name: nm[st], x: ys, marker: {color: col[st], line: {color: "#0B0630", width: 2}},
      y: ys.map(y => rows.filter(r => r.year === y && r.opportunity_status === st).reduce((a, r) => a + (st === "contracted" ? r.contracted_volume_t : r.eligible_final_product_t * r.inclusion_rate * r.expected_supplier_share), 0)),
      hovertemplate: "%{x}: %{y:,.0f} t<extra>" + nm[st] + "</extra>"});
  });
  traces.push({type: "scatter", mode: "lines+markers", name: "contratado (controle)", x: ys, y: ys.map(y => y >= DATA.contract_start ? s.ct : 0), line: {color: "#d55181", width: 2}, marker: {size: 8}});
  Plotly.react("dm", traces, {barmode: "stack", paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)", font: {color: "#D5D2DA", size: 11},
    margin: {l: 55, r: 10, t: 10, b: 40}, legend: {orientation: "h", y: -0.18}, yaxis: {gridcolor: "#3A3550", title: "t SKU/ano (sem ponderação)"}}, {displayModeBar: false, responsive: true});
}
document.querySelectorAll("input,select").forEach(e => e.addEventListener("input", render));
render();
</script></body></html>"""


def build_cockpit(path: Path, p: dict, cfg: dict, demand: pd.DataFrame, demand_origin: str, generated: str,
                  capex_ori_base: float, price_bounds: tuple[float, float]) -> None:
    from . import data as D
    years = list(range(cfg["base_year"], cfg["end_year"] + 1))
    potential = D.sku_volume(demand[demand.year == cfg["contract_start_year"]]).sum()
    payload = {
        "p": p, "alts": cfg["alternatives"], "order": list(cfg["alternatives"]),
        "seq": ["A1_ORI", "A2_ORI_STAGED", "C_TH_NSN", "E_ORI_HUB", "F_ORI_THEN_TH", "G_ORI_TH_NOW"],
        "demand": demand.to_dict(orient="records"), "years": years, "mix": D.region_mix(demand, p["regions"]),
        "contract_start": cfg["contract_start_year"], "capex_ori_base": capex_ori_base,
        "bounds": {"price": list(price_bounds), "capex": [capex_ori_base / 1e6 * 0.4, capex_ori_base / 1e6 * 1.6],
                   "contract_max": float(potential)},
        "frontier": {"vols": cfg["frontier"]["asia_contract_t"], "prices": cfg["frontier"]["price_usd_kg_dha"]},
        "app_label": {"salmon": "Salmão", "shrimp": "Camarão", "pet_food": "Pet food", "shrimp/fish": "China (aquafeed)"},
        "demand_origin": "PREMISSAS padrão v3" if demand_origin == "default_premises" else "arquivo do estudo de mercado",
        "demand_source": ", ".join(sorted(demand["source_id"].astype(str).unique())),
        "generated": generated, "version": cfg["version"],
    }
    html = (TEMPLATE.replace("__PLOTLY__", get_plotlyjs())
            .replace("__ENGINE__", (HERE / "cockpit_engine.js").read_text(encoding="utf-8"))
            .replace("__DATA__", json.dumps(payload, ensure_ascii=False))
            .replace("__CSY__", str(cfg["contract_start_year"]))
            .replace("__PLO__", f"{price_bounds[0]:.0f}").replace("__PHI__", f"{price_bounds[1]:.0f}")
            .replace("__CLO__", f"{capex_ori_base / 1e6 * 0.4:.0f}").replace("__CHI__", f"{capex_ori_base / 1e6 * 1.6:.0f}"))
    path.write_text(html, encoding="utf-8")
