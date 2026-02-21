"""
Bracket visualization — writes a formatted ASCII text bracket to a .txt file.
"""
from datetime import date

W = 26  # column width for team name field


def _fmt(team, seed=None) -> str:
    s = seed if seed is not None else team.seed
    return f"({s:>2}) {team.name}"


def _game_line(winner, loser, seed_lookup) -> str:
    w = _fmt(winner, seed_lookup.get(winner.name, winner.seed))
    l = _fmt(loser,  seed_lookup.get(loser.name,  loser.seed))
    return f"  {w:<{W}}  def.  {l}"


def _region_block(region: str, rounds: list, seed_lookup: dict) -> list[str]:
    """Return lines for one region's rounds (R64 through E8)."""
    round_labels = ["ROUND OF 64", "ROUND OF 32", "SWEET 16   ", "ELITE 8    "]
    lines = []
    bar = "─" * 58

    header = f" {region.upper()} REGION "
    lines.append("")
    lines.append(f"{'═' * 20}  {header}  {'═' * 20}")

    for r_idx, games in enumerate(rounds):
        lines.append("")
        lines.append(f"  {round_labels[r_idx]}")
        lines.append(f"  {bar}")
        for winner, loser in games:
            lines.append(_game_line(winner, loser, seed_lookup))

    # Region champion
    final_winner = rounds[-1][0][0]
    lines.append("")
    lines.append(f"  ★  {region.upper()} CHAMPION: {_fmt(final_winner, seed_lookup.get(final_winner.name, final_winner.seed))}")
    return lines


def draw_bracket(result: dict, out_path: str | None = None) -> str:
    """Write ASCII bracket to a .txt file. Returns the path."""
    if out_path is None:
        out_path = f"bracket_{date.today().isoformat()}.txt"

    # Build seed lookup from R64 games (before ELO mutates seed display)
    seed_lookup: dict[str, int] = {}
    for reg, rounds in result["region_brackets"].items():
        for winner, loser in rounds[0]:
            seed_lookup[winner.name] = winner.seed
            seed_lookup[loser.name]  = loser.seed

    lines = []
    border = "═" * 62

    lines.append(border)
    lines.append(f"{'NCAA MARCH MADNESS TOURNAMENT BRACKET':^62}")
    lines.append(f"{'Simulated Result':^62}")
    lines.append(border)

    # Four regions
    region_order = ["east", "west", "south", "midwest"]
    for reg in region_order:
        if reg in result["region_brackets"]:
            lines += _region_block(reg, result["region_brackets"][reg], seed_lookup)

    # Final Four
    lines.append("")
    lines.append("")
    lines.append(f"{'═' * 22}  FINAL FOUR  {'═' * 22}")
    lines.append("")
    lines.append(f"  {'─' * 58}")
    for winner, loser in result["f4_results"]:
        lines.append(_game_line(winner, loser, seed_lookup))

    # Championship
    champ, runner_up = result["champ_result"]
    lines.append("")
    lines.append(f"{'═' * 22}  CHAMPIONSHIP  {'═' * 19}")
    lines.append("")
    lines.append(f"  {'─' * 58}")
    lines.append(_game_line(champ, runner_up, seed_lookup))
    lines.append("")
    lines.append(f"  🏆  CHAMPION: {_fmt(champ, seed_lookup.get(champ.name, champ.seed))}")
    lines.append("")
    lines.append(border)

    text = "\n".join(lines)
    with open(out_path, "w") as f:
        f.write(text)

    return out_path
