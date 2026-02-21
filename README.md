# March Madness ELO Simulator

Simulates the NCAA Tournament using ELO ratings.

## Setup

```bash
pip install matplotlib pytest
```

## Input CSV format

Create a CSV with columns: `team, elo, seed, region`

```
team,elo,seed,region
Michigan,1871,1,east
Duke,1803,1,west
Arizona,1792,1,south
Houston,1784,1,midwest
...
```

- **64 teams total** (16 per region)
- Regions: `east`, `west`, `south`, `midwest` (case-insensitive)
- Seeds 1–16 per region
- ELO: any numeric rating (Warren Nolan's site is a good source)
- Extra columns (e.g. `record`, `rank`) are ignored

A sample file is included: `sample_teams.csv`

## Usage

### Single simulation + bracket image

```bash
python run.py --teams sample_teams.csv
```

Outputs:
- `bracket_YYYY-MM-DD.txt` — ASCII text bracket
- `bracket_YYYY-MM-DD.png` — visual bracket image

### Single sim + 10,000 trial Monte Carlo

```bash
python run.py --teams sample_teams.csv --trials 10000
```

Outputs:
- `bracket_YYYY-MM-DD.txt` — ASCII text bracket
- `bracket_YYYY-MM-DD.png` — visual bracket image
- `probs_YYYY-MM-DD.csv` — per-team round probabilities

### Custom output paths

```bash
python run.py --teams sample_teams.csv --trials 10000 \
  --out-image my_bracket.png \
  --out-probs my_probs.csv
```

### Reproducible results

```bash
python run.py --teams sample_teams.csv --trials 10000 --seed 42
```

## Probabilities CSV columns

| Column | Meaning |
|---|---|
| `team` | Team name |
| `seed` | Tournament seed (1–16) |
| `region` | Region |
| `prb_win_rd64` | P(win Round of 64 game) |
| `prb_win_rd32` | P(win Round of 32 game) |
| `prb_win_s16` | P(win Sweet 16 game) |
| `prb_win_e8` | P(win Elite 8 game) |
| `prb_win_f4` | P(win Final Four game) |
| `prb_win_champ` | P(win Championship game) |

## ELO mechanics

- **Win probability**: `P(A beats B) = 1 / (1 + 10^((B_elo - A_elo) / 400))`
- **Update after each game**: `new_elo = old_elo + K * (result - expected)` with K=20
- ELO is updated after every game before the next round is simulated
- Each Monte Carlo trial uses a fresh copy of the original ELOs

## Seeding analysis

Identify which teams are most over- or underseeded based on ELO vs. the average ELO
for their seed position across all four regions.

```bash
python analyze_seeding.py --teams teams_2.20.csv
python analyze_seeding.py --teams teams_2.20.csv --top 5
```

Outputs to terminal and saves `seeding_analysis_YYYY-MM-DD.txt`:
- Average ELO for each seed (1–16)
- Top N **underseeded** teams (ELO well above their seed's average — deserve a better seed)
- Top N **overseeded** teams (ELO well below their seed's average — got too generous a seed)

## Running tests

```bash
python -m pytest test_simulator.py -v
```
