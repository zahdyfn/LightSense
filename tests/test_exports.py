"""Pastikan ekspor berisi file Excel/PDF yang valid, bukan CSV satu kolom."""

from __future__ import annotations

import sys
import unittest
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import pandas as pd
from openpyxl import load_workbook

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

from exports import make_excel, make_pdf_zip  # noqa: E402
from numerical import analyze  # noqa: E402
from report import make_pdf  # noqa: E402


class ExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.results = analyze(pd.read_csv(PROJECT_DIR / "data" / "bh1750_public.csv"))

    def test_excel_keeps_columns_and_numeric_types(self) -> None:
        payload = make_excel(
            self.results["predictions"],
            title="LightSense Pengujian",
            source="Universitas Dinamika (2023)",
            metrics=self.results["metrics"],
        )
        self.assertTrue(payload.startswith(b"PK"))
        book = load_workbook(BytesIO(payload), data_only=True)
        self.assertEqual(book.sheetnames, ["Data Kalibrasi", "Ringkasan"])
        table = book["Data Kalibrasi"]
        self.assertEqual(table.max_row, len(self.results["predictions"]) + 1)
        self.assertEqual(table.max_column, 8)
        self.assertEqual(table["A1"].value, "BH1750 (lux)")
        self.assertEqual(table["B1"].value, "Lux Meter (lux)")
        self.assertEqual(table["C1"].value, "Least Squares (lux)")
        self.assertIsInstance(table["A2"].value, (int, float))
        self.assertIsInstance(table["C2"].value, (int, float))
        self.assertEqual(table["C2"].number_format, '#,##0.000;[Red](#,##0.000);"-"')
        self.assertTrue(table["C2"].value > 0)
        self.assertEqual(table.freeze_panes, "C2")
        self.assertEqual(table.auto_filter.ref, f"A1:H{table.max_row}")
        self.assertEqual(book["Ringkasan"]["A16"].value, "Metode")
        self.assertEqual(book["Ringkasan"]["A17"].value, "Sensor asli")

    def test_simple_excel(self) -> None:
        workbook = load_workbook(BytesIO(make_excel(self.results["cleaned"])))
        self.assertEqual(workbook["Data Kalibrasi"].max_column, 2)
        self.assertEqual(workbook["Data Kalibrasi"].max_row, 31)
        self.assertEqual(workbook["Data Kalibrasi"].freeze_panes, "A2")

    def test_pdf_zip_has_valid_document(self) -> None:
        pdf = make_pdf(self.results, "LightSense - Uji Otomatis", "Mahasiswa")
        self.assertTrue(pdf.startswith(b"%PDF-"))
        with ZipFile(BytesIO(make_pdf_zip(pdf))) as archive:
            self.assertEqual(archive.namelist(), ["LightSense_Laporan_Kalibrasi.pdf"])
            self.assertEqual(archive.read("LightSense_Laporan_Kalibrasi.pdf"), pdf)


if __name__ == "__main__":
    unittest.main()
