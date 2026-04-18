"""Compact information-state abstraction for a learnable rule-based agent.

Feature importance, from most important to least:
1. strength: strongest single signal; improve with opponent-range-aware equity.
2. street_index: changes hand meaning and action semantics by phase.
3. history: compact public betting-pattern bucket.
4. pot_odds: immediate price to continue.
5. draws: future-improvement potential.
6. position: small but consistent strategic edge.

Current key structure:
- `(street_index, strength_bucket, draws, position, pot_odds_bucket, history)`

Theoretical unique values per key entry:
- `street_index`: `4` values
  - `preflop`, `flop`, `turn`, `river`
- `strength_bucket`: `12` values
  - from `_bucket(strength, 12)`
- `draws`: `5` values
  - `0..4`
- `position`: `2` values
  - `0` or `1`
- `pot_odds_bucket`: `6` values
  - from `_bucket(pot_odds, 6)`
- `history`: `8` values
  - compact public betting-pattern bucket

New history representation:
- `0`: no strategic action yet
- `1`: passive-only current street
- `2`: raise-only current street
- `3`: passive -> raise on current street
- `4`: raise -> passive on current street
- `5`: multi-raise / highly contested current street
- `6`: earlier-street aggression, current street quiet or passive so far
- `7`: earlier-street aggression and current street already aggressive

This keeps what history was intended to capture:
- are we in a passive or aggressive line?
- has the hand already become aggressive on earlier streets?
- did the current street start passive and then become aggressive?
- did the current street start aggressive and then cool down?
- is the current street already heavily contested?

Why this simplification helps:
- the old raw-string history caused state explosion
- most of those strings were sparse and not worth learning separately
- the new indicators keep the main strategic distinctions while making the state
  space small enough to learn from realistic data

Theoretical total number of unique abstract states:
- `4 * 12 * 5 * 2 * 6 * 8`
- `23,040`

Complexity ranking by number of possible values:
1. `strength_bucket`: `12`
2. `history`: `8`
3. `pot_odds_bucket`: `6`
4. `draws`: `5`
5. `street_index`: `4`
6. `position`: `2`

Possible additions:
- opponent count buckets beyond raw active_players equity
- last aggressor / facing raise flag
- raise-size bucket
- nut advantage / range advantage proxy
- showdown tendency or fold-to-raise opponent features
"""

from collections import Counter

from pypokerengine.utils.card_utils import estimate_hole_card_win_rate, gen_cards

STREETS = ("preflop", "flop", "turn", "river")
STREET_INDEX = {name: i for i, name in enumerate(STREETS)}
RANK_VALUE = {r: i for i, r in enumerate("..23456789TJQKA")}

# Keep the key compact but readable: continuous values are bucketed, categorical
# values preserve semantics that matter for strategy lookup.
FEATURE_MEANINGS = {
    "street_index": "Which phase of the hand we are in.",
    "strength": "Estimated win probability / hand quality from this state.",
    "draws": "Flush/straight draw potential.",
    "position": "1 in position, 0 out of position.",
    "pot_odds": "Price to continue relative to the pot.",
    "history": "0..7 public betting-pattern bucket.",
}


def build_info_key(
    hole_card,
    community_card,
    street,
    action_histories,
    position,
    pot_odds,
    pressure,
    spr,
    simulations=48,
    active_players=2,
):
  street = _normalize_street(street)
  strength = hand_strength(hole_card, community_card, simulations, active_players)
  features = {
      "street": street,
      "street_index": STREET_INDEX[street],
      "strength": strength,
      "draws": _draw_bucket(hole_card, community_card),
      "pot_odds": max(0.0, pot_odds),
      "position": 1 if position else 0,
      "history": history_bucket(action_histories, street),
      "prior_aggression": _prior_street_aggression(action_histories, street),
      "current_street_raises": _current_street_raises(action_histories, street),
      "current_street_passive": _current_street_passive_count(action_histories, street),
      # Convenience metadata for debugging and future extensions.
      "active_players": max(2, int(active_players)),
      "feature_meanings": FEATURE_MEANINGS,
  }
  key = (
      features["street_index"],
      _bucket(strength, 12),
      features["draws"],
      features["position"],
      _bucket(min(features["pot_odds"], 0.999999), 6),
      features["history"],
  )
  return key, features


def hand_strength(hole_card, community_card, simulations=48, active_players=2):
  if not community_card:
    return _preflop_score(hole_card)
  return estimate_hole_card_win_rate(
      nb_simulation=simulations,
      nb_player=max(2, int(active_players)),
      hole_card=gen_cards(hole_card),
      community_card=gen_cards(community_card),
  )


def compress_history(action_histories, street):
  """Compatibility helper returning the compact history bucket."""
  return history_bucket(action_histories, street)


def history_bucket(action_histories, street):
  """Return a compact 0..7 public betting-pattern bucket.

  The first six buckets describe the current street action shape. The last two
  buckets are used when an earlier street already contained aggression and the
  current street is either still quiet/passive or already aggressive.
  """
  prior = _prior_street_aggression(action_histories, street)
  encoded = [_encode_action(action.get("action")) for action in action_histories.get(street, [])]
  encoded = [move for move in encoded if move in {"r", "c"}]
  current_raises = encoded.count("r")

  if prior:
    return 7 if current_raises > 0 else 6
  if not encoded:
    return 0
  passive_count = encoded.count("c")
  if current_raises >= 2:
    return 5
  if current_raises == 0:
    return 1
  if passive_count == 0:
    return 2
  first_raise = encoded.index("r")
  return 3 if first_raise > 0 else 4


def _encode_action(move):
  move = (move or "").lower()
  if move == "raise":
    return "r"
  if move in {"call", "check"}:
    return "c"
  if move == "fold":
    return "f"
  if move in {"smallblind", "bigblind", "ante", "straddle"}:
    return ""
  return ""


def _prior_street_aggression(action_histories, street):
  for name in STREETS:
    if name == street:
      break
    if _current_street_raises(action_histories, name) > 0:
      return 1
  return 0


def _current_street_raises(action_histories, street):
  raise_count = 0
  for action in action_histories.get(street, []):
    if _encode_action(action.get("action")) == "r":
      raise_count += 1
  return raise_count


def _current_street_passive_count(action_histories, street):
  passive_count = 0
  for action in action_histories.get(street, []):
    if _encode_action(action.get("action")) == "c":
      passive_count += 1
  return passive_count


def _normalize_street(street):
  street = (street or "preflop").lower()
  return street if street in STREET_INDEX else "preflop"


def _preflop_score(hole_card):
  ranks = sorted((RANK_VALUE[c[1]] for c in hole_card), reverse=True)
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


def _draw_bucket(hole_card, community_card):
  if len(community_card) < 3:
    return 0
  cards = hole_card + community_card
  flush_draw = int(max(Counter(card[0] for card in cards).values()) >= 4 and len(community_card) < 5)
  ranks = sorted({RANK_VALUE[c[1]] for c in cards})
  if 14 in ranks:
    ranks = [1] + ranks
  longest = current = 1
  gaps = 0
  for left, right in zip(ranks, ranks[1:]):
    diff = right - left
    if diff == 1:
      current += 1
    elif diff == 2:
      current += 1
      gaps += 1
    else:
      longest, current, gaps = max(longest, current), 1, 0
  longest = max(longest, current)
  straight_draw = 2 if longest >= 4 and gaps == 0 else 1 if longest >= 4 else 0
  return min(flush_draw * 2 + straight_draw, 4)


def _board_texture_bucket(community_card):
  if not community_card:
    return 0
  ranks = [RANK_VALUE[c[1]] for c in community_card]
  suits = [c[0] for c in community_card]
  return (
      int(len(set(ranks)) < len(ranks))
      + 2 * int(max(Counter(suits).values()) >= 2)
      + 4 * int(sum(rank >= 10 for rank in ranks) >= 2)
      + 8 * int(max(ranks) - min(ranks) <= 4)
  )


def _bucket(value, bucket_count):
  value = max(0.0, min(float(value), 0.999999))
  return min(int(value * bucket_count), bucket_count - 1)
