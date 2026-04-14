# Adversarial Search MCCFR V2 Results

Saved benchmark snapshot:

- vs `learnable_discounted_mccfr` (500 games): **291-209**
- average final stack: **580.44 vs 417.52**

Interpretation:
- v2 was the first search-augmented agent that clearly outperformed the prior learnable baseline in a longer run.
- Its search layer is gated and selective rather than always overriding the anchor policy.
