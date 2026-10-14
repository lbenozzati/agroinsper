"""Offline HTML explorer: volume curves by status/niche/scenario, bridge, and market table."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from plotly.offline import get_plotlyjs

PAGE = r"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>DHA Market Explorer</title><style>
:root{--ink:#fff;--ink2:#D5D2DA;--grid:#3A3550;--border:#E7E3EA33}
body{margin:0;font-family:Montserrat,Segoe UI,Arial,sans-serif;color:var(--ink);background:linear-gradient(160deg,#000E38,#060216 55%,#2E0133);min-height:100vh}
header{padding:18px 24px 4px}h1{margin:0;font-size:22px}.sub{color:var(--ink2);font-size:13px;margin-top:4px}
.bar{display:flex;flex-wrap:wrap;gap:14px;padding:10px 24px}.bar label{font-size:12.5px;color:var(--ink2)}
select{background:#0B0630;color:#fff;border:1px solid var(--border);border-radius:6px;padding:4px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;padding:0 24px 16px}.panel{background:rgba(255,255,255,.05);border:1px solid var(--border);border-radius:10px;padding:10px}
table{width:100%;border-collapse:collapse;font-size:12px}th,td{padding:5px;border-bottom:1px solid var(--grid);text-align:right}th:first-child,td:first-child,th:nth-child(2),td:nth-child(2){text-align:left}
th{color:var(--ink2)}.foot{font-size:11px;color:#B6B3BA;padding:0 24px 20px}@media(max-width:900px){.grid{grid-template-columns:1fr}}
</style></head><body>
<header><h1>Explorador de mercados de DHA (AlgaPrime) — estudo independente da fábrica</h1>
<div class="sub">Volumes são PREMISSAS derivadas de denominadores públicos; nenhum contrato público. Contratado = 0 em todos os cenários.</div></header>
<div class="bar"><label>Cenário <select id="sc"><option>low</option><option selected>base</option><option>high</option></select></label>
<label>Nicho <select id="ap"><option value="all">todos</option><option value="salmon">salmão</option><option value="shrimp">camarão</option><option value="pet_food">pet food</option></select></label>
<label>País <select id="ct"><option value="all">todos</option></select></label></div>
<div class="grid"><div class="panel"><div id="c1" style="height:360px"></div></div><div class="panel"><div id="c2" style="height:360px"></div></div>
<div class="panel" style="grid-column:1/-1"><table id="tb"></table></div></div>
<div class="foot" id="ft"></div>
<script>__PLOTLY__</script><script>
const D = __DATA__;
const $ = id => document.getElementById(id);
[...new Set(D.curves.map(r => r.country))].sort().forEach(c => { const o = document.createElement("option"); o.text = c; $("ct").appendChild(o); });
const L = {paper_bgcolor:"rgba(0,0,0,0)", plot_bgcolor:"rgba(0,0,0,0)", font:{color:"#D5D2DA", size:11}, margin:{l:55,r:10,t:30,b:40}, legend:{orientation:"h", y:-0.2}};
function render(){
  const sc=$("sc").value, ap=$("ap").value, ct=$("ct").value;
  const rows=D.curves.filter(r=>r.scenario===sc&&(ap==="all"||r.application===ap)&&(ct==="all"||r.country===ct));
  const ys=[...new Set(rows.map(r=>r.year))].sort();
  const sum=(k,y)=>rows.filter(r=>r.year===y).reduce((a,r)=>a+r[k],0);
  Plotly.react("c1",[["contracted_t","contratado","#3987e5"],["qualified_pipeline_t","pipeline qualificado (relação documentada)","#9085e9"],["unqualified_potential_t","potencial não qualificado","#B6B3BA"]].map(([k,n,c])=>({type:"bar",name:n,x:ys,y:ys.map(y=>sum(k,y)),marker:{color:c,line:{color:"#0B0630",width:2}},hovertemplate:"%{x}: %{y:,.0f} t<extra>"+n+"</extra>"})),
    Object.assign({},L,{barmode:"stack",title:{text:"Volume incremental (t SKU/ano)",font:{size:13,color:"#fff"}},yaxis:{gridcolor:"#3A3550"}}),{displayModeBar:false,responsive:true});
  const pr=ys.map(y=>{const rr=rows.filter(r=>r.year===y);const w=rr.reduce((a,r)=>a+r.qualified_pipeline_t+r.unqualified_potential_t,0);return w?Math.round(100*rr.reduce((a,r)=>a+r.unit_margin_usd_kg_dha*(r.qualified_pipeline_t+r.unqualified_potential_t),0)/w)/100:null;});
  const pmax=Math.max(1,...pr.filter(v=>v!==null));
  Plotly.react("c2",[{type:"scatter",mode:"lines+markers",x:ys,y:pr,line:{color:"#d55181",width:2},name:"margem ponderada",hovertemplate:"%{x}: US$ %{y:.1f}/kg DHA<extra></extra>"}],
    Object.assign({},L,{title:{text:"Margem de contribuição ponderada (US$/kg DHA)",font:{size:13,color:"#fff"}},yaxis:{gridcolor:"#3A3550",range:[0,pmax*1.3]},xaxis:{gridcolor:"#3A3550"}}),{displayModeBar:false,responsive:true});
  const m=D.markets[sc].filter(r=>(ap==="all"||r.application===ap)&&(ct==="all"||r.country===ct));
  $("tb").innerHTML="<tr><th>País</th><th>Nicho</th><th>Grupo</th><th>Status</th><th>TAM 2030 (t DHA)</th><th>SAM 2030</th><th>Incremental 2030 (t SKU)</th><th>Incremental 2035</th><th>Receita 2030 (US$ mi)</th><th>P(qualif.)</th><th>VPL comercial (US$ mi)</th><th>Confiança</th></tr>"+
    m.map(r=>`<tr><td>${r.country}</td><td>${r.application}</td><td>${r.group}</td><td>${r.relationship_status}</td><td>${r.tam_dha_2030_t.toFixed(0)}</td><td>${r.sam_dha_2030_t.toFixed(0)}</td><td>${r.incremental_sku_2030_t.toFixed(0)}</td><td>${r.incremental_sku_2035_t.toFixed(0)}</td><td>${r.revenue_2030_musd.toFixed(1)}</td><td>${(100*r.p_qualification).toFixed(0)}%</td><td>${r.commercial_npv_musd.toFixed(1)}</td><td>${r.data_confidence}</td></tr>`).join("");
  $("ft").textContent=`Cenário ativo: ${sc}. Fontes: source_registry.csv (status de acesso por linha); premissas: market_assumptions.csv, market_parameters.csv, nutrition_requirements.csv. Gerado ${D.generated}.`;
}
["sc","ap","ct"].forEach(i=>$(i).addEventListener("input",render)); render();
</script></body></html>"""


def build(path: Path, curves: pd.DataFrame, mkts: dict, generated: str) -> None:
    data = {"curves": curves.round(4).to_dict(orient="records"),
            "markets": {k: v.round(4).to_dict(orient="records") for k, v in mkts.items()}, "generated": generated}
    path.write_text(PAGE.replace("__PLOTLY__", get_plotlyjs()).replace("__DATA__", json.dumps(data, ensure_ascii=False)),
                    encoding="utf-8")
