# Data dictionary

The raw files contain generated demo records for 2025. The identifiers are synthetic and do not identify real people or companies.

## `data/raw/leads.csv`

One row per lead. Funnel outcomes are nested by design: every sales-accepted lead was marketing-qualified, and every won lead was sales-accepted.

| Field | Meaning |
|---|---|
| `lead_id` | Synthetic lead key, unique within this sample |
| `created_at` | Date the lead entered the system |
| `first_campaign_id` | Campaign credited with introducing the lead |
| `first_channel` | Channel for the first-touch campaign |
| `last_touch_channel` | Channel recorded for the final touch in the synthetic path |
| `customer_segment` | SMB, Mid-market or Enterprise, derived from company size band |
| `company_size_band` | Approximate employee range: 1-50, 51-200, 201-1000 or 1001+ |
| `region` | Broad market region |
| `job_seniority` | Individual Contributor, Manager, Director, VP or C-suite |
| `business_email` | 1 when the address is classified as a business email in the demo |
| `email_engagement_score` | Generated engagement score from 0 to 1 |
| `website_visits_30d` | Site visits in the 30-day lookback window |
| `pricing_page_visits_30d` | Visits to pricing pages in the same 30-day window |
| `content_downloads_90d` | Content downloads in the 90-day lookback window |
| `webinar_attended` | 1 if the lead attended a webinar |
| `demo_requested` | 1 if the lead requested a demo |
| `marketing_qualified` | 1 when the generated lead reaches the MQL stage |
| `sales_accepted` | 1 when sales accepts the lead; only possible for MQLs |
| `won` | 1 for a won deal; only possible for sales-accepted leads |
| `lead_status` | Won, Closed Lost, Open - Qualified, Open - Nurture or Closed - Unqualified |
| `days_to_first_response` | Generated number of days to first response |
| `estimated_deal_value_usd` | Generated potential deal value, present for all leads |
| `booked_revenue_usd` | Deal value recorded for won leads; zero otherwise |
| `days_to_win` | Generated days to win; blank for leads without a win |

## `data/raw/campaigns.csv`

One row per campaign. `lead_weight` controls the generated share of leads. `quality_effect` is a hidden generator parameter that influences outcomes; it is not a field used in scoring. `monthly_budget_usd` is the starting spend assumption. `campaign_budget_annual_usd` is simply 12 times that starting amount, not actual recorded spend.

## `data/raw/campaign_spend_monthly.csv`

One row per campaign and month. `spend_usd` is simulated monthly spend. `paid_impressions` and `paid_clicks` are populated only for Paid Search and Paid Social; they are blank for other channels because their exposure measures would not be directly comparable.

## `data/raw/touchpoints.csv`

One row per generated channel interaction. A lead can have several rows.

| Field | Meaning |
|---|---|
| `touchpoint_id` | Synthetic interaction key |
| `lead_id` | Links to `leads.csv` |
| `occurred_at` | Touch date |
| `channel`, `campaign_id` | Channel and campaign attached to that touch |
| `touch_type` | Type of interaction, such as ad click, webinar or email click |
| `engagement_points` | Small generated interaction weight, not a revenue credit |
| `is_first_touch`, `is_last_touch` | Flags for the first and final touches in the generated path |

## Processed and output files

- `campaign_monthly_performance.csv`: monthly spend joined to lead outcomes by first-touch campaign and cohort month.
- `campaign_summary.csv`, `channel_summary.csv`, `monthly_performance.csv`: rollups and derived efficiency measures.
- `scored_leads.csv`: all leads with predicted win probability, score band, reasons and suggested next action. Earlier historical rows are exploratory; the October to December cohort is the proper time-based test.
- `model_holdout_metrics.csv`, `score_deciles_holdout.csv`: evaluation measures from the chronological holdout.
- `attribution_summary.csv`: booked revenue credited by first-touch, last-touch and linear methods.
- `attribution_credit_shift.csv`: half the sum of absolute first-touch versus last-touch channel credit differences, plus the share of booked revenue represented. This measures disagreement between reporting rules, not causal impact.
- `attribution_by_cohort_and_first_campaign.csv`: attribution credit by cohort month and the lead's first campaign, allowing the dashboard filters to recalculate the comparison.
- `illustrative_budget_shift.csv`: one generated budget-shift example using historical average rates, with a warning attached.
- `data/processed/marketing_analytics.sqlite`: SQLite version of raw and processed tables for ad hoc querying.
