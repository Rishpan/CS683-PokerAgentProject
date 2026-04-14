# Adversarial Search MCCFR V3

This package keeps the v2 structure: a learnable discounted MCCFR base policy, an anchor policy that blends several signals, and a gated search override that only activates in higher-leverage spots.

## What changed in v3

v2 still depended on static search constants. v3 makes that layer persistent and learnable:

- `refinement_weights` are updated online so the anchor can shift between regret strategy, average strategy, learned action scores, counterfactual values, and search support.
- `search_weights` are updated online so the search score can re-balance rollout value, opponent response value, learned value, counterfactual value, policy bias, and the base-action bonus.
- override and gating thresholds are updated online so the agent can become more conservative or more willing to trust search depending on realized outcomes.

The adaptation is intentionally lightweight rather than academically exact. During training, each decision stores the same search diagnostics used at inference time. After the round ends, the realized reward is mixed with heuristic action values to build a target policy, and the refinement/search parameters are nudged toward components that better explain that target.

## Files

- `adversarial_search_mccfr_v3_agent.py`: v3 agent with `setup_ai()` compatibility.
- `train_adversarial_search_mccfr_v3_agent.py`: trainer for online adaptation and persistence.
- `adversarial_search_mccfr_v3_policy.json`: saved regrets, learned action weights, learned search parameters, and thresholds after training.
- `comparisons/`: saved comparison outputs against requested baselines.

## Train

```bash
python3 lucas_agents/adversarial_search_mccfr_v3/train_adversarial_search_mccfr_v3_agent.py --games 360
```

## Compare

```bash
python3 compare_agents.py \
  lucas_agents/adversarial_search_mccfr_v3/adversarial_search_mccfr_v3_agent.py \
  lucas_agents/adversarial_search_mccfr_v2/adversarial_search_mccfr_v2_agent.py
```
