"""CLI: python -m src run [--mc-sims N] [--no-charts] [--skip-upstream-tests]."""

import argparse

from .pipeline import run


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m src", description="Integrated DHA capacity x market strategy")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--mc-sims", type=int, default=None)
    r.add_argument("--no-charts", action="store_true")
    r.add_argument("--skip-upstream-tests", action="store_true")
    a = ap.parse_args(argv)
    res = run(mc_sims=a.mc_sims, run_upstream_tests=not a.skip_upstream_tests, charts=not a.no_charts)
    print(f"outputs written to {res['out']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
