# Data files

The `raw` folder holds four synthetic input files:

- `leads.csv`: one row per lead with pre-sales signals and generated funnel outcomes.
- `touchpoints.csv`: interaction paths for first-touch, last-touch and linear attribution comparisons.
- `campaigns.csv`: campaign lookup and generator settings.
- `campaign_spend_monthly.csv`: spend by campaign and month, with paid-media delivery only where it is comparable.

All demo data is created by `scripts/generate_demo_data.py` with a fixed random seed. No real customer or business data is used. See the root `DATA_DICTIONARY.md` for field meanings and known limitations.
