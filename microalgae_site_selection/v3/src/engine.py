"""Deterministic site/alternative engine: mass balance, modular capex, opex, network allocation, tax and DCF.

All money is nominal USD. Inputs are in USD of the base year; costs paid in local currency move with
relative PPP plus an explicit real-FX shock (`fx_shock`, + = real local depreciation). The same algorithm is
ported line by line to `cockpit_engine.js`; tests check both give the same NPV.
"""

from __future__ import annotations

import copy
import math

YEARS_KEY = "years"
CAPEX_MODULES = ("fermentation", "downstream", "utilities", "effluent", "buildings", "epc_owner")


def years(p: dict) -> list[int]:
    return list(range(p["base_year"], p["end_year"] + 1))


def infl(p: dict, year: int) -> float:
    return (1 + p["infl_usd"]) ** (year - p["base_year"])


def fxadj(p: dict, country: str, local_share: float) -> float:
    return local_share / (1 + p["fx_shock"][country]) + (1 - local_share)


def sugar_per_t(p: dict) -> float:
    """t sucrose per t SKU: DHA content / (DHA yield on sucrose x downstream recovery)."""
    return p["dha_fraction"] / (p["dha_yield"] * p["recovery"])


def variable_cost_lines(p: dict, site: str) -> dict:
    """Variable cost per t SKU in base-year USD (before inflation), by component."""
    s = p["sites"][site]
    c = s["country"]
    lines = {
        "sugar": sugar_per_t(p) * s["sugar"] * fxadj(p, c, s["sugar_local"]),
        "electricity": p["kwh_per_t"] * s["elec"] * fxadj(p, c, 0.9),
        "steam": p["steam_per_t"] * s["steam"] * fxadj(p, c, 0.9),
        "water_effluent": p["water_per_t"] * s["water"] * fxadj(p, c, 1.0),
        "nutrients_packaging": (p["nutrients"] + p["packaging"]) * fxadj(p, c, 0.3),
    }
    lines["indirect_tax_leakage"] = p["country"][c]["leak"] * sum(lines.values())
    return lines


def variable_cost(p: dict, site: str) -> float:
    return sum(variable_cost_lines(p, site).values())


def unit_capex(p: dict, unit: dict) -> dict:
    """Modular capex (base-year USD) for one module; brownfield shares utilities/buildings/owner costs."""
    s = p["sites"][unit["site"]]
    c = s["country"]
    direct_gf = p["module_t"] * p["capex_intensity"] * s["loc"]
    factors = {m: 1.0 for m in CAPEX_MODULES}
    if s["brownfield"]:
        factors["utilities"] = unit.get("utilities_factor", p["bf_utilities"])
        factors["buildings"] = unit.get("buildings_factor", p["bf_buildings"])
        factors["epc_owner"] = p["bf_owner"]
    mods = {m: direct_gf * p["share"][m] * factors[m] for m in CAPEX_MODULES}
    direct = sum(mods.values())
    cont = (p["cont_bf"] if s["brownfield"] else p["cont_gf"]) * direct
    duty = p["import_share"] * direct * p["country"][c]["duty"]
    conn = s["conn"] if unit.get("module", 1) == 1 else 0.0
    land = s["land"] if unit.get("module", 1) == 1 else 0.0
    total = direct + cont + duty + conn + land
    override = p["capex_override"].get(unit["site"])
    if override is not None and unit.get("module", 1) == 1:
        scale = override / total
        mods = {m: v * scale for m, v in mods.items()}
        cont, duty, conn, land, total = cont * scale, duty * scale, conn * scale, land * scale, override
    total *= p["capex_mult"][c]
    return {**mods, "contingency": cont, "import_duty": duty, "connection": conn, "land": land,
            "total": total, "land_share": (land * p["capex_mult"][c]) / total if total else 0.0}


def ramp(p: dict, year: int, online: int) -> float:
    k = year - online
    if k < 0:
        return 0.0
    return p["ramp1"] if k == 0 else p["ramp2"] if k == 1 else 1.0


def price_per_t(p: dict, region: str, year: int) -> float:
    fish = (p["fish_oil"] / p["fish_oil_base"]) ** p["passthrough"]
    return p["price_dha"] * p["price_mult"][region] * fish * p["dha_fraction"] * 1000 * infl(p, year)


def allocate(supply: dict, demand: dict, edges: dict) -> dict:
    """Max-contribution transportation by successive shortest paths (Bellman-Ford on the residual graph).

    supply: {plant: t}, demand: {region: t}, edges: {(plant, region): (margin_per_t, cap_t)}.
    Only edges with positive margin are used. Returns {(plant, region): t}.
    """
    plants = sorted(supply)
    regions = sorted(demand)
    nodes = ["S"] + [f"p:{x}" for x in plants] + [f"r:{x}" for x in regions] + ["T"]
    idx = {n: i for i, n in enumerate(nodes)}
    arcs: list[list] = []  # [u, v, cap, cost, rev_index]

    def add(u, v, cap, cost):
        arcs.append([idx[u], idx[v], cap, cost, len(arcs) + 1])
        arcs.append([idx[v], idx[u], 0.0, -cost, len(arcs) - 1])

    for x in plants:
        add("S", f"p:{x}", max(supply[x], 0.0), 0.0)
    edge_arc = {}
    for x in plants:
        for r in regions:
            if (x, r) in edges:
                m, cap = edges[(x, r)]
                if m > 0 and cap > 1e-9:
                    edge_arc[(x, r)] = len(arcs)
                    add(f"p:{x}", f"r:{r}", cap, -m)
    for r in regions:
        add(f"r:{r}", "T", max(demand[r], 0.0), 0.0)
    n = len(nodes)
    eps = 1e-7  # costs are USD/t (10^2-10^4): ignore float noise that would create spurious negative cycles
    for _ in range(4 * n * n + 10):
        dist = [math.inf] * n
        prev = [-1] * n
        dist[0] = 0.0
        for _it in range(n - 1):
            changed = False
            for k, (u, v, cap, cost, _r) in enumerate(arcs):
                if cap > 1e-9 and dist[u] + cost < dist[v] - eps:
                    dist[v] = dist[u] + cost
                    prev[v] = k
                    changed = True
            if not changed:
                break
        t = idx["T"]
        if dist[t] >= -eps or prev[t] < 0:
            break
        path = []
        v = t
        while v != 0 and len(path) <= n:
            k = prev[v]
            path.append(k)
            v = arcs[k][0]
        if v != 0:  # predecessor cycle: no valid augmenting path left
            break
        push = min(arcs[k][2] for k in path)
        for k in path:
            arcs[k][2] -= push
            arcs[arcs[k][4]][2] += push
    flows = {}
    for key, k in edge_arc.items():
        f = arcs[k + 1][2]
        if f > 1e-9:
            flows[key] = f
    return flows


def _resolve_units(p: dict, alt: dict) -> list[dict]:
    units = []
    count: dict[str, int] = {}
    base_units = [u for u in alt["units"] if not u.get("conditional")]
    for u in alt["units"]:
        s = p["sites"][u["site"]]
        count[u["site"]] = count.get(u["site"], 0) + 1
        unit = dict(u, module=count[u["site"]], id=f"{u['site']}#{count[u['site']]}")
        first = int(u.get("first_capex", s["first_capex"]))
        if u.get("conditional"):
            dy = p["decision_year"]
            if u["conditional"] == "asia":
                asia = sum(p["demand"][r][str(dy)] for r in p["asia_regions"])
                triggered = asia >= p["th_trigger_t"]
            else:
                probe = run_alternative(p, dict(alt, units=base_units), _probe=True)
                i = probe[YEARS_KEY].index(dy)
                triggered = probe["utilisation"][i] >= p["staged_trigger_util"]
            if not triggered:
                continue
            first = dy
        unit["first_capex"] = first
        unit["online"] = first + s["build"] + int(p["delay"].get(u["site"], 0))
        units.append(unit)
    return units


def run_alternative(p: dict, alt: dict, _probe: bool = False) -> dict:
    ys = years(p)
    units = _resolve_units(p, alt)
    hub = bool(alt.get("hub"))
    out = {YEARS_KEY: ys, "units": [{"id": u["id"], "site": u["site"], "online": u["online"],
                                    "first_capex": u["first_capex"]} for u in units]}
    if not units:
        zero = [0.0] * len(ys)
        out.update(npv=0.0, npv_ex_tv=0.0, tv_pv=0.0, irr=None, utilisation=zero, capacity_t=zero,
                   sold_t=zero, fcf=zero, kg_dha=0.0, lcod=None, disc_payback=None, peak_funding=0.0,
                   sold_by_region={r: zero for r in p["regions"]}, lines={}, unit_npv={})
        return out
    caps = {u["id"]: unit_capex(p, u) for u in units}
    sites = sorted({u["site"] for u in units})
    site_online = {s: min(u["online"] for u in units if u["site"] == s) for s in sites}
    led = {u["id"]: {k: [0.0] * len(ys) for k in
                     ("revenue", "var_cost", "freight", "transit", "fixed", "hub", "ebitda", "tax", "topup",
                      "capex", "d_wc", "qrtc", "fcf", "sold_t", "capacity_t", "dep")} for u in units}
    sold_by_region = {r: [0.0] * len(ys) for r in p["regions"]}
    sold_by_site_region = {}
    first_br = next((u["id"] for u in units if p["sites"][u["site"]]["country"] == "BR"), units[0]["id"])

    for u in units:
        c = p["sites"][u["site"]]["country"]
        lshare = p["sites"][u["site"]]["capex_local"]
        n = p["sites"][u["site"]]["build"] + int(p["delay"].get(u["site"], 0))
        for k in range(n):
            y = u["first_capex"] + k
            if y in ys:
                led[u["id"]]["capex"][ys.index(y)] += caps[u["id"]]["total"] / n * infl(p, y) * fxadj(p, c, lshare)
    if hub:
        y = p["hub"]["capex_year"]
        led[first_br]["capex"][ys.index(y)] += p["hub"]["capex"] * infl(p, y)

    for i, y in enumerate(ys):
        supply = {}
        unit_cap = {}
        for u in units:
            out_frac = p["outage"].get(u["site"], {}).get(str(y), 0.0)
            capt = p["module_t"] * p["oee"] * ramp(p, y, u["online"]) * (1 - out_frac)
            unit_cap[u["id"]] = capt
            supply[u["site"]] = supply.get(u["site"], 0.0) + capt
        demand = {r: p["demand"][r][str(y)] for r in p["regions"]}
        edges = {}
        for s in sites:
            c = p["sites"][s]["country"]
            vc = variable_cost(p, s) * infl(p, y)
            for r in p["regions"]:
                if r == "CHINA" and y < site_online[s] + p["sites"][s]["gacc_delay"]:
                    continue
                fr = p["freight"][c][r]
                price = price_per_t(p, r, y)
                margin = price - vc - fr["usd"] * infl(p, y) - price * fr["days"] / 365 * p["transit_rate"]
                asia = r in p["asia_regions"]
                if c == "BR" and asia and hub:
                    margin -= p["hub"]["handling"] * infl(p, y)
                cap = demand[r]
                if c == "BR" and asia:
                    cap *= p["asia_capture_hub"] if hub else p["asia_capture_br"]
                if c == "TH" and not asia:
                    cap *= p["west_capture_th"]
                edges[(s, r)] = (margin, cap)
        flows = allocate(supply, demand, edges)
        for s in sites:
            c = p["sites"][s]["country"]
            vc = variable_cost(p, s) * infl(p, y)
            s_units = [u for u in units if u["site"] == s]
            tot_cap = sum(unit_cap[u["id"]] for u in s_units)
            for r in p["regions"]:
                f = flows.get((s, r), 0.0)
                if f <= 0:
                    continue
                sold_by_region[r][i] += f
                sold_by_site_region.setdefault(f"{s}|{r}", [0.0] * len(ys))[i] += f
                fr = p["freight"][c][r]
                price = price_per_t(p, r, y)
                for u in s_units:
                    w = unit_cap[u["id"]] / tot_cap if tot_cap > 0 else 0.0
                    L = led[u["id"]]
                    L["revenue"][i] += f * w * price
                    L["var_cost"][i] += f * w * vc
                    L["freight"][i] += f * w * fr["usd"] * infl(p, y)
                    L["transit"][i] += f * w * price * fr["days"] / 365 * p["transit_rate"]
                    L["sold_t"][i] += f * w
                    if c == "BR" and r in p["asia_regions"] and hub:
                        L["hub"][i] += f * w * p["hub"]["handling"] * infl(p, y)
        for u in units:
            led[u["id"]]["capacity_t"][i] = unit_cap[u["id"]]
        if hub and y >= min(site_online.values()):
            led[first_br]["hub"][i] += p["hub"]["opex"] * infl(p, y)

    for u in units:
        c = p["sites"][u["site"]]["country"]
        s = p["sites"][u["site"]]
        cc = p["country"][c]
        L = led[u["id"]]
        capex_real = caps[u["id"]]["total"]
        hub_capex = p["hub"]["capex"] * infl(p, p["hub"]["capex_year"]) if (hub and u["id"] == first_br) else 0.0
        depreciable = (sum(L["capex"]) - hub_capex) * (1 - caps[u["id"]]["land_share"]) + hub_capex
        nol = 0.0
        wc_prev = 0.0
        nbv = 0.0
        holiday_start = u["online"]
        for i, y in enumerate(ys):
            pre = 0.5 if y == u["online"] - 1 else (1.0 if y >= u["online"] else 0.0)
            payroll = s["headcount"] * cc["labour"] * fxadj(p, c, 1.0) * infl(p, y) * pre
            fixed = (payroll + (p["maint_pct"] + p["ins_pct"]) * capex_real * infl(p, y) * (1.0 if y >= u["online"] else 0.0)
                     + s["qa"] * infl(p, y) * pre)
            L["fixed"][i] = fixed
            ebitda = (L["revenue"][i] - L["var_cost"][i] - L["freight"][i] - L["transit"][i] - fixed - L["hub"][i])
            L["ebitda"][i] = ebitda
            dep = depreciable / p["dep_years"] if u["online"] <= y < u["online"] + p["dep_years"] else 0.0
            L["dep"][i] = dep
            nbv += L["capex"][i] * (1 - caps[u["id"]]["land_share"]) - dep
            ebit = ebitda - dep
            in_holiday = c == "TH" and holiday_start <= y < holiday_start + cc["holiday"]
            rate = 0.0 if in_holiday else cc["cit"]
            if ebit < 0:
                nol += -ebit
                tax = 0.0
            else:
                offset = min(nol, cc["nol_cap"] * ebit) if not in_holiday else 0.0
                nol -= offset
                tax = rate * (ebit - offset)
            topup = 0.0
            if cc["globe_applies"] and ebit > 0:
                etr = tax / ebit
                if etr < p["globe_rate"]:
                    sbie = p["sbie_pay"] * payroll + p["sbie_asset"] * max(nbv, 0.0)
                    topup = (p["globe_rate"] - etr) * max(0.0, ebit - sbie)
            L["tax"][i] = tax
            L["topup"][i] = topup
            wc = p["wc_pct"] * L["revenue"][i]
            L["d_wc"][i] = wc - wc_prev
            wc_prev = wc
            if c == "TH" and cc["qrtc"] > 0 and i > 0:
                L["qrtc"][i] = cc["qrtc"] * L["capex"][i - 1]
            L["fcf"][i] = ebitda - tax - topup - L["capex"][i] - L["d_wc"][i] + L["qrtc"][i]

    npv = npv_ex = tv_pv = 0.0
    pv_cost = pv_kg = 0.0
    unit_npv = {}
    combined_disc = [0.0] * len(ys)
    for u in units:
        c = p["sites"][u["site"]]["country"]
        w = p["country"][c]["wacc"]
        L = led[u["id"]]
        u_npv = 0.0
        for i, y in enumerate(ys):
            df = (1 + w) ** -(y - p["base_year"] + 1)
            u_npv += L["fcf"][i] * df
            combined_disc[i] += L["fcf"][i] * df
            pv_cost += (L["capex"][i] + L["var_cost"][i] + L["freight"][i] + L["transit"][i] + L["fixed"][i]
                        + L["hub"][i] - L["qrtc"][i]) * df
            pv_kg += L["sold_t"][i] * p["dha_fraction"] * 1000 * df
        T = len(ys) - 1
        sust = caps[u["id"]]["total"] * infl(p, ys[T]) / p["economic_life"]
        e = L["ebitda"][T]
        tv_cf = (e - p["country"][c]["cit"] * max(0.0, e - sust) - sust) * (1 + p["g"])
        tv = tv_cf / (w - p["g"]) * (1 + w) ** -(ys[T] - p["base_year"] + 1)
        L["tv_pv"] = tv
        npv_ex += u_npv
        tv_pv += tv
        unit_npv[u["id"]] = u_npv + tv
    npv = npv_ex + tv_pv
    fcf = [sum(led[u["id"]]["fcf"][i] for u in units) for i in range(len(ys))]
    cap_t = [sum(led[u["id"]]["capacity_t"][i] for u in units) for i in range(len(ys))]
    sold = [sum(led[u["id"]]["sold_t"][i] for u in units) for i in range(len(ys))]
    util = [s_ / c_ if c_ > 0 else 0.0 for s_, c_ in zip(sold, cap_t)]
    cum = 0.0
    payback = None
    for i, y in enumerate(ys):
        cum += combined_disc[i]
        if payback is None and cum > 0 and any(cap_t[: i + 1]):
            payback = y
    tv_nominal = sum(led[u["id"]]["tv_pv"] * (1 + p["country"][p["sites"][u["site"]]["country"]]["wacc"])
                     ** (ys[-1] - p["base_year"] + 1) for u in units)
    flows_irr = fcf[:-1] + [fcf[-1] + tv_nominal]
    running = 0.0
    peak = 0.0
    for f in fcf:
        running += f
        peak = min(peak, running)
    lines = {k: [sum(led[u["id"]][k][i] for u in units) for i in range(len(ys))]
             for k in ("revenue", "var_cost", "freight", "transit", "fixed", "hub", "ebitda", "tax", "topup",
                       "capex", "d_wc", "qrtc", "fcf")}
    out.update(npv=npv, npv_ex_tv=npv_ex, tv_pv=tv_pv, irr=irr(flows_irr), utilisation=util, capacity_t=cap_t,
               sold_t=sold, fcf=fcf, kg_dha=pv_kg, lcod=(pv_cost / pv_kg) if pv_kg > 0 else None,
               sold_by_site_region=sold_by_site_region,
               disc_payback=payback, peak_funding=peak, sold_by_region=sold_by_region, lines=lines,
               unit_npv=unit_npv, capex_real={k: v["total"] for k, v in caps.items()},
               capex_modules=caps)
    return out


def irr(flows: list[float]) -> float | None:
    def npv_at(r):
        return sum(f / (1 + r) ** (k + 1) for k, f in enumerate(flows))
    lo, hi = -0.9, 1.5
    flo, fhi = npv_at(lo), npv_at(hi)
    if flo * fhi > 0:
        return None
    for _ in range(200):
        mid = (lo + hi) / 2
        fm = npv_at(mid)
        if flo * fm <= 0:
            hi, fhi = mid, fm
        else:
            lo, flo = mid, fm
    return (lo + hi) / 2


def scaled_demand(p: dict, mult: float) -> dict:
    q = copy.deepcopy(p)
    q["demand"] = {r: {y: v * mult for y, v in ys.items()} for r, ys in p["demand"].items()}
    return q


def msp(p: dict, alt: dict) -> float | None:
    """Net price (USD/kg DHA) giving NPV = 0, volume allocation re-solved at each price."""
    def f(price):
        q = dict(p, price_dha=price)
        return run_alternative(q, alt)["npv"]
    lo, hi = 2.0, 150.0
    flo, fhi = f(lo), f(hi)
    if flo * fhi > 0:
        return None
    for _ in range(50):
        mid = (lo + hi) / 2
        fm = f(mid)
        if flo * fm <= 0:
            hi = mid
        else:
            lo, flo = mid, fm
    return (lo + hi) / 2


def breakeven_demand_multiplier(p: dict, alt: dict) -> float | None:
    def f(m):
        return run_alternative(scaled_demand(p, m), alt)["npv"]
    lo, hi = 0.0, 6.0
    flo, fhi = f(lo), f(hi)
    if flo * fhi > 0:
        return None
    for _ in range(40):
        mid = (lo + hi) / 2
        fm = f(mid)
        if flo * fm <= 0:
            hi = mid
        else:
            lo, flo = mid, fm
    return (lo + hi) / 2


def npv_flows(flows: list[float], rate: float) -> float:
    return sum(f / (1 + rate) ** (k + 1) for k, f in enumerate(flows))
