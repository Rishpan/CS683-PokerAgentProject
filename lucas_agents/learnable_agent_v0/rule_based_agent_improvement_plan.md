# Rule-Based Agent Improvement Plan for `learnable_agent_v0`

## Current Situation

Recent training changes made `learnable_agent_v0` much more robust operationally:
- policy checkpoints during training
- coverage checkpoints during training
- retry/skip around failed matches
- fixed-policy self-play snapshots
- checkpoint evaluation plots

However, the most recent 500-game mixed run still underperformed against rule-based opponents:
- vs `threshold`: 43.33%
- vs `condition_threshold`: 40.00%
- vs `fixed_self`: 50.00%

So the system is now more stable, but not yet strategically better against the rule-based baselines.

## Main Diagnosis

The problem does **not** look like a pure optimization or runtime issue anymore. It looks like a **mismatch between what the learner is optimizing and what the rule-based agents are actually doing**.

### Likely causes

1. **Average-policy CFR alone is too smooth**
   - The current learner gradually averages behavior over many abstract states.
   - Rule-based opponents often have sharp threshold boundaries.
   - A smooth average strategy can become competent overall but fail to exploit brittle decision edges.

2. **Training rewards are too local and too generic**
   - Regret updates are mostly driven by normalized round outcomes.
   - That encourages broad improvement, but not explicit exploitation of deterministic opponent rules.

3. **Self-play can wash out exploit patterns**
   - Even when rule-based opponents are included, self-play encourages symmetry and robustness.
   - That often reduces the specialized exploit behavior needed to beat threshold-style agents.

4. **The abstraction may be too coarse for exploitative play**
   - If key rule-based triggers are compressed into the same abstract bucket, the learner cannot consistently separate exploit-worthy situations.

## Do We Need Local Search?

### Short answer
**Probably not as the first fix.**

### Why not first
Local search can help if:
- the opponent is predictable,
- the search model is accurate,
- and the search is only used in high-leverage spots.

But in this project, local search would likely be a **second-stage refinement**, not the main fix for `learnable_agent_v0`, because:
- the current learner is still weak against simple rule-based policies,
- the main issue appears to be exploit learning and representation,
- adding search too early would increase instability and engineering complexity.

### When local search *would* make sense
Local search becomes more promising after the base learner can already consistently match or slightly beat the rule-based baselines. Then it could be used as:
- a selective override in high-confidence exploit spots,
- a bounded one-step action scorer,
- or a learned-response refinement layer.

So local search is a **possible later upgrade**, but it is not my recommended first move here.

## Better First Moves

### 1. Add explicit opponent-style features and exploit signals
The learner currently reasons mostly from board/price/history abstractions. To beat rule-based players better, it should encode signals like:
- opponent fold-to-pressure tendency
- opponent raise frequency by street
- opponent passivity after checking/calling
- whether the line looks threshold-like (predictable value gating)
- whether the opponent over-folds at certain pressure levels

This can still stay inside `lucas_agents` and inside the current learnable framework.

### 2. Add opponent-specific training heads or score adjustments
Instead of one single blended policy signal, keep a shared policy plus small opponent-style adjustment terms.

For example:
- base strategy from regret-matching / average policy
- exploit adjustment when opponent resembles:
  - `threshold`
  - `condition_threshold`
  - `self-like`

This is lighter and safer than full local search.

### 3. Improve checkpoint selection, not just training
Training is clearly **not monotonic**. Later checkpoints can get worse against threshold-style opponents.

So the trainer should keep:
- best-vs-threshold checkpoint
- best-vs-condition-threshold checkpoint
- best robust checkpoint (for example, best minimum win rate across both)

This may immediately improve final deployed performance without changing the underlying learner much.

### 4. Train on harder exploit-focused schedules
Instead of static mixture only, use stages:

#### Stage A: policy shaping
- 30% fixed self
- 35% threshold
- 35% condition_threshold

#### Stage B: exploit sharpening
- 20% fixed self
- 40% threshold
- 40% condition_threshold

This reduces drift back toward smooth self-play behavior late in training.

### 5. Add targeted action-bias learning against deterministic patterns
Rule-based agents often have predictable mistakes:
- folding too often in certain pressure spots
- failing to bluff enough
- overcalling in value regions
- under-defending against pressure lines

A practical next step is to add a **small learnable exploit bias layer** on top of the current strategy:
- fold_bias
- call_bias
- raise_bias
based on opponent-style indicators and street/pressure context

This is much cheaper and safer than adding full search.

## Recommended Plan

### Phase 1: best-checkpoint tracking
Implement inside `learnable_agent_v0`:
- evaluate checkpoints against `threshold` and `condition_threshold`
- save:
  - `best_vs_threshold_policy.json`
  - `best_vs_condition_threshold_policy.json`
  - `best_robust_policy.json`

This should happen during training and is likely the highest ROI step.

### Phase 2: exploit-bias extension
Extend the learner with a small exploit adjustment that depends on:
- street
- pressure
- pot odds
- opponent aggression/fold stats
- recent public action pattern

Use this only as a bounded adjustment to the current strategy, not as a full replacement.

### Phase 3: staged training schedule
Move from a static mixture to a two-stage schedule so late training is more exploit-focused against rule-based players.

### Phase 4: optional selective local search
Only after the above works, test a very small selective search module:
- use it only on turn/river,
- only when opponent style is highly predictable,
- only when action margins are close,
- and only as a refinement layer.

## Recommendation Summary

If the goal is to beat rule-based agents consistently, I do **not** recommend jumping straight to local search.

I recommend this order instead:
1. **checkpoint selection / best robust checkpoint saving**
2. **opponent-aware exploit-bias learning**
3. **staged exploit-focused training schedule**
4. **only then consider selective local search**

That gives the best chance of improving real performance without making the system much more fragile.
