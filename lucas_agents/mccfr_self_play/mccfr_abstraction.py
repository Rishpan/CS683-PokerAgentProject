"""Tabular abstraction for the Lucas MCCFR poker agent.

Version 4 is explicitly single-hand oriented. It does not try to model
long-match behavior, and it does not encode fold endings because the hand is
already over once a fold happens.

Key layout:
  street | strength | position | spr_commitment | opponent_tendency | history

The history feature is intentionally compact:

- one bit for whether any earlier street in the current hand contained a raise
- one 4-state summary for the current street:
  - 0: unopened / checked-to spot
  - 1: passive-only spot (calls/limps so far, no raise)
  - 2: facing one raise
  - 3: facing a re-raise or multi-raise spot

This keeps the abstraction focused on the current hand trace rather than on a
fictional cross-hand opponent profile.
"""

from collections import Counter

from pypokerengine.engine.hand_evaluator import HandEvaluator
from pypokerengine.utils.card_utils import estimate_hole_card_win_rate, gen_cards


ABSTRACTION_NAME = "rich_hand_strength"
ABSTRACTION_VERSION = "rich_hand_strength_v4"

STREETS = ("preflop", "flop", "turn", "river")
STREET_INDEX = {street: index for index, street in enumerate(STREETS)}
STREET_COUNT = len(STREETS)
STRENGTH_BUCKETS = 8
COMMITMENT_BUCKETS = 5
OPPONENT_TENDENCY_BUCKETS = 3
HISTORY_BUCKETS = 8

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
  position = 1 if has_position(round_state, player_uuid) else 0
  strength = hand_strength(hole_card, round_state["community_card"], postflop_simulations)
  history = compress_action_history(round_state["action_histories"], street)
  commitment_bucket, commitment_features = spr_commitment_bucket(round_state, player_uuid)
  opponent_tendency = opponent_tendency_bucket(opponent_action_stats)

  key = (
      STREET_INDEX[street],
      bucket_strength(strength),
      position,
      commitment_bucket,
      opponent_tendency,
      history,
  )
  return "|".join(str(part) for part in key), {
      "street": street,
      "strength": strength,
      "position": position,
      "spr": commitment_features["spr"],
      "call_share": commitment_features["call_share"],
      "stack_share": commitment_features["stack_share"],
      "commitment_bucket": commitment_bucket,
      "opponent_tendency_bucket": opponent_tendency,
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
  prior_aggression = 1 if any_prior_raise(action_histories, current_street) else 0
  current_state = summarize_current_street(action_histories.get(current_street, []))
  return prior_aggression * 4 + current_state


def any_prior_raise(action_histories, current_street):
  current_index = STREET_INDEX[current_street]
  for street in STREETS[:current_index]:
    for action in action_histories.get(street, []):
      if action.get("action") == "RAISE":
        return True
  return False


def summarize_current_street(street_actions):
  raises = 0
  passive_actions = 0

  for action in street_actions:
    move = action.get("action")
    if move in ("SMALLBLIND", "BIGBLIND", "ANTE"):
      continue
    if move == "RAISE":
      raises += 1
    elif move == "CALL":
      passive_actions += 1

  if raises >= 2:
    return 3
  if raises == 1:
    return 2
  if passive_actions > 0:
    return 1
  return 0


def spr_commitment_bucket(round_state, player_uuid):
  pot_size = pot_size_from_round_state(round_state)
  effective_stack = effective_stack_size(round_state, player_uuid)
  to_call = amount_to_call(round_state, player_uuid)
  spr = 6.0 if pot_size <= 0 else min(float(effective_stack) / max(pot_size, 1), 12.0)
  call_share = 0.0 if to_call <= 0 else float(to_call) / max(pot_size + to_call, 1)
  stack_share = 0.0 if to_call <= 0 else min(float(to_call) / max(effective_stack, 1), 0.999999)

  if to_call <= 0:
    bucket = 0 if spr >= 2.0 else 1
  elif stack_share >= 0.60 or spr < 0.75:
    bucket = 4
  elif stack_share >= 0.33 or call_share >= 0.38 or spr < 1.5:
    bucket = 3
  elif call_share >= 0.20 or spr < 3.0:
    bucket = 2
  else:
    bucket = 1

  return bucket, {
      "spr": spr,
      "to_call": to_call,
      "pot_size": pot_size,
      "call_share": call_share,
      "stack_share": stack_share,
      "effective_stack": effective_stack,
  }


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


def opponent_tendency_bucket(opponent_action_stats):
  raises = opponent_action_stats.get("raise", 0)
  calls = opponent_action_stats.get("call", 0)
  total = raises + calls
  if total <= 0:
    return 1

  aggression = float(raises) / total
  if raises >= 2 and aggression >= 0.55:
    return 2
  if aggression <= 0.25:
    return 0
  return 1


def observe_opponent_actions(action_histories, player_uuid):
  stats = {"raise": 0, "call": 0}
  for street in STREETS:
    for action in action_histories.get(street, []):
      if action.get("uuid") == player_uuid:
        continue
      move = action.get("action")
      if move == "RAISE":
        stats["raise"] += 1
      elif move == "CALL":
        stats["call"] += 1
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


def effective_stack_size(round_state, player_uuid):
  hero_stack = my_stack(round_state, player_uuid)
  villain_stack = min(
      seat["stack"] for seat in round_state["seats"] if seat["uuid"] != player_uuid
  )
  return min(hero_stack, villain_stack)


def abstraction_state_upper_bound():
  return (
      STREET_COUNT
      * STRENGTH_BUCKETS
      * 2
      * COMMITMENT_BUCKETS
      * OPPONENT_TENDENCY_BUCKETS
      * HISTORY_BUCKETS
  )
