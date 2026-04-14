import copy
import json
import math
import os

from lucas_agents.learnable_discounted_mccfr.learnable_discounted_mccfr_agent import (
    LearnableDiscountedMCCFRAgent,
)


class AdversarialSearchMCCFRV2Agent(LearnableDiscountedMCCFRAgent):
  """
  Conservative adversarial-search refinement over the stronger learnable MCCFR base.

  v1 fully re-ranked actions with a shallow search score, which can override a
  much better learned policy. v2 treats search as a local refinement layer:
  it mostly activates in higher-leverage spots and only changes the default
  action when the search signal has enough margin and agreement.
  """

  DEFAULT_REFINEMENT_WEIGHTS = {
      "strategy": 0.22,
      "average": 0.40,
      "learned": 0.22,
      "counterfactual": 0.10,
      "search": 0.06,
  }

  DEFAULT_SEARCH_WEIGHTS = {
      "rollout": 0.34,
      "response": 0.28,
      "learned": 0.18,
      "counterfactual": 0.12,
      "policy_bias": 0.08,
      "base_action_bonus": 0.03,
  }

  DEFAULT_THRESHOLDS = {
      "learned_override_margin": 0.10,
      "search_gate_min": 0.46,
      "search_override_margin": 0.13,
      "search_blended_margin": 0.06,
      "search_support_floor": 0.24,
      "search_confidence_floor": 0.57,
  }

  def __init__(
      self,
      policy_path=None,
      training_enabled=True,
      exploration=0.02,
      prior_weight=0.16,
      save_interval=250,
      discount_interval=900,
      postflop_simulations=96,
      random_seed=None,
      learning_rate=0.035,
      weight_decay=0.0005,
      value_mix=0.65,
      refinement_weights=None,
      search_weights=None,
      thresholds=None,
  ):
    self.policy_path = policy_path or os.path.join(
        os.path.dirname(__file__), "adversarial_search_mccfr_v2_policy.json"
    )
    self.refinement_weights = dict(self.DEFAULT_REFINEMENT_WEIGHTS)
    self.search_weights = dict(self.DEFAULT_SEARCH_WEIGHTS)
    self.thresholds = dict(self.DEFAULT_THRESHOLDS)
    if refinement_weights:
      for name, value in refinement_weights.items():
        if name in self.refinement_weights:
          self.refinement_weights[name] = float(value)
    if search_weights:
      for name, value in search_weights.items():
        if name in self.search_weights:
          self.search_weights[name] = float(value)
    if thresholds:
      for name, value in thresholds.items():
        if name in self.thresholds:
          self.thresholds[name] = float(value)
    self.last_refinement_summary = None
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
      action = self._refined_action(
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
              "refinement_meta": {
                  "refinement_weights": self.refinement_weights,
                  "search_weights": self.search_weights,
                  "thresholds": self.thresholds,
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
    refinement_meta = payload.get("refinement_meta", {})
    for name, value in refinement_meta.get("refinement_weights", {}).items():
      if name in self.refinement_weights:
        self.refinement_weights[name] = float(value)
    for name, value in refinement_meta.get("search_weights", {}).items():
      if name in self.search_weights:
        self.search_weights[name] = float(value)
    for name, value in refinement_meta.get("thresholds", {}).items():
      if name in self.thresholds:
        self.thresholds[name] = float(value)

  def _refined_action(
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
    learned = self._softmax_distribution(
        {action: self._action_score(action, features) for action in legal_actions},
        legal_actions,
    )
    counterfactual = self._positive_distribution(
        self._counterfactual_values(features, legal_actions, reward=0.0),
        legal_actions,
    )
    anchor = self._anchor_policy(strategy, average, learned, counterfactual, legal_actions)
    default_action, default_reason = self._default_action(anchor, average, strategy, base_action, legal_actions)

    search_context = self._search_context(valid_actions, features, round_state)
    search_eval = None
    final_action = default_action

    if search_context["enabled"]:
      search_eval = self._search_evaluations(
          valid_actions=valid_actions,
          features=features,
          legal_actions=legal_actions,
          strategy=strategy,
          average=average,
          counterfactual=counterfactual,
          base_action=base_action,
          round_state=round_state,
          leverage=search_context["leverage"],
      )
      if self._should_override_with_search(
          default_action=default_action,
          anchor=anchor,
          search_eval=search_eval,
          leverage=search_context["leverage"],
      ):
        final_action = search_eval["best_action"]

    self.last_refinement_summary = {
        "info_key": info_key,
        "features": dict(features),
        "base_action": base_action,
        "default_action": default_action,
        "default_reason": default_reason,
        "final_action": final_action,
        "anchor_policy": anchor,
        "average_policy": average,
        "strategy_policy": strategy,
        "learned_policy": learned,
        "counterfactual_policy": counterfactual,
        "search_context": search_context,
        "search_eval": search_eval,
    }
    return final_action

  def _anchor_policy(self, strategy, average, learned, counterfactual, legal_actions):
    blended = self._zero_map()
    for action in legal_actions:
      blended[action] = (
          self.refinement_weights["strategy"] * strategy.get(action, 0.0)
          + self.refinement_weights["average"] * average.get(action, 0.0)
          + self.refinement_weights["learned"] * learned.get(action, 0.0)
          + self.refinement_weights["counterfactual"] * counterfactual.get(action, 0.0)
      )
    return self._normalize_distribution(blended, legal_actions)

  def _default_action(self, anchor, average, strategy, base_action, legal_actions):
    ranked = sorted(
        legal_actions,
        key=lambda action: (
            anchor.get(action, 0.0),
            average.get(action, 0.0),
            strategy.get(action, 0.0),
            1 if action == base_action else 0,
        ),
        reverse=True,
    )
    anchor_best = ranked[0]
    runner_up = ranked[1] if len(ranked) > 1 else ranked[0]
    anchor_margin = anchor.get(anchor_best, 0.0) - anchor.get(runner_up, 0.0)

    if anchor_best == base_action:
      return base_action, "anchor_matches_base"
    if anchor_margin >= self.thresholds["learned_override_margin"]:
      return anchor_best, "anchor_margin"
    return base_action, "base_default"

  def _search_context(self, valid_actions, features, round_state):
    street = features["street"]
    pressure = features["pressure"]
    to_call = features["to_call"]
    pot_size = max(float(self._pot_size(round_state)), 1.0)
    raise_ratio = self._raise_commitment_ratio(valid_actions, round_state, features)
    can_raise = any(action["action"] == "raise" for action in valid_actions)
    later_street = 1.0 if street in ("turn", "river") else 0.0
    meaningful_raise = 1.0 if can_raise and raise_ratio >= 0.10 else 0.0
    big_call = min(1.0, float(to_call) / pot_size)

    leverage = self._clamp(
        0.18
        + 0.30 * later_street
        + 0.22 * min(1.0, pressure / 0.28)
        + 0.16 * meaningful_raise
        + 0.14 * big_call,
        0.0,
        1.0,
    )
    enabled = leverage >= self.thresholds["search_gate_min"]
    reasons = []
    if later_street:
      reasons.append("later_street")
    if pressure >= 0.16:
      reasons.append("pressure")
    if meaningful_raise:
      reasons.append("meaningful_raise")
    if big_call >= 0.18:
      reasons.append("pot_commitment")
    return {
        "enabled": enabled,
        "leverage": leverage,
        "raise_ratio": raise_ratio,
        "reasons": reasons,
    }

  def _search_evaluations(
      self,
      valid_actions,
      features,
      legal_actions,
      strategy,
      average,
      counterfactual,
      base_action,
      round_state,
      leverage,
  ):
    raw_scores = {}
    detail = {}

    for action in legal_actions:
      rollout_value = self._rollout_value(action, features, valid_actions, round_state)
      response_value, responses = self._opponent_response_value(action, features, round_state)
      learned_value = self._action_score(action, features)
      policy_bias = 0.5 * strategy.get(action, 0.0) + 0.5 * average.get(action, 0.0)
      score = (
          self.search_weights["rollout"] * rollout_value
          + self.search_weights["response"] * response_value
          + self.search_weights["learned"] * learned_value
          + self.search_weights["counterfactual"] * counterfactual.get(action, 0.0)
          + self.search_weights["policy_bias"] * policy_bias
      )
      if action == base_action:
        score += self.search_weights["base_action_bonus"]
      raw_scores[action] = score
      detail[action] = {
          "score": score,
          "rollout": rollout_value,
          "response": response_value,
          "learned": learned_value,
          "counterfactual": counterfactual.get(action, 0.0),
          "policy_bias": policy_bias,
          "responses": responses,
      }

    search_policy = self._softmax_distribution(raw_scores, legal_actions, temperature=0.70)
    blended = self._zero_map()
    search_mix = min(0.22, self.refinement_weights["search"] + 0.12 * leverage)
    for action in legal_actions:
      blended[action] = (1.0 - search_mix) * (
          0.58 * average.get(action, 0.0) + 0.42 * strategy.get(action, 0.0)
      ) + search_mix * search_policy.get(action, 0.0)
    blended = self._normalize_distribution(blended, legal_actions)

    ranked = sorted(
        legal_actions,
        key=lambda action: (search_policy.get(action, 0.0), blended.get(action, 0.0)),
        reverse=True,
    )
    best_action = ranked[0]
    second_action = ranked[1] if len(ranked) > 1 else ranked[0]
    search_margin = search_policy.get(best_action, 0.0) - search_policy.get(second_action, 0.0)
    response_clarity = self._response_clarity(detail[best_action]["responses"])
    confidence = self._clamp(0.48 + 0.65 * search_margin + 0.18 * response_clarity + 0.12 * leverage, 0.0, 1.0)

    return {
        "best_action": best_action,
        "runner_up": second_action,
        "search_policy": search_policy,
        "blended_policy": blended,
        "search_margin": search_margin,
        "response_clarity": response_clarity,
        "confidence": confidence,
        "search_mix": search_mix,
        "detail": detail,
    }

  def _should_override_with_search(self, default_action, anchor, search_eval, leverage):
    best_action = search_eval["best_action"]
    if best_action == default_action:
      return True

    search_margin = search_eval["search_margin"]
    blended_margin = (
        search_eval["blended_policy"].get(best_action, 0.0)
        - search_eval["blended_policy"].get(default_action, 0.0)
    )
    search_support = search_eval["search_policy"].get(best_action, 0.0)
    anchor_support = anchor.get(best_action, 0.0)
    confidence = search_eval["confidence"]

    required_margin = self.thresholds["search_override_margin"] - 0.03 * leverage
    required_confidence = self.thresholds["search_confidence_floor"] - 0.04 * leverage

    return (
        search_margin >= required_margin
        and blended_margin >= self.thresholds["search_blended_margin"]
        and search_support >= self.thresholds["search_support_floor"]
        and (anchor_support >= 0.18 or search_support - anchor.get(default_action, 0.0) >= 0.10)
        and confidence >= required_confidence
    )

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
    draw_bonus = 0.028 * features["draws"]
    street_weight = self.STREET_WEIGHT[features["street"]]
    fold_rate = self._opponent_fold_rate()
    aggression = self._opponent_aggression()
    raise_cost = self._raise_commitment_ratio(valid_actions, round_state, features)

    if action == "fold":
      return -0.12 - pot_odds - 0.22 * max(0.0, strength - max(0.40, pot_odds))
    if action == "call":
      return street_weight * (
          strength
          - 0.95 * pot_odds
          + draw_bonus
          - 0.16 * pressure
          + 0.04 * aggression
      )
    return street_weight * (
        1.08 * (strength - 0.50)
        + draw_bonus
        + 0.12 * fold_rate
        - 0.08 * aggression
        - 0.10 * pressure
        - 0.10 * raise_cost
        + 0.05
    )

  def _opponent_response_value(self, action, features, round_state):
    if action == "fold":
      return 0.0, {"terminal": 1.0}

    street_weight = self.STREET_WEIGHT[features["street"]]
    strength = features["strength"]
    pressure = features["pressure"]
    pot_odds = features["pot_odds"]
    draw_bonus = 0.025 * features["draws"]
    aggression = self._opponent_aggression()
    fold_rate = self._opponent_fold_rate()
    position_bonus = 0.02 if features["position"] == 1 else 0.0
    pot_scale = min(1.4, self._pot_size(round_state) / float(max(round_state["small_blind_amount"] * 6, 1)))

    if action == "call":
      future_pressure = self._clamp(0.20 + 0.90 * aggression - 0.18 * fold_rate, 0.10, 0.78)
      passive = 1.0 - future_pressure
      pressure_value = street_weight * (
          strength
          - pot_odds
          - 0.18
          - 0.24 * pressure
          + draw_bonus
          + position_bonus
      )
      passive_value = street_weight * (
          strength
          - 0.55 * pot_odds
          + draw_bonus
          + position_bonus
          + 0.03
      )
      expected = future_pressure * pressure_value + passive * passive_value
      return expected, {"pressure": future_pressure, "passive": passive}

    fold_response = self._clamp(
        0.16 + 0.82 * fold_rate - 0.26 * aggression + 0.06 * pressure,
        0.08,
        0.72,
    )
    reraise_response = self._clamp(
        0.06 + 0.72 * aggression - 0.22 * fold_rate + 0.04 * pressure,
        0.05,
        0.48,
    )
    if fold_response + reraise_response >= 0.90:
      scale = 0.90 / (fold_response + reraise_response)
      fold_response *= scale
      reraise_response *= scale
    call_response = max(0.0, 1.0 - fold_response - reraise_response)

    fold_value = 0.18 + 0.08 * pot_scale
    call_value = street_weight * (
        1.02 * (strength - 0.49)
        + draw_bonus
        + position_bonus
        + 0.03 * pot_scale
        + 0.03
    )
    reraise_value = street_weight * (
        strength
        + draw_bonus
        - 0.48
        - 0.34 * pressure
        - 0.10 * aggression
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

  def _positive_distribution(self, values, legal_actions):
    positive = self._zero_map()
    for action in legal_actions:
      positive[action] = max(0.0, values.get(action, 0.0))
    total = sum(positive.get(action, 0.0) for action in legal_actions)
    if total <= 0:
      return self._normalize_distribution(positive, legal_actions)
    return {
        action: (positive.get(action, 0.0) / total if action in legal_actions else 0.0)
        for action in self.ACTIONS
    }

  def _softmax_distribution(self, scores, legal_actions, temperature=1.0):
    if not legal_actions:
      return self._zero_map()
    scale = max(temperature, 1e-6)
    max_score = max(scores.get(action, 0.0) for action in legal_actions)
    numerators = self._zero_map()
    total = 0.0
    for action in legal_actions:
      value = math.exp((scores.get(action, 0.0) - max_score) / scale)
      numerators[action] = value
      total += value
    if total <= 0:
      return self._normalize_distribution(numerators, legal_actions)
    return {
        action: (numerators.get(action, 0.0) / total if action in legal_actions else 0.0)
        for action in self.ACTIONS
    }

  def _normalize_distribution(self, values, legal_actions):
    total = sum(values.get(action, 0.0) for action in legal_actions)
    if total <= 0:
      uniform = 1.0 / max(len(legal_actions), 1)
      return {action: (uniform if action in legal_actions else 0.0) for action in self.ACTIONS}
    return {
        action: (values.get(action, 0.0) / total if action in legal_actions else 0.0)
        for action in self.ACTIONS
    }

  def _response_clarity(self, responses):
    if not responses:
      return 0.0
    values = sorted((float(value) for value in responses.values()), reverse=True)
    if len(values) == 1:
      return 1.0
    return self._clamp(values[0] - values[1], 0.0, 1.0)

  def _clamp(self, value, lower, upper):
    return max(lower, min(upper, value))


def setup_ai():
  return AdversarialSearchMCCFRV2Agent(training_enabled=False, exploration=0.0)
