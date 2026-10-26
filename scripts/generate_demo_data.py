"""Generate a realistic, fully synthetic B2B marketing and lead dataset."""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)
SEED = 41

CAMPAIGNS = [
    {"campaign_id":"C001","campaign_name":"Search - Brand","channel":"Paid Search","lead_weight":0.08,"monthly_budget_usd":7000,"quality_effect":0.70,"campaign_type":"High-intent search","notes":"Brand and product-name searches"},
    {"campaign_id":"C002","campaign_name":"Search - Generic","channel":"Paid Search","lead_weight":0.14,"monthly_budget_usd":12000,"quality_effect":0.20,"campaign_type":"Non-brand search","notes":"Category and problem searches"},
    {"campaign_id":"C003","campaign_name":"LinkedIn - Roles","channel":"Paid Social","lead_weight":0.10,"monthly_budget_usd":9000,"quality_effect":0.35,"campaign_type":"Role-targeted paid social","notes":"Job-function and seniority targeting"},
    {"campaign_id":"C004","campaign_name":"LinkedIn - Retargeting","channel":"Paid Social","lead_weight":0.06,"monthly_budget_usd":4000,"quality_effect":0.52,"campaign_type":"Retargeting","notes":"Visitors who returned after an earlier visit"},
    {"campaign_id":"C005","campaign_name":"Meta - Prospecting","channel":"Paid Social","lead_weight":0.12,"monthly_budget_usd":5000,"quality_effect":-0.35,"campaign_type":"Broad prospecting","notes":"Broad reach and discovery"},
    {"campaign_id":"C006","campaign_name":"Product Webinar","channel":"Webinar","lead_weight":0.09,"monthly_budget_usd":3500,"quality_effect":0.42,"campaign_type":"Owned event","notes":"Product use cases and live Q&A"},
    {"campaign_id":"C007","campaign_name":"Partner Webinar","channel":"Partner","lead_weight":0.06,"monthly_budget_usd":3500,"quality_effect":0.72,"campaign_type":"Partner event","notes":"Joint sessions with implementation partners"},
    {"campaign_id":"C008","campaign_name":"Lifecycle Email","channel":"Email","lead_weight":0.08,"monthly_budget_usd":1800,"quality_effect":0.22,"campaign_type":"Lifecycle nurture","notes":"Email to opted-in prospects"},
    {"campaign_id":"C009","campaign_name":"Newsletter Sponsorship","channel":"Email","lead_weight":0.06,"monthly_budget_usd":2500,"quality_effect":-0.12,"campaign_type":"Paid newsletter","notes":"Sponsored placements in trade newsletters"},
    {"campaign_id":"C010","campaign_name":"SEO - Product Pages","channel":"Organic Search","lead_weight":0.08,"monthly_budget_usd":4500,"quality_effect":0.45,"campaign_type":"Product-led organic search","notes":"Comparison and solution pages"},
    {"campaign_id":"C011","campaign_name":"SEO - Industry Guides","channel":"Organic Search","lead_weight":0.08,"monthly_budget_usd":3500,"quality_effect":0.08,"campaign_type":"Educational content","notes":"Research and practical guides"},
    {"campaign_id":"C012","campaign_name":"Named Account Outreach","channel":"ABM","lead_weight":0.05,"monthly_budget_usd":8000,"quality_effect":0.63,"campaign_type":"Account-based marketing","notes":"Named-account programs and tailored outreach"},
]
CHANNELS = ["Paid Search", "Paid Social", "Webinar", "Partner", "Email", "Organic Search", "ABM"]


def sigmoid(x):
    return 1 / (1 + np.exp(-np.clip(x, -25, 25)))


def main(n_leads=7200):
    rng = np.random.default_rng(SEED)
    campaigns = pd.DataFrame(CAMPAIGNS)
    campaigns["campaign_budget_annual_usd"] = campaigns["monthly_budget_usd"] * 12
    campaigns.to_csv(RAW / "campaigns.csv", index=False)

    # Lead dates are slightly lighter in midsummer and late December.
    month_weights = np.array([1.00, 0.96, 1.04, 1.03, 1.02, 0.98, 0.88, 0.91, 1.05, 1.07, 1.02, 0.82])
    month_weights = month_weights / month_weights.sum()
    months = rng.choice(np.arange(1, 13), size=n_leads, p=month_weights)
    days = np.array([rng.integers(1, pd.Period(f"2025-{m:02d}").days_in_month + 1) for m in months])
    created = pd.to_datetime([f"2025-{m:02d}-{d:02d}" for m, d in zip(months, days)])

    cidx = rng.choice(len(campaigns), size=n_leads, p=campaigns["lead_weight"].to_numpy())
    camp = campaigns.iloc[cidx].reset_index(drop=True)
    channel = camp["channel"].to_numpy()
    quality = camp["quality_effect"].to_numpy()
    campaign_ids = camp["campaign_id"].to_numpy()

    size_bands = np.array(["1-50", "51-200", "201-1000", "1001+"])
    size_probs = np.zeros((n_leads, 4))
    for i, ch in enumerate(channel):
        if ch == "ABM": p = [0.03, 0.12, 0.40, 0.45]
        elif ch == "Partner": p = [0.12, 0.28, 0.38, 0.22]
        elif ch == "Paid Search" and campaign_ids[i] == "C001": p = [0.16, 0.34, 0.34, 0.16]
        else: p = [0.37, 0.34, 0.21, 0.08]
        size_probs[i] = p
    size_band = np.array([rng.choice(size_bands, p=p) for p in size_probs])
    segment = np.where(size_band == "1-50", "SMB", np.where(size_band == "51-200", "Mid-market", np.where(size_band == "201-1000", "Mid-market", "Enterprise")))
    seniorities = np.array(["Individual Contributor", "Manager", "Director", "VP", "C-suite"])
    seniority_probs = {"ABM":[0.05,0.15,0.30,0.32,0.18], "Partner":[0.12,0.22,0.30,0.24,0.12], "Paid Search":[0.28,0.28,0.23,0.14,0.07], "Paid Social":[0.32,0.28,0.22,0.12,0.06], "Webinar":[0.20,0.25,0.27,0.18,0.10], "Email":[0.30,0.28,0.22,0.13,0.07], "Organic Search":[0.26,0.28,0.24,0.15,0.07]}
    seniority = np.array([rng.choice(seniorities, p=seniority_probs[ch]) for ch in channel])
    region = rng.choice(["North America", "Europe", "Asia Pacific", "Latin America"], size=n_leads, p=[0.52,0.25,0.17,0.06])
    business_email = rng.binomial(1, np.where(segment == "Enterprise", 0.97, np.where(segment == "Mid-market", 0.92, 0.80)))

    # Engagement signals are measured before the lead is handed to sales.
    engagement_shift = np.where(np.isin(channel, ["Email", "Webinar", "Partner", "Organic Search"]), 0.10, 0.0)
    email_engagement = np.clip(rng.beta(2.0 + engagement_shift * 4, 4.2, n_leads), 0, 1)
    web_rate = np.where(np.isin(channel, ["Paid Search", "Organic Search", "ABM"]), 4.2, 2.6)
    website_visits = rng.poisson(web_rate + email_engagement * 2.0, size=n_leads)
    pricing_visits = rng.poisson(0.25 + website_visits * 0.10 + np.where(np.isin(channel, ["Paid Search", "ABM"]), 0.22, 0), size=n_leads)
    content_downloads = rng.poisson(0.45 + np.where(np.isin(channel, ["Webinar", "Email", "Organic Search", "Partner"]), 0.45, 0), size=n_leads)
    webinar_attended = rng.binomial(1, np.where(np.isin(channel, ["Webinar", "Partner"]), 0.52, 0.08))
    demo_probability = sigmoid(-2.55 + 0.17 * pricing_visits + 0.10 * website_visits + 0.50 * (seniority == "Director") + 0.74 * np.isin(seniority, ["VP", "C-suite"]) + 0.20 * (size_band == "1001+") + quality * 0.30)
    demo_requested = rng.binomial(1, demo_probability)

    seniority_fit = np.select([seniority == "Manager", seniority == "Director", seniority == "VP", seniority == "C-suite"], [0.12, 0.24, 0.36, 0.40], default=-0.12)
    company_fit = np.select([size_band == "51-200", size_band == "201-1000", size_band == "1001+"], [0.08, 0.20, 0.24], default=-0.08)
    mql_p = sigmoid(-1.85 + 1.20 * demo_requested + 0.40 * pricing_visits + 0.09 * website_visits + 0.65 * email_engagement + 0.48 * webinar_attended + 0.20 * content_downloads + seniority_fit + company_fit)
    mql = rng.binomial(1, mql_p)
    sql_p = sigmoid(-0.55 + 0.52 * quality + 0.40 * demo_requested + 0.10 * pricing_visits + 0.35 * email_engagement + 0.18 * webinar_attended + seniority_fit * 0.65 + company_fit * 0.55)
    sql = mql * rng.binomial(1, sql_p)
    win_p = sigmoid(-1.50 + 0.65 * quality + 0.44 * demo_requested + 0.08 * pricing_visits + 0.22 * email_engagement + 0.16 * webinar_attended + seniority_fit * 0.70 + company_fit * 0.75 + 0.12 * business_email)
    won = sql * rng.binomial(1, win_p)

    base_value = np.select([size_band == "1-50", size_band == "51-200", size_band == "201-1000", size_band == "1001+"], [6500, 11000, 18500, 31000])
    deal_value = np.maximum(2500, rng.lognormal(np.log(base_value) - 0.10, 0.42, size=n_leads)).round(0).astype(int)
    booked_revenue = np.where(won == 1, deal_value, 0).astype(int)
    days_to_win = np.where(won == 1, rng.integers(12, 91, size=n_leads), np.nan)
    days_to_response = np.where(sql == 1, rng.integers(0, 6, size=n_leads), rng.integers(1, 15, size=n_leads))
    # Keep a modest open/closed distinction for the example priority queue.
    status = []
    for i in range(n_leads):
        if won[i]: status.append("Won")
        elif sql[i] and rng.random() < 0.24: status.append("Closed Lost")
        elif mql[i] and rng.random() < 0.12: status.append("Closed Lost")
        elif mql[i]: status.append("Open - Qualified")
        elif rng.random() < 0.30: status.append("Open - Nurture")
        else: status.append("Closed - Unqualified")

    leads = pd.DataFrame({
        "lead_id":[f"L{i:05d}" for i in range(1, n_leads + 1)],
        "created_at":created,
        "first_campaign_id":campaign_ids,
        "first_channel":channel,
        "customer_segment":segment,
        "company_size_band":size_band,
        "region":region,
        "job_seniority":seniority,
        "business_email":business_email,
        "email_engagement_score":np.round(email_engagement, 3),
        "website_visits_30d":website_visits,
        "pricing_page_visits_30d":pricing_visits,
        "content_downloads_90d":content_downloads,
        "webinar_attended":webinar_attended,
        "demo_requested":demo_requested,
        "marketing_qualified":mql,
        "sales_accepted":sql,
        "won":won,
        "lead_status":status,
        "days_to_first_response":days_to_response,
        "estimated_deal_value_usd":deal_value,
        "booked_revenue_usd":booked_revenue,
        "days_to_win":days_to_win,
    })
    leads.to_csv(RAW / "leads.csv", index=False, date_format="%Y-%m-%d")

    # Build a multi-touch path for each lead. First touch is the acquisition campaign;
    # later touches are chosen from plausible channels and are deliberately not a claim
    # that any one attribution model reveals causal impact.
    channel_campaigns = {ch: campaigns[campaigns.channel == ch].campaign_id.to_list() for ch in campaigns.channel.unique()}
    channel_weights = np.array([0.17, 0.16, 0.12, 0.08, 0.20, 0.18, 0.09])
    channel_weights /= channel_weights.sum()
    touch_rows = []
    touch_idx = 1
    touch_type_map = {
        "Paid Search":["Ad click", "Search visit"], "Paid Social":["Social ad click", "Retargeting click"],
        "Webinar":["Webinar registration", "Webinar attendance"], "Partner":["Partner referral", "Partner webinar"],
        "Email":["Email open", "Email click"], "Organic Search":["Organic search visit", "Content read"],
        "ABM":["Sales outreach", "Account engagement"]
    }
    last_channels = []
    for i, row in leads.iterrows():
        first_ch = row.first_channel
        first_camp = row.first_campaign_id
        # More touches for high-intent leads; this is observational, not causal.
        touch_count = int(np.clip(1 + rng.poisson(1.5 + 0.8 * row.demo_requested + 0.35 * row.webinar_attended), 1, 6))
        max_day = int(min(30, max(1, row.days_to_win - 1 if pd.notna(row.days_to_win) else 30)))
        touch_dates = [pd.Timestamp(row.created_at)]
        if touch_count > 1:
            add_days = sorted(rng.integers(1, max_day + 1, size=touch_count - 1).tolist())
            touch_dates += [pd.Timestamp(row.created_at) + pd.Timedelta(days=int(d)) for d in add_days]
        chosen = [first_ch]
        for j in range(touch_count - 1):
            if row.demo_requested and rng.random() < 0.30:
                ch = "ABM" if row.company_size_band in ["201-1000", "1001+"] else "Email"
            elif row.webinar_attended and rng.random() < 0.40:
                ch = "Webinar"
            else:
                ch = rng.choice(CHANNELS, p=channel_weights)
            chosen.append(str(ch))
        last_ch = chosen[-1]
        last_channels.append(last_ch)
        for j, (ch, ts) in enumerate(zip(chosen, touch_dates)):
            if j == 0:
                cid = first_camp
            else:
                cid = str(rng.choice(channel_campaigns[ch]))
            ttype = str(rng.choice(touch_type_map[ch]))
            engagement_points = int(rng.choice([1,2,3,4], p=[0.30,0.36,0.24,0.10]))
            touch_rows.append({
                "touchpoint_id":f"T{touch_idx:06d}", "lead_id":row.lead_id,
                "occurred_at":ts.strftime("%Y-%m-%d"), "channel":ch, "campaign_id":cid,
                "touch_type":ttype, "engagement_points":engagement_points,
                "is_first_touch":int(j == 0), "is_last_touch":int(j == len(chosen) - 1)
            })
            touch_idx += 1
    touches = pd.DataFrame(touch_rows)
    # Store the last touch channel on the lead record for convenient cohort summaries.
    leads["last_touch_channel"] = last_channels
    leads.to_csv(RAW / "leads.csv", index=False, date_format="%Y-%m-%d")
    touches.to_csv(RAW / "touchpoints.csv", index=False)

    # Monthly program cost and paid-media delivery. Only paid channels have impressions/clicks;
    # organic, event and partner metrics should not be compared as if they were ad clicks.
    months_index = pd.period_range("2025-01", "2025-12", freq="M")
    spend_rows = []
    seasonality = np.array([0.99,0.97,1.03,1.04,1.03,0.99,0.85,0.90,1.04,1.08,1.04,0.88])
    for _, c in campaigns.iterrows():
        for mi, period in enumerate(months_index):
            spend = c.monthly_budget_usd * seasonality[mi] * rng.normal(1, 0.035)
            if c.channel == "Paid Search":
                cpm = rng.uniform(28, 47); ctr = rng.uniform(0.028, 0.052)
                impressions = int(max(1000, spend / cpm * 1000))
                clicks = int(impressions * ctr)
            elif c.channel == "Paid Social":
                cpm = rng.uniform(17, 31); ctr = rng.uniform(0.006, 0.017)
                impressions = int(max(1000, spend / cpm * 1000))
                clicks = int(impressions * ctr)
            else:
                impressions = np.nan; clicks = np.nan
            spend_rows.append({"month":str(period),"campaign_id":c.campaign_id,"spend_usd":round(float(spend),2),"paid_impressions":impressions,"paid_clicks":clicks})
    spend_monthly = pd.DataFrame(spend_rows)
    spend_monthly.to_csv(RAW / "campaign_spend_monthly.csv", index=False)

    # A one-row-per-campaign lookup is also placed in the raw folder, so data can be explored
    # without having to open the generation script.
    print(f"Wrote {len(leads):,} leads, {len(touches):,} touchpoints, {len(campaigns)} campaigns, {len(spend_monthly)} monthly spend rows.")
    print(f"Won deals: {int(leads.won.sum()):,} | MQLs: {int(leads.marketing_qualified.sum()):,} | Sales accepted: {int(leads.sales_accepted.sum()):,}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Create demo campaign and lead data.")
    parser.add_argument("--leads", type=int, default=7200, help="Number of synthetic leads to create")
    args = parser.parse_args()
    main(args.leads)
