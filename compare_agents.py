
"""
example usage

python3 compare_agents.py lucas_agents/condition_threshold_player.py raise_player.py
"""
import argparse
import importlib.util
import sys
from pathlib import Path

from pypokerengine.api.game import setup_config, start_poker


DEFAULT_GAMES = 100
DEFAULT_STACK = 500
DEFAULT_BLIND = 10
DEFAULT_MAX_ROUND = 100


def load_player(script_path, module_name):
    path = Path(script_path).resolve()
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ValueError("Cannot load player script: %s" % path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not hasattr(module, "setup_ai"):
        raise ValueError("Player script must define setup_ai(): %s" % path)
    return module.setup_ai()


def run_match(player_a_path, player_b_path, max_round, initial_stack, small_blind):
    config = setup_config(
        max_round=max_round,
        initial_stack=initial_stack,
        small_blind_amount=small_blind,
    )
    player_a = load_player(player_a_path, "compare_player_a")
    player_b = load_player(player_b_path, "compare_player_b")
    config.register_player(name="player_a", algorithm=player_a)
    config.register_player(name="player_b", algorithm=player_b)
    result = start_poker(config, verbose=0)
    players = sorted(result["players"], key=lambda seat: seat["stack"], reverse=True)
    return players


def compare(player_a_path, player_b_path, games, max_round, initial_stack, small_blind):
    summary = {
        "player_a": {
            "label": "Player A (%s)" % Path(player_a_path).name,
            "wins": 0,
            "ties": 0,
            "total_stack": 0,
        },
        "player_b": {
            "label": "Player B (%s)" % Path(player_b_path).name,
            "wins": 0,
            "ties": 0,
            "total_stack": 0,
        },
    }

    for game_index in range(games):
        players = run_match(player_a_path, player_b_path, max_round, initial_stack, small_blind)
        top_stack = players[0]["stack"]
        winners = [player for player in players if player["stack"] == top_stack]

        for player in players:
            summary[player["name"]]["total_stack"] += player["stack"]

        if len(winners) == 1:
            summary[winners[0]["name"]]["wins"] += 1
        else:
            for winner in winners:
                summary[winner["name"]]["ties"] += 1

        print_progress(game_index + 1, games)

    return summary


def print_progress(current, total, width=30):
    filled = int(width * current / total)
    bar = "#" * filled + "-" * (width - filled)
    sys.stdout.write("\rProgress: [%s] %d/%d" % (bar, current, total))
    if current == total:
        sys.stdout.write("\n")
    sys.stdout.flush()


def print_summary(summary, games, max_round, initial_stack, small_blind):
    print("Head-to-head comparison")
    print("Games: %d | Max rounds/game: %d | Starting stack: $%d | Small blind: $%d" % (
        games, max_round, initial_stack, small_blind
    ))
    print("")
    print("%-35s %8s %8s %14s" % ("Player", "Wins", "Ties", "Avg Final Stack"))
    print("-" * 70)
    for _, stats in sorted(summary.items(), key=lambda item: (-item[1]["wins"], -item[1]["total_stack"])):
        avg_stack = float(stats["total_stack"]) / games
        print("%-35s %8d %8d %14.2f" % (stats["label"], stats["wins"], stats["ties"], avg_stack))


def main():
    parser = argparse.ArgumentParser(description="Run repeated poker games between two player scripts.")
    parser.add_argument("player_a")
    parser.add_argument("player_b")
    parser.add_argument("--games", type=int, default=DEFAULT_GAMES)
    parser.add_argument("--max-round", type=int, default=DEFAULT_MAX_ROUND)
    parser.add_argument("--initial-stack", type=int, default=DEFAULT_STACK)
    parser.add_argument("--small-blind", type=int, default=DEFAULT_BLIND)
    args = parser.parse_args()

    summary = compare(
        args.player_a,
        args.player_b,
        args.games,
        args.max_round,
        args.initial_stack,
        args.small_blind,
    )
    print_summary(summary, args.games, args.max_round, args.initial_stack, args.small_blind)


if __name__ == "__main__":
    main()
