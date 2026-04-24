# `raise_player` training speed fix

## Problem

Training with `--opponents raise_player` was much slower than default self-play.
This looked suspicious because the scripted opponent action is trivial:

```python
if "raise" is legal:
  return "raise"
return "call"
```

The slowdown was not caused by choosing the scripted action. It came from the
trainer repeatedly evaluating the same postflop hand strength while traversing
the game tree.

## Diagnosis

The MCCFR trainer expands every legal learner action at traverser nodes. Against
`raise_player`, the opponent keeps aggressive branches alive, so one training
iteration visits many more postflop decision nodes than a typical sampled
self-play line.

Profiling one `raise_player` iteration showed the hot path:

- `_traverse()`
- `rich_hand_strength_v5.build_info_key()`
- `rich_hand_strength_v5.hand_strength()`
- `estimate_hole_card_win_rate()`
- `HandEvaluator.eval_hand()`

The key observation was that most hand-strength work was duplicated. In one
sampled `raise_player` iteration:

```text
hand_strength calls: 596
unique (hole cards, community cards, simulations): 8
duplicate calls: 588
```

So the trainer was rerunning Monte Carlo equity estimation hundreds of times for
identical card states in the same traversal.

## Fix

### 1. Cache v5 hand strength

`lucas_agents/mccfr_self_play/abstractions/rich_hand_strength_v5.py` now wraps
the expensive hand-strength computation with a bounded `functools.lru_cache`.

The public function still accepts the same arguments:

```python
def hand_strength(hole_card, community_card, simulations):
  return _cached_hand_strength(tuple(hole_card), tuple(community_card), int(simulations))
```

The cached helper does the original work:

```python
@lru_cache(maxsize=200000)
def _cached_hand_strength(hole_card, community_card, simulations):
  ...
```

This preserves the same abstraction keys but avoids recomputing identical equity
estimates.

### 2. Remove redundant trainer copy

`lucas_agents/mccfr_self_play/mccfr_trainer.py` previously did this:

```python
next_state, _ = RoundManager.apply_action(deepcopy_game_state(game_state), action)
```

But this PyPokerEngine fork already deep-copies inside
`RoundManager.apply_action()`. The trainer now calls:

```python
next_state, _ = RoundManager.apply_action(game_state, action)
```

This removes one unnecessary copy per branch.

## Benchmark

Small local benchmark, 5 iterations, fresh temp policy, same seed:

Before caching:

```text
self:         0.331s / iteration
raise_player: 1.741s / iteration
```

After caching:

```text
self:         0.034s / iteration
raise_player: 0.131s / iteration
```

Additional check:

```text
raise_player 20 iterations: 2.636s total
per iteration: 0.132s
```

## Conclusion

`raise_player` is still expected to be slower than self-play because it creates
more aggressive postflop branches. The bug was that those branches repeatedly
ran the same Monte Carlo hand-strength simulation. Caching makes the cost depend
mostly on unique card states instead of repeated infoset visits.

