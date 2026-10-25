### Anomaly detection (seed 42, 12 injected anomalies)

| Method | Flagged | True positives | Precision | Recall | F1 |
|---|---|---|---|---|---|
| duplicates only | 4 | 4 | 1.0 | 0.333 | 0.5 |
| z-score only | 8 | 8 | 1.0 | 0.667 | 0.8 |
| Isolation Forest only (z>2 gate) | 16 | 8 | 0.5 | 0.667 | 0.571 |
| new-merchant only | 1 | 0 | 0.0 | 0.0 | 0.0 |
| dup + z-score (shipped) | 12 | 12 | 1.0 | 1.0 | 1.0 |
| dup + z-score + IForest | 20 | 12 | 0.6 | 1.0 | 0.75 |
| all four | 21 | 12 | 0.571 | 1.0 | 0.727 |

### Same methods on 10 other seeds (mean ± std)

| Method | Avg flagged | Precision | Recall | F1 |
|---|---|---|---|---|
| duplicates only | 4.1 | 0.98 ± 0.06 | 0.333 ± 0.0 | 0.497 ± 0.009 |
| z-score only | 8.3 | 0.702 ± 0.092 | 0.475 ± 0.075 | 0.56 ± 0.057 |
| Isolation Forest only (z>2 gate) | 15.2 | 0.516 ± 0.11 | 0.633 ± 0.041 | 0.564 ± 0.07 |
| new-merchant only | 2.7 | 0.05 ± 0.15 | 0.008 ± 0.025 | 0.014 ± 0.043 |
| dup + z-score (shipped) | 12.4 | 0.79 ± 0.065 | 0.808 ± 0.075 | 0.795 ± 0.039 |
| dup + z-score + IForest | 19.3 | 0.613 ± 0.098 | 0.967 ± 0.041 | 0.746 ± 0.074 |
| all four | 21.7 | 0.546 ± 0.089 | 0.967 ± 0.041 | 0.695 ± 0.077 |

### Recurring payments (9 fixed monthly payments injected per statement)

- seed 42: precision 1.0, recall 1.0 (false positives: none; missed: none)
- 10 other seeds: mean precision 0.980, mean recall 0.989

### How to read these numbers

- Ground truth is synthetic and has only two anomaly types (oversized spend x5-9, same-day duplicate). The detector is allowed to look for exactly those, so this is a **pipeline and tuning check, not a real-world accuracy claim**.
- Seed 42 is the seed the detector was debugged on, so its 1.0 / 1.0 is optimistic. **Quote the multi-seed table.**
- Isolation Forest is a real trade-off, not noise: across seeds it lifts recall (to ~0.97) but cuts precision (to ~0.61) because it fires on ordinary large-ish amounts too. The shipped default (dup + z-score) has the best F1; add the iforest signal to `ACTIVE_SIGNALS` in `ml/anomalies.py` if you would rather over-flag than miss one.
- The new-merchant rule has ~0 precision and recall here. The synthetic data has no novel-merchant anomalies, so this cannot show whether it helps on real statements. It stays OFF and unproven.
- A small injected anomaly can hide inside a category's normal range (e.g. a Rs.60 transport fare x5 = Rs.300), so recall below 1.0 on other seeds is expected and honest.
- For a resume-grade number: flag anomalies by hand on a real statement and score against that.