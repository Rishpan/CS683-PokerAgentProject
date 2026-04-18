"""Simple trainer for `learnable_agent_v0`.

Usage:
  python3 lucas_agents/learnable_agent_v0/train_learnable_cfr.py 150

What it does:
  - trains the CFR player for `games` training games
  - before training, snapshots the current learned policy for fixed self-play
  - in each training game, samples one opponent from a weighted pool
  - default opponent mix favors fixed-policy self-play, then threshold, then random
  - updates:
      - `learnable_cfr_policy.json`
      - `training_coverage.json`
      - `training_plots/latest.png`
      - `training_plots/<run_id>.png`
      - `fixed_policy_snapshot.json`
"""

import argparse
import json
import os
import shutil
import sys

PLOT_CACHE_DIR = os.path.join(os.path.dirname(__file__), ".plot_cache")
os.makedirs(PLOT_CACHE_DIR, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", PLOT_CACHE_DIR)
os.environ.setdefault("XDG_CACHE_HOME", PLOT_CACHE_DIR)

try:
  import matplotlib

  matplotlib.use("Agg")
  import matplotlib.pyplot as plt
  HAS_MATPLOTLIB = True
except ModuleNotFoundError:
  plt = None
  HAS_MATPLOTLIB = False


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
  sys.path.insert(0, PROJECT_ROOT)

from pypokerengine.api.game import setup_config, start_poker

from lucas_agents.learnable_agent_v0.fixed_policy_player import (
    DEFAULT_FIXED_POLICY_PATH,
    FixedPolicyLearnablePlayer,
)
from lucas_agents.learnable_agent_v0.learnable_cfr_player import (
    DEFAULT_COVERAGE_PATH,
    DEFAULT_POLICY_PATH,
    LearnableCFRPlayer,
)
from lucas_agents.learnable_agent_v0.random_player_wrapper import setup_ai as setup_random_ai
from lucas_agents.learnable_agent_v0.threshold_based_player import ThresholdBasedPlayer


DEFAULT_GAMES = 150
DEFAULT_STACK = 500
DEFAULT_SMALL_BLIND = 10
DEFAULT_MAX_ROUNDS = 80
DEFAULT_EXPLORATION = 0.12
DEFAULT_BASELINE_PRIOR_WEIGHT = 0.30
DEFAULT_BASELINE_ASSIST = 0.08
DEFAULT_SAVE_INTERVAL = 25
DEFAULT_DISCOUNT_INTERVAL = 500
DEFAULT_DISCOUNT_FACTOR = 0.995
DEFAULT_MIN_USE_STRATEGY_VISITS = 8
DEFAULT_RANDOM_SEED = 7
OPPONENT_WEIGHTS = {
    "fixed_self": 0.70,
    "threshold": 0.25,
    "random": 0.05,
}
PLOTS_DIR = os.path.join(os.path.dirname(__file__), "training_plots")


def parse_args():
  parser = argparse.ArgumentParser(
      description="Train the learnable_agent_v0 CFR player."
  )
  parser.add_argument("games", nargs="?", type=int, default=DEFAULT_GAMES)
  return parser.parse_args()


def snapshot_policy(source_path=DEFAULT_POLICY_PATH, snapshot_path=DEFAULT_FIXED_POLICY_PATH):
  os.makedirs(os.path.dirname(snapshot_path), exist_ok=True)
  if os.path.exists(source_path):
    shutil.copyfile(source_path, snapshot_path)
    return snapshot_path
  payload = {"strategy_sum": {}, "meta": {"snapshot_created_without_source": True}}
  with open(snapshot_path, "w", encoding="utf-8") as output:
    json.dump(payload, output, indent=2, sort_keys=True)
  return snapshot_path


def choose_opponent_name(learner):
  names = list(OPPONENT_WEIGHTS.keys())
  weights = [OPPONENT_WEIGHTS[name] for name in names]
  return learner.random.choices(names, weights=weights, k=1)[0]


def build_opponent(name):
  if name == "fixed_self":
    return FixedPolicyLearnablePlayer(policy_path=DEFAULT_FIXED_POLICY_PATH)
  if name == "threshold":
    return ThresholdBasedPlayer()
  if name == "random":
    return setup_random_ai()
  raise ValueError(f"Unsupported opponent: {name}")


def run_match(args, learner, opponent_name, learner_seat, match_index):
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
  return {
      "games": [],
      "coverage_pct": [],
      "unique_states": [],
      "overall_win_rate": [],
      "opponents": {
          name: {"games": [], "win_rate": [], "wins": 0, "matches": 0}
          for name in OPPONENT_WEIGHTS
      },
      "wins": 0,
      "matches": 0,
  }


def _update_plot_history(history, game_index, game_results, learner):
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
  if not HAS_MATPLOTLIB:
    print("plotting_skipped=matplotlib_not_installed")
    return

  os.makedirs(PLOTS_DIR, exist_ok=True)
  figure, axes = plt.subplots(2, 1, figsize=(9, 8), tight_layout=True)

  axes[0].plot(
      history["games"],
      history["coverage_pct"],
      linewidth=2,
      label="coverage %",
  )
  axes[0].set_title("Abstract State Coverage by Training Game")
  axes[0].set_xlabel("Training game")
  axes[0].set_ylabel("Coverage %")
  axes[0].grid(alpha=0.3)
  axes[0].legend()

  axes[1].plot(
      history["games"],
      [rate * 100.0 for rate in history["overall_win_rate"]],
      linewidth=2,
      label="overall",
  )
  for opponent_name, opponent_history in history["opponents"].items():
    if not opponent_history["games"]:
      continue
    axes[1].plot(
        opponent_history["games"],
        [rate * 100.0 for rate in opponent_history["win_rate"]],
        linewidth=2,
        label=opponent_name,
    )
  axes[1].set_title("Cumulative Win Rate by Training Game")
  axes[1].set_xlabel("Training game")
  axes[1].set_ylabel("Win rate %")
  axes[1].set_ylim(0, 100)
  axes[1].grid(alpha=0.3)
  axes[1].legend()

  run_path = os.path.join(PLOTS_DIR, f"{run_id}.png")
  latest_path = os.path.join(PLOTS_DIR, "latest.png")
  figure.savefig(run_path, dpi=160)
  figure.savefig(latest_path, dpi=160)
  plt.close(figure)
  print(f"saved_plot={latest_path}")
  print(f"saved_plot_run={run_path}")


def main():
  args = parse_args()
  args.verbose = 0
  snapshot_path = snapshot_policy()
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
          "opponent_weights": OPPONENT_WEIGHTS,
          "seat_cycle": ["player_a", "player_b"],
          "policy_path": DEFAULT_POLICY_PATH,
          "fixed_policy_snapshot": snapshot_path,
      }
  )

  total_rounds = 0
  match_index = 0
  plot_history = _init_plot_history()
  for game_index in range(1, args.games + 1):
    opponent_name = choose_opponent_name(learner)
    game_results = []
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
          "fixed_policy_snapshot": snapshot_path,
      }
  )
  print(f"saved_policy={DEFAULT_POLICY_PATH}")
  print(f"saved_coverage={DEFAULT_COVERAGE_PATH}")
  print(f"saved_fixed_policy_snapshot={snapshot_path}")
  if summary:
    print(
        f"coverage_delta={summary['new_state_count']} "
        f"unique_before={summary['unique_states_before']} "
        f"unique_after={summary['unique_states_after']}"
    )


if __name__ == "__main__":
  main()
