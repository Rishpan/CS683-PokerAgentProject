# Adversarial Search MCCFR V3.1

v3.1 exists because `v3` could learn an effective search layer, but that layer could still become too willing to trust noisy opponent-model signals or override the anchor policy on thin evidence. This version shifts the objective from "beat one learned family harder" to "stay strong across a broader mix of opponents without brittle search jumps."

## What changed from v3

- Search overrides are more conservative. Search now needs stronger margin, blended support, and confidence before it can displace the default anchor action.
- Search is explicitly regularized toward the anchor/base policy. Candidate actions get an `anchor_alignment` term, so actions that deviate too far from the anchor lose search score unless evidence is strong.
- Opponent-model search trust is discounted when observations are sparse or unstable. v3.1 computes a smoothed opponent-model reliability score from observed raise/fold counts and reduces search leverage, response scoring, and confidence when that reliability is low.
- Online adaptation is shrunk back toward safer priors. Refinement weights, search weights, and thresholds are all nudged toward conservative defaults during training so they do not drift too aggressively after noisy rewards.
- Training uses a mixed opponent pool instead of relying on one learned family. The trainer rotates through:
  - `condition_threshold_player`
  - `advanced_cfr_player`
  - `learnable_discounted_mccfr_agent`
  - `adversarial_search_mccfr_v2_agent`

## Files

- `adversarial_search_mccfr_v3_1_agent.py`: v3.1 agent with `setup_ai()` compatibility.
- `train_adversarial_search_mccfr_v3_1_agent.py`: mixed-pool trainer for the robust search-regularized version.
- `adversarial_search_mccfr_v3_1_policy.json`: saved regrets, learned action weights, learned search parameters, and thresholds after training.
- `comparisons/`: saved comparison outputs against the requested baselines.

## Train

```bash
python3 lucas_agents/adversarial_search_mccfr_v3_1/train_adversarial_search_mccfr_v3_1_agent.py --games 480
```

## Compare

```bash
python3 compare_agents.py \
  lucas_agents/adversarial_search_mccfr_v3_1/adversarial_search_mccfr_v3_1_agent.py \
  lucas_agents/advanced_cfr/advanced_cfr_player.py
```
