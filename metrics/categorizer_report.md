### Held-out eval set (n=301)

| Method | Accuracy | Macro-F1 | Weighted-F1 |
|---|---|---|---|
| rules | 1.0 | 1.0 | 1.0 |
| ml | 1.0 | 1.0 | 1.0 |
| hybrid | 1.0 | 1.0 | 1.0 |

### Unseen-merchant cross-validation (5-fold GroupKFold)

| Method | Accuracy | Macro-F1 | Weighted-F1 |
|---|---|---|---|
| rules | 1.0 | 1.0 | 1.0 |
| ml | 0.0654 | 0.0822 | 0.0647 |
| hybrid | 1.0 | 1.0 | 1.0 |

### How to read these numbers

- The eval set is synthetic and built from the same merchant templates the rules were written against, so ~1.0 only proves the pipeline works end to end. **It is not a real-world accuracy claim.**
- Unseen-merchant ML-only accuracy is near chance because synthetic merchant names carry no shared meaning. Real data and the user-correction loop (Day 4) are what improve this.
- ML confidence is informative: below 0.5 it is almost always wrong, so low-confidence rows are flagged for review.
- For a resume-grade number, hand-label real transactions and run `python -m ml.real_eval score <file>`.