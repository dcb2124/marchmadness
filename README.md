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
Michigan,1871,1,East
Duke,1803,1,West
Arizona,1792,1,South
Houston,1784,1,Midwest
...
```

- **64 teams total** (16 per region)
- Regions: `East`, `West`, `South`, `Midwest`
- Seeds 1–16 per region
- ELO: any numeric rating (Warren Nolan's site is a good source)

A sample file is included: `sample_teams.csv`

## Usage

### Single simulation + bracket image

```bash
python run.py --teams sample_teams.csv
```

Outputs: `bracket_YYYY-MM-DD.png`

### Single sim + 10,000 trial Monte Carlo

```bash
python run.py --teams sample_teams.csv --trials 10000
```

Outputs:
- `bracket_YYYY-MM-DD.png` — visual bracket from the single sim
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
| `prb_rd1` | P(advance past Round of 64) |
| `prb_rd2` | P(advance past Round of 32) |
| `prb_s16` | P(reach Sweet 16) |
| `prb_e8` | P(reach Elite 8) |
| `prb_f4` | P(reach Final Four) |
| `prb_finals` | P(reach Championship game) |
| `prb_champ` | P(win Championship) |

## ELO mechanics

- **Win probability**: `P(A beats B) = 1 / (1 + 10^((B_elo - A_elo) / 400))`
- **Update after each game**: `new_elo = old_elo + K * (result - expected)` with K=20
- ELO is updated after every game before the next round is simulated
- Each Monte Carlo trial uses a fresh copy of the original ELOs

## Running tests

```bash
python -m pytest test_simulator.py -v
```
