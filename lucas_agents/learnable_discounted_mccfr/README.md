# Learnable Discounted MCCFR

This package starts from the same discounted MCCFR-style agent family, but replaces the fixed fold/call/raise coefficients with trainable linear weights.

## Files
- `learnable_discounted_mccfr_agent.py`: learnable agent with `setup_ai()`.
- `train_learnable_discounted_mccfr_agent.py`: trainer for online updates and policy persistence.
- `learnable_discounted_mccfr_policy.json`: initial weights plus any learned regrets, average strategy, and updated coefficients.

## How learning works
The agent still uses discounted regret matching over information sets, but it also maintains an action-specific parameter dictionary:

- `fold`, `call`, and `raise` each have trainable coefficients
- the coefficients score features such as hand strength, pot odds, pressure, draws, opponent aggression, opponent fold rate, position, and short-stack pressure
- after every round, the chosen action and available alternatives are updated toward a mixed target:
  - the actual normalized round reward
  - the original discounted MCCFR heuristic counterfactual estimate

That gives a lightweight online learner: the agent begins with the old hand-tuned weights, then gradually shifts them when real outcomes disagree with the heuristic.

## Training

```bash
python3 lucas_agents/learnable_discounted_mccfr/train_learnable_discounted_mccfr_agent.py --games 400
```

## Compare

```bash
python3 compare_agents.py \
  lucas_agents/learnable_discounted_mccfr/learnable_discounted_mccfr_agent.py \
  lucas_agents/discounted_mccfr_plus/discounted_mccfr_plus_agent.py
```
