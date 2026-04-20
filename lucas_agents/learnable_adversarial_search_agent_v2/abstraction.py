from pypokerengine.utils.card_utils import estimate_hole_card_win_rate, gen_cards

STREETS = ("preflop", "flop", "turn", "river")
STREET_INDEX = {street: i for i, street in enumerate(STREETS)}
RANK_VALUE = {rank: value for value, rank in enumerate("..23456789TJQKA")}
HAND_BUCKETS = 6
BOARD_BUCKETS = 8
HISTORY_BUCKETS = 15
POSITION_BUCKETS = 2
POT_BUCKETS = 2
ABSTRACTION_SHAPE = {
    "street": len(STREETS),
    "hand_bucket": HAND_BUCKETS,
    "board_bucket": BOARD_BUCKETS,
    "history_bucket": HISTORY_BUCKETS,
    "position": POSITION_BUCKETS,
    "pot_bucket": POT_BUCKETS,
}
TOTAL_ABSTRACT_STATES = 4 * 6 * 8 * 15 * 2 * 2


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
  pot_bucket = _pot_bucket(round_state)
  state = (
      STREET_INDEX[street],
      _hand_bucket(equity),
      board,
      history,
      position,
      pot_bucket,
  )
  features = {
      "street": street,
      "street_index": STREET_INDEX[street],
      "equity": equity,
      "hand_bucket": state[1],
      "board_bucket": board,
      "history_bucket": history,
      "position": position,
      "pot_bucket": pot_bucket,
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
  if equity < 0.20:
    return 0
  if equity < 0.40:
    return 1
  if equity < 0.55:
    return 2
  if equity < 0.70:
    return 3
  if equity < 0.85:
    return 4
  return 5


def _board_bucket(community_card):
  if not community_card:
    return 0
  suits = [card[0] for card in community_card]
  ranks = sorted(RANK_VALUE[card[1]] for card in community_card)
  unique_ranks = sorted(set(ranks))
  suit_counts = {suit: suits.count(suit) for suit in set(suits)}
  max_suit = max(suit_counts.values()) if suit_counts else 0
  paired = len(unique_ranks) < len(ranks)
  high_board = max(ranks) >= 13
  low_board = max(ranks) <= 9
  connected_span = max(unique_ranks) - min(unique_ranks) if len(unique_ranks) >= 2 else 0
  connected = connected_span <= max(len(unique_ranks) + 1, 3)

  if max_suit >= 3:
    return 4
  if connected and len(unique_ranks) >= 3 and connected_span <= 4:
    return 5
  if high_board:
    return 6
  if low_board:
    return 7
  if max_suit == 2 and connected:
    return 3
  if max_suit == 2:
    return 2
  if paired:
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
  prior_raises = sum(1 for action in prior_actions if _encode_action(action.get("action")) == "r")
  total_raises = prior_raises + current_raises
  pot_size = _pot_size(round_state)
  to_call = _amount_to_call(round_state)
  stack = _my_stack_from_next_player(round_state)
  pressure = 0.0 if stack <= 0 else float(to_call) / max(stack, 1)

  if pressure >= 0.45 or to_call >= max(150, pot_size // 2):
    return 14
  if total_raises >= 3:
    return 13
  if street == "river" and current_raises > 0 and prior_raises >= 2:
    return 8
  if street == "turn" and current_raises > 0 and prior_raises >= 1:
    return 7
  if current_raises >= 2:
    return 2
  if current_raises == 1 and current_calls >= 1:
    return 3
  if current_raises == 1 and current_moves[:1] == ["k"]:
    return 5
  if len(current_moves) >= 2 and current_moves[0] == "k" and current_moves[1] == "r":
    return 6
  if current_raises == 1 and current_calls == 0:
    return 11
  if current_calls >= 2 and current_raises == 0:
    return 10
  if prior_raises > 0 and current_raises == 0 and current_calls == 0:
    return 9
  if prior_raises > 0 and current_raises > 0:
    return 12
  if current_raises == 1:
    return 1
  if current_calls > 0:
    return 10
  return 0


def _position_bucket(round_state):
  seats = round_state.get("seats", [])
  next_player = round_state.get("next_player", 0)
  dealer_btn = round_state.get("dealer_btn", 0)
  if len(seats) != 2:
    return 0
  return 1 if next_player == dealer_btn else 0


def _pot_bucket(round_state):
  pot_size = _pot_size(round_state)
  to_call = _amount_to_call(round_state)
  return 1 if pot_size >= 120 or to_call >= 40 else 0


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
