import json
import os

from pypokerengine.players import BasePokerPlayer
from pypokerengine.utils.card_utils import estimate_hole_card_win_rate, gen_cards

from lucas_agents.simplified_advanced_cfr.abstraction import build_info_key


ACTIONS = ("fold", "call", "raise")
POLICY_PATH = os.path.join(os.path.dirname(__file__), "advanced_cfr_policy.json")
STATS_PATH = os.path.join(os.path.dirname(__file__), "inference_stats.json")
TRACE_PATH = os.path.join(os.path.dirname(__file__), "latest_decision_trace.json")
TRACE_LIMIT = 120
STREET_THRESHOLDS = {
    "preflop": (0.74, 0.51),
    "flop": (0.70, 0.46),
    "turn": (0.73, 0.50),
    "river": (0.79, 0.57),
}
STREET_SIMULATIONS = {
    "flop": 48,
    "turn": 48,
    "river": 48,
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


def _load_policy():
  """
  Load the already-trained CFR averages once.

  The course requirement says the agent should not train live while choosing an
  action, so this function only reads the local saved policy from this folder.
  """
  if os.path.exists(POLICY_PATH):
    with open(POLICY_PATH, "r", encoding="utf-8") as source:
      payload = json.load(source)
    return payload.get("strategy_sum", {})
  return {}


def _read_json(path, default_value):
  if not os.path.exists(path):
    return default_value
  with open(path, "r", encoding="utf-8") as source:
    return json.load(source)


def _write_json(path, payload):
  with open(path, "w", encoding="utf-8") as output:
    json.dump(payload, output, indent=2, sort_keys=True)


def _default_stats():
  return {
      "total_decisions": 0,
      "base_action_used": 0,
      "learned_action_used": 0,
      "by_street": {
          "preflop": {"base": 0, "learned": 0},
          "flop": {"base": 0, "learned": 0},
          "turn": {"base": 0, "learned": 0},
          "river": {"base": 0, "learned": 0},
      },
  }


def _update_persistent_stats(street, used_learned_action):
  stats = _read_json(STATS_PATH, _default_stats())
  stats["total_decisions"] += 1
  if used_learned_action:
    stats["learned_action_used"] += 1
    stats["by_street"][street]["learned"] += 1
  else:
    stats["base_action_used"] += 1
    stats["by_street"][street]["base"] += 1
  _write_json(STATS_PATH, stats)


def _append_trace_entry(entry):
  trace = _read_json(TRACE_PATH, [])
  trace.append(entry)
  trace = trace[-TRACE_LIMIT:]
  _write_json(TRACE_PATH, trace)


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
  """
  Preserve the old agent's opponent model without using callback methods.

  The original `advanced_cfr` inherited a class that updated opponent counts in
  `receive_game_update_message`. Here we keep the callbacks untouched and
  instead increment the same kind of counters from the public action history
  whenever `declare_action` runs.
  """
  if not hasattr(player, "_opponent_action_totals"):
    player._opponent_action_totals = {}
  if not hasattr(player, "_seen_public_actions"):
    player._seen_public_actions = set()

  my_uuid = getattr(player, "uuid", None)
  round_count = round_state.get("round_count", 0)
  for street, street_actions in round_state["action_histories"].items():
    for index, action in enumerate(street_actions):
      if not action or action.get("uuid") == my_uuid:
        continue
      signature = (
          round_count,
          street,
          index,
          action.get("uuid"),
          action.get("action"),
          action.get("amount"),
      )
      if signature in player._seen_public_actions:
        continue
      player._seen_public_actions.add(signature)

      player_uuid = action.get("uuid")
      stats = player._opponent_action_totals.setdefault(
          player_uuid, {"raise": 0, "call": 0, "fold": 0}
      )
      move = action.get("action")
      if move in stats:
        stats[move] += 1
      elif move == "check":
        stats["call"] += 1


def _opponent_stats(player, round_state):
  _update_opponent_stats_from_history(player, round_state)
  stats = {"raise": 0, "call": 0, "fold": 0}
  for opponent in getattr(player, "_opponent_action_totals", {}).values():
    for action in stats:
      stats[action] += opponent[action]
  total = stats["raise"] + stats["call"] + stats["fold"]
  aggression = 0.25 if total == 0 else float(stats["raise"]) / total
  fold_rate = 0.18 if total == 0 else float(stats["fold"]) / total
  return aggression, fold_rate


def _preflop_strength(player, hole_card, round_state):
  ranks = sorted([RANK_VALUE[card[1]] for card in hole_card], reverse=True)
  high, low = ranks
  suited = hole_card[0][0] == hole_card[1][0]
  gap = high - low

  score = 0.35
  if high == low:
    score += 0.25 + min(high, 12) * 0.028
  else:
    score += max(high - 8, 0) * 0.045
    score += max(low - 8, 0) * 0.03
  if suited:
    score += 0.05
  if gap == 1:
    score += 0.05
  elif gap == 2:
    score += 0.025
  elif gap >= 4:
    score -= 0.05
  if high >= 12 and low >= 10:
    score += 0.06
  if high == 14 and low >= 10:
    score += 0.04
  if high < 10 and low < 8 and not suited:
    score -= 0.07
  if _has_position(player, round_state):
    score += 0.02
  return max(0.0, min(score, 0.95))


def _estimate_equity(player, hole_card, round_state):
  if round_state["street"] == "preflop":
    return _preflop_strength(player, hole_card, round_state)
  return estimate_hole_card_win_rate(
      nb_simulation=STREET_SIMULATIONS.get(round_state["street"], 48),
      nb_player=_active_player_count(round_state),
      hole_card=gen_cards(hole_card),
      community_card=gen_cards(round_state["community_card"]),
  )


def _position_bonus(player, round_state):
  return 0.015 if _has_position(player, round_state) else 0.0


def _board_pressure_adjustment(street, to_call, stack):
  adjustment = 0.0
  if street == "river":
    adjustment -= 0.01
  if stack > 0 and float(to_call) / stack >= 0.3:
    adjustment -= 0.04
  return adjustment


def _adjust_for_opponent(raise_threshold, call_threshold, aggression):
  if aggression >= 0.35:
    return raise_threshold + 0.03, call_threshold - 0.03
  if aggression <= 0.15:
    return raise_threshold - 0.02, call_threshold + 0.01
  return raise_threshold, call_threshold


def _adjust_for_price(raise_threshold, call_threshold, to_call, pot_size, stack):
  if to_call <= 0:
    return raise_threshold, call_threshold
  pot_odds = float(to_call) / max(pot_size + to_call, 1)
  stack_ratio = float(to_call) / max(stack, 1)
  call_threshold = max(call_threshold, pot_odds + 0.06)
  raise_threshold = max(raise_threshold, pot_odds + 0.18)
  if stack_ratio >= 0.35:
    call_threshold += 0.07
    raise_threshold += 0.05
  elif stack_ratio <= 0.08:
    call_threshold -= 0.02
  return raise_threshold, call_threshold


def _baseline_action(player, valid_actions, hole_card, round_state, aggression, fold_rate):
  """
  Use the rule-based backbone from the stronger agent as a safe fallback.

  The CFR table is sparse, so when a state is unseen or low-confidence we still
  want a deterministic decision that behaves well on the tournament portal.
  """
  street = round_state["street"]
  can_raise = any(action["action"] == "raise" for action in valid_actions)
  to_call = _amount_to_call(player, round_state)
  pot_size = _pot_size(round_state)
  stack = _my_stack(player, round_state)

  equity = _estimate_equity(player, hole_card, round_state)
  adjusted_equity = equity + _position_bonus(player, round_state)
  adjusted_equity += _board_pressure_adjustment(street, to_call, stack)

  raise_threshold, call_threshold = STREET_THRESHOLDS.get(street, (0.75, 0.52))
  raise_threshold, call_threshold = _adjust_for_opponent(raise_threshold, call_threshold, aggression)
  raise_threshold, call_threshold = _adjust_for_price(
      raise_threshold, call_threshold, to_call, pot_size, stack
  )
  raise_threshold -= 0.03 * fold_rate

  if to_call == 0:
    if can_raise and adjusted_equity >= raise_threshold - 0.06:
      action = "raise"
    else:
      action = "call"
  elif can_raise and adjusted_equity >= raise_threshold:
    action = "raise"
  elif adjusted_equity >= call_threshold:
    action = "call"
  else:
    action = "fold"

  return {
      "action": action,
      "street": street,
      "to_call": to_call,
      "pot_size": pot_size,
      "stack": stack,
      "equity": equity,
      "adjusted_equity": adjusted_equity,
      "raise_threshold": raise_threshold,
      "call_threshold": call_threshold,
      "aggression": aggression,
      "fold_rate": fold_rate,
      "hole_card": list(hole_card),
      "valid_actions": valid_actions,
  }


def _build_info_set(player, hole_card, round_state):
  to_call = _amount_to_call(player, round_state)
  pot_size = _pot_size(round_state)
  stack = _my_stack(player, round_state)
  pot_odds = 0.0 if to_call <= 0 else float(to_call) / max(pot_size + to_call, 1)
  pressure = 0.0 if stack <= 0 else min(1.0, float(to_call) / max(stack, 1))
  spr = float(stack) / max(pot_size, 1)
  key, features = build_info_key(
      hole_card=hole_card,
      community_card=round_state["community_card"],
      street=round_state["street"],
      action_histories=round_state["action_histories"],
      position=1 if _has_position(player, round_state) else 0,
      pot_odds=pot_odds,
      pressure=pressure,
      spr=spr,
      simulations=48,
  )
  features["to_call"] = to_call
  features["pot_size"] = pot_size
  features["stack"] = stack
  return repr(key), features


def _normalize_average_strategy(action_map, legal_actions):
  total = 0.0
  filtered = {}
  for action in ACTIONS:
    value = float(action_map.get(action, 0.0)) if action in legal_actions else 0.0
    filtered[action] = value
    total += value
  if total <= 0:
    return None
  return {action: filtered[action] / total for action in ACTIONS}


class SimplifiedAdvancedCFRPlayer(BasePokerPlayer):

  def __init__(self, use_learned_action=True):
    self.use_learned_action = use_learned_action

  def declare_action(self, valid_actions, hole_card, round_state):
    # Load the trained policy lazily so setup stays identical to the simple template.
    if not hasattr(self, "_strategy_sum"):
      self._strategy_sum = _load_policy()

    # Rebuild lightweight opponent features directly from public history because
    # the rest of the callback methods intentionally remain untouched.
    aggression, fold_rate = _opponent_stats(self, round_state)
    legal_actions = {entry["action"] for entry in valid_actions}
    base_details = _baseline_action(self, valid_actions, hole_card, round_state, aggression, fold_rate)
    base_action = base_details["action"]

    # Query the saved CFR average strategy for the current abstract information set.
    info_key, info_features = _build_info_set(self, hole_card, round_state)
    average_strategy = _normalize_average_strategy(self._strategy_sum.get(info_key, {}), legal_actions)

    # Only trust the learned action when the table is confident enough; otherwise
    # fall back to the rule-based action so unseen states stay stable.
    chosen_action = base_action
    used_learned_action = False
    learned_action = base_action
    learned_confidence = None
    if self.use_learned_action and average_strategy:
      learned_action = max(average_strategy, key=average_strategy.get)
      learned_confidence = average_strategy[learned_action]
      if learned_action != base_action and learned_confidence >= 0.72:
        chosen_action = learned_action
        used_learned_action = True

    _update_persistent_stats(round_state["street"], used_learned_action)
    _append_trace_entry(
        {
            "round_count": round_state.get("round_count"),
            "street": round_state["street"],
            "valid_actions": valid_actions,
            "hole_card": hole_card,
            "round_state": round_state,
            "derived": {
                "aggression": aggression,
                "fold_rate": fold_rate,
                "info_key": info_key,
                "info_features": info_features,
                "base_action": base_action,
                "chosen_action": chosen_action,
                "used_learned_action": used_learned_action,
                "learned_action": learned_action,
                "learned_confidence": learned_confidence,
                "average_strategy": average_strategy,
                "base_details": base_details,
            },
        }
    )
    return chosen_action

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


def setup_ai():
  return SimplifiedAdvancedCFRPlayer()
