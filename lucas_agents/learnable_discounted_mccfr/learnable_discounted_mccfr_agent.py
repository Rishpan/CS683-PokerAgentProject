import copy
import json
import os

from lucas_agents.discounted_mccfr_plus.discounted_mccfr_plus_agent import DiscountedMCCFRPlusAgent


class LearnableDiscountedMCCFRAgent(DiscountedMCCFRPlusAgent):
  """
  Discounted MCCFR-style agent with trainable linear action coefficients.

  The agent keeps the regret-matching machinery from DiscountedMCCFRPlusAgent,
  but replaces the hardcoded action scores with persistent action-specific
  weights that are updated online from round outcomes.
  """

  FEATURE_NAMES = (
      "bias",
      "strength",
      "pot_odds",
      "pressure",
      "draws",
      "aggression",
      "fold_rate",
      "position",
      "spr_short",
      "free_action",
      "street_weight",
  )

  DEFAULT_ACTION_WEIGHTS = {
      "fold": {
          "bias": 0.48,
          "strength": -1.0,
          "pot_odds": 0.20,
          "pressure": 0.40,
          "draws": 0.0,
          "aggression": 0.0,
          "fold_rate": 0.0,
          "position": 0.0,
          "spr_short": 0.0,
          "free_action": -0.22,
          "street_weight": 0.0,
      },
      "call": {
          "bias": 0.18,
          "strength": 1.0,
          "pot_odds": -0.92,
          "pressure": -0.12,
          "draws": 0.0315,
          "aggression": 0.10,
          "fold_rate": 0.0,
          "position": 0.03,
          "spr_short": 0.0,
          "free_action": 0.10,
          "street_weight": 0.04,
      },
      "raise": {
          "bias": 0.18,
          "strength": 1.0,
          "pot_odds": -0.10,
          "pressure": -0.10,
          "draws": 0.07,
          "aggression": -0.06,
          "fold_rate": 0.24,
          "position": 0.06,
          "spr_short": 0.05,
          "free_action": 0.04,
          "street_weight": 0.10,
      },
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
  ):
    self.policy_path = policy_path or os.path.join(
        os.path.dirname(__file__), "learnable_discounted_mccfr_policy.json"
    )
    self.action_weights = copy.deepcopy(self.DEFAULT_ACTION_WEIGHTS)
    self.learning_rate = learning_rate
    self.weight_decay = weight_decay
    self.value_mix = value_mix
    self.weight_update_count = 0
    super().__init__(
        policy_path=self.policy_path,
        training_enabled=training_enabled,
        exploration=exploration,
        prior_weight=prior_weight,
        save_interval=save_interval,
        discount_interval=discount_interval,
        postflop_simulations=postflop_simulations,
        random_seed=random_seed,
    )

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

  def _prior_strategy(self, features, legal_actions, base_action):
    raw = self._zero_map()
    for action in legal_actions:
      score = self._action_score(action, features)
      floor = 0.02 if action == "call" else 0.0
      raw[action] = max(floor, score)

    strength = features["strength"]
    pot_odds = features["pot_odds"]
    pressure = features["pressure"]
    draws = features["draws"]

    if "raise" in legal_actions and strength >= max(0.54, pot_odds + 0.12):
      raw["raise"] += 0.60
    if "raise" in legal_actions and draws >= 2 and pressure <= 0.18:
      raw["raise"] += 0.18
    if "call" in legal_actions and strength >= max(0.42, pot_odds + 0.04):
      raw["call"] += 0.28
    if "fold" in legal_actions and pressure > 0.30 and strength < 0.46:
      raw["fold"] += 0.60

    raw[base_action] += 1.35
    total = sum(raw.values())
    if total <= 0:
      uniform = 1.0 / max(len(legal_actions), 1)
      return {action: (uniform if action in legal_actions else 0.0) for action in self.ACTIONS}
    return {action: raw[action] / total for action in self.ACTIONS}

  def _counterfactual_values(self, features, legal_actions, reward):
    del reward
    values = self._zero_map()
    street_weight = self.STREET_WEIGHT[features["street"]]
    for action in legal_actions:
      score = self._action_score(action, features)
      if action == "fold":
        values[action] = score - 0.60
      else:
        values[action] = street_weight * score
    if "fold" in legal_actions and features["pressure"] > 0.24:
      values["fold"] += 0.10
    return values

  def _learn_from_decision(self, decision, reward):
    heuristic_targets = DiscountedMCCFRPlusAgent._counterfactual_values(
        self,
        decision["features"],
        decision["legal_actions"],
        reward,
    )
    realized = decision["chosen_action"]
    heuristic_targets[realized] = self.value_mix * reward + (1.0 - self.value_mix) * heuristic_targets[realized]

    for action in decision["legal_actions"]:
      prediction = self._action_score(action, decision["features"])
      target = heuristic_targets[action]
      error = max(-2.0, min(2.0, target - prediction))
      step_scale = 1.0 if action == realized else 0.30
      self._update_action_weights(action, decision["features"], self.learning_rate * step_scale * error)

    self.weight_update_count += 1

  def _update_action_weights(self, action, features, scaled_error):
    vector = self._feature_vector(features)
    weights = self.action_weights[action]
    for feature_name in self.FEATURE_NAMES:
      decay = self.weight_decay * weights[feature_name]
      weights[feature_name] += scaled_error * vector[feature_name] - decay

  def _action_score(self, action, features):
    vector = self._feature_vector(features)
    return sum(self.action_weights[action][name] * vector[name] for name in self.FEATURE_NAMES)

  def _feature_vector(self, features):
    return {
        "bias": 1.0,
        "strength": features["strength"],
        "pot_odds": features["pot_odds"],
        "pressure": features["pressure"],
        "draws": float(features["draws"]),
        "aggression": self._opponent_aggression(),
        "fold_rate": self._opponent_fold_rate(),
        "position": float(features["position"]),
        "spr_short": 1.0 if features["spr"] <= 2.5 else 0.0,
        "free_action": 1.0 if features.get("free_action") else 0.0,
        "street_weight": self.STREET_WEIGHT[features["street"]],
    }


def setup_ai():
  return LearnableDiscountedMCCFRAgent(training_enabled=False, exploration=0.0)
