import sqlite3
import unittest
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

class ProjectDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.leads = pd.read_csv(ROOT / "data/raw/leads.csv")
        cls.touches = pd.read_csv(ROOT / "data/raw/touchpoints.csv")
        cls.campaigns = pd.read_csv(ROOT / "data/raw/campaigns.csv")
        cls.spend = pd.read_csv(ROOT / "data/raw/campaign_spend_monthly.csv")

    def test_lead_ids_are_unique(self):
        self.assertTrue(self.leads.lead_id.is_unique)
        self.assertGreater(len(self.leads), 1000)

    def test_funnel_stages_are_nested(self):
        self.assertTrue((self.leads.sales_accepted <= self.leads.marketing_qualified).all())
        self.assertTrue((self.leads.won <= self.leads.sales_accepted).all())
        self.assertGreater(int(self.leads.marketing_qualified.sum()), int(self.leads.sales_accepted.sum()))

    def test_touchpoints_link_to_leads(self):
        lead_ids = set(self.leads.lead_id)
        self.assertTrue(set(self.touches.lead_id).issubset(lead_ids))
        by_lead = self.touches.groupby("lead_id").agg(first=("is_first_touch", "sum"), last=("is_last_touch", "sum"))
        self.assertTrue((by_lead["first"] == 1).all())
        self.assertTrue((by_lead["last"] == 1).all())

    def test_campaign_month_spend_has_no_duplicate_keys(self):
        self.assertFalse(self.spend.duplicated(["month", "campaign_id"]).any())
        self.assertEqual(self.spend.campaign_id.nunique(), len(self.campaigns))
        self.assertTrue((self.spend.spend_usd > 0).all())

    def test_model_is_evaluated_on_later_dates(self):
        metrics_path = ROOT / "outputs/model_holdout_metrics.csv"
        self.assertTrue(metrics_path.exists())
        metrics = pd.read_csv(metrics_path).iloc[0]
        self.assertLess(metrics.train_end, metrics.test_start)
        self.assertGreaterEqual(metrics.roc_auc, 0.5)
        self.assertLessEqual(metrics.roc_auc, 1.0)
        self.assertGreater(metrics.lift_top_10pct, 1.0)

    def test_dashboard_report_and_score_file_exist(self):
        self.assertTrue((ROOT / "index.html").exists())
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertNotIn("__DATA_JSON__", html)
        self.assertIn("const DATA =", html)
        self.assertIn("Chart", html)
        self.assertTrue((ROOT / "reports/marketing_campaign_effectiveness_report.pdf").exists())
        self.assertTrue((ROOT / "outputs/scored_leads.csv").exists())

    def test_sqlite_database_has_core_tables(self):
        db = ROOT / "data/processed/marketing_analytics.sqlite"
        self.assertTrue(db.exists())
        with sqlite3.connect(db) as conn:
            tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            self.assertTrue({"raw_leads", "touchpoints", "scored_leads", "channel_summary", "attribution_summary"}.issubset(tables))
            n = conn.execute("SELECT COUNT(*) FROM raw_leads").fetchone()[0]
            self.assertEqual(n, len(self.leads))

if __name__ == "__main__":
    unittest.main()
