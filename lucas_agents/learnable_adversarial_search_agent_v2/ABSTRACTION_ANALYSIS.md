# Learnable Adversarial Search Agent V2, abstraction analysis

This note explains why V2 coverage/state-gain saturates early and why threshold-agent exploitation improves slowly.

## Current abstraction

The V2 abstract state is:

- `street`: 4 buckets
- `hand_bucket`: 6 buckets
- `board_bucket`: 8 buckets
- `history_bucket`: 15 buckets
- `position`: 2 buckets
- `pot_bucket`: 2 buckets

Total theoretical states: `4 * 6 * 8 * 15 * 2 * 2 = 11520`

State tuple:

```python
(street, hand_bucket, board_bucket, history_bucket, position, pot_bucket)
```

## Main diagnosis

The abstraction is not purely "bad", but it is **misallocated**:

- **too coarse in exploit-relevant dimensions**
- **too fine in dimensions that inflate the state count without adding enough decision value**
- **missing some opponent-pressure and betting-sequence details that matter against the threshold agent**

That combination naturally causes:

- repeated revisits to the same abstract states
- state-gain dropping to near zero
- decent generic strength vs random
- only modest improvement vs threshold

## Where the abstraction is too coarse (too loose)

These are the places where strategically different situations are likely collapsing into the same bucket.

### 1. `pot_bucket` is far too coarse

Current design:

- bucket 0: small pot / small call amount
- bucket 1: `pot_size >= 120` or `to_call >= 40`

This is probably the single loosest part of the abstraction.

Why it hurts:

- medium pots and huge pots are merged
- cheap calls and high-commitment calls often merge once the threshold is crossed
- stack-to-pot pressure is barely represented

That means these very different spots can share one state:

- early turn with comfortable stack depth
- river facing a big polarizing bet
- near-commitment jam-like pressure spots

Against a threshold player, those differences matter a lot. If they are merged, the learner can only learn an averaged response.

### 2. `history_bucket` compresses too many betting sequences

The history abstraction uses 15 handcrafted categories. It mainly tracks:

- number of raises
- some check/raise patterns
- some pressure conditions
- some coarse street-specific patterns

This is useful, but still too lossy.

Likely collapse examples:

- min-raise then call vs raise-call-raise lines
- delayed aggression vs immediate aggression
- one-raise lines with very different pot sizes
- same raise count but different actor order and initiative transitions

Threshold agents are often exploitable based on **exact action timing and pressure progression**. Collapsing too many lines into the same history bucket makes it hard to learn those exploit responses.

### 3. `board_bucket` is too coarse for postflop exploitation

Board bucket has only 8 values and is determined by broad traits like:

- flushiness
n- connectedness
- high board / low board
- paired board

This is reasonable for generic play, but too coarse for learning targeted postflop exploit behavior.

Example collisions:

- dry ace-high board and coordinated ace-high board may both map similarly under the broad rules
- weak paired boards and strong paired boards can get collapsed
- monotone danger and paired-trips danger are not separated enough

If the threshold agent reacts strongly to specific board textures, V2 may not preserve those distinctions.

### 4. `hand_bucket` is too coarse near decision boundaries

There are only 6 hand-equity buckets.

This means many "close call / close fold / thin raise" situations get merged together, especially:

- medium-strength bluff catchers
- weak top-pair type spots
- draw-heavy medium equity hands

These boundary regions are often exactly where exploitative improvements come from.

### 5. No opponent-model feature is in the state

The training now uses mixed opponents, but the abstract state does not encode opponent identity or behavior summary.

So the same state can represent:

- a random opponent spot
- a threshold opponent spot
- an advanced CFR spot

That forces one shared policy bucket to serve multiple opponent types. This is especially bad for exploitation, because the correct exploit action may differ by opponent even when public state looks similar.

## Where the abstraction is too fine

These are the places where the state count may be larger than useful learning support.

### 1. The product space overstates meaningful reachability

`11520` states exist on paper, but many are likely:

- rarely reachable
- reachable only through strange action combinations
- not meaningful under the actual opponent pool

So the denominator is large, but a lot of those states may never matter much.

This makes state-gain appear poor even when practical learning is happening.

### 2. `history_bucket` may still be too split in low-value regions

Although history is too coarse in some exploit-relevant places, it can also be too split in less important places.

For example, separate buckets for lines that are strategically similar but rarely visited can produce:

- many low-data buckets
- unstable regret updates
- inflated total state count without enough revisit density

So history is simultaneously:

- too coarse where precision matters
- too fine where data is sparse

That is a classic bad abstraction allocation pattern.

### 3. `street x board x history x position x pot` multiplies sparse combinations

Even if each factor is individually sensible, the Cartesian product creates many combinations that get little support.

Example:

- a rare river history bucket
- on a niche board bucket
- with one pot bucket
- from one position

This may generate state IDs that are technically distinct but not statistically learnable.

## Why visited-state gain goes to zero

The near-zero new-state gain is likely caused by all of these together:

1. **policy-induced trajectory concentration**
   - once the learner stabilizes, it visits a narrow repeated subgraph

2. **opponent-policy concentration**
   - threshold and learned opponents produce repeated betting lines

3. **state aliasing in important places**
   - genuinely different real states are counted as the same abstract state

4. **too many low-value theoretical states**
   - many abstract states exist but are not practically visited

This means the learner is still training, but mostly refining previously seen abstract buckets.

## Why threshold win rate improves more slowly than random win rate

The random opponent is easy to exploit with broad, generic strength learning.

The threshold opponent is harder because:

- its mistakes are more structured
- exploiting it often requires recognizing specific pressure patterns
- those patterns are only partially represented in the current abstraction

So V2 can get stronger in a general sense while still failing to learn sharper threshold-specific counterplay.

## Most likely abstraction problems, ranked

### Highest priority problems

1. **Pot/pressure representation is too coarse**
2. **History representation loses too much exact sequence information**
3. **No opponent-aware state information**
4. **Board texture buckets are too broad for exploit learning**

### Secondary problems

5. **Theoretical state count includes many low-value combinations**
6. **Hand buckets are too coarse around marginal decision regions**

## Recommended fixes

## 1. Replace `pot_bucket` with a richer pressure representation

Instead of 2 buckets, use several buckets for:

- `to_call / stack`
- `to_call / pot`
- SPR (stack-to-pot ratio)
- pot-size bucket

Example:

- pressure bucket: 4 or 5 levels
- SPR bucket: 3 or 4 levels

This should help more than adding raw game count.

## 2. Redesign `history_bucket`

Instead of only 15 handcrafted categories, represent a short action signature such as:

- current street raise count
- prior street raise count
- whether last aggressive action came from opponent or self
- whether current node is facing aggression, unopened, or in a checked-to spot
- whether the line included a re-raise

This preserves exploit-relevant structure better.

## 3. Add opponent-type context during training

At minimum, include an opponent category feature in the training abstraction, for example:

- self
- threshold
- random
- advanced_cfr

Without this, one abstract policy is forced to average across incompatible opponent behaviors.

## 4. Refine board buckets where threshold exploitation matters

Possible additions:

- pairedness severity
- flush-draw severity
- straight-draw severity
- high-card concentration
- nut-advantage proxy

Not all are needed, but the current 8 buckets are probably too blunt.

## 5. Consider redistributing, not just increasing, bucket count

Do not only make the abstraction bigger.

Better approach:

- make `pot_bucket` and exploit-relevant history features finer
- make low-value sparse splits coarser

The goal is **better allocation**, not just more states.

## 6. Track reachable-state gain separately from total-state gain

Current total-state gain uses all 11520 theoretical states. That is useful but misleading.

Add another metric:

- reachable-state gain under the current opponent pool
- or rolling unique-state discovery in the last N games

That will better reflect whether training is actually exploring meaningful new territory.

## Bottom line

The current V2 abstraction likely suffers from both:

- **aliasing**: important exploit spots are merged too aggressively
- **sparsity inflation**: some theoretical distinctions increase the state space without enough training support

So yes, the symptoms you observed are consistent with:

- visiting the same abstract states too often
- not categorizing some strategically important states properly
- learning broad competence without enough targeted threshold exploitation

## Best next engineering step

If only one thing is changed first, it should be:

**replace the current 2-bucket pot abstraction and 15-bucket history abstraction with a more pressure-aware and sequence-aware representation**.

That is the most likely path to improving threshold exploitation and making new-state discovery more meaningful.
