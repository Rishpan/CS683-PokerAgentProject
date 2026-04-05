import json
import os
import random
from copy import deepcopy

from pypokerengine.players import BasePokerPlayer

from experiment.regret_minimization_research.abstraction import (
    compress_action_history,
    make_info_set_key,
)


class MinimumCFRPlayer(BasePokerPlayer):
  """
  Minimal learnable poker agent using regret matching over abstract information sets.

  This is not full-game exact CFR for Texas Hold'em. Instead, it uses:
  - coarse information-set abstraction
  - regret-matching action selection
  - online regret updates from sampled play
  - persistent parameters saved to disk

  Learnable parameters:
  - regret_sum[info_set][action]
  - strategy_sum[info_set][action]
  """

  ACTIONS = ("fold", "call", "raise")
  STREET_WEIGHT = {
      "preflop": 0.55,
      "flop": 0.75,
      "turn": 0.9,
      "river": 1.0,
  }

  def __init__(
      self,
      policy_path=None,
      exploration=0.08,
      training_enabled=True,
      save_interval=50,
      postflop_simulations=48,
      random_seed=None,
  ):
    self.policy_path = policy_path or os.path.join(
        os.path.dirname(__file__), "minimum_cfr_policy.json"
    )
    self.exploration = exploration
    self.training_enabled = training_enabled
    self.save_interval = max(1, save_interval)
    self.postflop_simulations = postflop_simulations
    self.random = random.Random(random_seed)

    self.regret_sum = {}
    self.strategy_sum = {}
    self.round_decisions = []
    self.round_start_stack = 0
    self.round_count = 0
    self.player_num = 2

    self._load_policy()

  def declare_action(self, valid_actions, hole_card, round_state):
    legal_actions = {action["action"] for action in valid_actions}
    info_key, features = self._build_info_set(hole_card, round_state)

    strategy = self._current_strategy(info_key, legal_actions)
    action = self._sample_action(strategy)

    if self.training_enabled:
      self.round_decisions.append(
          {
              "info_key": info_key,
              "strategy": deepcopy(strategy),
              "legal_actions": sorted(legal_actions),
              "chosen_action": action,
              "features": features,
          }
      )

    return action

  def receive_game_start_message(self, game_info):
    self.player_num = game_info["player_num"]

  def receive_round_start_message(self, round_count, hole_card, seats):
    del hole_card
    self.round_count = round_count
    self.round_decisions = []
    self.round_start_stack = self._stack_from_seats(seats)

  def receive_street_start_message(self, street, round_state):
    del street
    del round_state

  def receive_game_update_message(self, action, round_state):
    del action
    del round_state

  def receive_round_result_message(self, winners, hand_info, round_state):
    del winners
    del hand_info

    if not self.training_enabled or not self.round_decisions:
      return

    final_stack = self._my_stack(round_state)
    chip_delta = final_stack - self.round_start_stack
    normalizer = max(round_state["small_blind_amount"] * 4, 1)
    normalized_reward = max(-1.0, min(1.0, float(chip_delta) / normalizer))

    for decision in self.round_decisions:
      self._apply_regret_update(decision, normalized_reward)

    if self.round_count % self.save_interval == 0:
      self.save_policy()

  def save_policy(self):
    os.makedirs(os.path.dirname(self.policy_path), exist_ok=True)
    payload = {
        "regret_sum": self.regret_sum,
        "strategy_sum": self.strategy_sum,
        "meta": {
            "exploration": self.exploration,
            "postflop_simulations": self.postflop_simulations,
        },
    }
    with open(self.policy_path, "w", encoding="utf-8") as policy_file:
      json.dump(payload, policy_file, indent=2, sort_keys=True)

  def _load_policy(self):
    if not os.path.exists(self.policy_path):
      return

    with open(self.policy_path, "r", encoding="utf-8") as policy_file:
      payload = json.load(policy_file)

    self.regret_sum = payload.get("regret_sum", {})
    self.strategy_sum = payload.get("strategy_sum", {})

  def _build_info_set(self, hole_card, round_state):
    street = round_state["street"]
    history = compress_action_history(round_state["action_histories"], street)
    position = 1 if self._has_position(round_state) else 0
    info_set = make_info_set_key(
        hole_card_strs=hole_card,
        community_card_strs=round_state["community_card"],
        action_history_str=history,
        position=position,
    )
    info_key = repr(info_set)

    to_call = self._amount_to_call(round_state)
    pot_size = self._pot_size(round_state)
    stack = self._my_stack(round_state)
    pressure = 0.0 if stack <= 0 else min(1.0, float(to_call) / max(stack, 1))
    pot_odds = 0.0 if to_call <= 0 else float(to_call) / max(pot_size + to_call, 1)
    strength = float(info_set[0]) / 7.0

    features = {
        "street": street,
        "strength": strength,
        "pot_odds": pot_odds,
        "pressure": pressure,
    }
    return info_key, features

  def _current_strategy(self, info_key, legal_actions):
    regrets = self.regret_sum.setdefault(info_key, self._zero_action_map())
    strategy_sums = self.strategy_sum.setdefault(info_key, self._zero_action_map())

    positive = {
        action: max(regrets[action], 0.0) if action in legal_actions else 0.0
        for action in self.ACTIONS
    }
    total_positive = sum(positive.values())

    if total_positive > 0:
      strategy = {
          action: positive[action] / total_positive if action in legal_actions else 0.0
          for action in self.ACTIONS
      }
    else:
      legal_count = max(len(legal_actions), 1)
      strategy = {
          action: (1.0 / legal_count) if action in legal_actions else 0.0
          for action in self.ACTIONS
      }

    if self.training_enabled and self.exploration > 0:
      uniform_share = 1.0 / max(len(legal_actions), 1)
      for action in self.ACTIONS:
        if action in legal_actions:
          strategy[action] = (
              (1.0 - self.exploration) * strategy[action]
              + self.exploration * uniform_share
          )

    for action in self.ACTIONS:
      strategy_sums[action] += strategy[action]

    return strategy

  def _sample_action(self, strategy):
    draw = self.random.random()
    cumulative = 0.0
    fallback = "call" if strategy.get("call", 0.0) > 0 else "fold"

    for action in self.ACTIONS:
      probability = strategy.get(action, 0.0)
      if probability <= 0:
        continue
      cumulative += probability
      if draw <= cumulative:
        return action

    return fallback

  def _apply_regret_update(self, decision, round_reward):
    info_key = decision["info_key"]
    regrets = self.regret_sum.setdefault(info_key, self._zero_action_map())

    utilities = self._estimate_action_utilities(
        decision["features"], decision["legal_actions"], round_reward, decision["chosen_action"]
    )
    strategy = decision["strategy"]
    node_value = sum(strategy[action] * utilities[action] for action in self.ACTIONS)

    for action in decision["legal_actions"]:
      regrets[action] += utilities[action] - node_value

  def _estimate_action_utilities(self, features, legal_actions, round_reward, chosen_action):
    strength = features["strength"]
    pot_odds = features["pot_odds"]
    pressure = features["pressure"]
    street_weight = self.STREET_WEIGHT.get(features["street"], 0.8)

    utilities = self._zero_action_map()
    utilities["fold"] = -0.25 - 0.35 * max(0.0, strength - 0.5)
    utilities["call"] = (strength - pot_odds) * 1.1 - 0.15 * pressure
    utilities["raise"] = strength * 1.25 - 0.25 * pot_odds - 0.35 * pressure + 0.08

    chosen_baseline = utilities[chosen_action]
    utilities[chosen_action] = 0.7 * (round_reward * street_weight) + 0.3 * chosen_baseline

    for action in self.ACTIONS:
      if action not in legal_actions:
        utilities[action] = 0.0

    return utilities

  def _zero_action_map(self):
    return {action: 0.0 for action in self.ACTIONS}

  def _has_position(self, round_state):
    seats = round_state["seats"]
    my_index = self._my_seat_index(seats)
    if my_index is None:
      return False

    dealer_btn = round_state["dealer_btn"]
    if len(seats) == 2:
      return my_index == dealer_btn and round_state["street"] != "preflop"
    return my_index == (dealer_btn - 1) % len(seats)

  def _my_seat_index(self, seats):
    for index, seat in enumerate(seats):
      if seat["uuid"] == getattr(self, "uuid", None):
        return index
    return None

  def _my_stack(self, round_state):
    return self._stack_from_seats(round_state["seats"])

  def _stack_from_seats(self, seats):
    for seat in seats:
      if seat["uuid"] == getattr(self, "uuid", None):
        return seat["stack"]
    return 0

  def _pot_size(self, round_state):
    pot = round_state["pot"]
    return pot["main"]["amount"] + sum(side["amount"] for side in pot["side"])

  def _amount_to_call(self, round_state):
    histories = round_state["action_histories"].get(round_state["street"], [])
    highest_amount = 0
    my_amount = 0

    for action in histories:
      if action is None or "amount" not in action:
        continue
      amount = action["amount"]
      highest_amount = max(highest_amount, amount)
      if action.get("uuid") == getattr(self, "uuid", None):
        my_amount = amount

    return max(0, highest_amount - my_amount)


def setup_ai():
  return MinimumCFRPlayer()
