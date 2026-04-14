# Adversarial Search MCCFR V2

This package keeps the stronger `LearnableDiscountedMCCFRAgent` as the anchor policy and adds a conservative opponent-model search layer on top.

## Why v1 likely underperformed

The v1 design looked vulnerable in a few specific ways:

- It replaced the default learned action with a one-ply search ranking on every inference decision, so shallow search noise could beat a much better trained policy.
- Its saved policy was far smaller than the learnable baseline policy, which suggests the search layer was often compensating for weaker learned coverage instead of refining a strong prior.
- It searched even in low-leverage spots where the EV gap between `call` and `raise` is tiny, so model error could create unnecessary action churn.
- The search score mixed several heuristics on incompatible scales and then picked the top score directly, which makes overconfident overrides more likely.
- There was no explicit disagreement gate or confidence margin before replacing the baseline action.

## v2 design

v2 changes the role of search:

- Search is a gated refinement, not a full replacement.
- The agent first builds an anchor policy from current regret strategy, average strategy, learnable action scores, and counterfactual values.
- The default action remains the learned/base choice unless the anchor margin is already convincing.
- Opponent-model search is emphasized mostly in higher-leverage spots: later streets, larger pressure, meaningful raise commitments, and notable pot commitment.
- Search only overrides the default action when it has enough search margin, enough blended-policy margin, and enough confidence.

## Files

- `adversarial_search_mccfr_v2_agent.py`: v2 inference logic plus `setup_ai()`.
- `train_adversarial_search_mccfr_v2_agent.py`: lightweight trainer compatible with the existing project flow.
- `adversarial_search_mccfr_v2_policy.json`: seeded policy copied from the stronger learnable MCCFR policy and extended with v2 metadata.
- `comparison_vs_learnable.txt`: saved comparison output against the learnable baseline.

## Train

```bash
python3 lucas_agents/adversarial_search_mccfr_v2/train_adversarial_search_mccfr_v2_agent.py --games 300
```

## Compare

```bash
python3 compare_agents.py \
  lucas_agents/adversarial_search_mccfr_v2/adversarial_search_mccfr_v2_agent.py \
  lucas_agents/learnable_discounted_mccfr/learnable_discounted_mccfr_agent.py
```
