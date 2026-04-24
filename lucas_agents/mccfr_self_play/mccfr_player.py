import os
import random
import sys
from pathlib import Path

from pypokerengine.players import BasePokerPlayer

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
  sys.path.insert(0, str(CURRENT_DIR))

from mccfr_abstraction_loader import (
    abstraction_is_compatible,
    load_abstraction,
    resolve_policy_abstraction_ref,
)
from mccfr_config import (
    DEFAULT_BOOTSTRAP_ITERATIONS,
    DEFAULT_POLICY_PATH,

)
from mccfr_tables import ACTIONS, StrategyTable


class MCCFRPlayer(BasePokerPlayer):
  def __init__(
      self,
      policy_path=None,
      random_seed=None,
      bootstrap_iterations=DEFAULT_BOOTSTRAP_ITERATIONS,
      abstraction=None,
  ):
    self.policy_path = policy_path or DEFAULT_POLICY_PATH  
    # print(f"policy_path: {self.policy_path}")
    self.random = random.Random(random_seed)
    self.bootstrap_iterations = bootstrap_iterations
    self.abstraction_ref = resolve_policy_abstraction_ref(
        {},
        explicit_abstraction_ref=abstraction,
    )
    self.tables, self.metadata = StrategyTable.load(self.policy_path)
    if bootstrap_iterations > 0 and not self.tables.has_data():
      self._bootstrap_self_training()
      self.tables, self.metadata = StrategyTable.load(self.policy_path)
    self.abstraction_ref = resolve_policy_abstraction_ref(
        self.metadata,
        explicit_abstraction_ref=abstraction,
    )
    self.abstraction = load_abstraction(self.abstraction_ref)
    if self.metadata and not abstraction_is_compatible(
        self.metadata,
        self.abstraction,
        self.abstraction_ref,
    ):
      raise ValueError(
          "Policy metadata does not match the selected abstraction. Choose the "
          "policy that belongs to that abstraction or retrain with --reset-policy."
      )
    self.postflop_simulations = self.metadata.get("postflop_simulations", 64)

  def declare_action(self, valid_actions, hole_card, round_state):
    legal_actions = {entry["action"] for entry in valid_actions}
    opponent_stats = self.abstraction.observe_opponent_actions(
        round_state["action_histories"],
        self.uuid,
    )
    info_key, _ = self.abstraction.build_info_key(
        hole_card=hole_card,
        round_state=round_state,
        player_uuid=self.uuid,
        opponent_action_stats=opponent_stats,
        postflop_simulations=self.postflop_simulations,
    )
    strategy = self.tables.average_strategy(info_key, legal_actions)
    return self._sample_action(strategy, legal_actions)

  def receive_game_start_message(self, game_info):
    pass

  def receive_round_start_message(self, round_count, hole_card, seats):
    pass

  def receive_street_start_message(self, street, round_state):
    pass

  def receive_game_update_message(self, action, round_state):
    pass

  def receive_round_result_message(self, winners, hand_info, round_state):
    del winners, hand_info, round_state
    self.tables.save_lookup_stats(self.policy_path)

  def _sample_action(self, strategy, legal_actions):
    draw = self.random.random()
    cumulative = 0.0
    fallback = "call" if "call" in legal_actions else "fold"
    for action in ACTIONS:
      probability = strategy.get(action, 0.0)
      if probability <= 0:
        continue
      cumulative += probability
      if draw <= cumulative:
        return action
    return fallback

  def _bootstrap_self_training(self):
    from mccfr_trainer import train_self_play_policy

    train_self_play_policy(
        iterations=self.bootstrap_iterations,
        policy_path=self.policy_path,
        abstraction=self.abstraction_ref if hasattr(self, "abstraction_ref") else None,
        verbose=False,
    )



def setup_ai():
  return MCCFRPlayer()
