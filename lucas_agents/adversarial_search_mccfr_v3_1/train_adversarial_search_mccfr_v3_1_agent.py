import argparse
import os
import sys


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
  sys.path.insert(0, PROJECT_ROOT)

from pypokerengine.api.game import setup_config, start_poker

from lucas_agents.advanced_cfr.advanced_cfr_player import AdvancedCFRPlayer
from lucas_agents.adversarial_search_mccfr_v2.adversarial_search_mccfr_v2_agent import (
    AdversarialSearchMCCFRV2Agent,
)
from lucas_agents.adversarial_search_mccfr_v3_1.adversarial_search_mccfr_v3_1_agent import (
    AdversarialSearchMCCFRV31Agent,
)
from lucas_agents.condition_threshold_player import ConditionThresholdPlayer
from lucas_agents.learnable_discounted_mccfr.learnable_discounted_mccfr_agent import (
    LearnableDiscountedMCCFRAgent,
)


DEFAULT_POLICY_PATH = os.path.join(
    PROJECT_ROOT,
    "lucas_agents",
    "adversarial_search_mccfr_v3_1",
    "adversarial_search_mccfr_v3_1_policy.json",
)

MIXED_POOL = (
    ("condition_threshold_player", lambda _: ConditionThresholdPlayer()),
    ("advanced_cfr_player", lambda _: AdvancedCFRPlayer(training_enabled=False, exploration=0.0)),
    ("learnable_discounted_mccfr_agent", lambda _: LearnableDiscountedMCCFRAgent(training_enabled=False, exploration=0.0)),
    ("adversarial_search_mccfr_v2_agent", lambda _: AdversarialSearchMCCFRV2Agent(training_enabled=False, exploration=0.0)),
    ("advanced_cfr_player", lambda _: AdvancedCFRPlayer(training_enabled=False, exploration=0.0)),
    ("condition_threshold_player", lambda _: ConditionThresholdPlayer()),
)


def parse_args():
  parser = argparse.ArgumentParser(
      description="Train the regularized adversarial-search MCCFR v3.1 agent against a mixed opponent pool."
  )
  parser.add_argument("--games", type=int, default=480)
  parser.add_argument("--stack", type=int, default=500)
  parser.add_argument("--small-blind", type=int, default=10)
  parser.add_argument("--max-rounds-per-game", type=int, default=100)
  parser.add_argument("--policy-path", default=DEFAULT_POLICY_PATH)
  parser.add_argument("--verbose", type=int, default=0)
  return parser.parse_args()


def build_opponent(game_index, policy_path):
  del policy_path
  _, factory = MIXED_POOL[(game_index - 1) % len(MIXED_POOL)]
  return factory(None)


def main():
  args = parse_args()
  learner = AdversarialSearchMCCFRV31Agent(policy_path=args.policy_path, training_enabled=True)
  total_rounds = 0

  for game_index in range(1, args.games + 1):
    opponent_label, _ = MIXED_POOL[(game_index - 1) % len(MIXED_POOL)]
    opponent = build_opponent(game_index, args.policy_path)
    config = setup_config(
        max_round=args.max_rounds_per_game,
        initial_stack=args.stack,
        small_blind_amount=args.small_blind,
    )
    config.register_player(name="adversarial_search_mccfr_v3_1", algorithm=learner)
    config.register_player(name="opponent", algorithm=opponent)
    result = start_poker(config, verbose=args.verbose)
    if learner.round_count <= 0:
      raise RuntimeError("Training ended before any rounds were completed.")
    total_rounds += learner.round_count
    learner_stack = next(
        player["stack"] for player in result["players"] if player["name"] == "adversarial_search_mccfr_v3_1"
    )
    print(
        f"game={game_index}/{args.games} opponent={opponent_label} rounds_played={learner.round_count} "
        f"total_rounds={total_rounds} stack={learner_stack}"
    )

  learner.save_policy()
  print(f"saved_policy={args.policy_path}")


if __name__ == "__main__":
  main()
