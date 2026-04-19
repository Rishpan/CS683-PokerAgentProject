# CFR Update Explanation

This note explains how the simplified CFR-style update in
[cfr.py](./cfr.py) works.

It focuses on these questions:

1. what is stored during a hand
2. whether all visited abstract states are saved
3. what happens when the hand ends
4. how picked and non-picked actions are updated
5. what `setdefault(...)` is doing
6. how action utility is estimated
7. how `round_reward` is calculated
8. why `round_reward` is not the raw chip loss

This implementation is **not exact full-tree CFR**. It is a compact,
state-based approximation that:

- stores every visited abstract state during play
- waits until the hand finishes
- uses the final hand reward plus local state features
- updates regret rows for each visited abstract state


## 1. The Main Objects

In `cfr.py`, the main tables are:

```python
self.regret_sum = {}
self.strategy_sum = {}
self.round_decisions = []
```

Meaning:

- `regret_sum[info_key][action]`
  - cumulative regret for one action in one abstract state
- `strategy_sum[info_key][action]`
  - running total of how much probability mass the policy has assigned to that action in that abstract state
- `round_decisions`
  - all abstract states visited by the player during the current hand


## 2. What Is an `info_key`?

The abstraction compresses the raw poker state into:

```python
(street_index, strength_bucket, history_bucket, pot_odds_bucket)
```

Example:

```python
(1, 4, 6, 0)
```

This might mean:

- `street_index = 1`: flop
- `strength_bucket = 4`: medium-ish hand strength
- `history_bucket = 6`: earlier aggression, current street still quiet/passive
- `pot_odds_bucket = 0`: cheap or free to continue

That tuple is the abstract state. In the CFR table it is stored as:

```python
info_key = repr(info_state)
```


## 3. What Does `setdefault(...)` Do?

The code:

```python
regrets = self.regret_sum.setdefault(info_key, _zero_action_map())
average = self.strategy_sum.setdefault(info_key, _zero_action_map())
```

does **not** change `info_key`.

It only means:

1. if `info_key` already exists in the table, return its row
2. if it does not exist, create a new row with zeros and return it

So if this state has never appeared before:

```python
self.regret_sum[info_key] = {
    "fold": 0.0,
    "call": 0.0,
    "raise": 0.0,
}
```

Why this is needed:

- the CFR table is sparse
- not every abstract state appears in every game
- the first time a state appears, we need somewhere to store regret and strategy values

Without `setdefault(...)`, the code would need explicit initialization checks every time:

```python
if info_key not in self.regret_sum:
    self.regret_sum[info_key] = _zero_action_map()
```


## 4. What Happens During a Hand?

Each time the player acts:

1. `declare_action(...)` builds the abstract state
2. `strategy(...)` reads or creates its regret row
3. a strategy over `fold/call/raise` is computed
4. one action is picked
5. `record_decision(...)` saves that state visit into `round_decisions`

So yes:

**all visited abstract states during that hand are saved**

Example if the player acts 3 times in one hand:

```python
self.round_decisions = [
    {
        "info_key": "(0, 6, 2, 3)",
        "legal_actions": ("call", "fold", "raise"),
        "chosen_action": "call",
        "features": {
            "street": "preflop",
            "strength": 0.61,
            "history": 2,
            "pot_odds": 0.22,
        },
    },
    {
        "info_key": "(1, 4, 6, 0)",
        "legal_actions": ("call", "fold", "raise"),
        "chosen_action": "raise",
        "features": {
            "street": "flop",
            "strength": 0.43,
            "history": 6,
            "pot_odds": 0.00,
        },
    },
]
```


## 5. What Happens When the Hand Ends?

At the end of the hand, the trainer computes a final normalized reward.

Example:

- won chips: `+0.6`
- lost chips: `-0.5`

Then:

```python
for decision in self.round_decisions:
    self._update_regrets(decision, normalized_reward)
```

So yes:

**when one hand finishes, the code goes back over all saved abstract states from that hand and updates each one**

It does not only update the final state.


## 6. How One State Is Updated

Inside `_update_regrets(...)`, the code does:

```python
regrets = self.regret_sum.setdefault(decision["info_key"], _zero_action_map())
utilities = _action_utilities(...)
node_value = average utility over legal actions
for action in decision["legal_actions"]:
    regrets[action] += utilities[action] - node_value
```

### Meaning of `utilities[action]`

This is the estimated value of taking that action in that abstract state.

It uses:

- strength
- pot odds
- history bucket
- final hand reward

The utility is produced by `_action_utilities(...)` in `cfr.py`.

That function is a compact heuristic, not an exact solver. It says:

- `fold`
  - usually has a negative value because you give up the pot
  - folding strong hands is punished more than folding weak hands
- `call`
  - gets better when strength is high
  - gets worse when pot odds are bad
  - is scaled by street importance
- `raise`
  - starts from the `call` value
  - gets extra reward when strength is high
  - pays a small aggression cost
- `history`
  - adjusts whether aggression should look more or less attractive in this public line
- `chosen_action`
  - gets extra credit or blame from the actual final hand reward

In code form, the rough structure is:

```python
utilities["fold"] = -0.20 - 0.40 * max(0.0, strength - 0.5)
utilities["call"] = street_weight * (strength - max(0.10, pot_odds)) + 0.35 * round_reward
utilities["raise"] = utilities["call"] + 0.18 * strength - 0.08
```

Then history adjusts the action values:

```python
if history in {1, 3, 6}:
    utilities["raise"] += 0.05
elif history in {4, 5, 7}:
    utilities["raise"] -= 0.08
    utilities["call"] -= 0.03
```

Then the chosen action gets direct credit or blame from the realized outcome:

```python
utilities[chosen_action] += 0.45 * round_reward
```

So utility is updated from two sources:

1. local abstract-state features
2. the final result of the hand

### Meaning of `node_value`

This is the baseline value of the state itself.

In this simplified implementation:

```python
node_value = average of legal action utilities
```

Then regret is updated as:

```python
regret[action] += utility[action] - node_value
```

Interpretation:

- if an action is better than the state's baseline, regret goes up
- if an action is worse than baseline, regret goes down


## 7. Example: One State Update

Suppose one saved decision has:

```python
info_key = "(1, 4, 6, 0)"
legal_actions = ("fold", "call", "raise")
chosen_action = "call"
round_reward = +0.6
```

Assume `_action_utilities(...)` gives:

```python
utilities = {
    "fold": -0.30,
    "call": 0.12,
    "raise": 0.18,
}
```

Because the chosen action was `call`, the code adds a chosen-action bonus:

```python
utilities["call"] += 0.45 * round_reward
```

So:

```python
utilities = {
    "fold": -0.30,
    "call": 0.39,
    "raise": 0.18,
}
```

Now compute:

```python
node_value = (-0.30 + 0.39 + 0.18) / 3 = 0.09
```

Regret updates:

```python
regret["fold"]  += -0.30 - 0.09 = -0.39
regret["call"]  +=  0.39 - 0.09 = +0.30
regret["raise"] +=  0.18 - 0.09 = +0.09
```

### What this means

- `fold` looked clearly worse than baseline
- `call` looked best in this state
- `raise` also looked better than baseline, but not as much as `call`

So on later visits to this same abstract state, regret matching will move the strategy toward `call`, then `raise`, and away from `fold`.


## 8. How `round_reward` Is Calculated

`round_reward` is not the raw chip gain/loss.

The trainer computes:

```python
chip_delta = final_stack - round_start_stack
normalizer = max(small_blind_amount * 4, 1)
round_reward = max(-1.0, min(1.0, float(chip_delta) / normalizer))
```

So the workflow is:

1. remember your stack at the start of the hand
2. read your stack at the end of the hand
3. compute chip change
4. divide by a fixed scale based on blinds
5. clamp into `[-1.0, 1.0]`

### Example

Suppose:

- start stack = `500`
- end stack = `480`
- `small_blind_amount = 10`

Then:

```python
chip_delta = 480 - 500 = -20
normalizer = 10 * 4 = 40
round_reward = -20 / 40 = -0.5
```

That is why the note uses `-0.5`.

It means:

- the player lost 20 chips
- which is half of the chosen reward scale of 40 chips

### Why not use the raw lost money?

Because raw chip values create unstable learning.

If the code used raw chip deltas directly:

- one very large pot could dominate many smaller hands
- regret values would grow with stack size instead of strategy quality
- training would become sensitive to blind structure and game settings

The normalized reward fixes that by keeping the signal on a small, comparable scale.

Benefits:

- values stay numerically stable
- a hand in one training run is comparable to a hand in another
- the chosen-action bonus stays controlled
- regret updates do not explode after one all-in hand

So `-0.5` is not pretending the player literally lost 0.5 chips.
It means:

> this hand was moderately bad relative to the training reward scale


## 9. Picked Action vs Not Picked Actions

This is the important part:

**the code updates all legal actions, not only the chosen one**

That means:

- chosen action regret is updated
- non-chosen legal action regrets are also updated

Why?

Because regret learning asks:

> compared with the state's baseline value, which actions appear better or worse?

Even if only one action was actually taken, the code still estimates values for the alternatives.

### How the chosen action is special

The chosen action gets extra credit or blame from the actual hand result:

```python
if chosen_action in legal_actions:
    utilities[chosen_action] += 0.45 * round_reward
```

So:

- if the hand went well, the chosen action gets a boost
- if the hand went badly, the chosen action gets penalized

### How non-chosen actions are updated

They do not get that chosen-action bonus.

Their regret still changes because:

```python
regret[action] += utility[action] - node_value
```

So they are updated from their estimated utility relative to the state baseline.


## 10. Example: Multiple States in One Hand

Suppose one hand has 2 decisions by the player.

### State 1: Preflop

```python
info_key = "(0, 6, 2, 3)"
chosen_action = "call"
```

### State 2: Flop

```python
info_key = "(1, 4, 6, 0)"
chosen_action = "raise"
```

Suppose the hand result is:

```python
round_reward = -0.5
```

The code updates both states separately.

### Update for State 1

Suppose:

```python
utilities = {
    "fold": -0.10,
    "call": -0.20,
    "raise": -0.05,
}
```

Then:

```python
node_value = (-0.10 - 0.20 - 0.05) / 3 = -0.1167
```

Regret increments:

```python
fold  += -0.10 - (-0.1167) = +0.0167
call  += -0.20 - (-0.1167) = -0.0833
raise += -0.05 - (-0.1167) = +0.0667
```

Interpretation:

- preflop `call` looked worse than average
- preflop `raise` looked best

### Update for State 2

Suppose:

```python
utilities = {
    "fold": -0.25,
    "call": -0.08,
    "raise": -0.30,
}
```

Then:

```python
node_value = (-0.25 - 0.08 - 0.30) / 3 = -0.21
```

Regret increments:

```python
fold  += -0.25 - (-0.21) = -0.04
call  += -0.08 - (-0.21) = +0.13
raise += -0.30 - (-0.21) = -0.09
```

Interpretation:

- on the flop, `call` looked better than average
- on the flop, `raise` looked worse than average

So one hand can push different abstract states in different directions.


## 11. Why Utility Uses Both Local Features and Final Reward

This is an important design choice.

If the update used only the final hand result:

- every state in the hand would get nearly the same signal
- early-state and late-state decisions would be hard to separate

If the update used only local features:

- the learner would ignore whether the hand actually succeeded or failed

So the code mixes both:

- local features tell the model what kind of state this is
- final reward tells the model whether the actual hand outcome was good or bad

That is why two states in the same hand can get different regret updates even though they share the same final reward:

- they have different strengths
- different pot odds
- different history buckets
- different chosen actions


## 12. How Strategy Is Built from Regret Later

Later, when the same abstract state appears again, the code uses regret matching:

```python
positive[action] = max(regret[action], 0.0)
```

Suppose cumulative regrets for one state are:

```python
{
    "fold": -1.4,
    "call": 0.8,
    "raise": 2.4,
}
```

Then only positive regrets matter:

```python
{
    "fold": 0.0,
    "call": 0.8,
    "raise": 2.4,
}
```

Normalized into a strategy:

```python
fold  = 0.0
call  = 0.8 / 3.2 = 0.25
raise = 2.4 / 3.2 = 0.75
```

So the next time that abstract state is visited, the policy strongly prefers `raise`.


## 13. Summary

Yes, the code saves all visited abstract states during a hand.

Yes, when the hand ends, it goes back through those saved states and updates each one.

The picked action:

- is updated like every other legal action
- also gets extra reward or penalty from the real hand result

The non-picked legal actions:

- are also updated
- based on their estimated utilities relative to the state baseline

The update rule is:

```python
regret[action] += utility[action] - node_value
```

Over many hands:

- states where `raise` often looks best accumulate positive raise regret
- states where `call` looks best accumulate positive call regret
- states where `fold` is safest stop assigning much probability to aggressive actions

That is how the abstract policy becomes different for different abstract states.
