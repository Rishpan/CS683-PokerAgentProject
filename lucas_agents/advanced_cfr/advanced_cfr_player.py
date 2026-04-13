import json
import os
import random

from lucas_agents.advanced_cfr.abstraction import build_info_key
from lucas_agents.condition_threshold_player import ConditionThresholdPlayer


class AdvancedCFRPlayer(ConditionThresholdPlayer):
  ACTIONS = ("fold", "call", "raise")
  STREET_WEIGHT = {"preflop": 0.7, "flop": 0.9, "turn": 1.05, "river": 1.2}

  def __init__(
      self,
      policy_path=None,
      training_enabled=True,
      exploration=0.04,
      prior_weight=0.12,
      save_interval=250,
      discount_interval=500,
      postflop_simulations=48,
      random_seed=None,
  ):
    self.policy_path = policy_path or os.path.join(
        os.path.dirname(__file__), "advanced_cfr_policy.json"
    )
    super().__init__()
    self.training_enabled = training_enabled
    self.exploration = exploration
    self.prior_weight = prior_weight
    self.save_interval = save_interval
    self.discount_interval = discount_interval
    self.postflop_simulations = postflop_simulations
    self.random = random.Random(random_seed)

    self.regret_sum = {}
    self.strategy_sum = {}
    self.round_count = 0
    self.round_start_stack = 0
    self.round_decisions = []
    self.opponent_stats = {}
    self._load_policy()

  def declare_action(self, valid_actions, hole_card, round_state):
    legal_actions = {entry["action"] for entry in valid_actions}
    info_key, features = self._build_info_set(hole_card, round_state)
    base_action = self._baseline_action(valid_actions, hole_card, round_state)
    strategy = self._strategy_for(info_key, legal_actions, features, base_action)
    action = self._pick_action(info_key, strategy, features, legal_actions, base_action)

    if self.training_enabled:
      self.round_decisions.append(
          {
              "info_key": info_key,
              "legal_actions": tuple(sorted(legal_actions)),
              "strategy": dict(strategy),
              "chosen_action": action,
              "chosen_prob": max(strategy.get(action, 0.0), 0.05),
              "features": features,
          }
      )
    return action

  def receive_game_start_message(self, game_info):
    del game_info

  def receive_round_start_message(self, round_count, hole_card, seats):
    del hole_card
    self.round_count = round_count
    self.round_decisions = []
    self.round_start_stack = self._stack_from_seats(seats)

  def receive_street_start_message(self, street, round_state):
    del street
    del round_state

  def receive_game_update_message(self, action, round_state):
    super().receive_game_update_message(action, round_state)

  def receive_round_result_message(self, winners, hand_info, round_state):
    del winners
    del hand_info
    if not self.training_enabled or not self.round_decisions:
      return

    chip_delta = self._my_stack(round_state) - self.round_start_stack
    normalizer = max(round_state["small_blind_amount"] * 6, 1)
    reward = max(-1.5, min(1.5, chip_delta / float(normalizer)))

    for decision in self.round_decisions:
      self._update_regrets(decision, reward)

    if self.discount_interval and self.round_count % self.discount_interval == 0:
      self._apply_discount()
    if self.save_interval and self.round_count % self.save_interval == 0:
      self.save_policy()

  def save_policy(self):
    os.makedirs(os.path.dirname(self.policy_path), exist_ok=True)
    with open(self.policy_path, "w", encoding="utf-8") as output:
      json.dump(
          {
              "regret_sum": self.regret_sum,
              "strategy_sum": self.strategy_sum,
              "meta": {
                  "exploration": self.exploration,
                  "prior_weight": self.prior_weight,
                  "postflop_simulations": self.postflop_simulations,
              },
          },
          output,
          indent=2,
          sort_keys=True,
      )

  def _load_policy(self):
    if not os.path.exists(self.policy_path):
      return
    with open(self.policy_path, "r", encoding="utf-8") as source:
      payload = json.load(source)
    self.regret_sum = payload.get("regret_sum", {})
    self.strategy_sum = payload.get("strategy_sum", {})

  def _build_info_set(self, hole_card, round_state):
    to_call = self._amount_to_call(round_state)
    pot_size = self._pot_size(round_state)
    stack = self._my_stack(round_state)
    pot_odds = 0.0 if to_call <= 0 else float(to_call) / max(pot_size + to_call, 1)
    pressure = 0.0 if stack <= 0 else min(1.0, float(to_call) / max(stack, 1))
    spr = float(stack) / max(pot_size, 1)
    key, features = build_info_key(
        hole_card=hole_card,
        community_card=round_state["community_card"],
        street=round_state["street"],
        action_histories=round_state["action_histories"],
        position=1 if self._has_position(round_state) else 0,
        pot_odds=pot_odds,
        pressure=pressure,
        spr=spr,
        simulations=self.postflop_simulations,
    )
    features["to_call"] = to_call
    features["free_action"] = to_call == 0
    return repr(key), features

  def _strategy_for(self, info_key, legal_actions, features, base_action):
    regrets = self.regret_sum.setdefault(info_key, self._zero_map())
    sums = self.strategy_sum.setdefault(info_key, self._zero_map())
    prior = self._prior_strategy(features, legal_actions, base_action)

    numerators = {}
    total = 0.0
    for action in self.ACTIONS:
      if action not in legal_actions:
        numerators[action] = 0.0
        continue
      numerators[action] = max(regrets[action], 0.0) + self.prior_weight * prior[action]
      total += numerators[action]

    if total <= 0:
      strategy = dict(prior)
    else:
      strategy = {action: numerators[action] / total for action in self.ACTIONS}

    if self.training_enabled and self.exploration > 0:
      uniform = 1.0 / max(len(legal_actions), 1)
      for action in self.ACTIONS:
        if action in legal_actions:
          strategy[action] = (1.0 - self.exploration) * strategy[action] + self.exploration * uniform
        else:
          strategy[action] = 0.0

    weight = max(1.0, self.round_count ** 0.5)
    for action in self.ACTIONS:
      sums[action] += weight * strategy.get(action, 0.0)
    return strategy

  def _prior_strategy(self, features, legal_actions, base_action):
    strength = features["strength"]
    pot_odds = features["pot_odds"]
    pressure = features["pressure"]
    draw_bonus = 0.05 * features["draws"]
    aggression = self._opponent_aggression()
    fold_rate = self._opponent_fold_rate()

    raise_score = strength + draw_bonus + 0.18 * fold_rate - 0.08 * aggression - 0.16 * pot_odds
    call_score = strength + 0.5 * draw_bonus - pot_odds - 0.08 * pressure + 0.06 * aggression
    fold_score = 0.52 - strength + 0.34 * pressure + 0.18 * pot_odds

    raw = self._zero_map()
    raw["fold"] = max(0.0, fold_score) if "fold" in legal_actions else 0.0
    raw["call"] = max(0.02, call_score + 0.15) if "call" in legal_actions else 0.0
    raw["raise"] = max(0.0, raise_score + 0.12) if "raise" in legal_actions else 0.0

    if "raise" in legal_actions and strength >= max(0.56, pot_odds + 0.16):
      raw["raise"] += 0.45
    if "call" in legal_actions and strength >= max(0.45, pot_odds + 0.08):
      raw["call"] += 0.25
    if pressure > 0.28 and strength < 0.48:
      raw["fold"] += 0.45
    raw[base_action] += 1.8

    total = sum(raw.values())
    if total <= 0:
      uniform = 1.0 / max(len(legal_actions), 1)
      return {action: (uniform if action in legal_actions else 0.0) for action in self.ACTIONS}
    return {action: raw[action] / total for action in self.ACTIONS}

  def _pick_action(self, info_key, strategy, features, legal_actions, base_action):
    if not self.training_enabled:
      average = self.strategy_sum.get(info_key)
      if average:
        total = sum(average.values())
        if total > 0:
          normalized = {action: average[action] / total for action in self.ACTIONS}
          learned_action = max(normalized, key=normalized.get)
          if learned_action != base_action and normalized[learned_action] >= 0.72:
            return learned_action
      del strategy
      del features
      del legal_actions
      return base_action
    draw = self.random.random()
    cumulative = 0.0
    for action in self.ACTIONS:
      probability = strategy.get(action, 0.0)
      if probability <= 0:
        continue
      cumulative += probability
      if draw <= cumulative:
        return action
    return "call" if strategy.get("call", 0.0) > 0 else "fold"

  def _update_regrets(self, decision, reward):
    info_key = decision["info_key"]
    regrets = self.regret_sum.setdefault(info_key, self._zero_map())
    utilities = self._counterfactual_values(decision["features"], decision["legal_actions"], reward)
    realized = decision["chosen_action"]
    importance = min(2.5, 1.0 / decision["chosen_prob"])
    utilities[realized] = 0.7 * reward * importance + 0.3 * utilities[realized]
    node_value = sum(decision["strategy"].get(action, 0.0) * utilities[action] for action in self.ACTIONS)

    for action in decision["legal_actions"]:
      regrets[action] = max(0.0, regrets[action] + utilities[action] - node_value)

  def _counterfactual_values(self, features, legal_actions, reward):
    strength = features["strength"]
    pot_odds = features["pot_odds"]
    pressure = features["pressure"]
    street_weight = self.STREET_WEIGHT[features["street"]]
    draw_bonus = 0.04 * features["draws"]
    aggression = self._opponent_aggression()
    fold_rate = self._opponent_fold_rate()

    values = self._zero_map()
    values["fold"] = -0.18 - 0.3 * max(0.0, strength - 0.48)
    values["call"] = street_weight * (strength - pot_odds + draw_bonus - 0.18 * pressure)
    values["raise"] = street_weight * (
        strength
        + draw_bonus
        + 0.22 * fold_rate
        - 0.1 * aggression
        - 0.14 * pot_odds
        - 0.15 * pressure
        + 0.09
    )
    for action in self.ACTIONS:
      if action not in legal_actions:
        values[action] = 0.0
    if reward < 0 and "fold" in legal_actions and pressure > 0.22:
      values["fold"] += 0.08
    return values

  def _baseline_action(self, valid_actions, hole_card, round_state):
    street = round_state["street"]
    can_raise = any(action["action"] == "raise" for action in valid_actions)
    to_call = self._amount_to_call(round_state)
    pot_size = self._pot_size(round_state)
    stack = self._my_stack(round_state)

    equity = self._estimate_equity(hole_card, round_state)
    adjusted_equity = equity + self._position_bonus(round_state) + self._board_pressure_adjustment(
        street, to_call, stack
    )

    raise_threshold, call_threshold = self._street_thresholds(street)
    raise_threshold, call_threshold = self._adjust_for_opponent(raise_threshold, call_threshold)
    raise_threshold, call_threshold = self._adjust_for_price(
        raise_threshold, call_threshold, to_call, pot_size, stack
    )
    raise_threshold -= 0.03 * self._opponent_fold_rate()

    if to_call == 0:
      if can_raise and adjusted_equity >= raise_threshold - 0.06:
        return "raise"
      return "call"
    if can_raise and adjusted_equity >= raise_threshold:
      return "raise"
    if adjusted_equity >= call_threshold:
      return "call"
    return "fold"

  def _apply_discount(self):
    for table in (self.regret_sum, self.strategy_sum):
      for info_key, action_map in list(table.items()):
        for action in self.ACTIONS:
          action_map[action] *= 0.94
        if max(action_map.values()) < 1e-8:
          del table[info_key]

  def _opponent_fold_rate(self):
    folds = 0
    total = 0
    for stats in self.opponent_actions.values():
      folds += stats["fold"]
      total += stats["raise"] + stats["call"] + stats["fold"]
    return 0.18 if total == 0 else folds / float(total)

  def _zero_map(self):
    return {action: 0.0 for action in self.ACTIONS}

  def _has_position(self, round_state):
    seats = round_state["seats"]
    my_index = self._my_seat_index(seats)
    if my_index is None:
      return False
    dealer_btn = round_state["dealer_btn"]
    return my_index == dealer_btn and round_state["street"] != "preflop"

  def _my_stack(self, round_state):
    for seat in round_state["seats"]:
      if seat["uuid"] == getattr(self, "uuid", None):
        return seat["stack"]
    return 0

  def _stack_from_seats(self, seats):
    for seat in seats:
      if seat["uuid"] == getattr(self, "uuid", None):
        return seat["stack"]
    return 0

  def _my_seat_index(self, seats):
    for index, seat in enumerate(seats):
      if seat["uuid"] == getattr(self, "uuid", None):
        return index
    return None

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
  return AdvancedCFRPlayer(training_enabled=False, exploration=0.0)
