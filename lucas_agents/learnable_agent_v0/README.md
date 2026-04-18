# learnable_agent_v0

This folder contains the `learnable_agent_v0` poker agent and its training artifacts.

## Files
- `learnable_cfr_player.py`: the player used by `compare_agents.py`
- `fixed_policy_player.py`: frozen-policy self-play opponent used during training
- `random_player_wrapper.py`: local wrapper so training can include the repo random player
- `train_learnable_cfr.py`: training entrypoint
- `learnable_cfr_policy.json`: learned policy snapshot
- `fixed_policy_snapshot.json`: copy of policy made before a training run for fixed self-play
- `training_coverage.json`: coverage and training metadata
- `results.md`: compact benchmark log for the latest requested evaluations

## Train

```bash
python3 lucas_agents/learnable_agent_v0/train_learnable_cfr.py 10000
```

Training now uses a weighted opponent mix:
- fixed snapshot of itself: mostly
- threshold player: sometimes
- random player: rarely

Before each run, the trainer copies `learnable_cfr_policy.json` to `fixed_policy_snapshot.json`, then uses that frozen snapshot as the self-play opponent.

## Plotting

Plots are written to:
- `lucas_agents/learnable_agent_v0/training_plots/latest.png`
- `lucas_agents/learnable_agent_v0/training_plots/<run_id>.png`

If you do not have matplotlib installed, install it locally with:

```bash
python3 -m pip install --user matplotlib
```

## Compare

```bash
python3 compare_agents.py \
  lucas_agents/learnable_agent_v0/learnable_cfr_player.py \
  lucas_agents/condition_threshold_player.py \
  --games 300 --max-round 100 --initial-stack 500 --small-blind 10
```
