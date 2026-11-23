"""Algoritma numerik LightSense, terpisah dari antarmuka Streamlit.

Semua pasangan data memakai x = pembacaan sensor (lux) dan
y = pembacaan lux meter referensi (lux).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd


REQUIRED_COLUMNS = ("sensor_lux", "reference_lux")


def clean_data(data: pd.DataFrame) -> pd.DataFrame:
    """Validasi data dan tolak nilai yang tidak dapat dipakai saat kalibrasi."""
    if not all(name in data.columns for name in REQUIRED_COLUMNS):
        raise ValueError("Kolom wajib: sensor_lux dan reference_lux.")

    frame = data.loc[:, REQUIRED_COLUMNS].copy()
    for column in REQUIRED_COLUMNS:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")

    frame = frame.replace([np.inf, -np.inf], np.nan).dropna()
    frame = frame[(frame["sensor_lux"] >= 0) & (frame["reference_lux"] >= 0)]
    frame = frame.reset_index(drop=True)
    if len(frame) < 6 or frame["sensor_lux"].nunique() < 6:
        raise ValueError("Dibutuhkan minimal 6 pasangan valid dengan 6 pembacaan sensor berbeda.")
    return frame


def split_data(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Pilih titik uji interior secara sistematis; kedua ujung tetap latih.

    Kelompok dengan nilai sensor identik berada di satu subset, sehingga
    interpolasi tidak bisa 'melihat' observasi dari kelompok data uji.
    """
    values = np.sort(frame["sensor_lux"].unique())
    interior = values[1:-1]
    # Sekitar 20-25% titik untuk evaluasi, dengan cakupan rentang lux.
    test_points = set(interior[2::4].tolist())
    if not test_points:
        test_points = {float(interior[len(interior) // 2])}
    is_test = frame["sensor_lux"].isin(test_points)
    train = frame.loc[~is_test].sort_values("sensor_lux").reset_index(drop=True)
    test = frame.loc[is_test].sort_values("sensor_lux").reset_index(drop=True)
    return train, test


@dataclass(frozen=True)
class LeastSquaresResult:
    a: float
    b: float
    n: int
    sum_x: float
    sum_y: float
    sum_x2: float
    sum_xy: float
    denominator: float

    def predict(self, x: Any) -> np.ndarray:
        return self.a * np.asarray(x, dtype=float) + self.b


def least_squares(x: Any, y: Any) -> LeastSquaresResult:
    """Hitung regresi linear y=a*x+b dengan rumus normal secara eksplisit."""
    xarr = np.asarray(x, dtype=float)
    yarr = np.asarray(y, dtype=float)
    if xarr.ndim != 1 or xarr.shape != yarr.shape or len(xarr) < 2:
        raise ValueError("x dan y harus vektor dengan panjang sama (minimal 2).")
    n = len(xarr)
    sx = float(np.sum(xarr))
    sy = float(np.sum(yarr))
    sx2 = float(np.dot(xarr, xarr))
    sxy = float(np.dot(xarr, yarr))
    denominator = n * sx2 - sx**2
    if np.isclose(denominator, 0.0):
        raise ValueError("Regresi gagal: seluruh nilai sensor terlalu seragam.")
    a = (n * sxy - sx * sy) / denominator
    b = (sy - a * sx) / n
    return LeastSquaresResult(a, b, n, sx, sy, sx2, sxy, denominator)


def interpolation_anchors(train: pd.DataFrame) -> pd.DataFrame:
    """Jika ada x duplikat, gunakan rata-rata referensi sebagai satu titik."""
    return (
        train.groupby("sensor_lux", as_index=False, sort=True)["reference_lux"]
        .mean()
        .sort_values("sensor_lux")
        .reset_index(drop=True)
    )


def linear_interpolation(values: Any, anchors: pd.DataFrame) -> np.ndarray:
    """Interpolasi linear potongan, tidak mengekstrapolasi di luar domain."""
    xin = np.asarray(values, dtype=float)
    flattened = np.atleast_1d(xin).ravel()
    ax = anchors["sensor_lux"].to_numpy(dtype=float)
    ay = anchors["reference_lux"].to_numpy(dtype=float)
    if len(ax) < 2:
        raise ValueError("Interpolasi memerlukan minimal dua titik sensor unik.")
    result = np.full(flattened.shape, np.nan)
    for i, x in enumerate(flattened):
        if not np.isfinite(x) or x < ax[0] or x > ax[-1]:
            continue
        right = int(np.searchsorted(ax, x, side="left"))
        if right < len(ax) and ax[right] == x:
            result[i] = ay[right]
        else:
            left = right - 1
            x0, x1 = ax[left], ax[right]
            y0, y1 = ay[left], ay[right]
            result[i] = y0 + ((y1 - y0) / (x1 - x0)) * (x - x0)
    return result.reshape(np.atleast_1d(xin).shape)


def interpolation_steps(value: float, anchors: pd.DataFrame) -> dict[str, float] | None:
    """Dua titik yang membatasi nilai input untuk penjelasan manual."""
    x = anchors["sensor_lux"].to_numpy(dtype=float)
    y = anchors["reference_lux"].to_numpy(dtype=float)
    if value < x[0] or value > x[-1]:
        return None
    i = int(np.searchsorted(x, value))
    if i == 0:
        left, right = 0, 1
    elif i == len(x):
        left, right = len(x) - 2, len(x) - 1
    else:
        left, right = i - 1, i
    return {"x0": x[left], "x1": x[right], "y0": y[left], "y1": y[right]}


def error_metrics(actual: Any, predicted: Any) -> dict[str, float]:
    """Residual e=y_referensi-y_prediksi; MAPE hanya y aktual non-nol."""
    y = np.asarray(actual, dtype=float)
    yp = np.asarray(predicted, dtype=float)
    good = np.isfinite(y) & np.isfinite(yp)
    if not good.any():
        return {"MAE": np.nan, "RMSE": np.nan, "MAPE (%)": np.nan, "R²": np.nan}
    y, yp = y[good], yp[good]
    residuals = y - yp
    ss_res = float(np.sum(residuals**2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    nonzero = y != 0
    mape = float(np.mean(np.abs(residuals[nonzero] / y[nonzero])) * 100) if nonzero.any() else np.nan
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else np.nan
    return {
        "MAE": float(np.mean(np.abs(residuals))),
        "RMSE": float(np.sqrt(np.mean(residuals**2))),
        "MAPE (%)": mape,
        "R²": float(r2),
    }


def analyze(data: pd.DataFrame) -> dict[str, Any]:
    cleaned = clean_data(data)
    train, test = split_data(cleaned)
    model = least_squares(train["sensor_lux"], train["reference_lux"])
    anchors = interpolation_anchors(train)

    def make_predictions(frame: pd.DataFrame, group: str) -> pd.DataFrame:
        result = frame.copy()
        x = result["sensor_lux"].to_numpy()
        result["least_squares_lux"] = model.predict(x)
        result["interpolasi_lux"] = linear_interpolation(x, anchors)
        result["residual_raw"] = result["reference_lux"] - result["sensor_lux"]
        result["residual_least_squares"] = result["reference_lux"] - result["least_squares_lux"]
        result["residual_interpolasi"] = result["reference_lux"] - result["interpolasi_lux"]
        result["kelompok"] = group
        return result

    predictions = pd.concat(
        [make_predictions(train, "Kalibrasi"), make_predictions(test, "Pengujian")],
        ignore_index=True,
    ).sort_values("sensor_lux").reset_index(drop=True)

    metric_rows = []
    for name, column in (("Sensor asli", "sensor_lux"), ("Interpolasi linear", "interpolasi_lux"), ("Least squares", "least_squares_lux")):
        test_data = predictions[predictions["kelompok"] == "Pengujian"]
        metric_rows.append({"Metode": name, **error_metrics(test_data["reference_lux"], test_data[column])})

    return {
        "cleaned": cleaned,
        "train": train,
        "test": test,
        "model": model,
        "anchors": anchors,
        "predictions": predictions,
        "metrics": pd.DataFrame(metric_rows),
    }
