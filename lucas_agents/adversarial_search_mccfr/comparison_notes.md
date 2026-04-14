# Quick Comparison Snapshot

Date: 2026-04-13

Command:

```bash
python3 compare_agents.py \
  lucas_agents/adversarial_search_mccfr/adversarial_search_mccfr_agent.py \
  lucas_agents/learnable_discounted_mccfr/learnable_discounted_mccfr_agent.py \
  --games 12 \
  --max-round 40 \
  --initial-stack 500 \
  --small-blind 10
```

Result:

- `learnable_discounted_mccfr_agent.py`: 9 wins, average final stack `722.50`
- `adversarial_search_mccfr_agent.py`: 3 wins, average final stack `275.83`

This was only a smoke-level comparison to confirm that the new package runs end-to-end inside the existing harness and produces measurable output. The small sample should not be treated as a stable ranking.

Raw console output is also available in `quick_compare_results.txt`.
