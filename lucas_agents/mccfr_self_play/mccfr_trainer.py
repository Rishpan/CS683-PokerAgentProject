"""Offline self-play trainer for the Lucas external-sampling MCCFR agent.

The trainer is abstraction-agnostic. It only depends on the abstraction
interface defined in ``mccfr_abstraction_loader.py``. Policies are tied to the
abstraction metadata saved inside the policy file, so continuing training uses
the same abstraction by default.
"""

import argparse
import importlib.util
import os
import random
import sys
import time
from functools import lru_cache
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
  sys.path.insert(0, str(CURRENT_DIR))


def _find_project_root():
  for candidate in CURRENT_DIR.parents:
    if (candidate / "pypokerengine").exists():
      return candidate
  return CURRENT_DIR.parent


PROJECT_ROOT = str(_find_project_root())
if PROJECT_ROOT not in sys.path:
  sys.path.insert(0, PROJECT_ROOT)

from pypokerengine.api.emulator import Emulator
from pypokerengine.api.game import setup_config, start_poker
from pypokerengine.engine.action_checker import ActionChecker
from pypokerengine.engine.data_encoder import DataEncoder
from pypokerengine.engine.poker_constants import PokerConstants as Const
from pypokerengine.engine.round_manager import RoundManager
from pypokerengine.players import BasePokerPlayer

from mccfr_abstraction_loader import (
    abstraction_identity,
    abstraction_is_compatible,
    load_abstraction,
    observe_opponent_action_stats,
    resolve_policy_abstraction_ref,
)
from mccfr_config import (
    DEFAULT_CHECKPOINT_INTERVAL,
    DEFAULT_INITIAL_STACK,
    DEFAULT_LOG_INTERVAL,
    DEFAULT_MAX_ROUNDS,
    DEFAULT_POLICY_PATH,
    DEFAULT_POSTFLOP_SIMULATIONS,
    DEFAULT_SMALL_BLIND,
    DEFAULT_ABSTRACTION_REF,

)
from mccfr_player import MCCFRPlayer
from mccfr_tables import ACTIONS, StrategyTable

SELF_PLAY_OPPONENT = "self"
RAISE_PLAYER_OPPONENT = "raise_player"


class ExternalSamplingMCCFRTrainer:
  """Self-play MCCFR trainer over single-round sampled poker episodes.

  The algorithm does not care which abstraction is used. It only requires the
  abstraction module to provide a stable mapping from game state to infoset key
  plus lightweight metadata helpers.
  """
  def __init__(
      self,
      iterations,
      initial_stack,
      small_blind,
      max_rounds=1,
      policy_path=None,
      checkpoint_interval=500,
      log_interval=DEFAULT_LOG_INTERVAL,
      random_seed=None,
      postflop_simulations=64,
      reset_policy=False,
      abstraction=None,
      opponent_pool=None,
  ):
    self.iterations = iterations
    self.initial_stack = initial_stack
    self.small_blind = small_blind
    self.max_rounds = max_rounds
    self.policy_path = policy_path or DEFAULT_POLICY_PATH
    self.checkpoint_interval = max(1, checkpoint_interval)
    self.log_interval = max(1, log_interval)
    self.postflop_simulations = postflop_simulations
    self.random = random.Random(random_seed)
    self.opponent_pool = self._normalize_opponent_pool(opponent_pool)
    self.training_mode = self._training_mode_label()
    self.tables, self.metadata = StrategyTable.load(self.policy_path)
    self.abstraction_ref = resolve_policy_abstraction_ref(
        self.metadata,
        explicit_abstraction_ref=abstraction,
    )
    self.abstraction = load_abstraction(self.abstraction_ref)

    if abstraction and self.metadata and not abstraction_is_compatible(
        self.metadata,
        self.abstraction,
        self.abstraction_ref,
    ) and not reset_policy:
      raise ValueError(
          "Existing policy uses a different abstraction. Pass --reset-policy to "
          "start a fresh policy with the new abstraction or choose a different "
          "policy path."
      )

    if reset_policy or not abstraction_is_compatible(
        self.metadata,
        self.abstraction,
        self.abstraction_ref,
    ):
      self.tables = StrategyTable()
      self.metadata = {}

    self.abstraction_metadata = abstraction_identity(self.abstraction, self.abstraction_ref)
    self.metadata.update(
        {
            "algorithm": "external_sampling_mccfr",
            **self.abstraction_metadata,
            "abstraction_state_upper_bound": self.abstraction.abstraction_state_upper_bound(),
            "postflop_simulations": postflop_simulations,
            "initial_stack": initial_stack,
            "small_blind": small_blind,
            "max_rounds": max_rounds,
            "training_mode": self.training_mode,
            "training_opponents": [spec["label"] for spec in self.opponent_pool],
        }
    )
    self.emulator = Emulator()
    self.emulator.set_game_rule(
        player_num=2,
        max_round=max_rounds,
        small_blind_amount=small_blind,
        ante_amount=0,
    )
    self.players_info = {
        "p0": {"name": "mccfr_p0", "stack": initial_stack},
        "p1": {"name": "mccfr_p1", "stack": initial_stack},
    }
    self.episode_count = 0
    self.trained_round_count = 0
    self.start_time = None

  def train(self, eval_every=0, eval_games=0, verbose=False):
    self.start_time = time.time()
    for iteration in range(1, self.iterations + 1):
      game_state = self._new_episode_game_state(iteration)
      for round_index in range(self.max_rounds):
        round_state, _ = self.emulator.start_new_round(game_state)
        if self._is_round_finished(round_state) or self._active_stack_count(round_state) <= 1:
          break

        self.trained_round_count += 1
        for traverser in self.players_info.keys():
          start_stack = self._stack_by_uuid(round_state, traverser)
          opponent_spec = self._sample_opponent_spec()
          self._traverse(round_state, traverser, start_stack, opponent_spec)

        if round_index == self.max_rounds - 1:
          break
        game_state = self._sample_round_to_finish(round_state, self._sample_opponent_spec())
        if self._active_stack_count(game_state) <= 1:
          break
      self.episode_count += 1

      if verbose and self._should_log(iteration):
        self._log_progress(iteration)
      if iteration % self.checkpoint_interval == 0:
        self.save_policy()
        if verbose:
          print(f"checkpoint_saved iteration={iteration} path={self.policy_path}")
      if eval_every and eval_games and iteration % eval_every == 0:
        self.save_policy()
        self._evaluate(eval_games)

    self.save_policy()

  def save_policy(self):
    self.metadata["episodes"] = self.episode_count
    self.metadata["trained_rounds"] = self.trained_round_count
    abstraction_cap = self.abstraction.abstraction_state_upper_bound()
    visited_state_count = self._visited_state_count()
    self.metadata["visited_states"] = visited_state_count
    self.metadata["visited_info_sets"] = visited_state_count
    self.metadata["visited_state_percentage"] = round(
        100.0 * visited_state_count / max(abstraction_cap, 1), 4
    )
    self.tables.save(self.policy_path, metadata=self.metadata)

  def _new_round_root(self, iteration):
    game_state = self._new_episode_game_state(iteration)
    round_state, _ = self.emulator.start_new_round(game_state)
    return round_state

  def _new_episode_game_state(self, iteration):
    game_state = self.emulator.generate_initial_game_state(self.players_info)
    desired_dealer = iteration % len(self.players_info)
    game_state["table"].dealer_btn = (desired_dealer - 1) % len(self.players_info)
    return game_state



  def _traverse(self, game_state, traverser_uuid, start_stack, opponent_spec):
    if self._is_terminal(game_state):
      final_stack = self._stack_by_uuid(game_state, traverser_uuid)
      scale = max(self.small_blind * 2, 1)
      return float(final_stack - start_stack) / scale

    round_state = DataEncoder.encode_round_state(game_state)
    current_uuid = self._current_player_uuid(game_state)
    hole_card = self._hole_cards(game_state, current_uuid)
    valid_actions = ActionChecker.legal_actions(
        game_state["table"].seats.players,
        game_state["next_player"],
        game_state["small_blind_amount"],
        game_state["street"],
    )
    legal_actions = {entry["action"] for entry in valid_actions}
    opponent_stats = observe_opponent_action_stats(
        self.abstraction,
        round_state["action_histories"],
        current_uuid,
        historical_action_stats=None,
    )
    info_key, _ = self.abstraction.build_info_key(
        hole_card=hole_card,
        round_state=round_state,
        player_uuid=current_uuid,
        opponent_action_stats=opponent_stats,
        postflop_simulations=self.postflop_simulations,
    )
    strategy = self.tables.legal_strategy(info_key, legal_actions)

    if current_uuid == traverser_uuid:
      if opponent_spec["kind"] != SELF_PLAY_OPPONENT:
        # Against fixed scripted opponents there is no second learner copy to
        # accumulate the average strategy on opponent nodes, so record the
        # learner's realized strategy directly on its own infosets.
        self.tables.accumulate_average(info_key, strategy, weight=1.0)
      action_values = {}
      node_value = 0.0
      for action in legal_actions:
        next_state = self._apply_action(game_state, action)
        action_values[action] = self._traverse(
            next_state,
            traverser_uuid,
            start_stack,
            opponent_spec,
        )
        node_value += strategy[action] * action_values[action]
      self.tables.apply_regret_update(info_key, action_values, node_value, legal_actions)
      return node_value

    if opponent_spec["kind"] == SELF_PLAY_OPPONENT:
      sampled_action = self._sample_action(strategy, legal_actions)
      self.tables.accumulate_average(info_key, strategy, weight=1.0)
    else:
      sampled_action = self._raise_player_action(valid_actions)
    next_state = self._apply_action(game_state, sampled_action)
    return self._traverse(next_state, traverser_uuid, start_stack, opponent_spec)

  def _apply_action(self, game_state, action):
    next_state, _ = RoundManager.apply_action(game_state, action)
    return next_state

  def _sample_round_to_finish(self, game_state, opponent_spec):
    sampled_state = game_state
    while not self._is_round_finished(sampled_state):
      if self._active_stack_count(sampled_state) <= 1:
        break
      sampled_action = self._sample_transition_action(sampled_state, opponent_spec)
      sampled_state = self._apply_action(sampled_state, sampled_action)
    return sampled_state

  def _sample_transition_action(self, game_state, opponent_spec):
    valid_actions = ActionChecker.legal_actions(
        game_state["table"].seats.players,
        game_state["next_player"],
        game_state["small_blind_amount"],
        game_state["street"],
    )
    current_uuid = self._current_player_uuid(game_state)
    if opponent_spec["kind"] != SELF_PLAY_OPPONENT and current_uuid == "p1":
      return self._raise_player_action(valid_actions)

    legal_actions = {entry["action"] for entry in valid_actions}
    round_state = DataEncoder.encode_round_state(game_state)
    hole_card = self._hole_cards(game_state, current_uuid)
    opponent_stats = observe_opponent_action_stats(
        self.abstraction,
        round_state["action_histories"],
        current_uuid,
        historical_action_stats=None,
    )
    info_key, _ = self.abstraction.build_info_key(
        hole_card=hole_card,
        round_state=round_state,
        player_uuid=current_uuid,
        opponent_action_stats=opponent_stats,
        postflop_simulations=self.postflop_simulations,
    )
    strategy = self.tables.legal_strategy(info_key, legal_actions)
    return self._sample_action(strategy, legal_actions)

  def _current_player_uuid(self, game_state):
    next_player = game_state["next_player"]
    return game_state["table"].seats.players[next_player].uuid

  def _hole_cards(self, game_state, player_uuid):
    player = next(player for player in game_state["table"].seats.players if player.uuid == player_uuid)
    return [str(card) for card in player.hole_card]

  def _stack_by_uuid(self, game_state, player_uuid):
    player = next(player for player in game_state["table"].seats.players if player.uuid == player_uuid)
    return player.stack

  def _is_terminal(self, game_state):
    return self._is_round_finished(game_state)

  def _is_round_finished(self, game_state):
    return game_state["street"] == Const.Street.FINISHED

  def _active_stack_count(self, game_state):
    return sum(1 for player in game_state["table"].seats.players if player.stack > 0)

  def _sample_action(self, strategy, legal_actions):
    draw = self.random.random()
    cumulative = 0.0
    fallback = "call" if "call" in legal_actions else "fold"
    for action in ACTIONS:
      probability = strategy.get(action, 0.0)
      if probability <= 0:
        continue
      cumulative += probability
      if draw <= cumulative:
        return action
    return fallback

  def _raise_player_action(self, valid_actions):
    for entry in valid_actions:
      if entry["action"] == "raise":
        return "raise"
    if any(entry["action"] == "call" for entry in valid_actions):
      return "call"
    return "fold"

  def _evaluate(self, games):
    random_result = play_match(self.policy_path, os.path.join(PROJECT_ROOT, "randomplayer.py"), games)
    raise_result = play_match(self.policy_path, os.path.join(PROJECT_ROOT, "raise_player.py"), games)
    print(
        "evaluation "
        f"vs_random={random_result['avg_delta']:+.2f} "
        f"vs_raise={raise_result['avg_delta']:+.2f}"
    )

  def _should_log(self, iteration):
    return iteration == 1 or iteration == self.iterations or iteration % self.log_interval == 0

  def _log_progress(self, iteration):
    elapsed = max(time.time() - self.start_time, 1e-9)
    iterations_per_sec = iteration / elapsed
    remaining_iterations = max(self.iterations - iteration, 0)
    eta_seconds = remaining_iterations / max(iterations_per_sec, 1e-9)
    visited_states = self._visited_state_count()
    abstraction_cap = self.abstraction.abstraction_state_upper_bound()
    density = 100.0 * visited_states / max(abstraction_cap, 1)
    progress = 100.0 * iteration / max(self.iterations, 1)
    print(
        "progress "
        f"iter={iteration}/{self.iterations} "
        f"({progress:.1f}%) "
        f"visited_states={visited_states}/{abstraction_cap} "
        f"({density:.1f}%) "
        f"elapsed={elapsed:.1f}s "
        f"eta={eta_seconds:.1f}s "
        f"speed={iterations_per_sec:.2f} it/s"
    )

  def _visited_state_count(self):
    return len(set(self.tables.regret_sum) | set(self.tables.strategy_sum))

  def _normalize_opponent_pool(self, opponent_pool):
    if not opponent_pool:
      return [{"kind": SELF_PLAY_OPPONENT, "label": SELF_PLAY_OPPONENT}]

    specs = []
    for entry in opponent_pool:
      candidate = str(entry).strip()
      if not candidate:
        continue
      normalized = candidate.lower()
      if normalized in ("self", "self-play", "self_play"):
        specs.append({"kind": SELF_PLAY_OPPONENT, "label": SELF_PLAY_OPPONENT})
        continue
      if normalized in ("raise", "raise_player", "raise-player", "raise_player.py"):
        specs.append({"kind": RAISE_PLAYER_OPPONENT, "label": RAISE_PLAYER_OPPONENT})
        continue
      candidate_path = os.path.basename(candidate).lower()
      if candidate_path == "raise_player.py":
        specs.append({"kind": RAISE_PLAYER_OPPONENT, "label": RAISE_PLAYER_OPPONENT})
        continue
      raise ValueError(
          "Unsupported training opponent. Use 'self', 'raise_player', or a comma-separated mix."
      )

    if not specs:
      raise ValueError("Opponent pool is empty. Use 'self', 'raise_player', or both.")
    return specs

  def _training_mode_label(self):
    kinds = {spec["kind"] for spec in self.opponent_pool}
    if kinds == {SELF_PLAY_OPPONENT}:
      return "self_play"
    if SELF_PLAY_OPPONENT in kinds:
      return "mixed"
    return RAISE_PLAYER_OPPONENT

  def _sample_opponent_spec(self):
    return self.random.choice(self.opponent_pool)


@lru_cache(maxsize=None)
def _load_agent_setup(script_path):
  module_name = f"mccfr_eval_{abs(hash(script_path))}"
  spec = importlib.util.spec_from_file_location(module_name, script_path)
  if spec is None or spec.loader is None:
    raise ImportError(f"Could not import {script_path}")
  module = importlib.util.module_from_spec(spec)
  spec.loader.exec_module(module)
  if not hasattr(module, "setup_ai"):
    raise AttributeError(f"{script_path} is missing setup_ai()")
  return module.setup_ai


def load_agent_from_script(script_path):
  setup_ai = _load_agent_setup(script_path)
  agent = setup_ai()
  if not isinstance(agent, BasePokerPlayer):
    raise TypeError(f"{script_path} setup_ai() did not return a BasePokerPlayer")
  return agent


def play_match(policy_path, opponent_script, games):
  deltas = []
  for _ in range(games):
    learner = MCCFRPlayer(policy_path=policy_path)
    opponent = load_agent_from_script(opponent_script)
    config = setup_config(max_round=100, initial_stack=1000, small_blind_amount=10)
    config.register_player(name="mccfr", algorithm=learner)
    config.register_player(name="opponent", algorithm=opponent)
    result = start_poker(config, verbose=0)
    stacks = {seat["name"]: seat["stack"] for seat in result["players"]}
    deltas.append(stacks["mccfr"] - 1000)
  return {"avg_delta": sum(deltas) / max(len(deltas), 1)}


def train_self_play_policy(
    iterations,
    policy_path=DEFAULT_POLICY_PATH,
    initial_stack=DEFAULT_INITIAL_STACK,
    small_blind=DEFAULT_SMALL_BLIND,
    max_rounds=DEFAULT_MAX_ROUNDS,
    checkpoint_interval=DEFAULT_CHECKPOINT_INTERVAL,
    log_interval=DEFAULT_LOG_INTERVAL,
    random_seed=None,
    postflop_simulations=DEFAULT_POSTFLOP_SIMULATIONS,
    verbose=False,
    reset_policy=False,
    abstraction=None,
    opponent_pool=None,
):
  """Train a policy and save it to disk.

  By default training is self-play. Pass ``opponent_pool`` to train against
  ``"raise_player"`` or a mix of ``"self"`` and ``"raise_player"``.
  """
  trainer = ExternalSamplingMCCFRTrainer(
      iterations=iterations,
      initial_stack=initial_stack,
      small_blind=small_blind,
      max_rounds=max_rounds,
      policy_path=policy_path,
      checkpoint_interval=checkpoint_interval,
      log_interval=log_interval,
      random_seed=random_seed,
      postflop_simulations=postflop_simulations,
      reset_policy=reset_policy,
      abstraction=abstraction,
      opponent_pool=opponent_pool,
  )
  trainer.train(verbose=verbose)
  return trainer


def parse_args():
  parser = argparse.ArgumentParser(
      description="Train an external-sampling MCCFR poker agent by offline self-play.",
      epilog=(
          "Policies are tied to abstraction metadata. Use --abstraction to start a new "
          "policy with another abstraction module, and pair that with --reset-policy or "
          "a fresh --policy-path."
      ),
  )
  parser.add_argument("--iterations", type=int, default=2000, help="Number of self-play rounds.")
  parser.add_argument("--stack", type=int, default=DEFAULT_INITIAL_STACK, help="Initial stack for each player.")
  parser.add_argument("--small-blind", type=int, default=DEFAULT_SMALL_BLIND, help="Small blind amount.")
  parser.add_argument("--max-rounds", type=int, default=DEFAULT_MAX_ROUNDS, help="Rounds per training episode.")
  parser.add_argument("--checkpoint-interval", type=int, default=DEFAULT_CHECKPOINT_INTERVAL)
  parser.add_argument(
      "--log-interval",
      type=int,
      default=DEFAULT_LOG_INTERVAL,
      help="How often to print progress in verbose mode.",
  )
  parser.add_argument("--policy-path", default=DEFAULT_POLICY_PATH)
  parser.add_argument(
      "--abstraction",
      default=None,
      help=(
          "Import path or .py file for the abstraction module. If omitted, the "
          "trainer reuses the abstraction recorded in the policy metadata or the "
          f"default config preset ({DEFAULT_ABSTRACTION_REF}) for a new policy."
      ),
  )
  parser.add_argument(
      "--opponents",
      default=SELF_PLAY_OPPONENT,
      help=(
          "Comma-separated training opponent pool. Supported values are "
          "'self' and 'raise_player'. Example: self,raise_player"
      ),
  )
  parser.add_argument("--seed", type=int, default=None)
  parser.add_argument("--postflop-simulations", type=int, default=DEFAULT_POSTFLOP_SIMULATIONS)
  parser.add_argument("--eval-every", type=int, default=0)
  parser.add_argument("--eval-games", type=int, default=0)
  parser.add_argument(
      "--reset-policy",
      action="store_true",
      help="Ignore any existing policy tables and start from a fresh empty policy.",
  )
  parser.add_argument(
      "--quiet",
      action="store_true",
      help="Disable progress logging. Verbose mode is on by default.",
  )
  return parser.parse_args()


def main():
  args = parse_args()
  trainer = ExternalSamplingMCCFRTrainer(
      iterations=args.iterations,
      initial_stack=args.stack,
      small_blind=args.small_blind,
      max_rounds=args.max_rounds,
      policy_path=args.policy_path,
      checkpoint_interval=args.checkpoint_interval,
      log_interval=args.log_interval,
      random_seed=args.seed,
      postflop_simulations=args.postflop_simulations,
      reset_policy=args.reset_policy,
      abstraction=args.abstraction,
      opponent_pool=_parse_opponent_pool_arg(args.opponents),
  )
  trainer.train(eval_every=args.eval_every, eval_games=args.eval_games, verbose=not args.quiet)
  print(f"saved_policy={trainer.policy_path}")
  print(f"abstraction={trainer.abstraction_ref}")
  print(f"training_mode={trainer.training_mode}")
  print(f"training_opponents={[spec['label'] for spec in trainer.opponent_pool]}")
  print(f"visited_states={trainer._visited_state_count()}")


def _parse_opponent_pool_arg(opponents_arg):
  if opponents_arg is None:
    return None
  return [entry.strip() for entry in str(opponents_arg).split(",")]


if __name__ == "__main__":
  main()
