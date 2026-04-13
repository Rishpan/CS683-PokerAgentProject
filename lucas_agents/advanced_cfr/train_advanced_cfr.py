import argparse
import os
import sys


PROJECT_ROOT = "/Users/xiaofanlu/Desktop/school/cs683/AI-Poker-Agent"
if PROJECT_ROOT not in sys.path:
  sys.path.insert(0, PROJECT_ROOT)

from pypokerengine.api.game import setup_config, start_poker

from experiment.advanced_cfr.advanced_cfr_player import AdvancedCFRPlayer
from lucas_agent.condition_threshold_player import ConditionThresholdPlayer


def parse_args():
  parser = argparse.ArgumentParser(description="Train the advanced CFR player by fixed game count.")
  parser.add_argument("--games", type=int, default=200)
  parser.add_argument("--stack", type=int, default=500)
  parser.add_argument("--small-blind", type=int, default=10)
  parser.add_argument("--max-rounds-per-game", type=int, default=100)
  parser.add_argument(
      "--policy-path",
      default=os.path.join(PROJECT_ROOT, "experiment/advanced_cfr/advanced_cfr_policy.json"),
  )
  parser.add_argument("--verbose", type=int, default=0)
  return parser.parse_args()


def build_opponent(game_index):
  if game_index % 5 == 0:
    return AdvancedCFRPlayer(training_enabled=False, exploration=0.0)
  return ConditionThresholdPlayer()


def main():
  args = parse_args()
  learner = AdvancedCFRPlayer(policy_path=args.policy_path, training_enabled=True)
  total_rounds = 0
  game_index = 0

  while game_index < args.games:
    game_index += 1
    opponent = build_opponent(game_index)
    config = setup_config(
        max_round=args.max_rounds_per_game,
        initial_stack=args.stack,
        small_blind_amount=args.small_blind,
    )
    config.register_player(name="advanced_cfr", algorithm=learner)
    config.register_player(name="opponent", algorithm=opponent)
    result = start_poker(config, verbose=args.verbose)
    if learner.round_count <= 0:
      raise RuntimeError("Training ended before any rounds were completed.")
    total_rounds += learner.round_count
    print(
        f"game={game_index}/{args.games} rounds_played={learner.round_count} total_rounds={total_rounds} "
        f"stack={next(player['stack'] for player in result['players'] if player['name'] == 'advanced_cfr')}"
    )

  learner.save_policy()
  print(f"saved_policy={args.policy_path}")


if __name__ == "__main__":
  main()
