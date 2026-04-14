# Adversarial Search MCCFR

This package keeps the existing learnable / discounted MCCFR family for training, but adds a practical one-ply opponent-model lookahead at inference time.

## Files
- `adversarial_search_mccfr_agent.py`: agent implementation with `setup_ai()`.
- `train_adversarial_search_mccfr_agent.py`: lightweight trainer that reuses the existing MCCFR-style update flow.
- `adversarial_search_mccfr_policy.json`: saved regrets, average strategy, learnable action weights, and search metadata.

## What makes this "adversarial search"

At decision time the agent:

1. Enumerates legal `fold` / `call` / `raise` actions.
2. Builds a small opponent response model from observed opponent `fold`, `call`, and `raise` frequencies.
3. Estimates a shallow expected value for each action by combining:
   - rollout-based hand strength / equity information
   - expected opponent response value
   - inherited learned action score from the learnable discounted MCCFR agent
   - inherited MCCFR counterfactual heuristic and average-policy bias
4. Picks the action with the highest combined score.

This is intentionally lightweight. It is not a full game-tree solver and it does not try to perform deep re-solving.

## Important distinction

Monte Carlo equity rollouts are not adversarial search by themselves.

Rollouts estimate how often the current hand wins against random future cards. They do **not** model how a particular opponent is likely to react to `call` versus `raise`, and they do not compare explicit opponent responses across candidate actions.

The adversarial-search flavor here comes from the extra one-step action evaluation layer that predicts opponent reactions and scores each legal action against those predicted reactions.

## Training

Training still uses the inherited discounted MCCFR-style regret updates plus the learnable linear action weights:

```bash
python3 lucas_agents/adversarial_search_mccfr/train_adversarial_search_mccfr_agent.py --games 300
```

## Compare

```bash
python3 compare_agents.py \
  lucas_agents/adversarial_search_mccfr/adversarial_search_mccfr_agent.py \
  lucas_agents/learnable_discounted_mccfr/learnable_discounted_mccfr_agent.py
```
