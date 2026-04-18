# Design Note: From Raw Engine Input to Decisions

This note compares:

- [condition_threshold_player.py](../condition_threshold_player.py)
- [simplified_advanced_cfr_player.py](../simplified_advanced_cfr/simplified_advanced_cfr_player.py)

The goal is to understand:

1. what `valid_actions`, `hole_card`, and `round_state` look like
2. how each player transforms those raw inputs
3. what the abstraction component is
4. how abstraction is used in rule-based and hybrid rule-plus-learned agents

This is written with the next design goal in mind:

- building a stronger rule-based poker agent with a good abstraction

## 1. The Raw Input From PyPokerEngine

Both players receive the same three inputs inside `declare_action(...)`:

- `valid_actions`
- `hole_card`
- `round_state`

## 2. Representative Real Example

The following is a real preflop example recorded from the simplified player trace.

### `valid_actions`

```python
[
  {"action": "fold"},
  {"action": "call"},
  {"action": "raise"}
]
```

Meaning:

- `fold`: give up the hand
- `call`: match the current bet
- `raise`: put in more chips than the current bet

### `hole_card`

```python
["H6", "S8"]
```

Meaning:

- heart 6
- spade 8

These are private cards only the player sees.

### `round_state`

```python
{
  "action_histories": {
    "preflop": [
      {
        "action": "SMALLBLIND",
        "add_amount": 10,
        "amount": 10,
        "uuid": "spbjjmwjepfpadkqpdgbpi"
      },
      {
        "action": "BIGBLIND",
        "add_amount": 10,
        "amount": 20,
        "uuid": "sqtmneqyaiwcmaiokhdjvv"
      }
    ]
  },
  "big_blind_pos": 1,
  "community_card": [],
  "dealer_btn": 1,
  "next_player": 0,
  "pot": {
    "main": {
      "amount": 30
    },
    "side": []
  },
  "round_count": 2,
  "seats": [
    {
      "name": "player_a",
      "stack": 500,
      "state": "participating",
      "uuid": "spbjjmwjepfpadkqpdgbpi"
    },
    {
      "name": "player_b",
      "stack": 470,
      "state": "participating",
      "uuid": "sqtmneqyaiwcmaiokhdjvv"
    }
  ],
  "small_blind_amount": 10,
  "small_blind_pos": 0,
  "street": "preflop"
}
```

Key meaning:

- `street`: current phase of the hand
- `community_card`: public board cards
- `pot`: current chips available to win
- `seats`: each player stack and status
- `dealer_btn`: who has button position
- `action_histories`: all public actions so far

## 3. What Both Players Do First

Even though the agents look different, they start with very similar low-level extraction.

Both compute or use:

- current street
- whether raising is allowed
- amount needed to call
- pot size
- own stack
- some estimate of hand strength
- some notion of position

The shared idea is:

- raw poker engine input is too detailed and awkward
- a player needs a smaller decision summary first

That summary is already a form of abstraction.

## 4. ConditionThresholdPlayer: Lightweight Rule Abstraction

The rule-based player does not build an explicit tuple key, but it still performs abstraction.

### Main decision flow

From [condition_threshold_player.py](../condition_threshold_player.py):

```python
street = round_state["street"]
can_raise = any(action["action"] == "raise" for action in valid_actions)
to_call = self._amount_to_call(round_state)
pot_size = self._pot_size(round_state)
stack = self._my_stack(round_state)

equity = self._estimate_equity(hole_card, round_state)
adjusted_equity = equity + self._position_bonus(round_state) + self._board_pressure_adjustment(
    street, to_call, stack
)

raise_threshold, call_threshold = self._street_thresholds(street)
raise_threshold, call_threshold = self._adjust_for_opponent(raise_threshold, call_threshold)
raise_threshold, call_threshold = self._adjust_for_price(
    raise_threshold, call_threshold, to_call, pot_size, stack
)
```

### What is the abstraction here?

For this player, the abstraction is not one explicit object. It is an implicit summary made from:

- `equity`
- `adjusted_equity`
- `street`
- `to_call`
- `pot_size`
- `stack`
- opponent aggression
- position bonus

So the rule-based player compresses raw state into a few decision features, then uses thresholds.

### Preflop abstraction

Preflop it does not simulate outcomes. Instead it uses a handcrafted hand-strength heuristic:

- pair bonus
- high-card bonus
- suited bonus
- connector bonus
- weak-hand penalties

This means the player does not reason over exact cards directly. It converts cards into a single score:

- `equity` or preflop strength score

That score is already an abstraction.

### Postflop abstraction

Postflop, it uses Monte Carlo win-rate estimation:

```python
estimate_hole_card_win_rate(...)
```

Again, it reduces:

- hole cards
- community cards

into one number:

- estimated winning probability

So the rule player’s abstraction is:

- mostly continuous scalar summaries
- not a discrete table key

### Final decision style

The rule player then does:

- if strong enough for raise threshold: `raise`
- else if strong enough for call threshold: `call`
- else: `fold`

This is a threshold policy over abstracted features.

## 5. SimplifiedAdvancedCFRPlayer: Explicit Table Abstraction

The simplified CFR player starts with the same backbone as the rule player:

- `to_call`
- `pot_size`
- `stack`
- `equity`
- position
- pressure
- opponent behavior

But then it adds one major component:

- an explicit information-state abstraction key

### Main flow

The simplified player does:

1. compute opponent stats
2. compute a rule-based `base_action`
3. build `info_key`
4. look up learned `average_strategy`
5. use learned action only when confidence is high enough

Relevant code:

```python
aggression, fold_rate = _opponent_stats(self, round_state)
base_details = _baseline_action(self, valid_actions, hole_card, round_state, aggression, fold_rate)
base_action = base_details["action"]

info_key, info_features = _build_info_set(self, hole_card, round_state)
average_strategy = _normalize_average_strategy(self._strategy_sum.get(info_key, {}), legal_actions)
```

### What is the abstraction here?

The abstraction is explicit and discrete.

It is built in:

- [../simplified_advanced_cfr/abstraction.py](../simplified_advanced_cfr/abstraction.py)

The key is:

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

So instead of keeping the full raw state, the player maps it into:

- street bucket
- strength bucket
- made-hand bucket
- draw bucket
- board-texture bucket
- position
- pot-odds bucket
- pressure bucket
- SPR bucket
- compressed public history

This tuple is the abstraction.

## 6. Same Raw Input, Different Use

The easiest way to compare the two players is this:

### ConditionThresholdPlayer

Uses raw input to build:

- a few continuous features

Then decides directly with rules.

Pipeline:

```text
raw input -> hand strength / pot / position / opponent aggression -> thresholds -> action
```

### SimplifiedAdvancedCFRPlayer

Uses raw input to build:

- the same rule features
- plus a discrete abstraction key

Then decides with:

- base rule action
- optional learned override from table

Pipeline:

```text
raw input -> rule features -> base_action
raw input -> abstract info_key -> learned average_strategy
base_action + learned strategy -> final action
```

## 7. Concrete Example: Same Raw State Through Both Players

Use the earlier real preflop input:

```python
valid_actions = [{"action": "fold"}, {"action": "call"}, {"action": "raise"}]
hole_card = ["H6", "S8"]
street = "preflop"
pot_size = 30
to_call = 10
stack = 500
```

### ConditionThresholdPlayer view

It extracts:

- hand strength around `0.305`
- opponent aggression default `0.25`
- position effect
- betting price effect

Then it compares that to thresholds like:

- raise threshold around `0.7346`
- call threshold around `0.49`

Since `0.305` is below both, the rule player would typically:

- `fold`

### SimplifiedAdvancedCFRPlayer view

It computes a very similar baseline:

- same rough strength
- same price and pressure
- same baseline thresholds

So its `base_action` is also:

- `fold`

But then it also computes:

```python
info_key = "(0, 3, 0, 0, 0, 0, 1, 0, 5, '')"
```

and looks up:

```python
average_strategy = {
  "fold": 0.0432,
  "call": 0.1178,
  "raise": 0.8390
}
```

Since learned `raise` confidence is high, it overrides:

- base action `fold`
- final action `raise`

This example shows the main design difference:

- rule player stops at abstraction-for-thresholds
- simplified CFR player continues from abstraction into learned lookup

## 8. What “Abstraction” Really Means Here

For poker agents in this repo, abstraction means:

- converting a huge complicated exact game state
- into a smaller strategically meaningful representation

Why this is needed:

- exact poker states are enormous
- most exact states are too rare to learn separately
- raw engine data is too messy to reason about directly

Good abstraction keeps:

- what matters for decision making

and drops:

- exact details that usually do not matter enough

### In the rule player

Abstraction is mostly:

- scalar summaries
- equity
- thresholds
- pressure
- position

### In the simplified CFR player

Abstraction is:

- a compact discrete state key used to index learned policy

## 9. Which Design Is Better for a Strong Rule-Based Agent?

If your next goal is:

- build a better rule-based agent with good abstraction

then the most useful lesson is not “copy CFR”.

The useful lesson is:

- first design a better state summary
- then make your rules act on that summary

A good rule-based agent does not need a learned table if its abstraction is strong enough.

## 10. Suggested Design Direction for a Better Rule-Based Agent

If you want a stronger rule-based player, combine the best ideas from both agents.

### Keep from ConditionThresholdPlayer

- simple threshold-based decisions
- Monte Carlo postflop equity estimation
- opponent aggression adjustment
- price-sensitive play

### Borrow from SimplifiedAdvancedCFR abstraction

- explicitly track draws
- explicitly track board texture
- explicitly track SPR
- explicitly track public betting history
- use street-specific feature groups

### Practical new rule-based design

A good next design could use a feature object like:

```python
features = {
  "street": ...,
  "strength": ...,
  "made_hand": ...,
  "draws": ...,
  "texture": ...,
  "position": ...,
  "pot_odds": ...,
  "pressure": ...,
  "spr": ...,
  "aggression": ...,
  "fold_rate": ...,
  "history": ...,
}
```

Then write rules such as:

- on dry flop, top pair can value bet more often
- on coordinated flop, medium-strength hands call more and raise less
- with strong draw plus good pot odds, continue more often
- at low SPR, strong made hands commit more aggressively
- against passive opponents, bluff less and value bet more

This gives you:

- a rule-based agent
- but with a much richer abstraction than the current threshold player

## 11. Key Comparison Summary

### ConditionThresholdPlayer

- simpler
- easier to reason about
- abstraction is implicit
- action comes directly from thresholds

### SimplifiedAdvancedCFRPlayer

- more structured
- abstraction is explicit
- action comes from:
  - baseline rule policy
  - optional learned table override

### Main design lesson

The biggest upgrade is not necessarily learning.

The biggest upgrade is often:

- choosing better abstract features from the raw poker state

That is the right foundation for either:

- a better rule-based player
- or a future learned player
