#!/usr/bin/env python3
"""
Entry point for the March Madness ELO simulator.

Usage:
  python run.py --teams sample_teams.csv              # single sim + bracket image
  python run.py --teams sample_teams.csv --trials 10000  # also generate probs CSV
  python run.py --teams sample_teams.csv --trials 10000 --out-image bracket.png --out-probs probs.csv
"""
import argparse
import sys
from simulator import load_teams, run_single, run_trials, compute_probabilities, save_probabilities
from visualize import draw_bracket


def main():
    parser = argparse.ArgumentParser(description="March Madness ELO Tournament Simulator")
    parser.add_argument("--teams",     required=True, help="Path to teams CSV file")
    parser.add_argument("--trials",    type=int,       default=0,
                        help="Number of Monte Carlo trials (0 = skip, just do single sim)")
    parser.add_argument("--out-image", default=None,   help="Path for bracket output (TXT)")
    parser.add_argument("--out-probs", default=None,   help="Path for probabilities CSV")
    parser.add_argument("--seed",      type=int,       default=None,
                        help="Random seed for reproducibility")
    args = parser.parse_args()

    import random
    if args.seed is not None:
        random.seed(args.seed)

    print(f"Loading teams from {args.teams}...")
    teams = load_teams(args.teams)
    print(f"  {len(teams)} teams loaded across "
          f"{len(set(t.region for t in teams))} regions.")

    # --- Single simulation ---
    print("\nRunning single simulation...")
    result = run_single(teams)

    print("\n  Final Four:")
    for w, l in result["f4_results"]:
        print(f"    ({w.seed}) {w.name} def. ({l.seed}) {l.name}")
    champ, runner_up = result["champ_result"]
    print(f"\n  Championship:")
    print(f"    ({champ.seed}) {champ.name} def. ({runner_up.seed}) {runner_up.name}")
    print(f"\n  Champion: ({champ.seed}) {champ.name}")

    img_path = draw_bracket(result, args.out_image)
    print(f"  Bracket saved → {img_path}")

    # --- Monte Carlo ---
    if args.trials > 0:
        print(f"\nRunning {args.trials:,} trials...")
        all_results = run_trials(teams, args.trials)
        rows = compute_probabilities(teams, all_results)
        csv_path = save_probabilities(rows, args.out_probs)
        print(f"  Probabilities saved → {csv_path}")
        print("\nTop 10 championship probabilities:")
        print(f"  {'Team':<25} {'Seed':<6} {'Region':<10} {'Champ%':>7}")
        print("  " + "-" * 52)
        for row in rows[:10]:
            print(f"  {row['team']:<25} {row['seed']:<6} {row['region']:<10} "
                  f"{row['prb_win_champ']*100:>6.1f}%")


if __name__ == "__main__":
    main()
