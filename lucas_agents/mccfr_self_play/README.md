# MCCFR Self-Play

This package treats the abstraction as part of the policy identity.

## Folder layout

- Abstractions: `lucas_agents/mccfr_self_play/abstractions/`
- Policies: `lucas_agents/mccfr_self_play/policies/`
- Backward-compatible root files are still kept so older commands continue to work.

## Switch the active default pair

Edit [mccfr_config.py](/Users/xiaofanlu/Documents/github_repos/CS683-PokerAgentProject/lucas_agents/mccfr_self_play/mccfr_config.py:42) and change:

```python
DEFAULT_PROFILE_KEY = "rich_hand_strength_v5"
```

Available presets:

- `rich_hand_strength_v5`
- `rich_hand_strength_v4`
- `rich_hand_strength_v3`
- `bayes_opponent_compact_v1`

The active preset controls:

- `DEFAULT_ABSTRACTION_REF`
- `DEFAULT_POLICY_PATH`
- legacy fallback policy paths for that preset

## Current default: rich_hand_strength_v5

Default abstraction:

- file: `abstractions/rich_hand_strength_v5.py`
- abstraction name: `rich_hand_strength`
- abstraction version: `rich_hand_strength_v5`
- default policy: `policies/mccfr_policy.rich_hand_strength_v5.json`

`v5` is designed for one-hand MCCFR traces:

- history is hand-local, not match-local
- fold endings are ignored because they terminate the hand
- explicit `pot_odds` is restored as its own feature
- `spr_commitment` remains as a separate feature
- opponent tendency can incorporate prior completed hands in the same match
- prior-street aggression and current-street raise state are kept as the history signal

Key layout:

- `street`
- `strength`
- `position`
- `pot_odds`
- `spr_commitment`
- `opponent_tendency`
- `history`

## Required abstraction interface

Any abstraction module used by this package must define:

- `ABSTRACTION_NAME`
- `ABSTRACTION_VERSION`
- `build_info_key(hole_card, round_state, player_uuid, opponent_action_stats, postflop_simulations)`
- `observe_opponent_actions(action_histories, player_uuid)`
- `abstraction_state_upper_bound()`

The trainer only needs:

- a stable infoset key
- lightweight opponent features
- a rough abstraction state upper bound

## Policy and abstraction binding

Each saved policy stores:

- `abstraction_ref`
- `abstraction_name`
- `abstraction_version`

That means:

- continuing training reuses the policy's abstraction automatically
- loading a policy for play reuses the policy's abstraction automatically
- changing abstraction without resetting or switching policy paths is rejected

Legacy `v3` policies that still reference `mccfr_abstraction` are remapped automatically to the preserved `v3` abstraction preset.

## Train with the current default

```bash
python3 lucas_agents/mccfr_self_play/mccfr_trainer.py --iterations 500
```

## Train with an explicit preset

`v4`:

```bash
python3 lucas_agents/mccfr_self_play/mccfr_trainer.py \
  --abstraction lucas_agents/mccfr_self_play/abstractions/rich_hand_strength_v4.py \
  --policy-path lucas_agents/mccfr_self_play/policies/mccfr_policy.rich_hand_strength_v4.json \
  --reset-policy \
  --iterations 500
```

Bayesian opponent abstraction:

```bash
python3 lucas_agents/mccfr_self_play/mccfr_trainer.py \
  --abstraction lucas_agents/mccfr_self_play/abstractions/bayes_opponent_compact_v1.py \
  --policy-path lucas_agents/mccfr_self_play/policies/mccfr_policy.bayes_opponent_compact_v1.json \
  --iterations 500
```

## Create a new abstraction

1. Copy `mccfr_abstraction_template.py` or `abstractions/template.py`.
2. Implement the required interface.
3. Add a new preset entry in [mccfr_config.py](/Users/xiaofanlu/Documents/github_repos/CS683-PokerAgentProject/lucas_agents/mccfr_self_play/mccfr_config.py:8).
4. Point that preset at a dedicated policy filename under `policies/`.
5. Train with `--reset-policy` the first time.
