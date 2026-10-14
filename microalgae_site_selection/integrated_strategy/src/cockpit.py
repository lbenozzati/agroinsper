"""integrated_decision_cockpit.html: the v3 JS engine fed with market-study demand rows, policies and auxiliary drivers."""

from __future__ import annotations

import json
from pathlib import Path

from plotly.offline import get_plotlyjs

PAGE = r"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Integrated DHA Cockpit</title><style>
:root{--ink:#fff;--ink2:#D5D2DA;--muted:#B6B3BA;--grid:#3A3550;--border:#E7E3EA33;--blue:#3987e5;--mag:#d55181;--vio:#9085e9}
*{box-sizing:border-box}body{margin:0;font-family:Montserrat,Segoe UI,Arial,sans-serif;color:var(--ink);background:linear-gradient(160deg,#000E38,#060216 55%,#2E0133);min-height:100vh}
header{padding:16px 22px 4px}h1{margin:0;font-size:22px}h2{font-size:14px;margin:0 0 8px;color:var(--ink2);font-weight:600}.sub{color:var(--ink2);font-size:12.5px;margin-top:4px}
.warn{display:none;background:#8C2F7855;border:1px solid var(--mag);border-radius:6px;padding:6px 10px;font-size:12px;margin:6px 22px}
.grid{display:grid;grid-template-columns:330px 1fr;gap:14px;padding:10px 22px 18px}.panel{background:rgba(255,255,255,.05);border:1px solid var(--border);border-radius:10px;padding:12px}
label{display:block;font-size:12px;color:var(--ink2);margin:9px 0 2px}.val{float:right;color:#fff;font-weight:600}input[type=range]{width:100%}
select{width:100%;background:#0B0630;color:#fff;border:1px solid var(--border);border-radius:6px;padding:4px}.chk{display:inline-block;margin:2px 8px 2px 0;font-size:12px}
.kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:10px}.kpi{background:rgba(255,255,255,.05);border:1px solid var(--border);border-radius:8px;padding:9px}.kpi b{display:block;font-size:18px}.kpi span{font-size:11px;color:var(--ink2)}
table{width:100%;border-collapse:collapse;font-size:12px}th,td{padding:5px;border-bottom:1px solid var(--grid);text-align:right}th:first-child,td:first-child{text-align:left}th{color:var(--ink2)}tr.best td{background:#3987e522;font-weight:700}
.charts{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:12px}.foot{font-size:11px;color:var(--muted);padding:0 22px 20px}
@media(max-width:950px){.grid,.charts{grid-template-columns:1fr}.kpis{grid-template-columns:1fr 1fr}}
</style></head><body>
<header><h1>Painel integrado — capacidade, origem, mercados e momento do investimento</h1>
<div class="sub">Motor de caixa da v3 (paridade testada com Python) alimentado pela demanda do estudo de mercado. Controles exploram premissas; <b>não são previsões da Corbion</b>. Contratado padrão = 0 (nenhum contrato público).</div></header>
<div class="warn" id="warn"></div>
<div class="grid"><div class="panel">
<h2>Controles principais</h2>
<label>(a) Volume contratado firme incremental (t SKU/ano, desde __CSY__)<span class="val" id="v_ct"></span></label><input type="range" id="ct" min="0" max="30000" step="500">
<label>Parcela asiática do contratado<span class="val" id="v_as"></span></label><input type="range" id="as" min="0" max="1" step="0.05">
<label>(b) Preço líquido (multiplicador do preço do estudo de mercado)<span class="val" id="v_pm"></span></label><input type="range" id="pm" min="0.4" max="2.2" step="0.05">
<label>(c) Capex incremental Orindiúva, módulo 1 (US$ mi)<span class="val" id="v_cx"></span></label><input type="range" id="cx" min="30" max="250" step="1">
<h2 style="margin-top:14px">Mercado e cenário</h2>
<label>Cenário do estudo de mercado</label><select id="ms"><option value="low">baixo (stress)</option><option value="base" selected>base</option><option value="high">alto</option></select>
<label>Pesos do pipeline (v3)</label><select id="pw"><option value="stress">stress</option><option value="base" selected>base</option><option value="upside">upside</option><option value="none">só contratos</option></select>
<h2 style="margin-top:14px">Auxiliares (independentes salvo indicação)</h2>
<label>Óleo de peixe (US$/t; só preço via repasse 0,4)<span class="val" id="v_fo"></span></label><input type="range" id="fo" min="2500" max="6800" step="100">
<label>Açúcar Brasil (×)<span class="val" id="v_sb"></span></label><input type="range" id="sb" min="0.7" max="1.5" step="0.05">
<label>Açúcar Tailândia (×)<span class="val" id="v_st"></span></label><input type="range" id="st" min="0.7" max="1.4" step="0.05">
<label>Frete (×)<span class="val" id="v_fr"></span></label><input type="range" id="fr" min="0.5" max="3" step="0.1">
<label>Choque real BRL (+ = depreciação)<span class="val" id="v_fx"></span></label><input type="range" id="fx" min="-0.2" max="0.3" step="0.05">
<label>Atraso Tailândia (anos: licença/qualificação)<span class="val" id="v_dl"></span></label><input type="range" id="dl" min="0" max="3" step="1">
<h2 style="margin-top:14px">Filtros (afetam a demanda usada)</h2><div id="fa"></div><label>Região</label><div id="fg"></div><label>País</label><div id="fc"></div>
<label>Ano de leitura</label><select id="yr"></select><label>Política em destaque</label><select id="pol"></select>
</div><div>
<div class="kpis" id="kpis"></div>
<div class="panel"><h2>Políticas (VPL nominal USD com valor terminal; p10 = Monte Carlo conjunto, cenário base, estático)</h2><table id="tb"></table><div class="sub" id="seq"></div></div>
<div class="charts"><div class="panel"><h2>Fronteira: ΔVPL (B Orindiúva+Tailândia − A Orindiúva), US$ mi</h2><div id="c1" style="height:330px"></div></div>
<div class="panel"><h2>Carteira × capacidade da política em destaque (t SKU/ano)</h2><div id="c2" style="height:330px"></div></div></div>
<div class="panel" style="margin-top:12px"><h2>Rotas 2030: margem entregue por origem (US$/kg DHA) — passe o mouse para fonte e ano</h2><table id="rt"></table></div>
<div class="panel" style="margin-top:12px"><h2>Gates dos sites (v3)</h2><table id="gt"></table></div>
</div></div><div class="foot" id="ft"></div>
<script>__PLOTLY__</script><script>__ENGINE__</script><script>
const D=__DATA__, E=DHAEngine, $=id=>document.getElementById(id);
const fmt=(v,d=0)=>v===null||v===undefined||isNaN(v)?"—":v.toLocaleString("pt-BR",{minimumFractionDigits:d,maximumFractionDigits:d});
const pct=v=>v===null||v===undefined?"—":(100*v).toFixed(1)+"%";
function boxes(id,vals,lab){$(id).innerHTML=vals.map(v=>`<span class="chk"><input type="checkbox" class="${id}" value="${v}" checked> ${lab?lab[v]||v:v}</span>`).join("");}
const allRows=Object.values(D.demand).flat();
boxes("fa",[...new Set(allRows.map(r=>r.application))],D.app_label);boxes("fg",D.regions);boxes("fc",[...new Set(allRows.map(r=>r.country))].sort());
D.years.forEach(y=>{const o=document.createElement("option");o.value=y;o.text=y;if(y===2032)o.selected=true;$("yr").appendChild(o);});
Object.keys(D.policies).forEach(k=>{const o=document.createElement("option");o.value=k;o.text=D.policies[k].label;if(k==="A_ORI_1")o.selected=true;$("pol").appendChild(o);});
const CX0=Math.round(D.capex_ori_base/1e6);
$("ct").value=0;$("as").value=0.5;$("pm").value=1;$("cx").value=CX0;$("fo").value=D.fish_oil_base;$("sb").value=1;$("st").value=1;$("fr").value=1;$("fx").value=0;$("dl").value=0;
const chk=c=>[...document.querySelectorAll("."+c+":checked")].map(e=>e.value);
function S(){return{ct:+$("ct").value,as:+$("as").value,pm:+$("pm").value,cx:+$("cx").value,ms:$("ms").value,pw:$("pw").value,fo:+$("fo").value,sb:+$("sb").value,st:+$("st").value,fr:+$("fr").value,fx:+$("fx").value,dl:+$("dl").value,fa:chk("fa"),fg:chk("fg"),fc:chk("fc"),yr:+$("yr").value,pol:$("pol").value};}
function params(s,o){
  o=o||{};const p=JSON.parse(JSON.stringify(D.p[s.ms]));
  const w=s.pw==="none"?{contracted:1,qualified_pipeline:0,unqualified_potential:0}:p.scenario_weights[s.pw];
  const rows=D.demand[s.ms].filter(r=>s.fa.indexOf(r.application)>=0&&s.fg.indexOf(r.market)>=0&&s.fc.indexOf(r.country)>=0);
  let d=E.weightedDemand(rows,w,p.regions,D.years,null);
  const ct=o.ct!==undefined?o.ct:s.ct, as=o.as!==undefined?o.as:s.as;
  if(ct>0)d=E.addContracted(d,ct,as,D.mix[s.ms],p.asia_regions,D.contract_start);
  p.demand=d;p.price_dha=p.price_dha*(o.pm!==undefined?o.pm:s.pm);p.fish_oil=s.fo;
  p.capex_override=s.cx===CX0?{}:{BR_ORI_EXP:s.cx*1e6};
  for(const k in p.sites){p.sites[k].sugar*=p.sites[k].country==="BR"?s.sb:s.st;}
  for(const c in p.freight)for(const r in p.freight[c])p.freight[c][r].usd*=s.fr;
  p.fx_shock.BR=s.fx;p.delay={TH_NSN:s.dl};return p;}
function run(p,k){const pol=D.policies[k];if(!pol.units.length){const z=D.years.map(()=>0);return{npv:0,npv_ex_tv:0,irr:null,utilisation:z,capacity_t:z,sold_t:z,units:[],lines:null,peak_funding:0};}return E.runAlternative(p,{units:pol.units,hub:!!pol.hub});}
function margin(p,r){if(!r.lines)return null;const L=r.lines,sum=a=>a.reduce((x,y)=>x+y,0);const kg=sum(r.sold_t)*p.dha_fraction*1000;return kg>0?(sum(L.revenue)-sum(L.var_cost)-sum(L.freight)-sum(L.transit))/kg:null;}
function asiaNeeded(s){const f=v=>{const p=params(s,{ct:v,as:1});return run(p,"B_ORI_TH_NOW").npv-run(p,"A_ORI_1").npv;};let lo=0,hi=40000;if(f(lo)>=0)return 0;if(f(hi)<0)return null;for(let i=0;i<22;i++){const m=(lo+hi)/2;if(f(m)>=0)hi=m;else lo=m;}return hi;}
function warn(s){const w=[];const b=D.bounds;
 if(s.pm<b.pm[0]||s.pm>b.pm[1])w.push(`Preço ×${s.pm} fora da faixa justificada ${b.pm.join("–")}: EXTRAPOLAÇÃO.`);
 if(s.cx<b.cx[0]||s.cx>b.cx[1])w.push(`Capex US$ ${s.cx} mi fora de ${b.cx.map(v=>v.toFixed(0)).join("–")}: EXTRAPOLAÇÃO.`);
 if(s.ct>b.ct)w.push(`Contrato de ${fmt(s.ct)} t acima do pipeline qualificado do cenário alto em 2030 (${fmt(b.ct)} t): EXTRAPOLAÇÃO.`);
 if(s.fr>2)w.push("Frete ×"+s.fr+" acima das cotações observadas (2026): cenário de ruptura.");
 w.push("Dependências: o óleo de peixe move só o preço aqui; no Monte Carlo ele também move a adoção (ρ=0,4). Demais auxiliares são independentes.");
 $("warn").style.display="block";$("warn").innerHTML=w.join("<br>");}
let tm=null;
function render(){const s=S();
 $("v_ct").textContent=fmt(s.ct)+" t";$("v_as").textContent=Math.round(100*s.as)+"%";$("v_pm").textContent="×"+s.pm.toFixed(2)+" (US$ "+(D.p[s.ms].price_dha*s.pm).toFixed(1)+"/kg base)";
 $("v_cx").textContent=s.cx===CX0?(D.capex_ori_base/1e6).toFixed(1)+" (modelo)":s.cx;$("v_fo").textContent=fmt(s.fo);$("v_sb").textContent="×"+s.sb;$("v_st").textContent="×"+s.st;$("v_fr").textContent="×"+s.fr;$("v_fx").textContent=s.fx;$("v_dl").textContent=s.dl;
 warn(s);const p=params(s);const iy=D.years.indexOf(s.yr);const R={};Object.keys(D.policies).forEach(k=>R[k]=run(p,k));
 const order=Object.keys(R).sort((a,b)=>R[b].npv-R[a].npv);const best=order[0],second=order[1];
 let h="<tr><th>Política</th><th>VPL</th><th>Δ vs melhor</th><th>VPL s/ VT</th><th>TIR</th><th>Utiliz. "+s.yr+"</th><th>Margem entregue (US$/kg DHA)</th><th>Caixa mínimo acumulado</th><th>p10 MC (base)</th><th>Unidades</th></tr>";
 Object.keys(D.policies).forEach(k=>{const r=R[k];h+=`<tr class="${k===best?'best':''}"><td>${D.policies[k].label}</td><td>${fmt(r.npv/1e6,1)}</td><td>${fmt((r.npv-R[best].npv)/1e6,1)}</td><td>${fmt(r.npv_ex_tv/1e6,1)}</td><td>${pct(r.irr)}</td><td>${pct(r.utilisation[iy])}</td><td>${fmt(margin(p,r),1)}</td><td>${fmt(r.peak_funding/1e6,1)}</td><td>${fmt(D.p10[k],0)}</td><td>${r.units.map(u=>u.id.replace("BR_ORI_EXP","ORI").replace("TH_NSN","NSN")+"@"+u.online).join(", ")||"—"}</td></tr>`;});
 $("tb").innerHTML=h;
 const need=asiaNeeded(s);
 $("kpis").innerHTML=[["Melhor política",D.policies[best].label.split(" ")[0]+" · US$ "+fmt(R[best].npv/1e6,0)+" mi"],["Diferença 1ª − 2ª",`US$ ${fmt((R[best].npv-R[second].npv)/1e6,1)} mi vs ${D.policies[second].label.split(" ")[0]}`],["Contrato asiático p/ B > A",need===null?"> 40.000 t":fmt(need)+" t/ano"],["Caixa mínimo (destaque)","US$ "+fmt(R[s.pol].peak_funding/1e6,1)+" mi"]].map(([a,b])=>`<div class="kpi"><span>${a}</span><b>${b}</b></div>`).join("");
 $("seq").innerHTML=`Se nenhuma política tem VPL > 0, a leitura é <b>esperar/qualificar demanda</b>. Valor de diversificação só via fluxos e stress (resilience_value em stress_tests.csv), sem prêmio somado.`;
 portfolio(s,p,R[s.pol]);routes(s);clearTimeout(tm);tm=setTimeout(()=>front(s),150);
 $("ft").textContent=`Cenário de mercado ${s.ms}; pesos ${s.pw}; demanda: ${D.demand_source}; preço: estudo de mercado (B001, faixa de óleo de peixe conflitante); custos v3; motor v${D.v3_version}; gerado ${D.generated}.`;}
function front(s){const z=D.fr.vols.map(v=>D.fr.pms.map(pm=>{const p=params(s,{ct:v,as:1,pm:pm});return(run(p,"B_ORI_TH_NOW").npv-run(p,"A_ORI_1").npv)/1e6;}));
 const xs=D.fr.pms.map(pm=>+(D.p[s.ms].price_dha*pm).toFixed(1));const m=Math.max(1,...z.flat().map(Math.abs));
 Plotly.react("c1",[{type:"heatmap",x:xs,y:D.fr.vols,z:z,zmin:-m,zmax:m,colorscale:[[0,"#3987e5"],[0.5,"#3a3550"],[1,"#d55181"]],hovertemplate:"US$ %{x}/kg DHA<br>Ásia contratada %{y} t<br>ΔVPL %{z:.1f} mi<extra></extra>",colorbar:{tickfont:{color:"#D5D2DA"}}},
  {type:"contour",x:xs,y:D.fr.vols,z:z,contours:{start:0,end:0,size:1,coloring:"none"},line:{color:"#fff",width:3},showscale:false,hoverinfo:"skip"},
  {type:"scatter",x:[+(D.p[s.ms].price_dha*s.pm).toFixed(1)],y:[s.ct*s.as],mode:"markers",marker:{size:12,color:"#fff",symbol:"x"},hoverinfo:"skip"}],
  {paper_bgcolor:"rgba(0,0,0,0)",plot_bgcolor:"rgba(0,0,0,0)",font:{color:"#D5D2DA",size:11},margin:{l:55,r:10,t:10,b:40},showlegend:false,xaxis:{title:"US$/kg DHA"},yaxis:{title:"t/ano asiáticas contratadas"}},{displayModeBar:false,responsive:true});}
function portfolio(s,p,r){const ys=D.years.filter(y=>y>=2028);const rows=D.demand[s.ms].filter(x=>s.fa.indexOf(x.application)>=0&&s.fg.indexOf(x.market)>=0&&s.fc.indexOf(x.country)>=0);
 const w=s.pw==="none"?{contracted:1,qualified_pipeline:0,unqualified_potential:0}:D.p[s.ms].scenario_weights[s.pw];
 const lay=st=>ys.map(y=>rows.filter(x=>x.year===y&&x.opportunity_status===st).reduce((a,x)=>a+x.eligible_final_product_t*x.inclusion_rate*x.expected_supplier_share*w[st],0));
 const tr=[{type:"bar",name:"firme (controle)",x:ys,y:ys.map(y=>y>=D.contract_start?s.ct:0),marker:{color:"#3987e5"}},{type:"bar",name:"pipeline qualificado (ponderado)",x:ys,y:lay("qualified_pipeline"),marker:{color:"#9085e9"}},{type:"bar",name:"potencial (ponderado)",x:ys,y:lay("unqualified_potential"),marker:{color:"#B6B3BA"}},
  {type:"scatter",mode:"lines+markers",name:"capacidade efetiva",x:ys,y:ys.map(y=>r.capacity_t[D.years.indexOf(y)]),line:{color:"#d55181",width:2}}];
 Plotly.react("c2",tr,{barmode:"stack",paper_bgcolor:"rgba(0,0,0,0)",plot_bgcolor:"rgba(0,0,0,0)",font:{color:"#D5D2DA",size:11},margin:{l:55,r:10,t:10,b:40},legend:{orientation:"h",y:-0.2},yaxis:{gridcolor:"#3A3550"}},{displayModeBar:false,responsive:true});}
function routes(s){const rr=D.routes.filter(r=>s.fc.indexOf(r.dest_country)>=0&&s.fg.indexOf(r.region)>=0&&(s.fa.indexOf(r.niche)>=0||s.fa.indexOf("shrimp/fish")>=0&&r.region==="CHINA"));
 const keys=[...new Set(rr.map(r=>r.dest_country+"|"+r.niche))];
 $("rt").innerHTML="<tr><th>Destino · nicho</th><th>Orindiúva</th><th>Greenfield GO</th><th>Nakhon Sawan</th><th>Rayong</th></tr>"+keys.map(k=>{const [c,n]=k.split("|");const cell=o=>{const r=rr.find(x=>x.dest_country===c&&x.niche===n&&x.origin_site===o);return r?`<td title="${r.sources} · ano ${r.year} · confiança volume ${r.volume_confidence}${r.route_note?' · '+r.route_note:''}">${fmt(r.contribution_usd_kg_dha,1)}${r.route_legal_at_start?'':' *'}</td>`:"<td>—</td>";};return `<tr><td>${c} · ${D.app_label[n]||n}</td>${cell("BR_ORI_EXP")}${cell("BR_GF_GO")}${cell("TH_NSN")}${cell("TH_RYG")}</tr>`;}).join("");}
$("gt").innerHTML="<tr><th>Site</th>"+D.gate_names.map(g=>`<th>${g}</th>`).join("")+"</tr>"+Object.keys(D.gates).map(s=>`<tr><td>${s}</td>${D.gate_names.map(g=>`<td title="${(D.gates[s][g]||{}).basis||''}">${(D.gates[s][g]||{}).status||'—'}</td>`).join("")}</tr>`).join("");
document.querySelectorAll("input,select").forEach(e=>e.addEventListener("input",render));render();
</script></body></html>"""


def build(path: Path, engine_js: str, payload: dict, contract_start: int) -> None:
    html = (PAGE.replace("__PLOTLY__", get_plotlyjs()).replace("__ENGINE__", engine_js)
            .replace("__DATA__", json.dumps(payload, ensure_ascii=False, default=float)).replace("__CSY__", str(contract_start)))
    path.write_text(html, encoding="utf-8")
