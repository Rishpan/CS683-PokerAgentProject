# Discounted MCCFR+

This package contains the existing discounted MCCFR-style agent that previously lived as flat files in `lucas_agents/`.

## Files
- `discounted_mccfr_plus_agent.py`: main agent implementation with `setup_ai()`.
- `train_discounted_mccfr_plus_agent.py`: fixed-game trainer.
- `discounted_mccfr_plus_policy.json`: persisted regrets and average strategy.

## Method
`DiscountedMCCFRPlusAgent` extends `AdvancedCFRPlayer` and keeps the same overall regret-matching structure, while retuning three parts of the policy:

- lower exploration during training
- more aggressive raise priors when equity and fold pressure line up
- slower regret/strategy discounting so strong signals survive longer

It is still heuristic MCCFR-style learning rather than a full tabular game-tree traversal. The main gain is a stronger prior and a more persistent learned average strategy.

## Training

```bash
python3 lucas_agents/discounted_mccfr_plus/train_discounted_mccfr_plus_agent.py --games 400
```

## Compare

```bash
python3 compare_agents.py \
  lucas_agents/discounted_mccfr_plus/discounted_mccfr_plus_agent.py \
  lucas_agents/advanced_cfr/advanced_cfr_player.py
```
