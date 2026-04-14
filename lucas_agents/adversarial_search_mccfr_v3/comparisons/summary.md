# V3 Comparison Summary

Training run:
- `python3 lucas_agents/adversarial_search_mccfr_v3/train_adversarial_search_mccfr_v3_agent.py --games 240 --max-rounds-per-game 100`

Head-to-head results:
- vs `adversarial_search_mccfr_v2` (120 games): **76-44**, avg stack **632.00 vs 365.92**
- vs `learnable_discounted_mccfr` (120 games): **70-50**, avg stack **581.75 vs 415.58**
- vs `condition_threshold_player` (120 games): **45-75**, avg stack **373.67 vs 623.25**

Learned parameter snapshot:
- `refinement_weights`: average 0.0592, counterfactual 0.0456, learned 0.6158, search 0.2231, strategy 0.0563
- `search_weights`: base_action_bonus 0.0284, counterfactual 0.1530, learned 0.4275, policy_bias 0.0968, response 0.0878, rollout 0.2066
- `thresholds`: learned_override_margin 0.1152, search_blended_margin 0.0693, search_confidence_floor 0.5897, search_gate_min 0.4783, search_override_margin 0.1493, search_support_floor 0.2977

Interpretation:
- v3 improved over v2 and the learnable baseline in these runs.
- It was not robust against `condition_threshold_player`, which motivated v3.1.
