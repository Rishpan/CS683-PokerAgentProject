"""Tiny adversarial lookahead over the shared abstraction.

This is intentionally shallow: it does not try to reconstruct the full poker
tree. Instead it scores each legal action under a pessimistic opponent response
model on the same abstract state. That is enough to exercise the search path
now while keeping the abstraction reusable.
"""


class AdversarialSearch:

  def choose_action(self, legal_actions, features, cfr_strategy):
    best_action = None
    best_value = None
    for action in legal_actions:
      value = self._worst_case_value(action, features) + 0.05 * cfr_strategy.get(action, 0.0)
      if best_value is None or value > best_value:
        best_action = action
        best_value = value
    return best_action or ("call" if "call" in legal_actions else "fold")

  def _worst_case_value(self, action, features):
    responses = self._opponent_responses(action)
    return min(self._response_value(action, response, features) for response in responses)

  def _opponent_responses(self, action):
    if action == "fold":
      return ("terminal",)
    if action == "call":
      return ("check_back", "pressure")
    return ("folds", "calls", "reraises")

  def _response_value(self, action, response, features):
    strength = features["strength"]
    pot_odds = features["pot_odds"]
    history = features["history"]
    contested = 1.0 if history in {4, 5, 7} else 0.0

    if action == "fold":
      return -0.25
    if response == "terminal":
      return -0.25
    if response == "check_back":
      return strength - 0.5 * pot_odds
    if response == "pressure":
      return strength - pot_odds - 0.18 - 0.10 * contested
    if response == "folds":
      return 0.20 + 0.60 * pot_odds
    if response == "calls":
      return strength - 0.48 - 0.06 * contested
    if response == "reraises":
      return strength - 0.78 - 0.10 * contested
    return strength - pot_odds
