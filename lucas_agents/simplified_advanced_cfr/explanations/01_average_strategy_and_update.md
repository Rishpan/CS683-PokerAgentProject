# How `average_strategy` Is Calculated

This note explains:

1. where `average_strategy` comes from
2. which code computes it
3. how one decision is turned into one training update
4. how that later becomes the `average_strategy` used by the simplified runtime

## Important Distinction

The simplified runtime player in:

- [../simplified_advanced_cfr_player.py](../simplified_advanced_cfr_player.py)

does **not** train online.

It only reads a saved policy file:

- [../advanced_cfr_policy.json](../advanced_cfr_policy.json)

The training logic that creates that policy comes from the stronger training player:

- [../../advanced_cfr/advanced_cfr_player.py](../../advanced_cfr/advanced_cfr_player.py)

So when you ask "how is `average_strategy` calculated?", the answer is:

- during training: the trainer updates `strategy_sum`
- during inference: the simplified player normalizes the saved `strategy_sum` for the current `info_key`

## The Two Relevant Tables

In the training player, two main tables are stored per `info_key`:

- `regret_sum`
- `strategy_sum`

Meaning:

- `regret_sum[info_key][action]` tracks cumulative regret for each action
- `strategy_sum[info_key][action]` tracks how much probability mass has been assigned to each action over time

The simplified runtime uses **only** `strategy_sum`.

## Code That Builds the Per-Decision Strategy During Training

From [../../advanced_cfr/advanced_cfr_player.py](../../advanced_cfr/advanced_cfr_player.py), the key function is:

```python
def _strategy_for(self, info_key, legal_actions, features, base_action):
  regrets = self.regret_sum.setdefault(info_key, self._zero_map())
  sums = self.strategy_sum.setdefault(info_key, self._zero_map())
  prior = self._prior_strategy(features, legal_actions, base_action)

  numerators = {}
  total = 0.0
  for action in self.ACTIONS:
    if action not in legal_actions:
      numerators[action] = 0.0
      continue
    numerators[action] = max(regrets[action], 0.0) + self.prior_weight * prior[action]
    total += numerators[action]

  if total <= 0:
    strategy = dict(prior)
  else:
    strategy = {action: numerators[action] / total for action in self.ACTIONS}

  if self.training_enabled and self.exploration > 0:
    uniform = 1.0 / max(len(legal_actions), 1)
    for action in self.ACTIONS:
      if action in legal_actions:
        strategy[action] = (1.0 - self.exploration) * strategy[action] + self.exploration * uniform
      else:
        strategy[action] = 0.0

  weight = max(1.0, self.round_count ** 0.5)
  for action in self.ACTIONS:
    sums[action] += weight * strategy.get(action, 0.0)
  return strategy
```

## What This Means

For one decision state:

1. get the current regrets for that `info_key`
2. clip regrets below zero
3. add a handcrafted prior policy
4. normalize to get a decision-time strategy
5. optionally mix in exploration during training
6. add that strategy into `strategy_sum`

So `strategy_sum` is not one-shot. It is an accumulated average over many visits to the same abstract state.

## How Runtime `average_strategy` Is Computed

The simplified player later reads the saved `strategy_sum` and normalizes it with:

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

So runtime `average_strategy` is:

- the saved cumulative `strategy_sum` for the current `info_key`
- filtered to legal actions only
- normalized to sum to 1

## End-to-End Example of One Training Decision

Suppose the training player sees this abstract state:

```python
info_key = "(0, 3, 0, 0, 0, 0, 1, 0, 5, '')"
legal_actions = {"fold", "call", "raise"}
```

Assume before this visit:

```python
regret_sum[info_key] = {
  "fold": 0.20,
  "call": 0.10,
  "raise": 1.40
}

strategy_sum[info_key] = {
  "fold": 3.0,
  "call": 6.0,
  "raise": 21.0
}
```

Assume the handcrafted prior for this state is:

```python
prior = {
  "fold": 0.10,
  "call": 0.20,
  "raise": 0.70
}
```

Assume:

```python
prior_weight = 0.12
round_count = 25
weight = sqrt(25) = 5
```

### Step 1. Build numerators

For each legal action:

```python
fold  = max(0.20, 0.0) + 0.12 * 0.10 = 0.212
call  = max(0.10, 0.0) + 0.12 * 0.20 = 0.124
raise = max(1.40, 0.0) + 0.12 * 0.70 = 1.484
```

### Step 2. Normalize into strategy

Total:

```python
total = 0.212 + 0.124 + 1.484 = 1.820
```

Normalized:

```python
strategy = {
  "fold": 0.212 / 1.820,   # 0.1165
  "call": 0.124 / 1.820,   # 0.0681
  "raise": 1.484 / 1.820   # 0.8154
}
```

### Step 3. Add this strategy into `strategy_sum`

With weight `5`:

```python
strategy_sum[info_key]["fold"]  += 5 * 0.1165   # +0.5825
strategy_sum[info_key]["call"]  += 5 * 0.0681   # +0.3405
strategy_sum[info_key]["raise"] += 5 * 0.8154   # +4.0770
```

So after this visit:

```python
strategy_sum[info_key] = {
  "fold": 3.5825,
  "call": 6.3405,
  "raise": 25.0770
}
```

### Step 4. Runtime turns that into `average_strategy`

Later, the simplified runtime sees the same `info_key` and legal actions.

It normalizes:

```python
total = 3.5825 + 6.3405 + 25.0770 = 35.0
```

So:

```python
average_strategy = {
  "fold": 3.5825 / 35.0,   # 0.1024
  "call": 6.3405 / 35.0,   # 0.1812
  "raise": 25.0770 / 35.0  # 0.7165
}
```

That is what the simplified player uses at inference time.

## How the Regret Update Happens After the Round

After the round ends, the training player updates regrets with:

```python
def _update_regrets(self, decision, reward):
  info_key = decision["info_key"]
  regrets = self.regret_sum.setdefault(info_key, self._zero_map())
  utilities = self._counterfactual_values(decision["features"], decision["legal_actions"], reward)
  realized = decision["chosen_action"]
  importance = min(2.5, 1.0 / decision["chosen_prob"])
  utilities[realized] = 0.7 * reward * importance + 0.3 * utilities[realized]
  node_value = sum(decision["strategy"].get(action, 0.0) * utilities[action] for action in self.ACTIONS)

  for action in decision["legal_actions"]:
    regrets[action] = max(0.0, regrets[action] + utilities[action] - node_value)
```

Meaning:

1. the decision taken earlier is remembered
2. after the round, the agent gets a final reward
3. it estimates utility for fold/call/raise in that state
4. it computes the expected node value under the strategy it used
5. it adds action advantage `utility(action) - node_value` into regret

Those updated regrets affect the next visit to the same `info_key`.

So the full loop is:

1. build `info_key`
2. compute `strategy`
3. store decision
4. finish round
5. update regrets
6. next time same `info_key` appears, strategy changes
7. accumulated strategy mass becomes `strategy_sum`
8. runtime normalizes `strategy_sum` into `average_strategy`

## Why This Matters

The simplified player is really using the result of many old training visits.

So when you see:

```python
average_strategy = {
  "fold": 0.0432,
  "call": 0.1178,
  "raise": 0.8390
}
```

that is not directly hand-written. It is the normalized average of many prior training-time strategy contributions for that abstract state.
