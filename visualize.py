"""
Bracket visualization — draws a full 64-team bracket image using matplotlib.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
from datetime import date

# Layout constants
TEAM_H    = 0.4   # height of one team box
TEAM_W    = 2.8   # width of one team box
GAP       = 0.15  # gap between paired teams
ROUND_GAP = 3.4   # horizontal space per round column
REG_VGAP  = 2.0   # vertical gap between regions on same side

COLORS = {
    "East":    "#1a73e8",
    "West":    "#e84b1a",
    "South":   "#1aad52",
    "Midwest": "#9c1ae8",
    "F4":      "#d4a017",
    "Champ":   "#b8860b",
    "winner":  "#fff9c4",
    "loser":   "#f5f5f5",
    "box_bg":  "#ffffff",
    "line":    "#aaaaaa",
}

# Each region has 4 internal rounds (R64→R32→S16→E8 = rounds 0..3)
# Then F4 (round 4) and Champ (round 5) in the center.


def _team_label(team, seed=None) -> str:
    s = seed if seed is not None else team.seed
    return f"({s}) {team.name}"


def _draw_box(ax, x, y, text, color=COLORS["box_bg"], text_color="black",
              alpha=1.0, fontsize=7.5, bold=False):
    rect = FancyBboxPatch((x, y), TEAM_W, TEAM_H,
                          boxstyle="round,pad=0.03",
                          linewidth=0.6, edgecolor="#888888",
                          facecolor=color, alpha=alpha, zorder=3)
    ax.add_patch(rect)
    weight = "bold" if bold else "normal"
    ax.text(x + TEAM_W / 2, y + TEAM_H / 2, text,
            ha="center", va="center", fontsize=fontsize,
            color=text_color, weight=weight, zorder=4,
            clip_on=True)


def _draw_connector(ax, x_left, y_left, x_right, y_right):
    """Draw an L-shaped connector from right edge of left box to left edge of right box."""
    mid_x = (x_left + TEAM_W + x_right) / 2
    ax.plot([x_left + TEAM_W, mid_x], [y_left, y_left],
            color=COLORS["line"], lw=0.7, zorder=2)
    ax.plot([mid_x, mid_x], [y_left, y_right],
            color=COLORS["line"], lw=0.7, zorder=2)
    ax.plot([mid_x, x_right], [y_right, y_right],
            color=COLORS["line"], lw=0.7, zorder=2)


class BracketDrawer:
    """
    Lays out a 4-region bracket on a wide canvas.
    Left side (top→bottom): East, Midwest  (rounds go left→right toward center)
    Right side (top→bottom): West, South   (rounds go right→left toward center)
    Center: Final Four + Championship
    """

    def __init__(self, result: dict):
        self.result = result
        # Pre-build seed lookup from first-round games
        self._orig_seeds: dict[str, int] = {}
        for reg, rounds in result["region_brackets"].items():
            for w, l in rounds[0]:
                self._orig_seeds[w.name] = w.seed
                self._orig_seeds[l.name] = l.seed

    def _seed(self, team) -> int:
        return self._orig_seeds.get(team.name, team.seed)

    def draw(self, out_path: str | None = None) -> str:
        if out_path is None:
            out_path = f"bracket_{date.today().isoformat()}.png"

        fig_w = ROUND_GAP * 10 + 2   # 4 rounds each side + 2 center columns + margin
        fig_h = 30
        fig, ax = plt.subplots(figsize=(fig_w, fig_h))
        ax.set_xlim(0, fig_w)
        ax.set_ylim(0, fig_h)
        ax.axis("off")
        ax.set_facecolor("#f8f8f8")
        fig.patch.set_facecolor("#f8f8f8")

        ax.text(fig_w / 2, fig_h - 0.3,
                "NCAA March Madness Tournament Bracket",
                ha="center", va="top", fontsize=16, weight="bold", color="#222222")

        rb = self.result["region_brackets"]

        # --- Left side: East (top), Midwest (bottom) ---
        self._draw_region_left(ax, "East",    x_start=0.3,  y_top=fig_h - 1.5)
        self._draw_region_left(ax, "Midwest", x_start=0.3,  y_top=fig_h / 2 - 0.5)

        # --- Right side: West (top), South (bottom) ---
        right_start = fig_w - 0.3 - TEAM_W
        self._draw_region_right(ax, "West",  x_start=right_start, y_top=fig_h - 1.5)
        self._draw_region_right(ax, "South", x_start=right_start, y_top=fig_h / 2 - 0.5)

        # --- Final Four + Championship ---
        self._draw_center(ax, fig_w, fig_h)

        # Round labels (top)
        left_rounds  = ["R64", "R32", "S16", "E8"]
        right_rounds = ["E8", "S16", "R32", "R64"]
        for i, label in enumerate(left_rounds):
            ax.text(0.3 + i * ROUND_GAP + TEAM_W / 2, fig_h - 0.9,
                    label, ha="center", va="center", fontsize=8, color="#555555")
        for i, label in enumerate(right_rounds):
            ax.text(right_start - i * ROUND_GAP + TEAM_W / 2, fig_h - 0.9,
                    label, ha="center", va="center", fontsize=8, color="#555555")

        plt.tight_layout(pad=0.5)
        plt.savefig(out_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return out_path

    # ------------------------------------------------------------------
    # Region drawing helpers
    # ------------------------------------------------------------------

    def _draw_region_left(self, ax, region: str, x_start: float, y_top: float):
        rounds = self.result["region_brackets"][region]  # list of 4 round lists
        color = COLORS[region]
        ax.text(x_start, y_top + 0.1, region,
                fontsize=9, weight="bold", color=color)

        # Build slot positions for each round
        # Round 0 (R64): 8 games, 16 teams
        positions = self._left_round_positions(rounds, x_start, y_top - 0.3)
        self._render_left_rounds(ax, rounds, positions, x_start, color)

    def _draw_region_right(self, ax, region: str, x_start: float, y_top: float):
        rounds = self.result["region_brackets"][region]
        color = COLORS[region]
        ax.text(x_start + TEAM_W, y_top + 0.1, region,
                fontsize=9, weight="bold", color=color, ha="right")
        self._render_right_rounds(ax, rounds, x_start, y_top - 0.3, color)

    def _left_round_positions(self, rounds, x_start, y_top):
        """
        Returns list of lists of y-centers for each winner box per round.
        Round 0: 8 games → 8 winner y positions
        Round 1: 4 games → ...
        """
        # R64 slot y positions (top team of each pair)
        game_height = 2 * TEAM_H + GAP + 0.25  # space for one game pair
        positions = []

        # Round 0 y-tops for each game
        r0_ys = []
        for g in range(8):
            r0_ys.append(y_top - g * game_height)
        positions.append(r0_ys)

        # Subsequent rounds: winner sits midway between the two feeding games
        for r in range(1, 4):
            prev = positions[r - 1]
            ys = []
            for g in range(len(prev) // 2):
                y = (prev[g * 2] + prev[g * 2 + 1]) / 2
                ys.append(y)
            positions.append(ys)
        return positions

    def _render_left_rounds(self, ax, rounds, positions, x_start, color):
        # Draw all 4 rounds left→right
        all_teams_by_round = self._extract_round_teams_left(rounds)

        for r_idx in range(4):
            x = x_start + r_idx * ROUND_GAP
            games = rounds[r_idx]
            ys = positions[r_idx]

            if r_idx == 0:
                # Two teams per game slot
                for g_idx, (w, l) in enumerate(games):
                    y_top_game = ys[g_idx]
                    # top team
                    self._draw_team_box(ax, x, y_top_game, games[g_idx][0] if w == games[g_idx][0] else games[g_idx][1],
                                       games[g_idx][0], games[g_idx][1], winner=games[g_idx][0])
                    # bottom team
                    self._draw_team_box(ax, x, y_top_game - TEAM_H - GAP, games[g_idx][1] if w == games[g_idx][0] else games[g_idx][0],
                                       games[g_idx][0], games[g_idx][1], winner=games[g_idx][0])
                    # Winner box for next round drawn as part of that round
            else:
                for g_idx, (w, l) in enumerate(games):
                    y = ys[g_idx]
                    is_win = True
                    bg = COLORS["winner"]
                    label = _team_label(w, self._seed(w))
                    _draw_box(ax, x, y, label, color=bg, bold=True)

                    # connector from previous round
                    if r_idx > 0:
                        prev_ys = positions[r_idx - 1]
                        y_feed1 = prev_ys[g_idx * 2]
                        y_feed2 = prev_ys[g_idx * 2 + 1]
                        x_prev = x_start + (r_idx - 1) * ROUND_GAP
                        _draw_connector(ax, x_prev, y_feed1 if r_idx == 1 else y_feed1, x, y + TEAM_H / 2)

    def _draw_team_box(self, ax, x, y, team, team_a, team_b, winner):
        is_winner = (team.name == winner.name)
        bg = COLORS["winner"] if is_winner else COLORS["loser"]
        label = _team_label(team, self._seed(team))
        _draw_box(ax, x, y, label, color=bg, bold=is_winner)

    def _extract_round_teams_left(self, rounds):
        pass  # not needed for simplified render

    def _render_right_rounds(self, ax, rounds, x_start, y_top, color):
        positions = self._left_round_positions(rounds, x_start, y_top)
        for r_idx in range(4):
            # Mirror: round 0 is rightmost (x_start), round 3 is leftmost
            x = x_start - r_idx * ROUND_GAP
            games = rounds[r_idx]
            ys = positions[r_idx]

            if r_idx == 0:
                for g_idx, (w, l) in enumerate(games):
                    y_top_game = ys[g_idx]
                    self._draw_team_box(ax, x, y_top_game, games[g_idx][0], games[g_idx][0], games[g_idx][1], winner=w)
                    self._draw_team_box(ax, x, y_top_game - TEAM_H - GAP, games[g_idx][1], games[g_idx][0], games[g_idx][1], winner=w)
            else:
                for g_idx, (w, l) in enumerate(games):
                    y = ys[g_idx]
                    _draw_box(ax, x, y, _team_label(w, self._seed(w)), color=COLORS["winner"], bold=True)

    def _draw_center(self, ax, fig_w, fig_h):
        """Draw Final Four and Championship in the center."""
        cx = fig_w / 2 - TEAM_W / 2
        f4 = self.result["f4_results"]
        champ_w, champ_l = self.result["champ_result"]

        # F4 game 1 winner (top center)
        y1 = fig_h * 0.58
        y2 = fig_h * 0.40
        y_champ = (y1 + y2) / 2 + TEAM_H * 0.2

        ax.text(cx + TEAM_W / 2, y1 + TEAM_H + 0.3, "FINAL FOUR",
                ha="center", fontsize=10, weight="bold", color=COLORS["F4"])

        # Semifinal 1
        for idx, (w, l) in enumerate(f4):
            y = y1 if idx == 0 else y2
            _draw_box(ax, cx, y, _team_label(w, self._seed(w)),
                      color=COLORS["winner"], bold=True, fontsize=8.5)

        # Championship label
        ax.text(cx + TEAM_W / 2, y_champ + TEAM_H + 0.2, "CHAMPIONSHIP",
                ha="center", fontsize=9, weight="bold", color=COLORS["Champ"])

        # Champion box
        _draw_box(ax, cx, y_champ, _team_label(champ_w, self._seed(champ_w)),
                  color="#FFD700", bold=True, fontsize=9.5, text_color="#333333")

        # Trophy icon text
        ax.text(cx + TEAM_W / 2, y_champ - 0.5, "CHAMPION",
                ha="center", fontsize=8, color="#8B6914", weight="bold")


def draw_bracket(result: dict, out_path: str | None = None) -> str:
    """Main entry point. Returns path to saved image."""
    drawer = BracketDrawer(result)
    return drawer.draw(out_path)
