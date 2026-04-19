"""Compact information-state abstraction for CFR and search.

Signals kept on purpose:
1. strength: strongest signal for action quality.
2. street_index: the same hand means different things by phase.
3. history: a compact public betting-shape bucket.
4. pot_odds: immediate price to continue.

State layout:
- street_index: 4 buckets
- strength: 10 buckets
- history: 8 buckets
- pot_odds: 6 buckets

Total possible abstract states:
- 4 * 10 * 8 * 6 = 1,920

The history abstraction follows standard poker-abstraction practice: preserve
the public action shape that matters strategically, but avoid raw action-string
explosion that produces sparse CFR/search states.
"""

from pypokerengine.utils.card_utils import estimate_hole_card_win_rate, gen_cards

STREETS = ("preflop", "flop", "turn", "river")
STREET_INDEX = {street: i for i, street in enumerate(STREETS)}
RANK_VALUE = {rank: value for value, rank in enumerate("..23456789TJQKA")}
STRENGTH_BUCKETS = 10
POT_ODDS_BUCKETS = 6
HISTORY_BUCKETS = 8
ABSTRACTION_SHAPE = {
    "street_index": len(STREETS),
    "strength": STRENGTH_BUCKETS,
    "history": HISTORY_BUCKETS,
    "pot_odds": POT_ODDS_BUCKETS,
}
TOTAL_ABSTRACT_STATES = (
    ABSTRACTION_SHAPE["street_index"]
    * ABSTRACTION_SHAPE["strength"]
    * ABSTRACTION_SHAPE["history"]
    * ABSTRACTION_SHAPE["pot_odds"]
)


def build_abstraction(hole_card, round_state):
  street = _normalize_street(round_state.get("street"))
  to_call = _amount_to_call(round_state)
  pot_size = _pot_size(round_state)
  pot_odds = 0.0 if to_call <= 0 else float(to_call) / max(pot_size + to_call, 1)
  strength = _hand_strength(
      hole_card=hole_card,
      community_card=round_state.get("community_card", []),
      street=street,
      active_players=_active_player_count(round_state),
  )
  history = history_bucket(round_state.get("action_histories", {}), street)
  state = (
      STREET_INDEX[street],
      _bucket(strength, STRENGTH_BUCKETS),
      history,
      _bucket(min(pot_odds, 0.999999), POT_ODDS_BUCKETS),
  )
  features = {
      "street": street,
      "street_index": STREET_INDEX[street],
      "strength": strength,
      "history": history,
      "pot_odds": pot_odds,
      "to_call": to_call,
      "pot_size": pot_size,
      "abstraction_shape": ABSTRACTION_SHAPE,
      "total_abstract_states": TOTAL_ABSTRACT_STATES,
  }
  return state, features


def history_bucket(action_histories, street):
  """Public betting-pattern bucket in `0..7`.

  Buckets:
  - 0: no strategic action yet on this street
  - 1: passive-only on this street
  - 2: one raise and otherwise aggressive line
  - 3: passive -> raise
  - 4: raise -> passive
  - 5: multi-raise / contested
  - 6: earlier-street aggression, current street still quiet/passive
  - 7: earlier-street aggression and current street aggressive too
  """
  prior_aggression = any(_raise_count(action_histories, name) > 0 for name in STREETS[:STREET_INDEX[street]])
  encoded = [_encode_action(action.get("action")) for action in action_histories.get(street, [])]
  encoded = [move for move in encoded if move in {"c", "r"}]
  raise_count = encoded.count("r")

  if prior_aggression:
    return 7 if raise_count > 0 else 6
  if not encoded:
    return 0
  if raise_count >= 2:
    return 5
  if raise_count == 0:
    return 1
  if encoded[0] == "r":
    return 2 if encoded.count("c") == 0 else 4
  return 3


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


def _encode_action(action):
  action = (action or "").lower()
  if action == "raise":
    return "r"
  if action in {"call", "check"}:
    return "c"
  return ""


def _raise_count(action_histories, street):
  return sum(
      1
      for action in action_histories.get(street, [])
      if _encode_action(action.get("action")) == "r"
  )


def _normalize_street(street):
  street = (street or "preflop").lower()
  return street if street in STREET_INDEX else "preflop"


def _bucket(value, bucket_count):
  value = max(0.0, min(float(value), 0.999999))
  return min(int(value * bucket_count), bucket_count - 1)


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
