"""
March Madness ELO Simulator
"""
import csv
import random
import copy
from datetime import date
from dataclasses import dataclass, field
from typing import Optional

K = 20  # ELO K-factor for tournament games

# Standard bracket seed matchups within a region (1-indexed seeds)
SEED_MATCHUPS = [(1, 16), (8, 9), (5, 12), (4, 13), (6, 11), (3, 14), (7, 10), (2, 15)]

# Round names by round index (0=R64, 1=R32, 2=S16, 3=E8, 4=F4, 5=Champ)
ROUND_NAMES = ["Round of 64", "Round of 32", "Sweet 16", "Elite 8", "Final Four", "Championship"]
ROUND_KEYS  = ["rd64", "rd32", "s16", "e8", "f4", "champ"]

REGIONS = ["east", "west", "south", "midwest"]
# Final Four pairings: east vs west, south vs midwest
SEMIFINAL_PAIRS = [("east", "west"), ("south", "midwest")]


@dataclass
class Team:
    name: str
    elo: float
    seed: int
    region: str


def load_teams(path: str) -> list[Team]:
    """
    Load teams from CSV. Rows missing team/elo/seed/region are silently skipped.
    Raises ValueError if the resulting field fails structural validation:
      - exactly 64 unique team names
      - exactly 4 regions
      - exactly 16 teams per region
      - seeds 1-16 present exactly once per region
    """
    teams = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Skip rows missing any required field or with blank values
            try:
                name   = row["team"].strip()
                elo    = row["elo"].strip()
                seed   = row["seed"].strip()
                region = row["region"].strip()
            except KeyError:
                continue
            if not name or not elo or not seed or not region:
                continue
            region = region.lower()
            try:
                teams.append(Team(
                    name=name,
                    elo=float(elo),
                    seed=int(seed),
                    region=region,
                ))
            except (ValueError, TypeError):
                continue

    _validate_teams(teams)
    return teams


def _validate_teams(teams: list[Team]) -> None:
    errors = []

    names = [t.name for t in teams]
    if len(names) != len(set(names)):
        dupes = [n for n in set(names) if names.count(n) > 1]
        errors.append(f"Duplicate team names: {dupes}")

    if len(teams) != 64:
        errors.append(f"Expected 64 teams, got {len(teams)}")

    by_region: dict[str, list[Team]] = {}
    for t in teams:
        by_region.setdefault(t.region, []).append(t)

    unknown = sorted(set(by_region.keys()) - set(REGIONS))
    if unknown:
        errors.append(f"Unknown region name(s): {unknown}. Must be one of: {REGIONS}")

    if len(by_region) != 4:
        errors.append(f"Expected 4 regions, got {len(by_region)}: {list(by_region.keys())}")

    for region, rteams in by_region.items():
        if len(rteams) != 16:
            errors.append(f"Region '{region}': expected 16 teams, got {len(rteams)}")
            continue
        seeds = sorted(t.seed for t in rteams)
        if seeds != list(range(1, 17)):
            missing = sorted(set(range(1, 17)) - set(seeds))
            extra   = sorted(set(seeds) - set(range(1, 17)))
            msg = f"Region '{region}': seeds must be 1-16 exactly once."
            if missing: msg += f" Missing: {missing}."
            if extra:   msg += f" Extra/invalid: {extra}."
            errors.append(msg)

    if errors:
        raise ValueError("Invalid team file:\n  " + "\n  ".join(errors))


def win_prob(team_a: Team, team_b: Team) -> float:
    """P(team_a beats team_b) using ELO logistic formula."""
    return 1.0 / (1.0 + 10 ** ((team_b.elo - team_a.elo) / 400.0))


def update_elo(winner: Team, loser: Team) -> None:
    """Update ELO scores in-place after a game."""
    p = win_prob(winner, loser)
    winner.elo += K * (1 - p)
    loser.elo  += K * (0 - (1 - p))


def simulate_game(team_a: Team, team_b: Team) -> tuple[Team, Team]:
    """Return (winner, loser). Updates ELO in-place."""
    p = win_prob(team_a, team_b)
    if random.random() < p:
        winner, loser = team_a, team_b
    else:
        winner, loser = team_b, team_a
    update_elo(winner, loser)
    return winner, loser


def build_region_bracket(region_teams: list[Team]) -> list[Team]:
    """
    Order 16 teams into the standard bracket slot order for a region.
    Slots are paired: [0v1, 2v3, 4v5, 6v7, 8v9, 10v11, 12v13, 14v15]
    which map to matchups: 1v16, 8v9, 5v12, 4v13, 6v11, 3v14, 7v10, 2v15
    """
    by_seed = {t.seed: t for t in region_teams}
    ordered = []
    for s1, s2 in SEED_MATCHUPS:
        ordered.append(by_seed[s1])
        ordered.append(by_seed[s2])
    return ordered


def simulate_region(region_teams: list[Team]) -> tuple[Team, list[list[tuple]]]:
    """
    Simulate a single region (4 rounds).
    Returns (region_winner, rounds_results)
    rounds_results[r] = list of (winner, loser) tuples for each game in that round.
    """
    bracket = build_region_bracket(region_teams)
    all_rounds = []

    current = bracket
    while len(current) > 1:
        round_results = []
        next_round = []
        for i in range(0, len(current), 2):
            w, l = simulate_game(current[i], current[i+1])
            round_results.append((w, l))
            next_round.append(w)
        all_rounds.append(round_results)
        current = next_round

    return current[0], all_rounds


def simulate_tournament(teams: list[Team]) -> dict:
    """
    Simulate a full 64-team tournament.
    Returns a dict with keys: region_results, final_four_results, championship_result
    Each *_results is a list of (winner, loser) per game.
    """
    regions: dict[str, list[Team]] = {r: [] for r in REGIONS}
    for t in teams:
        regions[t.region].append(t)

    region_winners = {}
    region_brackets = {}
    for reg in REGIONS:
        winner, rounds = simulate_region(regions[reg])
        region_winners[reg] = winner
        region_brackets[reg] = rounds  # 4 rounds per region

    # Final Four (2 semifinal games)
    f4_results = []
    f4_winners = []
    for reg_a, reg_b in SEMIFINAL_PAIRS:
        w, l = simulate_game(region_winners[reg_a], region_winners[reg_b])
        f4_results.append((w, l))
        f4_winners.append(w)

    # Championship
    champ, runner_up = simulate_game(f4_winners[0], f4_winners[1])
    champ_result = (champ, runner_up)

    return {
        "region_brackets": region_brackets,   # {region: [round0_games, round1_games, ...]}
        "region_winners": region_winners,
        "f4_results": f4_results,
        "champ_result": champ_result,
        "champion": champ,
    }


def run_single(teams: list[Team]) -> dict:
    """Deep-copy teams so original ELOs are preserved, then simulate."""
    return simulate_tournament(copy.deepcopy(teams))


def run_trials(teams: list[Team], n: int = 10000) -> list[dict]:
    """Run n independent simulations. Returns list of result dicts."""
    return [run_single(teams) for _ in range(n)]


def compute_probabilities(teams: list[Team], results: list[dict]) -> list[dict]:
    """
    Given n simulation results, compute per-team win probabilities for each of the 6 rounds.
    Each column = P(team wins their game IN that round):
      prb_win_rd64  – won Round of 64 game
      prb_win_rd32  – won Round of 32 game
      prb_win_s16   – won Sweet 16 game
      prb_win_e8    – won Elite 8 game
      prb_win_f4    – won Final Four game
      prb_win_champ – won Championship game
    """
    n = len(results)
    # 6 slots: [rd64, rd32, s16, e8, f4, champ]
    counts = {t.name: [0] * 6 for t in teams}

    for result in results:
        rb = result["region_brackets"]
        for reg, rounds in rb.items():
            # rounds[0]=R64, rounds[1]=R32, rounds[2]=S16, rounds[3]=E8
            for r_idx, games in enumerate(rounds):
                for winner, loser in games:
                    if winner.name in counts:
                        counts[winner.name][r_idx] += 1

        # Final Four winners (index 4)
        for winner, loser in result["f4_results"]:
            if winner.name in counts:
                counts[winner.name][4] += 1

        # Championship winner (index 5)
        champ, runner_up = result["champ_result"]
        if champ.name in counts:
            counts[champ.name][5] += 1

    rows = []
    for t in teams:
        c = counts[t.name]
        rows.append({
            "team": t.name,
            "seed": t.seed,
            "region": t.region,
            "prb_win_rd64":  round(c[0] / n, 4),
            "prb_win_rd32":  round(c[1] / n, 4),
            "prb_win_s16":   round(c[2] / n, 4),
            "prb_win_e8":    round(c[3] / n, 4),
            "prb_win_f4":    round(c[4] / n, 4),
            "prb_win_champ": round(c[5] / n, 4),
        })
    rows.sort(key=lambda r: r["prb_win_champ"], reverse=True)
    return rows


def save_probabilities(rows: list[dict], path: str | None = None) -> str:
    if path is None:
        path = f"probs_{date.today().isoformat()}.csv"
    fieldnames = ["team", "seed", "region", "prb_win_rd64", "prb_win_rd32", "prb_win_s16",
                  "prb_win_e8", "prb_win_f4", "prb_win_champ"]
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    return path
