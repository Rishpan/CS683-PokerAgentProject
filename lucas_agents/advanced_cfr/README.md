## Advanced CFR Player

This folder contains a compact stronger replacement for the earlier minimal CFR prototype.

Method:
- sampled regret updates from played trajectories, inspired by Monte Carlo CFR
- regret-matching+ style action selection with non-negative regrets
- periodic discounting of regrets and average strategy, following the practical idea behind discounted CFR variants
- richer abstraction: strength bucket, draw bucket, board texture, position, pot odds, stack pressure, SPR, and compressed betting history

Primary references used:
- Waugh, Lanctot, Zinkevich, Bowling, "Monte Carlo Sampling for Regret Minimization in Extensive Games" (NeurIPS 2009): https://www.cs.cmu.edu/~kwaugh/publications/nips09b.pdf
- Tammelin, "Solving Large Imperfect Information Games Using CFR+" (2014): https://arxiv.org/abs/1407.5042
- Brown and Sandholm, "Solving Imperfect-Information Games via Discounted Regret Minimization" (AAAI 2019): https://ojs.aaai.org/index.php/AAAI/article/view/4019

Train:

```bash
python3 experiment/advanced_cfr/train_advanced_cfr.py --games 200 --max-rounds-per-game 100 --stack 500
```

Evaluate against Lucas agent:

```bash
python3 experiment/regret_minimization_research/run_agent_match.py \
  /Users/xiaofanlu/Desktop/school/cs683/AI-Poker-Agent/experiment/advanced_cfr/advanced_cfr_player.py \
  /Users/xiaofanlu/Desktop/school/cs683/AI-Poker-Agent/lucas_agent/condition_threshold_player.py \
  --rounds 2000 --stack 10000
```
