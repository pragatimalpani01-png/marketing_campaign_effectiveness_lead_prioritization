# Marketing Campaign Effectiveness and Lead Prioritization

This project asks two questions a marketing and sales team should be able to answer together: **which campaigns bring in leads that turn into customers, and who should sales contact next?** It goes beyond a basic cost-per-lead report by following leads through the funnel, testing a lead score on a later time period, and showing how attribution choices change the campaign story.

Everything in the repository is generated demo data. It is built to show the analysis and workflow clearly; it does not describe a real company's results.

## Start here

- **Dashboard:** open [`index.html`](index.html) in a browser, or publish the repository root with GitHub Pages. The dashboard has campaign and cohort filters, a searchable lead queue, an attribution comparison, and a budget-shift sandbox. Chart.js is loaded from a CDN, so charts need an internet connection.
- **Report:** [`reports/marketing_campaign_effectiveness_report.pdf`](reports/marketing_campaign_effectiveness_report.pdf)
- **Findings and recommendations:** [`outputs/analysis_summary.md`](outputs/analysis_summary.md) and [`OUTCOMES.md`](OUTCOMES.md)
- **How the score works:** [`MODEL_CARD.md`](MODEL_CARD.md)
- **Field definitions:** [`DATA_DICTIONARY.md`](DATA_DICTIONARY.md)

## What is included

| Area | Files |
|---|---|
| Raw data | `data/raw/leads.csv`, `touchpoints.csv`, `campaigns.csv`, `campaign_spend_monthly.csv` |
| Analysis code | `scripts/generate_demo_data.py`, `scripts/run_analysis.py` |
| Interactive story | `index.html`, `outputs/dashboard.html` |
| Report and charts | `reports/`, `visualizations/` |
| Analysis tables | `outputs/campaign_summary.csv`, `channel_summary.csv`, `monthly_performance.csv`, `campaign_monthly_performance.csv` |
| Lead score | `outputs/scored_leads.csv`, `outputs/model_holdout_metrics.csv`, `outputs/score_deciles_holdout.csv` |
| Attribution and planning | `outputs/attribution_summary.csv`, `outputs/attribution_by_cohort_and_first_campaign.csv`, `outputs/attribution_credit_shift.csv`, `outputs/illustrative_budget_shift.csv` |
| Queryable copy | `data/processed/marketing_analytics.sqlite` |
| SQL examples and tests | `sql/analysis_queries.sql`, `tests/` |

## What the demo shows

The fixed-seed sample contains 7,200 leads, 12 campaigns and seven channels. Recorded spend is about $760,000. The sample has 3,002 marketing-qualified leads, 1,602 sales-accepted leads and 553 wins, with roughly $8.77 million in booked deal value. That is 11.53 dollars of booked revenue for each recorded campaign dollar. It is **not** profit, margin or a fully loaded acquisition cost.

Partner webinars have the highest observed channel revenue-to-spend ratio in this generated sample, at about 21.8x. Paid Search brings the most booked revenue in total. The gap is the point: the channel with the best ratio is not always the one that contributes the most dollars, and a small number of deals can make a channel look unusually strong. The scorecard includes spend, lead volume, cost per win and revenue-to-spend together so no single number carries the decision. One extra check looks at disagreement between first-touch and last-touch reporting: about $1.86 million of booked-revenue credit, or 21.2% of the total, changes channel bucket when the method changes. This is a reporting difference, not revenue gained or lost.

The lead score is a logistic-regression baseline. It is trained on leads created from January through September 2025 and tested on leads created from October through December. On that held-out quarter, ROC AUC is about 0.717 and the top-scoring tenth of leads converts at about 2.39 times the overall holdout rate. Those figures describe a simulated dataset, not expected performance in a real sales team.

## Run it locally

Python 3.10 or newer is recommended.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate
pip install -r requirements.txt
python scripts/generate_demo_data.py
python scripts/run_analysis.py
python -m unittest discover -s tests -v
```

The generator uses a fixed random seed, so the same demo sample is produced each time unless you change the seed in `scripts/generate_demo_data.py`. The analysis script rebuilds the CSV rollups, scored lead file, SQLite database, charts, report and dashboard.

To create a larger sample, use `python scripts/generate_demo_data.py --leads 12000`. The standard analysis uses the dataset currently in `data/raw/`; rerun the analysis after regenerating it.

## How to read the metrics

- **Cost per lead:** recorded program spend divided by leads attributed to a campaign as the first touch.
- **Cost per MQL / SQL / win:** the same spend divided by each later funnel stage. These are simple allocated-cost views, not marginal acquisition costs.
- **Revenue-to-spend:** booked deal value divided by recorded program spend. It is not ROI after product delivery, sales payroll, discounts or gross margin.
- **Lead score:** predicted win probability from pre-sales signals. The score orders the queue; it is not a rule to reject leads.
- **Attribution:** first-touch, last-touch and linear approaches distribute recorded revenue differently. They do not establish incremental impact.
- **Budget sandbox:** a mechanical scenario using historical average rates. It assumes the rates stay fixed and does not model saturation or audience overlap.

## Important limitations

The dataset is synthetic and deliberately includes a plausible but simplified sales path. Marketing-qualified leads, sales acceptance and wins are generated as nested stages. The same person is represented by one synthetic lead ID; real CRM data would need account-level deduplication and rules for repeat inquiries. Paid impressions and clicks are included only for Paid Search and Paid Social because those exposure measures do not line up cleanly across webinars, email, organic and partner programs.

Use the results as a portfolio demonstration and a starting point for a live analysis. Before making real budget decisions, replace the generated records with consented first-party data, include margin and sales costs, define a consistent attribution window, and validate campaign changes with a control group or incrementality test where possible.

## Suggested GitHub Pages setup

In the repository, go to **Settings → Pages**, choose deployment from the `main` branch and the repository root. The dashboard is already copied to `index.html`. It uses Chart.js from a CDN and has its data embedded in the HTML file, so the page does not need to fetch the CSV files to render.

## License

The code is released under the MIT License. The demo data is synthetic and may be reused for portfolio and learning purposes.
