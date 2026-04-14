import argparse
import os
import sys


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
  sys.path.insert(0, PROJECT_ROOT)

from pypokerengine.api.game import setup_config, start_poker

from lucas_agents.advanced_cfr.advanced_cfr_player import AdvancedCFRPlayer
from lucas_agents.adversarial_search_mccfr.adversarial_search_mccfr_agent import (
    AdversarialSearchMCCFRAgent,
)
from lucas_agents.adversarial_search_mccfr_v2.adversarial_search_mccfr_v2_agent import (
    AdversarialSearchMCCFRV2Agent,
)
from lucas_agents.adversarial_search_mccfr_v3.adversarial_search_mccfr_v3_agent import (
    AdversarialSearchMCCFRV3Agent,
)
from lucas_agents.condition_threshold_player import ConditionThresholdPlayer
from lucas_agents.discounted_mccfr_plus.discounted_mccfr_plus_agent import DiscountedMCCFRPlusAgent
from lucas_agents.learnable_discounted_mccfr.learnable_discounted_mccfr_agent import (
    LearnableDiscountedMCCFRAgent,
)


DEFAULT_POLICY_PATH = os.path.join(
    PROJECT_ROOT,
    "lucas_agents",
    "adversarial_search_mccfr_v3",
    "adversarial_search_mccfr_v3_policy.json",
)


def parse_args():
  parser = argparse.ArgumentParser(description="Train the adaptive adversarial-search MCCFR v3 agent.")
  parser.add_argument("--games", type=int, default=360)
  parser.add_argument("--stack", type=int, default=500)
  parser.add_argument("--small-blind", type=int, default=10)
  parser.add_argument("--max-rounds-per-game", type=int, default=100)
  parser.add_argument("--policy-path", default=DEFAULT_POLICY_PATH)
  parser.add_argument("--verbose", type=int, default=0)
  return parser.parse_args()


def build_opponent(game_index, policy_path):
  if game_index % 17 == 0:
    return AdversarialSearchMCCFRV3Agent(policy_path=policy_path, training_enabled=False, exploration=0.0)
  if game_index % 13 == 0:
    return AdversarialSearchMCCFRV2Agent(training_enabled=False, exploration=0.0)
  if game_index % 11 == 0:
    return LearnableDiscountedMCCFRAgent(training_enabled=False, exploration=0.0)
  if game_index % 7 == 0:
    return AdversarialSearchMCCFRAgent(training_enabled=False, exploration=0.0)
  if game_index % 5 == 0:
    return DiscountedMCCFRPlusAgent(training_enabled=False, exploration=0.0)
  if game_index % 2 == 0:
    return ConditionThresholdPlayer()
  return AdvancedCFRPlayer(training_enabled=False, exploration=0.0)


def main():
  args = parse_args()
  learner = AdversarialSearchMCCFRV3Agent(policy_path=args.policy_path, training_enabled=True)
  total_rounds = 0

  for game_index in range(1, args.games + 1):
    opponent = build_opponent(game_index, args.policy_path)
    config = setup_config(
        max_round=args.max_rounds_per_game,
        initial_stack=args.stack,
        small_blind_amount=args.small_blind,
    )
    config.register_player(name="adversarial_search_mccfr_v3", algorithm=learner)
    config.register_player(name="opponent", algorithm=opponent)
    result = start_poker(config, verbose=args.verbose)
    if learner.round_count <= 0:
      raise RuntimeError("Training ended before any rounds were completed.")
    total_rounds += learner.round_count
    print(
        f"game={game_index}/{args.games} rounds_played={learner.round_count} total_rounds={total_rounds} "
        f"stack={next(player['stack'] for player in result['players'] if player['name'] == 'adversarial_search_mccfr_v3')}"
    )

  learner.save_policy()
  print(f"saved_policy={args.policy_path}")


if __name__ == "__main__":
  main()
