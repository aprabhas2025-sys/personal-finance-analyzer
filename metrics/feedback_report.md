### Feedback loop simulation (10 random merchant splits, ML-only accuracy on remaining rows of held-out merchants)

| Corrections per merchant | Held-out merchants | Total corrections | Accuracy before | Accuracy after |
|---|---|---|---|---|
| 1 | 16 | ~16 | 15.5% ± 8.5% | 99.7% ± 1.0% |
| 3 | 16 | ~46 | 15.4% ± 8.9% | 100.0% ± 0.0% |

### How to read these numbers

- 'Before' is the ML model on merchants it has never seen (near chance is expected: synthetic merchant names carry no shared meaning).
- 'After' is on OTHER transactions from the merchants the simulated user corrected. A jump here shows corrections do reach the model; it is not evidence the model generalizes to merchants nobody has corrected.
- The user is simulated with ground-truth labels, so real users' mistakes or inconsistent corrections are not modelled.
- Rules run before ML in the shipped hybrid, so a correction to a rule-matched merchant is applied to the current statement by merchant propagation, not by retraining.