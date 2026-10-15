import argparse

from . import pipeline

ap = argparse.ArgumentParser(description="Country rankings for Corbion AlgaPrime DHA")
ap.add_argument("what", choices=["plant", "market", "all", "rev2026"], nargs="?", default="all",
                help="plant/market = rankings congelados de 14/10/2026; rev2026 = revisão factual de 15/10/2026")
ap.add_argument("--mc-sims", type=int, default=None)
ap.add_argument("--no-charts", action="store_true")
a = ap.parse_args()
if a.what in ("plant", "all"):
    pipeline.run_plant(a.mc_sims, charts=not a.no_charts)
if a.what in ("market", "all"):
    pipeline.run_market(a.mc_sims, charts=not a.no_charts)
if a.what == "rev2026":
    from .rev2026 import pipeline as rev
    rev.run(a.mc_sims, charts=not a.no_charts)
