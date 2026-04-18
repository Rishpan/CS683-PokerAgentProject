import json
import math
import os
import random
from copy import deepcopy
from datetime import datetime, timezone

from pypokerengine.players import BasePokerPlayer

from lucas_agents.learnable_agent_v0.abstraction import build_info_key


ACTIONS = ("fold", "call", "raise")
TOTAL_ABSTRACT_STATES = 4 * 12 * 5 * 2 * 6 * 8
STREET_THRESHOLDS = {
    "preflop": (0.74, 0.51),
    "flop": (0.70, 0.46),
    "turn": (0.73, 0.50),
    "river": (0.79, 0.57),
}
STREET_SIMULATIONS = {"flop": 96, "turn": 144, "river": 192}
STREET_WEIGHT = {
    "preflop": 0.55,
    "flop": 0.78,
    "turn": 0.92,
    "river": 1.0,
}
DEFAULT_POLICY_PATH = os.path.join(
    os.path.dirname(__file__), "learnable_cfr_policy.json"
)
DEFAULT_COVERAGE_PATH = os.path.join(
    os.path.dirname(__file__), "training_coverage.json"
)


def _utc_now():
  return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _read_json(path, default_value):
  if not os.path.exists(path):
    return default_value
  with open(path, "r", encoding="utf-8") as source:
    return json.load(source)


def _write_json(path, payload):
  os.makedirs(os.path.dirname(path), exist_ok=True)
  with open(path, "w", encoding="utf-8") as output:
    json.dump(payload, output, indent=2, sort_keys=True)


def _sanitize_features(features):
  return {
      "street": features["street"],
      "street_index": features["street_index"],
      "strength": round(features["strength"], 4),
      "draws": features["draws"],
      "position": features["position"],
      "pot_odds": round(features["pot_odds"], 4),
      "history": features["history"],
      "prior_aggression": features["prior_aggression"],
      "current_street_raises": features["current_street_raises"],
      "current_street_passive": features["current_street_passive"],
      "active_players": features["active_players"],
      "pressure": round(features["pressure"], 4),
      "spr": round(features["spr"], 4),
      "to_call": int(features["to_call"]),
      "pot_size": int(features["pot_size"]),
      "stack": int(features["stack"]),
  }


def _baseline_action(player, valid_actions, hole_card, round_state):
  street = round_state["street"]
  can_raise = any(entry["action"] == "raise" for entry in valid_actions)
  to_call = player._amount_to_call(round_state)
  pot_size = player._pot_size(round_state)
  stack = player._my_stack(round_state)
  pot_odds = 0.0 if to_call <= 0 else float(to_call) / max(pot_size + to_call, 1)
  pressure = 0.0 if stack <= 0 else float(to_call) / max(stack, 1)
  aggression, fold_rate = _opponent_stats(player, round_state)

  _, features = build_info_key(
      hole_card=hole_card,
      community_card=round_state["community_card"],
      street=street,
      action_histories=round_state["action_histories"],
      position=player._has_position(round_state),
      pot_odds=pot_odds,
      pressure=pressure,
      spr=float(stack) / max(pot_size, 1),
      simulations=STREET_SIMULATIONS.get(street, 64),
      active_players=player._active_player_count(round_state),
  )

  strength = features["strength"] + (0.015 if features["position"] else 0.0)
  strength += _board_pressure_adjustment(street, pressure)
  raise_threshold, call_threshold = STREET_THRESHOLDS.get(street, (0.75, 0.52))
  raise_threshold, call_threshold = _adjust_for_opponent(raise_threshold, call_threshold, aggression)
  raise_threshold, call_threshold = _adjust_for_price(
      raise_threshold, call_threshold, pot_odds, pressure
  )
  raise_threshold, call_threshold = _adjust_for_draws(
      raise_threshold, call_threshold, street, features["draws"], features["position"], to_call
  )
  raise_threshold, call_threshold = _adjust_for_history(
      raise_threshold,
      call_threshold,
      street,
      features["history"],
      features["position"],
      fold_rate,
      features["prior_aggression"],
      features["current_street_raises"],
      features["current_street_passive"],
  )
  raise_threshold -= 0.02 * fold_rate

  if to_call == 0:
    margin = 0.06
    if features["history"] in {1, 6} and street != "preflop" and features["position"]:
      margin = 0.07
    if street in {"flop", "turn"} and features["draws"] >= 3 and features["history"] in {0, 1, 6}:
      margin = max(margin, 0.075)
    return "raise" if can_raise and strength >= raise_threshold - margin else "call"
  if can_raise and strength >= raise_threshold:
    return "raise"
  if strength >= call_threshold:
    return "call"
  return "fold"


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
      stats = player._opponent_action_totals.setdefault(
          action.get("uuid"), {"raise": 0, "call": 0, "fold": 0}
      )
      if move == "raise":
        stats["raise"] += 1
      elif move in {"call", "check"}:
        stats["call"] += 1
      elif move == "fold":
        stats["fold"] += 1


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
    raise_threshold += 0.04
    call_threshold += 0.015
  elif history == 4:
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
  if prior_aggression and raises_seen == 0 and history == 6:
    call_threshold -= 0.005
  if raises_seen >= 2:
    raise_threshold += 0.01
    call_threshold += 0.01
  return raise_threshold, call_threshold


class LearnableCFRPlayer(BasePokerPlayer):
  """Online CFR-style player with a mild threshold-policy warm start.

  The threshold baseline only shapes unseen or low-visit states. As visits
  accumulate, regret matching and the saved average strategy dominate decisions.
  """

  TOTAL_ABSTRACT_STATES = TOTAL_ABSTRACT_STATES

  def __init__(
      self,
      policy_path=None,
      coverage_path=None,
      exploration=0.12,
      training_enabled=False,
      save_interval=100,
      baseline_prior_weight=0.30,
      baseline_assist=0.08,
      min_use_strategy_visits=8,
      discount_interval=0,
      discount_factor=0.995,
      random_seed=None,
  ):
    self.policy_path = policy_path or DEFAULT_POLICY_PATH
    self.coverage_path = coverage_path or DEFAULT_COVERAGE_PATH
    self.exploration = max(0.0, float(exploration))
    self.training_enabled = training_enabled
    self.save_interval = max(1, int(save_interval))
    self.baseline_prior_weight = max(0.0, float(baseline_prior_weight))
    self.baseline_assist = max(0.0, float(baseline_assist))
    self.min_use_strategy_visits = max(1, int(min_use_strategy_visits))
    self.discount_interval = max(0, int(discount_interval))
    self.discount_factor = min(1.0, max(0.90, float(discount_factor)))
    self.random = random.Random(random_seed)

    self.regret_sum = {}
    self.strategy_sum = {}
    self.state_visits = {}
    self.state_examples = {}
    self.round_decisions = []
    self.round_start_stack = 0
    self.round_count = 0
    self.player_num = 2
    self._tracked_round = None
    self._opponent_action_totals = {}
    self._seen_public_actions = set()
    self.current_context = {
        "opponent": "unknown",
        "seat": "player_a",
        "match_index": 0,
    }
    self._active_run = None

    self._load_policy()

  def set_training_context(self, opponent_name, seat_label, match_index):
    self.current_context = {
        "opponent": opponent_name,
        "seat": seat_label,
        "match_index": int(match_index),
    }

  def begin_training_run(self, run_metadata):
    run_id = run_metadata.get("run_id") or f"run-{_utc_now()}"
    self._active_run = {
        "run_id": run_id,
        "started_at": _utc_now(),
        "metadata": deepcopy(run_metadata),
        "unique_states_before": len(self.state_visits),
        "total_visits_before": sum(self.state_visits.values()),
        "state_visit_delta": {},
        "new_states": set(),
        "matches": 0,
        "decision_count": 0,
        "by_opponent": {},
        "by_seat": {},
    }
    return run_id

  def finish_training_run(self, extra_metadata=None):
    if not self._active_run:
      return None

    payload = _read_json(
        self.coverage_path,
        {"meta": {}, "latest_run": {}, "runs": [], "states": {}, "training": {}},
    )
    run = self._active_run
    run_id = run["run_id"]
    tracked_state_count = len(self.state_visits)
    total_state_visits = sum(self.state_visits.values())
    latest_coverage_pct = round(100.0 * tracked_state_count / TOTAL_ABSTRACT_STATES, 4)
    payload["meta"] = {
        "latest_run_id": run_id,
        "latest_updated_at": _utc_now(),
        "theoretical_abstract_state_count": TOTAL_ABSTRACT_STATES,
        "tracked_state_count": tracked_state_count,
        "latest_coverage_pct": latest_coverage_pct,
        "total_state_visits": total_state_visits,
        "policy_path": self.policy_path,
        "coverage_path": self.coverage_path,
    }
    payload["training"] = {
        "regret_sum": self.regret_sum,
        "state_visits": self.state_visits,
        "state_examples": self.state_examples,
        "config": {
            "exploration": self.exploration,
            "baseline_prior_weight": self.baseline_prior_weight,
            "baseline_assist": self.baseline_assist,
            "min_use_strategy_visits": self.min_use_strategy_visits,
            "discount_interval": self.discount_interval,
            "discount_factor": self.discount_factor,
        },
    }

    for info_key, visits in run["state_visit_delta"].items():
      state_entry = payload["states"].setdefault(
          info_key,
          {
              "total_visits": 0,
              "visits_by_run": {},
              "first_seen_run": run_id,
              "first_seen_at": run["started_at"],
              "example_features": self.state_examples.get(info_key, {}),
          },
      )
      state_entry["total_visits"] = self.state_visits.get(info_key, visits)
      state_entry["visits_by_run"][run_id] = visits
      state_entry["last_seen_run"] = run_id
      state_entry["last_seen_at"] = _utc_now()
      if not state_entry.get("example_features"):
        state_entry["example_features"] = self.state_examples.get(info_key, {})

    summary = {
        "run_id": run_id,
        "started_at": run["started_at"],
        "finished_at": _utc_now(),
        "matches": run["matches"],
        "decision_count": run["decision_count"],
        "unique_states_before": run["unique_states_before"],
        "unique_states_after": tracked_state_count,
        "new_state_count": len(run["new_states"]),
        "new_states": sorted(run["new_states"]),
        "total_visits_before": run["total_visits_before"],
        "total_visits_after": total_state_visits,
        "state_visit_delta_total": sum(run["state_visit_delta"].values()),
        "coverage_pct_after": latest_coverage_pct,
        "by_opponent": run["by_opponent"],
        "by_seat": run["by_seat"],
        "config": run["metadata"],
    }
    if extra_metadata:
      summary["result"] = deepcopy(extra_metadata)
    payload["latest_run"] = summary
    payload["runs"].append(summary)
    _write_json(self.coverage_path, payload)
    self._active_run = None
    return summary

  def declare_action(self, valid_actions, hole_card, round_state):
    self._sync_round_state(round_state)
    legal_actions = {entry["action"] for entry in valid_actions}
    baseline_action = _baseline_action(self, valid_actions, hole_card, round_state)
    info_key, features = self._build_info_set(hole_card, round_state)
    self._register_state_visit(info_key, features)

    if self.training_enabled:
      strategy = self._current_strategy(info_key, legal_actions, baseline_action)
      chosen_action = self._sample_action(strategy, legal_actions)
      self.round_decisions.append(
          {
              "info_key": info_key,
              "strategy": deepcopy(strategy),
              "legal_actions": sorted(legal_actions),
              "chosen_action": chosen_action,
              "baseline_action": baseline_action,
              "features": deepcopy(features),
              "context": deepcopy(self.current_context),
          }
      )
      return chosen_action

    average_strategy = self._average_strategy(info_key, legal_actions)
    visit_count = self.state_visits.get(info_key, 0)
    if average_strategy and visit_count >= self.min_use_strategy_visits:
      return max(average_strategy, key=average_strategy.get)
    if average_strategy and visit_count > 0:
      blended = self._blend_with_prior(average_strategy, legal_actions, baseline_action, visit_count)
      return max(blended, key=blended.get)
    return baseline_action

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

  def finish_game(self, final_seats, small_blind_amount):
    self._finalize_tracked_round(self._stack_from_seats(final_seats), small_blind_amount)

  def save_policy(self):
    payload = {
        "strategy_sum": self.strategy_sum,
        "meta": {
            "min_use_strategy_visits": self.min_use_strategy_visits,
            "theoretical_abstract_state_count": TOTAL_ABSTRACT_STATES,
            "tracked_state_count": len(self.state_visits),
            "saved_at": _utc_now(),
            "strategy_state_count": len(self.strategy_sum),
        },
    }
    _write_json(self.policy_path, payload)

  def _load_policy(self):
    policy_payload = _read_json(self.policy_path, {"strategy_sum": {}})
    coverage_payload = _read_json(
        self.coverage_path,
        {"training": {"regret_sum": {}, "state_visits": {}, "state_examples": {}}},
    )
    training_payload = coverage_payload.get("training", {})
    self.regret_sum = training_payload.get("regret_sum", {})
    self.strategy_sum = policy_payload.get("strategy_sum", {})
    self.state_visits = training_payload.get("state_visits", {})
    self.state_examples = training_payload.get("state_examples", {})

  def _build_info_set(self, hole_card, round_state):
    to_call = self._amount_to_call(round_state)
    pot_size = self._pot_size(round_state)
    stack = self._my_stack(round_state)
    pot_odds = 0.0 if to_call <= 0 else float(to_call) / max(pot_size + to_call, 1)
    pressure = 0.0 if stack <= 0 else min(1.0, float(to_call) / max(stack, 1))
    spr = float(stack) / max(pot_size, 1)
    key, features = build_info_key(
        hole_card=hole_card,
        community_card=round_state["community_card"],
        street=round_state["street"],
        action_histories=round_state["action_histories"],
        position=self._has_position(round_state),
        pot_odds=pot_odds,
        pressure=pressure,
        spr=spr,
        simulations=STREET_SIMULATIONS.get(round_state["street"], 64),
        active_players=self._active_player_count(round_state),
    )
    features["pressure"] = pressure
    features["spr"] = spr
    features["to_call"] = to_call
    features["pot_size"] = pot_size
    features["stack"] = stack
    return repr(key), features

  def _sync_round_state(self, round_state):
    round_count = int(round_state.get("round_count", 0))
    stack = self._my_stack(round_state)
    if self._tracked_round is None:
      self._tracked_round = round_count
      self.round_count = round_count
      self.round_start_stack = stack
      self.round_decisions = []
      return
    if round_count != self._tracked_round:
      self._finalize_tracked_round(stack, round_state["small_blind_amount"])
      self._tracked_round = round_count
      self.round_count = round_count
      self.round_start_stack = stack
      self.round_decisions = []

  def _finalize_tracked_round(self, final_stack, small_blind_amount):
    if not self.training_enabled or not self.round_decisions:
      return
    normalizer = max(small_blind_amount * 4, 1)
    chip_delta = final_stack - self.round_start_stack
    normalized_reward = max(-1.0, min(1.0, float(chip_delta) / normalizer))
    for decision in self.round_decisions:
      self._apply_regret_update(decision, normalized_reward)
    if self.discount_interval and self.round_count % self.discount_interval == 0:
      self._discount_tables()
    if self.round_count % self.save_interval == 0:
      self.save_policy()

  def _register_state_visit(self, info_key, features):
    is_new = info_key not in self.state_visits
    self.state_visits[info_key] = self.state_visits.get(info_key, 0) + 1
    self.state_examples.setdefault(info_key, _sanitize_features(features))

    if not self._active_run:
      return
    self._active_run["decision_count"] += 1
    self._active_run["state_visit_delta"][info_key] = (
        self._active_run["state_visit_delta"].get(info_key, 0) + 1
    )
    if is_new:
      self._active_run["new_states"].add(info_key)
    opponent = self.current_context["opponent"]
    seat = self.current_context["seat"]
    self._active_run["by_opponent"][opponent] = self._active_run["by_opponent"].get(opponent, 0) + 1
    self._active_run["by_seat"][seat] = self._active_run["by_seat"].get(seat, 0) + 1

  def _current_strategy(self, info_key, legal_actions, baseline_action):
    regrets = self.regret_sum.setdefault(info_key, self._zero_action_map())
    strategy_sums = self.strategy_sum.setdefault(info_key, self._zero_action_map())
    positive = {
        action: max(regrets[action], 0.0) if action in legal_actions else 0.0
        for action in ACTIONS
    }
    total_positive = sum(positive.values())

    if total_positive > 0:
      strategy = {
          action: positive[action] / total_positive if action in legal_actions else 0.0
          for action in ACTIONS
      }
    else:
      strategy = self._prior_strategy(legal_actions, baseline_action)

    if self.training_enabled and self.exploration > 0:
      uniform_share = 1.0 / max(len(legal_actions), 1)
      for action in ACTIONS:
        if action in legal_actions:
          strategy[action] = (
              (1.0 - self.exploration) * strategy[action]
              + self.exploration * uniform_share
          )

    for action in ACTIONS:
      strategy_sums[action] += strategy[action]
    return strategy

  def _average_strategy(self, info_key, legal_actions):
    action_map = self.strategy_sum.get(info_key)
    if not action_map:
      return None
    total = sum(float(action_map.get(action, 0.0)) for action in legal_actions)
    if total <= 0:
      return None
    return {
        action: float(action_map.get(action, 0.0)) / total if action in legal_actions else 0.0
        for action in ACTIONS
    }

  def _blend_with_prior(self, average_strategy, legal_actions, baseline_action, visit_count):
    prior = self._prior_strategy(legal_actions, baseline_action)
    prior_weight = min(0.45, 1.0 / max(math.sqrt(visit_count), 1.0))
    blended = {}
    for action in ACTIONS:
      if action not in legal_actions:
        blended[action] = 0.0
      else:
        blended[action] = (
            (1.0 - prior_weight) * average_strategy.get(action, 0.0)
            + prior_weight * prior.get(action, 0.0)
        )
    return blended

  def _prior_strategy(self, legal_actions, baseline_action):
    legal_count = max(len(legal_actions), 1)
    uniform = 1.0 / legal_count
    baseline_bonus = self.baseline_prior_weight
    strategy = {}
    total = 0.0
    for action in ACTIONS:
      if action not in legal_actions:
        strategy[action] = 0.0
        continue
      value = uniform
      if action == baseline_action:
        value += baseline_bonus
      strategy[action] = value
      total += value
    if total <= 0:
      return {action: (uniform if action in legal_actions else 0.0) for action in ACTIONS}
    return {
        action: strategy[action] / total if action in legal_actions else 0.0
        for action in ACTIONS
    }

  def _sample_action(self, strategy, legal_actions):
    draw = self.random.random()
    cumulative = 0.0
    fallback = "call" if "call" in legal_actions else sorted(legal_actions)[0]
    for action in ACTIONS:
      probability = strategy.get(action, 0.0)
      if probability <= 0:
        continue
      cumulative += probability
      if draw <= cumulative:
        return action
    return fallback

  def _apply_regret_update(self, decision, round_reward):
    info_key = decision["info_key"]
    regrets = self.regret_sum.setdefault(info_key, self._zero_action_map())
    visit_count = max(1, self.state_visits.get(info_key, 1))

    utilities = self._estimate_action_utilities(
        decision["features"],
        decision["legal_actions"],
        round_reward,
        decision["chosen_action"],
        decision["baseline_action"],
        visit_count,
    )
    node_value = sum(decision["strategy"][action] * utilities[action] for action in ACTIONS)
    for action in decision["legal_actions"]:
      regrets[action] += utilities[action] - node_value

  def _estimate_action_utilities(
      self,
      features,
      legal_actions,
      round_reward,
      chosen_action,
      baseline_action,
      visit_count,
  ):
    strength = features["strength"]
    pot_odds = features["pot_odds"]
    pressure = features["pressure"]
    draws = features["draws"]
    in_position = 1 if features["position"] else 0
    history = features["history"]
    street_weight = STREET_WEIGHT.get(features["street"], 0.8)

    utilities = self._zero_action_map()
    utilities["fold"] = -0.24 - 0.40 * max(0.0, strength - max(0.45, pot_odds))
    utilities["call"] = (strength - pot_odds) * 1.08 - 0.12 * pressure + 0.03 * draws
    utilities["raise"] = (
        strength * 1.22
        - 0.20 * pot_odds
        - 0.28 * pressure
        + 0.05 * in_position
        + (0.03 if history in {0, 1, 6} else -0.02 if history in {3, 5, 7} else 0.0)
    )

    observed_component = 0.72 * (round_reward * street_weight)
    utilities[chosen_action] = 0.28 * utilities[chosen_action] + observed_component

    assist = self.baseline_assist / math.sqrt(visit_count)
    if baseline_action in legal_actions:
      utilities[baseline_action] += assist

    for action in ACTIONS:
      if action not in legal_actions:
        utilities[action] = 0.0
    return utilities

  def _discount_tables(self):
    for table in (self.regret_sum, self.strategy_sum):
      for info_key, action_map in table.items():
        for action in ACTIONS:
          action_map[action] *= self.discount_factor

  def _zero_action_map(self):
    return {action: 0.0 for action in ACTIONS}

  def _stack_from_seats(self, seats):
    for seat in seats:
      if seat["uuid"] == getattr(self, "uuid", None):
        return seat["stack"]
    return 0

  def _my_stack(self, round_state):
    for seat in round_state["seats"]:
      if seat["uuid"] == getattr(self, "uuid", None):
        return seat["stack"]
    return 0

  def _my_seat_index(self, seats):
    for index, seat in enumerate(seats):
      if seat["uuid"] == getattr(self, "uuid", None):
        return index
    return None

  def _has_position(self, round_state):
    seats = round_state["seats"]
    my_index = self._my_seat_index(seats)
    if my_index is None:
      return False
    player_count = len(seats)
    dealer_btn = round_state["dealer_btn"]
    if player_count == 2:
      return my_index == dealer_btn and round_state["street"] != "preflop"
    return my_index == (dealer_btn - 1) % player_count

  def _pot_size(self, round_state):
    pot = round_state["pot"]
    return pot["main"]["amount"] + sum(side["amount"] for side in pot["side"])

  def _amount_to_call(self, round_state):
    histories = round_state["action_histories"].get(round_state["street"], [])
    highest_amount = 0
    my_amount = 0
    for action in histories:
      if action is None or "amount" not in action:
        continue
      amount = action["amount"]
      highest_amount = max(highest_amount, amount)
      if action.get("uuid") == getattr(self, "uuid", None):
        my_amount = amount
    return max(0, highest_amount - my_amount)

  def _active_player_count(self, round_state):
    return len([seat for seat in round_state["seats"] if seat["state"] != "folded"])


def setup_ai():
  return LearnableCFRPlayer()
