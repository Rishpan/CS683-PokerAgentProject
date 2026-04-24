from pypokerengine.players import BasePokerPlayer

from lucas_agents.learnable_adversarial_search_agent.abstraction import (
    TOTAL_ABSTRACT_STATES,
    build_abstraction,
)
from lucas_agents.learnable_adversarial_search_agent.adversarial_search import AdversarialSearch
from lucas_agents.learnable_adversarial_search_agent.cfr import DEFAULT_POLICY_PATH, TabularCFR


class LearnableAdversarialSearchPlayer(BasePokerPlayer):
  TOTAL_ABSTRACT_STATES = TOTAL_ABSTRACT_STATES

  def __init__(
      self,
      policy_path=DEFAULT_POLICY_PATH,
      training_enabled=False,
      use_search=True,
      exploration=0.06,
      save_interval=50,
      random_seed=None,
  ):
    super().__init__()
    self.training_enabled = training_enabled
    self.use_search = False if training_enabled else bool(use_search)
    self.save_interval = max(1, save_interval)
    self.cfr = TabularCFR(
        policy_path=policy_path,
        exploration=exploration,
        training_enabled=training_enabled,
        random_seed=random_seed,
    )
    self.search = AdversarialSearch()
    self._declare_action_impl = self.declare_action
  def declare_action(self, valid_actions, hole_card, round_state):
    legal_actions = tuple(action["action"] for action in valid_actions)
    info_state, features = build_abstraction(hole_card, round_state)
    strategy = (
        self.cfr.strategy(info_state, legal_actions)
        if self.training_enabled
        else self.cfr.average_strategy(info_state, legal_actions)
    )

    if self.use_search:
      action = self.search.choose_action(legal_actions, features, strategy)
    else:
      action = self.cfr.sample_action(strategy)

    features["policy"] = strategy
    self.cfr.record_decision(info_state, legal_actions, action, features)
    return action

  def receive_game_start_message(self, game_info):
    pass

  def receive_round_start_message(self, round_count, hole_card, seats):
    pass

  def receive_street_start_message(self, street, round_state):
    pass

  def receive_game_update_message(self, action, round_state):
    pass

  def receive_round_result_message(self, winners, hand_info, round_state):
    pass

  def reset_match_state(self):
    self.declare_action = self._declare_action_impl
    if hasattr(self, "cfr"):
      self.cfr.reset_round_state()


def setup_ai():
  return LearnableAdversarialSearchPlayer()
