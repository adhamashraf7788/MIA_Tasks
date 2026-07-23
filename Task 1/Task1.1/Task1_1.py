# Teams and matches representation
TEAMS = ["ARG", "MEX", "POL", "KSA"]

MATCHUPS = [
    ("ARG", "MEX"),
    ("ARG", "POL"),
    ("ARG", "KSA"),
    ("MEX", "POL"),
    ("MEX", "KSA"),
    ("POL", "KSA"),
]

standings = {
    team: {"P": 0, "W": 0, "D": 0, "L": 0, "GF": 0, "GA": 0, "GD": 0, "Pts": 0}
    for team in TEAMS
}

# Stores the head-to-head result between every pair of teams.
# Key: frozenset({team1, team2}) so (ARG, POL) and (POL, ARG) map to the same match.
head_to_head = {}


def process_match(standings, team1, team2, team1_goals, team2_goals):
    """Updates both teams' stats for a single match."""
    standings[team1]["P"] += 1
    standings[team2]["P"] += 1

    standings[team1]["GF"] += team1_goals
    standings[team2]["GF"] += team2_goals
    standings[team1]["GA"] += team2_goals
    standings[team2]["GA"] += team1_goals

    if team1_goals > team2_goals:
        standings[team1]["W"] += 1
        standings[team1]["Pts"] += 3
        standings[team2]["L"] += 1
        winner = team1
    elif team1_goals < team2_goals:
        standings[team2]["W"] += 1
        standings[team2]["Pts"] += 3
        standings[team1]["L"] += 1
        winner = team2
    else:
        standings[team1]["D"] += 1
        standings[team1]["Pts"] += 1
        standings[team2]["D"] += 1
        standings[team2]["Pts"] += 1
        winner = None  # Draw

    standings[team1]["GD"] = standings[team1]["GF"] - standings[team1]["GA"]
    standings[team2]["GD"] = standings[team2]["GF"] - standings[team2]["GA"]

    # Record head-to-head result for the tiebreak
    head_to_head[frozenset((team1, team2))] = {
        "winner": winner,
        team1: team1_goals,
        team2: team2_goals,
    }


def get_score_input(team1, team2):
    """Prompts user to enter scores in 'X-Y' format with input validation."""
    while True:
        raw = input(f"Enter score for {team1} vs {team2} (format: 2-0): ").strip()
        parts = raw.split("-")
        if len(parts) != 2:
            print("  Invalid format. Please use 'X-Y', e.g. 2-0.")
            continue
        try:
            g1, g2 = int(parts[0]), int(parts[1])
        except ValueError:
            print("  Scores must be whole numbers, e.g. 2-0.")
            continue
        if g1 < 0 or g2 < 0:
            print("  Scores can't be negative.")
            continue
        return g1, g2


def head_to_head_result(team_a, team_b):
    """
    Returns:
      1 if team_a won against team_b
     -1 if team_b won against team_a
      0 if there was a draw
    """
    match = head_to_head.get(frozenset((team_a, team_b)))
    if not match:
        return 0
    if match["winner"] == team_a:
        return 1
    if match["winner"] == team_b:
        return -1
    return 0


def apply_head_to_head(sorted_teams, standings):
    """Finds consecutive teams tied on Points and GD, then applies H2H and GF fallbacks."""
    i = 0

    while i < len(sorted_teams):
        j = i

        # Group teams tied on Points AND Goal Difference
        tie_key = (
            standings[sorted_teams[i]]["Pts"],
            standings[sorted_teams[i]]["GD"],
        )

        while (
            j + 1 < len(sorted_teams)
            and (
                standings[sorted_teams[j + 1]]["Pts"],
                standings[sorted_teams[j + 1]]["GD"],
            ) == tie_key
        ):
            j += 1

        tied_group = sorted_teams[i : j + 1]

        # Apply head-to-head rule only when exactly two teams are tied
        if len(tied_group) == 2:
            team1, team2 = tied_group
            h2h = head_to_head_result(team1, team2)

            # team2 won head-to-head -> swap
            if h2h < 0:
                sorted_teams[i], sorted_teams[i + 1] = (
                    sorted_teams[i + 1],
                    sorted_teams[i],
                )
            # Tied on head-to-head -> fall back to Goals Scored (GF)
            elif h2h == 0:
                if standings[team2]["GF"] > standings[team1]["GF"]:
                    sorted_teams[i], sorted_teams[i + 1] = (
                        sorted_teams[i + 1],
                        sorted_teams[i],
                    )

        i = j + 1

    return sorted_teams


def sort_teams(standings):
    """
    Sorts teams according to FIFA criteria:
      1. Points (desc)
      2. Goal Difference (desc)
      3. Head-to-head result (if exactly 2 teams tied)
      4. Goals Scored (desc)
    """
    # Base sort by Points, GD, and GF
    teams_sorted = sorted(
        standings.keys(),
        key=lambda t: (
            -standings[t]["Pts"],
            -standings[t]["GD"],
            -standings[t]["GF"],
        ),
    )

    # Apply H2H tiebreak pass for pairs tied on Pts and GD
    return apply_head_to_head(teams_sorted, standings)


def print_standings(standings):
    """Prints the standings table in neatly aligned columns."""
    teams_sorted = sort_teams(standings)

    headers = ["Team", "P", "W", "D", "L", "GF", "GA", "GD", "Pts"]
    print(
        f"{headers[0]:<6}{headers[1]:>3}{headers[2]:>3}{headers[3]:>3}"
        f"{headers[4]:>3}{headers[5]:>4}{headers[6]:>4}{headers[7]:>5}{headers[8]:>5}"
    )

    for team in teams_sorted:
        s = standings[team]
        gd = s["GD"]
        gd_str = f"+{gd}" if gd > 0 else (f"{gd}" if gd < 0 else "0")
        print(
            f"{team:<6}{s['P']:>3}{s['W']:>3}{s['D']:>3}{s['L']:>3}"
            f"{s['GF']:>4}{s['GA']:>4}{gd_str:>5}{s['Pts']:>5}"
        )


def run_gf_tiebreak_demo():
    """Demo 1: Points + GD tie -> resolved by Goals Scored (GF)."""
    print("DEMO 1: Points + GD tie -> resolved by Goals Scored (GF)")

    demo_standings = {
        "EGY": {"P": 3, "W": 1, "D": 2, "L": 0, "GF": 5, "GA": 2, "GD": 3, "Pts": 5},
        "BEL": {"P": 3, "W": 1, "D": 2, "L": 0, "GF": 4, "GA": 1, "GD": 3, "Pts": 5},
        "ARG": {"P": 3, "W": 1, "D": 1, "L": 1, "GF": 3, "GA": 3, "GD": 0, "Pts": 4},
        "GER": {"P": 3, "W": 0, "D": 1, "L": 2, "GF": 1, "GA": 5, "GD": -4, "Pts": 1},
    }

    print("EGY and BEL are both Pts=5, GD=+3, but EGY has GF=5 vs BEL's GF=4.")
    print("Expected order: EGY above BEL (GF breaks tie), then ARG, then GER.\n")
    print_standings(demo_standings)

    order = sort_teams(demo_standings)
    assert order[0] == "EGY" and order[1] == "BEL", "GF tiebreak failed!"
    print("\nPASS: GF tiebreak works correctly!\n")


def run_head_to_head_demo():
    """Demo 2: Pts + GD tie -> resolved by Head-to-Head."""
    print("DEMO 2: Pts + GD tie -> resolved by Head-to-Head")

    demo_standings = {
        "EGY": {"P": 3, "W": 2, "D": 0, "L": 1, "GF": 5, "GA": 3, "GD": 2, "Pts": 6},
        "BEL": {"P": 3, "W": 2, "D": 0, "L": 1, "GF": 5, "GA": 3, "GD": 2, "Pts": 6},
        "ENG": {"P": 3, "W": 1, "D": 0, "L": 2, "GF": 2, "GA": 6, "GD": -4, "Pts": 3},
    }

    head_to_head.clear()
    head_to_head[frozenset(("EGY", "BEL"))] = {"winner": "EGY", "EGY": 2, "BEL": 1}

    print("EGY and BEL are tied on Pts=6 and GD=+2. EGY beat BEL 2-1 head-to-head.")
    print("Expected order: EGY above BEL, then ENG.\n")
    print_standings(demo_standings)

    order = sort_teams(demo_standings)
    assert order[0] == "EGY" and order[1] == "BEL", "Head-to-head tiebreak failed!"
    print("\nPASS: Head-to-head tiebreak works correctly!\n")


# Main Execution
if __name__ == "__main__":
    for team1, team2 in MATCHUPS:
        g1, g2 = get_score_input(team1, team2)
        process_match(standings, team1, team2, g1, g2)

    print()
    print("=== Final Group Standings ===")
    print_standings(standings)

    head_to_head.clear()

    print("\n--------------------------------------------------\n")
    run_gf_tiebreak_demo()
    print("--------------------------------------------------\n")
    run_head_to_head_demo()