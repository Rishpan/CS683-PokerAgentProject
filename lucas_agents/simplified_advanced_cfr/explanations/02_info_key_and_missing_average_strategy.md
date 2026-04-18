# Why `average_strategy` Can Be `null`, and What `info_key` Means

This note explains two related questions:

1. why some decisions have `average_strategy = null`
2. what the `info_key` tuple means, entry by entry

## Why `average_strategy` Can Be `null`

In the simplified player, runtime `average_strategy` is computed by:

```python
def _normalize_average_strategy(action_map, legal_actions):
  total = 0.0
  filtered = {}
  for action in ACTIONS:
    value = float(action_map.get(action, 0.0)) if action in legal_actions else 0.0
    filtered[action] = value
    total += value
  if total <= 0:
    return None
  return {action: filtered[action] / total for action in ACTIONS}
```

So `average_strategy` becomes `null` when:

- there is no saved entry for that `info_key`, or
- all saved values for the legal actions are zero

In practice, the usual reason is:

- this abstract state has not been learned enough
- or has never been visited during training

So your interpretation is correct:

- yes, `average_strategy = null` usually means this state did not get useful learned policy mass in the saved table

Then the simplified player falls back to:

- `base_action`

## Why Preflop Example Showed `info_key` and Flop Example Did Not

That was just a documentation inconsistency in the earlier explanation, not a logic difference.

Every decision state gets an `info_key`, including:

- preflop
- flop
- turn
- river

The flop state also had an `info_key`; it just was not highlighted earlier.

For example, the recorded flop example had:

```python
info_key = "(1, 0, 0, 0, 2, 1, 0, 0, 5, '/')"
```

So:

- preflop has an `info_key`
- flop has an `info_key`
- turn has an `info_key`
- river has an `info_key`

The only difference is whether that `info_key` exists in the learned policy with nonzero strategy mass.

## Where `info_key` Comes From

The simplified player builds it in:

- [../abstraction.py](../abstraction.py)

The key code is:

```python
key = (
    features["street_index"],
    _bucket(strength, 12),
    features["made_hand"],
    features["draws"],
    features["texture"],
    position,
    _bucket(pot_odds, 6),
    _bucket(pressure, 6),
    _bucket(min(spr, 4.0) / 4.0, 6),
    features["history"],
)
```

So `info_key` is a compact abstract state representation. It does not store the full raw `round_state`. It stores a bucketed summary of the strategically important parts.

## Meaning of Each Entry in `info_key`

Suppose we have this preflop key:

```python
info_key = "(0, 3, 0, 0, 0, 0, 1, 0, 5, '')"
```

This tuple has 10 entries.

### Entry 1: `street_index`

From:

```python
STREET_INDEX = {"preflop": 0, "flop": 1, "turn": 2, "river": 3}
```

So:

```python
0 = preflop
1 = flop
2 = turn
3 = river
```

For the example:

```python
0
```

means:

- this is a preflop state

### Entry 2: `_bucket(strength, 12)`

This is the hand strength bucket.

The bucket helper is:

```python
def _bucket(value, bucket_count):
  clipped = max(0.0, min(value, 0.999999))
  return min(int(clipped * bucket_count), bucket_count - 1)
```

So if:

```python
strength = 0.305
bucket_count = 12
```

then:

```python
int(0.305 * 12) = int(3.66) = 3
```

So the second entry:

```python
3
```

means:

- hand strength fell into bucket 3 out of 12

### Entry 3: `made_hand`

This is a coarse made-hand category:

```python
def _made_hand_bucket(strength, street):
  if street == "preflop":
    return 0
  if strength >= 0.88:
    return 4
  if strength >= 0.72:
    return 3
  if strength >= 0.56:
    return 2
  if strength >= 0.42:
    return 1
  return 0
```

For preflop:

```python
0
```

always means:

- no postflop made-hand category is used yet

### Entry 4: `draws`

Beginner meaning:

- a "draw" means your hand is **not strong yet**, but it is **close to becoming strong** if a helpful future card appears

Two common draw types are:

- flush draw: you have 4 cards of the same suit and want a 5th
- straight draw: your cards are close to forming 5 consecutive ranks

This entry is a draw bucket from `_draw_bucket(...)`.

For preflop:

```python
0
```

because there is no board yet.

For postflop it encodes:

- flush draw presence
- straight draw presence

Why this matters:

- if you have a strong draw, calling or raising can make sense even if your hand is not currently made yet
- if you have no draw and no made hand, folding becomes more attractive

Simple intuition:

- `0` means "not developing toward anything obvious"
- larger values mean "more ways this hand could improve soon"

### Entry 5: `texture`

Beginner meaning:

- "board texture" means what the **community cards look like together**
- some boards are dry and simple
- some boards are dangerous because they can help many hands

Examples:

- a paired board like `K K 4` has one kind of texture
- a connected board like `8 9 T` has another
- a two-suit board like `H6 HJ D9` can support flush draws

This entry is board texture from `_board_texture_bucket(...)`.

For preflop:

```python
0
```

because there is no community board.

Postflop it summarizes things like:

- paired board
- two-tone suit texture
- broadway-heavy board
- connected board

Why this matters:

- a dangerous board means opponents can easily have strong hands or strong draws
- a quiet board means medium hands are safer

So board texture changes how careful or aggressive the agent should be.

### Entry 6: `position`

This is:

```python
1 if in position else 0
```

In the example:

```python
0
```

means:

- out of position

Beginner meaning:

- "position" means whether you act **later** or **earlier** than your opponent in the betting round
- acting later is better because you get to see what the opponent does first

So:

- `1` means in position: the agent acts later
- `0` means out of position: the agent acts earlier

Why this matters:

- acting later gives more information
- because of that, players can usually play a bit more aggressively in position and more carefully out of position

### Entry 7: `_bucket(pot_odds, 6)`

Beginner meaning:

- "pot odds" means the price you are getting to continue
- it compares:
  - how much you must put in now
  - versus how much you can win from the pot

This buckets pot odds.

In the example:

```python
pot_odds = to_call / (pot_size + to_call) = 10 / (30 + 10) = 0.25
int(0.25 * 6) = 1
```

So:

```python
1
```

means:

- pot odds were in bucket 1 out of 6

Why this matters:

- if the price to call is cheap compared with the pot, calling becomes easier to justify
- if the price is expensive, the hand needs to be stronger

Simple intuition:

- low pot odds = cheap to continue
- high pot odds = expensive to continue

### Entry 8: `_bucket(pressure, 6)`

Beginner meaning:

- "pressure" here means how painful the current call is relative to your remaining stack

Pressure is:

```python
pressure = to_call / stack
```

In the example:

```python
pressure = 10 / 500 = 0.02
int(0.02 * 6) = 0
```

So:

```python
0
```

means:

- very low stack pressure

Why this matters:

- calling 10 chips out of a 500-chip stack is easy
- calling 200 chips out of a 500-chip stack is a much bigger commitment

So pressure tells the agent whether this decision is small and flexible, or large and dangerous.

### Entry 9: `_bucket(min(spr, 4.0) / 4.0, 6)`

Beginner meaning:

- SPR stands for "stack-to-pot ratio"
- it asks: compared with the pot, how deep are the remaining stacks?

SPR means:

```python
spr = stack / pot_size = 500 / 30 = 16.67
```

But it is clipped:

```python
min(16.67, 4.0) / 4.0 = 1.0
```

Then bucketed:

```python
int(1.0 * 6) -> capped to 5
```

So:

```python
5
```

means:

- very high effective SPR bucket

Why this matters:

- high SPR means there is a lot of money left behind compared with the pot
- low SPR means stacks are shallow and hands often become more direct: strong hands want to commit, weak hands want to get out

Simple intuition:

- high SPR = lots of room for future betting decisions
- low SPR = the hand is getting close to all-in type commitment

In this abstraction, very large SPR values are clipped together, so:

- all "very deep" situations share the same top bucket

### Entry 10: `history`

This is a compressed public action-history string.

Example encoding:

- `r` = raise
- `c` = call or check
- `f` = fold

For the preflop example:

```python
''
```

means:

- no betting actions beyond blinds had yet been compressed into the current state string

For later streets, examples look like:

- `'/'`
- `'//'`
- `'///'`

Each slash separates streets.

Important clarification:

- entry 10 is **not just the street**
- the street is already entry 1
- entry 10 is supposed to represent the **pattern of public betting actions so far**

For example, in principle:

- `'rc'` could mean raise then call on the current street
- `'cc/r'` could mean call-call preflop, then raise on flop

However, in the current implementation and current saved policy, the observed history strings are only:

- `''`
- `'/'`
- `'//'`
- `'///'`

Why?

Because the compression code checks lowercase action names like:

```python
if move == "raise":
elif move in ("call", "check"):
elif move == "fold":
```

but the engine trace often stores actions in uppercase like:

- `CALL`
- `RAISE`
- `SMALLBLIND`
- `BIGBLIND`

So with the current code, most action letters are not actually being recorded into the history string, and what remains is mostly only the street separators.

So in the current saved policy:

- entry 10 mostly tells you how far through the hand you are
- it does **not** yet fully capture the public betting pattern

That is weaker than intended.

## Full Meaning of the Preflop Example

Now we can decode:

```python
(0, 3, 0, 0, 0, 0, 1, 0, 5, '')
```

as:

1. `0`: preflop
2. `3`: strength bucket 3/12
3. `0`: no postflop made-hand bucket
4. `0`: no draw bucket
5. `0`: no board texture yet
6. `0`: out of position
7. `1`: pot odds bucket 1/6
8. `0`: low pressure bucket
9. `5`: very high SPR bucket
10. `''`: no compressed action string yet

## Flop Example Decoded

The recorded flop example had:

```python
info_key = "(1, 0, 0, 0, 2, 1, 0, 0, 5, '/')"
```

This means:

1. `1`: flop
2. `0`: very weak strength bucket
3. `0`: no meaningful made-hand bucket
4. `0`: no draw bucket
5. `2`: board texture bucket value 2
6. `1`: in position
7. `0`: zero pot-odds bucket because `to_call = 0`
8. `0`: zero pressure bucket
9. `5`: still high SPR bucket
10. `'/'`: one street separator, representing prior public history compression up to flop

## Why `info_key` Matters

The key idea is:

- the learned table is not stored for every exact raw `round_state`
- it is stored for abstract buckets

That means many different real poker situations can map to the same `info_key`.

This is necessary because:

- exact poker states are too many
- learning per exact raw state would be too sparse

So `info_key` is the bridge between:

- rich raw engine input
- compact learnable policy table

## Beginner Summary of Entries 4-10

If you are new to poker, the easiest way to read entries 4-10 is:

- entry 4 `draws`: "am I close to improving into a strong hand?"
- entry 5 `texture`: "does the board look dangerous or easy?"
- entry 6 `position`: "do I act before or after the opponent?"
- entry 7 `pot_odds`: "is it cheap or expensive to continue?"
- entry 8 `pressure`: "how big is this call compared with my stack?"
- entry 9 `spr`: "how much money is still left behind for future betting?"
- entry 10 `history`: "what public betting pattern have we seen so far?"

These are important because poker decisions are not only about your cards. They are also about:

- how expensive the decision is
- whether the board is dangerous
- whether you act with more or less information
- whether the hand is still deep or nearly committed

Two hands with the same card strength can be played very differently if these entries are different.

## How Many Possible Abstract States Are There?

Using the current abstraction design, a coarse upper bound is:

- street: `4`
- strength bucket: `12`
- made-hand bucket: `5`
- draw bucket: `5`
- texture bucket: `16`
- position: `2`
- pot-odds bucket: `6`
- pressure bucket: `6`
- SPR bucket: `6`
- history strings currently observed: `4`

Upper bound:

```text
4 * 12 * 5 * 5 * 16 * 2 * 6 * 6 * 6 * 4 = 829,440
```

So the current abstraction can represent up to about:

- `829,440` abstract states

This is only an upper bound.

Many of those combinations are impossible or meaningless, for example:

- preflop cannot have real board texture
- preflop cannot have real draw categories
- some bucket combinations never occur in real play

So the number of reachable states is lower than `829,440`.

## How Many States Are Covered by the Saved Policy?

I counted the saved policy entries in:

- [../advanced_cfr_policy.json](../advanced_cfr_policy.json)

The file currently contains:

- `9,594` `strategy_sum` states

So the saved table covers:

```text
9594 / 829440 ≈ 1.16%
```

of the coarse upper-bound state space.

That does **not** necessarily mean the policy is bad, because:

- many abstract states are unreachable
- many abstract states are extremely rare
- good performance may come from covering only the important regions

But it does explain why:

- some states have learned strategy
- some states return `average_strategy = null`

## Is a Table Enough, or Do We Need a Neural Network?

Short answer:

- for this current simplified project, a table can be enough to get a working agent
- but a table alone will remain sparse unless the abstraction is very small or training is very large

### Why a table can be enough

Advantages:

- simple
- easy to inspect
- easy to debug
- deterministic and explainable
- fits the course requirement well

If the abstraction is compact and well-designed, a table can work surprisingly well.

### Why a table can become insufficient

The problem is sparsity:

- many states are possible
- only some are visited enough during training
- unseen states fall back to `base_action`

So a pure table does not generalize well to nearby unseen states.

Example:

- if the agent learned one flop state with strength bucket `5`
- and a very similar flop state appears with strength bucket `6`
- the table treats them as completely different keys

A neural network or another function approximator can help because it can share learning across similar states.

### Do you need a neural network right now?

For this codebase, not necessarily.

A better first step is often:

1. keep the table
2. improve the abstraction
3. fix the history encoding issue
4. train longer or against a broader opponent pool

That is lower risk and much easier to explain.

### When a neural network becomes worth it

A neural network becomes more attractive if:

- you want more generalization across similar states
- the table stays too sparse
- you want to replace hard buckets with continuous features
- you are comfortable with more complex training and debugging

### Practical recommendation

For this project, the best recommendation is:

- keep the table for now
- fix and improve the abstraction first
- only move to a neural network if you find the table remains too sparse after that

So the answer is:

- table is enough for a solid, understandable baseline
- neural network is useful later if you want stronger generalization beyond covered states

## Short Answer to Your Two Questions

### Why was flop `average_strategy = null`?

Most likely because:

- that flop `info_key` had no nonzero saved `strategy_sum`

So yes:

- it likely means that state was not learned enough, or never visited enough during training

### Why did preflop show `info_key` but flop seemed not to?

That was only a presentation issue in the earlier note.

Both streets have `info_key`.

The real difference is:

- preflop key had learned strategy mass
- the shown flop key did not
