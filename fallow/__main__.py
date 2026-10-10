"""Command line: python -m fallow fetch | report [--reuse-grid] | plan [--fresh] [--json] [--budget 0.15] | site"""
import json
import sys

from . import NINE_FIELDS, data, plan, report


def main(argv):
    cmd = argv[1] if len(argv) > 1 else "report"
    if cmd == "fetch":
        data.refresh(NINE_FIELDS)
    elif cmd == "report":
        report.show(report.build(reuse_grid="--reuse-grid" in argv))
    elif cmd == "plan":
        # python -m fallow plan [--fresh] [--json] [--budget 0.15]
        budget = float(argv[argv.index("--budget") + 1]) if "--budget" in argv else 0.15
        p = plan.current(swing_budget=budget, refresh="--fresh" in argv)
        if "--json" in argv:
            print(json.dumps(p, indent=1))
        else:
            print(f"Week of {p['week_of']}, swing budget {budget:.0%}")
            for h in p["hold"]:
                print(f"  {h['symbol']:10} {h['weight']*100:5.1f}%   rising over {h['trend']} of 4")
            print(f"  {'USDT':10} {p['usdt']*100:5.1f}%")
    elif cmd == "site":
        report.publish()
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
