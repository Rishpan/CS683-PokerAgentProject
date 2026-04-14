# Lucas Agents

This folder contains Lucas's poker agents and supporting trainers.

## How to use a Lucas agent

Most agents expose `setup_ai()` so they can be used directly with the existing comparison harness.

Example:

```bash
python3 compare_agents.py \
  lucas_agents/adversarial_search_mccfr_v3_1/adversarial_search_mccfr_v3_1_agent.py \
  lucas_agents/advanced_cfr/advanced_cfr_player.py
```

To train an agent, run its package-specific trainer. Example:

```bash
python3 lucas_agents/adversarial_search_mccfr_v3_1/train_adversarial_search_mccfr_v3_1_agent.py --games 480
```

Policies are stored as `.json` files and should be kept in the repo.

## Current strongest agent

Current best all-around test agent: `adversarial_search_mccfr_v3_1`

Why:
- beats `advanced_cfr` over 300 games: **223-77**, avg stack **740.73 vs 256.17**
- beats `condition_threshold_player` over 300 games: **167-133**, avg stack **558.67 vs 438.87**
- beat `adversarial_search_mccfr_v2` in the latest saved comparison: **28-22**, avg stack **559.60 vs 439.40**

Important note:
- the v2 comparison above was only 50 games
- the strongest claim is that `v3_1` is the best current candidate and strongest robust agent so far
- if needed, rerun longer head-to-heads against `v2` and `learnable_discounted_mccfr` for a stricter final ranking

## Current comparison snapshot

- `advanced_cfr` vs `condition_threshold_player` (300 games): **188-111-1**, avg stack **617.53 vs 379.57**
- `learnable_discounted_mccfr` vs `advanced_cfr` (500 games): **344-156**, avg stack **685.76 vs 311.10**
- `learnable_discounted_mccfr` vs `discounted_mccfr_plus` (500 games): **316-184**, avg stack **629.74 vs 366.94**
- `adversarial_search_mccfr_v2` vs `learnable_discounted_mccfr` (500 games): **291-209**, avg stack **580.44 vs 417.52**
- `adversarial_search_mccfr_v3` vs `adversarial_search_mccfr_v2` (120 games): **76-44**, avg stack **632.00 vs 365.92**
- `adversarial_search_mccfr_v3` vs `learnable_discounted_mccfr` (120 games): **70-50**, avg stack **581.75 vs 415.58**
- `adversarial_search_mccfr_v3` vs `condition_threshold_player` (120 games): **45-75**, avg stack **373.67 vs 623.25**
- `adversarial_search_mccfr_v3_1` vs `advanced_cfr` (300 games): **223-77**, avg stack **740.73 vs 256.17**
- `adversarial_search_mccfr_v3_1` vs `condition_threshold_player` (300 games): **167-133**, avg stack **558.67 vs 438.87**
- `adversarial_search_mccfr_v3_1` vs `adversarial_search_mccfr_v2` (50 games): **28-22**, avg stack **559.60 vs 439.40**

## Agent guide

- `advanced_cfr/`: stronger practical CFR baseline with richer abstractions
- `discounted_mccfr_plus/`: discounted MCCFR-style improvement over earlier simple baselines
- `learnable_discounted_mccfr/`: discounted MCCFR with trainable action coefficients
- `adversarial_search_mccfr/`: first search-augmented attempt, mainly useful as an experiment
- `adversarial_search_mccfr_v2/`: gated search refinement over the learnable MCCFR anchor
- `adversarial_search_mccfr_v3/`: v2 plus learnable search/refinement parameters
- `adversarial_search_mccfr_v3_1/`: v3 with regularized search and mixed-opponent training, currently the strongest robust candidate
- `condition_threshold_player.py`: simple threshold-based baseline opponent
- `minimum_cfr_player.py`: smaller baseline CFR agent

## Logging policy

Large per-game comparison logs are not meant to stay in git.
Keep:
- agent code
- trainers
- policy `.json` files
- concise summary notes

Ignore:
- bulky raw comparison transcripts and progress logs
