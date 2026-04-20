class AdversarialSearch:

  def choose_action(self, legal_actions, features, cfr_strategy):
    best_action = None
    best_value = None
    for action in legal_actions:
      value = self._score(action, features) + 0.05 * cfr_strategy.get(action, 0.0)
      if best_value is None or value > best_value:
        best_action = action
        best_value = value
    return best_action or ("call" if "call" in legal_actions else "fold")

  def _score(self, action, features):
    equity = features.get("equity", 0.0)
    position = 0.03 if features.get("position", 0) == 1 else 0.0
    pressure = 0.12 if features.get("pot_bucket", 0) == 1 else 0.0
    board_penalty = 0.04 if features.get("board_bucket") in {3, 4, 5} else 0.0
    history_penalty = 0.06 if features.get("history_bucket") in {2, 4, 6, 8, 13, 14} else 0.0

    if action == "fold":
      return -0.20 - 0.25 * equity
    if action == "call":
      return equity + position - pressure - 0.5 * board_penalty
    if action == "raise":
      return equity + position - pressure - board_penalty - history_penalty + 0.04
    return equity
