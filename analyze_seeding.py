#!/usr/bin/env python3
"""
Seeding analysis — identifies the most over- and underseeded teams in a bracket CSV.

For each seed (1-16), computes the average ELO across the 4 teams with that seed.
Each team's deviation = their ELO minus their seed's average ELO.
  Positive deviation → underseeded (ELO better than typical for that seed)
  Negative deviation → overseeded  (ELO worse than typical for that seed)

Usage:
  python analyze_seeding.py --teams teams_2.20.csv
  python analyze_seeding.py --teams teams_2.20.csv --top 5
"""
import argparse
import csv
from collections import defaultdict
from datetime import date


def load_seeded_teams(path: str) -> list[dict]:
    teams = []
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            try:
                seed = int(row["seed"].strip())
                elo  = float(row["elo"].strip())
                name = row["team"].strip()
            except (KeyError, ValueError):
                continue
            teams.append({"name": name, "seed": seed, "elo": elo})
    return teams


def analyze(teams: list[dict], top_n: int = 4) -> list[str]:
    """Run analysis and return lines of output."""
    by_seed = defaultdict(list)
    for t in teams:
        by_seed[t["seed"]].append(t["elo"])

    seed_avg = {s: sum(v) / len(v) for s, v in by_seed.items()}

    lines = []
    lines.append("Seed averages:")
    for s in sorted(seed_avg):
        lines.append(f"  Seed {s:2d}: {seed_avg[s]:.1f}  (n={len(by_seed[s])})")

    for t in teams:
        t["dev"] = t["elo"] - seed_avg[t["seed"]]

    ranked = sorted(teams, key=lambda t: t["dev"], reverse=True)

    header = f"  {'Team':<30} {'Seed':>4}  {'ELO':>7}  {'SeedAvg':>7}  {'Delta':>7}"
    bar    = "  " + "-" * 62

    lines.append(f"\nTop {top_n} UNDERSEEDED (ELO well above seed average):")
    lines.append(header)
    lines.append(bar)
    for t in ranked[:top_n]:
        lines.append(f"  {t['name']:<30} {t['seed']:>4}  {t['elo']:>7.1f}  "
                     f"{seed_avg[t['seed']]:>7.1f}  {t['dev']:>+7.1f}")

    lines.append(f"\nTop {top_n} OVERSEEDED (ELO well below seed average):")
    lines.append(header)
    lines.append(bar)
    for t in ranked[-top_n:][::-1]:
        lines.append(f"  {t['name']:<30} {t['seed']:>4}  {t['elo']:>7.1f}  "
                     f"{seed_avg[t['seed']]:>7.1f}  {t['dev']:>+7.1f}")

    return lines


def main():
    parser = argparse.ArgumentParser(description="Seeding analysis for March Madness bracket CSV")
    parser.add_argument("--teams", required=True, help="Path to teams CSV file")
    parser.add_argument("--top",   type=int, default=4,
                        help="Number of over/underseeded teams to show (default: 4)")
    args = parser.parse_args()

    teams = load_seeded_teams(args.teams)
    header = f"Loaded {len(teams)} seeded teams from {args.teams}\n"
    print(header)
    lines = analyze(teams, args.top)
    for line in lines:
        print(line)

    out_path = f"seeding_analysis_{date.today().isoformat()}.txt"
    with open(out_path, "w") as f:
        f.write(header + "\n")
        f.write("\n".join(lines) + "\n")
    print(f"\nSaved → {out_path}")


if __name__ == "__main__":
    main()
