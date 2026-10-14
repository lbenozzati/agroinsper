// Port of src/engine.py (same algorithm, same parameter dict). Used by decision_cockpit.html and by the
// parity test (tests/test_cockpit_parity.py runs this file with node and compares NPVs with Python).
(function (root) {
  "use strict";
  const MODS = ["fermentation", "downstream", "utilities", "effluent", "buildings", "epc_owner"];

  function years(p) { const y = []; for (let k = p.base_year; k <= p.end_year; k++) y.push(k); return y; }
  function infl(p, y) { return Math.pow(1 + p.infl_usd, y - p.base_year); }
  function fxadj(p, c, share) { return share / (1 + p.fx_shock[c]) + (1 - share); }
  function sugarPerT(p) { return p.dha_fraction / (p.dha_yield * p.recovery); }

  function variableCostLines(p, site) {
    const s = p.sites[site], c = s.country;
    const L = {
      sugar: sugarPerT(p) * s.sugar * fxadj(p, c, s.sugar_local),
      electricity: p.kwh_per_t * s.elec * fxadj(p, c, 0.9),
      steam: p.steam_per_t * s.steam * fxadj(p, c, 0.9),
      water_effluent: p.water_per_t * s.water * fxadj(p, c, 1.0),
      nutrients_packaging: (p.nutrients + p.packaging) * fxadj(p, c, 0.3),
    };
    let sum = 0; for (const k in L) sum += L[k];
    L.indirect_tax_leakage = p.country[c].leak * sum;
    return L;
  }
  function variableCost(p, site) { const L = variableCostLines(p, site); let s = 0; for (const k in L) s += L[k]; return s; }

  function unitCapex(p, unit) {
    const s = p.sites[unit.site], c = s.country;
    const directGf = p.module_t * p.capex_intensity * s.loc;
    const f = {}; MODS.forEach(m => f[m] = 1.0);
    if (s.brownfield) {
      f.utilities = unit.utilities_factor !== undefined ? unit.utilities_factor : p.bf_utilities;
      f.buildings = unit.buildings_factor !== undefined ? unit.buildings_factor : p.bf_buildings;
      f.epc_owner = p.bf_owner;
    }
    let mods = {}; let direct = 0;
    MODS.forEach(m => { mods[m] = directGf * p.share[m] * f[m]; direct += mods[m]; });
    let cont = (s.brownfield ? p.cont_bf : p.cont_gf) * direct;
    let duty = p.import_share * direct * p.country[c].duty;
    const mod1 = (unit.module || 1) === 1;
    let conn = mod1 ? s.conn : 0.0, land = mod1 ? s.land : 0.0;
    let total = direct + cont + duty + conn + land;
    const ov = p.capex_override[unit.site];
    if (ov !== undefined && ov !== null && mod1) {
      const scale = ov / total;
      for (const m in mods) mods[m] *= scale;
      cont *= scale; duty *= scale; conn *= scale; land *= scale; total = ov;
    }
    total *= p.capex_mult[c];
    return Object.assign({}, mods, { contingency: cont, import_duty: duty, connection: conn, land: land, total: total,
      land_share: total ? (land * p.capex_mult[c]) / total : 0.0 });
  }

  function ramp(p, y, online) { const k = y - online; if (k < 0) return 0.0; return k === 0 ? p.ramp1 : k === 1 ? p.ramp2 : 1.0; }

  function pricePerT(p, r, y) {
    const fish = Math.pow(p.fish_oil / p.fish_oil_base, p.passthrough);
    return p.price_dha * p.price_mult[r] * fish * p.dha_fraction * 1000 * infl(p, y);
  }

  function allocate(supply, demand, edges) {
    const plants = Object.keys(supply).sort(), regions = Object.keys(demand).sort();
    const nodes = ["S"].concat(plants.map(x => "p:" + x), regions.map(x => "r:" + x), ["T"]);
    const idx = {}; nodes.forEach((n, i) => idx[n] = i);
    const arcs = [];
    function add(u, v, cap, cost) { arcs.push([idx[u], idx[v], cap, cost, arcs.length + 1]); arcs.push([idx[v], idx[u], 0.0, -cost, arcs.length - 1]); }
    plants.forEach(x => add("S", "p:" + x, Math.max(supply[x], 0.0), 0.0));
    const edgeArc = {};
    plants.forEach(x => regions.forEach(r => {
      const e = edges[x + "|" + r];
      if (e) { const m = e[0], cap = e[1]; if (m > 0 && cap > 1e-9) { edgeArc[x + "|" + r] = arcs.length; add("p:" + x, "r:" + r, cap, -m); } }
    }));
    regions.forEach(r => add("r:" + r, "T", Math.max(demand[r], 0.0), 0.0));
    const n = nodes.length, t = idx["T"];
    for (let it = 0; it < 4 * n * n + 10; it++) {
      const dist = new Array(n).fill(Infinity), prev = new Array(n).fill(-1);
      dist[0] = 0.0;
      for (let k = 0; k < n - 1; k++) {
        let changed = false;
        for (let a = 0; a < arcs.length; a++) {
          const [u, v, cap, cost] = arcs[a];
          if (cap > 1e-9 && dist[u] + cost < dist[v] - 1e-12) { dist[v] = dist[u] + cost; prev[v] = a; changed = true; }
        }
        if (!changed) break;
      }
      if (dist[t] >= -1e-12 || prev[t] < 0) break;
      let push = Infinity, v = t;
      while (v !== 0) { const a = prev[v]; push = Math.min(push, arcs[a][2]); v = arcs[a][0]; }
      v = t;
      while (v !== 0) { const a = prev[v]; arcs[a][2] -= push; arcs[arcs[a][4]][2] += push; v = arcs[a][0]; }
    }
    const flows = {};
    for (const key in edgeArc) { const f = arcs[edgeArc[key] + 1][2]; if (f > 1e-9) flows[key] = f; }
    return flows;
  }

  function resolveUnits(p, alt) {
    const units = [], count = {};
    const baseUnits = alt.units.filter(u => !u.conditional);
    for (const u of alt.units) {
      const s = p.sites[u.site];
      count[u.site] = (count[u.site] || 0) + 1;
      const unit = Object.assign({}, u, { module: count[u.site], id: u.site + "#" + count[u.site] });
      let first = s.first_capex;
      if (u.conditional) {
        const dy = p.decision_year;
        let triggered;
        if (u.conditional === "asia") {
          let asia = 0; p.asia_regions.forEach(r => asia += p.demand[r][String(dy)]);
          triggered = asia >= p.th_trigger_t;
        } else {
          const probe = runAlternative(p, Object.assign({}, alt, { units: baseUnits }));
          triggered = probe.utilisation[probe.years.indexOf(dy)] >= p.staged_trigger_util;
        }
        if (!triggered) continue;
        first = dy;
      }
      unit.first_capex = first;
      unit.online = first + s.build + (p.delay[u.site] || 0);
      units.push(unit);
    }
    return units;
  }

  function zeros(n) { return new Array(n).fill(0.0); }

  function runAlternative(p, alt) {
    const ys = years(p), N = ys.length;
    const units = resolveUnits(p, alt);
    const hub = !!alt.hub;
    const out = { years: ys, units: units.map(u => ({ id: u.id, site: u.site, online: u.online, first_capex: u.first_capex })) };
    if (!units.length) {
      return Object.assign(out, { npv: 0, npv_ex_tv: 0, tv_pv: 0, irr: null, utilisation: zeros(N), capacity_t: zeros(N),
        sold_t: zeros(N), fcf: zeros(N), lcod: null, disc_payback: null, peak_funding: 0, sold_by_region: {}, lines: {} });
    }
    const caps = {}; units.forEach(u => caps[u.id] = unitCapex(p, u));
    const sites = Array.from(new Set(units.map(u => u.site))).sort();
    const siteOnline = {}; sites.forEach(s => siteOnline[s] = Math.min.apply(null, units.filter(u => u.site === s).map(u => u.online)));
    const KEYS = ["revenue", "var_cost", "freight", "transit", "fixed", "hub", "ebitda", "tax", "topup", "capex", "d_wc", "qrtc", "fcf", "sold_t", "capacity_t", "dep"];
    const led = {}; units.forEach(u => { led[u.id] = {}; KEYS.forEach(k => led[u.id][k] = zeros(N)); });
    const soldByRegion = {}; p.regions.forEach(r => soldByRegion[r] = zeros(N));
    const brUnit = units.find(u => p.sites[u.site].country === "BR");
    const firstBr = brUnit ? brUnit.id : units[0].id;

    units.forEach(u => {
      const c = p.sites[u.site].country, ls = p.sites[u.site].capex_local;
      const n = p.sites[u.site].build + (p.delay[u.site] || 0);
      for (let k = 0; k < n; k++) {
        const y = u.first_capex + k, i = ys.indexOf(y);
        if (i >= 0) led[u.id].capex[i] += caps[u.id].total / n * infl(p, y) * fxadj(p, c, ls);
      }
    });
    if (hub) { const y = p.hub.capex_year; led[firstBr].capex[ys.indexOf(y)] += p.hub.capex * infl(p, y); }

    ys.forEach((y, i) => {
      const supply = {}, unitCap = {};
      units.forEach(u => {
        const o = (p.outage[u.site] || {})[String(y)] || 0.0;
        const ct = p.module_t * p.oee * ramp(p, y, u.online) * (1 - o);
        unitCap[u.id] = ct; supply[u.site] = (supply[u.site] || 0.0) + ct;
      });
      const demand = {}; p.regions.forEach(r => demand[r] = p.demand[r][String(y)]);
      const edges = {};
      sites.forEach(s => {
        const c = p.sites[s].country, vc = variableCost(p, s) * infl(p, y);
        p.regions.forEach(r => {
          if (r === "CHINA" && y < siteOnline[s] + p.sites[s].gacc_delay) return;
          const fr = p.freight[c][r], price = pricePerT(p, r, y);
          let margin = price - vc - fr.usd * infl(p, y) - price * fr.days / 365 * p.transit_rate;
          const asia = p.asia_regions.indexOf(r) >= 0;
          if (c === "BR" && asia && hub) margin -= p.hub.handling * infl(p, y);
          let cap = demand[r];
          if (c === "BR" && asia) cap *= hub ? p.asia_capture_hub : p.asia_capture_br;
          if (c === "TH" && !asia) cap *= p.west_capture_th;
          edges[s + "|" + r] = [margin, cap];
        });
      });
      const flows = allocate(supply, demand, edges);
      sites.forEach(s => {
        const c = p.sites[s].country, vc = variableCost(p, s) * infl(p, y);
        const sUnits = units.filter(u => u.site === s);
        let totCap = 0; sUnits.forEach(u => totCap += unitCap[u.id]);
        p.regions.forEach(r => {
          const f = flows[s + "|" + r] || 0.0;
          if (f <= 0) return;
          soldByRegion[r][i] += f;
          const fr = p.freight[c][r], price = pricePerT(p, r, y);
          sUnits.forEach(u => {
            const w = totCap > 0 ? unitCap[u.id] / totCap : 0.0, L = led[u.id];
            L.revenue[i] += f * w * price; L.var_cost[i] += f * w * vc;
            L.freight[i] += f * w * fr.usd * infl(p, y);
            L.transit[i] += f * w * price * fr.days / 365 * p.transit_rate;
            L.sold_t[i] += f * w;
            if (c === "BR" && p.asia_regions.indexOf(r) >= 0 && hub) L.hub[i] += f * w * p.hub.handling * infl(p, y);
          });
        });
      });
      units.forEach(u => led[u.id].capacity_t[i] = unitCap[u.id]);
      if (hub && y >= Math.min.apply(null, Object.values(siteOnline))) led[firstBr].hub[i] += p.hub.opex * infl(p, y);
    });

    units.forEach(u => {
      const c = p.sites[u.site].country, s = p.sites[u.site], cc = p.country[c], L = led[u.id];
      const capexReal = caps[u.id].total;
      const hubCapex = (hub && u.id === firstBr) ? p.hub.capex * infl(p, p.hub.capex_year) : 0.0;
      let sumCapex = 0; L.capex.forEach(v => sumCapex += v);
      const depreciable = (sumCapex - hubCapex) * (1 - caps[u.id].land_share) + hubCapex;
      let nol = 0.0, wcPrev = 0.0, nbv = 0.0;
      ys.forEach((y, i) => {
        const pre = y === u.online - 1 ? 0.5 : (y >= u.online ? 1.0 : 0.0);
        const payroll = s.headcount * cc.labour * fxadj(p, c, 1.0) * infl(p, y) * pre;
        const fixed = payroll + (p.maint_pct + p.ins_pct) * capexReal * infl(p, y) * (y >= u.online ? 1.0 : 0.0) + s.qa * infl(p, y) * pre;
        L.fixed[i] = fixed;
        const ebitda = L.revenue[i] - L.var_cost[i] - L.freight[i] - L.transit[i] - fixed - L.hub[i];
        L.ebitda[i] = ebitda;
        const dep = (y >= u.online && y < u.online + p.dep_years) ? depreciable / p.dep_years : 0.0;
        L.dep[i] = dep;
        nbv += L.capex[i] * (1 - caps[u.id].land_share) - dep;
        const ebit = ebitda - dep;
        const inHoliday = c === "TH" && y >= u.online && y < u.online + cc.holiday;
        const rate = inHoliday ? 0.0 : cc.cit;
        let tax;
        if (ebit < 0) { nol += -ebit; tax = 0.0; }
        else { const off = inHoliday ? 0.0 : Math.min(nol, cc.nol_cap * ebit); nol -= off; tax = rate * (ebit - off); }
        let topup = 0.0;
        if (cc.globe_applies && ebit > 0) {
          const etr = tax / ebit;
          if (etr < p.globe_rate) {
            const sbie = p.sbie_pay * payroll + p.sbie_asset * Math.max(nbv, 0.0);
            topup = (p.globe_rate - etr) * Math.max(0.0, ebit - sbie);
          }
        }
        L.tax[i] = tax; L.topup[i] = topup;
        const wc = p.wc_pct * L.revenue[i];
        L.d_wc[i] = wc - wcPrev; wcPrev = wc;
        if (c === "TH" && cc.qrtc > 0 && i > 0) L.qrtc[i] = cc.qrtc * L.capex[i - 1];
        L.fcf[i] = ebitda - tax - topup - L.capex[i] - L.d_wc[i] + L.qrtc[i];
      });
    });

    let npvEx = 0, tvPv = 0, pvCost = 0, pvKg = 0;
    const combinedDisc = zeros(N), tvNom = [];
    units.forEach(u => {
      const c = p.sites[u.site].country, w = p.country[c].wacc, L = led[u.id];
      ys.forEach((y, i) => {
        const df = Math.pow(1 + w, -(y - p.base_year + 1));
        npvEx += L.fcf[i] * df; combinedDisc[i] += L.fcf[i] * df;
        pvCost += (L.capex[i] + L.var_cost[i] + L.freight[i] + L.transit[i] + L.fixed[i] + L.hub[i] - L.qrtc[i]) * df;
        pvKg += L.sold_t[i] * p.dha_fraction * 1000 * df;
      });
      const T = N - 1;
      const sust = caps[u.id].total * infl(p, ys[T]) / p.economic_life;
      const e = L.ebitda[T];
      const tvCf = (e - p.country[c].cit * Math.max(0.0, e - sust) - sust) * (1 + p.g);
      const tv = tvCf / (w - p.g) * Math.pow(1 + w, -(ys[T] - p.base_year + 1));
      tvPv += tv; tvNom.push(tv * Math.pow(1 + w, ys[T] - p.base_year + 1));
    });
    const sum = (k, i) => units.reduce((a, u) => a + led[u.id][k][i], 0);
    const fcf = ys.map((_, i) => sum("fcf", i)), capT = ys.map((_, i) => sum("capacity_t", i)), sold = ys.map((_, i) => sum("sold_t", i));
    const util = sold.map((s, i) => capT[i] > 0 ? s / capT[i] : 0.0);
    let cum = 0, payback = null, anyCap = false;
    ys.forEach((y, i) => { cum += combinedDisc[i]; anyCap = anyCap || capT[i] > 0; if (payback === null && cum > 0 && anyCap) payback = y; });
    const flowsIrr = fcf.slice(0, N - 1).concat([fcf[N - 1] + tvNom.reduce((a, b) => a + b, 0)]);
    let running = 0, peak = 0; fcf.forEach(f => { running += f; peak = Math.min(peak, running); });
    const lines = {};
    ["revenue", "var_cost", "freight", "transit", "fixed", "hub", "ebitda", "tax", "topup", "capex", "d_wc", "qrtc", "fcf"].forEach(k => lines[k] = ys.map((_, i) => sum(k, i)));
    let capexReal = 0; units.forEach(u => capexReal += caps[u.id].total);
    return Object.assign(out, { npv: npvEx + tvPv, npv_ex_tv: npvEx, tv_pv: tvPv, irr: irr(flowsIrr), utilisation: util,
      capacity_t: capT, sold_t: sold, fcf: fcf, lcod: pvKg > 0 ? pvCost / pvKg : null, disc_payback: payback,
      peak_funding: peak, sold_by_region: soldByRegion, lines: lines, capex_real_total: capexReal });
  }

  function irr(flows) {
    const f = r => flows.reduce((a, v, k) => a + v / Math.pow(1 + r, k + 1), 0);
    let lo = -0.9, hi = 1.5, flo = f(lo), fhi = f(hi);
    if (flo * fhi > 0) return null;
    for (let k = 0; k < 200; k++) { const mid = (lo + hi) / 2, fm = f(mid); if (flo * fm <= 0) { hi = mid; fhi = fm; } else { lo = mid; flo = fm; } }
    return (lo + hi) / 2;
  }

  function msp(p, alt) {
    const f = price => runAlternative(Object.assign({}, p, { price_dha: price }), alt).npv;
    let lo = 2.0, hi = 150.0, flo = f(lo), fhi = f(hi);
    if (flo * fhi > 0) return null;
    for (let k = 0; k < 50; k++) { const mid = (lo + hi) / 2, fm = f(mid); if (flo * fm <= 0) hi = mid; else { lo = mid; flo = fm; } }
    return (lo + hi) / 2;
  }

  function skuVolume(row) { return row.eligible_final_product_t * row.inclusion_rate * row.expected_supplier_share; }

  function weightedDemand(rows, weights, regions, ys, filters) {
    const out = {}; regions.forEach(r => { out[r] = {}; ys.forEach(y => out[r][String(y)] = 0.0); });
    rows.forEach(row => {
      if (filters) for (const col in filters) { const al = filters[col]; if (al && al.length && al.indexOf(row[col]) < 0) return; }
      const eff = row.opportunity_status === "contracted" ? row.contracted_volume_t : skuVolume(row) * weights[row.opportunity_status];
      const y = String(row.year);
      if (out[row.market] && out[row.market][y] !== undefined) out[row.market][y] += eff;
    });
    return out;
  }

  function regionMix(rows, regions) {
    const v = {}; let tot = 0; regions.forEach(r => v[r] = 0);
    rows.forEach(row => { const s = skuVolume(row); v[row.market] += s; tot += s; });
    const out = {}; regions.forEach(r => out[r] = tot ? v[r] / tot : 0); return out;
  }

  function addContracted(demand, contracted, asiaShare, mix, asiaRegions, startYear) {
    const out = JSON.parse(JSON.stringify(demand));
    const rs = Object.keys(out), asia = rs.filter(r => asiaRegions.indexOf(r) >= 0), west = rs.filter(r => asiaRegions.indexOf(r) < 0);
    [[asia, asiaShare], [west, 1 - asiaShare]].forEach(([grp, share]) => {
      const tot = grp.reduce((a, r) => a + mix[r], 0) || 1.0;
      grp.forEach(r => { for (const y in out[r]) if (parseInt(y, 10) >= startYear) out[r][y] += contracted * share * mix[r] / tot; });
    });
    return out;
  }

  const api = { years, infl, fxadj, sugarPerT, variableCost, variableCostLines, unitCapex, allocate, runAlternative, irr, msp,
    weightedDemand, regionMix, addContracted };
  if (typeof module !== "undefined" && module.exports) module.exports = api; else root.DHAEngine = api;
})(typeof window !== "undefined" ? window : this);
