import json
import os


ACTIONS = ("fold", "call", "raise")


class StrategyTable:
  def __init__(self):
    self.regret_sum = {}
    self.strategy_sum = {}

  def has_data(self):
    return bool(self.strategy_sum)

  def legal_strategy(self, info_key, legal_actions):
    regrets = self.regret_sum.setdefault(info_key, self._zero_map())
    positive = {
        action: max(regrets[action], 0.0) if action in legal_actions else 0.0
        for action in ACTIONS
    }
    total = sum(positive.values())
    if total > 0:
      return {
          action: positive[action] / total if action in legal_actions else 0.0
          for action in ACTIONS
      }
    uniform = 1.0 / max(len(legal_actions), 1)
    return {action: (uniform if action in legal_actions else 0.0) for action in ACTIONS}

  def average_strategy(self, info_key, legal_actions):
    strategy_sum = self.strategy_sum.get(info_key)
    if not strategy_sum:
      return self.legal_strategy(info_key, legal_actions)

    total = sum(strategy_sum[action] for action in legal_actions)
    if total <= 0:
      uniform = 1.0 / max(len(legal_actions), 1)
      return {action: (uniform if action in legal_actions else 0.0) for action in ACTIONS}
    return {
        action: (strategy_sum[action] / total) if action in legal_actions else 0.0
        for action in ACTIONS
    }

  def accumulate_average(self, info_key, strategy, weight=1.0):
    strategy_sum = self.strategy_sum.setdefault(info_key, self._zero_map())
    for action in ACTIONS:
      strategy_sum[action] += weight * strategy.get(action, 0.0)

  def apply_regret_update(self, info_key, action_values, node_value, legal_actions):
    regrets = self.regret_sum.setdefault(info_key, self._zero_map())
    for action in legal_actions:
      regrets[action] += action_values[action] - node_value

  def save(self, path, metadata=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    payload = {
        "regret_sum": self.regret_sum,
        "strategy_sum": self.strategy_sum,
        "metadata": metadata or {},
    }
    with open(path, "w", encoding="utf-8") as output:
      json.dump(payload, output, indent=2, sort_keys=True)

  @classmethod
  def load(cls, path):
    table = cls()
    if not os.path.exists(path):
      return table, {}
    with open(path, "r", encoding="utf-8") as source:
      payload = json.load(source)
    table.regret_sum = payload.get("regret_sum", {})
    table.strategy_sum = payload.get("strategy_sum", {})
    return table, payload.get("metadata", {})

  def _zero_map(self):
    return {action: 0.0 for action in ACTIONS}
