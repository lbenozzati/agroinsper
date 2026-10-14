"""Run the rankings and write charts and memos."""

from __future__ import annotations

import json
import subprocess
from datetime import date

import pandas as pd

from . import charts as C
from . import plant as P

CRIT_SHORT_PLANT = {"production_economics": "Economia de\nprodução", "market_access": "Acesso a\nmercados",
                    "corbion_readiness": "Prontidão\nCorbion", "regulation_incentives": "Regulação e\nincentivos",
                    "strategic_risk": "Risco\nestratégico"}


def _commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=P.ROOT, text=True).strip()
    except Exception:
        return "n/a"


def run_plant(n_mc: int | None = None, charts: bool = True) -> dict:
    res = P.run(n_mc)
    tab = res["table"]
    model = res["model"]
    w = model.scenarios[model.base]
    if charts:
        C.setup()
        note = ("Score = triagem multicritério (0–10), não VPL. Cada país avaliado num site ao lado de uma usina de açúcar "
                "(EUA: moinho de milho/dextrose em Blair-NE). Fonte: plant_country_ranking.csv / plant_inputs_long.csv.")
        C.heatmap(tab, CRIT_SHORT_PLANT, w, P.OUT / "plant_heatmap.png",
                  "Melhor país para a nova unidade de DHA de microalgas",
                  f"Score por critério (0–10) e score final ponderado 30/20/15/15/20 · {len(tab)} países, {len(model.metrics)} métricas", note,
                  extra_cols={"Gate": tab.gate.map({"Pass": "ok", "Review": "rev.", "Fail": "falha"}),
                              "v2": tab.v2_rank.map(lambda x: "" if pd.isna(x) else f"{int(x)}º")})
        C.contributions(res["contributions"].div(1), {k: v.replace("\n", " ") for k, v in CRIT_SHORT_PLANT.items()},
                        list(tab.index), P.OUT / "plant_contributions.png",
                        "De onde vem o score de cada país",
                        "Contribuição de cada critério (score do critério × peso) para o score final", note)
        C.rank_probability(tab, P.OUT / "plant_rank_probability.png", "Quão robusto é o 1º lugar?",
                           "Probabilidade de 1º lugar com pesos incertos (Dirichlet em torno de 30/20/15/15/20) e com "
                           "dados incertos (ruído por confiança da fonte)",
                           "Probabilidades condicionais às distribuições assumidas; não são previsões calibradas. "
                           "Fonte: plant_country_ranking.csv.")
        pts = {}
        d = res["data"]
        for c in tab.index:
            la = d[(d.country == c) & (d.metric_id == "ref_mill_lat")].raw_value
            lo = d[(d.country == c) & (d.metric_id == "ref_mill_lon")].raw_value
            if len(la) and len(lo):
                pts[c] = (float(lo.iloc[0]), float(la.iloc[0]))
        C.bubble_map(tab, P.OUT / "plant_map.png", "Melhores países para a nova unidade (score de triagem)",
                     "Bolha na usina de referência de cada país; área proporcional ao score; destaque = 1º lugar",
                     note, points=pts)
        tm = res["tm"].pivot(index="origin", columns="market", values="door_to_door_days")
        wts = res["weights"].sort_values(ascending=False)
        tm = tm[[c for c in wts.index if c in tm.columns]].loc[list(tab.index)]
        C.matrix(tm, P.OUT / "plant_transit_days.png", "Dias porta a porta da usina de referência a cada mercado",
                 "Rota marítima por pontos de passagem (canais, estreitos, cabos) a 15 nós + escalas + trechos terrestres; "
                 "colunas ordenadas pelo peso na demanda de DHA 2030",
                 "Pesos dos mercados = SAM 2030 do estudo de mercado: " +
                 ", ".join(f"{C.PT.get(k, k)} {v:.0%}" for k, v in wts.items() if v >= 0.02) +
                 ". Fonte: plant_transit_matrix.csv.", fmt_d=0, reverse=True)
    from . import reports as R
    R.plant_memo(res)
    manifest = dict(run_date=str(date.today()), commit=_commit(), mc_sims=n_mc or res["cfg"]["mc_sims"],
                    countries=list(tab.index), metrics=len(model.metrics))
    (P.OUT / "run_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    return res


def run_market(n_mc: int | None = None, charts: bool = True):
    from . import market as M
    return M.run_all(n_mc, charts)
