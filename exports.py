"""Ekspor hasil kalibrasi ke workbook Excel dan ZIP laporan PDF."""

from __future__ import annotations

from io import BytesIO
from math import isfinite
from zipfile import ZIP_DEFLATED, ZipFile

import numpy as np
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter


NAVY = "10213A"
BLUE = "4268E8"
WHITE = "FFFFFF"
PALE = "F1F5FC"
MUTED = "52647D"

COLUMN_NAMES = {
    "sensor_lux": "BH1750 (lux)",
    "reference_lux": "Lux Meter (lux)",
    "least_squares_lux": "Least Squares (lux)",
    "interpolasi_lux": "Interpolasi (lux)",
    "residual_raw": "Residual Awal (lux)",
    "residual_least_squares": "Residual LS (lux)",
    "residual_interpolasi": "Residual Interpolasi (lux)",
    "kelompok": "Kelompok Data",
}


def _cell_value(value: object) -> object:
    """Simpan pengukuran sebagai angka Excel asli; NaN sebagai sel kosong."""
    if pd.isna(value):
        return None
    if isinstance(value, (int, float, np.integer, np.floating)):
        number = float(value)
        return number if isfinite(number) else None
    return str(value)


def make_excel(
    frame: pd.DataFrame,
    *,
    title: str = "Hasil Kalibrasi LightSense",
    source: str = "Dataset aktif pada aplikasi LightSense",
    metrics: pd.DataFrame | None = None,
) -> bytes:
    """Workbook dua sheet, kolom terpisah dan angka dibulatkan secara tampilan.

    Nilai penuh tetap tersimpan agar perhitungan lanjutan tidak kehilangan presisi.
    """
    book = Workbook()
    data_sheet = book.active
    data_sheet.title = "Data Kalibrasi"
    cols = list(frame.columns)
    data_sheet.append([COLUMN_NAMES.get(col, col.replace("_", " ").title()) for col in cols])
    header_fill = PatternFill("solid", fgColor=NAVY)
    alternate_fill = PatternFill("solid", fgColor=PALE)
    bottom = Border(bottom=Side(style="hair", color="DFE7F2"))

    for col_idx, label in enumerate(data_sheet[1], start=1):
        label.fill = header_fill
        label.font = Font(name="Aptos", size=11, bold=True, color=WHITE)
        label.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        data_sheet.column_dimensions[get_column_letter(col_idx)].width = min(30, max(20, len(str(label.value)) + 4))
    data_sheet.row_dimensions[1].height = 35

    for row_idx, values in enumerate(frame.itertuples(index=False, name=None), start=2):
        for col_idx, raw in enumerate(values, start=1):
            cell = data_sheet.cell(row_idx, col_idx, _cell_value(raw))
            cell.font = Font(name="Aptos", size=10, color=NAVY)
            cell.border = bottom
            cell.alignment = Alignment(vertical="center", horizontal="left" if isinstance(cell.value, str) else "right")
            if isinstance(cell.value, (int, float)):
                cell.number_format = '#,##0.000;[Red](#,##0.000);"-"'
            if row_idx % 2 == 0:
                cell.fill = alternate_fill
            if cols[col_idx - 1] == "kelompok" and cell.value == "Pengujian":
                cell.font = Font(name="Aptos", size=10, bold=True, color=BLUE)
        data_sheet.row_dimensions[row_idx].height = 21

    data_sheet.freeze_panes = "C2" if len(cols) > 2 else "A2"
    data_sheet.auto_filter.ref = data_sheet.dimensions
    data_sheet.sheet_view.showGridLines = False
    data_sheet.sheet_properties.pageSetUpPr.fitToPage = True
    data_sheet.page_setup.fitToWidth = 1
    data_sheet.print_title_rows = "1:1"

    info_sheet = book.create_sheet("Ringkasan")
    info_sheet.column_dimensions["A"].width = 30
    info_sheet.column_dimensions["B"].width = 24
    info_sheet.column_dimensions["C"].width = 23
    info_sheet.column_dimensions["D"].width = 24
    info_sheet.column_dimensions["E"].width = 18
    info_sheet.merge_cells("A1:E2")
    hero = info_sheet["A1"]
    hero.value = title
    hero.fill = header_fill
    hero.font = Font(name="Aptos Display", size=17, bold=True, color=WHITE)
    hero.alignment = Alignment(vertical="center", indent=1)
    info_sheet.row_dimensions[1].height = 27
    info_sheet.row_dimensions[2].height = 18
    info_sheet["A4"] = "Jumlah pasangan data"
    info_sheet["B4"] = len(frame)
    info_sheet["A5"] = "Satuan pengukuran"
    info_sheet["B5"] = "lux (lx)"
    info_sheet["A6"] = "Input model"
    info_sheet["B6"] = "BH1750"
    info_sheet["A7"] = "Target kalibrasi"
    info_sheet["B7"] = "Lux meter referensi"
    info_sheet["A9"] = "SUMBER DATA"
    info_sheet["A9"].font = Font(name="Aptos", bold=True, color=BLUE, size=11)
    info_sheet.merge_cells("A10:E12")
    info_sheet["A10"] = source
    info_sheet["A10"].alignment = Alignment(wrap_text=True, vertical="top")
    info_sheet["A10"].font = Font(name="Aptos", color=MUTED, size=10)
    for row in range(4, 8):
        info_sheet[f"A{row}"].font = Font(name="Aptos", color=MUTED, size=10)
        info_sheet[f"B{row}"].font = Font(name="Aptos", color=NAVY, bold=True, size=10)

    if metrics is not None and not metrics.empty:
        start = 15
        info_sheet.cell(start, 1, "EVALUASI PADA DATA PENGUJIAN")
        info_sheet.cell(start, 1).font = Font(name="Aptos", bold=True, color=BLUE, size=11)
        heads = ["Metode", "MAE (lux)", "RMSE (lux)", "MAPE (%)", "R²"]
        for col_idx, label in enumerate(heads, start=1):
            cell = info_sheet.cell(start + 1, col_idx, label)
            cell.fill = header_fill
            cell.font = Font(name="Aptos", color=WHITE, bold=True)
        for row_idx, record in enumerate(metrics.to_dict("records"), start=start + 2):
            for col_idx, key in enumerate(("Metode", "MAE", "RMSE", "MAPE (%)", "R²"), start=1):
                cell = info_sheet.cell(row_idx, col_idx, _cell_value(record[key]))
                cell.font = Font(name="Aptos", color=NAVY)
                if isinstance(cell.value, (int, float)):
                    cell.number_format = "0.0000"
                if row_idx % 2 == 0:
                    cell.fill = alternate_fill
        info_sheet.cell(start + 6, 1, "Residual = referensi - hasil prediksi; nilai kosong berarti tidak tersedia.")
        info_sheet.cell(start + 6, 1).font = Font(name="Aptos", color=MUTED, italic=True, size=10)

    info_sheet.sheet_view.showGridLines = False
    book.active = 0
    buffer = BytesIO()
    book.save(buffer)
    return buffer.getvalue()


def make_pdf_zip(pdf_bytes: bytes) -> bytes:
    """Alternatif download ketika ekstensi browser mencegat tautan PDF."""
    buffer = BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("LightSense_Laporan_Kalibrasi.pdf", pdf_bytes)
    return buffer.getvalue()
