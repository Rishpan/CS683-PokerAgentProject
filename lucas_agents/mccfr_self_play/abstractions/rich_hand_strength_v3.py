"""Legacy rich-hand-strength abstraction kept for old policy compatibility."""

from collections import Counter

from pypokerengine.engine.hand_evaluator import HandEvaluator
from pypokerengine.utils.card_utils import estimate_hole_card_win_rate, gen_cards


ABSTRACTION_NAME = "rich_hand_strength"
ABSTRACTION_VERSION = "rich_hand_strength_v3"
STREET_INDEX = {"preflop": 0, "flop": 1, "turn": 2, "river": 3}
STREET_COUNT = 4
STRENGTH_BUCKETS = 8
POT_ODDS_BUCKETS = 3
PRESSURE_BUCKETS = 3
AGGRESSION_BUCKETS = 2
HISTORY_BUCKETS = 9
MADE_HAND_SCORE = {
    HandEvaluator.HIGHCARD: 0.05,
    HandEvaluator.ONEPAIR: 0.22,
    HandEvaluator.TWOPAIR: 0.42,
    HandEvaluator.THREECARD: 0.56,
    HandEvaluator.STRAIGHT: 0.72,
    HandEvaluator.FLASH: 0.80,
    HandEvaluator.FULLHOUSE: 0.90,
    HandEvaluator.FOURCARD: 0.96,
    HandEvaluator.STRAIGHTFLASH: 1.0,
}
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


def build_info_key(
    hole_card,
    round_state,
    player_uuid,
    opponent_action_stats,
    postflop_simulations,
):
  street = round_state["street"]
  history = compress_action_history(round_state["action_histories"], street)
  position = 1 if has_position(round_state, player_uuid) else 0
  to_call = amount_to_call(round_state, player_uuid)
  pot_size = pot_size_from_round_state(round_state)
  stack = my_stack(round_state, player_uuid)
  pot_odds = 0.0 if to_call <= 0 else float(to_call) / max(pot_size + to_call, 1)
  pressure = 0.0 if stack <= 0 else min(0.999, float(to_call) / max(stack, 1))
  strength = hand_strength(hole_card, round_state["community_card"], postflop_simulations)
  aggression = opponent_aggression_bucket(opponent_action_stats)

  key = (
      STREET_INDEX[street],
      bucket_strength(strength),
      position,
      bucket_value(pot_odds, POT_ODDS_BUCKETS),
      bucket_value(pressure, PRESSURE_BUCKETS),
      aggression,
      history,
  )
  return "|".join(str(part) for part in key), {
      "street": street,
      "strength": strength,
      "position": position,
      "pot_odds": pot_odds,
      "pressure": pressure,
      "aggression_bucket": aggression,
      "history": history,
  }


def hand_strength(hole_card, community_card, simulations):
  if not community_card:
    return preflop_score(hole_card)
  hole_cards = gen_cards(hole_card)
  community_cards = gen_cards(community_card)
  equity = estimate_hole_card_win_rate(
      nb_simulation=simulations,
      nb_player=2,
      hole_card=hole_cards,
      community_card=community_cards,
  )
  made_hand = made_hand_score(hole_cards, community_cards)
  draw_strength = draw_score(hole_card, community_card)
  strength = 0.70 * equity + 0.20 * made_hand + 0.10 * draw_strength
  return max(0.0, min(strength, 0.999999))


def preflop_score(hole_card):
  ranks = sorted((RANK_VALUE[card[1]] for card in hole_card), reverse=True)
  high, low = ranks
  suited = hole_card[0][0] == hole_card[1][0]
  gap = high - low

  score = 0.30
  if high == low:
    score += 0.34 + min(high, 13) * 0.026
  else:
    score += max(high - 8, 0) * 0.050
    score += max(low - 8, 0) * 0.032

  if suited:
    score += 0.06
  if gap == 1:
    score += 0.05
  elif gap == 2:
    score += 0.025
  elif gap == 3:
    score += 0.005
  elif gap >= 4:
    score -= 0.05
  if high >= 12 and low >= 10:
    score += 0.06
  if high == 14 and low >= 10:
    score += 0.05
  if high == 14 and low <= 5:
    score += 0.02
  if high >= 11 and low >= 9 and gap <= 2:
    score += 0.03
  if high < 10 and low < 8 and not suited:
    score -= 0.07
  return max(0.0, min(score, 0.95))


def bucket_strength(strength):
  return bucket_value(strength, STRENGTH_BUCKETS)


def bucket_value(value, bucket_count):
  clipped = max(0.0, min(float(value), 0.999999))
  return min(int(clipped * bucket_count), bucket_count - 1)


def compress_action_history(action_histories, current_street):
  return summarize_street_history(action_histories.get(current_street, []))


def summarize_street_history(street_actions):
  raises = 0
  has_call = False
  has_fold = False

  for action in street_actions:
    move = action["action"]
    if move in ("SMALLBLIND", "BIGBLIND", "ANTE"):
      continue
    if move == "RAISE":
      raises += 1
    elif move == "CALL":
      has_call = True
    elif move == "FOLD":
      has_fold = True

  raise_bucket = min(raises, 2)
  if has_fold:
    ending = "f"
  elif has_call:
    ending = "c"
  else:
    ending = "n"
  return f"{raise_bucket}{ending}"


def made_hand_score(hole_cards, community_cards):
  hand_rank = HandEvaluator.eval_hand(hole_cards, community_cards)
  hand_class = _hand_class(hand_rank)
  return MADE_HAND_SCORE[hand_class]


def draw_score(hole_card, community_card):
  if len(community_card) < 3:
    return 0.0

  cards = hole_card + community_card
  suit_counts = Counter(card[0] for card in cards)
  flush_draw = max(suit_counts.values()) >= 4 and len(community_card) < 5

  ranks = sorted({RANK_VALUE[card[1]] for card in cards})
  if 14 in ranks:
    ranks = [1] + ranks
  longest, has_gutshot = _straight_draw_profile(ranks)

  if longest >= 4 and flush_draw:
    return 0.95
  if longest >= 4:
    return 0.72
  if has_gutshot and flush_draw:
    return 0.62
  if flush_draw:
    return 0.50
  if has_gutshot:
    return 0.32
  return 0.0


def _straight_draw_profile(ranks):
  longest = 1
  has_gutshot = False
  for start_index in range(len(ranks)):
    window = [ranks[start_index]]
    gaps = 0
    for next_rank in ranks[start_index + 1:]:
      diff = next_rank - window[-1]
      if diff == 1:
        window.append(next_rank)
      elif diff == 2 and gaps == 0:
        window.append(next_rank)
        gaps = 1
      elif diff > 2:
        break
      longest = max(longest, len(window))
      if len(window) >= 4 and gaps == 1:
        has_gutshot = True
  return longest, has_gutshot


def _hand_class(hand_rank):
  for hand_class in (
      HandEvaluator.STRAIGHTFLASH,
      HandEvaluator.FOURCARD,
      HandEvaluator.FULLHOUSE,
      HandEvaluator.FLASH,
      HandEvaluator.STRAIGHT,
      HandEvaluator.THREECARD,
      HandEvaluator.TWOPAIR,
      HandEvaluator.ONEPAIR,
  ):
    if hand_rank & hand_class:
      return hand_class
  return HandEvaluator.HIGHCARD


def opponent_aggression_bucket(opponent_action_stats):
  raises = opponent_action_stats.get("raise", 0)
  calls = opponent_action_stats.get("call", 0)
  folds = opponent_action_stats.get("fold", 0)
  total = raises + calls + folds
  if total <= 0:
    return 0
  aggression = float(raises) / total
  return 1 if aggression >= 0.35 else 0


def observe_opponent_actions(action_histories, player_uuid):
  stats = {"raise": 0, "call": 0, "fold": 0}
  for street_histories in action_histories.values():
    for action in street_histories:
      if action["uuid"] == player_uuid:
        continue
      move = action["action"]
      if move == "RAISE":
        stats["raise"] += 1
      elif move == "CALL":
        stats["call"] += 1
      elif move == "FOLD":
        stats["fold"] += 1
  return stats


def has_position(round_state, player_uuid):
  seats = round_state["seats"]
  player_count = len(seats)
  my_index = next((idx for idx, seat in enumerate(seats) if seat["uuid"] == player_uuid), None)
  if my_index is None:
    return False
  dealer_btn = round_state["dealer_btn"]
  if player_count == 2:
    return my_index == dealer_btn and round_state["street"] != "preflop"
  return my_index == (dealer_btn - 1) % player_count


def amount_to_call(round_state, player_uuid):
  street = round_state["street"]
  histories = round_state["action_histories"].get(street, [])
  highest_amount = 0
  my_amount = 0
  for action in histories:
    amount = action.get("amount", 0)
    highest_amount = max(highest_amount, amount)
    if action.get("uuid") == player_uuid:
      my_amount = amount
  return max(0, highest_amount - my_amount)


def pot_size_from_round_state(round_state):
  pot = round_state["pot"]
  return pot["main"]["amount"] + sum(side["amount"] for side in pot["side"])


def my_stack(round_state, player_uuid):
  for seat in round_state["seats"]:
    if seat["uuid"] == player_uuid:
      return seat["stack"]
  return 0


def abstraction_state_upper_bound():
  return (
      STREET_COUNT
      * STRENGTH_BUCKETS
      * 2
      * POT_ODDS_BUCKETS
      * PRESSURE_BUCKETS
      * AGGRESSION_BUCKETS
      * HISTORY_BUCKETS
  )
