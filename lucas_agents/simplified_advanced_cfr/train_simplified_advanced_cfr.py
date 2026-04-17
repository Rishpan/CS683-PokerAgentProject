import argparse
import os
import sys


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
  sys.path.insert(0, PROJECT_ROOT)

from pypokerengine.api.game import setup_config, start_poker

from lucas_agents.advanced_cfr.advanced_cfr_player import AdvancedCFRPlayer
from lucas_agents.condition_threshold_player import ConditionThresholdPlayer
from lucas_agents.simplified_advanced_cfr.simplified_advanced_cfr_player import (
    STATS_PATH,
    TRACE_PATH,
)
from randomplayer import RandomPlayer


DEFAULT_POLICY_PATH = os.path.join(
    PROJECT_ROOT, "lucas_agents", "simplified_advanced_cfr", "advanced_cfr_policy.json"
)


def parse_args():
  parser = argparse.ArgumentParser(
      description="Train the simplified Advanced CFR runtime against a mixed pool of existing players."
  )
  parser.add_argument("--games", type=int, default=400)
  parser.add_argument("--stack", type=int, default=500)
  parser.add_argument("--small-blind", type=int, default=10)
  parser.add_argument("--max-rounds-per-game", type=int, default=100)
  parser.add_argument("--verbose", type=int, default=0)
  parser.add_argument("--exploration", type=float, default=0.04)
  parser.add_argument("--prior-weight", type=float, default=0.12)
  parser.add_argument("--save-interval", type=int, default=100)
  parser.add_argument("--discount-interval", type=int, default=500)
  parser.add_argument("--policy-path", default=DEFAULT_POLICY_PATH)
  parser.add_argument(
      "--opponents",
      nargs="+",
      default=["condition_threshold", "random", "advanced_cfr"],
      choices=["condition_threshold", "random", "advanced_cfr"],
      help="Opponent pool to rotate through during offline training.",
  )
  return parser.parse_args()


def build_opponent(name):
  if name == "condition_threshold":
    return ConditionThresholdPlayer()
  if name == "random":
    return RandomPlayer()
  if name == "advanced_cfr":
    return AdvancedCFRPlayer(training_enabled=False, exploration=0.0)
  raise ValueError(f"Unsupported opponent: {name}")


def reset_inference_artifacts():
  for path, payload in (
      (STATS_PATH, {
          "total_decisions": 0,
          "base_action_used": 0,
          "learned_action_used": 0,
          "by_street": {
              "preflop": {"base": 0, "learned": 0},
              "flop": {"base": 0, "learned": 0},
              "turn": {"base": 0, "learned": 0},
              "river": {"base": 0, "learned": 0},
          },
      }),
      (TRACE_PATH, []),
  ):
    with open(path, "w", encoding="utf-8") as output:
      import json
      json.dump(payload, output, indent=2, sort_keys=True)


def main():
  args = parse_args()
  reset_inference_artifacts()
  learner = AdvancedCFRPlayer(
      policy_path=args.policy_path,
      training_enabled=True,
      exploration=args.exploration,
      prior_weight=args.prior_weight,
      save_interval=args.save_interval,
      discount_interval=args.discount_interval,
  )

  total_rounds = 0
  for game_index in range(1, args.games + 1):
    opponent_name = args.opponents[(game_index - 1) % len(args.opponents)]
    opponent = build_opponent(opponent_name)
    config = setup_config(
        max_round=args.max_rounds_per_game,
        initial_stack=args.stack,
        small_blind_amount=args.small_blind,
    )
    config.register_player(name="simplified_advanced_cfr", algorithm=learner)
    config.register_player(name=opponent_name, algorithm=opponent)
    result = start_poker(config, verbose=args.verbose)

    if learner.round_count <= 0:
      raise RuntimeError("Training ended before any rounds were completed.")
    total_rounds += learner.round_count

    learner_stack = next(
        player["stack"] for player in result["players"] if player["name"] == "simplified_advanced_cfr"
    )
    print(
        f"game={game_index}/{args.games} opponent={opponent_name} rounds={learner.round_count} "
        f"total_rounds={total_rounds} learner_stack={learner_stack}"
    )

  learner.save_policy()
  print(f"saved_policy={args.policy_path}")


if __name__ == "__main__":
  main()
