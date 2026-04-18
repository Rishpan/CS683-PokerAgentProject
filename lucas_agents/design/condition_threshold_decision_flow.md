# ConditionThresholdPlayer Decision Flow

This note breaks down how raw poker engine inputs become an action in:

- `lucas_agents/condition_threshold_player.py`
- `lucas_agents/simplified_advanced_cfr/simplified_advanced_cfr_player.py`

The main question is:

- how `ConditionThresholdPlayer.declare_action(...)` turns `valid_actions`, `hole_card`, and `round_state` into `fold` / `call` / `raise`
- whether `_baseline_action(...)` in the simplified CFR player uses the same logic

Short answer:

- yes, `_baseline_action(...)` is mostly the same rule-based logic
- no, it is not exactly identical
- the biggest differences are:
  - `_baseline_action(...)` gets `aggression` and `fold_rate` as inputs instead of reading aggression from the class state directly
  - `_baseline_action(...)` uses fewer postflop Monte Carlo simulations
  - `_baseline_action(...)` lowers the raise threshold when opponents fold more often
  - `_baseline_action(...)` returns a detail dictionary, not just the action string

## 0. Three Key Ideas: Equity, Aggression, Price

Before reading the flow, it helps to define the three ideas the rule agent uses most:

### Equity

In this code, `equity` means:

- an estimate of how often this hand would win if the rest of the hand were played out

You can think of it as:

- "how strong is my hand in this situation?"

But more precisely, it is not just raw card beauty. It is:

- hand strength relative to the current board
- relative to the number of players still active
- relative to the current street

Examples:

- preflop, `AA` has very high equity
- preflop, `72o` has low equity
- on the flop, top pair might have medium or high equity depending on the board
- on the river, a made flush may have very high equity unless the board is dangerous

In this repo:

- preflop equity is a handcrafted strength score
- postflop equity is estimated by Monte Carlo simulation

So yes, in plain language, equity mostly means:

- how strong the hand is right now

But the more exact meaning is:

- how likely the hand is to win from this state

### Aggression

`aggression` means:

- how often the opponent raises compared with all of their observed actions

Formula:

```text
aggression = raises / (raises + calls + folds)
```

High aggression means:

- the opponent raises a lot
- their bets are less likely to always mean a monster hand

Low aggression means:

- the opponent raises rarely
- when they do show strength, it is more believable

The agent uses aggression to shift thresholds:

- against aggressive opponents:
  - raise less often
  - call more often
- against passive opponents:
  - raise more often
  - call a bit less often

Reason:

- versus aggressive players, folding too much is exploitable
- versus passive players, raises often represent stronger ranges

### Price

`price` here means:

- how expensive it is to continue in the hand

It is mainly represented by:

- `to_call`: how many chips must be paid now to continue
- `pot_odds`: how much must be paid compared to the pot you can win
- `stack_ratio`: how large that payment is relative to your remaining stack

Formula:

```text
pot_odds = to_call / (pot_size + to_call)
```

Interpretation:

- small `to_call` into a large pot = good price
- large `to_call` into a small pot = bad price

So "price" answers:

- "how costly is it to keep playing?"

And the rule agent responds by becoming:

- looser when the price is cheap
- tighter when the price is expensive

## 0.1 Simple Intuition

The decision logic is basically trying to answer:

```text
Is my hand strong enough for how expensive this situation is,
after adjusting for position and opponent style?
```

That is why these three pieces matter:

- `equity` = hand quality
- `aggression` = what the opponent’s betting style means
- `price` = cost of continuing

## 1. Raw Inputs

Both rule paths start from:

- `valid_actions`
- `hole_card`
- `round_state`

### `valid_actions`

This is only used to answer one practical question:

- can this player legally `raise` right now?

The code does:

```python
can_raise = any(action["action"] == "raise" for action in valid_actions)
```

So for the rule logic:

- if `"raise"` appears in `valid_actions`, raising is considered legal
- otherwise, the player can only end on `call` or `fold`

Important detail:

- this logic does not use the raise amount range inside `valid_actions`
- it only checks whether raise exists at all

### `hole_card`

This is the player’s private hand, for example:

```python
["HA", "DK"]
```

It is used to estimate hand strength:

- preflop: a deterministic heuristic score
- postflop: a Monte Carlo equity estimate

### `round_state`

This is the main public game state. The rule logic extracts:

- `street`
- pot size
- amount needed to call
- player stack
- seat position
- number of active players
- community cards
- public action history

## 2. ConditionThresholdPlayer: Full Rule Flow

Main entry:

- `ConditionThresholdPlayer.declare_action(...)`

Relevant code:

- [condition_threshold_player.py](/Users/xiaofanlu/Documents/github_repos/CS683-PokerAgentProject/lucas_agents/condition_threshold_player.py:28)

The flow is:

```text
raw input
-> extract street / can_raise / to_call / pot_size / stack
-> estimate equity
-> add small adjustments
-> build raise/call thresholds
-> compare adjusted_equity to thresholds
-> return raise / call / fold
```

## 3. Step By Step: ConditionThresholdPlayer

### Step 1: Read the street

```python
street = round_state["street"]
```

Possible values:

- `preflop`
- `flop`
- `turn`
- `river`

This matters because:

- the equity method changes
- the base thresholds change
- the simulation count changes
- board pressure can change on the river

### Step 2: Check whether raising is allowed

```python
can_raise = any(action["action"] == "raise" for action in valid_actions)
```

This creates a hard constraint:

- even if the hand is strong enough, the agent will not return `raise` if `raise` is not legal

### Step 3: Compute `to_call`

Helper:

- [condition_threshold_player.py](/Users/xiaofanlu/Documents/github_repos/CS683-PokerAgentProject/lucas_agents/condition_threshold_player.py:205)

Logic:

1. look only at the current street’s action history
2. find the largest committed amount on this street
3. find this player’s committed amount on this street
4. subtract

Formula:

```text
to_call = max(0, highest_amount_on_street - my_amount_on_street)
```

Interpretation:

- `to_call == 0`: checking is possible
- `to_call > 0`: calling costs chips

### Step 4: Compute pot size

Helper:

- [condition_threshold_player.py](/Users/xiaofanlu/Documents/github_repos/CS683-PokerAgentProject/lucas_agents/condition_threshold_player.py:199)

Formula:

```text
pot_size = main_pot + all_side_pots
```

This is later used for pot odds.

### Step 5: Compute own stack

Helper:

- [condition_threshold_player.py](/Users/xiaofanlu/Documents/github_repos/CS683-PokerAgentProject/lucas_agents/condition_threshold_player.py:187)

This finds the current player’s remaining stack from `round_state["seats"]`.

### Step 6: Estimate equity

Helper:

- [condition_threshold_player.py](/Users/xiaofanlu/Documents/github_repos/CS683-PokerAgentProject/lucas_agents/condition_threshold_player.py:79)

This is the main hand-strength estimate.

Plain-language meaning:

- `equity` is the agent’s estimate of how good the hand is in the current situation
- more exactly, it is an estimate of win probability from here

So:

- higher equity means the hand should continue more often
- lower equity means the hand should fold more often

#### Preflop case

If `street == "preflop"`, the code calls `_preflop_strength(...)`.

Helper:

- [condition_threshold_player.py](/Users/xiaofanlu/Documents/github_repos/CS683-PokerAgentProject/lucas_agents/condition_threshold_player.py:93)

It computes a score from:

- pair or non-pair
- high card values
- suitedness
- gap between the two ranks
- premium-card bonuses
- weak-hand penalty
- small position bonus

Base score:

```text
score = 0.35
```

Then it adds or subtracts terms such as:

- pair bonus: `0.25 + min(rank, 12) * 0.028`
- suited bonus: `+0.05`
- connector bonus: `+0.05`
- one-gap bonus: `+0.025`
- large-gap penalty: `-0.05`
- two-high-card bonus: `+0.06`
- Ace-high-with-good-kicker bonus: `+0.04`
- weak unsuited low-card penalty: `-0.07`
- position bonus: `+0.02`

Finally:

```text
equity = clamp(score, 0.0, 0.95)
```

So preflop equity is not a true probability from simulation. It is a handcrafted strength score.

#### Postflop case

If the street is `flop`, `turn`, or `river`, the code uses Monte Carlo rollout:

```python
estimate_hole_card_win_rate(...)
```

Inputs:

- active player count
- hole cards
- community cards
- street-dependent simulation count

Simulation counts:

- flop: `80`
- turn: `120`
- river: `160`
- fallback default: `64`

So postflop equity is an estimated win rate.

### Step 7: Add small equity adjustments

After raw equity is computed, the player adjusts it:

```python
adjusted_equity = equity + position_bonus + board_pressure_adjustment
```

#### Position bonus

Helper:

- [condition_threshold_player.py](/Users/xiaofanlu/Documents/github_repos/CS683-PokerAgentProject/lucas_agents/condition_threshold_player.py:172)

Rule:

- `+0.015` if the player has position
- `+0.0` otherwise

The position test is in:

- [condition_threshold_player.py](/Users/xiaofanlu/Documents/github_repos/CS683-PokerAgentProject/lucas_agents/condition_threshold_player.py:175)

#### Board pressure adjustment

Helper:

- [condition_threshold_player.py](/Users/xiaofanlu/Documents/github_repos/CS683-PokerAgentProject/lucas_agents/condition_threshold_player.py:164)

Rules:

- on the river: `-0.01`
- if `to_call / stack >= 0.3`: `-0.04`

Interpretation:

- river spots are treated slightly more cautiously
- large commitments relative to stack are treated more cautiously

### Step 8: Get the base street thresholds

Helper:

- [condition_threshold_player.py](/Users/xiaofanlu/Documents/github_repos/CS683-PokerAgentProject/lucas_agents/condition_threshold_player.py:129)

Base thresholds:

| Street | Raise threshold | Call threshold |
|---|---:|---:|
| preflop | 0.74 | 0.51 |
| flop | 0.70 | 0.46 |
| turn | 0.73 | 0.50 |
| river | 0.79 | 0.57 |

These are the default cutoffs before any contextual adjustment.

### Step 9: Adjust thresholds for opponent aggression

Helper:

- [condition_threshold_player.py](/Users/xiaofanlu/Documents/github_repos/CS683-PokerAgentProject/lucas_agents/condition_threshold_player.py:138)

First it computes aggression:

- [condition_threshold_player.py](/Users/xiaofanlu/Documents/github_repos/CS683-PokerAgentProject/lucas_agents/condition_threshold_player.py:223)

Formula:

```text
aggression = total_raises / total_actions
```

Opponent action counts are updated from callback messages in:

- [condition_threshold_player.py](/Users/xiaofanlu/Documents/github_repos/CS683-PokerAgentProject/lucas_agents/condition_threshold_player.py:66)

Default when no data exists:

- `aggression = 0.25`

Threshold rules:

- if `aggression >= 0.35`: `raise += 0.03`, `call -= 0.03`
- if `aggression <= 0.15`: `raise -= 0.02`, `call += 0.01`
- otherwise: no change

Interpretation:

- versus aggressive opponents: raise less, call lighter
- versus passive opponents: raise more, call a bit tighter

Why this changes the decision:

- if an opponent is aggressive, their betting range is wider, so the agent should not over-fold
- if an opponent is passive, their strong actions are more meaningful, so the agent should respect them more

In practice the threshold changes do this:

- aggressive opponent:
  - raise threshold goes up
  - call threshold goes down
  - result: fewer raises, more calls
- passive opponent:
  - raise threshold goes down
  - call threshold goes up
  - result: more raises, fewer medium-strength calls

### Step 10: Adjust thresholds for price

Helper:

- [condition_threshold_player.py](/Users/xiaofanlu/Documents/github_repos/CS683-PokerAgentProject/lucas_agents/condition_threshold_player.py:146)

If `to_call <= 0`, no price adjustment happens.

Otherwise compute:

```text
pot_odds = to_call / (pot_size + to_call)
stack_ratio = to_call / stack
```

Then:

- `call_threshold = max(call_threshold, pot_odds + 0.06)`
- `raise_threshold = max(raise_threshold, pot_odds + 0.18)`

Extra stack-pressure rules:

- if `stack_ratio >= 0.35`: `call += 0.07`, `raise += 0.05`
- elif `stack_ratio <= 0.08`: `call -= 0.02`

Interpretation:

- expensive calls should require stronger hands
- expensive raises should require even stronger hands
- very large commitments get extra caution
- very cheap calls become slightly easier

This is what "price" means in the code:

- how much must be paid to continue
- compared to the pot
- and compared to the remaining stack

So a good way to read this rule is:

- if the price is cheap, continue more often
- if the price is expensive, continue only with stronger hands

### Step 11: Final action decision

This is the final rule tree:

```python
if to_call == 0:
  if can_raise and adjusted_equity >= raise_threshold - 0.06:
    return "raise"
  return "call"

if can_raise and adjusted_equity >= raise_threshold:
  return "raise"
if adjusted_equity >= call_threshold:
  return "call"
return "fold"
```

Interpretation:

#### Case A: free decision (`to_call == 0`)

- if strong enough and raise is legal: `raise`
- otherwise: `call`

Note:

- here `call` effectively means check

#### Case B: calling costs chips (`to_call > 0`)

- if strong enough for the raise threshold and raise is legal: `raise`
- else if strong enough for the call threshold: `call`
- else: `fold`

This is the full rule-based agent.

## 4. `_baseline_action(...)`: Step By Step

Relevant code:

- [simplified_advanced_cfr_player.py](/Users/xiaofanlu/Documents/github_repos/CS683-PokerAgentProject/lucas_agents/simplified_advanced_cfr/simplified_advanced_cfr_player.py:284)

The structure is intentionally very close to `ConditionThresholdPlayer`.

It does:

```text
raw input
-> extract street / can_raise / to_call / pot_size / stack
-> estimate equity
-> add small adjustments
-> build thresholds
-> compare adjusted_equity to thresholds
-> produce baseline action
```

### Same parts

`_baseline_action(...)` uses the same overall rule shape for:

- `street`
- `can_raise`
- `to_call`
- `pot_size`
- `stack`
- preflop heuristic structure
- position bonus
- board pressure adjustment
- street threshold table
- price adjustment formula
- final branch ordering

### Important differences

It is not perfectly identical.

#### Difference 1: opponent stats come from parameters

Signature:

```python
_baseline_action(player, valid_actions, hole_card, round_state, aggression, fold_rate)
```

So instead of calling an internal method like `_opponent_aggression()`, it receives:

- `aggression`
- `fold_rate`

Those values are computed outside the function by:

- [simplified_advanced_cfr_player.py](/Users/xiaofanlu/Documents/github_repos/CS683-PokerAgentProject/lucas_agents/simplified_advanced_cfr/simplified_advanced_cfr_player.py:194)

That reconstruction reads public action history directly instead of relying on callback updates.

Also:

- `check` is counted like `call` in the simplified player’s opponent model
- the original `ConditionThresholdPlayer` only counts explicit `raise`, `call`, and `fold` callback actions

Default values when no history exists:

- `aggression = 0.25`
- `fold_rate = 0.18`

#### Difference 2: postflop simulations are smaller

In `_estimate_equity(...)` inside the simplified CFR file:

- flop: `48`
- turn: `48`
- river: `48`

In `ConditionThresholdPlayer`:

- flop: `80`
- turn: `120`
- river: `160`

Meaning:

- same logic family
- different precision and potentially different equity values

#### Difference 3: fold rate directly changes the raise threshold

After the standard threshold adjustments, `_baseline_action(...)` adds:

```python
raise_threshold -= 0.03 * fold_rate
```

This does not exist in `ConditionThresholdPlayer`.

Interpretation:

- if opponents fold more often, the baseline becomes slightly more willing to raise
- with the default `fold_rate = 0.18`, the raise threshold is lowered by `0.0054`

#### Difference 4: return value

`ConditionThresholdPlayer.declare_action(...)` returns just:

- `"raise"`
- `"call"`
- `"fold"`

`_baseline_action(...)` returns a dictionary containing:

- chosen action
- equity
- adjusted equity
- thresholds
- aggression
- fold rate
- pot and stack values
- hole cards
- valid actions

This is for tracing and debugging.

## 5. Are The Two Rule Logics The Same?

Best answer:

- same backbone
- same decision tree
- not the same exact policy

### Same backbone

They both follow this exact conceptual process:

1. derive cost and pot context from `round_state`
2. estimate hand equity from `hole_card` plus public cards
3. nudge equity with small situational bonuses/penalties
4. choose street-specific thresholds
5. adjust thresholds for opponent behavior and bet price
6. compare adjusted equity against the thresholds
7. return `raise`, `call`, or `fold`

### Not exactly the same policy

They can diverge because `_baseline_action(...)` changes inputs and parameters in two places:

1. its postflop equity estimate can differ because simulation counts are lower
2. its raise threshold is lowered by opponent `fold_rate`

So the strict answer is:

- `_baseline_action(...)` is not a verbatim copy
- it is a modified version of the same rule-based logic

## 6. Full Simplified CFR Player Flow

This matters because `_baseline_action(...)` is only the fallback logic, not the full final policy.

Relevant code:

- [simplified_advanced_cfr_player.py](/Users/xiaofanlu/Documents/github_repos/CS683-PokerAgentProject/lucas_agents/simplified_advanced_cfr/simplified_advanced_cfr_player.py:375)

Full flow:

```text
valid_actions, hole_card, round_state
-> compute opponent aggression/fold_rate
-> compute baseline rule action
-> build abstract info_key
-> look up learned average strategy
-> if learned action is different and confidence >= 0.72, override baseline
-> otherwise keep baseline
```

So:

- `ConditionThresholdPlayer` stops after the rule comparison
- `SimplifiedAdvancedCFRPlayer` keeps going and may override the rule action with a learned action

## 7. End-To-End Example

Suppose:

- `valid_actions = [{"action": "fold"}, {"action": "call"}, {"action": "raise"}]`
- `hole_card = ["H6", "S8"]`
- `street = "preflop"`
- current street history implies `to_call = 10`
- `pot_size = 30`
- `stack = 500`
- no strong opponent read yet

### ConditionThresholdPlayer

1. `can_raise = True`
2. `to_call = 10`
3. `pot_size = 30`
4. `stack = 500`
5. preflop heuristic gives a relatively weak score
6. small position/pressure adjustments are applied
7. start from preflop thresholds `(0.74, 0.51)`
8. opponent aggression defaults near neutral
9. price adjustment may raise the thresholds slightly
10. if adjusted equity stays below `call_threshold`, action becomes `fold`

### `_baseline_action(...)`

It does almost the same 10 steps.

Then one extra baseline-specific rule applies:

11. lower `raise_threshold` by `0.03 * fold_rate`

If that reduction is not enough to cross the raise threshold, the action still stays `fold`.

## 8. Practical Summary

If your goal is to understand the rule-based decision process, use this mental model:

```text
hole_card + round_state
-> estimate strength
-> estimate how expensive it is to continue
-> estimate whether position helps
-> estimate whether opponent style should shift thresholds
-> compare adjusted strength against raise/call cutoffs
-> choose raise / call / fold
```

And for the direct comparison:

```text
ConditionThresholdPlayer
= pure threshold-based rule agent

_baseline_action in simplified CFR
= almost the same threshold-based rule agent
+ uses aggression/fold_rate inputs from reconstructed history
+ uses lower postflop simulation counts
+ slightly encourages raising when opponents fold more
```

## 9. Bottom Line

`ConditionThresholdPlayer` is a rule-based threshold agent.

It turns raw engine input into a few decision variables:

- equity
- adjusted equity
- to-call cost
- pot odds
- stack pressure
- position
- opponent aggression
- raise/call thresholds

Then it chooses:

- `raise` if adjusted equity clears the raise threshold
- else `call` if adjusted equity clears the call threshold
- else `fold`

`_baseline_action(...)` uses the same step-by-step structure, but it is not exactly the same implementation. The two biggest practical differences are:

- `_baseline_action(...)` uses different opponent-stat inputs
- `_baseline_action(...)` lowers the raise threshold using `fold_rate`

So if you want to understand the simplified CFR player’s rule backbone, you should think of `_baseline_action(...)` as:

- a near-copy of `ConditionThresholdPlayer`
- with a few parameter and calibration changes
- plus an outer learned-policy override in the full player

## 10. Direct Comparison: Same Or Better?

If you ignore the learned-policy override and compare only:

- `ConditionThresholdPlayer.declare_action(...)`
- `SimplifiedAdvancedCFRPlayer`'s `_baseline_action(...)`

then the right conclusion is:

- they are very similar
- they are not exactly the same
- from code inspection alone, neither is strictly better in all situations

### What is identical in spirit

They use the same rule backbone:

1. compute `to_call`, `pot_size`, `stack`, `street`
2. estimate equity
3. add position and pressure adjustments
4. start from the same street threshold table
5. adjust thresholds for aggression
6. adjust thresholds for price
7. use the same final decision tree:
   - raise if strong enough for raise threshold
   - else call if strong enough for call threshold
   - else fold

So at the design level, they are the same kind of player.

### What is not identical

There are three meaningful differences.

#### 1. `_baseline_action(...)` uses fold rate

It applies:

```python
raise_threshold -= 0.03 * fold_rate
```

That means:

- if opponents fold more often, `_baseline_action(...)` becomes slightly more willing to raise
- `ConditionThresholdPlayer` does not have this adjustment

So baseline is usually a little more bluff-friendly or pressure-friendly.

#### 2. `_baseline_action(...)` uses fewer postflop simulations

`ConditionThresholdPlayer` postflop simulations:

- flop: `80`
- turn: `120`
- river: `160`

`_baseline_action(...)` postflop simulations:

- flop: `48`
- turn: `48`
- river: `48`

That means:

- `ConditionThresholdPlayer` should usually have a more stable postflop equity estimate
- `_baseline_action(...)` should usually be faster, but slightly noisier

So if "better" means more accurate postflop equity estimation, `ConditionThresholdPlayer` is likely better.

#### 3. opponent stats are collected differently

`ConditionThresholdPlayer`:

- updates opponent stats through callback events

`_baseline_action(...)` path:

- reconstructs opponent stats from public action history each time
- also treats `check` as similar to `call` in the opponent totals

That means the two agents can see slightly different aggression values from the same match history.

### Practical behavior difference

If you compare only the rule policies, the most likely behavioral summary is:

- `ConditionThresholdPlayer` is slightly more conservative and slightly more stable postflop
- `_baseline_action(...)` is slightly more aggressive because it reduces raise threshold using `fold_rate`

### Which is better?

Without running head-to-head matches, the safest answer is:

- neither is universally better
- they are close variants of the same policy

But if you force a code-based judgment:

- `ConditionThresholdPlayer` is better if you value cleaner and more stable rule evaluation
- `_baseline_action(...)` is better if the extra fold-rate adjustment really captures profitable raise opportunities against folding opponents

### Final verdict

So the best short answer is:

- they are not the same
- they are very close
- `_baseline_action(...)` is a slightly modified and slightly more aggressive version of `ConditionThresholdPlayer`
- from code alone, I would not claim `_baseline_action(...)` is clearly better
- if anything, `ConditionThresholdPlayer` looks more reliable as a pure rule-based agent, while `_baseline_action(...)` looks more exploitative
