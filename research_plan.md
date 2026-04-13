# Poker agent research notes

## Current baseline
- `lucas_agents/advanced_cfr/advanced_cfr_player.py` is the current learned agent.
- `compare_agents.py` is the existing head-to-head comparison harness.
- `lucas_agents/advanced_cfr/train_advanced_cfr.py` had stale absolute paths and broken imports, now corrected.

## Main weaknesses in current advanced CFR
- Uses trajectory-based regret updates with heuristic counterfactual values, not true full-game CFR traversal.
- Training opponent pool is narrow, mostly `ConditionThresholdPlayer` with occasional mirror matches.
- Inference only trusts learned policy when a learned action strongly dominates, so it often falls back to the rule baseline.
- Postflop simulation count is moderate, which limits accuracy in marginal spots.

## Experimental stronger agent idea
`lucas_agents/discounted_mccfr_plus_agent.py`
- inherits from `AdvancedCFRPlayer`
- increases postflop simulation count
- lowers exploration to sharpen policy faster
- increases prior weight but retunes priors toward stronger value betting and pressure-aware folding
- preserves regret signal longer via slower discounting
- trusts learned raise actions more aggressively at inference time

## Evaluation plan
1. Re-train baseline advanced CFR cleanly.
2. Train discounted MCCFR+ agent.
3. Run repeated comparisons:
   - discounted MCCFR+ vs advanced CFR
   - discounted MCCFR+ vs condition threshold
   - advanced CFR vs condition threshold
4. Compare win count and average final stack over larger batches.

## Next likely improvements if superior agent is still weak
- opponent-mixture self-play with randomized parameter variants
- explicit bounty for exploitative responses to passive or over-folding opponents
- deeper abstraction around betting sequence and sizing pressure
- swap heuristic reward shaping for outcome plus street-level action EV estimates
