import copy
import json
import math
import os

from lucas_agents.adversarial_search_mccfr_v2.adversarial_search_mccfr_v2_agent import (
    AdversarialSearchMCCFRV2Agent,
)
from lucas_agents.learnable_discounted_mccfr.learnable_discounted_mccfr_agent import (
    LearnableDiscountedMCCFRAgent,
)


class AdversarialSearchMCCFRV31Agent(AdversarialSearchMCCFRV2Agent):
  """
  v3.1 keeps v3's learnable refinement layer, but regularizes search more
  aggressively so the agent is less likely to over-trust a brittle opponent
  model or drift too far from the anchor policy during training.
  """

  REFINEMENT_COMPONENTS = ("strategy", "average", "learned", "counterfactual", "search")
  SEARCH_COMPONENTS = (
      "rollout",
      "response",
      "learned",
      "counterfactual",
      "policy_bias",
      "anchor_alignment",
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
      "learned_override_margin": (0.05, 0.30),
      "search_gate_min": (0.34, 0.88),
      "search_override_margin": (0.08, 0.34),
      "search_blended_margin": (0.02, 0.22),
      "search_support_floor": (0.14, 0.48),
      "search_confidence_floor": (0.50, 0.90),
  }
  DEFAULT_REFINEMENT_PRIOR = {
      "strategy": 0.20,
      "average": 0.46,
      "learned": 0.18,
      "counterfactual": 0.10,
      "search": 0.06,
  }
  DEFAULT_SEARCH_PRIOR = {
      "rollout": 0.31,
      "response": 0.18,
      "learned": 0.18,
      "counterfactual": 0.11,
      "policy_bias": 0.11,
      "anchor_alignment": 0.08,
      "base_action_bonus": 0.03,
  }
  DEFAULT_THRESHOLD_PRIOR = {
      "learned_override_margin": 0.12,
      "search_gate_min": 0.56,
      "search_override_margin": 0.17,
      "search_blended_margin": 0.08,
      "search_support_floor": 0.25,
      "search_confidence_floor": 0.66,
  }
  DEFAULT_ADAPTATION_META = {
      "search_learning_rate": 0.014,
      "refinement_learning_rate": 0.011,
      "threshold_learning_rate": 0.008,
      "search_weight_decay": 0.0008,
      "threshold_decay": 0.0005,
      "reward_mix": 0.46,
      "search_prior_shrink": 0.020,
      "refinement_prior_shrink": 0.016,
      "threshold_prior_shrink": 0.018,
      "opponent_model_prior_count": 18.0,
      "opponent_model_floor": 0.20,
      "search_update_count": 0,
  }
  DEFAULT_REFINEMENT_WEIGHTS = DEFAULT_REFINEMENT_PRIOR
  DEFAULT_SEARCH_WEIGHTS = DEFAULT_SEARCH_PRIOR
  DEFAULT_THRESHOLDS = DEFAULT_THRESHOLD_PRIOR

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
      search_prior_shrink=None,
      refinement_prior_shrink=None,
      threshold_prior_shrink=None,
      opponent_model_prior_count=None,
      opponent_model_floor=None,
  ):
    self.policy_path = policy_path or os.path.join(
        os.path.dirname(__file__), "adversarial_search_mccfr_v3_1_policy.json"
    )
    self.seed_policy_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "adversarial_search_mccfr_v3",
        "adversarial_search_mccfr_v3_policy.json",
    )
    self.fallback_policy_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "adversarial_search_mccfr_v2",
        "adversarial_search_mccfr_v2_policy.json",
    )
    self.adaptation_meta = dict(self.DEFAULT_ADAPTATION_META)
    overrides = {
        "search_learning_rate": search_learning_rate,
        "refinement_learning_rate": refinement_learning_rate,
        "threshold_learning_rate": threshold_learning_rate,
        "search_weight_decay": search_weight_decay,
        "threshold_decay": threshold_decay,
        "reward_mix": reward_mix,
        "search_prior_shrink": search_prior_shrink,
        "refinement_prior_shrink": refinement_prior_shrink,
        "threshold_prior_shrink": threshold_prior_shrink,
        "opponent_model_prior_count": opponent_model_prior_count,
        "opponent_model_floor": opponent_model_floor,
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
        refinement_weights=(refinement_weights or self.DEFAULT_REFINEMENT_PRIOR),
        search_weights=(search_weights or self.DEFAULT_SEARCH_PRIOR),
        thresholds=(thresholds or self.DEFAULT_THRESHOLD_PRIOR),
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

    for name, value in self.DEFAULT_REFINEMENT_PRIOR.items():
      self.refinement_weights.setdefault(name, value)
    for name, value in self.DEFAULT_SEARCH_PRIOR.items():
      self.search_weights.setdefault(name, value)
    for name, value in self.DEFAULT_THRESHOLD_PRIOR.items():
      self.thresholds.setdefault(name, value)

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
          anchor=anchor,
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

  def _search_context(self, valid_actions, features, round_state):
    base_context = super()._search_context(valid_actions, features, round_state)
    opponent_model = self._opponent_model_summary()
    reliability = opponent_model["reliability"]
    leverage = self._clamp(
        base_context["leverage"] * (0.82 + 0.18 * reliability),
        0.0,
        1.0,
    )
    reliability_penalty = 0.06 * (1.0 - reliability)
    enabled = leverage >= self.thresholds["search_gate_min"] + reliability_penalty
    reasons = list(base_context["reasons"])
    if reliability < 0.45:
      reasons.append("opponent_model_uncertain")
    return {
        "enabled": enabled,
        "leverage": leverage,
        "raise_ratio": base_context["raise_ratio"],
        "reasons": reasons,
        "opponent_model": opponent_model,
    }

  def _search_evaluations(
      self,
      valid_actions,
      features,
      legal_actions,
      strategy,
      average,
      anchor,
      counterfactual,
      base_action,
      round_state,
      leverage,
  ):
    raw_scores = {}
    detail = {}
    opponent_model = self._opponent_model_summary()
    reliability = opponent_model["reliability"]

    for action in legal_actions:
      rollout_value = self._rollout_value(action, features, valid_actions, round_state)
      response_value, responses = self._opponent_response_value(action, features, round_state)
      learned_value = self._action_score(action, features)
      policy_bias = 0.5 * strategy.get(action, 0.0) + 0.5 * average.get(action, 0.0)
      anchor_alignment = self._anchor_alignment(anchor, base_action, action)
      score = (
          self.search_weights["rollout"] * rollout_value
          + self.search_weights["response"] * (reliability * response_value)
          + self.search_weights["learned"] * learned_value
          + self.search_weights["counterfactual"] * counterfactual.get(action, 0.0)
          + self.search_weights["policy_bias"] * policy_bias
          + self.search_weights["anchor_alignment"] * anchor_alignment
      )
      if action == base_action:
        score += self.search_weights["base_action_bonus"]
      raw_scores[action] = score
      detail[action] = {
          "score": score,
          "rollout": rollout_value,
          "response": reliability * response_value,
          "learned": learned_value,
          "counterfactual": counterfactual.get(action, 0.0),
          "policy_bias": policy_bias,
          "anchor_alignment": anchor_alignment,
          "responses": responses,
      }

    search_policy = self._softmax_distribution(raw_scores, legal_actions, temperature=0.74)
    blended = self._zero_map()
    base_mix = self.refinement_weights["search"] + 0.08 * leverage
    search_mix = min(0.16, base_mix * (0.45 + 0.55 * reliability))
    for action in legal_actions:
      blended[action] = (1.0 - search_mix) * anchor.get(action, 0.0) + search_mix * search_policy.get(action, 0.0)
    blended = self._normalize_distribution(blended, legal_actions)

    ranked = sorted(
        legal_actions,
        key=lambda action: (search_policy.get(action, 0.0), blended.get(action, 0.0)),
        reverse=True,
    )
    best_action = ranked[0]
    second_action = ranked[1] if len(ranked) > 1 else ranked[0]
    search_margin = search_policy.get(best_action, 0.0) - search_policy.get(second_action, 0.0)
    response_clarity = self._response_clarity(detail[best_action]["responses"]) * reliability
    anchor_gap = max(0.0, anchor.get(base_action, 0.0) - anchor.get(best_action, 0.0))
    confidence = self._clamp(
        0.44
        + 0.70 * search_margin
        + 0.16 * response_clarity
        + 0.10 * leverage
        + 0.10 * reliability
        - 0.26 * anchor_gap,
        0.0,
        1.0,
    )

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
        "opponent_model": opponent_model,
        "anchor_gap": anchor_gap,
    }

  def _should_override_with_search(self, default_action, anchor, search_eval, leverage):
    best_action = search_eval["best_action"]
    if best_action == default_action:
      return True

    reliability = search_eval["opponent_model"]["reliability"]
    search_margin = search_eval["search_margin"]
    blended_margin = (
        search_eval["blended_policy"].get(best_action, 0.0)
        - search_eval["blended_policy"].get(default_action, 0.0)
    )
    search_support = search_eval["search_policy"].get(best_action, 0.0)
    anchor_support = anchor.get(best_action, 0.0)
    default_anchor = anchor.get(default_action, 0.0)
    confidence = search_eval["confidence"]
    anchor_gap = max(0.0, default_anchor - anchor_support)
    required_margin = (
        self.thresholds["search_override_margin"]
        - 0.02 * leverage
        + 0.05 * (1.0 - reliability)
        + 0.55 * anchor_gap
    )
    required_blended = (
        self.thresholds["search_blended_margin"]
        + 0.03 * (1.0 - reliability)
        + 0.30 * anchor_gap
    )
    required_confidence = (
        self.thresholds["search_confidence_floor"]
        - 0.02 * leverage
        + 0.06 * (1.0 - reliability)
        + 0.12 * anchor_gap
    )

    return (
        search_margin >= required_margin
        and blended_margin >= required_blended
        and search_support >= self.thresholds["search_support_floor"] + 0.04 * anchor_gap
        and anchor_support >= max(0.10, default_anchor - (0.08 + 0.08 * reliability))
        and confidence >= required_confidence
        and (reliability >= 0.32 or confidence >= 0.80)
    )

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
      score = 0.48 * heuristic_targets.get(action, 0.0) + 0.18 * self._action_score(action, features)
      if search_eval:
        detail = search_eval["detail"][action]
        score += 0.10 * detail["rollout"] + 0.06 * detail["response"] + 0.06 * detail["policy_bias"]
        score += 0.05 * detail["anchor_alignment"]
      if action == chosen_action:
        score += reward_mix * reward
      if action == base_action:
        score += 0.06 if reward >= 0 else -0.02
      scores[action] = score

    return self._softmax_distribution(scores, legal_actions, temperature=0.80)

  def _update_refinement_weights(self, snapshot, target_policy, legal_actions, leverage):
    components = {
        "strategy": snapshot["strategy_policy"],
        "average": snapshot["average_policy"],
        "learned": snapshot["learned_policy"],
        "counterfactual": snapshot["counterfactual_policy"],
        "search": (
            snapshot["search_eval"]["search_policy"]
            if snapshot["search_eval"]
            else self._normalize_distribution({}, legal_actions)
        ),
    }
    anchor_policy = snapshot["anchor_policy"]
    learning_rate = self.adaptation_meta["refinement_learning_rate"]
    decay = self.adaptation_meta["search_weight_decay"]
    shrink = self.adaptation_meta["refinement_prior_shrink"]

    for name in self.REFINEMENT_COMPONENTS:
      component = components[name]
      target_expectation = sum(target_policy.get(action, 0.0) * component.get(action, 0.0) for action in legal_actions)
      anchor_expectation = sum(anchor_policy.get(action, 0.0) * component.get(action, 0.0) for action in legal_actions)
      gradient = leverage * (target_expectation - anchor_expectation)
      updated = self.refinement_weights[name] + learning_rate * gradient - decay * self.refinement_weights[name]
      updated += shrink * (self.DEFAULT_REFINEMENT_PRIOR[name] - updated)
      self.refinement_weights[name] = max(0.02, updated)

    self._normalize_named_weights(self.refinement_weights, self.REFINEMENT_COMPONENTS)

  def _update_search_weights(self, snapshot, target_policy, legal_actions, leverage, base_action):
    search_eval = snapshot["search_eval"]
    detail = search_eval["detail"]
    current_policy = search_eval["search_policy"]
    reliability = search_eval["opponent_model"]["reliability"]
    learning_rate = self.adaptation_meta["search_learning_rate"]
    decay = self.adaptation_meta["search_weight_decay"]
    shrink = self.adaptation_meta["search_prior_shrink"]
    effective_leverage = leverage * (0.70 + 0.30 * reliability)

    for name in self.SEARCH_COMPONENTS:
      target_expectation = 0.0
      current_expectation = 0.0
      for action in legal_actions:
        component_value = 1.0 if name == "base_action_bonus" and action == base_action else detail[action].get(name, 0.0)
        target_expectation += target_policy.get(action, 0.0) * component_value
        current_expectation += current_policy.get(action, 0.0) * component_value
      gradient = effective_leverage * (target_expectation - current_expectation)
      updated = self.search_weights[name] + learning_rate * gradient - decay * self.search_weights[name]
      updated += shrink * (self.DEFAULT_SEARCH_PRIOR[name] - updated)
      self.search_weights[name] = max(0.0, updated)

    self._normalize_named_weights(self.search_weights, self.SEARCH_COMPONENTS)

  def _update_thresholds(self, snapshot, target_policy, reward, chosen_action, leverage):
    search_eval = snapshot["search_eval"]
    default_action = snapshot["default_action"]
    base_action = snapshot["base_action"]
    anchor_best = max(snapshot["anchor_policy"], key=snapshot["anchor_policy"].get)
    learning_rate = self.adaptation_meta["threshold_learning_rate"]
    decay = self.adaptation_meta["threshold_decay"]
    shrink = self.adaptation_meta["threshold_prior_shrink"]

    missed_search = 0.0
    false_positive = 0.0
    good_override = 0.0
    reliability = 1.0

    if search_eval:
      reliability = search_eval["opponent_model"]["reliability"]
      best_action = search_eval["best_action"]
      advantage = target_policy.get(best_action, 0.0) - target_policy.get(default_action, 0.0)
      if best_action != chosen_action and reward < -0.05 and advantage > 0.02:
        missed_search = min(1.0, leverage + abs(reward) * 0.25)
      if best_action == chosen_action and reward > 0.05:
        good_override = min(1.0, leverage + reward * 0.22)
      if best_action == chosen_action and reward < -0.05:
        false_positive = min(1.0, leverage + abs(reward) * 0.36)
      if best_action != chosen_action and chosen_action == default_action and reward > 0.05:
        false_positive = max(false_positive, min(1.0, leverage + reward * 0.22))

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

    caution_scale = 1.0 + 0.30 * (1.0 - reliability)
    directional_updates = {
        "search_gate_min": -0.018 * (missed_search + good_override) + 0.034 * caution_scale * false_positive,
        "search_override_margin": -0.014 * (missed_search + good_override) + 0.026 * caution_scale * false_positive,
        "search_blended_margin": -0.010 * (missed_search + good_override) + 0.018 * caution_scale * false_positive,
        "search_support_floor": -0.008 * missed_search + 0.015 * caution_scale * false_positive,
        "search_confidence_floor": -0.012 * (missed_search + good_override) + 0.022 * caution_scale * false_positive,
        "learned_override_margin": -0.016 * good_anchor + 0.018 * bad_anchor,
    }

    for name in self.THRESHOLD_NAMES:
      lower, upper = self.THRESHOLD_BOUNDS[name]
      updated = self.thresholds[name] + learning_rate * leverage * directional_updates[name]
      updated -= decay * (self.thresholds[name] - self.DEFAULT_THRESHOLD_PRIOR[name])
      updated += shrink * (self.DEFAULT_THRESHOLD_PRIOR[name] - updated)
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

  def _anchor_alignment(self, anchor, base_action, action):
    support = anchor.get(action, 0.0)
    base_support = anchor.get(base_action, 0.0)
    gap = max(0.0, base_support - support)
    return self._clamp(support + (0.08 if action == base_action else 0.0) - 0.70 * gap, 0.0, 1.0)

  def _opponent_model_summary(self):
    total_actions = 0
    total_raises = 0
    total_folds = 0
    for stats in self.opponent_actions.values():
      total_raises += stats["raise"]
      total_folds += stats["fold"]
      total_actions += stats["raise"] + stats["call"] + stats["fold"]

    prior_count = max(1.0, self.adaptation_meta["opponent_model_prior_count"])
    prior_aggression = 0.25
    prior_fold = 0.18
    smoothed_aggression = (
        (total_raises + prior_count * prior_aggression) / (total_actions + prior_count)
    )
    smoothed_fold = (
        (total_folds + prior_count * prior_fold) / (total_actions + prior_count)
    )
    sample_factor = total_actions / float(total_actions + prior_count)
    variance = (
        smoothed_aggression * (1.0 - smoothed_aggression)
        + smoothed_fold * (1.0 - smoothed_fold)
    ) / max(total_actions + prior_count, 1.0)
    instability = self._clamp(math.sqrt(max(variance, 0.0)) * 2.2, 0.0, 1.0)
    reliability = self._clamp(
        self.adaptation_meta["opponent_model_floor"] + sample_factor * (1.0 - instability),
        self.adaptation_meta["opponent_model_floor"],
        1.0,
    )
    return {
        "total_actions": total_actions,
        "smoothed_aggression": smoothed_aggression,
        "smoothed_fold_rate": smoothed_fold,
        "sample_factor": sample_factor,
        "instability": instability,
        "reliability": reliability,
    }


def setup_ai():
  return AdversarialSearchMCCFRV31Agent(training_enabled=False, exploration=0.0)
