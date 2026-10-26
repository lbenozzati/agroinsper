"""Focused tests for the material rules of the 2026-10-15 revision."""

import math

import pandas as pd
import pytest

from src.rev2026 import interval as I
from src.rev2026 import markets as MK
from src.rev2026 import migration as MG
from src.rev2026 import sites as ST
from src.rev2026.common import DATA, load_config

CFG = load_config()


@pytest.fixture(scope="module")
def site():
    return ST.run(CFG)


@pytest.fixture(scope="module")
def mkt():
    return MK.run(CFG)


def test_weights_sum_to_one():
    for sec in ("site", "market"):
        assert math.isclose(sum(v["weight"] for v in CFG[sec]["criteria"].values()), 1.0)
        I.validate_specs(I.specs_from(CFG[sec]["metrics"]), CFG[sec]["criteria"])
        for w in CFG[sec]["weight_sets"].values():
            assert abs(sum(w.values()) - 1) < 1e-3


def test_unknown_is_interval_not_zero_or_five():
    specs = {"a": I.Spec("a", "c", 0.5, 0, 10), "b": I.Spec("b", "c", 0.5, 0, 10)}
    cells = pd.DataFrame([{"entity": "X", "metric_id": "a", "status": "OBSERVED", "value": 8},
                          {"entity": "X", "metric_id": "b", "status": "UNKNOWN", "value": None}])
    t = I.aggregate(I.cell_scores(cells, specs), specs, {"c": 1.0})
    assert math.isclose(t.at["X", "floor"], 4.0) and math.isclose(t.at["X", "ceiling"], 9.0)
    assert math.isclose(t.at["X", "unknown_weight"], 0.5)


def test_assumption_never_scores():
    specs = {"a": I.Spec("a", "c", 1.0, 0, 10)}
    cells = pd.DataFrame([{"entity": "X", "metric_id": "a", "status": "ASSUMPTION", "value": 10}])
    t = I.aggregate(I.cell_scores(cells, specs), specs, {"c": 1.0})
    assert t.at["X", "floor"] == 0.0 and t.at["X", "ceiling"] == 10.0


def test_component_weight_moves_to_known_parent():
    specs = {"opex": I.Spec("opex", "e", 0.5, 0, 10), "sugar": I.Spec("sugar", "e", 0.5, 0, 10,
                                                                        component_of="opex")}
    cells = pd.DataFrame([{"entity": "X", "metric_id": "opex", "status": "OBSERVED", "value": 6},
                          {"entity": "X", "metric_id": "sugar", "status": "OBSERVED", "value": 10}])
    t = I.aggregate(I.cell_scores(cells, specs), specs, {"e": 1.0})
    assert math.isclose(t.at["X", "floor"], 6.0)   # sugar no longer double counted


def test_tipping_matches_bruteforce(site):
    t, w = site["table"], site["crit_w"]
    for _, r in site["tipping"].dropna().head(5).iterrows():
        x = r.tipping_weight
        c = r.criterion
        rest = 1 - w[c]
        ww = {k: (x if k == c else w[k] * (1 - x) / rest) for k in w}
        tt = I.reweight(t, ww)
        assert abs(tt.at[r.leader_on_floor, r.basis] - tt.at[r.challenger, r.basis]) < 0.02


def test_regulation_is_gate_not_score():
    assert not any(k.startswith("ri_") for k in CFG["site"]["metrics"])
    g = pd.read_csv(DATA / "product_regulatory_matrix.csv")
    assert set(g.status) <= {"pass", "review", "unknown", "fail"}
    # printed licence date alone must not produce a fail
    assert g.loc[g.gate_id == "G01", "status"].iloc[0] == "review"


def test_no_documented_current_purchase_from_historical():
    acc = pd.read_csv(DATA / "customer_factory_matrix.csv")
    assert not (acc.evidence_stage == "current_purchase").any()
    assert set(acc.evidence_stage) <= set(CFG["market"]["evidence_stage_score"]) | {"unknown"}


def test_lactic_acid_is_not_dha_asset(site):
    ev = site["cells"].set_index(["entity", "metric_id"])
    assert ev.loc[("TH_RYG", "ex_dha_asset_operating"), "value"] == 0
    assert ev.loc[("TH_RYG", "ex_dha_asset_operating"), "absence_type"] == "documented_no"


def test_site_access_does_not_use_market_ranking_weights():
    dw = CFG["site"]["destination_weights"]
    for n, d in dw.items():
        assert math.isclose(sum(d.values()), 1.0)
    assert math.isclose(sum(CFG["site"]["niche_weights"].values()), 1.0)


def test_judgment_share_sites_within_budget(site):
    assert site["table"].judgment_weight.max() <= CFG["judgment_budget"]


def test_unknown_competitor_gets_no_bonus(mkt):
    # concorrente não encontrado = faixa no componente A (nunca a nota máxima garantida no piso)
    import pandas as pd
    from src.plant import RAW
    d = pd.read_csv(RAW / "market_rubric_components.csv")
    a = d[(d.rubric == "competicao") & (d.component == "A") & d.evidence.str.contains("não encontrado")]
    assert len(a) and (a.lo.astype(float) < a.hi.astype(float)).all()
    ev = mkt["evidence"]
    r = ev[ev.metric_id == "fc_competitive_rubric"]
    assert (r.score_lo <= r.score_hi).all() and (r.score_hi < 10).all()


def test_rank_ranges_bracket_floor_rank(site, mkt):
    tabs = [site["table"]] + [v["table"] for v in mkt["niches"].values()]
    for t in tabs:
        assert (t.rank_best <= t.rank_floor).all() and (t.rank_floor <= t.rank_worst).all()


def test_rubric_migration_covers_every_old_rubric(site, mkt):
    m = MG.rubric_migration(site, mkt)
    allowed = {"substituída por medida observada", "movida ao VPL", "movida para gate",
               "permanece julgamento explícito", "removida por dupla contagem"}
    assert set(m.status) <= allowed
    from src.rev2026.common import FROZEN
    n_old = len(pd.read_csv(FROZEN / "plant" / "plant_rubric_ratings_template.csv")) + \
        len(pd.read_csv(FROZEN / "market" / "market_rubric_ratings_template.csv"))
    assert len(m) == n_old


def test_sources_cited_exist():
    reg = set(pd.read_csv(DATA / "source_registry.csv").source_id)
    for f in ("site_cells.csv", "customer_factory_matrix.csv", "product_regulatory_matrix.csv"):
        for x in pd.read_csv(DATA / f).source_id.dropna():
            for s in str(x).split(";"):
                if s.startswith("R"):
                    assert s in reg, (f, s)


def test_economics_labelled_and_public_not_estimable():
    from src.rev2026 import economics as EC
    pub = EC.public_only(CFG)
    assert (pub.npv == "não estimável com dados públicos").all()
    h = EC.V3Handle(CFG["economics"])
    sc = CFG["economics"]["renewal_scenarios"]
    base = EC.metrics(h, h.params(sc["R2_renova_igual"]), "A1_ORI", extra=False)
    low = EC.metrics(h, h.params(sc["R1_renova_menor"]), "A1_ORI", extra=False)
    assert low["npv_musd"] < base["npv_musd"]            # lower renewal price/volume lowers NPV
    assert base["online_year"] == 2029                    # module after the 2027 debottleneck headroom
    assert base["utilisation_2035"] <= 1.0


def test_china_salmon_domestic_only():
    from src.rev2026 import markets as MK
    from src.rev2026.common import load_config
    c = MK.build_cells(load_config())
    r = c[(c.entity == "salmon|China") & (c.metric_id == "dm_dha_tech_t")].iloc[0]
    # só criação doméstica (~40-65 kt salmonídeos), nunca a importação de ~161 kt
    assert 250 < r.value < 500 and r.value_low < r.value < r.value_high
    assert set(c[c.entity == "salmon|China"].metric_id) == set(c[c.entity == "salmon|Norway"].metric_id)


def test_rubric_components_bounds():
    from src import market as M
    caps = {"canal": 10, "registro": 10, "competicao": 10}
    for n in ("salmon", "shrimp", "pet"):
        r = M.rubric_components(n, {})
        assert len(r) and (r.lo <= r.hi).all() and (r.lo >= 0).all()
        assert all(h <= caps[k] for k, h in zip(r.rubric, r.hi))
        assert set(r.rubric) == set(caps)
