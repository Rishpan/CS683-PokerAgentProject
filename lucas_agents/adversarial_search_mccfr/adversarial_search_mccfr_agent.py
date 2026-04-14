import copy
import json
import os

from lucas_agents.learnable_discounted_mccfr.learnable_discounted_mccfr_agent import (
    LearnableDiscountedMCCFRAgent,
)


class AdversarialSearchMCCFRAgent(LearnableDiscountedMCCFRAgent):
  """
  Practical adversarial-search-flavored MCCFR agent.

  Training still comes from the inherited discounted MCCFR / learnable-weight
  machinery. The "adversarial search" part only appears at inference time:
  the agent enumerates legal actions, predicts a small opponent response model
  for each action, and then picks the action with the best combined score.

  Important distinction:
  Monte Carlo equity rollouts are only one input feature here. A rollout by
  itself is not adversarial search because it estimates hand strength without
  explicitly modeling opponent reactions to a candidate action.
  """

  DEFAULT_SEARCH_WEIGHTS = {
      "rollout": 0.95,
      "response": 1.05,
      "learned": 0.55,
      "counterfactual": 0.40,
      "policy_bias": 0.18,
      "base_action_bonus": 0.08,
  }

  def __init__(
      self,
      policy_path=None,
      training_enabled=True,
      exploration=0.02,
      prior_weight=0.18,
      save_interval=250,
      discount_interval=900,
      postflop_simulations=96,
      random_seed=None,
      learning_rate=0.03,
      weight_decay=0.0005,
      value_mix=0.60,
      search_weights=None,
  ):
    self.policy_path = policy_path or os.path.join(
        os.path.dirname(__file__), "adversarial_search_mccfr_policy.json"
    )
    self.search_weights = dict(self.DEFAULT_SEARCH_WEIGHTS)
    if search_weights:
      for name, value in search_weights.items():
        if name in self.search_weights:
          self.search_weights[name] = float(value)
    self.last_search_summary = None
    super().__init__(
        policy_path=self.policy_path,
        training_enabled=training_enabled,
        exploration=exploration,
        prior_weight=prior_weight,
        save_interval=save_interval,
        discount_interval=discount_interval,
        postflop_simulations=postflop_simulations,
        random_seed=random_seed,
        learning_rate=learning_rate,
        weight_decay=weight_decay,
        value_mix=value_mix,
    )

  def declare_action(self, valid_actions, hole_card, round_state):
    legal_actions = {entry["action"] for entry in valid_actions}
    info_key, features = self._build_info_set(hole_card, round_state)
    base_action = self._baseline_action(valid_actions, hole_card, round_state)
    strategy = self._strategy_for(info_key, legal_actions, features, base_action)

    if self.training_enabled:
      action = super()._pick_action(info_key, strategy, features, legal_actions, base_action)
    else:
      action = self._adversarial_search_action(
          valid_actions=valid_actions,
          info_key=info_key,
          strategy=strategy,
          features=features,
          legal_actions=legal_actions,
          base_action=base_action,
          round_state=round_state,
      )

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

  def save_policy(self):
    os.makedirs(os.path.dirname(self.policy_path), exist_ok=True)
    with open(self.policy_path, "w", encoding="utf-8") as output:
      json.dump(
          {
              "regret_sum": self.regret_sum,
              "strategy_sum": self.strategy_sum,
              "action_weights": self.action_weights,
              "meta": {
                  "exploration": self.exploration,
                  "prior_weight": self.prior_weight,
                  "postflop_simulations": self.postflop_simulations,
                  "learning_rate": self.learning_rate,
                  "weight_decay": self.weight_decay,
                  "value_mix": self.value_mix,
                  "weight_update_count": self.weight_update_count,
              },
              "search_meta": {
                  "search_weights": self.search_weights,
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
    loaded_weights = payload.get("action_weights")
    if loaded_weights:
      merged = copy.deepcopy(self.DEFAULT_ACTION_WEIGHTS)
      for action, feature_map in loaded_weights.items():
        if action not in merged:
          continue
        for feature_name, value in feature_map.items():
          if feature_name in merged[action]:
            merged[action][feature_name] = float(value)
      self.action_weights = merged
    meta = payload.get("meta", {})
    self.weight_update_count = int(meta.get("weight_update_count", self.weight_update_count))
    search_meta = payload.get("search_meta", {})
    for name, value in search_meta.get("search_weights", {}).items():
      if name in self.search_weights:
        self.search_weights[name] = float(value)

  def _adversarial_search_action(
      self,
      valid_actions,
      info_key,
      strategy,
      features,
      legal_actions,
      base_action,
      round_state,
  ):
    average = self._normalized_average_strategy(info_key, legal_actions)
    counterfactual = self._counterfactual_values(features, legal_actions, reward=0.0)
    evaluations = {}

    for action in legal_actions:
      rollout_value = self._rollout_value(action, features, valid_actions, round_state)
      response_value, responses = self._opponent_response_value(action, features, round_state)
      learned_value = self._action_score(action, features)
      policy_bias = max(strategy.get(action, 0.0), average.get(action, 0.0))
      score = (
          self.search_weights["rollout"] * rollout_value
          + self.search_weights["response"] * response_value
          + self.search_weights["learned"] * learned_value
          + self.search_weights["counterfactual"] * counterfactual.get(action, 0.0)
          + self.search_weights["policy_bias"] * policy_bias
      )
      if action == base_action:
        score += self.search_weights["base_action_bonus"]
      evaluations[action] = {
          "score": score,
          "rollout": rollout_value,
          "response": response_value,
          "learned": learned_value,
          "counterfactual": counterfactual.get(action, 0.0),
          "policy_bias": policy_bias,
          "responses": responses,
      }

    best_action = max(
        sorted(legal_actions),
        key=lambda action: (
            evaluations[action]["score"],
            average.get(action, 0.0),
            strategy.get(action, 0.0),
            1 if action == base_action else 0,
        ),
    )
    self.last_search_summary = {
        "base_action": base_action,
        "best_action": best_action,
        "info_key": info_key,
        "features": dict(features),
        "evaluations": evaluations,
    }
    return best_action

  def _normalized_average_strategy(self, info_key, legal_actions):
    average = self.strategy_sum.get(info_key)
    if not average:
      uniform = 1.0 / max(len(legal_actions), 1)
      return {action: (uniform if action in legal_actions else 0.0) for action in self.ACTIONS}

    total = sum(average.get(action, 0.0) for action in legal_actions)
    if total <= 0:
      uniform = 1.0 / max(len(legal_actions), 1)
      return {action: (uniform if action in legal_actions else 0.0) for action in self.ACTIONS}
    return {
        action: (average.get(action, 0.0) / total if action in legal_actions else 0.0)
        for action in self.ACTIONS
    }

  def _rollout_value(self, action, features, valid_actions, round_state):
    strength = features["strength"]
    pot_odds = features["pot_odds"]
    pressure = features["pressure"]
    draw_bonus = 0.035 * features["draws"]
    street_weight = self.STREET_WEIGHT[features["street"]]
    fold_rate = self._opponent_fold_rate()
    aggression = self._opponent_aggression()
    raise_cost = self._raise_commitment_ratio(valid_actions, round_state, features)

    if action == "fold":
      surrender_cost = pot_odds + 0.30 * max(0.0, strength - max(pot_odds, 0.42))
      return -0.16 - surrender_cost
    if action == "call":
      return street_weight * (
          strength
          - max(pot_odds, 0.10)
          + draw_bonus
          - 0.18 * pressure
          + 0.05 * aggression
      )
    return street_weight * (
        1.45 * (strength - 0.50)
        + draw_bonus
        + 0.18 * fold_rate
        - 0.10 * aggression
        - 0.14 * pressure
        - 0.12 * raise_cost
        + 0.08
    )

  def _opponent_response_value(self, action, features, round_state):
    if action == "fold":
      return 0.0, {"terminal": 1.0}

    street_weight = self.STREET_WEIGHT[features["street"]]
    strength = features["strength"]
    pressure = features["pressure"]
    pot_odds = features["pot_odds"]
    draw_bonus = 0.03 * features["draws"]
    aggression = self._opponent_aggression()
    fold_rate = self._opponent_fold_rate()
    position_bonus = 0.03 if features["position"] == 1 else 0.0
    short_stack_bonus = 0.04 if features["spr"] <= 2.5 else 0.0
    pot_scale = min(1.6, self._pot_size(round_state) / float(max(round_state["small_blind_amount"] * 6, 1)))

    if action == "call":
      future_pressure = self._clamp(0.22 + 0.95 * aggression - 0.20 * fold_rate, 0.10, 0.82)
      passive = 1.0 - future_pressure
      pressure_value = street_weight * (
          strength
          - pot_odds
          - 0.20
          - 0.32 * pressure
          + draw_bonus
          + position_bonus
      )
      passive_value = street_weight * (
          strength
          - 0.55 * pot_odds
          + draw_bonus
          + position_bonus
          + 0.05
      )
      expected = future_pressure * pressure_value + passive * passive_value
      return expected, {"pressure": future_pressure, "passive": passive}

    fold_response = self._clamp(
        0.20 + 0.90 * fold_rate - 0.34 * aggression + 0.08 * pressure + short_stack_bonus,
        0.08,
        0.80,
    )
    reraise_response = self._clamp(
        0.07 + 0.85 * aggression - 0.30 * fold_rate + 0.05 * pressure,
        0.05,
        0.60,
    )
    if fold_response + reraise_response >= 0.95:
      scale = 0.95 / (fold_response + reraise_response)
      fold_response *= scale
      reraise_response *= scale
    call_response = max(0.0, 1.0 - fold_response - reraise_response)

    fold_value = 0.24 + 0.10 * pot_scale
    call_value = street_weight * (
        1.15 * (strength - 0.48)
        + draw_bonus
        + position_bonus
        + 0.04 * pot_scale
        + 0.04
    )
    reraise_value = street_weight * (
        strength
        + draw_bonus
        - 0.48
        - 0.46 * pressure
        - 0.12 * aggression
        + position_bonus
    )
    expected = (
        fold_response * fold_value
        + call_response * call_value
        + reraise_response * reraise_value
    )
    return expected, {
        "fold": fold_response,
        "call": call_response,
        "reraise": reraise_response,
    }

  def _raise_commitment_ratio(self, valid_actions, round_state, features):
    raise_action = next((action for action in valid_actions if action["action"] == "raise"), None)
    if not raise_action:
      return 0.0
    amount = raise_action.get("amount", {})
    if isinstance(amount, dict):
      min_raise = amount.get("min", 0) or 0
    else:
      min_raise = amount or 0

    to_call = features["to_call"]
    extra_cost = max(0.0, float(min_raise) - float(to_call))
    if extra_cost <= 0:
      extra_cost = max(round_state["small_blind_amount"] * 2.0, self._pot_size(round_state) * 0.25)
    stack = max(float(self._my_stack(round_state)), 1.0)
    return min(1.2, extra_cost / stack)

  def _clamp(self, value, lower, upper):
    return max(lower, min(upper, value))


def setup_ai():
  return AdversarialSearchMCCFRAgent(training_enabled=False, exploration=0.0)
