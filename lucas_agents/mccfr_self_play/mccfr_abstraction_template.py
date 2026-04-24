"""Template for a custom MCCFR self-play abstraction.

Copy this file, rename it, and then adjust the key features. The trainer and
player only depend on the interface defined here.
"""

ABSTRACTION_NAME = "replace_me"
ABSTRACTION_VERSION = "replace_me_v1"


def build_info_key(
    hole_card,
    round_state,
    player_uuid,
    opponent_action_stats,
    postflop_simulations,
):
  """Return ``(info_key, features)`` for the current information set.

  ``info_key`` must be a stable, JSON-serializable key, typically a string.
  ``features`` is optional debug metadata and is saved nowhere by the trainer.
  """
  del hole_card
  del player_uuid
  del opponent_action_stats
  del postflop_simulations

  street = round_state["street"]
  community_count = len(round_state["community_card"])
  key = f"{street}|board={community_count}"
  return key, {
      "street": street,
      "community_count": community_count,
  }


def observe_opponent_actions(action_histories, player_uuid):
  """Return any lightweight opponent summary consumed by ``build_info_key``."""
  del action_histories
  del player_uuid
  return {}


def abstraction_state_upper_bound():
  """Return the theoretical number of distinct infosets in this abstraction."""
  return 16
