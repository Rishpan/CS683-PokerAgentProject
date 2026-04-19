"""
Hand Abstraction for Texas Hold'em CFR
=======================================
Maps raw hands to abstract buckets (0-7) to make the state space tractable.

Card string format in PyPokerEngine: '{suit}{rank}'
  suit = 'C' (clubs), 'D' (diamonds), 'H' (hearts), 'S' (spades)
  rank = '2'-'9', 'T', 'J', 'Q', 'K', 'A'
  Example: 'CA' = Ace of Clubs, 'DK' = King of Diamonds, 'H9' = Nine of Hearts

Bucket range: 0 (weakest) to 7 (strongest)
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from pypokerengine.engine.card import Card
from pypokerengine.utils.card_utils import estimate_hole_card_win_rate, gen_cards

NUM_BUCKETS = 8

# Rank string to integer value mapping
_RANK_MAP = {
    '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7,
    '8': 8, '9': 9, 'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14
}


def preflop_bucket(hole_card_strs):
    """
    Assign a preflop hand to one of 8 strength buckets using a scoring heuristic.

    The heuristic captures the key dimensions of preflop hand strength:
      - High card value (normalized contribution from both cards)
      - Pair bonus (biggest single factor)
      - Suited bonus
      - Connectedness bonus (gap between ranks)

    Args:
        hole_card_strs: list of 2 card strings, e.g. ['CA', 'DK']
                        Format: '{suit}{rank}' where suit in CDHS, rank in 2-9TJQKA

    Returns:
        int: 0 (weakest) to 7 (strongest)

    Score computation:
        base score from high/low card value: 0.0 – 0.80
        + 0.30 for pairs
        + 0.05 for suited
        + 0.03 for connectors (gap == 1)
        + 0.01 for one-gap connectors (gap == 2)

    Bucket thresholds:
        [0, 0.25) → 0   weakest (e.g. 7-2 offsuit)
        [0.25, 0.35) → 1
        [0.35, 0.45) → 2
        [0.45, 0.55) → 3
        [0.55, 0.65) → 4
        [0.65, 0.75) → 5
        [0.75, 0.85) → 6
        [0.85, 1.0)  → 7  strongest (e.g. AA, KK, AKs)
    """
    # Parse card strings: card[0] = suit letter, card[1] = rank letter
    cards = [(c[0], c[1]) for c in hole_card_strs]
    ranks = sorted([_RANK_MAP[c[1]] for c in cards], reverse=True)
    suits = [c[0] for c in cards]

    high, low = ranks[0], ranks[1]
    suited = (suits[0] == suits[1])
    gap = high - low

    # Base score: normalized contribution from both cards
    # High card: maps [2,14] → [0, ~0.50], Low card: maps [2,14] → [0, ~0.30]
    score = (high - 2) / 12.0 * 0.5 + (low - 2) / 12.0 * 0.3

    # Pair bonus (gap == 0)
    if gap == 0:
        score += 0.30

    # Suited bonus
    if suited:
        score += 0.05

    # Connectivity bonus
    if gap == 1:
        score += 0.03
    elif gap == 2:
        score += 0.01

    # Clamp to [0, 1)
    score = min(max(score, 0.0), 0.999)

    # Map score to bucket index
    thresholds = [0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.85]
    for i, t in enumerate(thresholds):
        if score < t:
            return i
    return 7


def postflop_bucket(hole_card_strs, community_card_strs, nb_simulation=50):
    """
    Assign a postflop hand to one of 8 strength buckets using Monte Carlo equity estimation.

    Runs a Monte Carlo simulation to estimate the probability of winning against
    a random opponent hand, then maps that win rate to a bucket.

    Args:
        hole_card_strs: list of 2 card strings, e.g. ['CA', 'DK']
        community_card_strs: list of 3, 4, or 5 community card strings
        nb_simulation: number of MC rollouts (default 50 for speed, use 200+ for accuracy)

    Returns:
        int: 0 (weakest) to 7 (strongest)
    """
    hole = gen_cards(hole_card_strs)
    community = gen_cards(community_card_strs)
    win_rate = estimate_hole_card_win_rate(
        nb_simulation=nb_simulation,
        nb_player=2,
        hole_card=hole,
        community_card=community
    )
    # Map win_rate [0.0, 1.0] → bucket [0, 7]
    return min(int(win_rate * NUM_BUCKETS), NUM_BUCKETS - 1)


def get_hand_bucket(hole_card_strs, community_card_strs):
    """
    Get hand strength bucket based on the current street.

    Uses the preflop formula (no MC simulation) when there are no community cards,
    and Monte Carlo equity estimation for postflop streets.

    Args:
        hole_card_strs: list of 2 card strings
        community_card_strs: list of 0, 3, 4, or 5 community card strings

    Returns:
        int: 0 (weakest) to 7 (strongest)
    """
    if len(community_card_strs) == 0:
        return preflop_bucket(hole_card_strs)
    return postflop_bucket(hole_card_strs, community_card_strs)


def compress_action_history(action_histories_dict, street):
    """
    Convert PyPokerEngine's action_histories dict to a compact string for info set keys.

    Each street's actions are encoded as a sequence of single characters:
      'R' = raise, 'C' = call/check, 'F' = fold

    Streets are separated by '/', and only streets up to (and including) the
    current street are included.

    Args:
        action_histories_dict: round_state['action_histories']
            e.g. {'preflop': [{'action': 'call', 'amount': 10, 'uuid': '...'}, ...],
                  'flop': [...], ...}
        street: current street string ('preflop', 'flop', 'turn', 'river')

    Returns:
        str: compact action string, e.g. 'RC/C/CR'
             (preflop: raise-call / flop: call / turn: call-raise)

    Examples:
        preflop call only        → 'C'
        preflop raise, call      → 'RC'
        flop check, bet, call    → '.../CRC'   (with preflop prefix)
    """
    street_order = ['preflop', 'flop', 'turn', 'river']
    result = []

    for s in street_order:
        if s not in action_histories_dict:
            # Street hasn't happened yet; stop here
            break

        actions = action_histories_dict[s]
        if not actions:
            result.append('')
        else:
            compressed = ''
            for act in actions:
                a = act.get('action', '')
                if a == 'raise':
                    compressed += 'R'
                elif a in ('call', 'check'):
                    compressed += 'C'
                elif a == 'fold':
                    compressed += 'F'
                # Skip unknown action types
            result.append(compressed)

        if s == street:
            break

    return '/'.join(result)


def make_info_set_key(hole_card_strs, community_card_strs, action_history_str, position):
    """
    Create a hashable information set key for the CFR strategy table lookup.

    The information set captures everything the player can observe:
      - Hand strength (abstracted to a bucket, losing some information)
      - Position (out-of-position=0 or in-position=1)
      - Betting history (compressed to a compact string)

    Args:
        hole_card_strs: agent's hole cards, e.g. ['CA', 'DK']
        community_card_strs: visible community cards, e.g. ['H5', 'S7', 'D2']
        action_history_str: compressed action history from compress_action_history()
        position: 0 (out of position / small blind) or 1 (in position / big blind)

    Returns:
        tuple: (bucket: int, position: int, action_history_str: str)
               This tuple is hashable and can be used as a dict key.

    Example:
        hole=['CA','DK'], community=[], history='RC', position=1
        → (7, 1, 'RC')   (bucket 7 = very strong hand, in position, facing a raise)
    """
    bucket = get_hand_bucket(hole_card_strs, community_card_strs)
    return (bucket, position, action_history_str)


# ---------------------------------------------------------------------------
# Quick self-test when run directly
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    print("Hand Abstraction Self-Test")
    print("=" * 40)

    # Preflop bucket tests
    test_hands = [
        (['C7', 'D2'], 'Weakest: 7-2 offsuit'),
        (['CA', 'DA'], 'Pocket Aces (suited)'),
        (['CK', 'DK'], 'Pocket Kings'),
        (['CA', 'HK'], 'Ace-King offsuit'),
        (['CA', 'SA'], 'Pocket Aces (suited)'),
        (['H9', 'S8'], '9-8 suited'),
        (['C3', 'H7'], '7-3 offsuit'),
        (['DQ', 'HJ'], 'Queen-Jack offsuit'),
    ]

    print("\nPreflop Buckets (0=weakest, 7=strongest):")
    for hand, desc in test_hands:
        bucket = preflop_bucket(hand)
        print(f"  {hand[0]}{hand[1]}  bucket={bucket}  ({desc})")

    print("\naction_history compression test:")
    histories = {
        'preflop': [
            {'action': 'raise', 'amount': 20, 'uuid': 'p1'},
            {'action': 'call', 'amount': 20, 'uuid': 'p2'},
        ],
        'flop': [
            {'action': 'call', 'amount': 0, 'uuid': 'p2'},
            {'action': 'raise', 'amount': 40, 'uuid': 'p1'},
            {'action': 'call', 'amount': 40, 'uuid': 'p2'},
        ]
    }
    result = compress_action_history(histories, 'flop')
    print(f"  Preflop raise+call, Flop check+raise+call → '{result}'")
    assert result == 'RC/CRC', f"Expected 'RC/CRC' got '{result}'"
    print("  [PASS]")

    print("\ninfo set key test:")
    key = make_info_set_key(['CA', 'CK'], [], 'RC', 1)
    print(f"  AKs preflop, position=1, history='RC' → {key}")
    print("  Bucket should be 7 (very strong):", "PASS" if key[0] == 7 else "FAIL")
