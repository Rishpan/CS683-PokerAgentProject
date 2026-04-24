"""Compact MCCFR abstraction with a Bayesian opponent hand estimate.

Key layout:
  street | hero_strength | spr | opponent_strength

The opponent estimate is intentionally conservative. Aggressive actions update
belief toward both value and bluff classes so the abstraction does not
overreact to a single raise.
"""

from collections import Counter

try:
  from .mccfr_abstraction import hand_strength, my_stack, pot_size_from_round_state
except ImportError:
  from mccfr_abstraction import hand_strength, my_stack, pot_size_from_round_state


ABSTRACTION_NAME = "bayes_opponent_compact"
ABSTRACTION_VERSION = "bayes_opponent_compact_v1"

STREETS = ("preflop", "flop", "turn", "river")
STREET_INDEX = {street: index for index, street in enumerate(STREETS)}
HERO_STRENGTH_BUCKETS = 6
SPR_BUCKETS = 4
OPPONENT_BUCKETS = 5
OPPONENT_CLASSES = ("weak", "medium", "strong", "bluff")
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
  street = _normalize_street(round_state["street"])
  community_card = round_state["community_card"]
  hero_strength = hand_strength(hole_card, community_card, postflop_simulations)
  spr = stack_to_pot_ratio(round_state, player_uuid)
  opponent_posterior = opponent_hand_posterior(
      hole_card=hole_card,
      round_state=round_state,
      opponent_action_stats=opponent_action_stats,
      hero_strength=hero_strength,
  )
  opponent_strength = posterior_strength_score(opponent_posterior)

  key = (
      STREET_INDEX[street],
      _bucket(hero_strength, HERO_STRENGTH_BUCKETS),
      bucket_spr(spr),
      _bucket(opponent_strength, OPPONENT_BUCKETS),
  )
  return "|".join(str(part) for part in key), {
      "street": street,
      "hero_strength": hero_strength,
      "spr": spr,
      "opponent_strength": opponent_strength,
      "opponent_posterior": opponent_posterior,
  }


def observe_opponent_actions(action_histories, player_uuid):
  stats = {
      "raise_count": 0,
      "call_count": 0,
      "check_count": 0,
      "fold_count": 0,
      "events": [],
  }
  for street in STREETS:
    for action in action_histories.get(street, []):
      if action.get("uuid") == player_uuid:
        continue
      move = _encode_action(action.get("action"))
      if not move:
        continue
      if move == "raise":
        stats["raise_count"] += 1
      elif move == "call":
        stats["call_count"] += 1
      elif move == "check":
        stats["check_count"] += 1
      elif move == "fold":
        stats["fold_count"] += 1
      stats["events"].append(
          {
              "street": street,
              "action": move,
              "amount": max(action.get("amount", 0), 0),
              "paid": max(action.get("add_amount", action.get("paid", 0) or 0), 0),
          }
      )
  return stats


def abstraction_state_upper_bound():
  return len(STREETS) * HERO_STRENGTH_BUCKETS * SPR_BUCKETS * OPPONENT_BUCKETS


def stack_to_pot_ratio(round_state, player_uuid):
  pot_size = pot_size_from_round_state(round_state)
  if pot_size <= 0:
    return 4.0
  hero_stack = my_stack(round_state, player_uuid)
  villain_stack = min(
      seat["stack"] for seat in round_state["seats"] if seat["uuid"] != player_uuid
  )
  effective_stack = min(hero_stack, villain_stack)
  return min(float(effective_stack) / max(pot_size, 1), 8.0)


def opponent_hand_posterior(hole_card, round_state, opponent_action_stats, hero_strength):
  posterior = opponent_prior_distribution(
      hole_card=hole_card,
      community_card=round_state["community_card"],
      hero_strength=hero_strength,
  )
  small_blind = round_state.get("small_blind_amount", 10)
  for event in opponent_action_stats.get("events", []):
    likelihood = action_likelihood(event, small_blind)
    street_weight = 1.0 + 0.20 * STREET_INDEX[_normalize_street(event["street"])]
    posterior = normalize_distribution(
        {
            hand_class: posterior[hand_class] * (likelihood[hand_class] ** street_weight)
            for hand_class in OPPONENT_CLASSES
        }
    )
  return posterior


def opponent_prior_distribution(hole_card, community_card, hero_strength):
  board_wetness = board_texture_score(community_card)
  blocker = blocker_score(hole_card, community_card)
  strong = 0.20 + 0.10 * board_wetness - 0.14 * (hero_strength - 0.5) - 0.06 * blocker
  bluff = 0.16 + 0.08 * board_wetness + 0.04 * (1.0 - blocker)
  medium = 0.36 + 0.04 * (1.0 - board_wetness)
  weak = 1.0 - strong - bluff - medium
  return normalize_distribution(
      {
          "weak": max(weak, 0.12),
          "medium": max(medium, 0.22),
          "strong": max(strong, 0.10),
          "bluff": max(bluff, 0.10),
      }
  )


def action_likelihood(event, small_blind_amount):
  action = event["action"]
  pressure = min(
      float(event.get("paid", 0)) / max(float(small_blind_amount) * 4.0, 1.0),
      1.5,
  )
  if action == "raise":
    return {
        "weak": max(0.24, 0.74 - 0.28 * pressure),
        "medium": max(0.50, 0.92 - 0.10 * pressure),
        "strong": 1.18 + 0.55 * pressure,
        "bluff": 1.05 + 0.48 * pressure,
    }
  if action == "call":
    return {
        "weak": 0.92,
        "medium": 1.16 + 0.08 * pressure,
        "strong": 1.02 + 0.04 * pressure,
        "bluff": max(0.46, 0.70 - 0.10 * pressure),
    }
  if action == "check":
    return {
        "weak": 1.10,
        "medium": 1.00,
        "strong": 0.82,
        "bluff": 0.84,
    }
  if action == "fold":
    return {
        "weak": 1.35,
        "medium": 0.52,
        "strong": 0.18,
        "bluff": 0.42,
    }
  return {hand_class: 1.0 for hand_class in OPPONENT_CLASSES}


def posterior_strength_score(posterior):
  return max(
      0.0,
      min(
          0.999999,
          (
              0.12 * posterior["weak"]
              + 0.52 * posterior["medium"]
              + 0.90 * posterior["strong"]
              + 0.28 * posterior["bluff"]
          ),
      ),
  )


def board_texture_score(community_card):
  if not community_card:
    return 0.20

  suits = [card[0] for card in community_card]
  ranks = sorted(RANK_VALUE[card[1]] for card in community_card)
  unique_ranks = sorted(set(ranks))
  suit_pressure = max(Counter(suits).values()) / max(len(community_card), 1)
  paired = 1.0 if len(unique_ranks) < len(ranks) else 0.0
  high_cards = min(sum(rank >= 11 for rank in ranks) / max(len(ranks), 1), 1.0)
  connected = 0.0
  if len(unique_ranks) >= 2:
    span = max(unique_ranks) - min(unique_ranks)
    connected = max(0.0, 1.0 - float(span) / 10.0)
  return max(0.0, min(0.999999, 0.35 * suit_pressure + 0.25 * paired + 0.20 * high_cards + 0.20 * connected))


def blocker_score(hole_card, community_card):
  if not hole_card:
    return 0.0

  hole_ranks = [RANK_VALUE[card[1]] for card in hole_card]
  high_rank_blockers = sum(rank >= 11 for rank in hole_ranks) / max(len(hole_ranks), 1)

  board_rank_blockers = 0.0
  flush_blocker = 0.0
  if community_card:
    board_ranks = sorted((RANK_VALUE[card[1]] for card in community_card), reverse=True)
    important_ranks = set(board_ranks[:2])
    board_rank_blockers = sum(rank in important_ranks for rank in hole_ranks) / max(len(hole_ranks), 1)
    board_suits = Counter(card[0] for card in community_card)
    dominant_suit, dominant_count = board_suits.most_common(1)[0]
    if dominant_count >= 2:
      flush_blocker = sum(card[0] == dominant_suit for card in hole_card) / max(len(hole_card), 1)

  return max(
      0.0,
      min(
          0.999999,
          0.40 * high_rank_blockers + 0.35 * board_rank_blockers + 0.25 * flush_blocker,
      ),
  )


def bucket_spr(spr):
  if spr < 1.0:
    return 0
  if spr < 2.5:
    return 1
  if spr < 5.0:
    return 2
  return 3


def normalize_distribution(distribution):
  total = sum(max(value, 1e-9) for value in distribution.values())
  return {key: max(value, 1e-9) / total for key, value in distribution.items()}


def _bucket(value, bucket_count):
  clipped = max(0.0, min(float(value), 0.999999))
  return min(int(clipped * bucket_count), bucket_count - 1)


def _normalize_street(street):
  street = (street or "preflop").lower()
  return street if street in STREET_INDEX else "preflop"


def _encode_action(action):
  action = (action or "").upper()
  if action == "RAISE":
    return "raise"
  if action == "CALL":
    return "call"
  if action == "CHECK":
    return "check"
  if action == "FOLD":
    return "fold"
  return ""
