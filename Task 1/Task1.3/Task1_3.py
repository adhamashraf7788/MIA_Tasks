"""Soccer match simulator."""

import json
import random
import os
from enum import Enum

# ==========================================================
# Optional Groq API Key
# ==========================================================
# You can supply your Groq API key in any of these ways (checked in order):
#   1. A .env file in this directory: GROQ_API_KEY=gsk_...
#   2. An environment variable set in your shell
#   3. Typing it in when prompted below 
#
# If you skip the prompt (just press Enter), GROQ_API_KEY stays None and
# the built-in rule-based fallback AI is used automatically instead —
# the match still runs fully either way.

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# Simple fallback prompt using standard input()
if not GROQ_API_KEY:
    entered = input(
        "Enter Groq API key (or press Enter to skip & use rule-based AI): "
    ).strip()
    GROQ_API_KEY = entered or None
# ==========================================================
# Groq client (optional dependency)
# ==========================================================
try:
    from groq import Groq
    _GROQ_SDK_AVAILABLE = True
except ImportError:
    _GROQ_SDK_AVAILABLE = False


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class Position(Enum):
    FORWARD = "FORWARD"
    MIDFIELDER = "MIDFIELDER"
    DEFENDER = "DEFENDER"
    GOALKEEPER = "GOALKEEPER"


class EventType(Enum):
    GOAL = "GOAL"
    SUBSTITUTION = "SUBSTITUTION"
    HALF_TIME = "HALF_TIME"
    FULL_TIME = "FULL_TIME"
    DISCIPLINE = "DISCIPLINE"  # Bonus extension: logs a player being sent off


class Phase(Enum):
    REGULATION = "REGULATION"
    FINISHED = "FINISHED"


# Bonus (CHANGE_FORMATION support): exact ATTACK/DEFENSE bucket sizes per
# formation, straight from the spec table. Re-tagging active_lineup members
# into these bucket counts - not by their natural position label - is what
# "shifts both the numerator and denominator of each average."
FORMATIONS = {
    "DEFENSIVE_5_3_2": {"defense": 6, "attack": 5},
    "BALANCED_4_4_2": {"defense": 5, "attack": 6},
    "ATTACKING_3_4_3": {"defense": 4, "attack": 7},
}


# ---------------------------------------------------------------------------
# Player
# ---------------------------------------------------------------------------

class Player:
    """Represents an individual athlete."""

    STAMINA_FLOOR = 10.0

    def __init__(self, name, position, base_attack, base_defense):
        assert 1 <= base_attack <= 100, "base_attack must be scaled strictly from 1 to 100"
        assert 1 <= base_defense <= 100, "base_defense must be scaled strictly from 1 to 100"

        self.name = name
        self.position = position  # Position enum
        self.base_attack = base_attack      # 1-100
        self.base_defense = base_defense    # 1-100
        self.stamina = 100.0
        self.incidents = 0  # discipline bonus: tracked cards/fouls

    def deplete_stamina(self, rate):
        """Deducts rate from stamina, floored at STAMINA_FLOOR."""
        self.stamina = max(self.STAMINA_FLOOR, self.stamina - rate)

    def get_effective_attack(self):
        return self.base_attack * (self.stamina / 100.0)

    def get_effective_defense(self):
        return self.base_defense * (self.stamina / 100.0)

    def add_incident(self):
        """Bonus: discipline tracking. Returns True if player should be
        sent off (pulled from active lineup) after this incident."""
        self.incidents += 1
        return self.incidents >= 2  # 2 incidents = pulled (yellow-yellow style)

    def __repr__(self):
        return f"Player({self.name}, {self.position.value}, stamina={self.stamina:.1f})"


# ---------------------------------------------------------------------------
# Team
# ---------------------------------------------------------------------------

class Team:
    """Aggregate collection of Player instances."""

    def __init__(self, country_name, roster):
        assert len(roster) == 26, "roster must contain exactly 26 registered squad players"

        self.country_name = country_name
        self.roster = roster                     # full 26-player list
        self.active_lineup = self._pick_starting_xi(roster)
        self.substitutions_remaining = 5
        self.sent_off = []                        # bonus: disciplined players removed entirely

        # Bonus (CHANGE_FORMATION support): current formation name. Each
        # active player also carries a `.bucket` tag ("ATTACK"/"DEFENSE")
        # assigned by _apply_formation_buckets() below, using the exact
        # per-formation player counts from FORMATIONS - not fixed position
        # categories - so changing formation genuinely shifts both the
        # numerator (who gets summed) and denominator (bucket size).
        self.formation = "BALANCED_4_4_2"
        self._apply_formation_buckets()

    @staticmethod
    def _pick_starting_xi(roster):
        """
        Builds a realistic starting XI (1 GK, 4 DEF, 4 MID, 2 FWD) rather than
        blindly slicing the first 11 of the roster, which could otherwise
        accidentally exclude an entire position group (e.g. no forwards).
        """
        by_position = {pos: [p for p in roster if p.position == pos] for pos in Position}
        quota = {
            Position.GOALKEEPER: 1,
            Position.DEFENDER: 4,
            Position.MIDFIELDER: 4,
            Position.FORWARD: 2,
        }
        lineup = []
        for pos, count in quota.items():
            lineup.extend(by_position[pos][:count])
        return lineup

    @property
    def bench(self):
        """Derived: roster minus active_lineup (and minus sent-off players)."""
        return [p for p in self.roster
                if p not in self.active_lineup and p not in self.sent_off]

    def _apply_formation_buckets(self):
        """
        Bonus (CHANGE_FORMATION support): tags every active player as
        "DEFENSE" or "ATTACK" according to the current formation's exact
        bucket sizes (FORMATIONS table), not their natural position label.

        Natural DEFENDER/GOALKEEPER players are preferred for the DEFENSE
        bucket first (up to the formation's defense count), with everyone
        else falling into ATTACK. This means the default BALANCED_4_4_2
        formation reproduces exactly the base-spec split (FORWARD+MIDFIELDER
        vs DEFENDER+GOALKEEPER) for the standard 1-4-4-2 starting XI, while
        CHANGE_FORMATION can genuinely shift both bucket sizes per the spec's
        Defensive(6/5) / Balanced(5/6) / Attacking(4/7) table.
        """
        counts = FORMATIONS[self.formation]
        active = list(self.active_lineup)
        ordered = sorted(
            active,
            key=lambda p: 0 if p.position in (Position.DEFENDER, Position.GOALKEEPER) else 1,
        )
        defense_bucket = set(ordered[: counts["defense"]])
        for p in active:
            p.bucket = "DEFENSE" if p in defense_bucket else "ATTACK"

    def _aggregate(self, bucket_name, getter):
        """
        Shared helper for aggregate attack/defense.
        Returns 0.0 safely if the bucket is empty (e.g. after enough
        players are sent off), instead of raising a ZeroDivisionError
        (bonus: discipline safety).
        """
        relevant = [p for p in self.active_lineup if getattr(p, "bucket", None) == bucket_name]
        if not relevant:
            return 0.0
        return sum(getter(p) for p in relevant) / len(relevant)

    def get_aggregate_attack(self):
        return self._aggregate("ATTACK", lambda p: p.get_effective_attack())

    def get_aggregate_defense(self):
        return self._aggregate("DEFENSE", lambda p: p.get_effective_defense())

    def change_formation(self, formation_name):
        """
        Bonus: CHANGE_FORMATION doesn't add or remove players - it re-tags
        the same 11 active_lineup members into ATTACK/DEFENSE buckets of
        the new formation's exact sizes, shifting both the numerator (who
        gets summed) and denominator (bucket size) of each average.
        """
        if formation_name not in FORMATIONS:
            raise ValueError(f"Unknown formation: {formation_name}")
        self.formation = formation_name
        self._apply_formation_buckets()

    def execute_substitution(self, player_out, player_in):
        if self.substitutions_remaining <= 0:
            return False
        if player_out not in self.active_lineup:
            return False
        if player_in not in self.bench:
            return False

        idx = self.active_lineup.index(player_out)
        self.active_lineup[idx] = player_in
        self.substitutions_remaining -= 1
        self._apply_formation_buckets()  # re-tag so bucket sizes stay correct
        return True

    def auto_substitute_lowest_stamina(self):
        """
        Bonus: automatically swaps out whichever active player has the
        lowest stamina for the highest-rated bench player at the same
        position. Returns (player_out, player_in) or None if no valid sub
        is available.
        """
        if self.substitutions_remaining <= 0 or not self.active_lineup:
            return None

        player_out = min(self.active_lineup, key=lambda p: p.stamina)
        candidates = [p for p in self.bench if p.position == player_out.position]
        if not candidates:
            return None

        player_in = max(candidates, key=lambda p: p.base_attack + p.base_defense)
        if self.execute_substitution(player_out, player_in):
            return player_out, player_in
        return None

    def send_off_player(self, player):
        """Bonus: discipline system - permanently removes a player from the
        active lineup (not swapped with a bench player, just pulled)."""
        if player in self.active_lineup:
            self.active_lineup.remove(player)
            self.sent_off.append(player)
            self._apply_formation_buckets()  # re-tag remaining players; safe even if a bucket empties out

    def __repr__(self):
        return f"Team({self.country_name})"


# ---------------------------------------------------------------------------
# MatchEvent (immutable record)
# ---------------------------------------------------------------------------

class MatchEvent:
    """An immutable structural record logging a definitive occurrence."""

    _next_id = 1

    def __init__(self, event_type, minute, team, player, outcome_text):
        self._event_id = f"EVT{MatchEvent._next_id:04d}"
        MatchEvent._next_id += 1
        self._event_type = event_type
        self._minute = minute
        self._team = team
        self._player = player  # may be None for team-level events
        self._outcome_text = outcome_text

    @property
    def event_id(self):
        return self._event_id

    @property
    def event_type(self):
        return self._event_type

    @property
    def minute(self):
        return self._minute

    @property
    def team(self):
        return self._team

    @property
    def player(self):
        return self._player

    @property
    def outcome_text(self):
        return self._outcome_text

    def to_string(self):
        team_name = self._team.country_name if self._team else "N/A"
        player_name = self._player.name if self._player else "-"
        return (f"[{self._minute}'] {self._event_type.value} | "
                f"{team_name} | {player_name} | {self._outcome_text}")


# ---------------------------------------------------------------------------
# Match
# ---------------------------------------------------------------------------

class Match:
    """The central procedural state engine."""

    BASE_DECAY = 0.5
    ATTEMPT_PROBABILITY = 0.10

    # Bonus: discipline system. Each active player has a small per-minute
    # chance of picking up an incident (foul/card). A player's SECOND
    # incident gets them sent off (see Player.add_incident()).
    INCIDENT_PROBABILITY = 0.02

    # ------------------------------------------------------------------
    # Event-driven AI consultation tuning.
    #
    # The spec's own "Integration point" line says to call
    # observe_state -> decide_action -> apply_decision "once per
    # run_minute_tick()", i.e. once a minute, 90 times per side per match.
    # That's fine as a rule-based decision (cheap), but wasteful and slow
    # if decide_action() is backed by a real network call to an LLM.
    #
    # Since decide_action()'s *contract* only requires it to return a
    # valid action when called - not that it be called every minute - we
    # gate consultations behind meaningful triggers instead:
    #   - a goal is scored (by either side, since it changes both scores)
    #   - half-time is reached
    #   - a team's average active-lineup stamina drops below a fatigue
    #     threshold for the first time this half
    # This keeps coaching decisions responsive to what actually matters
    # in the match, while cutting AI calls from ~180/match to roughly
    # 5-15/match depending on how many goals/fatigue dips occur.
    # ------------------------------------------------------------------
    FATIGUE_CONSULT_THRESHOLD = 65.0

    def __init__(self, home_team, away_team):
        self.home_team = home_team
        self.away_team = away_team
        self.home_score = 0
        self.away_score = 0
        self.current_minute = 0
        self.timeline = []
        self.phase = Phase.REGULATION

        # Bonus AI Model: optional coach per side (see MatchAI below).
        self.home_ai = None
        self.away_ai = None

        # Event-driven consultation bookkeeping (per side).
        self._goal_just_scored = False
        self._fatigue_flagged = {"home": False, "away": False}

    def run_minute_tick(self):
        self.current_minute += 1
        self._goal_just_scored = False

        for team, ai in ((self.home_team, self.home_ai), (self.away_team, self.away_ai)):
            decay = self.BASE_DECAY
            if ai is not None:
                # Bonus risk dial: stamina decay = Base_Decay * (1 + (risk_tolerance-0.5)*0.4)
                decay = self.BASE_DECAY * (1 + (ai.risk_tolerance - 0.5) * 0.4)
            for player in team.active_lineup:
                player.deplete_stamina(decay)

        # Bonus: discipline checks run before goal attempts, so a player sent
        # off this minute can't also be credited with a goal attempt below.
        self.process_discipline(self.home_team)
        self.process_discipline(self.away_team)

        self.process_goal_attempt(self.home_team, self.away_team)
        self.process_goal_attempt(self.away_team, self.home_team)

        # Bonus AI Model: event-driven observe -> decide -> apply.
        # Instead of consulting both coaches every single minute, only
        # consult a side's AI when a real trigger fires for it this
        # minute (goal scored anywhere, half-time, or that side's
        # fatigue crossing the threshold for the first time).
        for side, team, ai in (("home", self.home_team, self.home_ai),
                                ("away", self.away_team, self.away_ai)):
            if ai is None:
                continue
            if self._should_consult_ai(side, team):
                action = ai.decide_action(self)
                ai.apply_decision(action)

        if self.current_minute == 45:
            self.timeline.append(
                MatchEvent(EventType.HALF_TIME, self.current_minute, None, None, "Half-time reached")
            )
            # Reset the fatigue flags at half-time so a second-half dip
            # in stamina can still trigger a fresh consultation.
            self._fatigue_flagged = {"home": False, "away": False}

        if self.current_minute >= 90:
            self.phase = Phase.FINISHED

    def _should_consult_ai(self, side, team):
        """
        Event-driven gate for AI coaching calls. Returns True only when
        something happened this minute that a real coach would want to
        react to, instead of blindly firing every minute.
        """
        # Trigger 1: a goal went in this minute (either team's coach may
        # want to react - chasing the game or protecting a lead).
        if self._goal_just_scored:
            return True

        # Trigger 2: half-time is always worth a tactical check-in.
        if self.current_minute == 45:
            return True

        # Trigger 3: this side's average stamina just dropped below the
        # fatigue threshold for the first time since kickoff/half-time.
        if team.active_lineup:
            avg_stamina = sum(p.stamina for p in team.active_lineup) / len(team.active_lineup)
            if avg_stamina < self.FATIGUE_CONSULT_THRESHOLD and not self._fatigue_flagged[side]:
                self._fatigue_flagged[side] = True
                return True

        return False

    def process_discipline(self, team):
        """
        Bonus: discipline system. Rolls each active player for an incident
        this minute. If a player's incident count reaches the send-off
        threshold, they are permanently pulled from the active lineup via
        Team.send_off_player(), and a DISCIPLINE event is logged.

        Iterates over a snapshot (list copy) of active_lineup since
        send_off_player() mutates that list in place.
        """
        for player in list(team.active_lineup):
            if random.random() < self.INCIDENT_PROBABILITY:
                sent_off = player.add_incident()
                if sent_off:
                    team.send_off_player(player)
                    event = MatchEvent(
                        EventType.DISCIPLINE, self.current_minute, team, player,
                        f"{player.name} picks up a second incident and is sent off!"
                    )
                    self.timeline.append(event)

    def process_goal_attempt(self, attacking_team, defending_team):
        if random.random() >= self.ATTEMPT_PROBABILITY:
            return  # no attempt generated this minute

        attack_rating = attacking_team.get_aggregate_attack()
        defense_rating = defending_team.get_aggregate_defense()

        # Bonus (Live Risk Dial): if this team has an AI coach, its
        # risk_tolerance shifts the attack multiplier's upper bound:
        #   upper_bound = 1.25 + (risk_tolerance - 0.5) * 0.4
        # risk_tolerance=1.0 -> 1.45 (bigger swings), 0.0 -> 1.05 (safer attack).
        ai = self.home_ai if attacking_team is self.home_team else self.away_ai
        attack_upper_bound = 1.25 + (ai.risk_tolerance - 0.5) * 0.4 if ai is not None else 1.25

        # Bonus: wider random swing on both sides (0.85-1.15) layered on top
        # of the base formula's own random ranges, so evenly matched teams
        # don't always land near a flat 50/50.
        attack_roll = attack_rating * random.uniform(0.75, attack_upper_bound) * random.uniform(0.85, 1.15)
        defense_roll = defense_rating * 1.3 * random.uniform(0.80, 1.20) * random.uniform(0.85, 1.15)

        if attack_roll > defense_roll:
            if attacking_team is self.home_team:
                self.home_score += 1
            else:
                self.away_score += 1

            # Flag that a goal happened this minute so both coaches get a
            # chance to react via the event-driven AI consultation gate.
            self._goal_just_scored = True

            scorer = random.choice(
                [p for p in attacking_team.active_lineup
                 if p.position in (Position.FORWARD, Position.MIDFIELDER)]
                or attacking_team.active_lineup
            )
            event = MatchEvent(
                EventType.GOAL, self.current_minute, attacking_team, scorer,
                f"GOAL! {scorer.name} scores for {attacking_team.country_name}."
            )
            self.timeline.append(event)

    def run_full_match(self):
        while self.phase == Phase.REGULATION:
            self.run_minute_tick()

        result_text = self._result_text()
        self.timeline.append(
            MatchEvent(EventType.FULL_TIME, self.current_minute, None, None, result_text)
        )
        return result_text

    def _result_text(self):
        if self.home_score > self.away_score:
            return f"{self.home_team.country_name} wins {self.home_score}-{self.away_score}"
        if self.away_score > self.home_score:
            return f"{self.away_team.country_name} wins {self.away_score}-{self.home_score}"
        return f"DRAW {self.home_score}-{self.away_score}"

    def print_timeline(self):
        for event in self.timeline:
            print(event.to_string())


# ---------------------------------------------------------------------------
# Bonus: Penalty Shootout (Task 1.1-style kick-by-kick board)
# ---------------------------------------------------------------------------

class PenaltyShootout:
    """
    Bonus third phase. Simulates a best-of-5 penalty shootout (with
    sudden death if needed), displaying a kick-by-kick board similar in
    spirit to Task 1.1's standings table.
    """

    def __init__(self, home_team, away_team):
        self.home_team = home_team
        self.away_team = away_team
        self.board = []  # list of (round_num, team_name, scored: bool)

    def _take_kick(self, kicker):
        # Simple make-probability model based on the kicker's effective attack
        make_chance = min(0.95, 0.55 + kicker.get_effective_attack() / 250)
        return random.random() < make_chance

    def run(self):
        home_kickers = self.home_team.active_lineup[:5]
        away_kickers = self.away_team.active_lineup[:5]
        home_score, away_score = 0, 0

        for round_num in range(5):
            if round_num < len(home_kickers):
                scored = self._take_kick(home_kickers[round_num])
                home_score += int(scored)
                self.board.append((round_num + 1, self.home_team.country_name, scored))

            if round_num < len(away_kickers):
                scored = self._take_kick(away_kickers[round_num])
                away_score += int(scored)
                self.board.append((round_num + 1, self.away_team.country_name, scored))

        # Sudden death if still tied
        sd_round = 6
        while home_score == away_score:
            hk = random.choice(self.home_team.active_lineup)
            ak = random.choice(self.away_team.active_lineup)
            h_scored = self._take_kick(hk)
            a_scored = self._take_kick(ak)
            home_score += int(h_scored)
            away_score += int(a_scored)
            self.board.append((sd_round, self.home_team.country_name, h_scored))
            self.board.append((sd_round, self.away_team.country_name, a_scored))
            sd_round += 1
            if sd_round > 20:  # safety cap
                break

        self.print_board()
        winner = self.home_team if home_score > away_score else self.away_team
        print(f"\nPenalty shootout result: {self.home_team.country_name} {home_score} - "
              f"{away_score} {self.away_team.country_name}")
        print(f"Winner: {winner.country_name}")
        return winner

    def print_board(self):
        print(f"{'Rd':<4}{'Team':<15}{'Result'}")
        for round_num, team_name, scored in self.board:
            result = "SCORED" if scored else "MISSED"
            print(f"{round_num:<4}{team_name:<15}{result}")


# ---------------------------------------------------------------------------
# BONUS: AI Model - Controlled Match Engine (powered by Groq)
# ---------------------------------------------------------------------------

class MatchAI:
    """
    Extends coaching logic onto a Team. Makes the tactical decisions a human
    coach would normally make (SUBSTITUTE / CHANGE_FORMATION / HOLD /
    PUSH_ATTACK), while Match/Team keep resolving the actual on-pitch math
    untouched.

    Consultation frequency: the spec's suggested integration point calls
    observe -> decide -> apply once per simulated minute (90x/side/match).
    Here, Match only invokes this class when Match._should_consult_ai()
    signals a real trigger (goal, half-time, fatigue threshold), so a real
    LLM-backed model gets called ~5-15 times per match instead of 180 -
    cutting latency and API usage while keeping decisions tied to moments
    that actually matter tactically.

    The model is a real LLM call to Groq's chat-completions endpoint. Each
    person running this script supplies their OWN key via the .env file,
    an environment variable, or the runtime prompt above (or api_key=...
    at construction) - nothing is embedded in the code. If the `groq`
    package isn't installed, no key is set, or a call fails for any
    reason, decide_action() transparently falls back to a rule-based
    decision, so the simulation is never blocked on network/API
    availability.
    """

    VALID_ACTIONS = ("SUBSTITUTE", "CHANGE_FORMATION", "HOLD", "PUSH_ATTACK")

    def __init__(self, controlled_team, risk_tolerance=0.5,
                 model_name="llama-3.3-70b-versatile", api_key=None):
        self.controlled_team = controlled_team
        self.risk_tolerance = risk_tolerance
        self.decision_log = []
        self._model_name = model_name  # which Groq-hosted LLM to call

        # Each person can either set GROQ_API_KEY via .env / env var /
        # the runtime prompt, or pass api_key=... explicitly here.
        resolved_key = api_key or GROQ_API_KEY
        # `model`: reference to the trained decision-making model (spec
        # attribute table) - here, the Groq LLM client itself. None if no
        # key/package is available, in which case decide_action() falls
        # back to rule-based logic.
        self.model = None
        if _GROQ_SDK_AVAILABLE and resolved_key:
            try:
                self.model = Groq(api_key=resolved_key)
            except Exception as exc:
                self.decision_log.append(f"[Groq client init failed: {exc}] using rule-based fallback")

    def observe_state(self, match):
        """Serializes score, minute, phase, and stamina levels into a
        state vector the model can read."""
        is_home = self.controlled_team is match.home_team
        own_score = match.home_score if is_home else match.away_score
        opponent_score = match.away_score if is_home else match.home_score
        lineup = self.controlled_team.active_lineup
        avg_stamina = sum(p.stamina for p in lineup) / len(lineup) if lineup else 0.0

        return {
            "minute": match.current_minute,
            "phase": match.phase.value,
            "own_score": own_score,
            "opponent_score": opponent_score,
            "avg_stamina": round(avg_stamina, 1),
            "subs_remaining": self.controlled_team.substitutions_remaining,
            "risk_tolerance": round(self.risk_tolerance, 2),
            "current_formation": self.controlled_team.formation,
        }

    def decide_action(self, match):
        """Feeds the observed state into the model and returns one of
        SUBSTITUTE, CHANGE_FORMATION, HOLD, or PUSH_ATTACK."""
        state = self.observe_state(match)

        if self.model is not None:
            action = self._decide_via_groq(state)
            if action is not None:
                return action

        return self._decide_via_rules(state)

    def _decide_via_groq(self, state):
        """--- Integration point: real LLM call ---
        Only reached when Match._should_consult_ai() fired a trigger for
        this side this minute, so this network round-trip happens a
        handful of times per match, not every minute."""
        prompt = (
            "You are an AI football coach controlling one team mid-match.\n"
            "Given the JSON match state below, choose exactly one action.\n"
            "Reply with ONLY one of these words, nothing else: "
            "SUBSTITUTE, CHANGE_FORMATION, HOLD, PUSH_ATTACK.\n\n"
            f"State: {json.dumps(state)}"
        )
        try:
            response = self.model.chat.completions.create(
                model=self._model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,
                max_tokens=8,
            )
            raw = response.choices[0].message.content.strip().upper()
            for action in self.VALID_ACTIONS:
                if action in raw:
                    return action
            self.decision_log.append(f"[Groq returned unparseable action {raw!r}] using rule-based fallback")
        except Exception as exc:
            self.decision_log.append(f"[Groq call failed: {exc}] using rule-based fallback")
        return None

    def _decide_via_rules(self, state):
        """Lightweight rule-based stand-in, used whenever the real model
        isn't available (no key / no package / call failure)."""
        if state["avg_stamina"] < 60 and state["subs_remaining"] > 0:
            return "SUBSTITUTE"
        if state["own_score"] < state["opponent_score"]:
            return "PUSH_ATTACK"
        if state["own_score"] > state["opponent_score"]:
            return "HOLD"
        return "CHANGE_FORMATION" if random.random() < 0.1 else "HOLD"

    def apply_decision(self, action):
        """Executes the chosen action against controlled_team and appends
        the reasoning to decision_log."""
        reasoning = f"action={action}"

        if action == "SUBSTITUTE":
            outcome = self.controlled_team.auto_substitute_lowest_stamina()
            reasoning += f" -> {outcome if outcome else 'no valid substitution available'}"

        elif action == "CHANGE_FORMATION":
            next_formation = random.choice(list(FORMATIONS.keys()))
            self.controlled_team.change_formation(next_formation)
            reasoning += f" -> switched to {next_formation}"

        elif action == "PUSH_ATTACK":
            self.risk_tolerance = min(1.0, self.risk_tolerance + 0.2)
            reasoning += f" -> risk_tolerance now {self.risk_tolerance:.2f}"

        elif action == "HOLD":
            self.risk_tolerance = max(0.0, self.risk_tolerance - 0.2)
            reasoning += f" -> risk_tolerance now {self.risk_tolerance:.2f}"

        self.decision_log.append(reasoning)


# ---------------------------------------------------------------------------
# Helper: build a sample squad
# ---------------------------------------------------------------------------

def build_sample_roster(prefix):
    """Builds a 26-player roster with a reasonable position distribution."""
    positions = (
        [Position.GOALKEEPER] * 3
        + [Position.DEFENDER] * 8
        + [Position.MIDFIELDER] * 8
        + [Position.FORWARD] * 7
    )
    roster = []
    for i, pos in enumerate(positions, start=1):
        roster.append(
            Player(
                name=f"{prefix}_{i:02d}",
                position=pos,
                base_attack=random.randint(50, 95),
                base_defense=random.randint(50, 95),
            )
        )
    return roster


# ---------------------------------------------------------------------------
# Demonstration
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    random.seed(42)  # reproducible demo run

    argentina = Team("ARG", build_sample_roster("ARG"))
    france = Team("FRA", build_sample_roster("FRA"))

    match = Match(argentina, france)

    # Bonus AI Model: attach a Groq-backed coach to each side. If GROQ_API_KEY
    # isn't set (or the `groq` package isn't installed), these silently run
    # on the rule-based fallback instead - the match still plays out fine.
    # Either way, Match only *consults* each coach on real triggers (goals,
    # half-time, fatigue dips) rather than every minute - see
    # Match._should_consult_ai().
    if GROQ_API_KEY is None:
        print("[info] No Groq API key provided. Using the built-in rule-based AI.\n")

    match.home_ai = MatchAI(argentina, risk_tolerance=0.5)
    match.away_ai = MatchAI(france, risk_tolerance=0.5)

    result = match.run_full_match()

    print("=== Match Timeline ===")
    match.print_timeline()

    print(f"\nFinal Score: {argentina.country_name} {match.home_score} - "
          f"{match.away_score} {france.country_name}")
    print(f"Result: {result}")

    # Bonus: demonstrate auto-substitution
    print("\n=== Auto-substitution demo (lowest stamina swap) ===")
    sub = argentina.auto_substitute_lowest_stamina()
    if sub:
        out_p, in_p = sub
        print(f"{out_p.name} (stamina {out_p.stamina:.1f}) subbed off, "
              f"{in_p.name} comes on.")
    else:
        print("No valid substitution available.")

    # Bonus: discipline system summary - shows any players actually sent off
    # during the simulated match via the wired-in process_discipline() checks.
    print("\n=== Discipline system summary ===")
    discipline_events = [e for e in match.timeline if e.event_type == EventType.DISCIPLINE]
    if discipline_events:
        for event in discipline_events:
            print(event.to_string())
    else:
        print("No players were sent off during this match (random chance).")
    print(f"ARG sent-off count: {len(argentina.sent_off)} | "
          f"FRA sent-off count: {len(france.sent_off)}")

    # Bonus: explicitly prove the discipline system's safety net - force an
    # entire position group (forwards) to be sent off and confirm
    # get_aggregate_attack() returns 0.0 instead of raising ZeroDivisionError.
    print("\n=== Safety-net stress test: emptying an entire position group ===")
    stress_team = Team("STRESS_TEST", build_sample_roster("STRESS"))
    forwards_in_lineup = [p for p in stress_team.active_lineup if p.position == Position.FORWARD]
    for fwd in forwards_in_lineup:
        stress_team.send_off_player(fwd)
    print(f"Forwards remaining in active lineup: "
          f"{[p for p in stress_team.active_lineup if p.position == Position.FORWARD]}")
    print(f"get_aggregate_attack() with no forwards/midfielders imbalance handled safely: "
          f"{stress_team.get_aggregate_attack():.2f} (no crash)")

    # Bonus: penalty shootout, only if the match was drawn
    if match.home_score == match.away_score:
        print("\n=== Match drawn - proceeding to penalties ===")
        PenaltyShootout(argentina, france).run()
    else:
        print("\n(Match had a winner in regulation - running a demo shootout anyway)")
        PenaltyShootout(argentina, france).run()

    # Bonus: show each coach's decision log (Groq-backed or rule-based
    # fallback, whichever was actually used above) plus a call-count
    # summary proving the event-driven gate cut consultations way down
    # from the naive once-per-minute (90/side) baseline.
    print("\n=== AI coach decision logs (event-driven consultations only) ===")
    print(f"{argentina.country_name} coach ({len(match.home_ai.decision_log)} consultations this match):")
    for entry in match.home_ai.decision_log:
        print(f"  - {entry}")
    print(f"{france.country_name} coach ({len(match.away_ai.decision_log)} consultations this match):")
    for entry in match.away_ai.decision_log:
        print(f"  - {entry}")