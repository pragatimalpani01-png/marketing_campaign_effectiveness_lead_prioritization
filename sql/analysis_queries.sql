-- Run these queries against data/processed/marketing_analytics.sqlite.
-- The database is rebuilt by scripts/run_analysis.py.

-- 1. Compare the campaigns on spend, lead volume and later-stage outcomes.
-- Spend and outcome counts are aggregated separately to avoid duplicating cost by lead row.
WITH spend_by_campaign AS (
    SELECT campaign_id, SUM(spend_usd) AS spend_usd
    FROM campaign_spend_monthly
    GROUP BY campaign_id
), outcomes_by_campaign AS (
    SELECT first_campaign_id AS campaign_id,
           COUNT(*) AS leads,
           SUM(marketing_qualified) AS mqls,
           SUM(sales_accepted) AS sqls,
           SUM(won) AS wins,
           SUM(booked_revenue_usd) AS booked_revenue_usd
    FROM raw_leads
    GROUP BY first_campaign_id
)
SELECT c.campaign_name,
       c.channel,
       ROUND(s.spend_usd, 2) AS spend_usd,
       o.leads,
       o.mqls,
       o.sqls,
       o.wins,
       ROUND(1.0 * s.spend_usd / NULLIF(o.leads, 0), 2) AS cost_per_lead_usd,
       ROUND(1.0 * s.spend_usd / NULLIF(o.wins, 0), 2) AS cost_per_win_usd,
       ROUND(1.0 * o.booked_revenue_usd / NULLIF(s.spend_usd, 0), 2) AS revenue_to_spend
FROM campaigns c
JOIN spend_by_campaign s USING (campaign_id)
JOIN outcomes_by_campaign o USING (campaign_id)
ORDER BY revenue_to_spend DESC;

-- 2. See the funnel by first-touch channel.
SELECT first_channel AS channel,
       COUNT(*) AS leads,
       SUM(marketing_qualified) AS mqls,
       SUM(sales_accepted) AS sqls,
       SUM(won) AS wins,
       ROUND(1.0 * SUM(marketing_qualified) / NULLIF(COUNT(*), 0), 3) AS mql_rate,
       ROUND(1.0 * SUM(sales_accepted) / NULLIF(SUM(marketing_qualified), 0), 3) AS sql_rate_from_mql,
       ROUND(1.0 * SUM(won) / NULLIF(SUM(sales_accepted), 0), 3) AS win_rate_from_sql
FROM raw_leads
GROUP BY first_channel
ORDER BY wins DESC;

-- 3. Check month-to-month lead cohorts and recorded revenue.
SELECT strftime('%Y-%m', created_at) AS cohort_month,
       COUNT(*) AS leads,
       SUM(marketing_qualified) AS mqls,
       SUM(sales_accepted) AS sqls,
       SUM(won) AS wins,
       SUM(booked_revenue_usd) AS booked_revenue_usd
FROM raw_leads
GROUP BY strftime('%Y-%m', created_at)
ORDER BY cohort_month;

-- 4. Review the highest-scoring open leads. This table is an analysis aid, not an automatic reject list.
SELECT lead_id, created_at, first_campaign_id, first_channel, priority_score,
       priority_tier, score_reasons, recommended_next_action
FROM scored_leads
WHERE lead_status LIKE 'Open%'
ORDER BY predicted_win_probability DESC
LIMIT 100;

-- 5. Compare the attribution views generated from the synthetic touchpoint paths.
SELECT channel,
       ROUND(first_touch_revenue_usd, 0) AS first_touch_usd,
       ROUND(last_touch_revenue_usd, 0) AS last_touch_usd,
       ROUND(linear_revenue_usd, 0) AS linear_usd
FROM attribution_summary
ORDER BY first_touch_revenue_usd DESC;

-- 6. See leads that received sales acceptance and how quickly the first response was recorded.
SELECT first_channel AS channel,
       COUNT(*) AS sales_accepted_leads,
       ROUND(AVG(days_to_first_response), 1) AS avg_days_to_first_response,
       SUM(won) AS wins
FROM raw_leads
WHERE sales_accepted = 1
GROUP BY first_channel
ORDER BY avg_days_to_first_response;
