"""Small tabular regret-minimization policy over the shared abstraction.

This module uses an outcome-sampling MCCFR-style update rather than a
handcrafted post-hoc utility heuristic.

Why MCCFR instead of full CFR here:
- vanilla CFR needs a full game-tree traversal every iteration
- this project only observes one sampled hand trajectory at training time
- outcome-sampling MCCFR is designed for exactly that sampled setting

Primary sources:
- Zinkevich et al. 2007, Eq. (7)-(8) for counterfactual regret and regret
  matching:
  https://papers.nips.cc/paper/3306-regret-minimization-in-games-with-incomplete-information
- Lanctot et al. 2009, Eq. (10) for the outcome-sampling MCCFR regret
  estimator:
  https://webdocs.cs.ualberta.ca/~bowling/papers/09nips-mccfr.pdf
"""

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

    # Zinkevich et al. (2007), Eq. (8): regret matching selects actions in
    # proportion to positive cumulative regret. If all regrets are non-positive,
    # fall back to a uniform distribution on legal actions.
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

    # In outcome-sampling MCCFR, every sampled action must keep non-zero
    # probability. We therefore mix in a small uniform exploration policy during
    # training. This makes the acting policy also the sampling policy used by
    # the regret estimator.
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
    # We only observe one sampled terminal history z from the played hand. Since
    # there is no full game-tree traversal available online, the natural update
    # is outcome-sampling MCCFR rather than vanilla CFR.
    #
    # Lanctot et al. (2009) show that the sampled regrets match CFR's regrets in
    # expectation. We therefore replay the visited abstract states from this hand
    # and apply the sampled regret increment from their Eq. (10).
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

    # Zinkevich et al. (2007), Eq. (7), define cumulative regret for each action
    # in an information set. In outcome-sampling MCCFR, `_action_utilities`
    # returns the sampled estimator of that per-action regret increment for this
    # one observed hand, so the update is a direct accumulation.
    for action in decision["legal_actions"]:
      regrets[action] += sampled_advantages[action]


def _action_utilities(
    legal_actions,
    sample_policy,
    chosen_action,
    terminal_utility,
    prefix_sample_prob,
):
  """Return the sampled MCCFR regret increment for each legal action.

  This function intentionally no longer uses handcrafted poker features. In
  CFR/MCCFR, the learning signal comes from the sampled terminal utility u_i(z),
  not from manually designed action scores.

  Lanctot et al. (2009), Eq. (10), give the outcome-sampling regret estimator:
  - chosen action a*:   +w_I * (1 - sigma(a*|I))
  - other actions a:    -w_I * sigma(a|I)

  Here `sigma(.|I)` is the sampling policy at the visited abstract state. Since
  the environment itself samples opponent/chance actions by actually playing the
  hand, and this code samples our own action from `sample_policy`, the remaining
  importance term is the inverse probability of our own sampled prefix:

      w_I = terminal_utility / prefix_sample_prob

  where `prefix_sample_prob` is the product of our sampled action probabilities
  from the start of the hand through the chosen action at this state.
  """
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
