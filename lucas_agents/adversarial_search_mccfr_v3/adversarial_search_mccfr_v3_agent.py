import copy
import json
import os

from lucas_agents.adversarial_search_mccfr_v2.adversarial_search_mccfr_v2_agent import (
    AdversarialSearchMCCFRV2Agent,
)
from lucas_agents.learnable_discounted_mccfr.learnable_discounted_mccfr_agent import (
    LearnableDiscountedMCCFRAgent,
)


class AdversarialSearchMCCFRV3Agent(AdversarialSearchMCCFRV2Agent):
  """
  v3 keeps the conservative v2 search refinement structure, but makes the
  search/refinement mix itself learn online from realized results.
  """

  REFINEMENT_COMPONENTS = ("strategy", "average", "learned", "counterfactual", "search")
  SEARCH_COMPONENTS = (
      "rollout",
      "response",
      "learned",
      "counterfactual",
      "policy_bias",
      "base_action_bonus",
  )
  THRESHOLD_NAMES = (
      "learned_override_margin",
      "search_gate_min",
      "search_override_margin",
      "search_blended_margin",
      "search_support_floor",
      "search_confidence_floor",
  )
  THRESHOLD_BOUNDS = {
      "learned_override_margin": (0.03, 0.28),
      "search_gate_min": (0.24, 0.82),
      "search_override_margin": (0.04, 0.28),
      "search_blended_margin": (0.01, 0.18),
      "search_support_floor": (0.10, 0.45),
      "search_confidence_floor": (0.38, 0.82),
  }
  DEFAULT_ADAPTATION_META = {
      "search_learning_rate": 0.018,
      "refinement_learning_rate": 0.014,
      "threshold_learning_rate": 0.010,
      "search_weight_decay": 0.0003,
      "threshold_decay": 0.0001,
      "reward_mix": 0.50,
      "search_update_count": 0,
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
      search_learning_rate=None,
      refinement_learning_rate=None,
      threshold_learning_rate=None,
      search_weight_decay=None,
      threshold_decay=None,
      reward_mix=None,
  ):
    self.policy_path = policy_path or os.path.join(
        os.path.dirname(__file__), "adversarial_search_mccfr_v3_policy.json"
    )
    self.seed_policy_path = os.path.join(
        os.path.dirname(__file__), "..", "adversarial_search_mccfr_v2", "adversarial_search_mccfr_v2_policy.json"
    )
    self.fallback_policy_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "learnable_discounted_mccfr",
        "learnable_discounted_mccfr_policy.json",
    )
    self.adaptation_meta = dict(self.DEFAULT_ADAPTATION_META)
    overrides = {
        "search_learning_rate": search_learning_rate,
        "refinement_learning_rate": refinement_learning_rate,
        "threshold_learning_rate": threshold_learning_rate,
        "search_weight_decay": search_weight_decay,
        "threshold_decay": threshold_decay,
        "reward_mix": reward_mix,
    }
    for name, value in overrides.items():
      if value is not None:
        self.adaptation_meta[name] = float(value)
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
        refinement_weights=refinement_weights,
        search_weights=search_weights,
        thresholds=thresholds,
    )

  def declare_action(self, valid_actions, hole_card, round_state):
    legal_actions = {entry["action"] for entry in valid_actions}
    info_key, features = self._build_info_set(hole_card, round_state)
    base_action = self._baseline_action(valid_actions, hole_card, round_state)
    strategy = self._strategy_for(info_key, legal_actions, features, base_action)

    if self.training_enabled:
      action = LearnableDiscountedMCCFRAgent._pick_action(
          self, info_key, strategy, features, legal_actions, base_action
      )
      search_snapshot = self._compute_refinement_snapshot(
          valid_actions=valid_actions,
          info_key=info_key,
          strategy=strategy,
          features=features,
          legal_actions=legal_actions,
          base_action=base_action,
          round_state=round_state,
      )
      self.round_decisions.append(
          {
              "info_key": info_key,
              "legal_actions": tuple(sorted(legal_actions)),
              "strategy": dict(strategy),
              "chosen_action": action,
              "chosen_prob": max(strategy.get(action, 0.0), 0.05),
              "features": features,
              "base_action": base_action,
              "search_snapshot": search_snapshot,
          }
      )
      return action

    action = self._refined_action(
        valid_actions=valid_actions,
        info_key=info_key,
        strategy=strategy,
        features=features,
        legal_actions=legal_actions,
        base_action=base_action,
        round_state=round_state,
    )
    return action

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
      self._learn_from_decision(decision, reward)
      self._learn_search_parameters(decision, reward)

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
              "adaptation_meta": self.adaptation_meta,
          },
          output,
          indent=2,
          sort_keys=True,
      )

  def _load_policy(self):
    payload = self._load_payload_from_candidates()
    if not payload:
      return

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

    loaded_adaptation = payload.get("adaptation_meta", {})
    for name, value in loaded_adaptation.items():
      if name in self.adaptation_meta:
        if name == "search_update_count":
          self.adaptation_meta[name] = int(value)
        else:
          self.adaptation_meta[name] = float(value)

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
    summary = self._compute_refinement_snapshot(
        valid_actions=valid_actions,
        info_key=info_key,
        strategy=strategy,
        features=features,
        legal_actions=legal_actions,
        base_action=base_action,
        round_state=round_state,
    )
    self.last_refinement_summary = summary
    return summary["final_action"]

  def _compute_refinement_snapshot(
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

    return {
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

  def _load_payload_from_candidates(self):
    for candidate in (self.policy_path, self.seed_policy_path, self.fallback_policy_path):
      if candidate and os.path.exists(candidate):
        with open(candidate, "r", encoding="utf-8") as source:
          return json.load(source)
    return None

  def _learn_search_parameters(self, decision, reward):
    snapshot = decision.get("search_snapshot")
    if not snapshot:
      return

    legal_actions = decision["legal_actions"]
    chosen_action = decision["chosen_action"]
    base_action = decision.get("base_action", snapshot["base_action"])
    leverage = snapshot["search_context"]["leverage"]
    target_policy = self._target_policy(decision, reward, legal_actions, chosen_action, base_action)

    self._update_refinement_weights(snapshot, target_policy, legal_actions, leverage)
    self._update_thresholds(snapshot, target_policy, reward, chosen_action, leverage)
    if snapshot["search_eval"]:
      self._update_search_weights(snapshot, target_policy, legal_actions, leverage, base_action)

    self.adaptation_meta["search_update_count"] = int(self.adaptation_meta["search_update_count"]) + 1

  def _target_policy(self, decision, reward, legal_actions, chosen_action, base_action):
    features = decision["features"]
    heuristic_targets = LearnableDiscountedMCCFRAgent._counterfactual_values(
        self,
        features,
        legal_actions,
        reward,
    )
    search_snapshot = decision.get("search_snapshot") or {}
    search_eval = search_snapshot.get("search_eval")
    scores = {}
    reward_mix = self.adaptation_meta["reward_mix"]

    for action in legal_actions:
      score = 0.48 * heuristic_targets.get(action, 0.0) + 0.20 * self._action_score(action, features)
      if search_eval:
        detail = search_eval["detail"][action]
        score += 0.12 * detail["rollout"] + 0.08 * detail["response"] + 0.06 * detail["policy_bias"]
      if action == chosen_action:
        score += reward_mix * reward
      if action == base_action:
        score += 0.06 if reward >= 0 else -0.03
      scores[action] = score

    return self._softmax_distribution(scores, legal_actions, temperature=0.75)

  def _update_refinement_weights(self, snapshot, target_policy, legal_actions, leverage):
    components = {
        "strategy": snapshot["strategy_policy"],
        "average": snapshot["average_policy"],
        "learned": snapshot["learned_policy"],
        "counterfactual": snapshot["counterfactual_policy"],
        "search": (
            snapshot["search_eval"]["search_policy"] if snapshot["search_eval"] else self._normalize_distribution({}, legal_actions)
        ),
    }
    anchor_policy = snapshot["anchor_policy"]
    learning_rate = self.adaptation_meta["refinement_learning_rate"]
    decay = self.adaptation_meta["search_weight_decay"]

    for name in self.REFINEMENT_COMPONENTS:
      component = components[name]
      target_expectation = sum(target_policy.get(action, 0.0) * component.get(action, 0.0) for action in legal_actions)
      anchor_expectation = sum(anchor_policy.get(action, 0.0) * component.get(action, 0.0) for action in legal_actions)
      gradient = leverage * (target_expectation - anchor_expectation)
      updated = self.refinement_weights[name] + learning_rate * gradient - decay * self.refinement_weights[name]
      self.refinement_weights[name] = max(0.02, updated)

    self._normalize_named_weights(self.refinement_weights, self.REFINEMENT_COMPONENTS)

  def _update_search_weights(self, snapshot, target_policy, legal_actions, leverage, base_action):
    search_eval = snapshot["search_eval"]
    detail = search_eval["detail"]
    current_policy = search_eval["search_policy"]
    learning_rate = self.adaptation_meta["search_learning_rate"]
    decay = self.adaptation_meta["search_weight_decay"]

    for name in self.SEARCH_COMPONENTS:
      target_expectation = 0.0
      current_expectation = 0.0
      for action in legal_actions:
        component_value = 1.0 if name == "base_action_bonus" and action == base_action else detail[action].get(name, 0.0)
        target_expectation += target_policy.get(action, 0.0) * component_value
        current_expectation += current_policy.get(action, 0.0) * component_value
      gradient = leverage * (target_expectation - current_expectation)
      updated = self.search_weights[name] + learning_rate * gradient - decay * self.search_weights[name]
      self.search_weights[name] = max(0.0, updated)

    self._normalize_named_weights(self.search_weights, self.SEARCH_COMPONENTS)

  def _update_thresholds(self, snapshot, target_policy, reward, chosen_action, leverage):
    search_eval = snapshot["search_eval"]
    default_action = snapshot["default_action"]
    base_action = snapshot["base_action"]
    anchor_best = max(snapshot["anchor_policy"], key=snapshot["anchor_policy"].get)
    learning_rate = self.adaptation_meta["threshold_learning_rate"]
    decay = self.adaptation_meta["threshold_decay"]

    missed_search = 0.0
    false_positive = 0.0
    good_override = 0.0

    if search_eval:
      best_action = search_eval["best_action"]
      advantage = target_policy.get(best_action, 0.0) - target_policy.get(default_action, 0.0)
      if best_action != chosen_action and reward < -0.05 and advantage > 0.02:
        missed_search = min(1.0, leverage + abs(reward) * 0.30)
      if best_action == chosen_action and reward > 0.05:
        good_override = min(1.0, leverage + reward * 0.25)
      if best_action == chosen_action and reward < -0.05:
        false_positive = min(1.0, leverage + abs(reward) * 0.30)
      if best_action != chosen_action and chosen_action == default_action and reward > 0.05:
        false_positive = max(false_positive, min(1.0, leverage + reward * 0.20))

    good_anchor = 0.0
    bad_anchor = 0.0
    if default_action != base_action and chosen_action == default_action:
      if reward > 0.05:
        good_anchor = min(1.0, reward)
      elif reward < -0.05:
        bad_anchor = min(1.0, abs(reward))
    if anchor_best == chosen_action and reward > 0.05:
      good_anchor = max(good_anchor, min(1.0, reward))
    if anchor_best == chosen_action and reward < -0.05:
      bad_anchor = max(bad_anchor, min(1.0, abs(reward)))

    directional_updates = {
        "search_gate_min": -0.030 * (missed_search + good_override) + 0.034 * false_positive,
        "search_override_margin": -0.020 * (missed_search + good_override) + 0.024 * false_positive,
        "search_blended_margin": -0.014 * (missed_search + good_override) + 0.016 * false_positive,
        "search_support_floor": -0.012 * missed_search + 0.014 * false_positive,
        "search_confidence_floor": -0.016 * (missed_search + good_override) + 0.020 * false_positive,
        "learned_override_margin": -0.016 * good_anchor + 0.020 * bad_anchor,
    }

    for name in self.THRESHOLD_NAMES:
      lower, upper = self.THRESHOLD_BOUNDS[name]
      updated = self.thresholds[name] + learning_rate * leverage * directional_updates[name]
      updated -= decay * (self.thresholds[name] - self.DEFAULT_THRESHOLDS[name])
      self.thresholds[name] = self._clamp(updated, lower, upper)

  def _normalize_named_weights(self, mapping, names):
    total = sum(max(0.0, mapping[name]) for name in names)
    if total <= 0:
      uniform = 1.0 / max(len(names), 1)
      for name in names:
        mapping[name] = uniform
      return
    for name in names:
      mapping[name] = max(0.0, mapping[name]) / total


def setup_ai():
  return AdversarialSearchMCCFRV3Agent(training_enabled=False, exploration=0.0)
