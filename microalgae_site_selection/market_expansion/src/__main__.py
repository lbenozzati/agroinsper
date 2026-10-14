"""CLI: python -m src run [--mc-sims N] [--no-charts] [--publish-v3]."""

import argparse

from .pipeline import run


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m src", description="Corbion DHA market expansion study")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--mc-sims", type=int, default=None)
    r.add_argument("--no-charts", action="store_true")
    r.add_argument("--publish-v3", action="store_true",
                   help="copy outputs/market_demand_scenarios.csv into ../v3/data/raw (feeds the site study)")
    a = ap.parse_args(argv)
    res = run(mc_sims=a.mc_sims, charts=not a.no_charts, publish_v3=a.publish_v3)
    print(f"outputs written to {res['out']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
