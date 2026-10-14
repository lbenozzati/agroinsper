"""CLI: python -m src run [--mc-sims N] [--no-charts] [--no-cockpit] [--out DIR]."""

import argparse
from pathlib import Path

from .pipeline import run


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m src", description="Corbion DHA capacity model v3")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="run the full pipeline")
    r.add_argument("--mc-sims", type=int, default=None)
    r.add_argument("--no-charts", action="store_true")
    r.add_argument("--no-cockpit", action="store_true")
    r.add_argument("--out", type=Path, default=None)
    args = ap.parse_args(argv)
    res = run(out_dir=args.out, mc_sims=args.mc_sims, charts=not args.no_charts, cockpit=not args.no_cockpit)
    print(f"outputs written to {res['out']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
