# Project notes

## Design choices

This project differs from a sales dashboard that only ranks campaigns by clicks or cost per lead. It keeps the acquisition view beside funnel progression, predicts a later outcome with a time-based test, compares three attribution rules, and includes a scenario tool that states its assumptions on screen.

## A few careful definitions

- Spend is summed from a monthly campaign cost file. It is not only media cost; for several non-paid channels it represents a generated program allocation.
- First-touch campaign is used to place each lead in one acquisition cohort. Touchpoints are used separately to compare attribution methods.
- Revenue-to-spend is booked deal value divided by recorded spend. It must not be called profit or ROI after all costs.
- The model score is a probability estimate from logistic regression, not a hard classification. `Now`, `Next` and `Nurture` are percentile-style ranking bands within the lead cohort month.
- The dashboard's active priority queue is restricted to open leads in the October to December validation cohort; the full scored file is available in `outputs/scored_leads.csv`.

## Rebuilding the work

The generator writes the raw inputs. The analysis script rebuilds the rollups, score file, SQLite database, charts, report, dashboard and root `index.html`. The data are deterministic under the default random seed, so output changes should normally follow a deliberate code or seed change.
