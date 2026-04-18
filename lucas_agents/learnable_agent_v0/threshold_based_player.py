from pypokerengine.players import BasePokerPlayer

from lucas_agents.learnable_agent_v0.abstraction import build_info_key


class ThresholdBasedPlayer(BasePokerPlayer):
  """Threshold policy built on the compact abstraction from `learnable_agent_v0`.

  Decision flow:
  1. Extract price and stack context from `round_state`.
  2. Build the abstraction key/features from cards + public history.
  3. Start from the same stable street thresholds as `ConditionThresholdPlayer`.
  4. Apply small adjustments for opponent style, price, draws, position, and history.
  5. Compare estimated strength against thresholds and choose raise/call/fold.

  Why this version should be stronger than the earlier attempt:
  - it keeps the strong baseline logic from `ConditionThresholdPlayer`
  - it uses the abstraction as a small edge, not a second competing strategy
  - history mostly changes how credible current aggression is, instead of
    pulling thresholds around too aggressively
  """

  STREET_THRESHOLDS = {
      "preflop": (0.74, 0.51),
      "flop": (0.70, 0.46),
      "turn": (0.73, 0.50),
      "river": (0.79, 0.57),
  }
  STREET_SIMULATIONS = {"flop": 96, "turn": 144, "river": 192}

  def __init__(self):
    self._opponent_action_totals = {}
    self._seen_public_actions = set()

  def declare_action(self, valid_actions, hole_card, round_state):
    street = round_state["street"]
    can_raise = any(entry["action"] == "raise" for entry in valid_actions)
    to_call = _amount_to_call(self, round_state)
    pot_size = _pot_size(round_state)
    stack = _my_stack(self, round_state)
    active_players = _active_player_count(round_state)
    pot_odds = 0.0 if to_call <= 0 else float(to_call) / max(pot_size + to_call, 1)
    pressure = 0.0 if stack <= 0 else float(to_call) / max(stack, 1)
    spr = float(stack) / max(pot_size, 1)
    aggression, fold_rate = _opponent_stats(self, round_state)

    _, features = build_info_key(
        hole_card=hole_card,
        community_card=round_state["community_card"],
        street=street,
        action_histories=round_state["action_histories"],
        position=_has_position(self, round_state),
        pot_odds=pot_odds,
        pressure=pressure,
        spr=spr,
        simulations=self.STREET_SIMULATIONS.get(street, 64),
        active_players=active_players,
    )

    strength = features["strength"]
    draws = features["draws"]
    history = features["history"]
    prior_aggression = features["prior_aggression"]
    current_raises = features["current_street_raises"]
    current_passive = features["current_street_passive"]
    adjusted_strength = strength + (0.015 if features["position"] else 0.0)
    adjusted_strength += _board_pressure_adjustment(street, pressure)

    raise_threshold, call_threshold = self.STREET_THRESHOLDS.get(street, (0.75, 0.52))
    raise_threshold, call_threshold = _adjust_for_opponent(raise_threshold, call_threshold, aggression)
    raise_threshold, call_threshold = _adjust_for_price(
        raise_threshold, call_threshold, pot_odds, pressure
    )
    raise_threshold, call_threshold = _adjust_for_draws(
        raise_threshold, call_threshold, street, draws, features["position"], to_call
    )
    raise_threshold, call_threshold = _adjust_for_history(
        raise_threshold,
        call_threshold,
        street,
        history,
        features["position"],
        fold_rate,
        prior_aggression,
        current_raises,
        current_passive,
    )
    raise_threshold -= 0.02 * fold_rate

    if to_call == 0:
      free_raise_margin = 0.06
      if history in {1, 6} and street != "preflop" and features["position"]:
        free_raise_margin = 0.07
      if street in {"flop", "turn"} and draws >= 3 and history in {0, 1, 6}:
        free_raise_margin = max(free_raise_margin, 0.075)
      if can_raise and adjusted_strength >= raise_threshold - free_raise_margin:
        return "raise"
      return "call"
    if can_raise and adjusted_strength >= raise_threshold:
      return "raise"
    if adjusted_strength >= call_threshold:
      return "call"
    return "fold"

  def receive_game_start_message(self, game_info):
    pass

  def receive_round_start_message(self, round_count, hole_card, seats):
    pass

  def receive_street_start_message(self, street, round_state):
    pass

  def receive_game_update_message(self, action, round_state):
    pass

  def receive_round_result_message(self, winners, hand_info, round_state):
    pass


def _my_stack(player, round_state):
  for seat in round_state["seats"]:
    if seat["uuid"] == getattr(player, "uuid", None):
      return seat["stack"]
  return 0


def _my_seat_index(player, seats):
  for index, seat in enumerate(seats):
    if seat["uuid"] == getattr(player, "uuid", None):
      return index
  return None


def _has_position(player, round_state):
  seats = round_state["seats"]
  my_index = _my_seat_index(player, seats)
  if my_index is None:
    return False
  player_count = len(seats)
  dealer_btn = round_state["dealer_btn"]
  if player_count == 2:
    return my_index == dealer_btn and round_state["street"] != "preflop"
  return my_index == (dealer_btn - 1) % player_count


def _pot_size(round_state):
  pot = round_state["pot"]
  return pot["main"]["amount"] + sum(side["amount"] for side in pot["side"])


def _amount_to_call(player, round_state):
  histories = round_state["action_histories"].get(round_state["street"], [])
  highest_amount = 0
  my_amount = 0
  for action in histories:
    if action is None or "amount" not in action:
      continue
    amount = action["amount"]
    highest_amount = max(highest_amount, amount)
    if action.get("uuid") == getattr(player, "uuid", None):
      my_amount = amount
  return max(0, highest_amount - my_amount)


def _active_player_count(round_state):
  return len([seat for seat in round_state["seats"] if seat["state"] != "folded"])


def _update_opponent_stats_from_history(player, round_state):
  my_uuid = getattr(player, "uuid", None)
  round_count = round_state.get("round_count", 0)
  for street, actions in round_state["action_histories"].items():
    for index, action in enumerate(actions):
      if not action or action.get("uuid") == my_uuid:
        continue
      move = (action.get("action") or "").lower()
      signature = (round_count, street, index, action.get("uuid"), move, action.get("amount"))
      if signature in player._seen_public_actions:
        continue
      player._seen_public_actions.add(signature)
      stats = player._opponent_action_totals.setdefault(action.get("uuid"), {"raise": 0, "call": 0, "fold": 0})
      if move == "raise":
        stats["raise"] += 1
      elif move in {"call", "check"}:
        stats["call"] += 1
      elif move == "fold":
        stats["fold"] += 1


def _opponent_stats(player, round_state):
  _update_opponent_stats_from_history(player, round_state)
  raise_total = call_total = fold_total = 0
  for stats in player._opponent_action_totals.values():
    raise_total += stats["raise"]
    call_total += stats["call"]
    fold_total += stats["fold"]
  total = raise_total + call_total + fold_total
  if total == 0:
    return 0.25, 0.18
  return float(raise_total) / total, float(fold_total) / total


def _board_pressure_adjustment(street, pressure):
  adjustment = -0.01 if street == "river" else 0.0
  if pressure >= 0.30:
    adjustment -= 0.04
  return adjustment


def _adjust_for_opponent(raise_threshold, call_threshold, aggression):
  if aggression >= 0.35:
    return raise_threshold + 0.03, call_threshold - 0.03
  if aggression <= 0.15:
    return raise_threshold - 0.02, call_threshold + 0.01
  return raise_threshold, call_threshold


def _adjust_for_price(raise_threshold, call_threshold, pot_odds, pressure):
  call_threshold = max(call_threshold, pot_odds + 0.06)
  raise_threshold = max(raise_threshold, pot_odds + 0.18)
  if pressure >= 0.35:
    return raise_threshold + 0.05, call_threshold + 0.07
  if pressure <= 0.08:
    return raise_threshold, call_threshold - 0.02
  return raise_threshold, call_threshold


def _adjust_for_draws(raise_threshold, call_threshold, street, draws, in_position, to_call):
  if street in {"flop", "turn"} and draws >= 2:
    call_threshold -= 0.02
    if in_position and to_call <= 0 and draws >= 3:
      raise_threshold -= 0.02
    elif in_position and draws >= 3:
      raise_threshold -= 0.01
  if street in {"flop", "turn"} and draws >= 3:
    call_threshold -= 0.005
  return raise_threshold, call_threshold


def _adjust_for_history(
    raise_threshold,
    call_threshold,
    street,
    history,
    in_position,
    fold_rate,
    prior_aggression,
    raises_seen,
    passive_count,
):
  # Quiet lines are the safest places to add controlled aggression.
  if history == 0 and street != "preflop" and in_position:
    raise_threshold -= 0.01
  elif history == 1:
    raise_threshold -= 0.015 + 0.02 * fold_rate
    if passive_count >= 2:
      call_threshold -= 0.005
    if in_position and street != "preflop":
      raise_threshold -= 0.005
  elif history == 2:
    raise_threshold += 0.015
    call_threshold -= 0.01
  elif history == 3:
    # Passive -> raise is usually stronger than a direct bet.
    raise_threshold += 0.04
    call_threshold += 0.015
  elif history == 4:
    # Raise -> passive often means the line cooled down after initiative.
    raise_threshold += 0.01
    call_threshold -= 0.005
  elif history == 5:
    raise_threshold += 0.05
    call_threshold += 0.03
  elif history == 6:
    call_threshold -= 0.01
    if in_position and street != "preflop":
      raise_threshold -= 0.005
  elif history == 7:
    raise_threshold += 0.03
    call_threshold += 0.005

  if prior_aggression and raises_seen == 0 and history in {6}:
    call_threshold -= 0.005
  if raises_seen >= 2:
    raise_threshold += 0.01
    call_threshold += 0.01
  return raise_threshold, call_threshold


def setup_ai():
  return ThresholdBasedPlayer()
