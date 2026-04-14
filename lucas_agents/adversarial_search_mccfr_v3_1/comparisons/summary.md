# V3.1 Comparison Summary

Training run:
- `python3 lucas_agents/adversarial_search_mccfr_v3_1/train_adversarial_search_mccfr_v3_1_agent.py --games 480`

Saved policy stats:
- `weight_update_count=47026`
- `search_update_count=14786`
- `regret_states=10493`

Head-to-head results:
- vs `advanced_cfr_player` (50 games): **34-16**, avg stack **677.20 vs 319.40**
- vs `condition_threshold_player` (50 games): **24-26**, avg stack **489.40 vs 507.60**
- vs `adversarial_search_mccfr_v2_agent` (50 games): **28-22**, avg stack **559.60 vs 439.40**

Larger follow-up runs:
- vs `advanced_cfr_player` (300 games): **223-77**, avg stack **740.73 vs 256.17**
- vs `condition_threshold_player` (300 games): **167-133**, avg stack **558.67 vs 438.87**

Sanity baseline:
- `advanced_cfr_player` vs `condition_threshold_player` (300 games): **188-111-1**, avg stack **617.53 vs 379.57**

Interpretation:
- v3.1 preserves the search-based strength while removing most of the brittleness shown by v3.
- Over the larger 300-game checks, v3.1 beat both `advanced_cfr` and `condition_threshold_player`.
- v3.1 is the current strongest robust candidate in this folder.
