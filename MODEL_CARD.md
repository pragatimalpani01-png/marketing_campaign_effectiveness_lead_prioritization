# Lead score: model card

## Purpose

Give a sales team a ranked list for follow-up, with a visible explanation of why a lead is near the top. This is a portfolio model, not a production sales decision system.

## Model

A logistic-regression classifier is trained on leads created before October 1, 2025. The model is checked on leads created from October 1 through December 31, 2025. This chronological split keeps the holdout later in time than the training data.

### Inputs

- First-touch channel and campaign
- Customer segment and company-size band
- Region and job seniority
- Business email flag
- Email engagement score
- Website visits and pricing-page visits
- Content downloads
- Webinar attendance
- Demo request

The pipeline imputes missing numeric and categorical values, scales numeric inputs, and one-hot encodes categorical inputs. Unknown categories are tolerated at scoring time.

### Excluded from model inputs

Sales acceptance, lead status, won outcome, booked revenue, estimated deal value and days to win are not used as features. Those fields describe later outcomes and would leak information into the score.

## Evaluation on the held-out quarter

| Metric | Result |
|---|---:|
| Training leads | 5,433 |
| Holdout leads | 1,767 |
| Holdout wins | 159 |
| ROC AUC | 0.717 |
| Average precision | 0.176 |
| Brier score | 0.0792 |
| Win rate across holdout | about 9.0% |
| Win rate in top-scoring 10% | 21.5% |
| Lift in top-scoring 10% | 2.39x |

The model is better at ranking the higher-intent records than treating every lead equally in this synthetic sample. The metrics are generated from one held-out quarter and should not be compared with a real team's benchmark without matching the target, time window and base rate.

## Use of the score

The score is a ranking aid. The exported file includes a `priority_tier`, `score_reasons` and `recommended_next_action`. The next action is rule-based so a rep can see the signal behind it. A demo request or repeated pricing activity can justify quick follow-up; low-score leads should not be automatically rejected.

## Known limitations

- All records and labels are generated, not collected from an actual CRM.
- The target is a won deal, which depends on sales execution and account conditions as well as marketing.
- The validation window is one quarter.
- Historical scores for January through September are included for exploration, but those rows overlap with the training period. Treat the October to December cohort as the out-of-time model test.
- No fairness, calibration-by-segment, drift or production monitoring assessment has been performed.
- The recommendation rules are simple and should be reviewed by sales before use.

## Before production use

Train on consented CRM data, deduplicate at account and person level, agree on the outcome and prediction horizon, validate on later cohorts, check calibration by useful business segments, review excluded or disadvantaged groups, measure sales capacity and monitor drift. Keep a human decision-maker in the loop.
