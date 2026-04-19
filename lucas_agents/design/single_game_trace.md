# Single Game Decision Trace

## Match Setup

- player_a: `condition_threshold_player.py`
- player_b: `raise_player.py`
- max_round: `100`
- initial_stack: `500`
- small_blind: `10`

## Final Result

```python
[{'name': 'player_b', 'uuid': 'mgtzikgmdfwidoyqymhueh', 'stack': 1000, 'state': 'participating'},
 {'name': 'player_a', 'uuid': 'ezuvdegskltrhzvsoiimcm', 'stack': 0, 'state': 'folded'}]
```

## Traced Decisions

### Decision 1

- player: `player_a`
- round_count: `1`
- street: `preflop`
- chosen_action: `{'action': 'fold', 'amount': None}`

#### valid_actions

```python
[{'action': 'fold'}, {'action': 'call'}, {'action': 'raise'}]
```

#### hole_card

```python
['D9', 'C2']
```

#### round_state

```python
{'street': 'preflop',
 'pot': {'main': {'amount': 60}, 'side': []},
 'community_card': [],
 'dealer_btn': 0,
 'next_player': 0,
 'small_blind_pos': 1,
 'big_blind_pos': 0,
 'round_count': 1,
 'small_blind_amount': 10,
 'seats': [{'name': 'player_a',
            'uuid': 'ezuvdegskltrhzvsoiimcm',
            'stack': 480,
            'state': 'participating'},
           {'name': 'player_b',
            'uuid': 'mgtzikgmdfwidoyqymhueh',
            'stack': 460,
            'state': 'participating'}],
 'action_histories': {'preflop': [{'action': 'SMALLBLIND',
                                   'amount': 10,
                                   'add_amount': 10,
                                   'uuid': 'mgtzikgmdfwidoyqymhueh'},
                                  {'action': 'BIGBLIND',
                                   'amount': 20,
                                   'add_amount': 10,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'},
                                  {'action': 'RAISE',
                                   'amount': 40,
                                   'paid': 30,
                                   'add_amount': 20,
                                   'uuid': 'mgtzikgmdfwidoyqymhueh'}]}}
```

### Decision 2

- player: `player_a`
- round_count: `2`
- street: `preflop`
- chosen_action: `{'action': 'call', 'amount': None}`

#### valid_actions

```python
[{'action': 'fold'}, {'action': 'call'}, {'action': 'raise'}]
```

#### hole_card

```python
['SQ', 'C4']
```

#### round_state

```python
{'street': 'preflop',
 'pot': {'main': {'amount': 30}, 'side': []},
 'community_card': [],
 'dealer_btn': 1,
 'next_player': 0,
 'small_blind_pos': 0,
 'big_blind_pos': 1,
 'round_count': 2,
 'small_blind_amount': 10,
 'seats': [{'name': 'player_a',
            'uuid': 'ezuvdegskltrhzvsoiimcm',
            'stack': 470,
            'state': 'participating'},
           {'name': 'player_b',
            'uuid': 'mgtzikgmdfwidoyqymhueh',
            'stack': 500,
            'state': 'participating'}],
 'action_histories': {'preflop': [{'action': 'SMALLBLIND',
                                   'amount': 10,
                                   'add_amount': 10,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'},
                                  {'action': 'BIGBLIND',
                                   'amount': 20,
                                   'add_amount': 10,
                                   'uuid': 'mgtzikgmdfwidoyqymhueh'}]}}
```

### Decision 3

- player: `player_a`
- round_count: `2`
- street: `preflop`
- chosen_action: `{'action': 'call', 'amount': None}`

#### valid_actions

```python
[{'action': 'fold'}, {'action': 'call'}, {'action': 'raise'}]
```

#### hole_card

```python
['SQ', 'C4']
```

#### round_state

```python
{'street': 'preflop',
 'pot': {'main': {'amount': 60}, 'side': []},
 'community_card': [],
 'dealer_btn': 1,
 'next_player': 0,
 'small_blind_pos': 0,
 'big_blind_pos': 1,
 'round_count': 2,
 'small_blind_amount': 10,
 'seats': [{'name': 'player_a',
            'uuid': 'ezuvdegskltrhzvsoiimcm',
            'stack': 460,
            'state': 'participating'},
           {'name': 'player_b',
            'uuid': 'mgtzikgmdfwidoyqymhueh',
            'stack': 480,
            'state': 'participating'}],
 'action_histories': {'preflop': [{'action': 'SMALLBLIND',
                                   'amount': 10,
                                   'add_amount': 10,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'},
                                  {'action': 'BIGBLIND',
                                   'amount': 20,
                                   'add_amount': 10,
                                   'uuid': 'mgtzikgmdfwidoyqymhueh'},
                                  {'action': 'CALL',
                                   'amount': 20,
                                   'paid': 10,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'},
                                  {'action': 'RAISE',
                                   'amount': 40,
                                   'paid': 20,
                                   'add_amount': 20,
                                   'uuid': 'mgtzikgmdfwidoyqymhueh'}]}}
```

### Decision 4

- player: `player_a`
- round_count: `2`
- street: `flop`
- chosen_action: `{'action': 'call', 'amount': None}`

#### valid_actions

```python
[{'action': 'fold'}, {'action': 'call'}, {'action': 'raise'}]
```

#### hole_card

```python
['SQ', 'C4']
```

#### round_state

```python
{'street': 'flop',
 'pot': {'main': {'amount': 80}, 'side': []},
 'community_card': ['H2', 'H7', 'CA'],
 'dealer_btn': 1,
 'next_player': 0,
 'small_blind_pos': 0,
 'big_blind_pos': 1,
 'round_count': 2,
 'small_blind_amount': 10,
 'seats': [{'name': 'player_a',
            'uuid': 'ezuvdegskltrhzvsoiimcm',
            'stack': 440,
            'state': 'participating'},
           {'name': 'player_b',
            'uuid': 'mgtzikgmdfwidoyqymhueh',
            'stack': 480,
            'state': 'participating'}],
 'action_histories': {'preflop': [{'action': 'SMALLBLIND',
                                   'amount': 10,
                                   'add_amount': 10,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'},
                                  {'action': 'BIGBLIND',
                                   'amount': 20,
                                   'add_amount': 10,
                                   'uuid': 'mgtzikgmdfwidoyqymhueh'},
                                  {'action': 'CALL',
                                   'amount': 20,
                                   'paid': 10,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'},
                                  {'action': 'RAISE',
                                   'amount': 40,
                                   'paid': 20,
                                   'add_amount': 20,
                                   'uuid': 'mgtzikgmdfwidoyqymhueh'},
                                  {'action': 'CALL',
                                   'amount': 40,
                                   'paid': 20,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'}],
                      'flop': []}}
```

### Decision 5

- player: `player_a`
- round_count: `2`
- street: `flop`
- chosen_action: `{'action': 'fold', 'amount': None}`

#### valid_actions

```python
[{'action': 'fold'}, {'action': 'call'}, {'action': 'raise'}]
```

#### hole_card

```python
['SQ', 'C4']
```

#### round_state

```python
{'street': 'flop',
 'pot': {'main': {'amount': 100}, 'side': []},
 'community_card': ['H2', 'H7', 'CA'],
 'dealer_btn': 1,
 'next_player': 0,
 'small_blind_pos': 0,
 'big_blind_pos': 1,
 'round_count': 2,
 'small_blind_amount': 10,
 'seats': [{'name': 'player_a',
            'uuid': 'ezuvdegskltrhzvsoiimcm',
            'stack': 440,
            'state': 'participating'},
           {'name': 'player_b',
            'uuid': 'mgtzikgmdfwidoyqymhueh',
            'stack': 460,
            'state': 'participating'}],
 'action_histories': {'preflop': [{'action': 'SMALLBLIND',
                                   'amount': 10,
                                   'add_amount': 10,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'},
                                  {'action': 'BIGBLIND',
                                   'amount': 20,
                                   'add_amount': 10,
                                   'uuid': 'mgtzikgmdfwidoyqymhueh'},
                                  {'action': 'CALL',
                                   'amount': 20,
                                   'paid': 10,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'},
                                  {'action': 'RAISE',
                                   'amount': 40,
                                   'paid': 20,
                                   'add_amount': 20,
                                   'uuid': 'mgtzikgmdfwidoyqymhueh'},
                                  {'action': 'CALL',
                                   'amount': 40,
                                   'paid': 20,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'}],
                      'flop': [{'action': 'CALL',
                                'amount': 0,
                                'paid': 0,
                                'uuid': 'ezuvdegskltrhzvsoiimcm'},
                               {'action': 'RAISE',
                                'amount': 20,
                                'paid': 20,
                                'add_amount': 20,
                                'uuid': 'mgtzikgmdfwidoyqymhueh'}]}}
```

### Decision 6

- player: `player_a`
- round_count: `3`
- street: `preflop`
- chosen_action: `{'action': 'call', 'amount': None}`

#### valid_actions

```python
[{'action': 'fold'}, {'action': 'call'}, {'action': 'raise'}]
```

#### hole_card

```python
['H9', 'CT']
```

#### round_state

```python
{'street': 'preflop',
 'pot': {'main': {'amount': 60}, 'side': []},
 'community_card': [],
 'dealer_btn': 0,
 'next_player': 0,
 'small_blind_pos': 1,
 'big_blind_pos': 0,
 'round_count': 3,
 'small_blind_amount': 10,
 'seats': [{'name': 'player_a',
            'uuid': 'ezuvdegskltrhzvsoiimcm',
            'stack': 420,
            'state': 'participating'},
           {'name': 'player_b',
            'uuid': 'mgtzikgmdfwidoyqymhueh',
            'stack': 520,
            'state': 'participating'}],
 'action_histories': {'preflop': [{'action': 'SMALLBLIND',
                                   'amount': 10,
                                   'add_amount': 10,
                                   'uuid': 'mgtzikgmdfwidoyqymhueh'},
                                  {'action': 'BIGBLIND',
                                   'amount': 20,
                                   'add_amount': 10,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'},
                                  {'action': 'RAISE',
                                   'amount': 40,
                                   'paid': 30,
                                   'add_amount': 20,
                                   'uuid': 'mgtzikgmdfwidoyqymhueh'}]}}
```

### Decision 7

- player: `player_a`
- round_count: `3`
- street: `flop`
- chosen_action: `{'action': 'fold', 'amount': None}`

#### valid_actions

```python
[{'action': 'fold'}, {'action': 'call'}, {'action': 'raise'}]
```

#### hole_card

```python
['H9', 'CT']
```

#### round_state

```python
{'street': 'flop',
 'pot': {'main': {'amount': 100}, 'side': []},
 'community_card': ['S6', 'HK', 'DK'],
 'dealer_btn': 0,
 'next_player': 0,
 'small_blind_pos': 1,
 'big_blind_pos': 0,
 'round_count': 3,
 'small_blind_amount': 10,
 'seats': [{'name': 'player_a',
            'uuid': 'ezuvdegskltrhzvsoiimcm',
            'stack': 400,
            'state': 'participating'},
           {'name': 'player_b',
            'uuid': 'mgtzikgmdfwidoyqymhueh',
            'stack': 500,
            'state': 'participating'}],
 'action_histories': {'preflop': [{'action': 'SMALLBLIND',
                                   'amount': 10,
                                   'add_amount': 10,
                                   'uuid': 'mgtzikgmdfwidoyqymhueh'},
                                  {'action': 'BIGBLIND',
                                   'amount': 20,
                                   'add_amount': 10,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'},
                                  {'action': 'RAISE',
                                   'amount': 40,
                                   'paid': 30,
                                   'add_amount': 20,
                                   'uuid': 'mgtzikgmdfwidoyqymhueh'},
                                  {'action': 'CALL',
                                   'amount': 40,
                                   'paid': 20,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'}],
                      'flop': [{'action': 'RAISE',
                                'amount': 20,
                                'paid': 20,
                                'add_amount': 20,
                                'uuid': 'mgtzikgmdfwidoyqymhueh'}]}}
```

### Decision 8

- player: `player_a`
- round_count: `4`
- street: `preflop`
- chosen_action: `{'action': 'call', 'amount': None}`

#### valid_actions

```python
[{'action': 'fold'}, {'action': 'call'}, {'action': 'raise'}]
```

#### hole_card

```python
['H6', 'HA']
```

#### round_state

```python
{'street': 'preflop',
 'pot': {'main': {'amount': 30}, 'side': []},
 'community_card': [],
 'dealer_btn': 1,
 'next_player': 0,
 'small_blind_pos': 0,
 'big_blind_pos': 1,
 'round_count': 4,
 'small_blind_amount': 10,
 'seats': [{'name': 'player_a',
            'uuid': 'ezuvdegskltrhzvsoiimcm',
            'stack': 390,
            'state': 'participating'},
           {'name': 'player_b',
            'uuid': 'mgtzikgmdfwidoyqymhueh',
            'stack': 580,
            'state': 'participating'}],
 'action_histories': {'preflop': [{'action': 'SMALLBLIND',
                                   'amount': 10,
                                   'add_amount': 10,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'},
                                  {'action': 'BIGBLIND',
                                   'amount': 20,
                                   'add_amount': 10,
                                   'uuid': 'mgtzikgmdfwidoyqymhueh'}]}}
```

### Decision 9

- player: `player_a`
- round_count: `4`
- street: `preflop`
- chosen_action: `{'action': 'call', 'amount': None}`

#### valid_actions

```python
[{'action': 'fold'}, {'action': 'call'}, {'action': 'raise'}]
```

#### hole_card

```python
['H6', 'HA']
```

#### round_state

```python
{'street': 'preflop',
 'pot': {'main': {'amount': 60}, 'side': []},
 'community_card': [],
 'dealer_btn': 1,
 'next_player': 0,
 'small_blind_pos': 0,
 'big_blind_pos': 1,
 'round_count': 4,
 'small_blind_amount': 10,
 'seats': [{'name': 'player_a',
            'uuid': 'ezuvdegskltrhzvsoiimcm',
            'stack': 380,
            'state': 'participating'},
           {'name': 'player_b',
            'uuid': 'mgtzikgmdfwidoyqymhueh',
            'stack': 560,
            'state': 'participating'}],
 'action_histories': {'preflop': [{'action': 'SMALLBLIND',
                                   'amount': 10,
                                   'add_amount': 10,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'},
                                  {'action': 'BIGBLIND',
                                   'amount': 20,
                                   'add_amount': 10,
                                   'uuid': 'mgtzikgmdfwidoyqymhueh'},
                                  {'action': 'CALL',
                                   'amount': 20,
                                   'paid': 10,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'},
                                  {'action': 'RAISE',
                                   'amount': 40,
                                   'paid': 20,
                                   'add_amount': 20,
                                   'uuid': 'mgtzikgmdfwidoyqymhueh'}]}}
```

### Decision 10

- player: `player_a`
- round_count: `4`
- street: `flop`
- chosen_action: `{'action': 'call', 'amount': None}`

#### valid_actions

```python
[{'action': 'fold'}, {'action': 'call'}, {'action': 'raise'}]
```

#### hole_card

```python
['H6', 'HA']
```

#### round_state

```python
{'street': 'flop',
 'pot': {'main': {'amount': 80}, 'side': []},
 'community_card': ['D2', 'D4', 'DT'],
 'dealer_btn': 1,
 'next_player': 0,
 'small_blind_pos': 0,
 'big_blind_pos': 1,
 'round_count': 4,
 'small_blind_amount': 10,
 'seats': [{'name': 'player_a',
            'uuid': 'ezuvdegskltrhzvsoiimcm',
            'stack': 360,
            'state': 'participating'},
           {'name': 'player_b',
            'uuid': 'mgtzikgmdfwidoyqymhueh',
            'stack': 560,
            'state': 'participating'}],
 'action_histories': {'preflop': [{'action': 'SMALLBLIND',
                                   'amount': 10,
                                   'add_amount': 10,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'},
                                  {'action': 'BIGBLIND',
                                   'amount': 20,
                                   'add_amount': 10,
                                   'uuid': 'mgtzikgmdfwidoyqymhueh'},
                                  {'action': 'CALL',
                                   'amount': 20,
                                   'paid': 10,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'},
                                  {'action': 'RAISE',
                                   'amount': 40,
                                   'paid': 20,
                                   'add_amount': 20,
                                   'uuid': 'mgtzikgmdfwidoyqymhueh'},
                                  {'action': 'CALL',
                                   'amount': 40,
                                   'paid': 20,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'}],
                      'flop': []}}
```

### Decision 11

- player: `player_a`
- round_count: `4`
- street: `flop`
- chosen_action: `{'action': 'call', 'amount': None}`

#### valid_actions

```python
[{'action': 'fold'}, {'action': 'call'}, {'action': 'raise'}]
```

#### hole_card

```python
['H6', 'HA']
```

#### round_state

```python
{'street': 'flop',
 'pot': {'main': {'amount': 100}, 'side': []},
 'community_card': ['D2', 'D4', 'DT'],
 'dealer_btn': 1,
 'next_player': 0,
 'small_blind_pos': 0,
 'big_blind_pos': 1,
 'round_count': 4,
 'small_blind_amount': 10,
 'seats': [{'name': 'player_a',
            'uuid': 'ezuvdegskltrhzvsoiimcm',
            'stack': 360,
            'state': 'participating'},
           {'name': 'player_b',
            'uuid': 'mgtzikgmdfwidoyqymhueh',
            'stack': 540,
            'state': 'participating'}],
 'action_histories': {'preflop': [{'action': 'SMALLBLIND',
                                   'amount': 10,
                                   'add_amount': 10,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'},
                                  {'action': 'BIGBLIND',
                                   'amount': 20,
                                   'add_amount': 10,
                                   'uuid': 'mgtzikgmdfwidoyqymhueh'},
                                  {'action': 'CALL',
                                   'amount': 20,
                                   'paid': 10,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'},
                                  {'action': 'RAISE',
                                   'amount': 40,
                                   'paid': 20,
                                   'add_amount': 20,
                                   'uuid': 'mgtzikgmdfwidoyqymhueh'},
                                  {'action': 'CALL',
                                   'amount': 40,
                                   'paid': 20,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'}],
                      'flop': [{'action': 'CALL',
                                'amount': 0,
                                'paid': 0,
                                'uuid': 'ezuvdegskltrhzvsoiimcm'},
                               {'action': 'RAISE',
                                'amount': 20,
                                'paid': 20,
                                'add_amount': 20,
                                'uuid': 'mgtzikgmdfwidoyqymhueh'}]}}
```

### Decision 12

- player: `player_a`
- round_count: `4`
- street: `turn`
- chosen_action: `{'action': 'call', 'amount': None}`

#### valid_actions

```python
[{'action': 'fold'}, {'action': 'call'}, {'action': 'raise'}]
```

#### hole_card

```python
['H6', 'HA']
```

#### round_state

```python
{'street': 'turn',
 'pot': {'main': {'amount': 120}, 'side': []},
 'community_card': ['D2', 'D4', 'DT', 'SK'],
 'dealer_btn': 1,
 'next_player': 0,
 'small_blind_pos': 0,
 'big_blind_pos': 1,
 'round_count': 4,
 'small_blind_amount': 10,
 'seats': [{'name': 'player_a',
            'uuid': 'ezuvdegskltrhzvsoiimcm',
            'stack': 340,
            'state': 'participating'},
           {'name': 'player_b',
            'uuid': 'mgtzikgmdfwidoyqymhueh',
            'stack': 540,
            'state': 'participating'}],
 'action_histories': {'preflop': [{'action': 'SMALLBLIND',
                                   'amount': 10,
                                   'add_amount': 10,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'},
                                  {'action': 'BIGBLIND',
                                   'amount': 20,
                                   'add_amount': 10,
                                   'uuid': 'mgtzikgmdfwidoyqymhueh'},
                                  {'action': 'CALL',
                                   'amount': 20,
                                   'paid': 10,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'},
                                  {'action': 'RAISE',
                                   'amount': 40,
                                   'paid': 20,
                                   'add_amount': 20,
                                   'uuid': 'mgtzikgmdfwidoyqymhueh'},
                                  {'action': 'CALL',
                                   'amount': 40,
                                   'paid': 20,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'}],
                      'flop': [{'action': 'CALL',
                                'amount': 0,
                                'paid': 0,
                                'uuid': 'ezuvdegskltrhzvsoiimcm'},
                               {'action': 'RAISE',
                                'amount': 20,
                                'paid': 20,
                                'add_amount': 20,
                                'uuid': 'mgtzikgmdfwidoyqymhueh'},
                               {'action': 'CALL',
                                'amount': 20,
                                'paid': 20,
                                'uuid': 'ezuvdegskltrhzvsoiimcm'}],
                      'turn': []}}
```

### Decision 13

- player: `player_a`
- round_count: `4`
- street: `turn`
- chosen_action: `{'action': 'fold', 'amount': None}`

#### valid_actions

```python
[{'action': 'fold'}, {'action': 'call'}, {'action': 'raise'}]
```

#### hole_card

```python
['H6', 'HA']
```

#### round_state

```python
{'street': 'turn',
 'pot': {'main': {'amount': 160}, 'side': []},
 'community_card': ['D2', 'D4', 'DT', 'SK'],
 'dealer_btn': 1,
 'next_player': 0,
 'small_blind_pos': 0,
 'big_blind_pos': 1,
 'round_count': 4,
 'small_blind_amount': 10,
 'seats': [{'name': 'player_a',
            'uuid': 'ezuvdegskltrhzvsoiimcm',
            'stack': 340,
            'state': 'participating'},
           {'name': 'player_b',
            'uuid': 'mgtzikgmdfwidoyqymhueh',
            'stack': 500,
            'state': 'participating'}],
 'action_histories': {'preflop': [{'action': 'SMALLBLIND',
                                   'amount': 10,
                                   'add_amount': 10,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'},
                                  {'action': 'BIGBLIND',
                                   'amount': 20,
                                   'add_amount': 10,
                                   'uuid': 'mgtzikgmdfwidoyqymhueh'},
                                  {'action': 'CALL',
                                   'amount': 20,
                                   'paid': 10,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'},
                                  {'action': 'RAISE',
                                   'amount': 40,
                                   'paid': 20,
                                   'add_amount': 20,
                                   'uuid': 'mgtzikgmdfwidoyqymhueh'},
                                  {'action': 'CALL',
                                   'amount': 40,
                                   'paid': 20,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'}],
                      'flop': [{'action': 'CALL',
                                'amount': 0,
                                'paid': 0,
                                'uuid': 'ezuvdegskltrhzvsoiimcm'},
                               {'action': 'RAISE',
                                'amount': 20,
                                'paid': 20,
                                'add_amount': 20,
                                'uuid': 'mgtzikgmdfwidoyqymhueh'},
                               {'action': 'CALL',
                                'amount': 20,
                                'paid': 20,
                                'uuid': 'ezuvdegskltrhzvsoiimcm'}],
                      'turn': [{'action': 'CALL',
                                'amount': 0,
                                'paid': 0,
                                'uuid': 'ezuvdegskltrhzvsoiimcm'},
                               {'action': 'RAISE',
                                'amount': 40,
                                'paid': 40,
                                'add_amount': 40,
                                'uuid': 'mgtzikgmdfwidoyqymhueh'}]}}
```

### Decision 14

- player: `player_a`
- round_count: `5`
- street: `preflop`
- chosen_action: `{'action': 'call', 'amount': None}`

#### valid_actions

```python
[{'action': 'fold'}, {'action': 'call'}, {'action': 'raise'}]
```

#### hole_card

```python
['SK', 'H7']
```

#### round_state

```python
{'street': 'preflop',
 'pot': {'main': {'amount': 60}, 'side': []},
 'community_card': [],
 'dealer_btn': 0,
 'next_player': 0,
 'small_blind_pos': 1,
 'big_blind_pos': 0,
 'round_count': 5,
 'small_blind_amount': 10,
 'seats': [{'name': 'player_a',
            'uuid': 'ezuvdegskltrhzvsoiimcm',
            'stack': 320,
            'state': 'participating'},
           {'name': 'player_b',
            'uuid': 'mgtzikgmdfwidoyqymhueh',
            'stack': 620,
            'state': 'participating'}],
 'action_histories': {'preflop': [{'action': 'SMALLBLIND',
                                   'amount': 10,
                                   'add_amount': 10,
                                   'uuid': 'mgtzikgmdfwidoyqymhueh'},
                                  {'action': 'BIGBLIND',
                                   'amount': 20,
                                   'add_amount': 10,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'},
                                  {'action': 'RAISE',
                                   'amount': 40,
                                   'paid': 30,
                                   'add_amount': 20,
                                   'uuid': 'mgtzikgmdfwidoyqymhueh'}]}}
```

### Decision 15

- player: `player_a`
- round_count: `5`
- street: `flop`
- chosen_action: `{'action': 'fold', 'amount': None}`

#### valid_actions

```python
[{'action': 'fold'}, {'action': 'call'}, {'action': 'raise'}]
```

#### hole_card

```python
['SK', 'H7']
```

#### round_state

```python
{'street': 'flop',
 'pot': {'main': {'amount': 100}, 'side': []},
 'community_card': ['H9', 'CQ', 'D6'],
 'dealer_btn': 0,
 'next_player': 0,
 'small_blind_pos': 1,
 'big_blind_pos': 0,
 'round_count': 5,
 'small_blind_amount': 10,
 'seats': [{'name': 'player_a',
            'uuid': 'ezuvdegskltrhzvsoiimcm',
            'stack': 300,
            'state': 'participating'},
           {'name': 'player_b',
            'uuid': 'mgtzikgmdfwidoyqymhueh',
            'stack': 600,
            'state': 'participating'}],
 'action_histories': {'preflop': [{'action': 'SMALLBLIND',
                                   'amount': 10,
                                   'add_amount': 10,
                                   'uuid': 'mgtzikgmdfwidoyqymhueh'},
                                  {'action': 'BIGBLIND',
                                   'amount': 20,
                                   'add_amount': 10,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'},
                                  {'action': 'RAISE',
                                   'amount': 40,
                                   'paid': 30,
                                   'add_amount': 20,
                                   'uuid': 'mgtzikgmdfwidoyqymhueh'},
                                  {'action': 'CALL',
                                   'amount': 40,
                                   'paid': 20,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'}],
                      'flop': [{'action': 'RAISE',
                                'amount': 20,
                                'paid': 20,
                                'add_amount': 20,
                                'uuid': 'mgtzikgmdfwidoyqymhueh'}]}}
```

### Decision 16

- player: `player_a`
- round_count: `6`
- street: `preflop`
- chosen_action: `{'action': 'call', 'amount': None}`

#### valid_actions

```python
[{'action': 'fold'}, {'action': 'call'}, {'action': 'raise'}]
```

#### hole_card

```python
['H9', 'DK']
```

#### round_state

```python
{'street': 'preflop',
 'pot': {'main': {'amount': 30}, 'side': []},
 'community_card': [],
 'dealer_btn': 1,
 'next_player': 0,
 'small_blind_pos': 0,
 'big_blind_pos': 1,
 'round_count': 6,
 'small_blind_amount': 10,
 'seats': [{'name': 'player_a',
            'uuid': 'ezuvdegskltrhzvsoiimcm',
            'stack': 290,
            'state': 'participating'},
           {'name': 'player_b',
            'uuid': 'mgtzikgmdfwidoyqymhueh',
            'stack': 680,
            'state': 'participating'}],
 'action_histories': {'preflop': [{'action': 'SMALLBLIND',
                                   'amount': 10,
                                   'add_amount': 10,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'},
                                  {'action': 'BIGBLIND',
                                   'amount': 20,
                                   'add_amount': 10,
                                   'uuid': 'mgtzikgmdfwidoyqymhueh'}]}}
```

### Decision 17

- player: `player_a`
- round_count: `6`
- street: `preflop`
- chosen_action: `{'action': 'call', 'amount': None}`

#### valid_actions

```python
[{'action': 'fold'}, {'action': 'call'}, {'action': 'raise'}]
```

#### hole_card

```python
['H9', 'DK']
```

#### round_state

```python
{'street': 'preflop',
 'pot': {'main': {'amount': 60}, 'side': []},
 'community_card': [],
 'dealer_btn': 1,
 'next_player': 0,
 'small_blind_pos': 0,
 'big_blind_pos': 1,
 'round_count': 6,
 'small_blind_amount': 10,
 'seats': [{'name': 'player_a',
            'uuid': 'ezuvdegskltrhzvsoiimcm',
            'stack': 280,
            'state': 'participating'},
           {'name': 'player_b',
            'uuid': 'mgtzikgmdfwidoyqymhueh',
            'stack': 660,
            'state': 'participating'}],
 'action_histories': {'preflop': [{'action': 'SMALLBLIND',
                                   'amount': 10,
                                   'add_amount': 10,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'},
                                  {'action': 'BIGBLIND',
                                   'amount': 20,
                                   'add_amount': 10,
                                   'uuid': 'mgtzikgmdfwidoyqymhueh'},
                                  {'action': 'CALL',
                                   'amount': 20,
                                   'paid': 10,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'},
                                  {'action': 'RAISE',
                                   'amount': 40,
                                   'paid': 20,
                                   'add_amount': 20,
                                   'uuid': 'mgtzikgmdfwidoyqymhueh'}]}}
```

### Decision 18

- player: `player_a`
- round_count: `6`
- street: `flop`
- chosen_action: `{'action': 'call', 'amount': None}`

#### valid_actions

```python
[{'action': 'fold'}, {'action': 'call'}, {'action': 'raise'}]
```

#### hole_card

```python
['H9', 'DK']
```

#### round_state

```python
{'street': 'flop',
 'pot': {'main': {'amount': 80}, 'side': []},
 'community_card': ['S2', 'DT', 'HT'],
 'dealer_btn': 1,
 'next_player': 0,
 'small_blind_pos': 0,
 'big_blind_pos': 1,
 'round_count': 6,
 'small_blind_amount': 10,
 'seats': [{'name': 'player_a',
            'uuid': 'ezuvdegskltrhzvsoiimcm',
            'stack': 260,
            'state': 'participating'},
           {'name': 'player_b',
            'uuid': 'mgtzikgmdfwidoyqymhueh',
            'stack': 660,
            'state': 'participating'}],
 'action_histories': {'preflop': [{'action': 'SMALLBLIND',
                                   'amount': 10,
                                   'add_amount': 10,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'},
                                  {'action': 'BIGBLIND',
                                   'amount': 20,
                                   'add_amount': 10,
                                   'uuid': 'mgtzikgmdfwidoyqymhueh'},
                                  {'action': 'CALL',
                                   'amount': 20,
                                   'paid': 10,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'},
                                  {'action': 'RAISE',
                                   'amount': 40,
                                   'paid': 20,
                                   'add_amount': 20,
                                   'uuid': 'mgtzikgmdfwidoyqymhueh'},
                                  {'action': 'CALL',
                                   'amount': 40,
                                   'paid': 20,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'}],
                      'flop': []}}
```

### Decision 19

- player: `player_a`
- round_count: `6`
- street: `flop`
- chosen_action: `{'action': 'call', 'amount': None}`

#### valid_actions

```python
[{'action': 'fold'}, {'action': 'call'}, {'action': 'raise'}]
```

#### hole_card

```python
['H9', 'DK']
```

#### round_state

```python
{'street': 'flop',
 'pot': {'main': {'amount': 100}, 'side': []},
 'community_card': ['S2', 'DT', 'HT'],
 'dealer_btn': 1,
 'next_player': 0,
 'small_blind_pos': 0,
 'big_blind_pos': 1,
 'round_count': 6,
 'small_blind_amount': 10,
 'seats': [{'name': 'player_a',
            'uuid': 'ezuvdegskltrhzvsoiimcm',
            'stack': 260,
            'state': 'participating'},
           {'name': 'player_b',
            'uuid': 'mgtzikgmdfwidoyqymhueh',
            'stack': 640,
            'state': 'participating'}],
 'action_histories': {'preflop': [{'action': 'SMALLBLIND',
                                   'amount': 10,
                                   'add_amount': 10,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'},
                                  {'action': 'BIGBLIND',
                                   'amount': 20,
                                   'add_amount': 10,
                                   'uuid': 'mgtzikgmdfwidoyqymhueh'},
                                  {'action': 'CALL',
                                   'amount': 20,
                                   'paid': 10,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'},
                                  {'action': 'RAISE',
                                   'amount': 40,
                                   'paid': 20,
                                   'add_amount': 20,
                                   'uuid': 'mgtzikgmdfwidoyqymhueh'},
                                  {'action': 'CALL',
                                   'amount': 40,
                                   'paid': 20,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'}],
                      'flop': [{'action': 'CALL',
                                'amount': 0,
                                'paid': 0,
                                'uuid': 'ezuvdegskltrhzvsoiimcm'},
                               {'action': 'RAISE',
                                'amount': 20,
                                'paid': 20,
                                'add_amount': 20,
                                'uuid': 'mgtzikgmdfwidoyqymhueh'}]}}
```

### Decision 20

- player: `player_a`
- round_count: `6`
- street: `turn`
- chosen_action: `{'action': 'raise', 'amount': None}`

#### valid_actions

```python
[{'action': 'fold'}, {'action': 'call'}, {'action': 'raise'}]
```

#### hole_card

```python
['H9', 'DK']
```

#### round_state

```python
{'street': 'turn',
 'pot': {'main': {'amount': 120}, 'side': []},
 'community_card': ['S2', 'DT', 'HT', 'CK'],
 'dealer_btn': 1,
 'next_player': 0,
 'small_blind_pos': 0,
 'big_blind_pos': 1,
 'round_count': 6,
 'small_blind_amount': 10,
 'seats': [{'name': 'player_a',
            'uuid': 'ezuvdegskltrhzvsoiimcm',
            'stack': 240,
            'state': 'participating'},
           {'name': 'player_b',
            'uuid': 'mgtzikgmdfwidoyqymhueh',
            'stack': 640,
            'state': 'participating'}],
 'action_histories': {'preflop': [{'action': 'SMALLBLIND',
                                   'amount': 10,
                                   'add_amount': 10,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'},
                                  {'action': 'BIGBLIND',
                                   'amount': 20,
                                   'add_amount': 10,
                                   'uuid': 'mgtzikgmdfwidoyqymhueh'},
                                  {'action': 'CALL',
                                   'amount': 20,
                                   'paid': 10,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'},
                                  {'action': 'RAISE',
                                   'amount': 40,
                                   'paid': 20,
                                   'add_amount': 20,
                                   'uuid': 'mgtzikgmdfwidoyqymhueh'},
                                  {'action': 'CALL',
                                   'amount': 40,
                                   'paid': 20,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'}],
                      'flop': [{'action': 'CALL',
                                'amount': 0,
                                'paid': 0,
                                'uuid': 'ezuvdegskltrhzvsoiimcm'},
                               {'action': 'RAISE',
                                'amount': 20,
                                'paid': 20,
                                'add_amount': 20,
                                'uuid': 'mgtzikgmdfwidoyqymhueh'},
                               {'action': 'CALL',
                                'amount': 20,
                                'paid': 20,
                                'uuid': 'ezuvdegskltrhzvsoiimcm'}],
                      'turn': []}}
```

### Decision 21

- player: `player_a`
- round_count: `6`
- street: `turn`
- chosen_action: `{'action': 'raise', 'amount': None}`

#### valid_actions

```python
[{'action': 'fold'}, {'action': 'call'}, {'action': 'raise'}]
```

#### hole_card

```python
['H9', 'DK']
```

#### round_state

```python
{'street': 'turn',
 'pot': {'main': {'amount': 240}, 'side': []},
 'community_card': ['S2', 'DT', 'HT', 'CK'],
 'dealer_btn': 1,
 'next_player': 0,
 'small_blind_pos': 0,
 'big_blind_pos': 1,
 'round_count': 6,
 'small_blind_amount': 10,
 'seats': [{'name': 'player_a',
            'uuid': 'ezuvdegskltrhzvsoiimcm',
            'stack': 200,
            'state': 'participating'},
           {'name': 'player_b',
            'uuid': 'mgtzikgmdfwidoyqymhueh',
            'stack': 560,
            'state': 'participating'}],
 'action_histories': {'preflop': [{'action': 'SMALLBLIND',
                                   'amount': 10,
                                   'add_amount': 10,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'},
                                  {'action': 'BIGBLIND',
                                   'amount': 20,
                                   'add_amount': 10,
                                   'uuid': 'mgtzikgmdfwidoyqymhueh'},
                                  {'action': 'CALL',
                                   'amount': 20,
                                   'paid': 10,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'},
                                  {'action': 'RAISE',
                                   'amount': 40,
                                   'paid': 20,
                                   'add_amount': 20,
                                   'uuid': 'mgtzikgmdfwidoyqymhueh'},
                                  {'action': 'CALL',
                                   'amount': 40,
                                   'paid': 20,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'}],
                      'flop': [{'action': 'CALL',
                                'amount': 0,
                                'paid': 0,
                                'uuid': 'ezuvdegskltrhzvsoiimcm'},
                               {'action': 'RAISE',
                                'amount': 20,
                                'paid': 20,
                                'add_amount': 20,
                                'uuid': 'mgtzikgmdfwidoyqymhueh'},
                               {'action': 'CALL',
                                'amount': 20,
                                'paid': 20,
                                'uuid': 'ezuvdegskltrhzvsoiimcm'}],
                      'turn': [{'action': 'RAISE',
                                'amount': 40,
                                'paid': 40,
                                'add_amount': 40,
                                'uuid': 'ezuvdegskltrhzvsoiimcm'},
                               {'action': 'RAISE',
                                'amount': 80,
                                'paid': 80,
                                'add_amount': 40,
                                'uuid': 'mgtzikgmdfwidoyqymhueh'}]}}
```

### Decision 22

- player: `player_a`
- round_count: `6`
- street: `turn`
- chosen_action: `{'action': 'call', 'amount': None}`

#### valid_actions

```python
[{'action': 'fold'}, {'action': 'call'}]
```

#### hole_card

```python
['H9', 'DK']
```

#### round_state

```python
{'street': 'turn',
 'pot': {'main': {'amount': 400}, 'side': []},
 'community_card': ['S2', 'DT', 'HT', 'CK'],
 'dealer_btn': 1,
 'next_player': 0,
 'small_blind_pos': 0,
 'big_blind_pos': 1,
 'round_count': 6,
 'small_blind_amount': 10,
 'seats': [{'name': 'player_a',
            'uuid': 'ezuvdegskltrhzvsoiimcm',
            'stack': 120,
            'state': 'participating'},
           {'name': 'player_b',
            'uuid': 'mgtzikgmdfwidoyqymhueh',
            'stack': 480,
            'state': 'participating'}],
 'action_histories': {'preflop': [{'action': 'SMALLBLIND',
                                   'amount': 10,
                                   'add_amount': 10,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'},
                                  {'action': 'BIGBLIND',
                                   'amount': 20,
                                   'add_amount': 10,
                                   'uuid': 'mgtzikgmdfwidoyqymhueh'},
                                  {'action': 'CALL',
                                   'amount': 20,
                                   'paid': 10,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'},
                                  {'action': 'RAISE',
                                   'amount': 40,
                                   'paid': 20,
                                   'add_amount': 20,
                                   'uuid': 'mgtzikgmdfwidoyqymhueh'},
                                  {'action': 'CALL',
                                   'amount': 40,
                                   'paid': 20,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'}],
                      'flop': [{'action': 'CALL',
                                'amount': 0,
                                'paid': 0,
                                'uuid': 'ezuvdegskltrhzvsoiimcm'},
                               {'action': 'RAISE',
                                'amount': 20,
                                'paid': 20,
                                'add_amount': 20,
                                'uuid': 'mgtzikgmdfwidoyqymhueh'},
                               {'action': 'CALL',
                                'amount': 20,
                                'paid': 20,
                                'uuid': 'ezuvdegskltrhzvsoiimcm'}],
                      'turn': [{'action': 'RAISE',
                                'amount': 40,
                                'paid': 40,
                                'add_amount': 40,
                                'uuid': 'ezuvdegskltrhzvsoiimcm'},
                               {'action': 'RAISE',
                                'amount': 80,
                                'paid': 80,
                                'add_amount': 40,
                                'uuid': 'mgtzikgmdfwidoyqymhueh'},
                               {'action': 'RAISE',
                                'amount': 120,
                                'paid': 80,
                                'add_amount': 40,
                                'uuid': 'ezuvdegskltrhzvsoiimcm'},
                               {'action': 'RAISE',
                                'amount': 160,
                                'paid': 80,
                                'add_amount': 40,
                                'uuid': 'mgtzikgmdfwidoyqymhueh'}]}}
```

### Decision 23

- player: `player_a`
- round_count: `6`
- street: `river`
- chosen_action: `{'action': 'raise', 'amount': None}`

#### valid_actions

```python
[{'action': 'fold'}, {'action': 'call'}, {'action': 'raise'}]
```

#### hole_card

```python
['H9', 'DK']
```

#### round_state

```python
{'street': 'river',
 'pot': {'main': {'amount': 440}, 'side': []},
 'community_card': ['S2', 'DT', 'HT', 'CK', 'DJ'],
 'dealer_btn': 1,
 'next_player': 0,
 'small_blind_pos': 0,
 'big_blind_pos': 1,
 'round_count': 6,
 'small_blind_amount': 10,
 'seats': [{'name': 'player_a',
            'uuid': 'ezuvdegskltrhzvsoiimcm',
            'stack': 80,
            'state': 'participating'},
           {'name': 'player_b',
            'uuid': 'mgtzikgmdfwidoyqymhueh',
            'stack': 480,
            'state': 'participating'}],
 'action_histories': {'preflop': [{'action': 'SMALLBLIND',
                                   'amount': 10,
                                   'add_amount': 10,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'},
                                  {'action': 'BIGBLIND',
                                   'amount': 20,
                                   'add_amount': 10,
                                   'uuid': 'mgtzikgmdfwidoyqymhueh'},
                                  {'action': 'CALL',
                                   'amount': 20,
                                   'paid': 10,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'},
                                  {'action': 'RAISE',
                                   'amount': 40,
                                   'paid': 20,
                                   'add_amount': 20,
                                   'uuid': 'mgtzikgmdfwidoyqymhueh'},
                                  {'action': 'CALL',
                                   'amount': 40,
                                   'paid': 20,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'}],
                      'flop': [{'action': 'CALL',
                                'amount': 0,
                                'paid': 0,
                                'uuid': 'ezuvdegskltrhzvsoiimcm'},
                               {'action': 'RAISE',
                                'amount': 20,
                                'paid': 20,
                                'add_amount': 20,
                                'uuid': 'mgtzikgmdfwidoyqymhueh'},
                               {'action': 'CALL',
                                'amount': 20,
                                'paid': 20,
                                'uuid': 'ezuvdegskltrhzvsoiimcm'}],
                      'turn': [{'action': 'RAISE',
                                'amount': 40,
                                'paid': 40,
                                'add_amount': 40,
                                'uuid': 'ezuvdegskltrhzvsoiimcm'},
                               {'action': 'RAISE',
                                'amount': 80,
                                'paid': 80,
                                'add_amount': 40,
                                'uuid': 'mgtzikgmdfwidoyqymhueh'},
                               {'action': 'RAISE',
                                'amount': 120,
                                'paid': 80,
                                'add_amount': 40,
                                'uuid': 'ezuvdegskltrhzvsoiimcm'},
                               {'action': 'RAISE',
                                'amount': 160,
                                'paid': 80,
                                'add_amount': 40,
                                'uuid': 'mgtzikgmdfwidoyqymhueh'},
                               {'action': 'CALL',
                                'amount': 160,
                                'paid': 40,
                                'uuid': 'ezuvdegskltrhzvsoiimcm'}],
                      'river': []}}
```

### Decision 24

- player: `player_a`
- round_count: `7`
- street: `preflop`
- chosen_action: `{'action': 'call', 'amount': None}`

#### valid_actions

```python
[{'action': 'fold'}, {'action': 'call'}, {'action': 'raise'}]
```

#### hole_card

```python
['HK', 'D8']
```

#### round_state

```python
{'street': 'preflop',
 'pot': {'main': {'amount': 60}, 'side': []},
 'community_card': [],
 'dealer_btn': 0,
 'next_player': 0,
 'small_blind_pos': 1,
 'big_blind_pos': 0,
 'round_count': 7,
 'small_blind_amount': 10,
 'seats': [{'name': 'player_a',
            'uuid': 'ezuvdegskltrhzvsoiimcm',
            'stack': 540,
            'state': 'participating'},
           {'name': 'player_b',
            'uuid': 'mgtzikgmdfwidoyqymhueh',
            'stack': 400,
            'state': 'participating'}],
 'action_histories': {'preflop': [{'action': 'SMALLBLIND',
                                   'amount': 10,
                                   'add_amount': 10,
                                   'uuid': 'mgtzikgmdfwidoyqymhueh'},
                                  {'action': 'BIGBLIND',
                                   'amount': 20,
                                   'add_amount': 10,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'},
                                  {'action': 'RAISE',
                                   'amount': 40,
                                   'paid': 30,
                                   'add_amount': 20,
                                   'uuid': 'mgtzikgmdfwidoyqymhueh'}]}}
```

### Decision 25

- player: `player_a`
- round_count: `7`
- street: `flop`
- chosen_action: `{'action': 'call', 'amount': None}`

#### valid_actions

```python
[{'action': 'fold'}, {'action': 'call'}, {'action': 'raise'}]
```

#### hole_card

```python
['HK', 'D8']
```

#### round_state

```python
{'street': 'flop',
 'pot': {'main': {'amount': 100}, 'side': []},
 'community_card': ['S4', 'C3', 'DT'],
 'dealer_btn': 0,
 'next_player': 0,
 'small_blind_pos': 1,
 'big_blind_pos': 0,
 'round_count': 7,
 'small_blind_amount': 10,
 'seats': [{'name': 'player_a',
            'uuid': 'ezuvdegskltrhzvsoiimcm',
            'stack': 520,
            'state': 'participating'},
           {'name': 'player_b',
            'uuid': 'mgtzikgmdfwidoyqymhueh',
            'stack': 380,
            'state': 'participating'}],
 'action_histories': {'preflop': [{'action': 'SMALLBLIND',
                                   'amount': 10,
                                   'add_amount': 10,
                                   'uuid': 'mgtzikgmdfwidoyqymhueh'},
                                  {'action': 'BIGBLIND',
                                   'amount': 20,
                                   'add_amount': 10,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'},
                                  {'action': 'RAISE',
                                   'amount': 40,
                                   'paid': 30,
                                   'add_amount': 20,
                                   'uuid': 'mgtzikgmdfwidoyqymhueh'},
                                  {'action': 'CALL',
                                   'amount': 40,
                                   'paid': 20,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'}],
                      'flop': [{'action': 'RAISE',
                                'amount': 20,
                                'paid': 20,
                                'add_amount': 20,
                                'uuid': 'mgtzikgmdfwidoyqymhueh'}]}}
```

### Decision 26

- player: `player_a`
- round_count: `7`
- street: `turn`
- chosen_action: `{'action': 'call', 'amount': None}`

#### valid_actions

```python
[{'action': 'fold'}, {'action': 'call'}, {'action': 'raise'}]
```

#### hole_card

```python
['HK', 'D8']
```

#### round_state

```python
{'street': 'turn',
 'pot': {'main': {'amount': 160}, 'side': []},
 'community_card': ['S4', 'C3', 'DT', 'ST'],
 'dealer_btn': 0,
 'next_player': 0,
 'small_blind_pos': 1,
 'big_blind_pos': 0,
 'round_count': 7,
 'small_blind_amount': 10,
 'seats': [{'name': 'player_a',
            'uuid': 'ezuvdegskltrhzvsoiimcm',
            'stack': 500,
            'state': 'participating'},
           {'name': 'player_b',
            'uuid': 'mgtzikgmdfwidoyqymhueh',
            'stack': 340,
            'state': 'participating'}],
 'action_histories': {'preflop': [{'action': 'SMALLBLIND',
                                   'amount': 10,
                                   'add_amount': 10,
                                   'uuid': 'mgtzikgmdfwidoyqymhueh'},
                                  {'action': 'BIGBLIND',
                                   'amount': 20,
                                   'add_amount': 10,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'},
                                  {'action': 'RAISE',
                                   'amount': 40,
                                   'paid': 30,
                                   'add_amount': 20,
                                   'uuid': 'mgtzikgmdfwidoyqymhueh'},
                                  {'action': 'CALL',
                                   'amount': 40,
                                   'paid': 20,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'}],
                      'flop': [{'action': 'RAISE',
                                'amount': 20,
                                'paid': 20,
                                'add_amount': 20,
                                'uuid': 'mgtzikgmdfwidoyqymhueh'},
                               {'action': 'CALL',
                                'amount': 20,
                                'paid': 20,
                                'uuid': 'ezuvdegskltrhzvsoiimcm'}],
                      'turn': [{'action': 'RAISE',
                                'amount': 40,
                                'paid': 40,
                                'add_amount': 40,
                                'uuid': 'mgtzikgmdfwidoyqymhueh'}]}}
```

### Decision 27

- player: `player_a`
- round_count: `7`
- street: `river`
- chosen_action: `{'action': 'call', 'amount': None}`

#### valid_actions

```python
[{'action': 'fold'}, {'action': 'call'}, {'action': 'raise'}]
```

#### hole_card

```python
['HK', 'D8']
```

#### round_state

```python
{'street': 'river',
 'pot': {'main': {'amount': 240}, 'side': []},
 'community_card': ['S4', 'C3', 'DT', 'ST', 'D4'],
 'dealer_btn': 0,
 'next_player': 0,
 'small_blind_pos': 1,
 'big_blind_pos': 0,
 'round_count': 7,
 'small_blind_amount': 10,
 'seats': [{'name': 'player_a',
            'uuid': 'ezuvdegskltrhzvsoiimcm',
            'stack': 460,
            'state': 'participating'},
           {'name': 'player_b',
            'uuid': 'mgtzikgmdfwidoyqymhueh',
            'stack': 300,
            'state': 'participating'}],
 'action_histories': {'preflop': [{'action': 'SMALLBLIND',
                                   'amount': 10,
                                   'add_amount': 10,
                                   'uuid': 'mgtzikgmdfwidoyqymhueh'},
                                  {'action': 'BIGBLIND',
                                   'amount': 20,
                                   'add_amount': 10,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'},
                                  {'action': 'RAISE',
                                   'amount': 40,
                                   'paid': 30,
                                   'add_amount': 20,
                                   'uuid': 'mgtzikgmdfwidoyqymhueh'},
                                  {'action': 'CALL',
                                   'amount': 40,
                                   'paid': 20,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'}],
                      'flop': [{'action': 'RAISE',
                                'amount': 20,
                                'paid': 20,
                                'add_amount': 20,
                                'uuid': 'mgtzikgmdfwidoyqymhueh'},
                               {'action': 'CALL',
                                'amount': 20,
                                'paid': 20,
                                'uuid': 'ezuvdegskltrhzvsoiimcm'}],
                      'turn': [{'action': 'RAISE',
                                'amount': 40,
                                'paid': 40,
                                'add_amount': 40,
                                'uuid': 'mgtzikgmdfwidoyqymhueh'},
                               {'action': 'CALL',
                                'amount': 40,
                                'paid': 40,
                                'uuid': 'ezuvdegskltrhzvsoiimcm'}],
                      'river': [{'action': 'RAISE',
                                 'amount': 40,
                                 'paid': 40,
                                 'add_amount': 40,
                                 'uuid': 'mgtzikgmdfwidoyqymhueh'}]}}
```

### Decision 28

- player: `player_a`
- round_count: `8`
- street: `preflop`
- chosen_action: `{'action': 'call', 'amount': None}`

#### valid_actions

```python
[{'action': 'fold'}, {'action': 'call'}, {'action': 'raise'}]
```

#### hole_card

```python
['H7', 'DA']
```

#### round_state

```python
{'street': 'preflop',
 'pot': {'main': {'amount': 30}, 'side': []},
 'community_card': [],
 'dealer_btn': 1,
 'next_player': 0,
 'small_blind_pos': 0,
 'big_blind_pos': 1,
 'round_count': 8,
 'small_blind_amount': 10,
 'seats': [{'name': 'player_a',
            'uuid': 'ezuvdegskltrhzvsoiimcm',
            'stack': 410,
            'state': 'participating'},
           {'name': 'player_b',
            'uuid': 'mgtzikgmdfwidoyqymhueh',
            'stack': 560,
            'state': 'participating'}],
 'action_histories': {'preflop': [{'action': 'SMALLBLIND',
                                   'amount': 10,
                                   'add_amount': 10,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'},
                                  {'action': 'BIGBLIND',
                                   'amount': 20,
                                   'add_amount': 10,
                                   'uuid': 'mgtzikgmdfwidoyqymhueh'}]}}
```

### Decision 29

- player: `player_a`
- round_count: `8`
- street: `preflop`
- chosen_action: `{'action': 'call', 'amount': None}`

#### valid_actions

```python
[{'action': 'fold'}, {'action': 'call'}, {'action': 'raise'}]
```

#### hole_card

```python
['H7', 'DA']
```

#### round_state

```python
{'street': 'preflop',
 'pot': {'main': {'amount': 60}, 'side': []},
 'community_card': [],
 'dealer_btn': 1,
 'next_player': 0,
 'small_blind_pos': 0,
 'big_blind_pos': 1,
 'round_count': 8,
 'small_blind_amount': 10,
 'seats': [{'name': 'player_a',
            'uuid': 'ezuvdegskltrhzvsoiimcm',
            'stack': 400,
            'state': 'participating'},
           {'name': 'player_b',
            'uuid': 'mgtzikgmdfwidoyqymhueh',
            'stack': 540,
            'state': 'participating'}],
 'action_histories': {'preflop': [{'action': 'SMALLBLIND',
                                   'amount': 10,
                                   'add_amount': 10,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'},
                                  {'action': 'BIGBLIND',
                                   'amount': 20,
                                   'add_amount': 10,
                                   'uuid': 'mgtzikgmdfwidoyqymhueh'},
                                  {'action': 'CALL',
                                   'amount': 20,
                                   'paid': 10,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'},
                                  {'action': 'RAISE',
                                   'amount': 40,
                                   'paid': 20,
                                   'add_amount': 20,
                                   'uuid': 'mgtzikgmdfwidoyqymhueh'}]}}
```

### Decision 30

- player: `player_a`
- round_count: `8`
- street: `flop`
- chosen_action: `{'action': 'call', 'amount': None}`

#### valid_actions

```python
[{'action': 'fold'}, {'action': 'call'}, {'action': 'raise'}]
```

#### hole_card

```python
['H7', 'DA']
```

#### round_state

```python
{'street': 'flop',
 'pot': {'main': {'amount': 80}, 'side': []},
 'community_card': ['ST', 'D9', 'S8'],
 'dealer_btn': 1,
 'next_player': 0,
 'small_blind_pos': 0,
 'big_blind_pos': 1,
 'round_count': 8,
 'small_blind_amount': 10,
 'seats': [{'name': 'player_a',
            'uuid': 'ezuvdegskltrhzvsoiimcm',
            'stack': 380,
            'state': 'participating'},
           {'name': 'player_b',
            'uuid': 'mgtzikgmdfwidoyqymhueh',
            'stack': 540,
            'state': 'participating'}],
 'action_histories': {'preflop': [{'action': 'SMALLBLIND',
                                   'amount': 10,
                                   'add_amount': 10,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'},
                                  {'action': 'BIGBLIND',
                                   'amount': 20,
                                   'add_amount': 10,
                                   'uuid': 'mgtzikgmdfwidoyqymhueh'},
                                  {'action': 'CALL',
                                   'amount': 20,
                                   'paid': 10,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'},
                                  {'action': 'RAISE',
                                   'amount': 40,
                                   'paid': 20,
                                   'add_amount': 20,
                                   'uuid': 'mgtzikgmdfwidoyqymhueh'},
                                  {'action': 'CALL',
                                   'amount': 40,
                                   'paid': 20,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'}],
                      'flop': []}}
```

### Decision 31

- player: `player_a`
- round_count: `8`
- street: `flop`
- chosen_action: `{'action': 'call', 'amount': None}`

#### valid_actions

```python
[{'action': 'fold'}, {'action': 'call'}, {'action': 'raise'}]
```

#### hole_card

```python
['H7', 'DA']
```

#### round_state

```python
{'street': 'flop',
 'pot': {'main': {'amount': 100}, 'side': []},
 'community_card': ['ST', 'D9', 'S8'],
 'dealer_btn': 1,
 'next_player': 0,
 'small_blind_pos': 0,
 'big_blind_pos': 1,
 'round_count': 8,
 'small_blind_amount': 10,
 'seats': [{'name': 'player_a',
            'uuid': 'ezuvdegskltrhzvsoiimcm',
            'stack': 380,
            'state': 'participating'},
           {'name': 'player_b',
            'uuid': 'mgtzikgmdfwidoyqymhueh',
            'stack': 520,
            'state': 'participating'}],
 'action_histories': {'preflop': [{'action': 'SMALLBLIND',
                                   'amount': 10,
                                   'add_amount': 10,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'},
                                  {'action': 'BIGBLIND',
                                   'amount': 20,
                                   'add_amount': 10,
                                   'uuid': 'mgtzikgmdfwidoyqymhueh'},
                                  {'action': 'CALL',
                                   'amount': 20,
                                   'paid': 10,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'},
                                  {'action': 'RAISE',
                                   'amount': 40,
                                   'paid': 20,
                                   'add_amount': 20,
                                   'uuid': 'mgtzikgmdfwidoyqymhueh'},
                                  {'action': 'CALL',
                                   'amount': 40,
                                   'paid': 20,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'}],
                      'flop': [{'action': 'CALL',
                                'amount': 0,
                                'paid': 0,
                                'uuid': 'ezuvdegskltrhzvsoiimcm'},
                               {'action': 'RAISE',
                                'amount': 20,
                                'paid': 20,
                                'add_amount': 20,
                                'uuid': 'mgtzikgmdfwidoyqymhueh'}]}}
```

### Decision 32

- player: `player_a`
- round_count: `8`
- street: `turn`
- chosen_action: `{'action': 'call', 'amount': None}`

#### valid_actions

```python
[{'action': 'fold'}, {'action': 'call'}, {'action': 'raise'}]
```

#### hole_card

```python
['H7', 'DA']
```

#### round_state

```python
{'street': 'turn',
 'pot': {'main': {'amount': 120}, 'side': []},
 'community_card': ['ST', 'D9', 'S8', 'S9'],
 'dealer_btn': 1,
 'next_player': 0,
 'small_blind_pos': 0,
 'big_blind_pos': 1,
 'round_count': 8,
 'small_blind_amount': 10,
 'seats': [{'name': 'player_a',
            'uuid': 'ezuvdegskltrhzvsoiimcm',
            'stack': 360,
            'state': 'participating'},
           {'name': 'player_b',
            'uuid': 'mgtzikgmdfwidoyqymhueh',
            'stack': 520,
            'state': 'participating'}],
 'action_histories': {'preflop': [{'action': 'SMALLBLIND',
                                   'amount': 10,
                                   'add_amount': 10,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'},
                                  {'action': 'BIGBLIND',
                                   'amount': 20,
                                   'add_amount': 10,
                                   'uuid': 'mgtzikgmdfwidoyqymhueh'},
                                  {'action': 'CALL',
                                   'amount': 20,
                                   'paid': 10,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'},
                                  {'action': 'RAISE',
                                   'amount': 40,
                                   'paid': 20,
                                   'add_amount': 20,
                                   'uuid': 'mgtzikgmdfwidoyqymhueh'},
                                  {'action': 'CALL',
                                   'amount': 40,
                                   'paid': 20,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'}],
                      'flop': [{'action': 'CALL',
                                'amount': 0,
                                'paid': 0,
                                'uuid': 'ezuvdegskltrhzvsoiimcm'},
                               {'action': 'RAISE',
                                'amount': 20,
                                'paid': 20,
                                'add_amount': 20,
                                'uuid': 'mgtzikgmdfwidoyqymhueh'},
                               {'action': 'CALL',
                                'amount': 20,
                                'paid': 20,
                                'uuid': 'ezuvdegskltrhzvsoiimcm'}],
                      'turn': []}}
```

### Decision 33

- player: `player_a`
- round_count: `8`
- street: `turn`
- chosen_action: `{'action': 'fold', 'amount': None}`

#### valid_actions

```python
[{'action': 'fold'}, {'action': 'call'}, {'action': 'raise'}]
```

#### hole_card

```python
['H7', 'DA']
```

#### round_state

```python
{'street': 'turn',
 'pot': {'main': {'amount': 160}, 'side': []},
 'community_card': ['ST', 'D9', 'S8', 'S9'],
 'dealer_btn': 1,
 'next_player': 0,
 'small_blind_pos': 0,
 'big_blind_pos': 1,
 'round_count': 8,
 'small_blind_amount': 10,
 'seats': [{'name': 'player_a',
            'uuid': 'ezuvdegskltrhzvsoiimcm',
            'stack': 360,
            'state': 'participating'},
           {'name': 'player_b',
            'uuid': 'mgtzikgmdfwidoyqymhueh',
            'stack': 480,
            'state': 'participating'}],
 'action_histories': {'preflop': [{'action': 'SMALLBLIND',
                                   'amount': 10,
                                   'add_amount': 10,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'},
                                  {'action': 'BIGBLIND',
                                   'amount': 20,
                                   'add_amount': 10,
                                   'uuid': 'mgtzikgmdfwidoyqymhueh'},
                                  {'action': 'CALL',
                                   'amount': 20,
                                   'paid': 10,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'},
                                  {'action': 'RAISE',
                                   'amount': 40,
                                   'paid': 20,
                                   'add_amount': 20,
                                   'uuid': 'mgtzikgmdfwidoyqymhueh'},
                                  {'action': 'CALL',
                                   'amount': 40,
                                   'paid': 20,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'}],
                      'flop': [{'action': 'CALL',
                                'amount': 0,
                                'paid': 0,
                                'uuid': 'ezuvdegskltrhzvsoiimcm'},
                               {'action': 'RAISE',
                                'amount': 20,
                                'paid': 20,
                                'add_amount': 20,
                                'uuid': 'mgtzikgmdfwidoyqymhueh'},
                               {'action': 'CALL',
                                'amount': 20,
                                'paid': 20,
                                'uuid': 'ezuvdegskltrhzvsoiimcm'}],
                      'turn': [{'action': 'CALL',
                                'amount': 0,
                                'paid': 0,
                                'uuid': 'ezuvdegskltrhzvsoiimcm'},
                               {'action': 'RAISE',
                                'amount': 40,
                                'paid': 40,
                                'add_amount': 40,
                                'uuid': 'mgtzikgmdfwidoyqymhueh'}]}}
```

### Decision 34

- player: `player_a`
- round_count: `9`
- street: `preflop`
- chosen_action: `{'action': 'call', 'amount': None}`

#### valid_actions

```python
[{'action': 'fold'}, {'action': 'call'}, {'action': 'raise'}]
```

#### hole_card

```python
['CT', 'DK']
```

#### round_state

```python
{'street': 'preflop',
 'pot': {'main': {'amount': 60}, 'side': []},
 'community_card': [],
 'dealer_btn': 0,
 'next_player': 0,
 'small_blind_pos': 1,
 'big_blind_pos': 0,
 'round_count': 9,
 'small_blind_amount': 10,
 'seats': [{'name': 'player_a',
            'uuid': 'ezuvdegskltrhzvsoiimcm',
            'stack': 340,
            'state': 'participating'},
           {'name': 'player_b',
            'uuid': 'mgtzikgmdfwidoyqymhueh',
            'stack': 600,
            'state': 'participating'}],
 'action_histories': {'preflop': [{'action': 'SMALLBLIND',
                                   'amount': 10,
                                   'add_amount': 10,
                                   'uuid': 'mgtzikgmdfwidoyqymhueh'},
                                  {'action': 'BIGBLIND',
                                   'amount': 20,
                                   'add_amount': 10,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'},
                                  {'action': 'RAISE',
                                   'amount': 40,
                                   'paid': 30,
                                   'add_amount': 20,
                                   'uuid': 'mgtzikgmdfwidoyqymhueh'}]}}
```

### Decision 35

- player: `player_a`
- round_count: `9`
- street: `flop`
- chosen_action: `{'action': 'call', 'amount': None}`

#### valid_actions

```python
[{'action': 'fold'}, {'action': 'call'}, {'action': 'raise'}]
```

#### hole_card

```python
['CT', 'DK']
```

#### round_state

```python
{'street': 'flop',
 'pot': {'main': {'amount': 100}, 'side': []},
 'community_card': ['D9', 'D4', 'H5'],
 'dealer_btn': 0,
 'next_player': 0,
 'small_blind_pos': 1,
 'big_blind_pos': 0,
 'round_count': 9,
 'small_blind_amount': 10,
 'seats': [{'name': 'player_a',
            'uuid': 'ezuvdegskltrhzvsoiimcm',
            'stack': 320,
            'state': 'participating'},
           {'name': 'player_b',
            'uuid': 'mgtzikgmdfwidoyqymhueh',
            'stack': 580,
            'state': 'participating'}],
 'action_histories': {'preflop': [{'action': 'SMALLBLIND',
                                   'amount': 10,
                                   'add_amount': 10,
                                   'uuid': 'mgtzikgmdfwidoyqymhueh'},
                                  {'action': 'BIGBLIND',
                                   'amount': 20,
                                   'add_amount': 10,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'},
                                  {'action': 'RAISE',
                                   'amount': 40,
                                   'paid': 30,
                                   'add_amount': 20,
                                   'uuid': 'mgtzikgmdfwidoyqymhueh'},
                                  {'action': 'CALL',
                                   'amount': 40,
                                   'paid': 20,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'}],
                      'flop': [{'action': 'RAISE',
                                'amount': 20,
                                'paid': 20,
                                'add_amount': 20,
                                'uuid': 'mgtzikgmdfwidoyqymhueh'}]}}
```

### Decision 36

- player: `player_a`
- round_count: `9`
- street: `turn`
- chosen_action: `{'action': 'call', 'amount': None}`

#### valid_actions

```python
[{'action': 'fold'}, {'action': 'call'}, {'action': 'raise'}]
```

#### hole_card

```python
['CT', 'DK']
```

#### round_state

```python
{'street': 'turn',
 'pot': {'main': {'amount': 160}, 'side': []},
 'community_card': ['D9', 'D4', 'H5', 'D5'],
 'dealer_btn': 0,
 'next_player': 0,
 'small_blind_pos': 1,
 'big_blind_pos': 0,
 'round_count': 9,
 'small_blind_amount': 10,
 'seats': [{'name': 'player_a',
            'uuid': 'ezuvdegskltrhzvsoiimcm',
            'stack': 300,
            'state': 'participating'},
           {'name': 'player_b',
            'uuid': 'mgtzikgmdfwidoyqymhueh',
            'stack': 540,
            'state': 'participating'}],
 'action_histories': {'preflop': [{'action': 'SMALLBLIND',
                                   'amount': 10,
                                   'add_amount': 10,
                                   'uuid': 'mgtzikgmdfwidoyqymhueh'},
                                  {'action': 'BIGBLIND',
                                   'amount': 20,
                                   'add_amount': 10,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'},
                                  {'action': 'RAISE',
                                   'amount': 40,
                                   'paid': 30,
                                   'add_amount': 20,
                                   'uuid': 'mgtzikgmdfwidoyqymhueh'},
                                  {'action': 'CALL',
                                   'amount': 40,
                                   'paid': 20,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'}],
                      'flop': [{'action': 'RAISE',
                                'amount': 20,
                                'paid': 20,
                                'add_amount': 20,
                                'uuid': 'mgtzikgmdfwidoyqymhueh'},
                               {'action': 'CALL',
                                'amount': 20,
                                'paid': 20,
                                'uuid': 'ezuvdegskltrhzvsoiimcm'}],
                      'turn': [{'action': 'RAISE',
                                'amount': 40,
                                'paid': 40,
                                'add_amount': 40,
                                'uuid': 'mgtzikgmdfwidoyqymhueh'}]}}
```

### Decision 37

- player: `player_a`
- round_count: `9`
- street: `river`
- chosen_action: `{'action': 'fold', 'amount': None}`

#### valid_actions

```python
[{'action': 'fold'}, {'action': 'call'}, {'action': 'raise'}]
```

#### hole_card

```python
['CT', 'DK']
```

#### round_state

```python
{'street': 'river',
 'pot': {'main': {'amount': 240}, 'side': []},
 'community_card': ['D9', 'D4', 'H5', 'D5', 'CA'],
 'dealer_btn': 0,
 'next_player': 0,
 'small_blind_pos': 1,
 'big_blind_pos': 0,
 'round_count': 9,
 'small_blind_amount': 10,
 'seats': [{'name': 'player_a',
            'uuid': 'ezuvdegskltrhzvsoiimcm',
            'stack': 260,
            'state': 'participating'},
           {'name': 'player_b',
            'uuid': 'mgtzikgmdfwidoyqymhueh',
            'stack': 500,
            'state': 'participating'}],
 'action_histories': {'preflop': [{'action': 'SMALLBLIND',
                                   'amount': 10,
                                   'add_amount': 10,
                                   'uuid': 'mgtzikgmdfwidoyqymhueh'},
                                  {'action': 'BIGBLIND',
                                   'amount': 20,
                                   'add_amount': 10,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'},
                                  {'action': 'RAISE',
                                   'amount': 40,
                                   'paid': 30,
                                   'add_amount': 20,
                                   'uuid': 'mgtzikgmdfwidoyqymhueh'},
                                  {'action': 'CALL',
                                   'amount': 40,
                                   'paid': 20,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'}],
                      'flop': [{'action': 'RAISE',
                                'amount': 20,
                                'paid': 20,
                                'add_amount': 20,
                                'uuid': 'mgtzikgmdfwidoyqymhueh'},
                               {'action': 'CALL',
                                'amount': 20,
                                'paid': 20,
                                'uuid': 'ezuvdegskltrhzvsoiimcm'}],
                      'turn': [{'action': 'RAISE',
                                'amount': 40,
                                'paid': 40,
                                'add_amount': 40,
                                'uuid': 'mgtzikgmdfwidoyqymhueh'},
                               {'action': 'CALL',
                                'amount': 40,
                                'paid': 40,
                                'uuid': 'ezuvdegskltrhzvsoiimcm'}],
                      'river': [{'action': 'RAISE',
                                 'amount': 40,
                                 'paid': 40,
                                 'add_amount': 40,
                                 'uuid': 'mgtzikgmdfwidoyqymhueh'}]}}
```

### Decision 38

- player: `player_a`
- round_count: `10`
- street: `preflop`
- chosen_action: `{'action': 'fold', 'amount': None}`

#### valid_actions

```python
[{'action': 'fold'}, {'action': 'call'}, {'action': 'raise'}]
```

#### hole_card

```python
['S4', 'D2']
```

#### round_state

```python
{'street': 'preflop',
 'pot': {'main': {'amount': 30}, 'side': []},
 'community_card': [],
 'dealer_btn': 1,
 'next_player': 0,
 'small_blind_pos': 0,
 'big_blind_pos': 1,
 'round_count': 10,
 'small_blind_amount': 10,
 'seats': [{'name': 'player_a',
            'uuid': 'ezuvdegskltrhzvsoiimcm',
            'stack': 250,
            'state': 'participating'},
           {'name': 'player_b',
            'uuid': 'mgtzikgmdfwidoyqymhueh',
            'stack': 720,
            'state': 'participating'}],
 'action_histories': {'preflop': [{'action': 'SMALLBLIND',
                                   'amount': 10,
                                   'add_amount': 10,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'},
                                  {'action': 'BIGBLIND',
                                   'amount': 20,
                                   'add_amount': 10,
                                   'uuid': 'mgtzikgmdfwidoyqymhueh'}]}}
```

### Decision 39

- player: `player_a`
- round_count: `11`
- street: `preflop`
- chosen_action: `{'action': 'call', 'amount': None}`

#### valid_actions

```python
[{'action': 'fold'}, {'action': 'call'}, {'action': 'raise'}]
```

#### hole_card

```python
['D2', 'CA']
```

#### round_state

```python
{'street': 'preflop',
 'pot': {'main': {'amount': 60}, 'side': []},
 'community_card': [],
 'dealer_btn': 0,
 'next_player': 0,
 'small_blind_pos': 1,
 'big_blind_pos': 0,
 'round_count': 11,
 'small_blind_amount': 10,
 'seats': [{'name': 'player_a',
            'uuid': 'ezuvdegskltrhzvsoiimcm',
            'stack': 230,
            'state': 'participating'},
           {'name': 'player_b',
            'uuid': 'mgtzikgmdfwidoyqymhueh',
            'stack': 710,
            'state': 'participating'}],
 'action_histories': {'preflop': [{'action': 'SMALLBLIND',
                                   'amount': 10,
                                   'add_amount': 10,
                                   'uuid': 'mgtzikgmdfwidoyqymhueh'},
                                  {'action': 'BIGBLIND',
                                   'amount': 20,
                                   'add_amount': 10,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'},
                                  {'action': 'RAISE',
                                   'amount': 40,
                                   'paid': 30,
                                   'add_amount': 20,
                                   'uuid': 'mgtzikgmdfwidoyqymhueh'}]}}
```

### Decision 40

- player: `player_a`
- round_count: `11`
- street: `flop`
- chosen_action: `{'action': 'raise', 'amount': None}`

#### valid_actions

```python
[{'action': 'fold'}, {'action': 'call'}, {'action': 'raise'}]
```

#### hole_card

```python
['D2', 'CA']
```

#### round_state

```python
{'street': 'flop',
 'pot': {'main': {'amount': 100}, 'side': []},
 'community_card': ['SA', 'H3', 'D8'],
 'dealer_btn': 0,
 'next_player': 0,
 'small_blind_pos': 1,
 'big_blind_pos': 0,
 'round_count': 11,
 'small_blind_amount': 10,
 'seats': [{'name': 'player_a',
            'uuid': 'ezuvdegskltrhzvsoiimcm',
            'stack': 210,
            'state': 'participating'},
           {'name': 'player_b',
            'uuid': 'mgtzikgmdfwidoyqymhueh',
            'stack': 690,
            'state': 'participating'}],
 'action_histories': {'preflop': [{'action': 'SMALLBLIND',
                                   'amount': 10,
                                   'add_amount': 10,
                                   'uuid': 'mgtzikgmdfwidoyqymhueh'},
                                  {'action': 'BIGBLIND',
                                   'amount': 20,
                                   'add_amount': 10,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'},
                                  {'action': 'RAISE',
                                   'amount': 40,
                                   'paid': 30,
                                   'add_amount': 20,
                                   'uuid': 'mgtzikgmdfwidoyqymhueh'},
                                  {'action': 'CALL',
                                   'amount': 40,
                                   'paid': 20,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'}],
                      'flop': [{'action': 'RAISE',
                                'amount': 20,
                                'paid': 20,
                                'add_amount': 20,
                                'uuid': 'mgtzikgmdfwidoyqymhueh'}]}}
```

### Decision 41

- player: `player_a`
- round_count: `11`
- street: `flop`
- chosen_action: `{'action': 'raise', 'amount': None}`

#### valid_actions

```python
[{'action': 'fold'}, {'action': 'call'}, {'action': 'raise'}]
```

#### hole_card

```python
['D2', 'CA']
```

#### round_state

```python
{'street': 'flop',
 'pot': {'main': {'amount': 180}, 'side': []},
 'community_card': ['SA', 'H3', 'D8'],
 'dealer_btn': 0,
 'next_player': 0,
 'small_blind_pos': 1,
 'big_blind_pos': 0,
 'round_count': 11,
 'small_blind_amount': 10,
 'seats': [{'name': 'player_a',
            'uuid': 'ezuvdegskltrhzvsoiimcm',
            'stack': 170,
            'state': 'participating'},
           {'name': 'player_b',
            'uuid': 'mgtzikgmdfwidoyqymhueh',
            'stack': 650,
            'state': 'participating'}],
 'action_histories': {'preflop': [{'action': 'SMALLBLIND',
                                   'amount': 10,
                                   'add_amount': 10,
                                   'uuid': 'mgtzikgmdfwidoyqymhueh'},
                                  {'action': 'BIGBLIND',
                                   'amount': 20,
                                   'add_amount': 10,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'},
                                  {'action': 'RAISE',
                                   'amount': 40,
                                   'paid': 30,
                                   'add_amount': 20,
                                   'uuid': 'mgtzikgmdfwidoyqymhueh'},
                                  {'action': 'CALL',
                                   'amount': 40,
                                   'paid': 20,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'}],
                      'flop': [{'action': 'RAISE',
                                'amount': 20,
                                'paid': 20,
                                'add_amount': 20,
                                'uuid': 'mgtzikgmdfwidoyqymhueh'},
                               {'action': 'RAISE',
                                'amount': 40,
                                'paid': 40,
                                'add_amount': 20,
                                'uuid': 'ezuvdegskltrhzvsoiimcm'},
                               {'action': 'RAISE',
                                'amount': 60,
                                'paid': 40,
                                'add_amount': 20,
                                'uuid': 'mgtzikgmdfwidoyqymhueh'}]}}
```

### Decision 42

- player: `player_a`
- round_count: `11`
- street: `turn`
- chosen_action: `{'action': 'raise', 'amount': None}`

#### valid_actions

```python
[{'action': 'fold'}, {'action': 'call'}, {'action': 'raise'}]
```

#### hole_card

```python
['D2', 'CA']
```

#### round_state

```python
{'street': 'turn',
 'pot': {'main': {'amount': 280}, 'side': []},
 'community_card': ['SA', 'H3', 'D8', 'CT'],
 'dealer_btn': 0,
 'next_player': 0,
 'small_blind_pos': 1,
 'big_blind_pos': 0,
 'round_count': 11,
 'small_blind_amount': 10,
 'seats': [{'name': 'player_a',
            'uuid': 'ezuvdegskltrhzvsoiimcm',
            'stack': 130,
            'state': 'participating'},
           {'name': 'player_b',
            'uuid': 'mgtzikgmdfwidoyqymhueh',
            'stack': 590,
            'state': 'participating'}],
 'action_histories': {'preflop': [{'action': 'SMALLBLIND',
                                   'amount': 10,
                                   'add_amount': 10,
                                   'uuid': 'mgtzikgmdfwidoyqymhueh'},
                                  {'action': 'BIGBLIND',
                                   'amount': 20,
                                   'add_amount': 10,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'},
                                  {'action': 'RAISE',
                                   'amount': 40,
                                   'paid': 30,
                                   'add_amount': 20,
                                   'uuid': 'mgtzikgmdfwidoyqymhueh'},
                                  {'action': 'CALL',
                                   'amount': 40,
                                   'paid': 20,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'}],
                      'flop': [{'action': 'RAISE',
                                'amount': 20,
                                'paid': 20,
                                'add_amount': 20,
                                'uuid': 'mgtzikgmdfwidoyqymhueh'},
                               {'action': 'RAISE',
                                'amount': 40,
                                'paid': 40,
                                'add_amount': 20,
                                'uuid': 'ezuvdegskltrhzvsoiimcm'},
                               {'action': 'RAISE',
                                'amount': 60,
                                'paid': 40,
                                'add_amount': 20,
                                'uuid': 'mgtzikgmdfwidoyqymhueh'},
                               {'action': 'RAISE',
                                'amount': 80,
                                'paid': 40,
                                'add_amount': 20,
                                'uuid': 'ezuvdegskltrhzvsoiimcm'},
                               {'action': 'CALL',
                                'amount': 80,
                                'paid': 20,
                                'uuid': 'mgtzikgmdfwidoyqymhueh'}],
                      'turn': [{'action': 'RAISE',
                                'amount': 40,
                                'paid': 40,
                                'add_amount': 40,
                                'uuid': 'mgtzikgmdfwidoyqymhueh'}]}}
```

### Decision 43

- player: `player_a`
- round_count: `11`
- street: `turn`
- chosen_action: `{'action': 'call', 'amount': None}`

#### valid_actions

```python
[{'action': 'fold'}, {'action': 'call'}, {'action': 'raise'}]
```

#### hole_card

```python
['D2', 'CA']
```

#### round_state

```python
{'street': 'turn',
 'pot': {'main': {'amount': 440}, 'side': []},
 'community_card': ['SA', 'H3', 'D8', 'CT'],
 'dealer_btn': 0,
 'next_player': 0,
 'small_blind_pos': 1,
 'big_blind_pos': 0,
 'round_count': 11,
 'small_blind_amount': 10,
 'seats': [{'name': 'player_a',
            'uuid': 'ezuvdegskltrhzvsoiimcm',
            'stack': 50,
            'state': 'participating'},
           {'name': 'player_b',
            'uuid': 'mgtzikgmdfwidoyqymhueh',
            'stack': 510,
            'state': 'participating'}],
 'action_histories': {'preflop': [{'action': 'SMALLBLIND',
                                   'amount': 10,
                                   'add_amount': 10,
                                   'uuid': 'mgtzikgmdfwidoyqymhueh'},
                                  {'action': 'BIGBLIND',
                                   'amount': 20,
                                   'add_amount': 10,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'},
                                  {'action': 'RAISE',
                                   'amount': 40,
                                   'paid': 30,
                                   'add_amount': 20,
                                   'uuid': 'mgtzikgmdfwidoyqymhueh'},
                                  {'action': 'CALL',
                                   'amount': 40,
                                   'paid': 20,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'}],
                      'flop': [{'action': 'RAISE',
                                'amount': 20,
                                'paid': 20,
                                'add_amount': 20,
                                'uuid': 'mgtzikgmdfwidoyqymhueh'},
                               {'action': 'RAISE',
                                'amount': 40,
                                'paid': 40,
                                'add_amount': 20,
                                'uuid': 'ezuvdegskltrhzvsoiimcm'},
                               {'action': 'RAISE',
                                'amount': 60,
                                'paid': 40,
                                'add_amount': 20,
                                'uuid': 'mgtzikgmdfwidoyqymhueh'},
                               {'action': 'RAISE',
                                'amount': 80,
                                'paid': 40,
                                'add_amount': 20,
                                'uuid': 'ezuvdegskltrhzvsoiimcm'},
                               {'action': 'CALL',
                                'amount': 80,
                                'paid': 20,
                                'uuid': 'mgtzikgmdfwidoyqymhueh'}],
                      'turn': [{'action': 'RAISE',
                                'amount': 40,
                                'paid': 40,
                                'add_amount': 40,
                                'uuid': 'mgtzikgmdfwidoyqymhueh'},
                               {'action': 'RAISE',
                                'amount': 80,
                                'paid': 80,
                                'add_amount': 40,
                                'uuid': 'ezuvdegskltrhzvsoiimcm'},
                               {'action': 'RAISE',
                                'amount': 120,
                                'paid': 80,
                                'add_amount': 40,
                                'uuid': 'mgtzikgmdfwidoyqymhueh'}]}}
```

### Decision 44

- player: `player_a`
- round_count: `11`
- street: `river`
- chosen_action: `{'action': 'raise', 'amount': None}`

#### valid_actions

```python
[{'action': 'fold'}, {'action': 'call'}, {'action': 'raise'}]
```

#### hole_card

```python
['D2', 'CA']
```

#### round_state

```python
{'street': 'river',
 'pot': {'main': {'amount': 480}, 'side': []},
 'community_card': ['SA', 'H3', 'D8', 'CT', 'HK'],
 'dealer_btn': 0,
 'next_player': 0,
 'small_blind_pos': 1,
 'big_blind_pos': 0,
 'round_count': 11,
 'small_blind_amount': 10,
 'seats': [{'name': 'player_a',
            'uuid': 'ezuvdegskltrhzvsoiimcm',
            'stack': 10,
            'state': 'participating'},
           {'name': 'player_b',
            'uuid': 'mgtzikgmdfwidoyqymhueh',
            'stack': 510,
            'state': 'participating'}],
 'action_histories': {'preflop': [{'action': 'SMALLBLIND',
                                   'amount': 10,
                                   'add_amount': 10,
                                   'uuid': 'mgtzikgmdfwidoyqymhueh'},
                                  {'action': 'BIGBLIND',
                                   'amount': 20,
                                   'add_amount': 10,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'},
                                  {'action': 'RAISE',
                                   'amount': 40,
                                   'paid': 30,
                                   'add_amount': 20,
                                   'uuid': 'mgtzikgmdfwidoyqymhueh'},
                                  {'action': 'CALL',
                                   'amount': 40,
                                   'paid': 20,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'}],
                      'flop': [{'action': 'RAISE',
                                'amount': 20,
                                'paid': 20,
                                'add_amount': 20,
                                'uuid': 'mgtzikgmdfwidoyqymhueh'},
                               {'action': 'RAISE',
                                'amount': 40,
                                'paid': 40,
                                'add_amount': 20,
                                'uuid': 'ezuvdegskltrhzvsoiimcm'},
                               {'action': 'RAISE',
                                'amount': 60,
                                'paid': 40,
                                'add_amount': 20,
                                'uuid': 'mgtzikgmdfwidoyqymhueh'},
                               {'action': 'RAISE',
                                'amount': 80,
                                'paid': 40,
                                'add_amount': 20,
                                'uuid': 'ezuvdegskltrhzvsoiimcm'},
                               {'action': 'CALL',
                                'amount': 80,
                                'paid': 20,
                                'uuid': 'mgtzikgmdfwidoyqymhueh'}],
                      'turn': [{'action': 'RAISE',
                                'amount': 40,
                                'paid': 40,
                                'add_amount': 40,
                                'uuid': 'mgtzikgmdfwidoyqymhueh'},
                               {'action': 'RAISE',
                                'amount': 80,
                                'paid': 80,
                                'add_amount': 40,
                                'uuid': 'ezuvdegskltrhzvsoiimcm'},
                               {'action': 'RAISE',
                                'amount': 120,
                                'paid': 80,
                                'add_amount': 40,
                                'uuid': 'mgtzikgmdfwidoyqymhueh'},
                               {'action': 'CALL',
                                'amount': 120,
                                'paid': 40,
                                'uuid': 'ezuvdegskltrhzvsoiimcm'}],
                      'river': [{'action': 'CALL',
                                 'amount': 0,
                                 'paid': 0,
                                 'uuid': 'mgtzikgmdfwidoyqymhueh'}]}}
```

### Decision 45

- player: `player_a`
- round_count: `12`
- street: `preflop`
- chosen_action: `{'action': 'raise', 'amount': None}`

#### valid_actions

```python
[{'action': 'fold'}, {'action': 'call'}, {'action': 'raise'}]
```

#### hole_card

```python
['S9', 'C9']
```

#### round_state

```python
{'street': 'preflop',
 'pot': {'main': {'amount': 30}, 'side': []},
 'community_card': [],
 'dealer_btn': 1,
 'next_player': 0,
 'small_blind_pos': 0,
 'big_blind_pos': 1,
 'round_count': 12,
 'small_blind_amount': 10,
 'seats': [{'name': 'player_a',
            'uuid': 'ezuvdegskltrhzvsoiimcm',
            'stack': 0,
            'state': 'participating'},
           {'name': 'player_b',
            'uuid': 'mgtzikgmdfwidoyqymhueh',
            'stack': 970,
            'state': 'participating'}],
 'action_histories': {'preflop': [{'action': 'SMALLBLIND',
                                   'amount': 10,
                                   'add_amount': 10,
                                   'uuid': 'ezuvdegskltrhzvsoiimcm'},
                                  {'action': 'BIGBLIND',
                                   'amount': 20,
                                   'add_amount': 10,
                                   'uuid': 'mgtzikgmdfwidoyqymhueh'}]}}
```
