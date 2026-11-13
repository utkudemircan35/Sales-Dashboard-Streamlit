"""Basit arayuz, ortak filtreler, aciklamalar ve tahmin davranisi."""
from pathlib import Path
from datetime import date
import unittest
import numpy as np
from streamlit.testing.v1 import AppTest


class AppTests(unittest.TestCase):
    def test_sections_filters_and_forecast(self):
        path = Path(__file__).resolve().parents[1] / "streamlit_app.py"
        app = AppTest.from_file(str(path), default_timeout=90).run()
        self.assertFalse(app.exception)
        self.assertTrue(app.metric[0].value.startswith("₺"))
        self.assertTrue(app.metric[0].proto.help)
        self.assertEqual(len(app.button), 0)
        for section in ["Customers", "Products", "Forecast", "Data notes"]:
            app.segmented_control(key="section").set_value(section).run()
            self.assertFalse(app.exception, section)
        app.segmented_control(key="section").set_value("Products").run()
        app.selectbox(key="category").set_value("1000 Parça Puzzle").run()
        self.assertFalse(app.exception)
        self.assertTrue(any("1000 Parça Puzzle" in caption.value for caption in app.caption))
        app.selectbox(key="category").set_value("All categories").run()
        app.segmented_control(key="section").set_value("Forecast").run()
        self.assertFalse(app.exception)
        estimates = app.dataframe[-1].value.Estimate.to_numpy()
        self.assertEqual(len(estimates), 4)
        self.assertTrue(np.isfinite(estimates).all())
        self.assertTrue(any("Selected method:" in caption.value for caption in app.caption))
        self.assertEqual(app.metric[2].label, "Independent test error")
        for horizon in [8, 12]:
            app.selectbox(key="forecast_horizon").set_value(horizon).run()
            self.assertFalse(app.exception)
            self.assertEqual(len(app.dataframe[-1].value), horizon)
        app.segmented_control(key="forecast_target").set_value("Sales (₺)").run()
        self.assertFalse(app.exception)
        self.assertTrue(app.metric[0].value.startswith("₺"))
        app.date_input(key="period").set_value((date(2020, 1, 2), date(2020, 1, 3))).run()
        self.assertFalse(app.exception)
        self.assertTrue(any("complete calendar weeks" in info.value for info in app.info))
        app.segmented_control(key="section").set_value("Products").run()
        self.assertFalse(app.exception)
        self.assertTrue(any("3 complete" in info.value for info in app.info))


if __name__ == "__main__":
    unittest.main()
