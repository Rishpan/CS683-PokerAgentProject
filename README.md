## Term Project - Rishab Pangal, Lucas Lu, Mrinaal Ramachandran

### Set up environment
using the conda or pyenv

- conda create -n CompSci683 python=x.x
- source activate CompSci683

replace the CompSci683 with whatever name you want
replace x.x with the current python version
https://conda.io/docs/index.html

pip install PyPokerEngine  
https://ishikota.github.io/PyPokerEngine/



testing installmement:

```
import pypokerengine   
print("hello world")
```

### Lucas agent packages

- `lucas_agents/advanced_cfr/`: baseline learned CFR-style agent family
- `lucas_agents/discounted_mccfr_plus/`: discounted MCCFR+ package and trainer
- `lucas_agents/learnable_discounted_mccfr/`: learnable discounted MCCFR package with online coefficient updates



### Create your own player
#### Example player

```

class RaisedPlayer(BasePokerPlayer):

  def declare_action(self, valid_actions, hole_card, round_state):
    #Implement your code
    return action

  def receive_game_start_message(self, game_info):
    pass

  def receive_round_start_message(self, round_count, hole_card, seats):
    pass

  def receive_street_start_message(self, street, round_state):
    pass

  def receive_game_update_message(self, action, round_state):
    pass

  def receive_round_result_message(self, winners, hand_info, round_state):
    pass
```
#### Example Game
The example game is in the example.py

#### Information for the game
```valid_actions```: vaild action list


```
[
    { "action" : "fold"  },
    { "action" : "call" },
    { "action" : "raise" }
]
OR 
[
    {"action": "fold"},
    {"action": "call"}
]
```

In the limited version, user only allowed to raise for four time in one round game.    
In addition, in each street (preflop,flop,turn,river),each player only allowed to raise for four times.

Other information is similar to the PyPokerEngine,please check the detail about the parameter [link](https://github.com/ishikota/PyPokerEngine/blob/master/AI_CALLBACK_FORMAT.md)
