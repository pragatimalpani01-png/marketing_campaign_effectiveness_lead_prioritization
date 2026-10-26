# Analysis notes

## What the sample says

The sample contains 7,200 leads across 12 campaigns and seven channels. Recorded program spend is $760,209. The campaigns created 3,002 marketing-qualified leads, 1,602 sales-accepted leads and 553 wins. Booked revenue in the sample is $8,768,402, or 11.53 dollars of booked revenue for each recorded marketing dollar. This is a revenue-to-spend ratio, not profit or a fully loaded customer-acquisition-cost calculation.

- Overall cost per lead is $106. Cost per won deal is $1,375.
- Partner has the highest observed channel revenue-to-spend ratio at 21.80x. Paid Search brings in the most booked revenue in absolute dollars.
- Paid Social has the lowest observed revenue-to-spend ratio at 7.64x. That is a reason to inspect targeting and conversion quality, not enough on its own to shut the channel off.
- The campaign with the most booked revenue is Named Account Outreach; it accounts for 15.6% of recorded booked revenue.

## The lead score

The score is a logistic-regression baseline trained on leads created before October 1, 2025. Evaluation uses October through December as a chronological holdout. On that holdout, ROC AUC is 0.717, average precision is 0.176, and the Brier score is 0.0792. The top-scoring 10% have a 21.5% win rate, against 9.0% for the full holdout, a lift of 2.39x. These results describe ranking performance on this simulated sample; they are not a promise of performance in a live CRM.

The score uses information available before sales acceptance: channel and campaign, account size, region, seniority, business email, site visits, pricing visits, content activity, webinar attendance and demo request. It does not use the sales-accepted flag, win outcome, booked revenue or deal value as model inputs. Recommended next actions are rule-based suggestions layered on top of the score, so the reason for a recommendation is visible.

## Attribution is a view, not a verdict

First-touch, last-touch and linear models allocate the same booked deals in different ways. First touch gives credit to the campaign that introduced the lead; last touch gives credit to the last recorded channel; linear spreads credit across unique channels touched. None of these methods proves that a channel caused a sale. The multi-touch log is synthetic and the paths are illustrative. Use this comparison to find where the story changes, then validate it with experiments or a stronger incrementality design. Across this sample, about $1,855,552 of credit changes channel bucket between first-touch and last-touch reporting, equal to 21.2% of booked revenue. That amount measures attribution disagreement; it is not revenue gained or lost.

## A budget question worth testing

A mechanical scenario moves $21,244 from Paid Social to Partner. Based on historical average cost and revenue per lead, it estimates +20.0 net leads and +300,821 net booked revenue. This is not a forecast: no channel saturation, audience overlap, auction changes, sales capacity or uncertainty intervals are included. Treat it as a hypothesis for a capped test.

## Practical next steps

1. Put a short SLA around demo requests and repeat pricing visits, then measure response time and progression to sales acceptance.
2. Compare campaigns on cost per sales-accepted lead and cost per win alongside cost per lead. Keep lead volume in the view, but do not let volume settle the decision.
3. Test channel changes in small increments and preserve a control group where practical. Avoid reallocating the full budget based on one retrospective ratio.
4. Add CRM outcomes, account-level duplicates, sales touch timestamps, margins and consented attribution data before using this approach for real planning.

## Data and limitations

All rows are synthetic. Monthly spend is simulated; paid impressions and clicks are populated only for Paid Search and Paid Social because those figures do not have a comparable meaning for the other channels. Revenue is booked deal value, not margin. Leads are assigned one first-touch campaign for acquisition reporting, while touchpoints are used for attribution comparisons. The sample has no randomised control group, so channel results are descriptive rather than causal.
