import argparse
import os
import sys
import time
import traceback

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
  sys.path.insert(0, PROJECT_ROOT)

from pypokerengine.api.game import setup_config, start_poker

from lucas_agents.learnable_adversarial_search_agent_v3.cfr import DEFAULT_POLICY_PATH
from lucas_agents.learnable_adversarial_search_agent_v3.player import LearnableAdversarialSearchPlayerV3
from lucas_agents.learnable_agent_v0.threshold_based_player import ThresholdBasedPlayer
from lucas_agents.learnable_agent_v0.random_player_wrapper import setup_ai as setup_random_player
from lucas_agents.advanced_cfr.advanced_cfr_player import AdvancedCFRPlayer


def parse_args():
  parser = argparse.ArgumentParser(description="Train CFR over the 6D abstraction.")
  parser.add_argument("--games", type=int, default=200)
  parser.add_argument("--policy-path", default=DEFAULT_POLICY_PATH)
  parser.add_argument("--save-interval", type=int, default=25)
  parser.add_argument("--max-round", type=int, default=80)
  parser.add_argument("--initial-stack", type=int, default=500)
  parser.add_argument("--small-blind", type=int, default=10)
  parser.add_argument("--self-play-ratio", type=float, default=0.5)
  parser.add_argument("--opponents", default="self,threshold")
  parser.add_argument("--exploration", type=float, default=0.06)
  parser.add_argument("--max-retries", type=int, default=2)
  parser.add_argument("--verbose", action="store_true")
  return parser.parse_args()


def main():
  args = parse_args()
  learner = TrainingLearnableAdversarialSearchPlayerV3(
      policy_path=args.policy_path,
      training_enabled=True,
      use_search=False,
      exploration=args.exploration,
      save_interval=args.save_interval,
  )

  opponent_pool = _parse_opponents(args.opponents)
  wins = {name: 0 for name in opponent_pool}
  matches = {name: 0 for name in opponent_pool}
  skipped = 0
  start_time = time.time()
  previous_state_count = len(learner.cfr.state_visits)

  for game_index in range(1, args.games + 1):
    opponent_name = _choose_opponent(game_index, args.self_play_ratio, opponent_pool)
    learner_seat = "player_a" if game_index % 2 else "player_b"
    result = None
    error_text = None

    for attempt in range(1, args.max_retries + 2):
      try:
        opponent = _build_opponent(opponent_name, args.policy_path)
        _prepare_player_for_match(learner)
        _prepare_player_for_match(opponent)
        result = _play_match(
            learner=learner,
            opponent=opponent,
            learner_seat=learner_seat,
            max_round=args.max_round,
            initial_stack=args.initial_stack,
            small_blind=args.small_blind,
            verbose=args.verbose,
        )
        error_text = None
        break
      except Exception as exc:
        error_text = f"game={game_index} opponent={opponent_name} attempt={attempt} error={type(exc).__name__}: {exc}"
        print()
        print(error_text)
        print(traceback.format_exc())
        _recover_from_failed_match(learner, game_index, attempt)
        if attempt > args.max_retries:
          skipped += 1
          break

    if result is not None:
      learner_stack = next(player["stack"] for player in result["players"] if player["name"] == learner_seat)
      matches[opponent_name] += 1
      if learner_stack > args.initial_stack:
        wins[opponent_name] += 1
    current_state_count = len(learner.cfr.state_visits)
    new_states = current_state_count - previous_state_count
    previous_state_count = current_state_count
    _print_progress(game_index, args.games, start_time, learner, opponent_name, wins, matches, skipped, new_states)
    if game_index % args.save_interval == 0:
      learner.save_policy()
      print()
      print(
          f"checkpoint game={game_index} states={len(learner.cfr.state_visits)}/{learner.TOTAL_ABSTRACT_STATES} "
          f"state_gain={100.0 * len(learner.cfr.state_visits) / learner.TOTAL_ABSTRACT_STATES:5.2f}% "
          f"results={_format_results_summary(wins, matches)} "
          f"skipped={skipped}"
      )

  learner.save_policy()
  print()
  print(f"training_complete games={args.games} skipped={skipped} states={len(learner.cfr.state_visits)}/{learner.TOTAL_ABSTRACT_STATES}")


def _build_opponent(name, policy_path):
  if name == "self":
    return LearnableAdversarialSearchPlayerV3(
        policy_path=policy_path,
        training_enabled=False,
        use_search=False,
    )
  if name == "threshold":
    return ThresholdBasedPlayer()
  if name == "random":
    return setup_random_player()
  if name == "advanced_cfr":
    return AdvancedCFRPlayer(training_enabled=False, exploration=0.0)
  raise ValueError(f"Unsupported opponent {name}")


def _parse_opponents(raw_value):
  supported = {"self", "threshold", "random", "advanced_cfr"}
  opponents = [name.strip() for name in raw_value.split(",") if name.strip()]
  if not opponents:
    raise ValueError("At least one opponent must be configured")
  invalid = [name for name in opponents if name not in supported]
  if invalid:
    raise ValueError(f"Unsupported opponents: {', '.join(invalid)}")
  return opponents


def _choose_opponent(game_index, self_play_ratio, opponent_pool):
  if opponent_pool == ["self", "threshold"]:
    prior_self = int(round((game_index - 1) * self_play_ratio))
    current_self = int(round(game_index * self_play_ratio))
    return "self" if current_self > prior_self else "threshold"
  return opponent_pool[(game_index - 1) % len(opponent_pool)]


def _format_results_summary(wins, matches):
  parts = []
  for name in matches:
    parts.append(f"{name}={wins[name]}/{matches[name]}")
  return " ".join(parts)


def _print_progress(game_index, total_games, start_time, learner, opponent_name, wins, matches, skipped, new_states):
  width = 24
  completed = int(width * game_index / max(total_games, 1))
  bar = "#" * completed + "-" * (width - completed)
  elapsed = time.time() - start_time
  rate = elapsed / max(game_index, 1)
  eta = rate * max(total_games - game_index, 0)
  total_states = learner.TOTAL_ABSTRACT_STATES
  total_gain = 100.0 * len(learner.cfr.state_visits) / total_states
  new_state_gain = 100.0 * new_states / total_states
  message = (
      f"\r[{bar}] {game_index}/{total_games} "
      f"opp={opponent_name:<9} "
      f"new_gain={new_state_gain:5.2f}% "
      f"total_gain={total_gain:5.2f}% "
      f"{_format_results_summary(wins, matches)} "
      f"skipped={skipped} "
      f"eta={eta:5.1f}s"
  )
  print(message, end="", flush=True)


def _play_match(learner, opponent, learner_seat, max_round, initial_stack, small_blind, verbose):
  config = setup_config(
      max_round=max_round,
      initial_stack=initial_stack,
      small_blind_amount=small_blind,
  )
  if learner_seat == "player_a":
    config.register_player(name="player_a", algorithm=learner)
    config.register_player(name="player_b", algorithm=opponent)
  else:
    config.register_player(name="player_a", algorithm=opponent)
    config.register_player(name="player_b", algorithm=learner)
  return start_poker(config, verbose=verbose)


def _prepare_player_for_match(player):
  if hasattr(player, "reset_match_state"):
    player.reset_match_state()


def _recover_from_failed_match(learner, game_index, attempt):
  learner.reset_match_state()
  learner.save_policy()
  print(f"recovered_from_error game={game_index} attempt={attempt} checkpoint_saved=1")


class TrainingLearnableAdversarialSearchPlayerV3(LearnableAdversarialSearchPlayerV3):

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.round_count = 0
    self.round_start_stack = 0

  def receive_round_start_message(self, round_count, hole_card, seats):
    del hole_card
    self.round_count = round_count
    self.round_start_stack = _stack_from_seats(self, seats)
    self.cfr.round_decisions = []

  def receive_round_result_message(self, winners, hand_info, round_state):
    del winners
    del hand_info
    final_stack = _stack_from_seats(self, round_state.get("seats", []))
    chip_delta = final_stack - self.round_start_stack
    small_blind = max(round_state.get("small_blind_amount", 10), 1)
    terminal_utility = float(chip_delta) / float(small_blind)
    self.cfr.finish_round(terminal_utility)
    if self.round_count % self.save_interval == 0:
      self.cfr.save()

  def save_policy(self):
    self.cfr.save()


def _stack_from_seats(player, seats):
  for seat in seats:
    if seat.get("uuid") == getattr(player, "uuid", None):
      return seat.get("stack", 0)
  return 0


if __name__ == "__main__":
  main()
