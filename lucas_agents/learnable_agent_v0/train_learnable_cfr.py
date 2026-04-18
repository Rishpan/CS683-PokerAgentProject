"""Simple trainer for `learnable_agent_v0`.

Usage:
  python3 lucas_agents/learnable_agent_v0/train_learnable_cfr.py 150

What it does:
  - trains the CFR player for `games` training games
  - in each training game, plays against every opponent in `OPPONENTS`
  - for each opponent, plays once as `player_a` and once as `player_b`
  - updates:
      - `learnable_cfr_policy.json`
      - `training_coverage.json`
      - `training_plots/latest.png`
      - `training_plots/<run_id>.png`

What to expect:
  - the coverage plot should usually increase over time, then flatten as learning
    starts revisiting existing abstract states more often
  - the win-rate plot can be noisy early, especially for small runs
  - a single-game run still creates a plot, but it only contains one point

How to add more players:
  1. Add the player name to `OPPONENTS`
  2. Extend `build_opponent(...)` with that name and class
  3. Re-run training; the per-opponent win-rate line is added automatically
"""

import argparse
import os
import sys

PLOT_CACHE_DIR = os.path.join(os.path.dirname(__file__), ".plot_cache")
os.makedirs(PLOT_CACHE_DIR, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", PLOT_CACHE_DIR)
os.environ.setdefault("XDG_CACHE_HOME", PLOT_CACHE_DIR)

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
  sys.path.insert(0, PROJECT_ROOT)

from pypokerengine.api.game import setup_config, start_poker

from lucas_agents.learnable_agent_v0.learnable_cfr_player import (
    DEFAULT_COVERAGE_PATH,
    DEFAULT_POLICY_PATH,
    LearnableCFRPlayer,
)
from lucas_agents.learnable_agent_v0.threshold_based_player import ThresholdBasedPlayer
from lucas_agents.simplified_advanced_cfr.simplified_advanced_cfr_player import (
    SimplifiedAdvancedCFRPlayer,
)


DEFAULT_GAMES = 150
DEFAULT_STACK = 500
DEFAULT_SMALL_BLIND = 10
DEFAULT_MAX_ROUNDS = 80
DEFAULT_EXPLORATION = 0.12
DEFAULT_BASELINE_PRIOR_WEIGHT = 0.30
DEFAULT_BASELINE_ASSIST = 0.08
DEFAULT_SAVE_INTERVAL = 100
DEFAULT_DISCOUNT_INTERVAL = 500
DEFAULT_DISCOUNT_FACTOR = 0.995
DEFAULT_MIN_USE_STRATEGY_VISITS = 8
DEFAULT_RANDOM_SEED = 7
OPPONENTS = ("threshold", "simplified_advanced_cfr")
PLOTS_DIR = os.path.join(os.path.dirname(__file__), "training_plots")


def parse_args():
  """Parse the single training argument: number of training games."""
  parser = argparse.ArgumentParser(
      description="Train the learnable_agent_v0 CFR player."
  )
  parser.add_argument("games", nargs="?", type=int, default=DEFAULT_GAMES)
  return parser.parse_args()


def build_opponent(name):
  """Instantiate one supported training opponent."""
  if name == "threshold":
    return ThresholdBasedPlayer()
  if name == "simplified_advanced_cfr":
    return SimplifiedAdvancedCFRPlayer(use_learned_action=True)
  raise ValueError(f"Unsupported opponent: {name}")


def run_match(args, learner, opponent_name, learner_seat, match_index):
  """Run one learner-vs-opponent match for a fixed seat assignment."""
  learner.set_training_context(opponent_name, learner_seat, match_index)
  opponent = build_opponent(opponent_name)
  config = setup_config(
      max_round=DEFAULT_MAX_ROUNDS,
      initial_stack=DEFAULT_STACK,
      small_blind_amount=DEFAULT_SMALL_BLIND,
  )

  if learner_seat == "player_a":
    config.register_player(name="player_a", algorithm=learner)
    config.register_player(name="player_b", algorithm=opponent)
  else:
    config.register_player(name="player_a", algorithm=opponent)
    config.register_player(name="player_b", algorithm=learner)

  result = start_poker(config, verbose=args.verbose)
  learner.finish_game(result["players"], DEFAULT_SMALL_BLIND)
  learner_stack = next(
      player["stack"]
      for player in result["players"]
      if player["name"] == learner_seat
  )
  if learner._active_run:
    learner._active_run["matches"] += 1
  opponent_stack = next(
      player["stack"]
      for player in result["players"]
      if player["name"] != learner_seat
  )
  return learner.round_count, learner_stack, opponent_stack


def _init_plot_history():
  """Create the in-memory history used for coverage and win-rate plots."""
  return {
      "games": [],
      "coverage_pct": [],
      "unique_states": [],
      "overall_win_rate": [],
      "opponents": {
          name: {"games": [], "win_rate": [], "wins": 0, "matches": 0}
          for name in OPPONENTS
      },
      "wins": 0,
      "matches": 0,
  }


def _update_plot_history(history, game_index, game_results, learner):
  """Append one training game's results to the plotting history."""
  for opponent_name, learner_stack, opponent_stack in game_results:
    history["matches"] += 1
    opponent_history = history["opponents"][opponent_name]
    opponent_history["matches"] += 1
    if learner_stack > opponent_stack:
      history["wins"] += 1
      opponent_history["wins"] += 1
  history["games"].append(game_index)
  history["coverage_pct"].append(
      100.0 * len(learner.state_visits) / learner.TOTAL_ABSTRACT_STATES
      if hasattr(learner, "TOTAL_ABSTRACT_STATES")
      else 100.0 * len(learner.state_visits) / 23040.0
  )
  history["unique_states"].append(len(learner.state_visits))
  history["overall_win_rate"].append(history["wins"] / max(history["matches"], 1))

  seen = set()
  for opponent_name, _, _ in game_results:
    if opponent_name in seen:
      continue
    seen.add(opponent_name)
    opponent_history = history["opponents"][opponent_name]
    opponent_history["games"].append(game_index)
    opponent_history["win_rate"].append(
        opponent_history["wins"] / max(opponent_history["matches"], 1)
    )


def _save_plots(run_id, history):
  """Save the latest coverage and win-rate charts for this training run."""
  os.makedirs(PLOTS_DIR, exist_ok=True)
  figure, axes = plt.subplots(2, 1, figsize=(9, 8), tight_layout=True)
  game_ticks = history["games"] or [1]

  axes[0].plot(
      history["games"],
      history["coverage_pct"],
      linewidth=2,
      marker="o",
      markersize=5,
      label="coverage %",
  )
  axes[0].set_title("Abstract State Coverage by Training Game")
  axes[0].set_xlabel("Training game")
  axes[0].set_ylabel("Coverage %")
  axes[0].set_xticks(game_ticks)
  axes[0].grid(alpha=0.3)
  axes[0].legend()

  axes[1].plot(
      history["games"],
      [rate * 100.0 for rate in history["overall_win_rate"]],
      linewidth=2,
      marker="o",
      markersize=5,
      label="overall",
  )
  for opponent_name, opponent_history in history["opponents"].items():
    axes[1].plot(
        opponent_history["games"],
        [rate * 100.0 for rate in opponent_history["win_rate"]],
        linewidth=2,
        marker="o",
        markersize=5,
        label=opponent_name,
    )
  axes[1].set_title("Cumulative Win Rate by Training Game")
  axes[1].set_xlabel("Training game")
  axes[1].set_ylabel("Win rate %")
  axes[1].set_ylim(0, 100)
  axes[1].set_xticks(game_ticks)
  axes[1].grid(alpha=0.3)
  axes[1].legend()

  run_path = os.path.join(PLOTS_DIR, f"{run_id}.png")
  latest_path = os.path.join(PLOTS_DIR, "latest.png")
  figure.savefig(run_path, dpi=160)
  figure.savefig(latest_path, dpi=160)
  plt.close(figure)


def main():
  args = parse_args()
  args.verbose = 0
  learner = LearnableCFRPlayer(
      policy_path=DEFAULT_POLICY_PATH,
      coverage_path=DEFAULT_COVERAGE_PATH,
      exploration=DEFAULT_EXPLORATION,
      training_enabled=True,
      save_interval=DEFAULT_SAVE_INTERVAL,
      baseline_prior_weight=DEFAULT_BASELINE_PRIOR_WEIGHT,
      baseline_assist=DEFAULT_BASELINE_ASSIST,
      min_use_strategy_visits=DEFAULT_MIN_USE_STRATEGY_VISITS,
      discount_interval=DEFAULT_DISCOUNT_INTERVAL,
      discount_factor=DEFAULT_DISCOUNT_FACTOR,
      random_seed=DEFAULT_RANDOM_SEED,
  )

  run_id = learner.begin_training_run(
      {
          "games": args.games,
          "stack": DEFAULT_STACK,
          "small_blind": DEFAULT_SMALL_BLIND,
          "max_rounds_per_game": DEFAULT_MAX_ROUNDS,
          "exploration": DEFAULT_EXPLORATION,
          "baseline_prior_weight": DEFAULT_BASELINE_PRIOR_WEIGHT,
          "baseline_assist": DEFAULT_BASELINE_ASSIST,
          "min_use_strategy_visits": DEFAULT_MIN_USE_STRATEGY_VISITS,
          "opponents": list(OPPONENTS),
          "seat_cycle": ["player_a", "player_b"],
          "policy_path": DEFAULT_POLICY_PATH,
      }
  )

  total_rounds = 0
  match_index = 0
  plot_history = _init_plot_history()
  for game_index in range(1, args.games + 1):
    game_results = []
    for opponent_name in OPPONENTS:
      for learner_seat in ("player_a", "player_b"):
        match_index += 1
        rounds_played, learner_stack, opponent_stack = run_match(
            args, learner, opponent_name, learner_seat, match_index
        )
        total_rounds += rounds_played
        game_results.append((opponent_name, learner_stack, opponent_stack))
        print(
            f"run={run_id} game={game_index}/{args.games} match={match_index} "
            f"opponent={opponent_name} learner_seat={learner_seat} "
            f"rounds={rounds_played} total_rounds={total_rounds} learner_stack={learner_stack} "
            f"unique_states={len(learner.state_visits)}"
        )
    _update_plot_history(plot_history, game_index, game_results, learner)
    _save_plots(run_id, plot_history)

  learner.save_policy()
  summary = learner.finish_training_run(
      {
          "matches_played": match_index,
          "total_rounds": total_rounds,
          "final_unique_states": len(learner.state_visits),
          "policy_path": DEFAULT_POLICY_PATH,
          "coverage_path": DEFAULT_COVERAGE_PATH,
      }
  )
  print(f"saved_policy={DEFAULT_POLICY_PATH}")
  print(f"saved_coverage={DEFAULT_COVERAGE_PATH}")
  if summary:
    print(
        f"coverage_delta={summary['new_state_count']} "
        f"unique_before={summary['unique_states_before']} "
        f"unique_after={summary['unique_states_after']}"
    )


if __name__ == "__main__":
  main()
