# 🏆 FIFA World Cup Group Stage Standings Engine (Task 1.1)

An interactive Python implementation of the World Cup Group Stage Standings Engine. The system computes live standings tables, updates statistical dictionaries, enforces official FIFA tie-breaking hierarchies, and formats broadcast-ready tables with strict sign constraints.

---

## 🏗️ Architectural & Code Explanation

### 1. Data Structure Architecture
The standings state is maintained as a nested Python dictionary where each country name maps to its aggregate tournament metrics initialized at zero:

```python
standings = {
    "ARG": {"P": 0, "W": 0, "D": 0, "L": 0, "GF": 0, "GA": 0, "GD": 0, "Pts": 0},
    "MEX": {"P": 0, "W": 0, "D": 0, "L": 0, "GF": 0, "GA": 0, "GD": 0, "Pts": 0},
    "POL": {"P": 0, "W": 0, "D": 0, "L": 0, "GF": 0, "GA": 0, "GD": 0, "Pts": 0},
    "KSA": {"P": 0, "W": 0, "D": 0, "L": 0, "GF": 0, "GA": 0, "GD": 0, "Pts": 0},
}
```

* **`P`**: Matches Played (incremented by $+1$ for both teams per match).
* **`W` / `D` / `L`**: Wins ($+3$ Pts), Draws ($+1$ Pt each), Losses ($+0$ Pts).
* **`GF` / `GA`**: Goals For (scored) and Goals Against (conceded).
* **`GD`**: Goal Difference calculated dynamically as $	ext{GF} - 	ext{GA}$.
* **`Pts`**: Total accumulated points.

---

### 2. Core Functions & Execution Mechanics

#### A. `process_match(standings, team1, team2, team1_goals, team2_goals)`
* **Purpose**: Updates the nested dictionary for `team1` and `team2` following a match outcome.
* **Logic**:
  * Increments `P` by $1$ for both teams.
  * Adds `team1_goals` to `team1['GF']` and `team2['GA']`.
  * Adds `team2_goals` to `team2['GF']` and `team1['GA']`.
  * Recalculates `GD` for both teams: $	ext{GD} = 	ext{GF} - 	ext{GA}$.
  * **Points Allocation**:
    * If `team1_goals > team2_goals`: `team1` gets $+1$ `W`, $+3$ `Pts`; `team2` gets $+1$ `L`, $+0$ `Pts`.
    * If `team2_goals > team1_goals`: `team2` gets $+1$ `W`, $+3$ `Pts`; `team1` gets $+1$ `L`, $+0$ `Pts`.
    * If `team1_goals == team2_goals`: Both teams get $+1$ `D` and $+1$ `Pt`.

#### B. `sort_standings(standings, match_history)`
* **Purpose**: Applies FIFA's strict 4-level sorting hierarchy to order teams:
  1. **Primary**: Points (`Pts`) — Highest first.
  2. **Secondary**: Goal Difference (`GD`) — Best first.
  3. **Tertiary**: Goals Scored (`GF`) — Most first.
  4. **Quaternary (Bonus)**: Head-to-Head result lookup between tied teams from recorded match history.

#### C. `print_standings(standings)`
* **Purpose**: Renders the sorted table into neatly formatted, aligned terminal columns.
* **Formatting Rules**:
  * Goal Difference (`GD`) formatting strictly adheres to FIFA presentation rules:
    * Positive GD: Includes explicit `+` prefix (e.g., `+3`, `+8`).
    * Negative GD: Includes explicit `-` prefix (e.g., `-13`).
    * Zero GD: Formatted as plain `0` (never `+0` or `-0`).

#### D. Input Validation Wrapper (Bonus)
* **Purpose**: Uses regular expressions / exception handling to validate user score inputs (e.g., verifying `X-Y` integer format). Prevents program termination if a user inputs bad formats like `"two-zero"` or blank strings.

---

## 📊 Terminal Output & Execution Breakdown

Below is the line-by-line analytical breakdown of the provided execution logs:

```text
Enter score for ARG vs MEX (format: 2-0): 2-2
Enter score for ARG vs POL (format: 2-0): 2-1
Enter score for ARG vs KSA (format: 2-0): 2-0
Enter score for MEX vs POL (format: 2-0): 1-13
Enter score for MEX vs KSA (format: 2-0): 3-4
Enter score for POL vs KSA (format: 2-0): 1-10

=== Final Group Standings ===
Team    P  W  D  L  GF  GA   GD  Pts
ARG     3  2  1  0   6   3   +3    7
KSA     3  2  0  1  14   6   +8    6
POL     3  1  0  2  15  13   +2    3
MEX     3  0  1  2   6  19  -13    1
```

### Table Meaning & Statistical Verification
* **ARG (1st Place - 7 Pts)**: Undefeated record (2 Wins, 1 Draw). Scored 6 goals, conceded 3 $ightarrow$ $	ext{GD} = +3$.
* **KSA (2nd Place - 6 Pts)**: 2 Wins (beat MEX 4-3 and POL 10-1) and 1 Loss (to ARG 0-2). Accumulates 14 GF, 6 GA $ightarrow$ $	ext{GD} = +8$.
* **POL (3rd Place - 3 Pts)**: 1 Win (blew out MEX 13-1) and 2 Losses. Despite scoring 15 goals, finishes 3rd due to lower total points ($3$ Pts).
* **MEX (4th Place - 1 Pt)**: 1 Draw (2-2 vs ARG) and 2 heavy losses. Conceded 19 goals $ightarrow$ $	ext{GD} = -13$.

---

### Tie-Breaker Demonstration Outputs

#### Demonstration 1: Goals Scored (`GF`) Fallback
```text
DEMO 1: Points + GD tie -> resolved by Goals Scored (GF)
EGY and BEL are both Pts=5, GD=+3, but EGY has GF=5 vs BEL's GF=4.
Expected order: EGY above BEL (GF breaks tie), then ARG, then GER.

Team    P  W  D  L  GF  GA   GD  Pts
EGY     3  1  2  0   5   2   +3    5
BEL     3  1  2  0   4   1   +3    5
ARG     3  1  1  1   3   3    0    4
GER     3  0  1  2   1   5   -4    1

PASS: GF tiebreak works correctly!
```
* **Analysis**: `EGY` and `BEL` are completely tied on Points ($5$) and GD ($+3$). The engine evaluates Level 3 tie-break (`GF`). Since `EGY` scored $5$ goals vs `BEL`'s $4$, `EGY` is sorted into 1st place.

#### Demonstration 2: Head-to-Head (Bonus) Fallback
```text
DEMO 2: Pts + GD tie -> resolved by Head-to-Head
EGY and BEL are tied on Pts=6 and GD=+2. EGY beat BEL 2-1 head-to-head.
Expected order: EGY above BEL, then ENG.

Team    P  W  D  L  GF  GA   GD  Pts
EGY     3  2  0  1   5   3   +2    6
BEL     3  2  0  1   5   3   +2    6
ENG     3  1  0  2   2   6   -4    3

PASS: Head-to-head tiebreak works correctly!
```
* **Analysis**: `EGY` and `BEL` are tied across Points ($6$), GD ($+2$), and GF ($5$). The engine queries match history for `EGY` vs `BEL`, finds `EGY` won $2-1$, and correctly places `EGY` above `BEL`.

---

## 🚀 How to Run

1. Run the script via python:
   ```bash
   python Task1_1.py
   ```
2. Enter scores in `X-Y` format when prompted (e.g., `2-0`).
