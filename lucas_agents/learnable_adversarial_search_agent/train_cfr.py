"""Train the shared-abstraction CFR policy.

Training intentionally disables adversarial search. The learner updates only the
CFR table, while opponents are:
- a frozen copy of the same player class ("self")
- ThresholdBasedPlayer from `learnable_agent_v0`
"""

import argparse
import os
import sys
import time

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
  sys.path.insert(0, PROJECT_ROOT)

from pypokerengine.api.game import setup_config, start_poker

from lucas_agents.learnable_adversarial_search_agent.cfr import DEFAULT_POLICY_PATH
from lucas_agents.learnable_adversarial_search_agent.player import LearnableAdversarialSearchPlayer
from lucas_agents.learnable_agent_v0.threshold_based_player import ThresholdBasedPlayer


def parse_args():
  parser = argparse.ArgumentParser(description="Train CFR over the shared abstraction.")
  parser.add_argument("--games", type=int, default=200)
  parser.add_argument("--policy-path", default=DEFAULT_POLICY_PATH)
  parser.add_argument("--save-interval", type=int, default=25)
  parser.add_argument("--max-round", type=int, default=80)
  parser.add_argument("--initial-stack", type=int, default=500)
  parser.add_argument("--small-blind", type=int, default=10)
  parser.add_argument("--self-play-ratio", type=float, default=0.5)
  parser.add_argument("--verbose", action="store_true")
  return parser.parse_args()


def main():
  args = parse_args()
  learner = TrainingLearnableAdversarialSearchPlayer(
      policy_path=args.policy_path,
      training_enabled=True,
      use_search=False,
      save_interval=args.save_interval,
  )

  wins = {"self": 0, "threshold": 0}
  matches = {"self": 0, "threshold": 0}
  start_time = time.time()

  for game_index in range(1, args.games + 1):
    opponent_name = _choose_opponent(game_index, args.self_play_ratio)
    opponent = _build_opponent(opponent_name, args.policy_path)
    learner_seat = "player_a" if game_index % 2 else "player_b"
    result = _play_match(
        learner=learner,
        opponent=opponent,
        learner_seat=learner_seat,
        max_round=args.max_round,
        initial_stack=args.initial_stack,
        small_blind=args.small_blind,
        verbose=args.verbose,
    )
    learner_stack = next(player["stack"] for player in result["players"] if player["name"] == learner_seat)
    matches[opponent_name] += 1
    if learner_stack > args.initial_stack:
      wins[opponent_name] += 1
    _print_progress(game_index, args.games, start_time, learner, opponent_name, wins, matches)
    if game_index % args.save_interval == 0:
      learner.save_policy()
      print()
      print(
          f"checkpoint game={game_index} states={len(learner.cfr.state_visits)}/{learner.TOTAL_ABSTRACT_STATES} "
          f"wins_self={wins['self']}/{max(matches['self'], 1)} "
          f"wins_threshold={wins['threshold']}/{max(matches['threshold'], 1)}"
      )

  learner.save_policy()
  print()


def _build_opponent(name, policy_path):
  if name == "self":
    return LearnableAdversarialSearchPlayer(
        policy_path=policy_path,
        training_enabled=False,
        use_search=False,
    )
  if name == "threshold":
    return ThresholdBasedPlayer()
  raise ValueError(f"Unsupported opponent {name}")


def _choose_opponent(game_index, self_play_ratio):
  prior_self = int(round((game_index - 1) * self_play_ratio))
  current_self = int(round(game_index * self_play_ratio))
  return "self" if current_self > prior_self else "threshold"


def _print_progress(game_index, total_games, start_time, learner, opponent_name, wins, matches):
  width = 24
  completed = int(width * game_index / max(total_games, 1))
  bar = "#" * completed + "-" * (width - completed)
  elapsed = time.time() - start_time
  rate = elapsed / max(game_index, 1)
  eta = rate * max(total_games - game_index, 0)
  coverage = 100.0 * len(learner.cfr.state_visits) / learner.TOTAL_ABSTRACT_STATES
  message = (
      f"\r[{bar}] {game_index}/{total_games} "
      f"opp={opponent_name:<9} "
      f"coverage={coverage:5.1f}% "
      f"self={wins['self']}/{matches['self']} "
      f"threshold={wins['threshold']}/{matches['threshold']} "
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


class TrainingLearnableAdversarialSearchPlayer(LearnableAdversarialSearchPlayer):

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
    # CFR/MCCFR is defined in terms of terminal utility u_i(z), not a clipped or
    # handcrafted reward. See:
    # - Zinkevich et al. 2007, utility function discussion in Definition 1 and
    #   counterfactual regret in Eq. (7):
    #   https://papers.nips.cc/paper/3306-regret-minimization-in-games-with-incomplete-information
    # - Lanctot et al. 2009, sampled counterfactual value in Eq. (6) and the
    #   outcome-sampling regret estimator in Eq. (10):
    #   https://webdocs.cs.ualberta.ca/~bowling/papers/09nips-mccfr.pdf
    #
    # We therefore use the realized chip change from this hand as the terminal
    # utility signal, scaled into small-blind units:
    #
    #   utility = chip_delta / small_blind_amount
    #
    # This keeps the update interpretable and scale-stable across blind sizes,
    # while preserving the sign and relative size of wins/losses. Unlike the
    # old clipped reward, a pot that loses 6 small blinds now really updates as
    # -6.0, not as an arbitrary bounded surrogate.
    #
    # Concrete per-hand example from
    # `lucas_agents/design/single_game_trace.md`, Decision 1:
    # - round start stack for player_a: 500
    # - after posting the big blind and then folding, final stack: 480
    # - chip_delta = 480 - 500 = -20
    # - small blind = 10
    # - terminal_utility = -20 / 10 = -2.0
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
