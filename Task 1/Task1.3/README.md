# ⚽ FIFA World Cup Match Simulation Engine

An object-oriented, event-driven FIFA World Cup simulation system built in Python. The engine simulates a full 90-minute match featuring realistic stamina decay, position-based attribute aggregation, a dynamic red-card discipline system, an event-driven AI coach (powered by Groq or a rule-based fallback), and a best-of-5 penalty shootout for drawn matches.

---

## 🏗 System Architecture & Class Overview

The system is designed around a modular Object-Oriented Architecture following strict mathematical formulas and deterministic state machines.

```
       ┌────────────────┐          ┌────────────────┐
       │     Player     │ 1----11* │      Team      │
       └───────┬────────┘          └───────┬────────┘
               │                           │
               ▼                           ▼
       ┌────────────────────────────────────────────┐
       │                   Match                    │
       └───────┬───────────────────────────┬────────┘
               │                           │
               ▼                           ▼
       ┌────────────────┐          ┌────────────────┐
       │   MatchEvent   │          │    MatchAI     │
       └────────────────┘          └────────────────┘
```

### 1. `Player`
Represents an individual athlete on the field.
* **Attributes**: Name, position (`FORWARD`, `MIDFIELDER`, `DEFENDER`, `GOALKEEPER`), base attack (1–100), base defense (1–100), dynamic stamina (initialized at 100.0), and incident tracking.
* **Key Logic**:
  * `deplete_stamina(rate)`: Reduces stamina per minute, clamped strictly at a floor of `10.0`.
  * `get_effective_attack()` / `get_effective_defense()`: Scales base attributes linearly by current stamina percentage: $\text{Base} \times (\text{Stamina} / 100.0)$.

### 2. `Team`
Acts as an aggregate container managing players, lineups, formations, and bench availability.
* **Attributes**: Roster (26 players), active lineup (11 starters), bench (15 players), remaining substitutions (5), and formation layout.
* **Key Logic**:
  * `get_aggregate_attack()` / `get_aggregate_defense()`: Sums effective stats across current positional buckets and averages them over active members. Handled safely to return `0.0` if a bucket is empty (preventing `ZeroDivisionError`).
  * `change_formation(formation_name)`: Dynamically re-tags players into `DEFENSE` vs. `ATTACK` buckets (`5-3-2`, `4-4-2`, `3-4-3`) to shift tactical output without altering player stats.
  * `execute_substitution()` & `auto_substitute_lowest_stamina()`: Swaps fatigue-depleted starters with top bench candidates of the same position.

### 3. `MatchEvent`
An **immutable structural record** logging occurrences during the match (goals, yellow/red cards, half-time, full-time). Exposes read-only properties to keep the timeline tamper-proof.

### 4. `Match`
The procedural state engine running the minute-by-minute simulation loop.
* **Logic**:
  * **Minute Loop**: Decrements stamina, checks for incidents/discipline, evaluates goal attempts, and transitions through match phases (`REGULATION` $\rightarrow$ `FINISHED`).
  * **Math Engine**: Scoring attempts occur with a 10% base chance per minute. A goal is scored when:
    $$\text{Attack Roll} > \text{Defense Roll}$$
  * **Event-Driven AI Gate (`_should_consult_ai`)**: Optimizes AI coaching requests by only triggering consultations on key match events (goals, half-time, major fatigue dips) instead of querying every single minute (cutting API calls from ~180 to 5–15 per match).

### 5. `MatchAI` (Bonus AI Model)
Acts as a tactical coach modifying team strategy mid-match.
* **Integrates**: Real-time Groq LLM client (`llama-3.3-70b-versatile`) with automatic rule-based fallback if no API key is supplied.
* **Actions**: `SUBSTITUTE`, `CHANGE_FORMATION`, `HOLD` (lower risk/stamina consumption), and `PUSH_ATTACK` (higher risk/attack variance).

### 6. `PenaltyShootout`
Simulates a best-of-5 kick-by-kick penalty shootout (with sudden death capability) if regulation ends in a draw.

---

## 📊 Terminal Output Guide

When you run the script, the output is broken into distinct analytical sections:

```text
=== Match Timeline ===
[6'] DISCIPLINE | FRA | FRA_13 | FRA_13 picks up a second incident and is sent off!
[9'] GOAL | ARG | ARG_13 | GOAL! ARG_13 scores for ARG.
...
[90'] FULL_TIME | N/A | - | DRAW 3-3
```
* **Match Timeline**: Chronological, real-time breakdown logging exact timestamps `[Minute']`, event types, involved teams/players, and descriptive event text.

---

```text
Final Score: ARG 3 - 3 FRA
Result: DRAW 3-3
```
* **Match Outcome**: The final scoreline and state phase resolution after 90 minutes.

---

```text
=== Auto-substitution demo (lowest stamina swap) ===
ARG_04 (stamina 48.2) subbed off, ARG_10 comes on.
```
* **Substitution Summary**: Demonstrates automated bench management targeting the player with the lowest stamina pool.

---

```text
=== Discipline system summary ===
...
ARG sent-off count: 2 | FRA sent-off count: 3
```
* **Discipline Log**: Lists all yellow/red card dismissals and tallies sent-off players per squad.

---

```text
=== Safety-net stress test: emptying an entire position group ===
Forwards remaining in active lineup: []
get_aggregate_attack() with no forwards/midfielders imbalance handled safely: 73.00 (no crash)
```
* **Safety Test Verification**: Proves defensive programming—verifying that removing an entire position group doesn't crash the simulation with a zero-division exception.

---

```text
=== Match drawn - proceeding to penalties ===
Rd  Team           Result
1   ARG            SCORED
1   FRA            MISSED
...
Penalty shootout result: ARG 4 - 1 FRA
Winner: ARG
```
* **Penalty Shootout Board**: A kick-by-kick breakdown showing each round, attempt results (`SCORED` / `MISSED`), and the winner.

---

```text
=== AI coach decision logs (event-driven consultations only) ===
ARG coach (8 consultations this match):
  - action=PUSH_ATTACK -> risk_tolerance now 0.70
  - action=PUSH_ATTACK -> risk_tolerance now 0.90
```
* **AI Decision Audit**: Displays how many event-driven triggers fired and tracks each coach's tactical choices (`risk_tolerance` adjustments, formation switches, or substitutions).

---

## 🚀 How to Run

1. **Prerequisites**: Python 3.8+
2. **Optional LLM Setup**: Set your Groq API key in environment variables or a `.env` file:
   ```bash
   export GROQ_API_KEY="your-groq-api-key"
   ```
3. **Execute**:
   ```bash
   python Task1_3.py
   ```
   *(Note: If no API key is provided, press Enter at the prompt to run using the built-in rule-based fallback AI).*
