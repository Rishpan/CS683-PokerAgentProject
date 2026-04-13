import random

from lucas_agents.advanced_cfr.advanced_cfr_player import AdvancedCFRPlayer


class ResearchSuperiorAgent(AdvancedCFRPlayer):
  """
  Experimental stronger variant built on top of AdvancedCFRPlayer.

  Main ideas:
  - richer postflop rollouts for better equity estimates
  - less exploration when training so the policy sharpens faster
  - stronger exploitation of learned average strategy at inference time
  - more aggressive value betting and more disciplined folding under pressure
  - slower discounting to preserve useful regret signal longer
  """

  def __init__(
      self,
      policy_path=None,
      training_enabled=True,
      exploration=0.025,
      prior_weight=0.18,
      save_interval=250,
      discount_interval=900,
      postflop_simulations=96,
      random_seed=None,
  ):
    super().__init__(
        policy_path=policy_path,
        training_enabled=training_enabled,
        exploration=exploration,
        prior_weight=prior_weight,
        save_interval=save_interval,
        discount_interval=discount_interval,
        postflop_simulations=postflop_simulations,
        random_seed=random_seed,
    )
    self.random = random.Random(random_seed)

  def _prior_strategy(self, features, legal_actions, base_action):
    strength = features["strength"]
    pot_odds = features["pot_odds"]
    pressure = features["pressure"]
    draw_bonus = 0.07 * features["draws"]
    aggression = self._opponent_aggression()
    fold_rate = self._opponent_fold_rate()
    in_position = features["position"] == 1
    spr = features["spr"]

    raise_score = (
        strength
        + draw_bonus
        + 0.24 * fold_rate
        - 0.06 * aggression
        - 0.10 * pot_odds
        - 0.10 * pressure
        + (0.06 if in_position else 0.0)
        + (0.05 if spr <= 2.5 else 0.0)
    )
    call_score = (
        strength
        + 0.45 * draw_bonus
        - 0.92 * pot_odds
        - 0.12 * pressure
        + 0.10 * aggression
        + (0.03 if in_position else 0.0)
    )
    fold_score = 0.48 - strength + 0.40 * pressure + 0.20 * pot_odds

    raw = self._zero_map()
    raw["fold"] = max(0.0, fold_score) if "fold" in legal_actions else 0.0
    raw["call"] = max(0.02, call_score + 0.18) if "call" in legal_actions else 0.0
    raw["raise"] = max(0.0, raise_score + 0.18) if "raise" in legal_actions else 0.0

    if "raise" in legal_actions and strength >= max(0.54, pot_odds + 0.12):
      raw["raise"] += 0.60
    if "raise" in legal_actions and features["draws"] >= 2 and pressure <= 0.18:
      raw["raise"] += 0.18
    if "call" in legal_actions and strength >= max(0.42, pot_odds + 0.04):
      raw["call"] += 0.28
    if pressure > 0.30 and strength < 0.46:
      raw["fold"] += 0.60

    raw[base_action] += 1.35

    total = sum(raw.values())
    if total <= 0:
      uniform = 1.0 / max(len(legal_actions), 1)
      return {action: (uniform if action in legal_actions else 0.0) for action in self.ACTIONS}
    return {action: raw[action] / total for action in self.ACTIONS}

  def _counterfactual_values(self, features, legal_actions, reward):
    strength = features["strength"]
    pot_odds = features["pot_odds"]
    pressure = features["pressure"]
    street_weight = self.STREET_WEIGHT[features["street"]]
    draw_bonus = 0.06 * features["draws"]
    aggression = self._opponent_aggression()
    fold_rate = self._opponent_fold_rate()
    in_position = features["position"] == 1

    values = self._zero_map()
    values["fold"] = -0.12 - 0.36 * max(0.0, strength - 0.45)
    values["call"] = street_weight * (
        strength - 0.90 * pot_odds + draw_bonus - 0.20 * pressure + (0.02 if in_position else 0.0)
    )
    values["raise"] = street_weight * (
        strength
        + draw_bonus
        + 0.28 * fold_rate
        - 0.08 * aggression
        - 0.10 * pot_odds
        - 0.14 * pressure
        + 0.12
        + (0.04 if in_position else 0.0)
    )

    for action in self.ACTIONS:
      if action not in legal_actions:
        values[action] = 0.0
    if reward < 0 and "fold" in legal_actions and pressure > 0.24:
      values["fold"] += 0.12
    return values

  def _pick_action(self, info_key, strategy, features, legal_actions, base_action):
    if not self.training_enabled:
      average = self.strategy_sum.get(info_key)
      if average:
        total = sum(average.values())
        if total > 0:
          normalized = {action: average[action] / total for action in self.ACTIONS}
          learned_action = max(normalized, key=normalized.get)
          if learned_action == "raise" and normalized[learned_action] >= 0.60:
            return learned_action
          if learned_action != base_action and normalized[learned_action] >= 0.68:
            return learned_action
      return base_action
    return super()._pick_action(info_key, strategy, features, legal_actions, base_action)

  def _apply_discount(self):
    for table in (self.regret_sum, self.strategy_sum):
      for info_key, action_map in list(table.items()):
        for action in self.ACTIONS:
          action_map[action] *= 0.97
        if max(action_map.values()) < 1e-8:
          del table[info_key]


def setup_ai():
  return ResearchSuperiorAgent(training_enabled=False, exploration=0.0)
