"""Ekspor laporan kalibrasi LightSense sebagai PDF ringkas."""

from __future__ import annotations

from datetime import datetime
from html import escape
from io import BytesIO
from pathlib import Path

import numpy as np
import reportlab
from reportlab.graphics.shapes import Circle, Drawing, Line, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

DATA_SOURCE = (
    "Universitas Dinamika (2023), Bab IV, Tabel 4.1 Uji Sensor BH1750, "
    "https://repository.dinamika.ac.id/id/eprint/6856/1/19410200003-2023-UNIVERSITASDINAMIKA.pdf"
)

NAVY = colors.HexColor("#10213A")
BLUE = colors.HexColor("#356CF0")
LIGHT_BLUE = colors.HexColor("#EDF4FF")
GRAY = colors.HexColor("#5C6C80")

# Gunakan font TrueType tertanam dari paket ReportLab agar spasi huruf dan
# layout PDF konsisten di berbagai PDF viewer/versi Windows.
_FONT_DIR = Path(reportlab.__file__).resolve().parent / "fonts"
pdfmetrics.registerFont(TTFont("LS-Vera", str(_FONT_DIR / "Vera.ttf")))
pdfmetrics.registerFont(TTFont("LS-Vera-Bold", str(_FONT_DIR / "VeraBd.ttf")))
pdfmetrics.registerFont(TTFont("LS-Vera-Italic", str(_FONT_DIR / "VeraIt.ttf")))
pdfmetrics.registerFont(TTFont("LS-Vera-BoldItalic", str(_FONT_DIR / "VeraBI.ttf")))
pdfmetrics.registerFontFamily("LS-Vera", normal="LS-Vera", bold="LS-Vera-Bold", italic="LS-Vera-Italic", boldItalic="LS-Vera-BoldItalic")


def _pdf_plot(results: dict) -> Drawing:
    """Plot vektor sederhana supaya grafik tetap tajam saat PDF diperbesar."""
    frame = results["predictions"]
    x = frame["sensor_lux"].to_numpy(dtype=float)
    y = frame["reference_lux"].to_numpy(dtype=float)
    z = frame["least_squares_lux"].to_numpy(dtype=float)
    drawing = Drawing(470, 196)
    left, bottom, width, height = 58, 28, 386, 137
    ymax = max(1.0, float(np.max(np.r_[x, y, z]))) * 1.08

    def sx(value):
        return left + float(value) / ymax * width

    def sy(value):
        return bottom + float(value) / ymax * height

    for fraction in (0, 0.25, 0.5, 0.75, 1):
        py = bottom + fraction * height
        drawing.add(Line(left, py, left + width, py, strokeColor=colors.HexColor("#DCE5F0")))
        drawing.add(String(left - 7, py - 3, f"{ymax * fraction:.0f}", textAnchor="end", fontName="LS-Vera", fontSize=8, fillColor=GRAY))
    drawing.add(Line(left, bottom, left + width, bottom, strokeColor=NAVY))
    drawing.add(Line(left, bottom, left, bottom + height, strokeColor=NAVY))
    for xv, yv in zip(x, y):
        drawing.add(Circle(sx(xv), sy(yv), 2.6, fillColor=BLUE, strokeColor=None))
    drawing.add(Line(sx(0), sy(results["model"].b), sx(ymax), sy(results["model"].a * ymax + results["model"].b), strokeColor=colors.HexColor("#EC7C35"), strokeWidth=2))
    drawing.add(String(250, 5, "Sensor BH1750 (lux)", fontName="LS-Vera", fontSize=9, textAnchor="middle", fillColor=NAVY))
    drawing.add(String(left, 183, "Referensi lux meter (lux)", fontName="LS-Vera", fontSize=9, fillColor=NAVY))
    return drawing


def make_pdf(results: dict, project_title: str, student: str, source_detail: str = DATA_SOURCE, is_public: bool = True) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=(21 * cm, 29.7 * cm),
        rightMargin=1.9 * cm, leftMargin=1.9 * cm,
        topMargin=1.75 * cm, bottomMargin=1.8 * cm,
        title="LightSense - Laporan Kalibrasi Sensor Intensitas Cahaya",
        author=student or "LightSense",
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="HeroLS", parent=styles["Title"], fontName="LS-Vera-Bold", fontSize=20, leading=27, textColor=NAVY, alignment=TA_LEFT, spaceAfter=9))
    styles.add(ParagraphStyle(name="SubLS", parent=styles["Normal"], fontName="LS-Vera", fontSize=10.2, leading=15, textColor=GRAY, spaceAfter=13))
    styles.add(ParagraphStyle(name="HeadingLS", parent=styles["Heading2"], fontName="LS-Vera-Bold", fontSize=12, leading=17, textColor=NAVY, spaceBefore=15, spaceAfter=7))
    styles.add(ParagraphStyle(name="BodyLS", parent=styles["BodyText"], fontName="LS-Vera", fontSize=9.2, leading=14, textColor=NAVY, spaceAfter=6))
    styles.add(ParagraphStyle(name="SmallLS", parent=styles["BodyText"], fontName="LS-Vera", fontSize=7.4, leading=10.5, textColor=GRAY, wordWrap="CJK"))

    story = []
    title = escape(project_title.strip() or "LightSense")
    label = escape(student.strip() or "Tidak dicantumkan")
    story.append(Paragraph(title, styles["HeroLS"]))
    story.append(Paragraph("Laporan hasil kalibrasi sensor intensitas cahaya BH1750", styles["SubLS"]))
    story.append(HRFlowable(width="100%", thickness=1.2, color=BLUE))
    story.append(Spacer(1, 11))
    story.append(Paragraph(f"<b>Penyusun:</b> {label}", styles["BodyLS"]))
    story.append(Paragraph(f"<b>Tanggal ekspor:</b> {datetime.now():%d-%m-%Y %H:%M}", styles["BodyLS"]))
    data_kind = "Data sekunder hasil penelitian publik" if is_public else "Data yang diunggah pengguna (asal perlu verifikasi)"
    story.append(Paragraph(f"<b>Jenis data:</b> {data_kind}.", styles["BodyLS"]))

    frame = results["cleaned"]
    model = results["model"]
    metric = results["metrics"]
    story.append(Paragraph("1. Gambaran data", styles["HeadingLS"]))
    story.append(Paragraph(
        f"Sebanyak {len(frame)} pasangan pengukuran dipakai, dengan {len(results['train'])} data untuk "
        f"membangun kurva kalibrasi dan {len(results['test'])} data terpisah untuk pengujian. "
        f"Rentang referensi: {frame['reference_lux'].min():.2f} sampai {frame['reference_lux'].max():.2f} lux. "
        "Variabel input adalah pembacaan BH1750 (lux), sedangkan output adalah estimasi lux terkoreksi.",
        styles["BodyLS"],
    ))
    story.append(Paragraph("2. Perhitungan metode numerik", styles["HeadingLS"]))
    story.append(Paragraph(
        f"<b>Least squares:</b> lux_terkoreksi = ({model.a:.6f} x sensor_lux) + ({model.b:.6f}). "
        "Koefisien dihitung dari jumlah x, y, x kuadrat, dan x*y pada data kalibrasi. "
        "<b>Interpolasi linear:</b> y = y0 + (y1-y0)(x-x0)/(x1-x0), diterapkan pada dua titik kalibrasi terdekat. "
        "Interpolasi tidak digunakan di luar rentang data latih.", styles["BodyLS"],
    ))
    story.append(Paragraph("3. Grafik hasil kalibrasi", styles["HeadingLS"]))
    story.append(_pdf_plot(results))
    story.append(Paragraph("Titik biru: referensi lux meter. Garis oranye: kurva least squares.", styles["SmallLS"]))
    table_data = [["Metode", "MAE (lux)", "RMSE (lux)", "MAPE (%)", "R2"]]
    for row in metric.to_dict("records"):
        table_data.append([row["Metode"], f"{row['MAE']:.3f}", f"{row['RMSE']:.3f}", f"{row['MAPE (%)']:.3f}", f"{row['R²']:.4f}"])
    table = Table(table_data, colWidths=[142, 75, 77, 77, 59], repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BLUE]),
        ("FONTNAME", (0, 0), (-1, -1), "LS-Vera"),
        ("FONTNAME", (0, 0), (-1, 0), "LS-Vera-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8), ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
    ]))
    story.append(KeepTogether([
        Paragraph("4. Evaluasi pada data pengujian", styles["HeadingLS"]),
        table,
        Spacer(1, 9),
        Paragraph("MAE dan RMSE dalam lux. MAPE menggunakan nilai referensi tidak nol. Residual didefinisikan sebagai referensi dikurangi prediksi.", styles["SmallLS"]),
    ]))

    story.append(Paragraph("5. Interpretasi engineering", styles["HeadingLS"]))
    best = metric.loc[metric["RMSE"].idxmin(), "Metode"]
    story.append(Paragraph(
        f"Berdasarkan RMSE pada subset pengujian, metode dengan error terkecil adalah <b>{escape(best)}</b>. "
        "Kesimpulan ini hanya berlaku untuk data dan rentang pengukuran yang diamati. "
        "Data sekunder tidak menggantikan verifikasi perangkat fisik; setiap sensor dan kondisi pencahayaan "
        "dapat menghasilkan karakteristik yang berbeda.", styles["BodyLS"],
    ))
    story.append(Paragraph("6. Sumber data dan batasan", styles["HeadingLS"]))
    story.append(Paragraph(escape(source_detail), styles["SmallLS"]))
    limitation = (
        "Data tabel dialihformat dari sumber publik. Tidak ada percobaan langsung yang dilakukan oleh pembuat aplikasi."
        if is_public else "Sumber dan kondisi pengukuran data unggahan belum diverifikasi oleh aplikasi."
    )
    story.append(Paragraph(limitation + " Hasil merupakan analisis numerik, bukan sertifikasi kalibrasi alat.", styles["SmallLS"]))

    story.append(Paragraph("Lampiran - Pasangan data dan hasil prediksi", styles["HeadingLS"]))
    p = results["predictions"].sort_values("sensor_lux")
    rows = [["BH1750", "Referensi", "Interpolasi", "Least squares", "Subset"]]
    for _, row in p.iterrows():
        rows.append([
            f"{row['sensor_lux']:.2f}", f"{row['reference_lux']:.2f}",
            f"{row['interpolasi_lux']:.2f}", f"{row['least_squares_lux']:.2f}", row["kelompok"],
        ])
    appendix = Table(rows, colWidths=[68, 75, 85, 90, 112], repeatRows=1, hAlign="LEFT")
    appendix.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BLUE]),
        ("FONTNAME", (0, 0), (-1, -1), "LS-Vera"),
        ("FONTNAME", (0, 0), (-1, 0), "LS-Vera-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(appendix)

    def footer(canvas, page_doc):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#DCE5F0"))
        canvas.line(1.9 * cm, 1.4 * cm, 19.1 * cm, 1.4 * cm)
        canvas.setFont("LS-Vera", 8)
        canvas.setFillColor(GRAY)
        canvas.drawString(1.9 * cm, 1.04 * cm, "LightSense | Metode Numerik")
        canvas.drawRightString(19.1 * cm, 1.04 * cm, f"Halaman {page_doc.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()
