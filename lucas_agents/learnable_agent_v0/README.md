# learnable_agent_v0

This folder contains the `learnable_agent_v0` poker agent and its training artifacts.

## Files
- `learnable_cfr_player.py`: the player used by `compare_agents.py`
- `train_learnable_cfr.py`: training entrypoint
- `learnable_cfr_policy.json`: learned policy snapshot
- `training_coverage.json`: coverage and training metadata
- `results.md`: compact benchmark log for the latest requested evaluations

## Train

```bash
python3 lucas_agents/learnable_agent_v0/train_learnable_cfr.py 10000
```

## Compare

```bash
python3 compare_agents.py \
  lucas_agents/learnable_agent_v0/learnable_cfr_player.py \
  lucas_agents/condition_threshold_player.py \
  --games 300 --max-round 100 --initial-stack 500 --small-blind 10
```
