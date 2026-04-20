# Learnable Adversarial Search Agent v2

This variant keeps the same overall structure as `learnable_adversarial_search_agent`, but changes the abstraction to the requested 6-dimensional state:

```python
state = (
  street,
  hand_bucket,
  board_bucket,
  history_bucket,
  position,
  pot_bucket,
)
```

Bucket sizes:
- street: 4
- hand_bucket: 6
- board_bucket: 8
- history_bucket: 15
- position: 2
- pot_bucket: 2

Total abstract states:
- `4 * 6 * 8 * 15 * 2 * 2 = 11,520`

## Notes

- Training keeps search disabled.
- Inference can still use the simple search module.
- Trainer is resilient to match exceptions and continues after retries.
- Opponents during training are:
  - threshold-based player
  - frozen self-play player using the current saved policy

## Training

Example:

```bash
python3 lucas_agents/learnable_adversarial_search_agent_v2/train_cfr.py --games 3000
```
