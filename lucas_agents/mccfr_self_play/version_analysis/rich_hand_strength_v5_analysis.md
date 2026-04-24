# `rich_hand_strength_v5` analysis

This note summarizes:

- what each infoset dimension means
- why `mccfr_policy.rich_hand_strength_v5.stats_raise_player.json` shows many missing infosets
- whether the highly visited keys are sensible
- how `_traverse` actually samples hands and opponents
- what to change next

## 1. Infoset layout

`rich_hand_strength_v5.py` builds keys as:

`street | strength | position | pot_odds | spr_commitment | history`

Nominal abstraction size:

`4 * 8 * 2 * 4 * 5 * 12 = 15,360`

### `street`

- values: `0..3`
- mapping:
  - `0 = preflop`
  - `1 = flop`
  - `2 = turn`
  - `3 = river`

### `strength`

- values: `0..7`
- built from `bucket_value(strength, 8)`
- bucket meaning is approximately:
  - `0 = [0.000, 0.125)`
  - `1 = [0.125, 0.250)`
  - `2 = [0.250, 0.375)`
  - `3 = [0.375, 0.500)`
  - `4 = [0.500, 0.625)`
  - `5 = [0.625, 0.750)`
  - `6 = [0.750, 0.875)`
  - `7 = [0.875, 1.000)`

Preflop this is a heuristic score. Postflop it is:

- `0.70 * equity`
- `0.20 * made_hand_score`
- `0.10 * draw_score`

### `position`

- values: `0` or `1`
- `1` means has position
- heads-up rule:
  - preflop, the button is not marked as having position
  - postflop, the button is marked as having position

Important consequence:

- in heads-up preflop, `position = 1` is effectively unreachable

### `pot_odds`

- values: `0..3`
- based on `to_call / (pot + to_call)`
- bucket meaning:
  - `0 = [0.00, 0.25)`
  - `1 = [0.25, 0.50)`
  - `2 = [0.50, 0.75)`
  - `3 = [0.75, 1.00)`

If `to_call <= 0`, this is `0`.

### `spr_commitment`

- values: `0..4`
- combines SPR, call share, and stack share
- practical meaning:
  - `0 = no call required, SPR >= 2`
  - `1 = low commitment / cheap continue`
  - `2 = medium commitment`
  - `3 = high commitment`
  - `4 = near stack-off / very low SPR`

### `history`

- values: `0..11`
- encoded as:

`history = prior_raise_bucket * 4 + current_state`

Where:

- `prior_raise_bucket`:
  - `0 = no raises on earlier streets`
  - `1 = exactly 1 earlier-street raise`
  - `2 = 2 or more earlier-street raises`

- `current_state`:
  - `0 = current street unopened`
  - `1 = current street passive only`
  - `2 = current street has exactly 1 raise`
  - `3 = current street has 2 or more raises`

So:

- `0..3` = no prior-street raises
- `4..7` = one prior-street raise
- `8..11` = two or more prior-street raises

### Not actually used in the key

`opponent_action_stats` is computed and passed around, but `rich_hand_strength_v5` does not use it in the infoset key.

## 2. What the stats file means

`mccfr_policy.rich_hand_strength_v5.stats_raise_player.json` is not a policy file. It is a lookup log produced by `StrategyTable.average_strategy()`.

- `visited_info_keys` means the acting player looked up an infoset that existed in `strategy_sum`
- `missing_info_keys` means the acting player looked up an infoset that did not exist in `strategy_sum`, so play fell back to regret-matching or uniform fallback

This matters because "missing" does not mean the abstraction lost information. It means the loaded policy had no saved average strategy for that infoset.

## 3. Why there are many missing infosets

There are several causes, and they stack.

### A. Coverage is sparse

The loaded policy metadata says:

- `episodes = 1000`
- `visited_states = 600`
- `visited_state_percentage = 3.9062`

That is only 600 distinct visited states out of a nominal 15,360-state abstraction.

Even before evaluating against `raise_player`, the policy is sparse.

### B. `raise_player` pushes the game into rare aggressive branches

`raise_player.py` always raises when raise is legal, otherwise it calls.

That produces many states with:

- current-street single raise or 2+ raises
- prior aggressive streets
- postflop raised-pot continuations

Those branches are exactly where the top missing keys cluster.

Examples of top missing keys:

- `0|4|0|0|2|3`
  - preflop, medium strength, no position flag, low price, medium commitment, current street already has 2+ raises
- `1|5|1|0|2|7`
  - flop, stronger hand, in position, low price, medium commitment, one prior-street raise and 2+ raises on the flop
- `2|6|1|0|3|11`
  - turn, strong hand, in position, low price, high commitment, multiple aggressive streets and 2+ raises on the current street

These are plausible states against an always-raise opponent, but they are underrepresented in self-play training.

### C. Trainer stores regrets more broadly than average strategies

This is the most important trainer-level issue.

In `_traverse`:

- traverser nodes get regret updates
- in self-play, opponent nodes get average-strategy accumulation

So self-play deliberately updates different tables on different node types.

Result:

- some infosets appear in `regret_sum`
- but do not appear in `strategy_sum`

At action time, `MCCFRPlayer` uses `average_strategy()`, which only checks `strategy_sum`.

So a state can be "known" to the trainer from a regret perspective and still be counted as missing at runtime.

For the current policy and `stats_raise_player.json`:

- `6367` total missing lookups
- `388` of those misses are regret-only states
- `5979` of those misses are absent from both `regret_sum` and `strategy_sum`

So most misses are genuinely unseen policy states, but a nontrivial fraction come from the regret/average split.

### D. The abstraction upper bound is loose

The 15,360 bound counts combinations that are not reachable in heads-up play.

Examples:

- preflop with `position = 1`
- preflop with any prior-street raises

So the reported percentage understates effective coverage somewhat. The policy is still sparse, but the bound is not tight.

## 4. Are the highly visited keys good?

Mostly yes for `raise_player` evaluation. No for broad robustness.

Top visited keys include:

- `0|3|0|1|2|2`
- `0|2|0|1|2|2`
- `0|4|0|1|2|2`
- `0|4|0|0|1|3`
- `1|3|1|0|1|6`

Interpretation:

- many are preflop
- most are medium-strength hands
- many are facing a raise
- many are in moderate commitment states
- several are raised-pot flop/turn continuations

That is exactly what should happen against an always-raise opponent.

So these keys are "good" in the narrow sense that they match the induced distribution from `raise_player`.

They are not "good" in the broader sense of coverage quality:

- only `244` distinct infosets were visited in the `raise_player` stats file
- visited traffic is highly concentrated in a small region of the state space
- high-price `pot_odds` buckets `2` and `3` do not appear in visited lookups
- `spr_commitment = 4` does not appear in visited lookups

Conclusion:

- the hot keys are sensible
- but they show a narrow, biased operating region rather than a well-covered policy

## 5. Confirming `_traverse` behavior

Your understanding is basically correct, with one important nuance.

### What happens per training iteration

For each training iteration:

1. a fresh initial game state is created
2. one poker round is started
3. the trainer runs two traversals:
   - one with `p0` as traverser
   - one with `p1` as traverser

So each iteration is one sampled poker hand environment, but the trainer evaluates it twice, once from each learner seat as traverser.

### Self-play case

If the opponent pool is default self-play:

- both seats are learner policy copies
- at opponent nodes, the acting action is sampled from the current strategy
- average strategy is accumulated on those opponent nodes

This is effectively self vs self.

### Scripted-opponent case

If the opponent pool contains `raise_player.py`:

- the traverser seat is still the learner
- the opponent seat is the scripted agent
- when the scripted agent acts, `_scripted_opponent_action()` is called
- no learner average strategy is accumulated on those scripted-opponent nodes
- for scripted-opponent training, the learner's own traverser infosets are explicitly accumulated into `strategy_sum`

So this is learner vs scripted opponent, not self vs self.

### Important nuance

The hand is not re-dealt separately for each action branch.

The sampled private cards and public chance outcomes define one sampled episode root, and `_traverse` then recursively explores decision branches from that sampled hand state using external sampling.

So the cleanest description is:

- one sampled round root per iteration
- two traversals from that root, one per learner seat
- each traversal is either learner vs learner or learner vs scripted opponent, depending on the sampled opponent spec

## 6. How to improve the poker player

### Priority 1: fix the trainer/policy-table mismatch

This is the highest-value change.

Problem:

- runtime play uses `strategy_sum`
- self-play training often updates only regrets on traverser nodes
- this creates avoidable runtime misses

Good fixes:

- store average strategy for all learner infosets, not just opponent nodes
- or, at inference time, fall back to regret-matching from `regret_sum` before treating a state as missing

The second option is easy and pragmatic. The first option is cleaner if you want the exported policy file to be self-contained as an average-strategy policy.

### Priority 2: train against a mixed opponent pool

Training only in self-play produces a narrow state distribution. Training only against `raise_player` would overfit another narrow distribution.

Better:

- use a mixed pool such as `self,raise_player.py,lucas_agents/condition_threshold_player.py`
- optionally add a random or loose-passive opponent too

This should improve support on:

- repeated-raise branches
- strange price points
- unusual postflop aggression patterns

### Priority 3: train longer

More training is necessary, but not sufficient by itself.

Given current metadata:

- 1000 episodes
- 600 visited states

This is too small for this abstraction, even allowing for unreachable states.

More iterations will help, but if the opponent distribution stays narrow and the trainer still under-populates `strategy_sum`, misses will remain.

So:

- more training: yes
- more training alone: no

### Priority 4: tighten or revise the abstraction

A new abstraction may help, but it is not the first fix I would make.

Current abstraction issues:

- it counts some unreachable combinations
- history is quite expressive, which increases sparsity
- `pot_odds` and `spr_commitment` can partially overlap in what they capture
- no opponent-style signal is actually in the key, despite computing opponent stats

Possible abstraction improvements:

- remove unreachable combinations from any coverage accounting
- simplify history, for example:
  - separate "current street raised?" from "multi-street aggression?"
  - reduce 12 history buckets to a smaller, better-supported set
- consider reducing one of:
  - `pot_odds`
  - `spr_commitment`
  if they are creating too many sparse combinations
- if exploitability against scripted opponents matters, add a compact opponent-style feature back into the key

I would not jump to a brand-new abstraction before fixing the trainer issue and running broader training. Right now the evidence points more strongly to coverage and training-distribution problems than to abstraction failure.

### Priority 5: improve evaluation and diagnostics

Current stats are useful, but they should be expanded.

Recommended additions:

- report misses split into:
  - absent from both `regret_sum` and `strategy_sum`
  - present only in `regret_sum`
- track hit/miss rates per street and per history bucket
- log distinct-key coverage against each opponent type
- separate self-play stats from scripted-opponent stats instead of letting them accumulate into one file

## 7. Recommended next order of work

Recommended order:

1. update inference or training so regret-known states are not treated as missing
2. train with a mixed opponent pool
3. increase training iterations materially
4. re-check the miss histogram
5. only then decide whether the abstraction should be simplified or redesigned

## 8. Bottom line

The current problem is not mainly that `rich_hand_strength_v5` is malformed.

The bigger issues are:

- sparse training coverage
- a mismatch between what training updates and what inference reads
- evaluation against an aggressive scripted opponent that reaches branches self-play rarely covers

So the best next step is not immediately "invent a new abstraction."

The best next step is:

- fix policy lookup behavior
- broaden training opponents
- train longer
- then reassess whether abstraction complexity is still the bottleneck
