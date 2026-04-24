import json
import os
from collections import Counter


ACTIONS = ("fold", "call", "raise")


class StrategyTable:
  def __init__(self):
    self.regret_sum = {}
    self.strategy_sum = {}
    self.lookup_stats = {
        "missing_info_keys": Counter(),
        "visited_info_keys": Counter(),
    }

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
      self._record_lookup(info_key, found=False)
      return self.legal_strategy(info_key, legal_actions)

    self._record_lookup(info_key, found=True)
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
    self.save_lookup_stats(path)

  @classmethod
  def load(cls, path):
    table = cls()
    if not os.path.exists(path):
      return table, {}
    with open(path, "r", encoding="utf-8") as source:
      payload = json.load(source)
    table.regret_sum = payload.get("regret_sum", {})
    table.strategy_sum = payload.get("strategy_sum", {})
    table._load_lookup_stats(path)
    return table, payload.get("metadata", {})

  def _zero_map(self):
    return {action: 0.0 for action in ACTIONS}

  def _record_lookup(self, info_key, found):
    bucket = "visited_info_keys" if found else "missing_info_keys"
    self.lookup_stats[bucket][info_key] += 1

  def save_lookup_stats(self, path):
    stats_path = self._lookup_stats_path(path)
    os.makedirs(os.path.dirname(stats_path), exist_ok=True)
    payload = {
        "missing_info_keys": self._sorted_counter_dict(self.lookup_stats["missing_info_keys"]),
        "visited_info_keys": self._sorted_counter_dict(self.lookup_stats["visited_info_keys"]),
        "missing_total": sum(self.lookup_stats["missing_info_keys"].values()),
        "visited_total": sum(self.lookup_stats["visited_info_keys"].values()),
    }
    with open(stats_path, "w", encoding="utf-8") as output:
      json.dump(payload, output, indent=2)

  def _load_lookup_stats(self, path):
    stats_path = self._lookup_stats_path(path)
    if not os.path.exists(stats_path):
      return
    with open(stats_path, "r", encoding="utf-8") as source:
      payload = json.load(source)
    self.lookup_stats["missing_info_keys"] = Counter(payload.get("missing_info_keys", {}))
    self.lookup_stats["visited_info_keys"] = Counter(payload.get("visited_info_keys", {}))

  def _lookup_stats_path(self, path):
    if path.endswith(".json"):
      return f"{path[:-5]}.stats.json"
    return f"{path}.stats.json"

  def _sorted_counter_dict(self, counter):
    return {
        info_key: count
        for info_key, count in sorted(counter.items(), key=lambda item: (-item[1], item[0]))
    }
