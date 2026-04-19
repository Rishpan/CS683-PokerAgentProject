import argparse
import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
  sys.path.insert(0, str(PROJECT_ROOT))

from pypokerengine.api.game import setup_config, start_poker

from lucas_agents.condition_threshold_player import ConditionThresholdPlayer
from lucas_agents.minimum_cfr_player import MinimumCFRPlayer


DEFAULT_GAMES = 500
DEFAULT_STACK = 500
DEFAULT_BLIND = 10
DEFAULT_MAX_ROUND = 100


def parse_args():
  parser = argparse.ArgumentParser(
      description="Train the minimum CFR-style player against itself or a fixed opponent."
  )
  parser.add_argument(
      "--games",
      type=int,
      default=DEFAULT_GAMES,
      help="Number of training games to run.",
  )
  parser.add_argument(
      "--stack",
      type=int,
      default=DEFAULT_STACK,
      help="Starting stack for each player. Default 500 means $1000 total in play.",
  )
  parser.add_argument("--small-blind", type=int, default=DEFAULT_BLIND, help="Small blind amount.")
  parser.add_argument(
      "--max-round",
      type=int,
      default=DEFAULT_MAX_ROUND,
      help="Maximum rounds per game before stacks reset.",
  )
  parser.add_argument(
      "--opponent",
      choices=("self", "threshold"),
      default="threshold",
      help="Opponent type for training.",
  )
  parser.add_argument(
      "--policy-path",
      default=os.path.join(PROJECT_ROOT, "lucas_agents", "minimum_cfr_policy.json"),
      help="Where to save the learned policy JSON.",
  )
  parser.add_argument("--verbose", type=int, default=0, help="Engine verbosity level.")
  return parser.parse_args()


def build_players(args):
  learner = MinimumCFRPlayer(policy_path=args.policy_path, training_enabled=True)
  if args.opponent == "self":
    opponent = MinimumCFRPlayer(policy_path=args.policy_path, training_enabled=True)
  else:
    opponent = ConditionThresholdPlayer()
  return learner, opponent


def print_progress(current, total, width=30):
  filled = int(width * current / total)
  bar = "#" * filled + "-" * (width - filled)
  sys.stdout.write("\rProgress: [%s] %d/%d" % (bar, current, total))
  if current == total:
    sys.stdout.write("\n")
  sys.stdout.flush()


def main():
  args = parse_args()
  learner, opponent = build_players(args)
  result = None

  for game_index in range(args.games):
    config = setup_config(
        max_round=args.max_round,
        initial_stack=args.stack,
        small_blind_amount=args.small_blind,
    )
    config.register_player(name="minimum_cfr", algorithm=learner)
    config.register_player(name=args.opponent, algorithm=opponent)

    result = start_poker(config, verbose=args.verbose)
    print_progress(game_index + 1, args.games)

  learner.save_policy()

  print("Training complete")
  print("games_played: %d" % args.games)
  print("max_round_per_game: %d" % args.max_round)
  print("starting_stack_per_player: %d" % args.stack)
  print("total_chips_in_play: %d" % (args.stack * 2))
  for player in result["players"]:
    print("%s: final_stack=%d" % (player["name"], player["stack"]))
  print("saved_policy: %s" % args.policy_path)


if __name__ == "__main__":
  main()
