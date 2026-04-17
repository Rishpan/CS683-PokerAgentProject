# Simplified Advanced CFR: Input, Transformation, and Action Selection

This note explains what the simplified agent receives in `declare_action()`, how that raw input is transformed into decision features such as `aggression` and `fold_rate`, how `base_action` is chosen, and how the agent tracks whether it used the base policy or the learned CFR policy.

The runtime player is:

- [simplified_advanced_cfr_player.py](./simplified_advanced_cfr_player.py)

The local abstraction module used by inference is:

- [abstraction.py](./abstraction.py)

The persistent runtime artifacts are:

- [advanced_cfr_policy.json](./advanced_cfr_policy.json)
- [inference_stats.json](./inference_stats.json)
- [latest_decision_trace.json](./latest_decision_trace.json)

## What `declare_action()` Receives

Every decision from the poker engine provides:

- `valid_actions`: what the engine currently allows
- `hole_card`: the agent's private two cards
- `round_state`: the full public game state at this point in the hand

Typical `valid_actions` in this engine look like:

```python
[
  {"action": "fold"},
  {"action": "call"},
  {"action": "raise"}
]
```

Typical `hole_card` looks like:

```python
["H6", "S8"]
```

One real `round_state` example from the recorded trace looks like:

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

The most important fields inside `round_state` are:

- `street`: `"preflop"`, `"flop"`, `"turn"`, or `"river"`
- `community_card`: public board cards
- `pot`: current main pot and side pots
- `seats`: each player's stack and status
- `dealer_btn`: dealer/button position
- `small_blind_amount`: blind size
- `action_histories`: all public actions so far
- `next_player`: which seat acts next
- `round_count`: current hand number

## How Raw Input Becomes Decision Features

The simplified agent transforms the raw engine input in four stages.

### 1. Opponent history becomes `aggression` and `fold_rate`

The agent reconstructs opponent tendencies from `round_state["action_histories"]`.

- `aggression = opponent_raises / (opponent_raises + opponent_calls + opponent_folds)`
- `fold_rate = opponent_folds / (opponent_raises + opponent_calls + opponent_folds)`

If there is no opponent history yet, the defaults are:

- `aggression = 0.25`
- `fold_rate = 0.18`

This is done by:

- `_update_opponent_stats_from_history(...)`
- `_opponent_stats(...)`

### 2. Raw game state becomes betting context

The agent computes:

- `to_call`: how many chips are needed to continue
- `pot_size`: current pot
- `stack`: own remaining stack
- `position`: whether the player acts in position

These come from:

- `_amount_to_call(...)`
- `_pot_size(...)`
- `_my_stack(...)`
- `_has_position(...)`

### 3. Cards become strength features

The agent estimates:

- `equity`: preflop heuristic or Monte Carlo win rate postflop
- `adjusted_equity`: equity plus position and pressure adjustments

It also builds abstraction features:

- `strength`
- `draws`
- `made_hand`
- `texture`
- `pot_odds`
- `pressure`
- `spr`
- compressed `history`

These features are packed into an `info_key` used to look up the saved average CFR strategy.

### 4. The rule-based baseline becomes `base_action`

The baseline policy computes:

- `raise_threshold`
- `call_threshold`

Those thresholds are adjusted by:

- opponent aggression
- fold rate
- pot odds
- stack pressure

Then the baseline chooses:

- if `to_call == 0`: usually `call`, but `raise` if the hand is strong enough
- if facing a bet: `raise`, `call`, or `fold` depending on `adjusted_equity` versus thresholds

This is done inside `_baseline_action(...)`.

## How Final Action Is Chosen

The simplified agent does not always use the learned CFR table.

It first computes:

- `base_action`
- `info_key`
- `average_strategy` from the saved policy

Then it applies this rule:

- if there is no learned strategy for this state, use `base_action`
- if there is a learned strategy but it is not confident, use `base_action`
- only use the learned action when:
  - learned best action is different from `base_action`
  - learned probability is at least `0.72`

So the final action is:

- `learned_action` only in high-confidence disagreements
- otherwise `base_action`

## One Real Game Run

I ran one actual game with:

```bash
python3 compare_agents.py \
  lucas_agents/simplified_advanced_cfr/simplified_advanced_cfr_player.py \
  lucas_agents/condition_threshold_player.py \
  --games 1 --max-round 25
```

Result:

- simplified agent won the game
- final stacks: `990` vs `0`

The saved runtime stats after that run were:

```json
{
  "base_action_used": 15,
  "by_street": {
    "flop": {
      "base": 6,
      "learned": 0
    },
    "preflop": {
      "base": 3,
      "learned": 8
    },
    "river": {
      "base": 2,
      "learned": 0
    },
    "turn": {
      "base": 4,
      "learned": 1
    }
  },
  "learned_action_used": 9,
  "total_decisions": 24
}
```

## Representative Decisions From That Game

### Preflop example

Raw input:

```python
valid_actions = [{"action": "fold"}, {"action": "call"}, {"action": "raise"}]
hole_card = ["H6", "S8"]
```

Important public state:

```python
street = "preflop"
pot_size = 30
to_call = 10
stack = 500
community_card = []
```

Derived values:

```python
aggression = 0.25
fold_rate = 0.18
equity = 0.305
adjusted_equity = 0.305
raise_threshold = 0.7346
call_threshold = 0.49
info_key = "(0, 3, 0, 0, 0, 0, 1, 0, 5, '')"
average_strategy = {
  "fold": 0.0432,
  "call": 0.1178,
  "raise": 0.8390
}
```

Decision:

- `base_action = "fold"`
- learned best action = `"raise"` with confidence `0.8390`
- final action = `"raise"`
- reason: learned policy disagreed with base policy and exceeded the `0.72` confidence gate

### Flop example

Raw input:

```python
hole_card = ["D4", "S2"]
community_card = ["H6", "HJ", "D9"]
```

Derived values:

```python
aggression = 0.25
fold_rate = 0.18
equity = 0.1875
adjusted_equity = 0.2025
raise_threshold = 0.6946
call_threshold = 0.46
average_strategy = null
```

Decision:

- `base_action = "call"`
- no learned strategy for that abstract state
- final action = `"call"`

### Turn example

Raw input:

```python
hole_card = ["D4", "S2"]
community_card = ["H6", "HJ", "D9", "S4"]
```

Derived values:

```python
aggression = 0.25
fold_rate = 0.18
equity = 0.4792
adjusted_equity = 0.4942
raise_threshold = 0.7246
call_threshold = 0.50
average_strategy = {
  "fold": 0.0172,
  "call": 0.1195,
  "raise": 0.8632
}
```

Decision:

- `base_action = "call"`
- learned best action = `"raise"` with confidence `0.8632`
- final action = `"raise"`

### River example

Raw input:

```python
hole_card = ["C9", "C8"]
community_card = ["DQ", "D4", "H6", "S6", "D9"]
```

Derived values:

```python
aggression = 0.25
fold_rate = 0.18
equity = 0.7708
adjusted_equity = 0.7608
raise_threshold = 0.7846
call_threshold = 0.57
average_strategy = null
```

Decision:

- `base_action = "raise"`
- no learned override
- final action = `"raise"`

## Where The Stats Are Saved

The player now persists two files inside this folder.

### `inference_stats.json`

Stores cumulative counts:

- total decisions
- how many times `base_action` was used
- how many times a learned action override was used
- per-street breakdown

### `latest_decision_trace.json`

Stores the most recent decision snapshots, including:

- raw `valid_actions`
- raw `hole_card`
- raw `round_state`
- derived values such as `aggression`, `fold_rate`, `info_key`, `average_strategy`
- `base_action`
- final chosen action
- whether the learned policy overrode the base policy

## When Stats Reset

The runtime stats are intentionally persistent across inference runs.

They reset only when a new offline training run starts through:

- [train_simplified_advanced_cfr.py](./train_simplified_advanced_cfr.py)

That trainer now clears:

- `inference_stats.json`
- `latest_decision_trace.json`

at the beginning of training.

## Practical Usage

To generate a fresh trace and updated stats:

```bash
python3 compare_agents.py \
  lucas_agents/simplified_advanced_cfr/simplified_advanced_cfr_player.py \
  lucas_agents/condition_threshold_player.py \
  --games 1 --max-round 25
```

Then inspect:

```bash
cat lucas_agents/simplified_advanced_cfr/inference_stats.json
cat lucas_agents/simplified_advanced_cfr/latest_decision_trace.json
```

## Handcrafted vs Learned Parameters

The current simplified agent is a hybrid:

- a handcrafted baseline policy
- a learned CFR average-strategy table

So it is not fully hand-tuned and it is not fully learned either.

### What is currently handcrafted

The following parts are manually chosen constants or rules in the code.

In [simplified_advanced_cfr_player.py](./simplified_advanced_cfr_player.py):

- `STREET_THRESHOLDS`
  - preflop raise threshold `0.74`
  - preflop call threshold `0.51`
  - flop raise threshold `0.70`
  - flop call threshold `0.46`
  - turn raise threshold `0.73`
  - turn call threshold `0.50`
  - river raise threshold `0.79`
  - river call threshold `0.57`
- `STREET_SIMULATIONS`
  - flop `48`
  - turn `48`
  - river `48`
- default opponent priors
  - default `aggression = 0.25`
  - default `fold_rate = 0.18`
- confidence gate for learned override
  - learned action must have probability at least `0.72`
- position bonus
  - `_position_bonus(...) = 0.015`
- board pressure adjustments
  - river penalty `-0.01`
  - high stack-pressure penalty `-0.04`
- opponent adjustment rules
  - aggressive opponent threshold `0.35`
  - passive opponent threshold `0.15`
  - corresponding threshold shifts such as `+0.03`, `-0.03`, `-0.02`, `+0.01`
- pot-price adjustment rules
  - call threshold floor `pot_odds + 0.06`
  - raise threshold floor `pot_odds + 0.18`
  - high stack-ratio adjustment `+0.07`, `+0.05`
  - low stack-ratio adjustment `-0.02`
- preflop strength formula coefficients
  - base score `0.35`
  - pair bonus `0.25 + min(rank, 12) * 0.028`
  - high-card bonuses `0.045`, `0.03`
  - suited bonus `0.05`
  - connector / gap bonuses `0.05`, `0.025`
  - wide-gap penalty `-0.05`
  - broadway / ace-high bonuses `0.06`, `0.04`
  - weak-offsuit penalty `-0.07`
  - in-position preflop bonus `0.02`

In [abstraction.py](./abstraction.py):

- strength bucket count `12`
- pot-odds bucket count `6`
- pressure bucket count `6`
- SPR bucket count `6`
- made-hand bucket cutoffs
  - `0.42`, `0.56`, `0.72`, `0.88`
- draw encoding design
- board-texture encoding design
- history compression format

So in practice, the current runtime contains many handcrafted numbers. It is best thought of as:

- learned action table on top of
- handcrafted state representation and handcrafted fallback logic

### What is currently learned

The current learned component is:

- `strategy_sum` in [advanced_cfr_policy.json](./advanced_cfr_policy.json)

For each abstract information state `info_key`, the policy stores average action mass over:

- `fold`
- `call`
- `raise`

At inference time, this becomes:

- `average_strategy[fold]`
- `average_strategy[call]`
- `average_strategy[raise]`

Then the agent may use the learned best action if its confidence is high enough.

So the currently learned parameters are:

- the action preferences for each abstract state

The currently not-learned parameters are:

- thresholds
- bonuses
- penalties
- abstraction bucket boundaries
- confidence gate
- simulation counts

## How Many Things Are Handcrafted vs Learned

There is no single small parameter vector in the current design. Instead:

- the learned part is a large table indexed by `info_key`
- the handcrafted part is a collection of rule constants and bucket definitions

So the right way to think about parameter count is:

- handcrafted: dozens of explicit constants and rule cutoffs
- learned: potentially thousands of state-action table entries in the saved policy

That means most of the policy capacity is learned, but most of the policy structure is still handcrafted.

## How To Make More Of It Learnable

There are three progressively stronger ways to make this agent learn more over time.

### 1. Learn the baseline thresholds

Right now the baseline uses fixed thresholds such as:

- preflop raise threshold `0.74`
- flop call threshold `0.46`
- learned override gate `0.72`

These can be moved into a parameter file, for example:

```python
PARAMS = {
  "preflop_raise_threshold": 0.74,
  "preflop_call_threshold": 0.51,
  "flop_raise_threshold": 0.70,
  ...
}
```

Then offline training can update them based on match results.

Methods that work:

- random search
- grid search
- Bayesian optimization
- evolutionary strategies
- hill climbing

This is the simplest way to turn handcrafted logic into learnable logic.

### 2. Learn a weighted linear action scorer

Instead of rules like:

- if `adjusted_equity >= raise_threshold`, then raise

you can define per-action scores:

```python
score_raise = w0 + w1*strength + w2*pot_odds + w3*pressure + w4*position + w5*fold_rate
score_call  = ...
score_fold  = ...
```

Then choose the action with the highest score, or convert scores into probabilities.

This makes the following learnable:

- how much strength should matter
- how much pot odds should matter
- how much pressure should matter
- how much opponent aggression should matter
- how much position should matter

Methods that work:

- gradient-style updates on realized reward
- policy-gradient style updates
- regret-style updates
- contextual bandit updates

This is a good next step because it preserves interpretability while learning more than fixed thresholds.

### 3. Learn the abstraction or replace it with a function approximator

Right now the agent uses handcrafted buckets:

- strength bucket
- pot-odds bucket
- pressure bucket
- SPR bucket
- handcrafted draw bucket
- handcrafted board-texture bucket

A more learnable design would use:

- continuous features instead of hard buckets
- a small neural network
- a linear model with richer features
- clustering learned from self-play data

This would let the model learn which distinctions actually matter instead of forcing all bucket boundaries by hand.

## A Practical Learning Roadmap

If the goal is to keep the code simple but make it improve over time, the most practical progression is:

### Stage 1: Keep current runtime, tune constants offline

Keep:

- same `declare_action()`
- same abstraction
- same CFR table logic

Learn offline:

- street thresholds
- confidence gate
- opponent prior defaults
- pressure penalties

This is low-risk and easy to test.

### Stage 2: Replace hard thresholds with trainable weights

Keep:

- same input features
- same action set
- same tournament-safe inference structure

Learn:

- action scoring weights

This gives better adaptation while still being explainable.

### Stage 3: Learn both policy and representation

Keep:

- offline training only
- cheap inference at runtime

Learn:

- policy parameters
- representation / abstraction parameters

This is the strongest long-term direction, but also the biggest implementation jump.

## What Method Will Make It Improve Over Time

If you want a concrete answer for "what method should I use so handcrafted parameters learn and get better over time?", the best options are:

### Best simple option

Offline parameter search over the handcrafted constants.

Example loop:

1. Start from current handcrafted constants.
2. Generate a slightly modified parameter set.
3. Train or evaluate against an opponent pool.
4. Keep the new set if performance improves.
5. Repeat.

Good algorithms:

- hill climbing
- random search
- evolutionary search

This is easy to implement and works surprisingly well for poker heuristics.

### Best medium-complexity option

Train a linear action-value or action-score model on top of the current features.

Use features such as:

- `strength`
- `pot_odds`
- `pressure`
- `spr`
- `position`
- `draws`
- `texture`
- `aggression`
- `fold_rate`

Then learn one weight vector per action.

This is a strong balance between:

- simplicity
- learnability
- explainability
- fast inference

### Best closest-to-current option

Keep the current CFR table, but also make the baseline parameters trainable.

That means:

- keep learned `strategy_sum`
- tune thresholds and penalties offline

This is the least disruptive extension of the current agent.

## Important Constraint for Class Submission

For the course requirement, live training should not happen while choosing actions.

So any learning method should be:

- done offline before submission
- saved to file
- loaded at runtime for fast inference

That means:

- tune parameters offline
- save them in JSON
- have `declare_action()` only read and use them

This keeps the runtime tournament-safe while still allowing the agent to get better over repeated training runs.
