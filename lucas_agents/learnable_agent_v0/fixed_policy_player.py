import json
import os

from pypokerengine.players import BasePokerPlayer

from lucas_agents.learnable_agent_v0.learnable_cfr_player import (
    ACTIONS,
    DEFAULT_POLICY_PATH,
    LearnableCFRPlayer,
    _baseline_action,
)


DEFAULT_FIXED_POLICY_PATH = os.path.join(
    os.path.dirname(__file__), "fixed_policy_snapshot.json"
)


def _read_json(path, default_value):
  if not os.path.exists(path):
    return default_value
  with open(path, "r", encoding="utf-8") as source:
    return json.load(source)


class FixedPolicyLearnablePlayer(LearnableCFRPlayer):
  """Inference-only snapshot opponent for self-play training.

  This player loads a frozen copy of the learnable CFR average strategy and does
  not update regrets or write any files during play.
  """

  def __init__(self, policy_path=None, min_use_strategy_visits=1):
    self._fixed_policy_path = policy_path or DEFAULT_FIXED_POLICY_PATH
    super().__init__(
        policy_path=self._fixed_policy_path,
        coverage_path=os.path.join(os.path.dirname(__file__), "training_coverage.json"),
        exploration=0.0,
        training_enabled=False,
        save_interval=10**9,
        baseline_prior_weight=0.30,
        baseline_assist=0.0,
        min_use_strategy_visits=min_use_strategy_visits,
        discount_interval=0,
        discount_factor=1.0,
        random_seed=0,
    )

  def _load_policy(self):
    policy_payload = _read_json(self._fixed_policy_path, {"strategy_sum": {}})
    self.regret_sum = {}
    self.strategy_sum = policy_payload.get("strategy_sum", {})
    self.state_visits = {
        key: self.min_use_strategy_visits for key in self.strategy_sum.keys()
    }
    self.state_examples = {}

  def save_policy(self):
    return

  def finish_game(self, final_seats, small_blind_amount):
    return

  def declare_action(self, valid_actions, hole_card, round_state):
    self._sync_round_state(round_state)
    legal_actions = {entry["action"] for entry in valid_actions}
    baseline_action = _baseline_action(self, valid_actions, hole_card, round_state)
    info_key, _ = self._build_info_set(hole_card, round_state)
    average_strategy = self._average_strategy(info_key, legal_actions)
    if average_strategy:
      return max(average_strategy, key=average_strategy.get)
    return baseline_action


def setup_ai():
  return FixedPolicyLearnablePlayer()
