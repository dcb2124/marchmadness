"""
Tests for the March Madness ELO simulator.
Run with: python -m pytest test_simulator.py -v
"""
import csv
import os
import random
import tempfile
import pytest
from simulator import (
    Team, load_teams, _validate_teams, win_prob, update_elo, simulate_game,
    build_region_bracket, simulate_region, simulate_tournament,
    run_single, run_trials, compute_probabilities, save_probabilities,
    SEED_MATCHUPS, REGIONS,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def make_teams(n_per_region=16) -> list[Team]:
    """Create a minimal 64-team field with sensible ELOs."""
    teams = []
    base_elos = {
        1: 1800, 2: 1750, 3: 1720, 4: 1700,
        5: 1680, 6: 1660, 7: 1640, 8: 1620,
        9: 1600, 10: 1580, 11: 1560, 12: 1540,
        13: 1520, 14: 1500, 15: 1480, 16: 1460,
    }
    for region in REGIONS:
        for seed in range(1, n_per_region + 1):
            teams.append(Team(
                name=f"{region}_S{seed}",
                elo=float(base_elos[seed]),
                seed=seed,
                region=region,
            ))
    return teams


@pytest.fixture
def teams():
    return make_teams()


@pytest.fixture
def region_teams():
    return [t for t in make_teams() if t.region == "east"]


@pytest.fixture
def tmp_csv(tmp_path):
    path = tmp_path / "teams.csv"
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["team", "elo", "seed", "region"])
        for t in make_teams():
            w.writerow([t.name, t.elo, t.seed, t.region])
    return str(path)


# ---------------------------------------------------------------------------
# ELO math
# ---------------------------------------------------------------------------

class TestWinProb:
    def test_equal_elo_is_fifty_fifty(self):
        a = Team("A", 1500, 1, "East")
        b = Team("B", 1500, 1, "West")
        assert win_prob(a, b) == pytest.approx(0.5)

    def test_higher_elo_favored(self):
        a = Team("A", 1700, 1, "East")
        b = Team("B", 1500, 1, "West")
        p = win_prob(a, b)
        assert p > 0.5

    def test_prob_sums_to_one(self):
        a = Team("A", 1700, 1, "East")
        b = Team("B", 1600, 2, "West")
        assert win_prob(a, b) + win_prob(b, a) == pytest.approx(1.0)

    def test_400_point_gap(self):
        """400 pt gap → ~91% win probability."""
        a = Team("A", 1900, 1, "East")
        b = Team("B", 1500, 16, "East")
        p = win_prob(a, b)
        assert 0.90 < p < 0.92

    def test_prob_bounded(self):
        # Use a realistic but large gap (600 pts → ~97% win prob, still < 1.0)
        a = Team("A", 2100, 1, "East")
        b = Team("B", 1500, 16, "East")
        p = win_prob(a, b)
        assert 0 < p < 1


class TestUpdateElo:
    def test_winner_gains_points(self):
        w = Team("W", 1600, 1, "East")
        l = Team("L", 1600, 2, "East")
        w_before, l_before = w.elo, l.elo
        update_elo(w, l)
        assert w.elo > w_before
        assert l.elo < l_before

    def test_zero_sum(self):
        """Total ELO is conserved."""
        w = Team("W", 1700, 1, "East")
        l = Team("L", 1600, 2, "East")
        total_before = w.elo + l.elo
        update_elo(w, l)
        assert w.elo + l.elo == pytest.approx(total_before)

    def test_upset_gains_more(self):
        """Underdog gains more points when winning than favorite."""
        fav  = Team("Fav",  1800, 1, "East")
        dog  = Team("Dog",  1500, 16, "East")
        dog2 = Team("Dog2", 1500, 16, "East")
        fav2 = Team("Fav2", 1800, 1,  "East")
        # Underdog wins
        update_elo(dog, fav)
        dog_gain = dog.elo - 1500

        # Favorite wins
        update_elo(fav2, dog2)
        fav_gain = fav2.elo - 1800

        assert dog_gain > fav_gain


class TestSimulateGame:
    def test_returns_winner_and_loser(self):
        a = Team("A", 1700, 1, "East")
        b = Team("B", 1600, 2, "East")
        w, l = simulate_game(a, b)
        assert {w.name, l.name} == {"A", "B"}

    def test_elo_updated_after_game(self):
        a = Team("A", 1700, 1, "East")
        b = Team("B", 1600, 2, "East")
        a_start, b_start = a.elo, b.elo
        simulate_game(a, b)
        assert a.elo != a_start or b.elo != b_start  # at least one changed

    def test_strong_team_wins_more_often(self):
        random.seed(42)
        wins = 0
        for _ in range(1000):
            a = Team("A", 1900, 1, "East")
            b = Team("B", 1500, 16, "East")
            w, _ = simulate_game(a, b)
            if w.name == "A":
                wins += 1
        assert wins > 850  # should win ~91% of the time


# ---------------------------------------------------------------------------
# Bracket construction
# ---------------------------------------------------------------------------

class TestBuildRegionBracket:
    def test_correct_length(self, region_teams):
        bracket = build_region_bracket(region_teams)
        assert len(bracket) == 16

    def test_matchup_order(self, region_teams):
        bracket = build_region_bracket(region_teams)
        pairs = [(bracket[i].seed, bracket[i+1].seed) for i in range(0, 16, 2)]
        assert pairs == list(SEED_MATCHUPS)

    def test_all_teams_present(self, region_teams):
        bracket = build_region_bracket(region_teams)
        assert set(t.name for t in bracket) == set(t.name for t in region_teams)


# ---------------------------------------------------------------------------
# Region simulation
# ---------------------------------------------------------------------------

class TestSimulateRegion:
    def test_returns_single_winner(self, region_teams):
        winner, rounds = simulate_region(region_teams)
        assert isinstance(winner, Team)

    def test_four_rounds(self, region_teams):
        _, rounds = simulate_region(region_teams)
        assert len(rounds) == 4

    def test_round_game_counts(self, region_teams):
        _, rounds = simulate_region(region_teams)
        expected = [8, 4, 2, 1]
        for r, exp in zip(rounds, expected):
            assert len(r) == exp

    def test_winner_comes_from_teams(self, region_teams):
        names = {t.name for t in region_teams}
        winner, _ = simulate_region(region_teams)
        assert winner.name in names

    def test_elo_changes_during_sim(self, region_teams):
        import copy
        original_elos = {t.name: t.elo for t in region_teams}
        cloned = copy.deepcopy(region_teams)
        simulate_region(cloned)
        changed = sum(1 for t in cloned if t.elo != original_elos[t.name])
        assert changed > 0


# ---------------------------------------------------------------------------
# Full tournament
# ---------------------------------------------------------------------------

class TestSimulateTournament:
    def test_returns_champion(self, teams):
        result = simulate_tournament(teams)
        assert "champion" in result
        assert isinstance(result["champion"], Team)

    def test_champion_in_team_list(self, teams):
        names = {t.name for t in teams}
        result = simulate_tournament(teams)
        assert result["champion"].name in names

    def test_four_regions_in_results(self, teams):
        result = simulate_tournament(teams)
        assert set(result["region_brackets"].keys()) == set(REGIONS)

    def test_two_f4_games(self, teams):
        result = simulate_tournament(teams)
        assert len(result["f4_results"]) == 2

    def test_championship_has_two_teams(self, teams):
        result = simulate_tournament(teams)
        w, l = result["champ_result"]
        assert w.name != l.name

    def test_run_single_preserves_original_elos(self, teams):
        orig = {t.name: t.elo for t in teams}
        run_single(teams)
        for t in teams:
            assert t.elo == orig[t.name], f"{t.name} ELO was mutated"


# ---------------------------------------------------------------------------
# Monte Carlo
# ---------------------------------------------------------------------------

class TestRunTrials:
    def test_correct_count(self, teams):
        results = run_trials(teams, n=50)
        assert len(results) == 50

    def test_each_result_has_champion(self, teams):
        results = run_trials(teams, n=20)
        for r in results:
            assert "champion" in r


class TestComputeProbabilities:
    def test_returns_one_row_per_team(self, teams):
        results = run_trials(teams, n=100)
        rows = compute_probabilities(teams, results)
        assert len(rows) == len(teams)

    def test_probabilities_between_0_and_1(self, teams):
        results = run_trials(teams, n=100)
        rows = compute_probabilities(teams, results)
        for row in rows:
            for key in ["prb_win_rd64", "prb_win_rd32", "prb_win_s16",
                        "prb_win_e8", "prb_win_f4", "prb_win_champ"]:
                assert 0.0 <= row[key] <= 1.0, f"{key} out of range for {row['team']}"

    def test_probs_decrease_across_rounds(self, teams):
        """On average, later-round probs should be ≤ earlier-round probs."""
        random.seed(0)
        results = run_trials(teams, n=500)
        rows = compute_probabilities(teams, results)
        for row in rows:
            assert row["prb_win_rd64"] >= row["prb_win_rd32"], row["team"]
            assert row["prb_win_rd32"] >= row["prb_win_s16"],  row["team"]
            assert row["prb_win_s16"]  >= row["prb_win_e8"],   row["team"]
            assert row["prb_win_e8"]   >= row["prb_win_f4"],   row["team"]
            assert row["prb_win_f4"]   >= row["prb_win_champ"], row["team"]

    def test_champ_probs_sum_to_one(self, teams):
        random.seed(1)
        results = run_trials(teams, n=500)
        rows = compute_probabilities(teams, results)
        total = sum(r["prb_win_champ"] for r in rows)
        assert total == pytest.approx(1.0, abs=0.02)

    def test_better_seed_higher_champ_prob(self, teams):
        """Seed 1 should beat seed 16 in championship probability on average."""
        random.seed(2)
        results = run_trials(teams, n=1000)
        rows = compute_probabilities(teams, results)
        by_name = {r["team"]: r for r in rows}
        for region in REGIONS:
            s1 = by_name[f"{region}_S1"]["prb_win_champ"]
            s16 = by_name[f"{region}_S16"]["prb_win_champ"]
            assert s1 > s16, f"{region}: seed 1 ({s1}) not > seed 16 ({s16})"


# ---------------------------------------------------------------------------
# CSV I/O
# ---------------------------------------------------------------------------

def write_csv(path, rows, header=("team", "elo", "seed", "region")):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


class TestLoadTeams:
    def test_loads_correct_count(self, tmp_csv):
        teams = load_teams(tmp_csv)
        assert len(teams) == 64

    def test_fields_parsed(self, tmp_csv):
        teams = load_teams(tmp_csv)
        t = teams[0]
        assert isinstance(t.name, str)
        assert isinstance(t.elo, float)
        assert isinstance(t.seed, int)
        assert isinstance(t.region, str)

    def test_all_regions_present(self, tmp_csv):
        teams = load_teams(tmp_csv)
        assert set(t.region for t in teams) == set(REGIONS)

    def test_skips_row_missing_seed(self, tmp_path):
        """A row with blank seed is skipped; remaining valid rows still validated."""
        path = str(tmp_path / "teams.csv")
        good_rows = [[f"{r}_S{s}", 1600, s, r] for r in REGIONS for s in range(1, 17)]
        # Add an extra row with blank seed — should be skipped silently
        rows = good_rows + [["NoSeedTeam", 1600, "", "East"]]
        write_csv(path, rows)
        teams = load_teams(path)
        assert len(teams) == 64
        assert all(t.name != "NoSeedTeam" for t in teams)

    def test_skips_row_missing_region(self, tmp_path):
        path = str(tmp_path / "teams.csv")
        good_rows = [[f"{r}_S{s}", 1600, s, r] for r in REGIONS for s in range(1, 17)]
        rows = good_rows + [["NoRegionTeam", 1600, 1, ""]]
        write_csv(path, rows)
        teams = load_teams(path)
        assert len(teams) == 64

    def test_skips_row_missing_elo(self, tmp_path):
        path = str(tmp_path / "teams.csv")
        good_rows = [[f"{r}_S{s}", 1600, s, r] for r in REGIONS for s in range(1, 17)]
        rows = good_rows + [["NoEloTeam", "", 1, "East"]]
        write_csv(path, rows)
        teams = load_teams(path)
        assert len(teams) == 64

    def test_skips_row_with_bad_elo(self, tmp_path):
        path = str(tmp_path / "teams.csv")
        good_rows = [[f"{r}_S{s}", 1600, s, r] for r in REGIONS for s in range(1, 17)]
        rows = good_rows + [["BadEloTeam", "not_a_number", 1, "East"]]
        write_csv(path, rows)
        teams = load_teams(path)
        assert len(teams) == 64

    def test_extra_columns_ignored(self, tmp_path):
        path = str(tmp_path / "teams.csv")
        rows = [[f"{r}_S{s}", 1600, s, r, "extra_col"] for r in REGIONS for s in range(1, 17)]
        write_csv(path, rows, header=("team", "elo", "seed", "region", "conference"))
        teams = load_teams(path)
        assert len(teams) == 64


class TestValidateTeams:
    def good_teams(self):
        return [Team(f"{r}_S{s}", 1600, s, r) for r in REGIONS for s in range(1, 17)]

    def test_valid_field_passes(self):
        _validate_teams(self.good_teams())  # should not raise

    def test_wrong_total_count(self):
        teams = self.good_teams()[:63]
        with pytest.raises(ValueError, match="63"):
            _validate_teams(teams)

    def test_duplicate_team_name(self):
        teams = self.good_teams()
        teams[1].name = teams[0].name  # make a duplicate
        with pytest.raises(ValueError, match="Duplicate"):
            _validate_teams(teams)

    def test_wrong_region_count(self):
        teams = [Team(f"X_S{s}", 1600, s, "East") for s in range(1, 65)]
        with pytest.raises(ValueError, match="region"):
            _validate_teams(teams)

    def test_wrong_team_count_per_region(self):
        teams = self.good_teams()
        for t in teams:
            if t.region == "east" and t.seed == 16:
                t.region = "west"
                break
        with pytest.raises(ValueError, match="east"):
            _validate_teams(teams)

    def test_missing_seed_in_region(self):
        teams = self.good_teams()
        for t in teams:
            if t.region == "east" and t.seed == 1:
                t.seed = 17
                break
        with pytest.raises(ValueError, match="east"):
            _validate_teams(teams)

    def test_duplicate_seed_in_region(self):
        teams = self.good_teams()
        for t in teams:
            if t.region == "east" and t.seed == 16:
                t.seed = 1
                break
        with pytest.raises(ValueError, match="east"):
            _validate_teams(teams)

    def test_unknown_region_name(self):
        teams = self.good_teams()
        for t in teams:
            if t.region == "east":
                t.region = "atlantic"
        with pytest.raises(ValueError, match="Unknown region"):
            _validate_teams(teams)

    def test_mixed_case_region_accepted(self, tmp_path):
        path = str(tmp_path / "teams.csv")
        rows = []
        region_map = {"East": "east", "West": "West", "South": "SOUTH", "Midwest": "MidWest"}
        for csv_region, actual_region in region_map.items():
            for s in range(1, 17):
                rows.append([f"{actual_region}_S{s}", 1600, s, actual_region])
        write_csv(path, rows)
        teams = load_teams(path)
        assert all(t.region in REGIONS for t in teams)


class TestSaveProbabilities:
    def test_creates_file(self, teams, tmp_path):
        results = run_trials(teams, n=10)
        rows = compute_probabilities(teams, results)
        out = str(tmp_path / "probs.csv")
        path = save_probabilities(rows, out)
        assert os.path.exists(path)

    def test_correct_columns(self, teams, tmp_path):
        results = run_trials(teams, n=10)
        rows = compute_probabilities(teams, results)
        out = str(tmp_path / "probs.csv")
        save_probabilities(rows, out)
        with open(out) as f:
            reader = csv.DictReader(f)
            cols = reader.fieldnames
        expected = ["team", "seed", "region", "prb_win_rd64", "prb_win_rd32",
                    "prb_win_s16", "prb_win_e8", "prb_win_f4", "prb_win_champ"]
        assert cols == expected

    def test_correct_row_count(self, teams, tmp_path):
        results = run_trials(teams, n=10)
        rows = compute_probabilities(teams, results)
        out = str(tmp_path / "probs.csv")
        save_probabilities(rows, out)
        with open(out) as f:
            data = list(csv.DictReader(f))
        assert len(data) == 64
