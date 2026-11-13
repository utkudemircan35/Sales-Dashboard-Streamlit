"""Regresyon kontrolleri: python -m unittest discover -s tests -v"""
import unittest
import numpy as np
import pandas as pd

from data_analysis import clean_transactions, abc_xyz_analysis, monthly_sales
from forecast import (complete_week_index, prepare_weekly_data, evaluate_forecast,
                      predict_time_model, selection_origins, required_weeks, error_scores)


def transactions(dates, quantities=None, prices=None, codes=None):
    count = len(dates)
    return pd.DataFrame({
        "InvoiceNo": [f"I{i}" for i in range(count)], "CustomerID": "Customer",
        "InvoiceDate": pd.to_datetime(dates), "StockCode": codes or ["1"] * count,
        "Description": "Book", "Category": "Category", "City": "City",
        "Quantity": quantities if quantities is not None else [10.] * count,
        "NetPrice": prices if prices is not None else [10.] * count,
        "UnitPrice": 12.,
    })


class AnalysisTests(unittest.TestCase):
    def test_missing_city_is_kept_and_removals_reconcile(self):
        raw = transactions(["2020-01-02"] * 4, [1, -2, 0, 3])
        raw.loc[0, "City"] = None
        raw.loc[0, "UnitPrice"] = None
        raw = pd.concat([raw, raw.iloc[[0]]], ignore_index=True)
        clean, report = clean_transactions(raw)
        self.assertEqual(len(clean), 2)
        self.assertEqual(clean.iloc[0]["City"], "Unknown")
        self.assertEqual(report["possible_return_rows"], 1)
        self.assertEqual(report["raw_rows"], report["clean_rows"] + sum(s["Rows removed"] for s in report["steps"]))

    def test_single_dominant_product_is_a(self):
        clean, _ = clean_transactions(transactions(["2020-01-02"] * 3, [90, 6, 4], codes=["1", "2", "3"]))
        result = abc_xyz_analysis(clean)
        self.assertEqual(result.iloc[0]["ABCClass"], "A")
        self.assertEqual(abc_xyz_analysis(clean.iloc[:1]).iloc[0]["ABCClass"], "A")
        self.assertTrue(result["CV"].isna().all())
        self.assertTrue((result["XYZClass"] == "N/A").all())

    def test_xyz_uses_units_not_price(self):
        clean, _ = clean_transactions(transactions(["2020-01-15", "2020-02-15", "2020-03-15"], prices=[1, 10, 100]))
        result = abc_xyz_analysis(clean, "2020-01-01", "2020-03-31")
        self.assertEqual(result.iloc[0]["CV"], 0)
        self.assertEqual(result.iloc[0]["XYZClass"], "X")

    def test_missing_month_counts_as_zero(self):
        clean, _ = clean_transactions(transactions(["2020-01-15", "2020-03-15"]))
        self.assertEqual(monthly_sales(clean).loc[pd.Period("2020-02")], 0)
        result = abc_xyz_analysis(clean, "2020-01-01", "2020-03-31")
        self.assertAlmostEqual(result.iloc[0]["CV"], np.std([10, 0, 10], ddof=1) / np.mean([10, 0, 10]))

    def test_partial_months_do_not_create_xyz_history(self):
        clean, _ = clean_transactions(transactions(["2020-01-31", "2020-02-15", "2020-03-01"]))
        self.assertEqual(abc_xyz_analysis(clean).iloc[0]["XYZClass"], "N/A")

    def test_empty_complete_calendar_is_safe(self):
        clean, _ = clean_transactions(transactions(["2020-01-02"]))
        weeks = complete_week_index("2020-01-02", "2020-01-03")
        self.assertTrue(prepare_weekly_data(clean, weeks).empty)

    def test_calendar_retains_zero_sales_weeks(self):
        clean, _ = clean_transactions(transactions(["2020-06-01", "2020-06-15"]))
        weeks = complete_week_index("2020-06-01", "2020-06-21")
        weekly = prepare_weekly_data(clean, weeks)
        self.assertEqual(weekly["Units"].tolist(), [10, 0, 10])
        self.assertEqual(len(weekly), 3)

    def test_test_values_cannot_change_model_predictions(self):
        weekly = pd.DataFrame({"Week Start": pd.date_range("2020-01-06", periods=40, freq="W-MON"),
                               "Period": np.arange(1, 41), "Units": np.arange(100., 140.)})
        result = evaluate_forecast(weekly, "Units", 4)
        changed = weekly.copy()
        changed.loc[result["test_start"]:, "Units"] *= 100
        changed_result = evaluate_forecast(changed, "Units", 4)
        self.assertEqual(result["model"], changed_result["model"])
        pd.testing.assert_frame_equal(result["comparison"], changed_result["comparison"])
        np.testing.assert_allclose(result["test_table"].Predicted, changed_result["test_table"].Predicted)
        np.testing.assert_array_equal(changed_result["test_table"].Actual, changed.iloc[-4:].Units)
        np.testing.assert_array_equal(weekly.Units, np.arange(100., 140.))

    def test_product_forecast_uses_selected_calendar(self):
        dates = pd.date_range("2020-06-01", periods=24, freq="W-MON")
        clean, _ = clean_transactions(transactions(dates))
        weeks = complete_week_index(dates[0], dates[-1] + pd.Timedelta(days=6))
        weekly = prepare_weekly_data(clean, weeks)
        result = evaluate_forecast(weekly, "Units", 4)
        self.assertAlmostEqual(result["future"].sum(), 40)
        self.assertEqual(result["test_scores"]["MAE"], 0)
        self.assertEqual(len(result["test_table"]), 4)

    def test_validation_windows_match_horizon_and_exclude_final_test(self):
        for horizon in [4, 8, 12]:
            origins = selection_origins(60, horizon)
            self.assertGreaterEqual(len(origins), 2)
            self.assertGreaterEqual(origins[0], 12)
            self.assertEqual(origins[-1] + horizon, 60 - horizon)
            for previous, following in zip(origins, origins[1:]):
                self.assertEqual(previous + horizon, following)

    def test_short_history_is_rejected_for_each_horizon(self):
        for horizon in [4, 8, 12]:
            with self.assertRaises(ValueError):
                selection_origins(required_weeks(horizon) - 1, horizon)
            self.assertEqual(len(selection_origins(required_weeks(horizon), horizon)), 2)

    def test_weighted_average_favors_recent_week(self):
        train = pd.DataFrame({"Units": [10., 20., 30., 40.]})
        prediction = predict_time_model("Weighted 4 weeks", train, "Units", [5, 6, 7, 8])
        np.testing.assert_allclose(prediction, [30., 30., 30., 30.])

    def test_zero_sales_error_is_not_a_fake_percentage(self):
        score = error_scores([0., 0.], [0., 0.])
        self.assertEqual(score["MAE"], 0)
        self.assertTrue(np.isnan(score["WAPE (%)"]))

    def test_future_uses_selected_method_refitted_on_all_observed_weeks(self):
        weekly = pd.DataFrame({"Week Start": pd.date_range("2020-01-06", periods=40, freq="W-MON"),
                               "Period": np.arange(1, 41), "Units": np.arange(100., 140.)})
        result = evaluate_forecast(weekly, "Units", 8)
        self.assertEqual(result["model"], "Linear trend")
        np.testing.assert_allclose(result["future"], np.arange(140., 148.))
        score = error_scores(result["test_table"].Actual, result["test_table"].Predicted)
        self.assertEqual(score["WAPE (%)"], result["test_scores"]["WAPE (%)"])


if __name__ == "__main__":
    unittest.main()
