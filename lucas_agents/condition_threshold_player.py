from pypokerengine.players import BasePokerPlayer
from pypokerengine.utils.card_utils import estimate_hole_card_win_rate, gen_cards


class ConditionThresholdPlayer(BasePokerPlayer):
  """
  Simple but competitive rule-based opponent.

  Strategy outline:
  - Preflop: use a hand-strength heuristic with pair / high-card / suited / connector bonuses.
  - Postflop: estimate equity with a small Monte Carlo rollout.
  - Compare equity against pot odds and street-based thresholds.
  - Adapt slightly to opponent aggression: call lighter versus aggressive players,
    value-raise more often versus passive players.
  """

  STREET_ORDER = {
      "preflop": 0,
      "flop": 1,
      "turn": 2,
      "river": 3,
  }

  def __init__(self):
    self.opponent_actions = {}
    self.total_rounds = 0

  def declare_action(self, valid_actions, hole_card, round_state):
    street = round_state["street"]
    can_raise = any(action["action"] == "raise" for action in valid_actions)
    to_call = self._amount_to_call(round_state)
    pot_size = self._pot_size(round_state)
    stack = self._my_stack(round_state)

    equity = self._estimate_equity(hole_card, round_state)
    adjusted_equity = equity + self._position_bonus(round_state) + self._board_pressure_adjustment(
        street, to_call, stack
    )

    raise_threshold, call_threshold = self._street_thresholds(street)
    raise_threshold, call_threshold = self._adjust_for_opponent(raise_threshold, call_threshold)
    raise_threshold, call_threshold = self._adjust_for_price(
        raise_threshold, call_threshold, to_call, pot_size, stack
    )

    if to_call == 0:
      if can_raise and adjusted_equity >= raise_threshold - 0.06:
        return "raise"
      return "call"

    if can_raise and adjusted_equity >= raise_threshold:
      return "raise"
    if adjusted_equity >= call_threshold:
      return "call"
    return "fold"

  def receive_game_start_message(self, game_info):
    pass

  def receive_round_start_message(self, round_count, hole_card, seats):
    self.total_rounds = round_count

  def receive_street_start_message(self, street, round_state):
    pass

  def receive_game_update_message(self, action, round_state):
    player_uuid = action["player_uuid"]
    if player_uuid == getattr(self, "uuid", None):
      return

    stats = self.opponent_actions.setdefault(player_uuid, {"raise": 0, "call": 0, "fold": 0})
    act = action["action"]
    if act in stats:
      stats[act] += 1

  def receive_round_result_message(self, winners, hand_info, round_state):
    pass

  def _estimate_equity(self, hole_card, round_state):
    if round_state["street"] == "preflop":
      return self._preflop_strength(hole_card, round_state)

    active_players = self._active_player_count(round_state)
    community = gen_cards(round_state["community_card"])
    simulations = self._simulation_count(round_state["street"])
    return estimate_hole_card_win_rate(
        nb_simulation=simulations,
        nb_player=active_players,
        hole_card=gen_cards(hole_card),
        community_card=community,
    )

  def _preflop_strength(self, hole_card, round_state):
    ranks = sorted([self._rank_value(card[1]) for card in hole_card], reverse=True)
    high, low = ranks
    suits = [card[0] for card in hole_card]
    suited = suits[0] == suits[1]
    gap = high - low

    score = 0.35

    if high == low:
      score += 0.25 + min(high, 12) * 0.028
    else:
      score += max(high - 8, 0) * 0.045
      score += max(low - 8, 0) * 0.03

    if suited:
      score += 0.05
    if gap == 1:
      score += 0.05
    elif gap == 2:
      score += 0.025
    elif gap >= 4:
      score -= 0.05

    if high >= 12 and low >= 10:
      score += 0.06
    if high == 14 and low >= 10:
      score += 0.04
    if high < 10 and low < 8 and not suited:
      score -= 0.07

    if self._has_position(round_state):
      score += 0.02

    return max(0.0, min(score, 0.95))

  def _street_thresholds(self, street):
    thresholds = {
        "preflop": (0.74, 0.51),
        "flop": (0.70, 0.46),
        "turn": (0.73, 0.50),
        "river": (0.79, 0.57),
    }
    return thresholds.get(street, (0.75, 0.52))

  def _adjust_for_opponent(self, raise_threshold, call_threshold):
    aggression = self._opponent_aggression()
    if aggression >= 0.35:
      return raise_threshold + 0.03, call_threshold - 0.03
    if aggression <= 0.15:
      return raise_threshold - 0.02, call_threshold + 0.01
    return raise_threshold, call_threshold

  def _adjust_for_price(self, raise_threshold, call_threshold, to_call, pot_size, stack):
    if to_call <= 0:
      return raise_threshold, call_threshold

    pot_odds = float(to_call) / max(pot_size + to_call, 1)
    stack_ratio = float(to_call) / max(stack, 1)

    call_threshold = max(call_threshold, pot_odds + 0.06)
    raise_threshold = max(raise_threshold, pot_odds + 0.18)

    if stack_ratio >= 0.35:
      call_threshold += 0.07
      raise_threshold += 0.05
    elif stack_ratio <= 0.08:
      call_threshold -= 0.02

    return raise_threshold, call_threshold

  def _board_pressure_adjustment(self, street, to_call, stack):
    adjustment = 0.0
    if street == "river":
      adjustment -= 0.01
    if stack > 0 and float(to_call) / stack >= 0.3:
      adjustment -= 0.04
    return adjustment

  def _position_bonus(self, round_state):
    return 0.015 if self._has_position(round_state) else 0.0

  def _has_position(self, round_state):
    seats = round_state["seats"]
    my_index = self._my_seat_index(seats)
    if my_index is None:
      return False

    player_count = len(seats)
    dealer_btn = round_state["dealer_btn"]
    if player_count == 2:
      return my_index == dealer_btn and round_state["street"] != "preflop"
    return my_index == (dealer_btn - 1) % player_count

  def _my_stack(self, round_state):
    for seat in round_state["seats"]:
      if seat["uuid"] == getattr(self, "uuid", None):
        return seat["stack"]
    return 0

  def _my_seat_index(self, seats):
    for index, seat in enumerate(seats):
      if seat["uuid"] == getattr(self, "uuid", None):
        return index
    return None

  def _pot_size(self, round_state):
    pot = round_state["pot"]
    main_amount = pot["main"]["amount"]
    side_amount = sum(side["amount"] for side in pot["side"])
    return main_amount + side_amount

  def _amount_to_call(self, round_state):
    histories = round_state["action_histories"].get(round_state["street"], [])
    highest_amount = 0
    my_amount = 0

    for action in histories:
      if action is None or "amount" not in action:
        continue
      amount = action["amount"]
      highest_amount = max(highest_amount, amount)
      if action.get("uuid") == getattr(self, "uuid", None):
        my_amount = amount

    return max(0, highest_amount - my_amount)

  def _active_player_count(self, round_state):
    return len([seat for seat in round_state["seats"] if seat["state"] != "folded"])

  def _opponent_aggression(self):
    total_raises = 0
    total_actions = 0
    for stats in self.opponent_actions.values():
      total_raises += stats["raise"]
      total_actions += stats["raise"] + stats["call"] + stats["fold"]

    if total_actions == 0:
      return 0.25
    return float(total_raises) / total_actions

  def _simulation_count(self, street):
    return {
        "flop": 80,
        "turn": 120,
        "river": 160,
    }.get(street, 64)

  def _rank_value(self, rank_char):
    rank_map = {
        "2": 2,
        "3": 3,
        "4": 4,
        "5": 5,
        "6": 6,
        "7": 7,
        "8": 8,
        "9": 9,
        "T": 10,
        "J": 11,
        "Q": 12,
        "K": 13,
        "A": 14,
    }
    return rank_map[rank_char]


def setup_ai():
  return ConditionThresholdPlayer()
