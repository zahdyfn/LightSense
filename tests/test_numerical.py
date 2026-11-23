"""Pengujian independen tanpa koneksi sensor atau browser."""

import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from numerical import (  # noqa: E402
    analyze,
    clean_data,
    error_metrics,
    interpolation_anchors,
    interpolation_steps,
    least_squares,
    linear_interpolation,
)


class TestNumerical(unittest.TestCase):
    def setUp(self):
        self.source = pd.read_csv(Path(__file__).resolve().parents[1] / "data" / "bh1750_public.csv")

    def test_public_data_exact_rows(self):
        self.assertEqual(len(self.source), 30)
        self.assertAlmostEqual(self.source.iloc[0].sensor_lux, 1.67)
        self.assertAlmostEqual(self.source.iloc[-1].reference_lux, 717)

    def test_least_squares_known_line(self):
        m = least_squares([0, 1, 2, 3], [4, 7, 10, 13])
        self.assertAlmostEqual(m.a, 3)
        self.assertAlmostEqual(m.b, 4)
        np.testing.assert_allclose(m.predict([5]), [19])

    def test_interpolation_known_line_and_boundary(self):
        anchors = interpolation_anchors(pd.DataFrame({
            "sensor_lux": [0, 10, 20], "reference_lux": [2, 12, 22]
        }))
        result = linear_interpolation([-1, 0, 5, 15, 20, 30], anchors)
        self.assertTrue(np.isnan(result[0]))
        self.assertTrue(np.isnan(result[-1]))
        np.testing.assert_allclose(result[1:5], [2, 7, 17, 22])
        steps = interpolation_steps(5, anchors)
        self.assertEqual(steps["x0"], 0)
        self.assertEqual(steps["x1"], 10)

    def test_metrics(self):
        output = error_metrics([10, 20], [12, 18])
        self.assertAlmostEqual(output["MAE"], 2)
        self.assertAlmostEqual(output["RMSE"], 2)
        self.assertAlmostEqual(output["MAPE (%)"], 15)

    def test_data_validation(self):
        bad = self.source.copy()
        bad.loc[0, "sensor_lux"] = -1
        good = clean_data(bad)
        self.assertEqual(len(good), 29)
        with self.assertRaises(ValueError):
            clean_data(pd.DataFrame({"sensor_lux": [1, 1], "reference_lux": [1, 2]}))

    def test_holdout_independent_and_valid(self):
        result = analyze(self.source)
        self.assertEqual(len(result["train"]) + len(result["test"]), 30)
        self.assertTrue(set(result["train"]["sensor_lux"]).isdisjoint(set(result["test"]["sensor_lux"])))
        self.assertTrue(np.isfinite(result["metrics"].loc[:, ["MAE", "RMSE", "MAPE (%)"]].to_numpy()).all())
        self.assertEqual(len(result["metrics"]), 3)


if __name__ == "__main__":
    unittest.main()
