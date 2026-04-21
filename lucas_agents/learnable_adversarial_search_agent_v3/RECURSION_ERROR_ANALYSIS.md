# RecursionError Analysis for `train_cfr.py`

## Summary

The `RecursionError: maximum recursion depth exceeded` during long CFR training runs was not caused by the CFR logic itself. It was caused by reusing the same player object across many matches while `pypokerengine` repeatedly wrapped that object's `declare_action` method with its timeout decorator.

This caused the call stack around `declare_action` to grow match after match until Python eventually hit the recursion limit.

## What Happened

Inside `pypokerengine/api/game.py`, `Config.register_player(...)` mutates the passed player instance:

```python
algorithm.declare_action = timeout2(0.5, default_action_info)(algorithm.declare_action)
```

That means every time the same player object is registered for a new match, its `declare_action` method gets wrapped again.

In `lucas_agents/learnable_adversarial_search_agent_v2/train_cfr.py`, the training loop creates one learner object and reuses it for all games:

```python
learner = TrainingLearnableAdversarialSearchPlayerV2(...)
```

Then each call to `_play_match(...)` eventually re-registers that same learner instance with the engine. Because the engine mutates the instance in place, the learner's `declare_action` method becomes:

1. original `declare_action`
2. timeout wrapper around `declare_action`
3. timeout wrapper around the timeout wrapper
4. another timeout wrapper around that
5. repeated over hundreds or thousands of matches

By the time the run gets deep enough, one action request triggers a long chain of nested wrapper calls. That is why the traceback showed:

- repeated calls to `pypokerengine/utils/timeout_decorator.py`, line 120
- repeated `return function(*args, **kwargs)`
- eventual failure in `signal.signal(...)`

The failure is therefore cumulative state corruption on the player object, not a one-off bad poker state.

## Why So Many Games Were Skipped

Once the learner object had accumulated too many wrappers, retries did not help.

The old code retried the same match using the same learner object:

```python
for attempt in range(1, args.max_retries + 2):
```

But that learner instance was already poisoned by the wrapper buildup. So each retry started from an already broken `declare_action` method, making repeated failures likely. That is why skipped games grew so large.

## Constraint

The fix had to avoid changing anything under `pypokerengine/`.

So the solution had to live entirely in:

- `lucas_agents/learnable_adversarial_search_agent_v2/player.py`
- `lucas_agents/learnable_adversarial_search_agent_v2/train_cfr.py`

## Fix

### 1. Preserve the original `declare_action`

In `player.py`, the player now stores its original bound `declare_action` implementation during initialization:

```python
self._declare_action_impl = self.declare_action
```

### 2. Add a reset hook for each match

The player now exposes:

```python
def reset_match_state(self):
    self.declare_action = self._declare_action_impl
    if hasattr(self, "cfr"):
        self.cfr.round_decisions = []
```

This restores the unwrapped method before the engine can wrap it again for the next match.

### 3. Reset both players before every attempt

In `train_cfr.py`, each attempt now calls:

```python
_prepare_player_for_match(learner)
_prepare_player_for_match(opponent)
```

That ensures each match starts from a clean callable, even though `pypokerengine` still wraps methods internally.

### 4. Recover safely after a failed match

When an exception occurs, training now:

1. resets the learner state
2. clears partial round decision state
3. saves the CFR policy immediately
4. logs that recovery happened

This prevents one bad match from contaminating the rest of the training run.

## Why This Fix Works

The engine still applies its timeout wrapper, but now it only wraps a clean base method for the current match.

So instead of getting:

`timeout(timeout(timeout(timeout(declare_action))))`

across the entire training session, each match gets only one fresh wrapper layer at registration time.

That removes the runaway recursion buildup without any engine changes.

## Behavioral Impact

The fix does not change:

- CFR regret updates
- policy loading or saving format
- opponent selection
- match rules
- action logic inside the learner

The fix only changes runtime lifecycle management around reused player instances and failure recovery.

## Remaining Risk

This patch specifically addresses the recursive timeout-wrapper accumulation problem.

If another exception occurs during training for a different reason, the run can still skip that match after exhausting retries. However, the learner will now checkpoint and reset cleanly, so unrelated failures should be much less likely to poison the rest of the run.

## Files Changed

- [player.py](/Users/xiaofanlu/Documents/github_repos/CS683-PokerAgentProject/lucas_agents/learnable_adversarial_search_agent_v2/player.py)
- [train_cfr.py](/Users/xiaofanlu/Documents/github_repos/CS683-PokerAgentProject/lucas_agents/learnable_adversarial_search_agent_v2/train_cfr.py)

