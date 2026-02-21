"""
Bracket visualization — writes a formatted ASCII text bracket to a .txt file
and a PNG bracket image using matplotlib.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from datetime import date

W = 26  # column width for team name field


def _fmt(team, seed=None) -> str:
    s = seed if seed is not None else team.seed
    return f"({s:>2}) {team.name}"


def _game_line(winner, loser, seed_lookup) -> str:
    w_seed = seed_lookup.get(winner.name, winner.seed)
    l_seed = seed_lookup.get(loser.name,  loser.seed)
    w = _fmt(winner, w_seed)
    l = _fmt(loser,  l_seed)
    upset = w_seed >= l_seed + 2
    sep = " UPSETS " if upset else "  def.  "
    suffix = "!!!!!" if upset else ""
    return f"  {w:<{W}}{sep}{l}{suffix}"


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


# ---------------------------------------------------------------------------
# PNG bracket
# ---------------------------------------------------------------------------

# Layout constants
_TW   = 2.6   # team box width
_TH   = 0.32  # team box height
_GAP  = 0.10  # gap between paired teams in R64
_RCOL = 3.0   # horizontal space per round column

_COLOR_WIN  = "#fff9c4"
_COLOR_LOSE = "#f0f0f0"
_COLOR_LINE = "#aaaaaa"
_REGION_COLORS = {
    "east":    "#1a73e8",
    "west":    "#e84b1a",
    "south":   "#1aad52",
    "midwest": "#9c1ae8",
}


def _png_label(team, seed_lookup) -> str:
    s = seed_lookup.get(team.name, team.seed)
    return f"({s}) {team.name}"


def _png_box(ax, x, y, text, bg, bold=False, fontsize=6.5):
    rect = FancyBboxPatch((x, y), _TW, _TH,
                          boxstyle="round,pad=0.02",
                          linewidth=0.5, edgecolor="#999999",
                          facecolor=bg, zorder=3)
    ax.add_patch(rect)
    ax.text(x + _TW / 2, y + _TH / 2, text,
            ha="center", va="center", fontsize=fontsize,
            weight="bold" if bold else "normal", zorder=4, clip_on=True)


def _hline(ax, x0, x1, y):
    ax.plot([x0, x1], [y, y], color=_COLOR_LINE, lw=0.6, zorder=2)


def _vline(ax, x, y0, y1):
    ax.plot([x, x], [y0, y1], color=_COLOR_LINE, lw=0.6, zorder=2)


def _region_game_ys(n_games, y_top):
    """Return list of y-top positions for each game pair, evenly spaced."""
    pair_h = 2 * _TH + _GAP
    spacing = pair_h + 0.35
    return [y_top - i * spacing for i in range(n_games)]


def _draw_region_left(ax, region, rounds, seed_lookup, x0, y_top):
    """Draw a region whose rounds advance left→right (east, midwest)."""
    color = _REGION_COLORS.get(region, "#333333")
    ax.text(x0, y_top + 0.15, region.upper(),
            fontsize=8, weight="bold", color=color)

    # Compute game y-top positions for each round
    r0_ys = _region_game_ys(8, y_top)

    round_ys = [r0_ys]
    for r in range(1, 4):
        prev = round_ys[r - 1]
        # Winner box midpoint between the two feeding game centers
        pair_h = 2 * _TH + _GAP
        next_ys = []
        for g in range(len(prev) // 2):
            y1_center = prev[g * 2] - _TH / 2     # center of game g*2
            y2_center = prev[g * 2 + 1] - _TH / 2 # center of game g*2+1
            next_ys.append((y1_center + y2_center) / 2 - _TH / 2)
        round_ys.append(next_ys)

    # Round 0: draw both teams per game
    x = x0
    for g_idx, (w, l) in enumerate(rounds[0]):
        yt = round_ys[0][g_idx]
        _png_box(ax, x, yt,        _png_label(w, seed_lookup), _COLOR_WIN,  bold=True)
        _png_box(ax, x, yt - _TH - _GAP, _png_label(l, seed_lookup), _COLOR_LOSE)
        # Bracket stub: right edge of winner → midpoint
        mid_x = x + _TW + (_RCOL - _TW) / 2
        w_cy = yt + _TH / 2
        _hline(ax, x + _TW, mid_x, w_cy)

    # Rounds 1-3: winner box + connectors
    for r in range(1, 4):
        x = x0 + r * _RCOL
        for g_idx, (w, l) in enumerate(rounds[r]):
            yt = round_ys[r][g_idx]
            cy = yt + _TH / 2
            _png_box(ax, x, yt, _png_label(w, seed_lookup), _COLOR_WIN, bold=True)

            # Connectors from the two feeding games
            prev_ys = round_ys[r - 1]
            x_prev = x0 + (r - 1) * _RCOL
            mid_x = x_prev + _TW + (_RCOL - _TW) / 2

            y_feed1 = prev_ys[g_idx * 2] + _TH / 2
            y_feed2 = prev_ys[g_idx * 2 + 1] + _TH / 2

            # Vertical bar connecting the two feed midpoints
            _vline(ax, mid_x, min(y_feed1, y_feed2), max(y_feed1, y_feed2))
            # Horizontal to this box
            _hline(ax, mid_x, x, cy)

            # Stub right of this box for next round (if not E8)
            if r < 3:
                next_mid_x = x + _TW + (_RCOL - _TW) / 2
                _hline(ax, x + _TW, next_mid_x, cy)

    return round_ys


def _draw_region_right(ax, region, rounds, seed_lookup, x0, y_top):
    """Draw a region whose rounds advance right→left (west, south)."""
    color = _REGION_COLORS.get(region, "#333333")
    ax.text(x0 + _TW, y_top + 0.15, region.upper(),
            fontsize=8, weight="bold", color=color, ha="right")

    r0_ys = _region_game_ys(8, y_top)

    round_ys = [r0_ys]
    for r in range(1, 4):
        prev = round_ys[r - 1]
        next_ys = []
        for g in range(len(prev) // 2):
            y1_center = prev[g * 2] - _TH / 2
            y2_center = prev[g * 2 + 1] - _TH / 2
            next_ys.append((y1_center + y2_center) / 2 - _TH / 2)
        round_ys.append(next_ys)

    # Round 0
    x = x0
    for g_idx, (w, l) in enumerate(rounds[0]):
        yt = round_ys[0][g_idx]
        _png_box(ax, x, yt,               _png_label(w, seed_lookup), _COLOR_WIN,  bold=True)
        _png_box(ax, x, yt - _TH - _GAP,  _png_label(l, seed_lookup), _COLOR_LOSE)
        mid_x = x - (_RCOL - _TW) / 2
        w_cy = yt + _TH / 2
        _hline(ax, mid_x, x, w_cy)

    # Rounds 1-3
    for r in range(1, 4):
        x = x0 - r * _RCOL
        for g_idx, (w, l) in enumerate(rounds[r]):
            yt = round_ys[r][g_idx]
            cy = yt + _TH / 2
            _png_box(ax, x, yt, _png_label(w, seed_lookup), _COLOR_WIN, bold=True)

            prev_ys = round_ys[r - 1]
            x_prev = x0 - (r - 1) * _RCOL
            mid_x = x_prev - (_RCOL - _TW) / 2

            y_feed1 = prev_ys[g_idx * 2] + _TH / 2
            y_feed2 = prev_ys[g_idx * 2 + 1] + _TH / 2

            _vline(ax, mid_x, min(y_feed1, y_feed2), max(y_feed1, y_feed2))
            _hline(ax, x + _TW, mid_x, cy)

            if r < 3:
                next_mid_x = x - (_RCOL - _TW) / 2
                _hline(ax, next_mid_x, x, cy)

    return round_ys


def draw_bracket_png(result: dict, out_path: str | None = None) -> str:
    """Draw a PNG bracket image. Returns the path."""
    if out_path is None:
        out_path = f"bracket_{date.today().isoformat()}.png"

    # Seed lookup from R64
    seed_lookup: dict[str, int] = {}
    for reg, rounds in result["region_brackets"].items():
        for w, l in rounds[0]:
            seed_lookup[w.name] = w.seed
            seed_lookup[l.name] = l.seed

    # Figure size: 4 rounds per side + center 2 cols
    total_cols = 4 + 4 + 1.5   # left 4, right 4, center
    fig_w = total_cols * _RCOL + 0.5
    fig_h = 22.0

    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    ax.set_xlim(0, fig_w)
    ax.set_ylim(0, fig_h)
    ax.axis("off")
    ax.set_facecolor("#f8f8f8")
    fig.patch.set_facecolor("#f8f8f8")

    ax.text(fig_w / 2, fig_h - 0.2,
            "NCAA March Madness Tournament Bracket",
            ha="center", va="top", fontsize=13, weight="bold", color="#222222")

    rb = result["region_brackets"]

    half_h = fig_h / 2
    top_y  = fig_h - 1.2
    mid_y  = half_h - 0.3

    left_x  = 0.3
    right_x = fig_w - 0.3 - _TW

    # Left side: east (top), midwest (bottom)
    east_ys    = _draw_region_left(ax, "east",    rb["east"],    seed_lookup, left_x,  top_y)
    midwest_ys = _draw_region_left(ax, "midwest", rb["midwest"], seed_lookup, left_x,  mid_y)

    # Right side: west (top), south (bottom)
    west_ys  = _draw_region_right(ax, "west",  rb["west"],  seed_lookup, right_x, top_y)
    south_ys = _draw_region_right(ax, "south", rb["south"], seed_lookup, right_x, mid_y)

    # Center: Final Four + Championship
    cx = fig_w / 2 - _TW / 2

    f4 = result["f4_results"]
    champ, runner_up = result["champ_result"]

    # F4 semi 1 (east/west winner) → top, semi 2 (south/midwest) → bottom
    # Place them symmetrically around center
    y_f4_top = fig_h * 0.56
    y_f4_bot = fig_h * 0.40
    y_champ  = (y_f4_top + y_f4_bot) / 2 - _TH / 2

    ax.text(cx + _TW / 2, y_f4_top + _TH + 0.25, "FINAL FOUR",
            ha="center", fontsize=9, weight="bold", color="#d4a017")

    for idx, (w, l) in enumerate(f4):
        y = y_f4_top if idx == 0 else y_f4_bot
        _png_box(ax, cx, y, _png_label(w, seed_lookup), _COLOR_WIN, bold=True, fontsize=7.5)

    # Connector between the two F4 winners → championship
    mid_f4_x = cx + _TW + 0.3
    _hline(ax, cx + _TW, mid_f4_x, y_f4_top + _TH / 2)
    _hline(ax, cx + _TW, mid_f4_x, y_f4_bot + _TH / 2)
    _vline(ax, mid_f4_x, y_f4_bot + _TH / 2, y_f4_top + _TH / 2)

    ax.text(cx + _TW / 2, y_champ + _TH + 0.15, "CHAMPIONSHIP",
            ha="center", fontsize=8, weight="bold", color="#8B6914")
    _png_box(ax, cx, y_champ, _png_label(champ, seed_lookup),
             "#FFD700", bold=True, fontsize=8)
    ax.text(cx + _TW / 2, y_champ - 0.28, "CHAMPION",
            ha="center", fontsize=7, color="#8B6914", weight="bold")

    # Round labels
    round_labels_l = ["R64", "R32", "S16", "E8"]
    round_labels_r = ["E8",  "S16", "R32", "R64"]
    label_y = fig_h - 0.75
    for i, lbl in enumerate(round_labels_l):
        ax.text(left_x + i * _RCOL + _TW / 2, label_y, lbl,
                ha="center", fontsize=7, color="#555555")
    for i, lbl in enumerate(round_labels_r):
        ax.text(right_x - i * _RCOL + _TW / 2, label_y, lbl,
                ha="center", fontsize=7, color="#555555")
    ax.text(cx + _TW / 2, label_y, "F4 / Champ",
            ha="center", fontsize=7, color="#555555")

    plt.tight_layout(pad=0.3)
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out_path
