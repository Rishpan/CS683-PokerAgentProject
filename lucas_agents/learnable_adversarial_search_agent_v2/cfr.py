import json
import os
import random

ACTIONS = ("fold", "call", "raise")
DEFAULT_POLICY_PATH = os.path.join(os.path.dirname(__file__), "cfr_policy.json")


class TabularCFR:

  def __init__(
      self,
      policy_path=DEFAULT_POLICY_PATH,
      exploration=0.06,
      training_enabled=False,
      random_seed=None,
  ):
    self.policy_path = policy_path
    self.exploration = exploration
    self.training_enabled = training_enabled
    self.random = random.Random(random_seed)
    self.regret_sum = {}
    self.strategy_sum = {}
    self.round_decisions = []
    self.state_visits = set()
    self._load()

  def strategy(self, info_state, legal_actions):
    info_key = repr(info_state)
    regrets = self.regret_sum.setdefault(info_key, _zero_action_map())
    average = self.strategy_sum.setdefault(info_key, _zero_action_map())
    legal_actions = set(legal_actions)
    positive = {
        action: max(regrets[action], 0.0) if action in legal_actions else 0.0
        for action in ACTIONS
    }
    total_positive = sum(positive.values())
    if total_positive > 0:
      strategy = {
          action: positive[action] / total_positive if action in legal_actions else 0.0
          for action in ACTIONS
      }
    else:
      uniform = 1.0 / max(len(legal_actions), 1)
      strategy = {action: uniform if action in legal_actions else 0.0 for action in ACTIONS}

    if self.training_enabled and self.exploration > 0:
      uniform = 1.0 / max(len(legal_actions), 1)
      for action in ACTIONS:
        if action in legal_actions:
          strategy[action] = (1.0 - self.exploration) * strategy[action] + self.exploration * uniform

    for action in ACTIONS:
      average[action] += strategy[action]
    self.state_visits.add(info_key)
    return strategy

  def average_strategy(self, info_state, legal_actions):
    info_key = repr(info_state)
    totals = self.strategy_sum.get(info_key, _zero_action_map())
    total = sum(totals[action] for action in legal_actions)
    if total <= 0:
      return self.strategy(info_state, legal_actions)
    return {
        action: (totals[action] / total) if action in legal_actions else 0.0
        for action in ACTIONS
    }

  def sample_action(self, strategy):
    draw = self.random.random()
    cumulative = 0.0
    fallback = "call" if strategy.get("call", 0.0) > 0 else "fold"
    for action in ACTIONS:
      probability = strategy.get(action, 0.0)
      if probability <= 0:
        continue
      cumulative += probability
      if draw <= cumulative:
        return action
    return fallback

  def record_decision(self, info_state, legal_actions, action, features):
    if not self.training_enabled:
      return
    sample_policy = {name: features["policy"].get(name, 0.0) for name in ACTIONS}
    self.round_decisions.append(
        {
            "info_key": repr(info_state),
            "legal_actions": tuple(sorted(legal_actions)),
            "chosen_action": action,
            "sample_policy": sample_policy,
            "sample_prob": max(sample_policy.get(action, 0.0), 1e-12),
        }
    )

  def finish_round(self, terminal_utility):
    if not self.training_enabled:
      self.round_decisions = []
      return
    prefix_sample_prob = 1.0
    for decision in self.round_decisions:
      prefix_sample_prob *= decision["sample_prob"]
      self._update_regrets(decision, terminal_utility, prefix_sample_prob)
    self.round_decisions = []

  def save(self):
    os.makedirs(os.path.dirname(self.policy_path), exist_ok=True)
    with open(self.policy_path, "w", encoding="utf-8") as output:
      json.dump(
          {
              "regret_sum": self.regret_sum,
              "strategy_sum": self.strategy_sum,
              "meta": {"exploration": self.exploration},
          },
          output,
          indent=2,
          sort_keys=True,
      )

  def _load(self):
    if not os.path.exists(self.policy_path):
      return
    with open(self.policy_path, "r", encoding="utf-8") as source:
      payload = json.load(source)
    self.regret_sum = payload.get("regret_sum", {})
    self.strategy_sum = payload.get("strategy_sum", {})

  def _update_regrets(self, decision, terminal_utility, prefix_sample_prob):
    regrets = self.regret_sum.setdefault(decision["info_key"], _zero_action_map())
    sampled_advantages = _action_utilities(
        legal_actions=decision["legal_actions"],
        sample_policy=decision["sample_policy"],
        chosen_action=decision["chosen_action"],
        terminal_utility=terminal_utility,
        prefix_sample_prob=prefix_sample_prob,
    )
    for action in decision["legal_actions"]:
      regrets[action] += sampled_advantages[action]


def _action_utilities(legal_actions, sample_policy, chosen_action, terminal_utility, prefix_sample_prob):
  weight = float(terminal_utility) / max(float(prefix_sample_prob), 1e-12)
  increments = {}
  for action in legal_actions:
    probability = sample_policy.get(action, 0.0)
    if action == chosen_action:
      increments[action] = weight * (1.0 - probability)
    else:
      increments[action] = -weight * probability
  return increments


def _zero_action_map():
  return {action: 0.0 for action in ACTIONS}
