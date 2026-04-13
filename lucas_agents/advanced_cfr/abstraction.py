from collections import Counter

from pypokerengine.utils.card_utils import estimate_hole_card_win_rate, gen_cards


STREET_INDEX = {"preflop": 0, "flop": 1, "turn": 2, "river": 3}
RANK_VALUE = {
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


def hand_strength(hole_card, community_card, simulations):
  if not community_card:
    return _preflop_score(hole_card)
  return estimate_hole_card_win_rate(
      nb_simulation=simulations,
      nb_player=2,
      hole_card=gen_cards(hole_card),
      community_card=gen_cards(community_card),
  )


def build_info_key(
    hole_card,
    community_card,
    street,
    action_histories,
    position,
    pot_odds,
    pressure,
    spr,
    simulations,
):
  strength = hand_strength(hole_card, community_card, simulations)
  features = {
      "street": street,
      "street_index": STREET_INDEX[street],
      "strength": strength,
      "made_hand": _made_hand_bucket(strength, street),
      "draws": _draw_bucket(hole_card, community_card),
      "texture": _board_texture_bucket(community_card),
      "pot_odds": pot_odds,
      "pressure": pressure,
      "spr": spr,
      "position": position,
      "history": _compress_history(action_histories, street),
  }
  key = (
      features["street_index"],
      _bucket(strength, 12),
      features["made_hand"],
      features["draws"],
      features["texture"],
      position,
      _bucket(pot_odds, 6),
      _bucket(pressure, 6),
      _bucket(min(spr, 4.0) / 4.0, 6),
      features["history"],
  )
  return key, features


def _preflop_score(hole_card):
  ranks = sorted((RANK_VALUE[c[1]] for c in hole_card), reverse=True)
  high, low = ranks
  suited = hole_card[0][0] == hole_card[1][0]
  gap = high - low

  score = 0.35
  if high == low:
    score += 0.25 + min(high, 12) * 0.028
  else:
    score += max(high - 8, 0) * 0.045
    score += max(low - 8, 0) * 0.03
  if high == low:
    score += 0.0
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


def _draw_bucket(hole_card, community_card):
  if len(community_card) < 3:
    return 0

  cards = hole_card + community_card
  suit_counts = Counter(card[0] for card in cards)
  max_suit = max(suit_counts.values())
  flush_draw = 1 if max_suit >= 4 and len(community_card) < 5 else 0

  ranks = sorted({RANK_VALUE[c[1]] for c in cards})
  if 14 in ranks:
    ranks = [1] + ranks
  longest = 1
  current = 1
  gaps = 0
  for idx in range(1, len(ranks)):
    diff = ranks[idx] - ranks[idx - 1]
    if diff == 1:
      current += 1
    elif diff == 2:
      current += 1
      gaps += 1
    else:
      longest = max(longest, current)
      current = 1
      gaps = 0
  longest = max(longest, current)
  straight_draw = 2 if longest >= 4 and gaps == 0 else 1 if longest >= 4 else 0

  return min(flush_draw * 2 + straight_draw, 4)


def _board_texture_bucket(community_card):
  if not community_card:
    return 0

  ranks = [RANK_VALUE[c[1]] for c in community_card]
  suits = [c[0] for c in community_card]
  paired = 1 if len(set(ranks)) < len(ranks) else 0
  two_tone = 1 if max(Counter(suits).values()) >= 2 else 0
  broadway = 1 if sum(rank >= 10 for rank in ranks) >= 2 else 0
  connected = 1 if max(ranks) - min(ranks) <= 4 else 0
  return paired + 2 * two_tone + 4 * broadway + 8 * connected


def _made_hand_bucket(strength, street):
  if street == "preflop":
    return 0
  if strength >= 0.88:
    return 4
  if strength >= 0.72:
    return 3
  if strength >= 0.56:
    return 2
  if strength >= 0.42:
    return 1
  return 0


def _compress_history(action_histories, street):
  parts = []
  for name in ("preflop", "flop", "turn", "river"):
    street_actions = action_histories.get(name, [])
    encoded = []
    for action in street_actions:
      move = action.get("action")
      if move == "raise":
        encoded.append("r")
      elif move in ("call", "check"):
        encoded.append("c")
      elif move == "fold":
        encoded.append("f")
    parts.append("".join(encoded)[-4:])
    if name == street:
      break
  return "/".join(parts)


def _bucket(value, bucket_count):
  clipped = max(0.0, min(value, 0.999999))
  return min(int(clipped * bucket_count), bucket_count - 1)
