import argparse
import importlib.util
from copy import deepcopy
from pathlib import Path
from pprint import pformat

from pypokerengine.api.game import setup_config, start_poker
from pypokerengine.players import BasePokerPlayer


DEFAULT_PLAYER_A = "lucas_agents/condition_threshold_player.py"
DEFAULT_PLAYER_B = "raise_player.py"
DEFAULT_OUTPUT = "lucas_agents/design/single_game_trace.md"
DEFAULT_INITIAL_STACK = 500
DEFAULT_SMALL_BLIND = 10
DEFAULT_MAX_ROUND = 100


def load_player(script_path, module_name):
    path = Path(script_path).resolve()
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ValueError("Cannot load player script: %s" % path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not hasattr(module, "setup_ai"):
        raise ValueError("Player script must define setup_ai(): %s" % path)
    return module.setup_ai()


class TracingPlayer(BasePokerPlayer):
    def __init__(self, inner_player, player_name):
        self.inner_player = inner_player
        self.player_name = player_name
        self.trace_entries = []

    def _sync_runtime_state(self):
        self.inner_player.uuid = getattr(self, "uuid", None)

    def declare_action(self, valid_actions, hole_card, round_state):
        self._sync_runtime_state()
        raw_action = self.inner_player.declare_action(valid_actions, hole_card, round_state)
        if isinstance(raw_action, tuple):
            action, amount = raw_action
            returned_action = raw_action
        else:
            action, amount = raw_action, None
            returned_action = raw_action
        self.trace_entries.append(
            {
                "player_name": self.player_name,
                "street": round_state.get("street"),
                "round_count": round_state.get("round_count"),
                "valid_actions": deepcopy(valid_actions),
                "hole_card": deepcopy(hole_card),
                "round_state": deepcopy(round_state),
                "chosen_action": {"action": action, "amount": amount},
            }
        )
        return returned_action

    def receive_game_start_message(self, game_info):
        self._sync_runtime_state()
        if hasattr(self.inner_player, "receive_game_start_message"):
            self.inner_player.receive_game_start_message(game_info)

    def receive_round_start_message(self, round_count, hole_card, seats):
        self._sync_runtime_state()
        self.inner_player.receive_round_start_message(round_count, hole_card, seats)

    def receive_street_start_message(self, street, round_state):
        self._sync_runtime_state()
        self.inner_player.receive_street_start_message(street, round_state)

    def receive_game_update_message(self, action, round_state):
        self._sync_runtime_state()
        self.inner_player.receive_game_update_message(action, round_state)

    def receive_round_result_message(self, winners, hand_info, round_state):
        self._sync_runtime_state()
        self.inner_player.receive_round_result_message(winners, hand_info, round_state)


def build_markdown(trace_entries, game_result, player_a_path, player_b_path, max_round, initial_stack, small_blind):
    players_by_stack = sorted(game_result["players"], key=lambda seat: seat["stack"], reverse=True)
    lines = [
        "# Single Game Decision Trace",
        "",
        "## Match Setup",
        "",
        "- player_a: `%s`" % Path(player_a_path).name,
        "- player_b: `%s`" % Path(player_b_path).name,
        "- max_round: `%d`" % max_round,
        "- initial_stack: `%d`" % initial_stack,
        "- small_blind: `%d`" % small_blind,
        "",
        "## Final Result",
        "",
        "```python",
        pformat(players_by_stack, width=100, sort_dicts=False),
        "```",
        "",
        "## Traced Decisions",
        "",
    ]

    for index, entry in enumerate(trace_entries, start=1):
        lines.extend(
            [
                "### Decision %d" % index,
                "",
                "- player: `%s`" % entry["player_name"],
                "- round_count: `%s`" % entry["round_count"],
                "- street: `%s`" % entry["street"],
                "- chosen_action: `%s`" % entry["chosen_action"],
                "",
                "#### valid_actions",
                "",
                "```python",
                pformat(entry["valid_actions"], width=100, sort_dicts=False),
                "```",
                "",
                "#### hole_card",
                "",
                "```python",
                pformat(entry["hole_card"], width=100, sort_dicts=False),
                "```",
                "",
                "#### round_state",
                "",
                "```python",
                pformat(entry["round_state"], width=100, sort_dicts=False),
                "```",
                "",
            ]
        )

    return "\n".join(lines)


def run_trace(player_a_path, player_b_path, output_path, max_round, initial_stack, small_blind):
    config = setup_config(
        max_round=max_round,
        initial_stack=initial_stack,
        small_blind_amount=small_blind,
    )

    traced_player = TracingPlayer(load_player(player_a_path, "trace_player_a"), "player_a")
    opponent_player = load_player(player_b_path, "trace_player_b")
    config.register_player(name="player_a", algorithm=traced_player)
    config.register_player(name="player_b", algorithm=opponent_player)

    game_result = start_poker(config, verbose=0)
    markdown = build_markdown(
        traced_player.trace_entries,
        game_result,
        player_a_path,
        player_b_path,
        max_round,
        initial_stack,
        small_blind,
    )

    target = Path(output_path).resolve()
    target.write_text(markdown, encoding="utf-8")
    return target, len(traced_player.trace_entries), game_result


def main():
    parser = argparse.ArgumentParser(description="Run one game and save a readable decision trace for player_a.")
    parser.add_argument("--player-a", default=DEFAULT_PLAYER_A)
    parser.add_argument("--player-b", default=DEFAULT_PLAYER_B)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--max-round", type=int, default=DEFAULT_MAX_ROUND)
    parser.add_argument("--initial-stack", type=int, default=DEFAULT_INITIAL_STACK)
    parser.add_argument("--small-blind", type=int, default=DEFAULT_SMALL_BLIND)
    args = parser.parse_args()

    output_path, decision_count, game_result = run_trace(
        args.player_a,
        args.player_b,
        args.output,
        args.max_round,
        args.initial_stack,
        args.small_blind,
    )
    print("Saved %d traced decisions to %s" % (decision_count, output_path))
    print("Final players: %s" % pformat(game_result["players"], width=100, sort_dicts=False))


if __name__ == "__main__":
    main()
