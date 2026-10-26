"""Run the campaign analysis, train a transparent baseline scorer, and build outputs."""
from pathlib import Path
import json
import sqlite3
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss, precision_score, recall_score
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak, KeepTogether

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
OUT = ROOT / "outputs"
VIZ = ROOT / "visualizations"
REPORTS = ROOT / "reports"
for p in (PROCESSED, OUT, VIZ, REPORTS): p.mkdir(parents=True, exist_ok=True)
CUTOFF = pd.Timestamp("2025-10-01")
CATEGORICAL = ["first_channel", "first_campaign_id", "customer_segment", "company_size_band", "region", "job_seniority"]
NUMERIC = ["business_email", "email_engagement_score", "website_visits_30d", "pricing_page_visits_30d", "content_downloads_90d", "webinar_attended", "demo_requested"]
FEATURES = CATEGORICAL + NUMERIC
CHANNEL_ORDER = ["Paid Search", "Paid Social", "Webinar", "Partner", "Email", "Organic Search", "ABM"]


def ratio(a, b):
    return float(a / b) if b is not None and b != 0 and pd.notna(b) else np.nan


def add_efficiency(frame):
    d = frame.copy()
    for name, numerator, denominator in [
        ("cost_per_lead_usd", "spend_usd", "leads"), ("cost_per_mql_usd", "spend_usd", "mqls"),
        ("cost_per_sql_usd", "spend_usd", "sqls"), ("cost_per_win_usd", "spend_usd", "wins"),
        ("mql_rate", "mqls", "leads"), ("sql_rate_from_mql", "sqls", "mqls"),
        ("win_rate_from_sql", "wins", "sqls"), ("win_rate_from_lead", "wins", "leads"),
        ("revenue_to_spend", "booked_revenue_usd", "spend_usd"), ("revenue_per_lead_usd", "booked_revenue_usd", "leads")]:
        d[name] = [ratio(a, b) for a, b in zip(d[numerator], d[denominator])]
    return d


def action_for(r):
    if int(r.get("demo_requested", 0)) == 1: return "Route to sales within one business hour"
    if int(r.get("pricing_page_visits_30d", 0)) >= 2: return "Send a tailored follow-up on pricing and fit"
    if int(r.get("webinar_attended", 0)) == 1: return "Follow up with a use case from the session"
    if float(r.get("email_engagement_score", 0)) >= .62 and int(r.get("website_visits_30d", 0)) >= 4: return "Send one relevant proof point, then check intent"
    if int(r.get("content_downloads_90d", 0)) >= 2: return "Offer a short guide matched to the topic viewed"
    return "Keep in nurture and watch for a stronger signal"


def reason_for(r):
    bits = []
    if int(r.get("demo_requested", 0)) == 1: bits.append("demo request")
    if int(r.get("pricing_page_visits_30d", 0)) >= 2: bits.append("repeat pricing visits")
    if int(r.get("webinar_attended", 0)) == 1: bits.append("webinar attendance")
    if float(r.get("email_engagement_score", 0)) >= .62: bits.append("strong email engagement")
    if int(r.get("website_visits_30d", 0)) >= 6: bits.append("repeat site visits")
    if r.get("job_seniority") in ["Director", "VP", "C-suite"]: bits.append("senior role")
    if r.get("company_size_band") in ["201-1000", "1001+"]: bits.append("larger account")
    return ", ".join(bits[:3]) if bits else "few clear buying signals so far"


def format_money(v, digits=0):
    return "n/a" if pd.isna(v) else f"${v:,.{digits}f}"


def format_pct(v, digits=1):
    return "n/a" if pd.isna(v) else f"{100*v:.{digits}f}%"


def create_charts(monthly, channels, deciles, attribution, heatmap):
    plt.rcParams.update({"font.size": 9, "axes.titlesize": 12, "axes.labelsize": 9, "figure.facecolor": "white", "axes.facecolor": "white"})
    # Monthly funnel cohorts.
    fig, ax = plt.subplots(figsize=(9.5, 4.1)); m = monthly.sort_values("month")
    for col, label in [("leads", "Leads"), ("mqls", "Marketing-qualified"), ("sqls", "Sales-accepted")]:
        ax.plot(m.month, m[col], marker="o", linewidth=1.8, label=label)
    ax.plot(m.month, m.wins, marker="s", linestyle="--", linewidth=1.8, label="Won deals")
    ax.set_ylabel("Count"); ax.set_xlabel("Lead cohort month"); ax.tick_params(axis="x", rotation=40); ax.grid(axis="y", alpha=.22); ax.legend(frameon=False, ncol=2)
    ax.set_title("Lead volume and progression through the funnel")
    fig.tight_layout(); fig.savefig(VIZ/"monthly_funnel.png", dpi=180, bbox_inches="tight"); plt.close(fig)

    # Channel efficiency: lead cost on x, lead-to-win rate on y, volume shown by bubble size.
    fig, ax = plt.subplots(figsize=(9.2, 5.0)); d = channels.dropna(subset=["cost_per_lead_usd", "win_rate_from_lead"])
    ax.scatter(d.cost_per_lead_usd, d.win_rate_from_lead*100, s=80+np.sqrt(d.leads.clip(lower=1))*10, alpha=.78, edgecolors="white", linewidths=1)
    for _, r in d.iterrows(): ax.annotate(r.channel, (r.cost_per_lead_usd, r.win_rate_from_lead*100), xytext=(4, 4), textcoords="offset points", fontsize=8)
    ax.set_xlabel("Cost per lead (USD)"); ax.set_ylabel("Lead-to-win rate (%)"); ax.set_title("Cheap leads are not always the best leads"); ax.grid(alpha=.22)
    fig.tight_layout(); fig.savefig(VIZ/"channel_economics.png", dpi=180, bbox_inches="tight"); plt.close(fig)

    # Funnel drop-off.
    funnel_names = ["Leads", "Marketing-qualified", "Sales-accepted", "Won"]
    values = [int(monthly.leads.sum()), int(monthly.mqls.sum()), int(monthly.sqls.sum()), int(monthly.wins.sum())]
    fig, ax = plt.subplots(figsize=(8.5, 4.0)); bars = ax.barh(funnel_names[::-1], values[::-1])
    ax.set_xlabel("Count"); ax.set_title("Where prospects leave the journey"); ax.grid(axis="x", alpha=.2)
    for b, v in zip(bars, values[::-1]): ax.text(v+max(values)*.012, b.get_y()+b.get_height()/2, f"{v:,}", va="center")
    ax.set_xlim(0, max(values)*1.16); fig.tight_layout(); fig.savefig(VIZ/"funnel_dropoff.png", dpi=180, bbox_inches="tight"); plt.close(fig)

    # Holdout score deciles.
    fig, ax1 = plt.subplots(figsize=(9.0, 4.5)); d = deciles.sort_values("decile")
    ax1.bar(d.decile_label, d.win_rate*100, alpha=.86, label="Observed win rate")
    ax1.set_ylabel("Observed win rate (%)"); ax1.set_xlabel("Score band, highest to lowest"); ax1.tick_params(axis="x", rotation=30); ax1.grid(axis="y", alpha=.2)
    ax2 = ax1.twinx(); ax2.plot(d.decile_label, d.lift, color="black", marker="o", linestyle="--", label="Lift vs holdout average"); ax2.set_ylabel("Lift vs holdout average")
    h1,l1=ax1.get_legend_handles_labels(); h2,l2=ax2.get_legend_handles_labels(); ax1.legend(h1+h2,l1+l2,frameon=False,loc="upper right")
    ax1.set_title("A useful score should rank leads, not just describe them")
    fig.tight_layout(); fig.savefig(VIZ/"lead_score_lift.png", dpi=180, bbox_inches="tight"); plt.close(fig)

    # Attribution comparison.
    d = attribution.sort_values("first_touch_revenue_usd", ascending=False); fig, ax = plt.subplots(figsize=(9.5, 4.5)); x=np.arange(len(d)); w=.25
    ax.bar(x-w, d.first_touch_revenue_usd, w, label="First touch"); ax.bar(x, d.last_touch_revenue_usd, w, label="Last touch"); ax.bar(x+w, d.linear_revenue_usd, w, label="Linear")
    ax.set_xticks(x); ax.set_xticklabels(d.channel, rotation=32, ha="right"); ax.set_ylabel("Attributed booked revenue (USD)"); ax.set_title("One sale can tell three attribution stories"); ax.grid(axis="y", alpha=.2); ax.legend(frameon=False, ncol=3)
    fig.tight_layout(); fig.savefig(VIZ/"attribution_comparison.png", dpi=180, bbox_inches="tight"); plt.close(fig)

    # Spend and first-touch revenue.
    d=channels.sort_values("spend_usd",ascending=False); fig,ax=plt.subplots(figsize=(9.5,4.5)); x=np.arange(len(d)); w=.38
    ax.bar(x-w/2,d.spend_usd,w,label="Spend"); ax.bar(x+w/2,d.booked_revenue_usd,w,label="Booked revenue credited to first touch")
    ax.set_xticks(x); ax.set_xticklabels(d.channel,rotation=32,ha="right"); ax.set_ylabel("USD"); ax.set_title("Budget and booked revenue by first-touch channel"); ax.grid(axis="y",alpha=.2); ax.legend(frameon=False)
    fig.tight_layout(); fig.savefig(VIZ/"spend_vs_revenue.png",dpi=180,bbox_inches="tight"); plt.close(fig)

    # Quarterly efficiency heatmap.
    h=heatmap.pivot(index="channel",columns="quarter",values="revenue_to_spend").reindex(CHANNEL_ORDER); arr=h.to_numpy(dtype=float)
    fig,ax=plt.subplots(figsize=(8,4.7)); im=ax.imshow(np.ma.masked_invalid(arr),aspect="auto",interpolation="nearest")
    ax.set_xticks(np.arange(len(h.columns))); ax.set_xticklabels(h.columns); ax.set_yticks(np.arange(len(h.index))); ax.set_yticklabels(h.index)
    for i in range(arr.shape[0]):
        for j in range(arr.shape[1]): ax.text(j,i,f"{arr[i,j]:.1f}x" if np.isfinite(arr[i,j]) else "-",ha="center",va="center",fontsize=8)
    ax.set_title("Revenue-to-spend ratio moves around by quarter"); fig.colorbar(im,ax=ax,label="Booked revenue / spend")
    fig.tight_layout(); fig.savefig(VIZ/"channel_quarter_heatmap.png",dpi=180,bbox_inches="tight"); plt.close(fig)


def main():
    leads = pd.read_csv(RAW/"leads.csv", parse_dates=["created_at"])
    touches = pd.read_csv(RAW/"touchpoints.csv", parse_dates=["occurred_at"])
    campaigns = pd.read_csv(RAW/"campaigns.csv")
    spend = pd.read_csv(RAW/"campaign_spend_monthly.csv")
    leads["cohort_month"] = leads.created_at.dt.to_period("M").astype(str)
    leads["pipeline_value_usd"] = np.where(leads.sales_accepted.eq(1), leads.estimated_deal_value_usd, 0)
    leads["created_quarter"] = leads.created_at.dt.to_period("Q").astype(str)

    # Chronological holdout: the model sees January-September and is checked on October-December.
    train_mask = leads.created_at < CUTOFF
    test_mask = ~train_mask
    preprocessor = ColumnTransformer([
        ("numeric", Pipeline([("imputer", SimpleImputer(strategy="median")), ("scale", StandardScaler())]), NUMERIC),
        ("categorical", Pipeline([("imputer", SimpleImputer(strategy="most_frequent")), ("onehot", OneHotEncoder(handle_unknown="ignore"))]), CATEGORICAL),
    ])
    model = Pipeline([("features", preprocessor), ("logistic", LogisticRegression(max_iter=1200, C=0.75, random_state=41))])
    model.fit(leads.loc[train_mask, FEATURES], leads.loc[train_mask, "won"].astype(int))
    p_test = model.predict_proba(leads.loc[test_mask, FEATURES])[:, 1]
    y_test = leads.loc[test_mask, "won"].astype(int).to_numpy()
    test_rank = np.argsort(-p_test)
    top_n = max(1, int(np.ceil(len(y_test)*.10)))
    top_idx = test_rank[:top_n]
    holdout_rate = float(y_test.mean())
    top_rate = float(y_test[top_idx].mean())
    model_metrics = {
        "train_start": str(leads.loc[train_mask, "created_at"].min().date()),
        "train_end": str(leads.loc[train_mask, "created_at"].max().date()),
        "test_start": str(leads.loc[test_mask, "created_at"].min().date()),
        "test_end": str(leads.loc[test_mask, "created_at"].max().date()),
        "train_leads": int(train_mask.sum()), "test_leads": int(test_mask.sum()),
        "train_wins": int(leads.loc[train_mask, "won"].sum()), "test_wins": int(y_test.sum()),
        "holdout_win_rate": holdout_rate,
        "roc_auc": float(roc_auc_score(y_test, p_test)) if len(np.unique(y_test)) > 1 else np.nan,
        "average_precision": float(average_precision_score(y_test, p_test)),
        "brier_score": float(brier_score_loss(y_test, p_test)),
        "precision_top_10pct": top_rate,
        "recall_top_10pct": float(y_test[top_idx].sum()/max(1,y_test.sum())),
        "lift_top_10pct": float(top_rate/holdout_rate) if holdout_rate else np.nan,
    }
    pd.DataFrame([model_metrics]).to_csv(OUT/"model_holdout_metrics.csv", index=False)

    # Score every row for an analysis output. The out-of-time evaluation above is the
    # defensible test; older rows are shown for exploration, not presented as a live test.
    leads["predicted_win_probability"] = model.predict_proba(leads[FEATURES])[:, 1]
    leads["priority_score"] = (leads.predicted_win_probability*100).round(1)
    leads["score_status"] = np.where(leads.created_at >= CUTOFF, "Out-of-time holdout cohort", "Historical cohort; model trained on overlapping dates")
    leads["cohort_month"] = leads.created_at.dt.to_period("M").astype(str)
    # Tier leads against peers entering in the same month, so older training rows do not set
    # the priority thresholds for the later, held-out queue.
    leads["priority_tier"] = "Nurture"
    for _, idx in leads.groupby("cohort_month").groups.items():
        month_rank = leads.loc[idx, "predicted_win_probability"].rank(method="first", ascending=False)
        n_month = len(idx)
        leads.loc[idx, "priority_tier"] = np.where(month_rank <= n_month*.10, "Now", np.where(month_rank <= n_month*.35, "Next", "Nurture"))
    leads["score_reasons"] = leads.apply(reason_for, axis=1)
    leads["recommended_next_action"] = leads.apply(action_for, axis=1)
    score_cols = ["lead_id","created_at","cohort_month","first_campaign_id","first_channel","customer_segment","company_size_band","region","job_seniority","business_email","email_engagement_score","website_visits_30d","pricing_page_visits_30d","content_downloads_90d","webinar_attended","demo_requested","marketing_qualified","sales_accepted","won","lead_status","estimated_deal_value_usd","booked_revenue_usd","predicted_win_probability","priority_score","priority_tier","score_reasons","recommended_next_action","score_status"]
    scored = leads[score_cols].sort_values("predicted_win_probability", ascending=False)
    scored.to_csv(OUT/"scored_leads.csv", index=False, date_format="%Y-%m-%d")

    # Monthly outcome and spend view. Campaign spend is separate from first-touch lead counts.
    outcomes = leads.groupby(["cohort_month","first_campaign_id"]).agg(
        leads=("lead_id","size"), mqls=("marketing_qualified","sum"), sqls=("sales_accepted","sum"),
        wins=("won","sum"), booked_revenue_usd=("booked_revenue_usd","sum"), pipeline_value_usd=("pipeline_value_usd","sum")
    ).reset_index().rename(columns={"cohort_month":"month","first_campaign_id":"campaign_id"})
    campaign_monthly = spend.merge(campaigns[["campaign_id","campaign_name","channel"]], on="campaign_id", how="left")
    campaign_monthly = campaign_monthly.merge(outcomes, on=["month","campaign_id"], how="left")
    for col in ["leads","mqls","sqls","wins","booked_revenue_usd","pipeline_value_usd"]: campaign_monthly[col] = campaign_monthly[col].fillna(0)
    for col in ["leads","mqls","sqls","wins","booked_revenue_usd","pipeline_value_usd"]: campaign_monthly[col] = campaign_monthly[col].astype(int)
    campaign_monthly["quarter"] = pd.PeriodIndex(campaign_monthly.month, freq="M").asfreq("Q").astype(str)
    campaign_monthly.to_csv(OUT/"campaign_monthly_performance.csv", index=False)

    campaign_summary = campaign_monthly.groupby(["campaign_id","campaign_name","channel"], as_index=False).agg(
        spend_usd=("spend_usd","sum"), paid_impressions=("paid_impressions","sum"), paid_clicks=("paid_clicks","sum"),
        leads=("leads","sum"), mqls=("mqls","sum"), sqls=("sqls","sum"), wins=("wins","sum"),
        booked_revenue_usd=("booked_revenue_usd","sum"), pipeline_value_usd=("pipeline_value_usd","sum")
    )
    campaign_summary = add_efficiency(campaign_summary).sort_values("revenue_to_spend", ascending=False)
    campaign_summary.to_csv(OUT/"campaign_summary.csv", index=False)
    channel_summary = campaign_summary.groupby("channel", as_index=False).agg(
        spend_usd=("spend_usd","sum"), paid_impressions=("paid_impressions","sum"), paid_clicks=("paid_clicks","sum"),
        leads=("leads","sum"), mqls=("mqls","sum"), sqls=("sqls","sum"), wins=("wins","sum"),
        booked_revenue_usd=("booked_revenue_usd","sum"), pipeline_value_usd=("pipeline_value_usd","sum")
    )
    channel_summary = add_efficiency(channel_summary).sort_values("revenue_to_spend", ascending=False)
    channel_summary.to_csv(OUT/"channel_summary.csv", index=False)
    monthly = campaign_monthly.groupby("month", as_index=False).agg(
        spend_usd=("spend_usd","sum"), leads=("leads","sum"), mqls=("mqls","sum"), sqls=("sqls","sum"), wins=("wins","sum"),
        booked_revenue_usd=("booked_revenue_usd","sum"), pipeline_value_usd=("pipeline_value_usd","sum")
    )
    monthly["cost_per_lead_usd"] = monthly.spend_usd / monthly.leads.replace(0, np.nan)
    monthly["revenue_to_spend"] = monthly.booked_revenue_usd / monthly.spend_usd.replace(0, np.nan)
    monthly.to_csv(OUT/"monthly_performance.csv", index=False)

    # Attribution credit is split across first touch, last touch and unique-channel linear models.
    touch_by_lead = {k:g.sort_values(["occurred_at","touchpoint_id"]) for k,g in touches.groupby("lead_id")}
    attribution_rows = []
    won_leads = leads[leads.won.eq(1)]
    for _, r in won_leads.iterrows():
        t = touch_by_lead.get(r.lead_id)
        if t is None or t.empty: continue
        first_ch = r.first_channel
        last_rows = t[t.is_last_touch.eq(1)]
        last_ch = str(last_rows.iloc[-1].channel) if not last_rows.empty else str(t.iloc[-1].channel)
        unique_channels = list(dict.fromkeys(t.channel.astype(str).tolist()))
        shares = {}
        shares[first_ch] = shares.get(first_ch, 0) + float(r.booked_revenue_usd)
        # The per-lead method values are stored alongside each credited channel.
        lin_share = float(r.booked_revenue_usd) / len(unique_channels)
        credits = {}
        for ch in [first_ch, last_ch, *unique_channels]: credits.setdefault(ch, {"first_touch_revenue_usd":0.0,"last_touch_revenue_usd":0.0,"linear_revenue_usd":0.0})
        credits[first_ch]["first_touch_revenue_usd"] += float(r.booked_revenue_usd)
        credits[last_ch]["last_touch_revenue_usd"] += float(r.booked_revenue_usd)
        for ch in unique_channels: credits[ch]["linear_revenue_usd"] += lin_share
        for credited_ch, vals in credits.items():
            attribution_rows.append({"cohort_month":r.cohort_month,"first_campaign_id":r.first_campaign_id,"first_channel":first_ch,"credited_channel":credited_ch,**vals})
    attrib_detail = pd.DataFrame(attribution_rows)
    attrib_summary = attrib_detail.groupby("credited_channel", as_index=False).agg(
        first_touch_revenue_usd=("first_touch_revenue_usd","sum"), last_touch_revenue_usd=("last_touch_revenue_usd","sum"), linear_revenue_usd=("linear_revenue_usd","sum")
    ).rename(columns={"credited_channel":"channel"})
    for ch in CHANNEL_ORDER:
        if ch not in attrib_summary.channel.to_list(): attrib_summary.loc[len(attrib_summary)] = [ch,0,0,0]
    attrib_summary.to_csv(OUT/"attribution_summary.csv", index=False)
    attrib_detail.to_csv(OUT/"attribution_by_cohort_and_first_campaign.csv", index=False)
    attribution_credit_shift_usd = float(0.5 * (attrib_summary.first_touch_revenue_usd - attrib_summary.last_touch_revenue_usd).abs().sum())
    attribution_credit_shift_rate = float(attribution_credit_shift_usd / attrib_summary.first_touch_revenue_usd.sum()) if attrib_summary.first_touch_revenue_usd.sum() else np.nan
    pd.DataFrame([{"credit_moved_usd":attribution_credit_shift_usd,"share_of_booked_revenue":attribution_credit_shift_rate,"definition":"Half the sum of absolute channel-level differences between first-touch and last-touch credit. Measures how much credit changes channel bucket, not causal impact."}]).to_csv(OUT/"attribution_credit_shift.csv", index=False)

    # Out-of-time score deciles. Decile 1 contains the highest scores.
    holdout = leads.loc[test_mask, ["lead_id","won","predicted_win_probability"]].copy()
    holdout = holdout.sort_values("predicted_win_probability", ascending=False).reset_index(drop=True)
    holdout["decile"] = (np.floor(np.arange(len(holdout))*10/len(holdout)).astype(int)+1).clip(1,10)
    deciles = holdout.groupby("decile", as_index=False).agg(leads=("lead_id","size"), wins=("won","sum"), mean_score=("predicted_win_probability","mean"))
    deciles["win_rate"] = deciles.wins / deciles.leads
    deciles["lift"] = deciles.win_rate / (holdout_rate if holdout_rate else np.nan)
    deciles["decile_label"] = deciles.decile.map(lambda n: "Top 10%" if n==1 else f"Band {n}")
    deciles.to_csv(OUT/"score_deciles_holdout.csv", index=False)

    # Quarter-by-channel efficiency, for the channel heatmap.
    quarter_channel = campaign_monthly.groupby(["quarter","channel"], as_index=False).agg(spend_usd=("spend_usd","sum"), booked_revenue_usd=("booked_revenue_usd","sum"))
    quarter_channel["revenue_to_spend"] = quarter_channel.booked_revenue_usd / quarter_channel.spend_usd.replace(0,np.nan)
    quarter_channel.to_csv(OUT/"channel_quarter_summary.csv", index=False)

    # Mechanical budget-shift example: same budget, historical averages, no saturation assumption.
    low = channel_summary.sort_values("revenue_to_spend", ascending=True).iloc[0]
    high = channel_summary.sort_values("revenue_to_spend", ascending=False).iloc[0]
    transfer = min(float(low.spend_usd)*0.10, float(channel_summary.spend_usd.sum())*0.03)
    low_cpl = float(low.cost_per_lead_usd) if pd.notna(low.cost_per_lead_usd) else np.nan
    high_cpl = float(high.cost_per_lead_usd) if pd.notna(high.cost_per_lead_usd) else np.nan
    lost_leads = transfer/low_cpl if low_cpl and np.isfinite(low_cpl) else 0
    gain_leads = transfer/high_cpl if high_cpl and np.isfinite(high_cpl) else 0
    low_rate = float(low.win_rate_from_lead) if pd.notna(low.win_rate_from_lead) else 0
    high_rate = float(high.win_rate_from_lead) if pd.notna(high.win_rate_from_lead) else 0
    low_rev = float(low.revenue_per_lead_usd) if pd.notna(low.revenue_per_lead_usd) else 0
    high_rev = float(high.revenue_per_lead_usd) if pd.notna(high.revenue_per_lead_usd) else 0
    scenario = pd.DataFrame([{
        "source_channel":str(low.channel), "destination_channel":str(high.channel), "transfer_usd":round(transfer,2),
        "estimated_leads_lost":round(lost_leads,1), "estimated_leads_gained":round(gain_leads,1),
        "estimated_net_leads":round(gain_leads-lost_leads,1),
        "estimated_net_wins":round(gain_leads*high_rate-lost_leads*low_rate,1),
        "estimated_net_booked_revenue_usd":round(gain_leads*high_rev-lost_leads*low_rev,2),
        "warning":"Mechanical scenario only. Uses historical averages and assumes no saturation, auction change or channel interaction. Test before reallocating."
    }])
    scenario.to_csv(OUT/"illustrative_budget_shift.csv", index=False)

    total_spend = float(campaign_summary.spend_usd.sum())
    total_leads = int(campaign_summary.leads.sum()); total_mqls = int(campaign_summary.mqls.sum())
    total_sqls = int(campaign_summary.sqls.sum()); total_wins = int(campaign_summary.wins.sum())
    total_revenue = float(campaign_summary.booked_revenue_usd.sum())
    best_roas = channel_summary.iloc[0]
    best_revenue = channel_summary.sort_values("booked_revenue_usd",ascending=False).iloc[0]
    weakest = channel_summary.sort_values("revenue_to_spend",ascending=True).iloc[0]
    top_campaign = campaign_summary.sort_values("booked_revenue_usd",ascending=False).iloc[0]
    campaign_share = float(top_campaign.booked_revenue_usd / total_revenue) if total_revenue else np.nan
    top_rate = float(y_test[top_idx].mean())
    create_charts(monthly, channel_summary, deciles, attrib_summary, quarter_channel)

    summary_text = f'''# Analysis notes

## What the sample says

The sample contains {total_leads:,} leads across 12 campaigns and seven channels. Recorded program spend is {format_money(total_spend)}. The campaigns created {total_mqls:,} marketing-qualified leads, {total_sqls:,} sales-accepted leads and {total_wins:,} wins. Booked revenue in the sample is {format_money(total_revenue)}, or {total_revenue/total_spend:.2f} dollars of booked revenue for each recorded marketing dollar. This is a revenue-to-spend ratio, not profit or a fully loaded customer-acquisition-cost calculation.

- Overall cost per lead is {format_money(total_spend/total_leads)}. Cost per won deal is {format_money(total_spend/total_wins)}.
- {best_roas.channel} has the highest observed channel revenue-to-spend ratio at {best_roas.revenue_to_spend:.2f}x. {best_revenue.channel} brings in the most booked revenue in absolute dollars.
- {weakest.channel} has the lowest observed revenue-to-spend ratio at {weakest.revenue_to_spend:.2f}x. That is a reason to inspect targeting and conversion quality, not enough on its own to shut the channel off.
- The campaign with the most booked revenue is {top_campaign.campaign_name}; it accounts for {campaign_share:.1%} of recorded booked revenue.

## The lead score

The score is a logistic-regression baseline trained on leads created before October 1, 2025. Evaluation uses October through December as a chronological holdout. On that holdout, ROC AUC is {model_metrics['roc_auc']:.3f}, average precision is {model_metrics['average_precision']:.3f}, and the Brier score is {model_metrics['brier_score']:.4f}. The top-scoring 10% have a {top_rate:.1%} win rate, against {holdout_rate:.1%} for the full holdout, a lift of {model_metrics['lift_top_10pct']:.2f}x. These results describe ranking performance on this simulated sample; they are not a promise of performance in a live CRM.

The score uses information available before sales acceptance: channel and campaign, account size, region, seniority, business email, site visits, pricing visits, content activity, webinar attendance and demo request. It does not use the sales-accepted flag, win outcome, booked revenue or deal value as model inputs. Recommended next actions are rule-based suggestions layered on top of the score, so the reason for a recommendation is visible.

## Attribution is a view, not a verdict

First-touch, last-touch and linear models allocate the same booked deals in different ways. First touch gives credit to the campaign that introduced the lead; last touch gives credit to the last recorded channel; linear spreads credit across unique channels touched. None of these methods proves that a channel caused a sale. The multi-touch log is synthetic and the paths are illustrative. Use this comparison to find where the story changes, then validate it with experiments or a stronger incrementality design. Across this sample, about {format_money(attribution_credit_shift_usd)} of credit changes channel bucket between first-touch and last-touch reporting, equal to {attribution_credit_shift_rate:.1%} of booked revenue. That amount measures attribution disagreement; it is not revenue gained or lost.

## A budget question worth testing

A mechanical scenario moves {format_money(transfer)} from {low.channel} to {high.channel}. Based on historical average cost and revenue per lead, it estimates {scenario.iloc[0].estimated_net_leads:+.1f} net leads and {scenario.iloc[0].estimated_net_booked_revenue_usd:+,.0f} net booked revenue. This is not a forecast: no channel saturation, audience overlap, auction changes, sales capacity or uncertainty intervals are included. Treat it as a hypothesis for a capped test.

## Practical next steps

1. Put a short SLA around demo requests and repeat pricing visits, then measure response time and progression to sales acceptance.
2. Compare campaigns on cost per sales-accepted lead and cost per win alongside cost per lead. Keep lead volume in the view, but do not let volume settle the decision.
3. Test channel changes in small increments and preserve a control group where practical. Avoid reallocating the full budget based on one retrospective ratio.
4. Add CRM outcomes, account-level duplicates, sales touch timestamps, margins and consented attribution data before using this approach for real planning.

## Data and limitations

All rows are synthetic. Monthly spend is simulated; paid impressions and clicks are populated only for Paid Search and Paid Social because those figures do not have a comparable meaning for the other channels. Revenue is booked deal value, not margin. Leads are assigned one first-touch campaign for acquisition reporting, while touchpoints are used for attribution comparisons. The sample has no randomised control group, so channel results are descriptive rather than causal.
'''
    (OUT/"analysis_summary.md").write_text(summary_text, encoding="utf-8")

    # Keep the dashboard queue limited to open leads in the chronological holdout cohort.
    priority = leads[(leads.created_at >= CUTOFF) & (leads.lead_status.str.startswith("Open"))].copy()
    priority = priority.sort_values("predicted_win_probability",ascending=False).groupby("first_campaign_id", group_keys=False).head(25)
    priority = priority.sort_values("predicted_win_probability",ascending=False)
    dash_data = {
        "campaignMonthly": campaign_monthly[["month","campaign_id","campaign_name","channel","spend_usd","leads","mqls","sqls","wins","booked_revenue_usd","pipeline_value_usd","paid_impressions","paid_clicks"]].replace({np.nan:None}).to_dict(orient="records"),
        "campaigns": campaign_summary.replace({np.nan:None}).to_dict(orient="records"),
        "channels": channel_summary.replace({np.nan:None}).to_dict(orient="records"),
        "attribution": attrib_detail.replace({np.nan:None}).to_dict(orient="records"),
        "attributionSummary": attrib_summary.replace({np.nan:None}).to_dict(orient="records"),
        "deciles": deciles.replace({np.nan:None}).to_dict(orient="records"),
        "model": model_metrics,
        "priorityQueue": [{
            "lead_id":r.lead_id,"created_at":r.created_at.strftime("%Y-%m-%d"),"cohort_month":r.cohort_month,
            "campaign_id":r.first_campaign_id,"channel":r.first_channel,"score":round(float(r.priority_score),1),
            "tier":r.priority_tier,"action":r.recommended_next_action,"reasons":r.score_reasons,
            "company_size":r.company_size_band,"seniority":r.job_seniority,"demo":int(r.demo_requested),"pricing_visits":int(r.pricing_page_visits_30d)
        } for _,r in priority.iterrows()],
        "overall":{"spend":total_spend,"leads":total_leads,"mqls":total_mqls,"sqls":total_sqls,"wins":total_wins,"revenue":total_revenue}
    }
    (OUT/"dashboard_data.json").write_text(json.dumps(dash_data,ensure_ascii=False,default=str),encoding="utf-8")
    template_path=ROOT/"templates"/"dashboard_template.html"
    if template_path.exists():
        template=template_path.read_text(encoding="utf-8")
        template=template.replace("__DATA_JSON__",json.dumps(dash_data,ensure_ascii=False,default=str).replace("</","<\\/"))
        (OUT/"dashboard.html").write_text(template,encoding="utf-8")
        # GitHub Pages can serve the dashboard directly from the repository root.
        (ROOT/"index.html").write_text(template,encoding="utf-8")

    # A small SQLite copy makes the project easy to explore without importing CSVs by hand.
    db_path = PROCESSED/"marketing_analytics.sqlite"
    with sqlite3.connect(db_path) as conn:
        db_leads = leads.copy()
        db_leads["created_quarter"] = db_leads["created_quarter"].astype(str)
        db_leads["created_at"] = db_leads["created_at"].dt.strftime("%Y-%m-%d")
        db_touches = touches.copy()
        db_touches["occurred_at"] = db_touches["occurred_at"].dt.strftime("%Y-%m-%d")
        db_spend = spend.copy()
        db_campaigns = campaigns.copy()
        db_tables = {
            "raw_leads": db_leads, "touchpoints": db_touches, "campaigns": db_campaigns,
            "campaign_spend_monthly": db_spend, "scored_leads": scored,
            "campaign_summary": campaign_summary, "channel_summary": channel_summary,
            "campaign_monthly_performance": campaign_monthly, "attribution_summary": attrib_summary,
            "score_deciles_holdout": deciles,
        }
        for table_name, frame in db_tables.items():
            frame.to_sql(table_name, conn, if_exists="replace", index=False)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_raw_leads_campaign ON raw_leads(first_campaign_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_raw_leads_month ON raw_leads(created_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_touchpoints_lead ON touchpoints(lead_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_monthly_campaign ON campaign_monthly_performance(campaign_id, month)")

    build_report(total_spend,total_leads,total_mqls,total_sqls,total_wins,total_revenue,channel_summary,campaign_summary,model_metrics,deciles,scenario.iloc[0],weakest,best_roas,best_revenue,attribution_credit_shift_usd,attribution_credit_shift_rate)
    print("Analysis complete.")
    print(f"Leads {total_leads:,} | MQL {total_mqls:,} | SQL {total_sqls:,} | Wins {total_wins:,}")
    print(f"Spend {format_money(total_spend)} | Booked revenue {format_money(total_revenue)} | Revenue/spend {total_revenue/total_spend:.2f}x")
    print(f"Holdout ROC AUC {model_metrics['roc_auc']:.3f} | Top-decile lift {model_metrics['lift_top_10pct']:.2f}x")


def build_report(total_spend,total_leads,total_mqls,total_sqls,total_wins,total_revenue,channels,campaigns,model_metrics,deciles,scenario,weakest,best_roas,best_revenue,attribution_credit_shift_usd,attribution_credit_shift_rate):
    out_path=REPORTS/"marketing_campaign_effectiveness_report.pdf"
    doc=SimpleDocTemplate(str(out_path),pagesize=letter,rightMargin=.62*inch,leftMargin=.62*inch,topMargin=.62*inch,bottomMargin=.62*inch,title="Marketing Campaign Effectiveness and Lead Prioritization")
    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name="CoverTitle",parent=styles["Title"],fontName="Helvetica-Bold",fontSize=25,leading=30,textColor=colors.HexColor("#172b3d"),alignment=TA_LEFT,spaceAfter=12))
    styles.add(ParagraphStyle(name="Deck",parent=styles["Normal"],fontSize=11,leading=16,textColor=colors.HexColor("#506174"),spaceAfter=14))
    styles.add(ParagraphStyle(name="Section",parent=styles["Heading1"],fontSize=18,leading=22,textColor=colors.HexColor("#172b3d"),spaceBefore=4,spaceAfter=10))
    styles.add(ParagraphStyle(name="Sub",parent=styles["Heading2"],fontSize=12,leading=15,textColor=colors.HexColor("#167d79"),spaceBefore=9,spaceAfter=5))
    styles.add(ParagraphStyle(name="BodyCompact",parent=styles["BodyText"],fontSize=9.2,leading=13,spaceAfter=6))
    styles.add(ParagraphStyle(name="Small",parent=styles["BodyText"],fontSize=8,leading=10,textColor=colors.HexColor("#536273"),spaceAfter=4))
    story=[]
    def P(txt,style="BodyCompact"): return Paragraph(txt,styles[style])
    def footer(canvas,doc_):
        canvas.saveState(); canvas.setStrokeColor(colors.HexColor("#d9e0e5")); canvas.line(.62*inch,.45*inch,7.88*inch,.45*inch)
        canvas.setFont("Helvetica",8); canvas.setFillColor(colors.HexColor("#69798a")); canvas.drawString(.62*inch,.28*inch,"Marketing campaign effectiveness | Synthetic portfolio analysis")
        canvas.drawRightString(7.88*inch,.28*inch,f"Page {doc_.page}"); canvas.restoreState()
    def table(data,widths=None,header=True):
        t=Table(data,colWidths=widths,repeatRows=1 if header else 0,hAlign="LEFT")
        commands=[("VALIGN",(0,0),(-1,-1),"MIDDLE"),("LEFTPADDING",(0,0),(-1,-1),6),("RIGHTPADDING",(0,0),(-1,-1),6),("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),("LINEBELOW",(0,0),(-1,-1),.35,colors.HexColor("#dce3e8"))]
        if header: commands += [("BACKGROUND",(0,0),(-1,0),colors.HexColor("#eaf0f3")),("TEXTCOLOR",(0,0),(-1,0),colors.HexColor("#172b3d")),("FONTNAME",(0,0),(-1,0),"Helvetica-Bold")]
        commands += [("FONTSIZE",(0,0),(-1,-1),8),("FONTNAME",(0,1),(-1,-1),"Helvetica")]
        t.setStyle(TableStyle(commands)); return t

    story += [Spacer(1,.35*inch),P("MARKETING PERFORMANCE / LEAD PRIORITIZATION","Small"),Spacer(1,.08*inch),P("From campaign spend to sales conversations","CoverTitle"),P("A practical review of what marketing brings in, where leads fall out of the funnel, and how to choose the next lead to contact.","Deck"),Spacer(1,.12*inch)]
    kpi_data=[["Recorded spend","Leads","Sales-accepted","Won deals","Booked revenue"],[format_money(total_spend),f"{total_leads:,}",f"{total_sqls:,}",f"{total_wins:,}",format_money(total_revenue)]]
    kpi=table(kpi_data,[1.42*inch]*5)
    kpi.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#172b3d")),("TEXTCOLOR",(0,0),(-1,0),colors.white),("FONTSIZE",(0,0),(-1,0),7.5),("FONTSIZE",(0,1),(-1,1),11),("FONTNAME",(0,1),(-1,1),"Helvetica-Bold"),("BOX",(0,0),(-1,-1),.5,colors.HexColor("#dce3e8"))]))
    story += [kpi,Spacer(1,.18*inch),P("The central finding","Sub"),P(f"Lead volume is only the opening number. Across the sample, {total_leads:,} leads became {total_mqls:,} marketing-qualified leads, {total_sqls:,} sales-accepted leads and {total_wins:,} wins. Recorded booked revenue is {format_money(total_revenue)} against {format_money(total_spend)} of program spend. That works out to {total_revenue/total_spend:.2f}x booked revenue per recorded marketing dollar, but it is not profit and does not include every cost of selling or serving a customer."),P(f"{best_roas.channel} has the highest observed revenue-to-spend ratio. {best_revenue.channel} brings in the most booked revenue in absolute dollars. Those are different questions, and both belong in a budget review."),Spacer(1,.1*inch),P("What this report covers","Sub"),P("The work combines campaign economics, funnel losses, a chronological lead-score test, and a comparison of first-touch, last-touch and linear attribution. All records are synthetic and exist to demonstrate the workflow; none should be read as the performance of a real company."),PageBreak()]

    story += [P("1. Campaign economics","Section"),P("Cost per lead is helpful for spotting expensive acquisition. It is not enough to decide where budget belongs. A low-cost channel can still struggle to create sales-ready demand, while a costly channel may earn its place if its leads progress and close at a higher rate."),Image(str(VIZ/"channel_economics.png"),width=7.05*inch,height=3.8*inch),Spacer(1,.05*inch)]
    rows=[["Channel","Spend","Leads","Cost / lead","Wins","Cost / win","Revenue / spend"]]
    for _,r in channels.sort_values("revenue_to_spend",ascending=False).iterrows():
        rows.append([r.channel,format_money(r.spend_usd),f"{int(r.leads):,}",format_money(r.cost_per_lead_usd),f"{int(r.wins):,}",format_money(r.cost_per_win_usd),f"{r.revenue_to_spend:.2f}x"])
    story += [table(rows,[1.25*inch,.9*inch,.55*inch,.8*inch,.48*inch,.78*inch,.95*inch]),Spacer(1,.08*inch),P(f"The weakest observed ratio belongs to {weakest.channel} at {weakest.revenue_to_spend:.2f}x. This is a review cue rather than an automatic cut: check audience overlap, assisted conversions, sales capacity and what would happen if that channel disappeared before making a change."),PageBreak()]

    story += [P("2. Where the funnel thins out","Section"),Image(str(VIZ/"funnel_dropoff.png"),width=6.8*inch,height=3.2*inch),Image(str(VIZ/"monthly_funnel.png"),width=7.0*inch,height=3.1*inch),P("The funnel stages are nested: every sales-accepted lead was marketing-qualified, and every win was sales-accepted. The largest raw drop is from initial lead to marketing qualification, but the most useful operating question is which campaigns deliver people who sales accepts and eventually closes. A follow-up SLA on clear intent signals is easier to act on than a vague request to generate more leads."),PageBreak()]

    story += [P("3. A lead score sales can question","Section"),P("The baseline score uses a logistic regression trained on January through September, then tests its rankings on October through December. It uses channel, campaign, account size, seniority, region, business email, recent site activity, pricing visits, content activity, webinar attendance and demo requests. It does not use the sales outcome, deal value or revenue as inputs."),Image(str(VIZ/"lead_score_lift.png"),width=7.0*inch,height=3.45*inch)]
    mm=[["Test measure","Result"],["Holdout period",f"{model_metrics['test_start']} to {model_metrics['test_end']}"],["Holdout leads",f"{model_metrics['test_leads']:,}"],["ROC AUC",f"{model_metrics['roc_auc']:.3f}"],["Average precision",f"{model_metrics['average_precision']:.3f}"],["Brier score",f"{model_metrics['brier_score']:.4f}"],["Win rate in top score decile",format_pct(float(deciles.iloc[0].win_rate))],["Win rate across holdout",format_pct(model_metrics['holdout_win_rate'])],["Top-decile lift",f"{model_metrics['lift_top_10pct']:.2f}x"]]
    story += [table(mm,[2.6*inch,2.0*inch]),Spacer(1,.08*inch),P("The point of the score is to order the queue, not to replace a sales rep's judgment. Each record carries a short list of visible signals and a suggested next step. The reported metrics come from the held-out quarter; the full scored CSV also contains historical scores for exploration, and those earlier scores are not a fair out-of-time test."),PageBreak()]

    story += [P("4. Attribution changes the story","Section"),P("A first-touch report asks which campaign introduced the lead. A last-touch report asks which channel appeared last before the recorded path ended. Linear attribution shares credit among unique channels touched. Each view answers a different bookkeeping question; none proves that a channel caused the sale."),Image(str(VIZ/"attribution_comparison.png"),width=7.05*inch,height=3.45*inch),Image(str(VIZ/"channel_quarter_heatmap.png"),width=6.3*inch,height=3.4*inch),P(f"Across all channels, about {format_money(attribution_credit_shift_usd)} of booked-revenue credit moves from one channel bucket to another when the report changes from first-touch to last-touch. That is {attribution_credit_shift_rate:.1%} of booked revenue. It is attribution disagreement, not money gained or lost."),P("The quarterly heatmap is included to show how quickly a strong-looking ratio can move when a small channel has only a handful of wins. Read it with volume and spend, not in isolation."),PageBreak()]

    story += [P("5. What to do next","Section"),P("Start with a measured sales handoff. Demo requests and repeat pricing visits are the clearest immediate signals in this sample, so route them quickly and measure whether a faster response improves acceptance and win rate."),P("Use three campaign measures together: cost per sales-accepted lead, cost per win, and booked revenue per recorded marketing dollar. Keep cost per lead as an acquisition diagnostic, not the main verdict."),P(f"A simple budget exercise would move {format_money(scenario['transfer_usd'])} from {scenario['source_channel']} to {scenario['destination_channel']}. Under historical average rates, that would suggest {scenario['estimated_net_leads']:+.1f} net leads and {scenario['estimated_net_booked_revenue_usd']:+,.0f} net booked revenue. That is a mechanical scenario, not a forecast: it assumes no saturation, no auction movement, no audience overlap and no sales-capacity limit. A small test is the sensible next step."),P("Before applying this to a real business","Sub"),P("Replace the demo data with consented CRM and campaign records, define a common lead identity, deduplicate people and accounts, align the spend and sales windows, and add gross margin or contribution profit. Keep a holdout period for score testing. For budget changes, use a control group or incrementality test where possible."),P("Method and limitations","Sub"),P("The dataset is synthetic. Cost and delivery numbers are generated. Revenue is booked deal value, not contribution margin. Paid impressions and clicks are included only for Paid Search and Paid Social because other channels do not share the same exposure denominator. The score is a simple baseline, the holdout is one quarter, and the touchpoint paths are simulated. All channel and attribution findings are descriptive; no causal claim is made."),Spacer(1,.12*inch),P("Files to explore","Sub"),P("The companion project includes raw lead and touchpoint files, campaign spend records, scored leads, model metrics, campaign and channel rollups, attribution tables, SQL examples, Python scripts, chart files, and an interactive dashboard. Use README.md for the run instructions.")]
    doc.build(story,onFirstPage=footer,onLaterPages=footer)

if __name__ == "__main__": main()
