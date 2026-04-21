# V3 abstraction postmortem

This note explains why the V3 abstraction still appears unsuccessful despite adding richer features, and why only a small fraction of the theoretical state space was visited after 10,000 games.

## Executive summary

V3 fixed several real weaknesses in V2, but it over-corrected.

Compared with V2, V3:

- reduced some important aliasing
- added pressure, SPR, and opponent identity information
- made history and board representation richer

But it also:

- exploded the theoretical state space from `11,520` to `645,120`
- spread training samples too thin across too many buckets
- improved some matchups while failing on the main target, the threshold agent
- still saturated on new-state discovery relative to the new design

The result is that V3 is **more expressive**, but not **better allocated**.

## Observed outcomes

### V2 mixed training snapshot

The strongest V2 mixed setup used:

- mixed opponents
- exploration tuning
- about `1,910` visited policy states in the final v2 policy file
- total-gain roughly in the mid-`15%` range relative to the V2 abstraction size

Performance was roughly:

- threshold around high-20% win rate
- random much stronger than threshold
- self / advanced CFR moderate

### V3 results

V3 final policy file:

- `regret_sum`: `12,725`
- `strategy_sum`: `12,725`

Theoretical state count:

- `645,120`

Reported result after 10,000 games:

- total-gain around `1.68%`
- threshold win rate still around `26.9%`
- random performance dropped relative to V2
- self-play and advanced CFR improved

This is the key failure pattern:

- V3 discovered more absolute states than V2
- but the state space expanded so much that sample efficiency worsened
- threshold exploitation did not improve materially

## Why V3 still looks bad

## 1. State-space growth outpaced information value

V2 state size:

- `4 * 6 * 8 * 15 * 2 * 2 = 11,520`

V3 state size:

- `4 * 7 * 10 * 18 * 2 * 4 * 4 * 4 = 645,120`

This is about **56x larger**.

That increase came from adding:

- finer hand buckets
- finer board buckets
- larger history bucket system
- pressure bucket
- SPR bucket
- opponent bucket

Each change individually makes sense, but their product is too large for 10,000-game tabular CFR training.

### Why this matters

Tabular CFR depends on revisiting information states enough times to estimate regrets well.

When the state space grows too fast:

- regrets become noisy
- many buckets stay under-trained
- policy quality becomes uneven
- exploitation learning slows down

This is a classic abstraction allocation problem: adding dimensions does not help if each dimension fragments the sample support too much.

## 2. Opponent bucket is helpful conceptually, but expensive in practice

V3 added opponent identity to the abstraction.

That is directionally correct because the correct exploit policy can differ by opponent type. However, it multiplies the whole state space by `4`:

- self
- threshold
- random
- advanced CFR

This means the same public situation is now split into four separate learning tables.

### Why this is expensive

The threshold-exploitation problem was not that the learner had **no** distinction at all. The main problem was that it lacked the **right strategic distinctions**.

Adding opponent identity helps, but not enough to justify a full 4x split of every state when the training budget is still only 10,000 games.

A cheaper alternative would have been:

- separate exploit-focused training runs per target opponent, or
- a smaller opponent-style feature, or
- maintaining separate evaluation schedules without multiplying the whole tabular state

## 3. V3 still over-splits some low-value regions

The V3 history representation is more expressive than V2, but it is still a handcrafted bucket system.

This means it can still fail in both directions:

- merge important exploit distinctions
- split unimportant rare sequences

Even though V3 added more sequence structure, the design still relies on categorical compression rather than a compact set of high-signal betting features.

That makes it easy to create many rare state combinations without guaranteeing better exploitability.

## 4. Pressure and SPR were correct additions, but too expensive when multiplied together

Pressure bucket and SPR bucket were good ideas.

But V3 added both of them as independent dimensions:

- `pressure_bucket`: 4
- `spr_bucket`: 4

Together they already multiply the space by `16`.

This would be justified if:

- they created very stable exploit-relevant separation, and
- the training data volume were much larger

But with tabular training at this scale, they probably create too many finely split stack/pot situations that are not revisited often enough.

A more efficient approach would combine them into one smaller commitment/pressure feature.

## 5. The board abstraction got richer, but may still not target threshold-specific mistakes

V3 expanded board buckets from `8` to `10`.

That helps general texture recognition, but may still not capture the exact features that matter for exploiting the threshold player. For example:

- whether the board strongly favors top-pair over draws
- whether there are paired-overcard pressure spots
- whether the threshold player overfolds or overcalls on specific runouts

In other words, V3 may be more descriptive, but not necessarily more exploit-targeted.

## 6. V3 likely improved generic strategic sharpness more than exploit specialization

This matches the result pattern:

- self-play got better
- advanced CFR matchup improved
- random got worse than V2
- threshold barely moved

That suggests V3 learned a more internally consistent strategy in a richer state representation, but not one that became substantially better at exploiting the threshold heuristic.

This is common when a representation becomes more equilibrium-like but less sample-efficient for opponent-specific exploitation.

## What the visited-state results mean

The user observation is important:

> 10,000 games only visited around 2% of the states

That is not just because the abstraction is huge. It also means:

- many states are effectively unreachable under the training policies
- many states are reachable but extremely rare
- the abstraction is over-fragmented relative to the actual game trajectories

So the raw visited-state fraction is not merely "small because denominator big". It is also evidence that the abstraction is not well matched to the training distribution.

## Comparison with prior V2 experience

### What V2 got right

- small enough to revisit states frequently
- stronger random exploitation
- better sample efficiency
- easier to stabilize regret updates

### What V2 got wrong

- pot abstraction much too coarse
- history abstraction too compressed in exploit-relevant spots
- no opponent-aware distinction
- threshold exploitation bottlenecked by aliasing

### What V3 fixed

- more pressure awareness
- more sequence awareness
- opponent differentiation
- some reduction of harmful aliasing

### What V3 broke

- too much sparsity
- too many rarely revisited buckets
- too much denominator inflation
- weaker data efficiency for tabular learning

The lesson is not that V2 was good and V3 was bad.

The lesson is:

- **V2 was under-specified**
- **V3 was over-specified**
- the next design should be **compact but pressure-aware**

## Research-aligned interpretation

This matches common CFR and poker abstraction lessons:

1. **abstraction quality is not about more buckets, but about preserving decision-relevant distinctions**
2. **tabular CFR becomes sample-inefficient when the abstraction grows faster than revisit counts**
3. **action abstraction and state abstraction must control branching, otherwise the effective game becomes too sparse**
4. **many successful poker systems use carefully chosen compact abstractions or subgame solving rather than a naive large tabular product space**

External references reviewed for context:

- overviews of CFR emphasize that information-set design is central to practical performance in large poker games
- poker AI systems like Cepheus, DeepStack, and Libratus rely heavily on abstraction, decomposition, or localized solving because raw tabular expansion is infeasible
- practical success in poker AI comes from balancing abstraction fidelity with tractable revisit density, not simply increasing feature count

## What to improve next

## 1. Build a compact V3.1, not a larger V4

The next abstraction should be **smaller than V3**, not larger.

Target principle:

- keep the useful ideas from V3
- remove multiplicative dimensions that do not pay for themselves

## 2. Replace separate pressure and SPR buckets with one compact commitment bucket

Instead of:

- 4 pressure buckets
- 4 SPR buckets

Use one combined feature with maybe 4 or 5 values representing:

- low pressure / deep
- moderate pressure / medium
- high pressure / shallow
- all-in-like commitment

This preserves the signal with much lower multiplicative cost.

## 3. Remove opponent bucket from the main tabular state

The 4x multiplier is too expensive.

Alternatives:

- train threshold-focused runs separately
- maintain separate policy files per target opponent family
- use evaluation routing instead of state-space splitting

If opponent-awareness is kept, it should be much cheaper than a full global split.

## 4. Simplify history into a few high-signal features instead of 18 categorical buckets

Use compact features such as:

- current street raise count bucket
- prior aggression present or absent
- facing aggression or checked-to
- re-raise present or absent

These often capture more useful structure with fewer combinations than handcrafted large categorical enums.

## 5. Keep richer pressure representation, but coarsen board and hand slightly if needed

The biggest gain likely comes from preserving pressure/commitment context.

If the state space must shrink, it is probably better to:

- keep pressure-aware features
- keep a compact history signal
- slightly reduce board/hand granularity

rather than dropping pressure and keeping large texture buckets.

## 6. Track practical reachability metrics

Add metrics like:

- unique states discovered in the last 500 games
- reachable-state gain under the current opponent pool
- state revisit histogram
- top most visited states

This will help distinguish:

- healthy concentration on important states
- pathological collapse onto too few states
- fragmentation into too many low-data states

## Recommended next abstraction size

A better next target is something closer to the `20k` to `80k` range, not `645k`.

That range is still much larger than V2, but small enough that 10,000 to 20,000 games can revisit states meaningfully.

Example shape idea:

- street: 4
- hand bucket: 6
- board bucket: 8
- history features collapsed to 8 or 10 effective categories
- position: 2
- commitment bucket: 4

This would give something on the order of:

- `4 * 6 * 8 * 10 * 2 * 4 = 15360`

or with one extra compact feature:

- `4 * 6 * 8 * 10 * 2 * 4 * 2 = 30720`

That is much more realistic for tabular training.

## Bottom line

V3 failed because it improved the abstraction in the right directions but at the wrong scale.

It is not just that only ~2% of states were visited. The deeper problem is:

- too many dimensions were multiplied together
- training support per state became too low
- the added detail did not translate into better threshold exploitation

So the next design should not be "more detailed".

It should be **more selective**:

- preserve pressure and sequence information
- cut multiplicative fragmentation
- optimize for revisit density and exploit-relevant distinctions

That is the most likely path to improving threshold performance without collapsing sample efficiency.
