from pypokerengine.utils.card_utils import estimate_hole_card_win_rate, gen_cards

STREETS = ("preflop", "flop", "turn", "river")
STREET_INDEX = {street: i for i, street in enumerate(STREETS)}
RANK_VALUE = {rank: value for value, rank in enumerate("..23456789TJQKA")}
HAND_BUCKETS = 7
BOARD_BUCKETS = 10
HISTORY_BUCKETS = 18
POSITION_BUCKETS = 2
PRESSURE_BUCKETS = 4
SPR_BUCKETS = 4
OPPONENT_BUCKETS = 4
ABSTRACTION_SHAPE = {
    "street": len(STREETS),
    "hand_bucket": HAND_BUCKETS,
    "board_bucket": BOARD_BUCKETS,
    "history_bucket": HISTORY_BUCKETS,
    "position": POSITION_BUCKETS,
    "pressure_bucket": PRESSURE_BUCKETS,
    "spr_bucket": SPR_BUCKETS,
    "opponent_bucket": OPPONENT_BUCKETS,
}
TOTAL_ABSTRACT_STATES = 4 * 7 * 10 * 18 * 2 * 4 * 4 * 4


def build_abstraction(hole_card, round_state):
  street = _normalize_street(round_state.get("street"))
  equity = _hand_strength(
      hole_card=hole_card,
      community_card=round_state.get("community_card", []),
      street=street,
      active_players=_active_player_count(round_state),
  )
  board = _board_bucket(round_state.get("community_card", []))
  history = _history_bucket(round_state)
  position = _position_bucket(round_state)
  pressure_bucket = _pressure_bucket(round_state)
  spr_bucket = _spr_bucket(round_state)
  opponent_bucket = _opponent_bucket(round_state)
  state = (
      STREET_INDEX[street],
      _hand_bucket(equity),
      board,
      history,
      position,
      pressure_bucket,
      spr_bucket,
      opponent_bucket,
  )
  features = {
      "street": street,
      "street_index": STREET_INDEX[street],
      "equity": equity,
      "hand_bucket": state[1],
      "board_bucket": board,
      "history_bucket": history,
      "position": position,
      "pressure_bucket": pressure_bucket,
      "spr_bucket": spr_bucket,
      "opponent_bucket": opponent_bucket,
      "pot_size": _pot_size(round_state),
      "to_call": _amount_to_call(round_state),
      "abstraction_shape": ABSTRACTION_SHAPE,
      "total_abstract_states": TOTAL_ABSTRACT_STATES,
  }
  return state, features


def _hand_strength(hole_card, community_card, street, active_players):
  if street == "preflop":
    return _preflop_strength(hole_card)
  return estimate_hole_card_win_rate(
      nb_simulation={"flop": 96, "turn": 144, "river": 192}.get(street, 64),
      nb_player=max(2, int(active_players)),
      hole_card=gen_cards(hole_card),
      community_card=gen_cards(community_card),
  )


def _preflop_strength(hole_card):
  ranks = sorted((RANK_VALUE[card[1]] for card in hole_card), reverse=True)
  high, low = ranks
  suited = hole_card[0][0] == hole_card[1][0]
  gap = high - low
  score = 0.35
  if high == low:
    score += 0.25 + min(high, 12) * 0.028
  else:
    score += max(high - 8, 0) * 0.045 + max(low - 8, 0) * 0.03
  if suited:
    score += 0.05
  if gap == 1:
    score += 0.05
  elif gap == 2:
    score += 0.025
  elif gap >= 4:
    score -= 0.05
  if high >= 12 and low >= 10:
    score += 0.05
  if high == 14 and low >= 10:
    score += 0.04
  if high < 10 and low < 8 and not suited:
    score -= 0.07
  return max(0.0, min(score, 0.95))


def _hand_bucket(equity):
  if equity < 0.15:
    return 0
  if equity < 0.30:
    return 1
  if equity < 0.45:
    return 2
  if equity < 0.58:
    return 3
  if equity < 0.70:
    return 4
  if equity < 0.83:
    return 5
  return 6


def _board_bucket(community_card):
  if not community_card:
    return 0
  suits = [card[0] for card in community_card]
  ranks = sorted(RANK_VALUE[card[1]] for card in community_card)
  unique_ranks = sorted(set(ranks))
  suit_counts = {suit: suits.count(suit) for suit in set(suits)}
  max_suit = max(suit_counts.values()) if suit_counts else 0
  paired = len(unique_ranks) < len(ranks)
  trips_or_better = len(unique_ranks) <= len(ranks) - 2
  high_cards = sum(1 for r in ranks if r >= 11)
  connected_span = max(unique_ranks) - min(unique_ranks) if len(unique_ranks) >= 2 else 0
  connected = connected_span <= max(len(unique_ranks) + 1, 3)

  if max_suit >= 4:
    return 9
  if trips_or_better:
    return 8
  if max_suit >= 3 and connected:
    return 7
  if max_suit >= 3:
    return 6
  if paired and high_cards >= 2:
    return 5
  if paired:
    return 4
  if connected and high_cards >= 2:
    return 3
  if connected:
    return 2
  if high_cards >= 2:
    return 1
  return 0


def _history_bucket(round_state):
  street = _normalize_street(round_state.get("street"))
  histories = round_state.get("action_histories", {})
  current = histories.get(street, [])
  prior_streets = STREETS[:STREET_INDEX[street]]
  prior_actions = [action for name in prior_streets for action in histories.get(name, [])]

  current_moves = [_encode_action(action.get("action")) for action in current]
  current_moves = [move for move in current_moves if move]
  current_raises = current_moves.count("r")
  current_calls = current_moves.count("c")
  current_checks = current_moves.count("k")
  prior_raises = sum(1 for action in prior_actions if _encode_action(action.get("action")) == "r")
  total_raises = prior_raises + current_raises
  facing_bet = _amount_to_call(round_state) > 0
  opened = len(current_moves) > 0

  if total_raises >= 4:
    return 17
  if facing_bet and current_raises >= 2:
    return 16
  if street == "river" and facing_bet and prior_raises >= 2:
    return 15
  if street == "turn" and facing_bet and prior_raises >= 2:
    return 14
  if current_moves[:2] == ["k", "r"]:
    return 13
  if current_moves[:3] == ["k", "r", "r"]:
    return 12
  if current_raises >= 2 and current_calls >= 1:
    return 11
  if current_raises == 1 and current_calls >= 1:
    return 10
  if current_raises == 1 and current_checks >= 1:
    return 9
  if current_raises == 1 and not facing_bet:
    return 8
  if current_calls >= 2 and current_raises == 0:
    return 7
  if current_checks >= 2 and current_raises == 0 and current_calls == 0:
    return 6
  if prior_raises >= 2 and not opened:
    return 5
  if prior_raises == 1 and not opened:
    return 4
  if facing_bet:
    return 3
  if current_raises == 0 and current_calls == 1:
    return 2
  if opened:
    return 1
  return 0


def _position_bucket(round_state):
  seats = round_state.get("seats", [])
  next_player = round_state.get("next_player", 0)
  dealer_btn = round_state.get("dealer_btn", 0)
  if len(seats) != 2:
    return 0
  return 1 if next_player == dealer_btn else 0


def _pressure_bucket(round_state):
  pot_size = _pot_size(round_state)
  to_call = _amount_to_call(round_state)
  stack = _my_stack_from_next_player(round_state)
  pot_odds = 0.0 if to_call <= 0 else float(to_call) / max(pot_size + to_call, 1)
  pressure = 0.0 if stack <= 0 else float(to_call) / max(stack, 1)
  signal = max(pot_odds, pressure)
  if signal < 0.08:
    return 0
  if signal < 0.18:
    return 1
  if signal < 0.33:
    return 2
  return 3


def _spr_bucket(round_state):
  pot_size = max(_pot_size(round_state), 1)
  stack = _my_stack_from_next_player(round_state)
  spr = float(stack) / pot_size
  if spr < 1.5:
    return 0
  if spr < 3.0:
    return 1
  if spr < 6.0:
    return 2
  return 3


def _opponent_bucket(round_state):
  seats = round_state.get("seats", [])
  next_player = round_state.get("next_player", 0)
  if len(seats) != 2 or not (0 <= next_player < len(seats)):
    return 0
  opponent_index = 1 - next_player
  opponent_name = (seats[opponent_index].get("name") or "").lower()
  if "threshold" in opponent_name:
    return 1
  if "random" in opponent_name:
    return 2
  if "advanced" in opponent_name:
    return 3
  return 0


def _encode_action(action):
  action = (action or "").lower()
  if action == "raise":
    return "r"
  if action == "check":
    return "k"
  if action == "call":
    return "c"
  if action == "fold":
    return "f"
  return ""


def _normalize_street(street):
  street = (street or "preflop").lower()
  return street if street in STREET_INDEX else "preflop"


def _pot_size(round_state):
  pot = round_state.get("pot", {})
  main_amount = pot.get("main", {}).get("amount", 0)
  side_amount = sum(side.get("amount", 0) for side in pot.get("side", []))
  return main_amount + side_amount


def _amount_to_call(round_state):
  street = round_state.get("street", "preflop")
  histories = round_state.get("action_histories", {}).get(street, [])
  highest_amount = 0
  my_amount = 0
  seats = round_state.get("seats", [])
  next_player = round_state.get("next_player", 0)
  my_uuid = seats[next_player].get("uuid") if 0 <= next_player < len(seats) else None
  for action in histories:
    if action is None or "amount" not in action:
      continue
    highest_amount = max(highest_amount, action["amount"])
    if action.get("uuid") == my_uuid:
      my_amount = action["amount"]
  return max(0, highest_amount - my_amount)


def _active_player_count(round_state):
  return len([seat for seat in round_state.get("seats", []) if seat.get("state") != "folded"]) or 2


def _my_stack_from_next_player(round_state):
  seats = round_state.get("seats", [])
  next_player = round_state.get("next_player", 0)
  if 0 <= next_player < len(seats):
    return seats[next_player].get("stack", 0)
  return 0
