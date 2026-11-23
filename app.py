"""LightSense - Dashboard Metode Numerik Kalibrasi Intensitas Cahaya.

Jalankan: python -m streamlit run app.py
"""

from __future__ import annotations

from html import escape
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from exports import make_excel, make_pdf_zip
from numerical import (
    analyze,
    clean_data,
    interpolation_steps,
    linear_interpolation,
)
from report import DATA_SOURCE, make_pdf


ROOT = Path(__file__).resolve().parent
DATA_FILE = ROOT / "data" / "bh1750_public.csv"
BLUE = "#4268E8"
CYAN = "#15B8A6"
AMBER = "#F49A4F"
MUTED = "#A3B4CA"

st.set_page_config(
    page_title="LightSense | Kalibrasi Intensitas Cahaya",
    page_icon="💡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      :root { --ls-ink: #172947; --ls-muted: #697B99; --ls-blue: #4268E8; --ls-teal: #10A89A; }
      html, body, [data-testid="stApp"] { font-family: Inter, "Segoe UI", Arial, sans-serif; }
      [data-testid="stAppViewContainer"] { background: radial-gradient(ellipse at 95% -10%, #E9EFFF 0%, transparent 34%), #F6F8FD; }
      .block-container { padding-top: 1.7rem; padding-bottom: 3.2rem; max-width: 1440px; padding-left: 2.7rem; padding-right: 2.7rem; }
      h1,h2,h3 { font-family: Inter, "Segoe UI", Arial, sans-serif; letter-spacing: -.038em; color: #172947; }
      h1 { font-size: clamp(2rem, 2.8vw, 2.75rem) !important; font-weight: 790 !important; }
      h2 { font-size: 1.42rem !important; font-weight: 750 !important; }
      h3 { font-size: 1.12rem !important; font-weight: 720 !important; }
      p, li, label { line-height: 1.55; }
      [data-testid="stSidebar"] { background: linear-gradient(170deg, #101F39 0%, #15294A 65%, #0F1D35 100%) !important; border-right: none; }
      [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
      [data-testid="stSidebar"] [data-testid="stCaptionContainer"] { color: #C0CCE0 !important; }
      [data-testid="stSidebar"] [data-testid="stRadio"] label { color: #E9F0FF !important; }
      [data-testid="stSidebar"] [data-testid="stRadio"] label p { color: #E9F0FF !important; font-weight: 590; }
      [data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] { gap: 5px; }
      [data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] > label {padding: .64rem .73rem; border-radius: 11px; transition: background .15s ease;}
      [data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] > label:hover {background: rgba(255,255,255,.08);}
      [data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] > label:has(input:checked) { background: linear-gradient(105deg, rgba(73,115,246,.38), rgba(41,115,212,.14)); border: 1px solid rgba(131,169,255,.28); }
      [data-testid="stSidebar"] hr { border-color: rgba(201,218,247,.13); }
      [data-testid="stSidebar"] [data-testid="stAlert"] { background: rgba(255,255,255,.065); border: 1px solid rgba(255,255,255,.1); }
      .ls-brand {display: flex; align-items:center; gap:12px; margin:9px 0 20px;}
      .ls-brand-mark {width:45px;height:45px;border-radius:14px;background:linear-gradient(135deg,#7595FF,#4166E8);box-shadow:0 8px 24px #193F92;color:white;display:flex;align-items:center;justify-content:center;font-size:26px;font-weight:800;}
      .ls-brand-name {font-size:1.48rem;color:#FFF;font-weight:810;letter-spacing:-.06em;line-height:1.05;}
      .ls-brand-sub {font-size:.59rem;letter-spacing:.19em;color:#9DAFCB;margin-top:5px;font-weight:800;}
      .ls-side-label {color:#8299BA;font-size:.68rem;font-weight:800;letter-spacing:.17em;margin:20px 0 12px;}
      .ls-side-card {border:1px solid rgba(181,203,244,.15);padding:16px;border-radius:14px;background:rgba(255,255,255,.055);}
      .ls-side-chip {display:inline-flex;align-items:center;gap:6px;color:#8DE2CA;font-size:.67rem;font-weight:800;letter-spacing:.04em;}
      .ls-side-chip:before {content:"";display:inline-block;width:7px;height:7px;background:#51D6AC;border-radius:50%;box-shadow:0 0 0 4px rgba(81,214,172,.14);}
      .ls-side-name {color:#EEF4FF;font-size:.84rem;font-weight:700;line-height:1.45;margin:10px 0 5px;}
      .ls-side-meta {color:#9BAECB;font-size:.73rem;}
      .ls-eyebrow {font-size:.73rem;text-transform:uppercase;color:#4268E8;font-weight:800;letter-spacing:.16em;margin-bottom:10px;}
      .ls-subtitle {color:#6B7D99;line-height:1.7;margin-top:-.35rem;max-width:770px;font-size:.97rem;}
      .ls-page-heading {margin: 4px 0 24px;}
      .ls-page-heading h1 {margin:0 0 9px;}
      .ls-panel {padding:21px 23px;border-radius:17px;background:#FFFFFF;border:1px solid #E5EAF5;box-shadow:0 10px 28px rgba(25,51,95,.035);}
      .ls-small {font-size:.84rem;color:#7484A0;line-height:1.6;}
      .ls-info {padding:17px 21px;background:#EFF5FF;border:1px solid #DBE7FF;border-radius:13px;color:#31517C;font-size:.91rem;line-height:1.6;}
      .ls-hero {position:relative;display:flex;min-height:257px;align-items:center;justify-content:space-between;overflow:hidden;border-radius:23px;padding:33px 43px;background:linear-gradient(116deg,#142744 6%,#1A3D7E 60%,#335FE1 115%);box-shadow:0 22px 48px rgba(27,58,122,.18);margin:2px 0 23px;color:#FFFFFF;}
      .ls-hero:before {content:"";position:absolute;width:420px;height:420px;right:-125px;top:-125px;border-radius:50%;border:1px solid rgba(255,255,255,.15);box-shadow:0 0 0 46px rgba(255,255,255,.035),0 0 0 100px rgba(255,255,255,.028);}
      .ls-hero-content {position:relative;z-index:2;max-width:660px;}
      .ls-hero-kicker {color:#B9CEFF;font-size:.68rem;font-weight:800;letter-spacing:.19em;margin-bottom:18px;}
      .ls-hero h1 {color:#FFF !important;line-height:1.17;font-size:2.3rem !important;font-weight:780;max-width:660px;margin:0 0 13px;}
      .ls-hero h1 em {font-style:normal;color:#88E5DF;}
      .ls-hero p {color:#D7E4FF;font-size:.95rem;line-height:1.7;max-width:530px;margin:0 0 20px;}
      .ls-hero-tags {display:flex;gap:9px;flex-wrap:wrap;}
      .ls-hero-tags span {border:1px solid rgba(232,243,255,.26);padding:6px 11px;border-radius:25px;color:#DCEAFF;font-size:.67rem;font-weight:800;letter-spacing:.07em;background:rgba(255,255,255,.06);}
      .ls-hero-gauge {width:205px;height:205px;flex:0 0 205px;border-radius:50%;border:1px solid rgba(224,240,255,.22);display:flex;align-items:center;justify-content:center;background:radial-gradient(circle,rgba(55,98,195,.65) 0%,rgba(255,255,255,.015) 70%);position:relative;z-index:2;}
      .ls-hero-gauge:before {content:"";position:absolute;width:157px;height:157px;border-radius:50%;border:12px solid rgba(255,255,255,.11);border-top-color:#8CE6DC;border-right-color:#72A8FF;transform:rotate(-31deg);}
      .ls-gauge-inner {position:relative;text-align:center;z-index:3;}
      .ls-gauge-label {font-size:.62rem;letter-spacing:.17em;color:#B9CFF6;font-weight:800;}
      .ls-gauge-value {font-size:2.6rem;color:#FFF;letter-spacing:-.06em;font-weight:800;line-height:1.25;}
      .ls-gauge-value span {font-size:.88rem;color:#C7DCF7;letter-spacing:0;}
      .ls-gauge-foot {font-size:.61rem;color:#AFC7EC;letter-spacing:.04em;}
      .ls-stat {min-height:155px;padding:20px 21px 17px;background:#FFFFFF;border:1px solid #E5EAF4;border-radius:17px;box-shadow:0 9px 29px rgba(19,45,90,.045);position:relative;overflow:hidden;}
      .ls-stat:before {content:"";height:3px;width:48px;background:var(--stat-color);border-radius:4px;position:absolute;top:0;left:21px;}
      .ls-stat-label {font-size:.68rem;letter-spacing:.115em;color:#8190A8;font-weight:800;text-transform:uppercase;}
      .ls-stat-value {font-size:2rem;line-height:1.1;margin:19px 0 6px;color:#18304E;font-weight:790;letter-spacing:-.06em;}
      .ls-stat-value span {font-size:.9rem;color:#7D8EA8;font-weight:600;letter-spacing:0;}
      .ls-stat-note {font-size:.78rem;color:#8190A8;}
      .ls-insight {background:#F0F5FF;border:1px solid #DEE9FF;border-radius:15px;padding:19px 22px;}
      .ls-insight-label {font-size:.72rem;text-transform:uppercase;letter-spacing:.12em;color:#617DA9;font-weight:800;}
      .ls-insight-value {font-size:1.58rem;font-weight:800;color:#23447A;letter-spacing:-.04em;margin:5px 0;}
      .ls-insight p {margin:0;color:#6B7F9F;font-size:.81rem;}
      .ls-progress {margin:16px 0;}
      .ls-progress-title {display:flex;justify-content:space-between;color:#36506E;font-weight:650;font-size:.82rem;margin-bottom:8px;}
      .ls-progress-title strong {font-size:.8rem;color:#4B6386;}
      .ls-track {height:9px;background:#E8EDF7;border-radius:12px;overflow:hidden;}
      .ls-fill {height:100%;border-radius:12px;background:var(--bar-color);}
      .ls-sectionline {margin:12px 0 14px;display:flex;align-items:center;justify-content:space-between;gap:12px;}
      .ls-sectionline h3 {font-size:1.12rem;margin:0;font-weight:770;color:#1B3050;}
      .ls-tag {font-size:.67rem;padding:6px 10px;border:1px solid #DCE5F4;background:#F4F7FC;color:#6A7E9D;border-radius:30px;font-weight:800;letter-spacing:.065em;white-space:nowrap;}
      [data-testid="stVerticalBlockBorderWrapper"] {border-color:#E2E8F3 !important;border-radius:18px !important;background:#FFF;box-shadow:0 8px 22px rgba(27,54,99,.035);}
      [data-testid="stMetric"] {background:#FFFFFF;border:1px solid #E4EBF6;padding:17px 20px;border-radius:14px;}
      [data-testid="stMetricLabel"] {color:#7284A1;}
      [data-testid="stMetricValue"] {color:#22385C;}
      [data-testid="stTabs"] button {font-weight:700;}
      [data-testid="stDataFrame"], [data-testid="stDataEditor"] {border:1px solid #E3EAF5;border-radius:11px;overflow:hidden;}
      [data-testid="stAlert"] {border-radius:12px;}
      div.stButton>button[kind="primary"], div.stDownloadButton>button[kind="primary"] {background:#4268E8;border-color:#4268E8;box-shadow:0 7px 16px rgba(66,104,232,.20);border-radius:10px;font-weight:700;}
      div.stButton>button, div.stDownloadButton>button {border-radius:10px;font-weight:650;}
      .ls-footer {color:#93A1B6;font-size:.73rem;letter-spacing:.035em;margin-top:13px;text-align:center;}
      a {color:#315CD2 !important;}
      @media (max-width: 1050px) {.ls-hero-gauge {display:none}.ls-hero{padding:28px}.block-container{padding-left:1.4rem;padding-right:1.4rem}}
      @media (max-width: 650px) {.ls-hero h1{font-size:1.7rem !important}.ls-hero{min-height:0}.ls-stat{min-height:130px}.ls-stat-value{font-size:1.6rem}}
    </style>
    """,
    unsafe_allow_html=True,
)


def source_description() -> str:
    return st.session_state.get("dataset_source", DATA_SOURCE)


def init_state() -> None:
    if "current_data" not in st.session_state:
        st.session_state.current_data = pd.read_csv(DATA_FILE)
        st.session_state.dataset_name = "Dataset publik BH1750 - Universitas Dinamika"
        st.session_state.dataset_source = DATA_SOURCE
        st.session_state.editor_revision = 0


def df_download(frame: pd.DataFrame) -> bytes:
    # Titik koma lebih kompatibel dengan pengaturan regional Excel Indonesia.
    # Untuk tipe angka yang terjamin dan format siap pakai, pilih XLSX.
    return frame.to_csv(index=False, sep=";", float_format="%.3f").encode("utf-8-sig")


def section(eyebrow: str, heading: str, description: str) -> None:
    st.markdown(
        f'<div class="ls-page-heading"><div class="ls-eyebrow">{escape(eyebrow)}</div>'
        f'<h1>{escape(heading)}</h1><div class="ls-subtitle">{escape(description)}</div></div>',
        unsafe_allow_html=True,
    )


def sectionline(title: str, badge: str = "") -> None:
    badge_html = f'<span class="ls-tag">{escape(badge)}</span>' if badge else ""
    st.markdown(f'<div class="ls-sectionline"><h3>{escape(title)}</h3>{badge_html}</div>', unsafe_allow_html=True)


def stat(label: str, value: str, note: str, color: str = BLUE) -> None:
    st.markdown(
        f'<div class="ls-stat" style="--stat-color:{color}">'
        f'<div class="ls-stat-label">{escape(label)}</div>'
        f'<div class="ls-stat-value">{value}</div>'
        f'<div class="ls-stat-note">{escape(note)}</div></div>',
        unsafe_allow_html=True,
    )


def metric_progress(name: str, value: float, max_value: float, color: str) -> None:
    width = 100 * value / max(max_value, 1e-9)
    st.markdown(
        f'<div class="ls-progress"><div class="ls-progress-title">'
        f'<span>{escape(name)}</span><strong>{value:.2f} lx</strong></div>'
        f'<div class="ls-track"><div class="ls-fill" style="width:{width:.1f}%;--bar-color:{color}"></div></div></div>',
        unsafe_allow_html=True,
    )


def chart_layout(figure: go.Figure, height: int = 390) -> go.Figure:
    figure.update_layout(
        height=height,
        margin=dict(l=12, r=14, t=53, b=18),
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        font=dict(family="Inter, Segoe UI, Arial", color="#61738F", size=12),
        legend=dict(orientation="h", yanchor="bottom", y=1.11, xanchor="left", x=0,
                    font=dict(size=11, color="#5E708D")),
        hovermode="closest",
        xaxis=dict(gridcolor="#EFF2F8", zerolinecolor="#EFF2F8", showline=False,
                   tickfont=dict(color="#8390A6"), title_font=dict(color="#687C98", size=12)),
        yaxis=dict(gridcolor="#EFF2F8", zerolinecolor="#EFF2F8", showline=False,
                   tickfont=dict(color="#8390A6"), title_font=dict(color="#687C98", size=12)),
        hoverlabel=dict(bgcolor="#1A2E4D", font=dict(color="#FFFFFF")),
    )
    return figure


def plot_calibration(result: dict, with_raw: bool = True) -> go.Figure:
    pred = result["predictions"]
    model = result["model"]
    xspan = np.linspace(float(pred["sensor_lux"].min()), float(pred["sensor_lux"].max()), 180)
    fig = go.Figure()
    if with_raw:
        fig.add_trace(go.Scatter(
            x=xspan, y=xspan, mode="lines", name="Sensor asli",
            line=dict(color=MUTED, dash="dash", width=2),
        ))
    fig.add_trace(go.Scatter(
        x=pred["sensor_lux"], y=pred["reference_lux"], mode="markers",
        name="Lux meter", marker=dict(size=9, color=CYAN, opacity=.9, line=dict(width=1.5, color="#FFFFFF")),
        customdata=pred["kelompok"], hovertemplate="Sensor: %{x:.2f} lux<br>Referensi: %{y:.2f} lux<br>Subset: %{customdata}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=xspan, y=model.predict(xspan), mode="lines", name="Least squares",
        line=dict(color=AMBER, width=3),
    ))
    fig.add_trace(go.Scatter(
        x=xspan, y=linear_interpolation(xspan, result["anchors"]), mode="lines",
        name="Interpolasi linear", line=dict(color=BLUE, width=2),
    ))
    fig.update_xaxes(title="Pembacaan BH1750 (lux)")
    fig.update_yaxes(title="Intensitas cahaya (lux)")
    return chart_layout(fig)


def plot_residuals(result: dict) -> go.Figure:
    test = result["predictions"].query("kelompok == 'Pengujian'")
    fig = go.Figure()
    for name, column, color in [
        ("Sensor asli", "residual_raw", MUTED),
        ("Interpolasi", "residual_interpolasi", BLUE),
        ("Least squares", "residual_least_squares", AMBER),
    ]:
        fig.add_trace(go.Bar(x=test["sensor_lux"].round(2).astype(str), y=test[column], name=name, marker_color=color))
    fig.update_layout(barmode="group")
    fig.update_xaxes(title="Pembacaan sensor pada data uji (lux)")
    fig.update_yaxes(title="Residual = referensi - prediksi (lux)")
    return chart_layout(fig, 370)


def show_metrics(result: dict) -> None:
    frame = result["metrics"]
    base = frame.iloc[0]
    winner = frame.iloc[int(frame["RMSE"].argmin())]
    columns = st.columns(4, gap="medium")
    with columns[0]:
        stat("Total Pengukuran", str(len(result["cleaned"])), "Pasangan sensor dan referensi", BLUE)
    with columns[1]:
        stat("Data Kalibrasi", str(len(result["train"])), f"{len(result['test'])} titik uji terpisah", CYAN)
    with columns[2]:
        stat("MAE Sensor Asli", f"{base['MAE']:.2f} <span>lx</span>", "Sebelum proses koreksi", AMBER)
    with columns[3]:
        stat("RMSE Terendah", f"{winner['RMSE']:.2f} <span>lx</span>", f"Model: {winner['Metode']}", BLUE)


def navigation() -> str:
    with st.sidebar:
        st.markdown(
            '<div class="ls-brand"><div class="ls-brand-mark">L</div><div>'
            '<div class="ls-brand-name">LightSense</div>'
            '<div class="ls-brand-sub">SENSOR ANALYTICS</div></div></div>',
            unsafe_allow_html=True,
        )
        st.markdown('<div class="ls-side-label">WORKSPACE</div>', unsafe_allow_html=True)
        pages = [
            "Overview", "Data Management", "Numerical Computation", "Visualization",
            "Evaluation", "Engineering Interpretation", "Report",
        ]
        page = st.radio("Navigasi", pages, label_visibility="collapsed")
        st.divider()
        st.markdown('<div class="ls-side-label">DATASET AKTIF</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="ls-side-card"><div class="ls-side-chip">DATA READY</div>'
            f'<div class="ls-side-name">{escape(st.session_state.dataset_name)}</div>'
            f'<div class="ls-side-meta">{len(st.session_state.current_data)} pengukuran · BH1750</div></div>',
            unsafe_allow_html=True,
        )
        st.markdown('<div class="ls-side-label">PENS · METODE NUMERIK</div>', unsafe_allow_html=True)
        st.caption("Data sekunder · tidak terhubung dengan sensor fisik")
    return page


def page_overview(result: dict) -> None:
    ref_min = float(result["cleaned"]["reference_lux"].min())
    ref_max = float(result["cleaned"]["reference_lux"].max())
    st.markdown(
        '<div class="ls-hero"><div class="ls-hero-content">'
        '<div class="ls-hero-kicker">LIGHTSENSE / INSTRUMENTATION ANALYTICS</div>'
        '<h1>Measure the light.<br><em>Improve the accuracy.</em></h1>'
        '<p>Dashboard kalibrasi sensor intensitas cahaya BH1750 dengan '
        'interpolasi linear, least squares, dan evaluasi terhadap lux meter referensi.</p>'
        '<div class="ls-hero-tags"><span>BH1750</span><span>LUX METER</span>'
        '<span>2 NUMERICAL METHODS</span></div></div>'
        '<div class="ls-hero-gauge"><div class="ls-gauge-inner"><div class="ls-gauge-label">MAX REFERENCE</div>'
        f'<div class="ls-gauge-value">{ref_max:.0f}<span> lx</span></div>'
        f'<div class="ls-gauge-foot">FROM {ref_min:.0f} LUX</div></div></div></div>',
        unsafe_allow_html=True,
    )
    show_metrics(result)
    st.markdown('<div style="height:17px"></div>', unsafe_allow_html=True)
    left, right = st.columns([1.63, 1], gap="medium")
    with left:
        with st.container(border=True):
            sectionline("Kurva Kalibrasi", "SENSOR VS REFERENSI")
            st.plotly_chart(plot_calibration(result), width="stretch", config={"displayModeBar": False})
    with right:
        metric = result["metrics"]
        best = metric.iloc[int(metric["RMSE"].argmin())]
        before = float(metric.iloc[0]["MAE"])
        improvement = (before - float(best["MAE"])) / before * 100 if before else 0
        st.markdown(
            '<div class="ls-insight"><div class="ls-insight-label">BEST PERFORMING METHOD</div>'
            f'<div class="ls-insight-value">{escape(str(best["Metode"]))}</div>'
            f'<p>MAE berkurang {improvement:.1f}% dibanding hasil sensor awal.</p></div>',
            unsafe_allow_html=True,
        )
        st.markdown('<div style="height:15px"></div>', unsafe_allow_html=True)
        with st.container(border=True):
            sectionline("Error Comparison", "RMSE / LUX")
            max_rmse = float(metric["RMSE"].max())
            for position, color in enumerate((MUTED, BLUE, CYAN)):
                row = metric.iloc[position]
                metric_progress(str(row["Metode"]), float(row["RMSE"]), max_rmse, color)
            st.caption("Nilai RMSE lebih rendah menunjukkan error prediksi lebih kecil pada data uji.")
    st.markdown('<div style="height:10px"></div>', unsafe_allow_html=True)
    st.markdown('<div class="ls-info"><b>Catatan validasi.</b> Semua nilai error diperoleh dari data pengujian yang dipisah dari data kalibrasi. Ini merupakan analisis numerik data penelitian publik, bukan kalibrasi perangkat secara langsung.</div>', unsafe_allow_html=True)


def page_data_management(result: dict) -> None:
    section("Dataset / Data Management", "Kelola data pengukuran", "Impor, periksa, dan koreksi pasangan sensor dengan lux meter. Semua data disimpan selama sesi aplikasi berjalan.")
    k1, k2, k3 = st.columns(3)
    with k1:
        stat("Data Tersedia", str(len(result["cleaned"])), "Pasangan data valid", BLUE)
    with k2:
        stat("Rentang Sensor", f"{result['cleaned']['sensor_lux'].max():.0f} <span>lx</span>", "Nilai maksimum BH1750", CYAN)
    with k3:
        stat("Variabel", "02", "sensor_lux + reference_lux", AMBER)
    st.markdown('<div style="height:20px"></div>', unsafe_allow_html=True)
    col1, col2 = st.columns([1.55, 1], gap="large")
    with col1:
        sectionline("Tabel Dataset Aktif", "EDITABLE DATA")
        st.caption(f"{st.session_state.dataset_name} · Ubah nilai langsung pada tabel, lalu simpan.")
        edited = st.data_editor(
            st.session_state.current_data,
            num_rows="dynamic", hide_index=True, width="stretch",
            column_config={
                "sensor_lux": st.column_config.NumberColumn("BH1750 (lux)", min_value=0, format="%.2f"),
                "reference_lux": st.column_config.NumberColumn("Lux meter (lux)", min_value=0, format="%.2f"),
            },
            key=f"data_editor_{st.session_state.editor_revision}",
        )
        b1, b2 = st.columns(2)
        with b1:
            if st.button("Simpan perubahan", type="primary", width="stretch"):
                try:
                    st.session_state.current_data = clean_data(edited)
                    st.session_state.editor_revision += 1
                    st.success("Perubahan diterapkan pada sesi ini.")
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))
        with b2:
            st.download_button(
                "Unduh Excel rapi (.xlsx)",
                make_excel(result["cleaned"], title="Dataset Aktif LightSense", source=source_description()),
                file_name="LightSense_Dataset_Aktif.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                width="stretch",
            )
        with st.expander("Perlu format CSV untuk aplikasi lain?"):
            st.download_button("Unduh CSV (pemisah ;)", df_download(result["cleaned"]), file_name="LightSense_Dataset_Aktif.csv", mime="text/csv")
            st.caption("Di Excel dengan setelan Indonesia, CSV berkoma sering masuk ke satu kolom. Pakai Excel (.xlsx) agar kolom langsung rapi.")

        st.write("")
        if st.button("Kembalikan dataset publik", width="stretch"):
            st.session_state.current_data = pd.read_csv(DATA_FILE)
            st.session_state.dataset_name = "Dataset publik BH1750 - Universitas Dinamika"
            st.session_state.dataset_source = DATA_SOURCE
            st.session_state.editor_revision += 1
            st.rerun()

    with col2:
        sectionline("Impor Dataset Baru", "CSV / EXCEL")
        uploaded = st.file_uploader("Unggah CSV atau Excel (.xlsx)", type=["csv", "xlsx"])
        if uploaded is not None:
            try:
                frame = pd.read_excel(uploaded) if uploaded.name.lower().endswith(".xlsx") else pd.read_csv(uploaded)
                options = list(frame.columns)
                if len(options) < 2:
                    st.error("File wajib punya sedikitnya dua kolom numerik.")
                else:
                    sensor_choice = st.selectbox("Kolom hasil sensor", options, index=options.index("sensor_lux") if "sensor_lux" in options else 0)
                    ref_choice = st.selectbox("Kolom lux meter referensi", options, index=options.index("reference_lux") if "reference_lux" in options else 1)
                    if st.button("Gunakan file ini", type="primary"):
                        if sensor_choice == ref_choice:
                            st.error("Kolom sensor dan referensi harus berbeda.")
                        else:
                            clean = clean_data(frame[[sensor_choice, ref_choice]].rename(columns={sensor_choice: "sensor_lux", ref_choice: "reference_lux"}))
                            st.session_state.current_data = clean
                            st.session_state.dataset_name = uploaded.name
                            st.session_state.dataset_source = f"File diunggah pengguna: {uploaded.name}. Sumber dan prosedur pengukuran harus diverifikasi."
                            st.session_state.editor_revision += 1
                            st.rerun()
            except (ValueError, ImportError, UnicodeDecodeError) as exc:
                st.error(f"File tidak dapat diproses: {exc}")
        st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)
        sectionline("Format Kolom", "DATA SCHEMA")
        st.code("sensor_lux,reference_lux\n31.7,36\n60,65\n65,71", language="csv")
        st.caption("Nilai negatif, kosong, dan tidak numerik dikeluarkan. Minimal enam nilai sensor berbeda.")
        st.info("Kolom 'reference_lux' harus berasal dari alat atau data rujukan sungguhan. Jangan membuat nilai referensi dari sensor yang sama.")


def page_computation(result: dict) -> None:
    section("Analisis / Numerical Computation", "Perhitungan metode numerik", "Uji input sensor dan pelajari setiap langkah yang dipakai untuk menghasilkan lux terkoreksi.")
    model, anchors = result["model"], result["anchors"]
    st.markdown('<div class="ls-info"><b>Metode yang digunakan:</b> regresi least squares untuk melihat tren keseluruhan data, dan interpolasi linear untuk mengestimasi nilai di antara titik-titik kalibrasi.</div>', unsafe_allow_html=True)
    st.markdown('<div style="height:17px"></div>', unsafe_allow_html=True)
    tab_ls, tab_interp = st.tabs(["Least Squares", "Interpolasi Linear"])
    with tab_ls:
        sectionline("Regresi Linear dengan Kuadrat Terkecil", "METHOD 01")
        st.latex(r"\hat{y}=ax+b")
        st.latex(r"a=\frac{n\sum xy-(\sum x)(\sum y)}{n\sum x^2-(\sum x)^2}, \qquad b=\frac{\sum y-a\sum x}{n}")
        st.markdown("**Hasil penjumlahan dari data kalibrasi**")
        st.dataframe(pd.DataFrame([{
            "n": model.n, "Σx": model.sum_x, "Σy": model.sum_y,
            "Σx²": model.sum_x2, "Σxy": model.sum_xy,
            "Penyebut": model.denominator,
        }]).style.format(precision=3), hide_index=True, width="stretch")
        st.markdown(f"**Koefisien:** a = `{model.a:.8f}` dan b = `{model.b:.8f}`")
        st.latex(rf"\boxed{{\hat{{y}}={model.a:.6f}x {model.b:+.6f}}}")
        st.caption("Rumus diimplementasikan langsung pada numerical.py, bukan memanggil fungsi regresi siap pakai.")
    with tab_interp:
        sectionline("Interpolasi antara Dua Titik Terdekat", "METHOD 02")
        st.latex(r"\hat{y}=y_0+\frac{y_1-y_0}{x_1-x_0}(x-x_0)")
        st.caption("Titik interpolasi berasal dari data kalibrasi, bukan data pengujian.")
        st.dataframe(anchors.rename(columns={"sensor_lux": "x sensor (lux)", "reference_lux": "y referensi (lux)"}), hide_index=True, width="stretch", height=245)

    st.markdown('<div style="height:24px"></div>', unsafe_allow_html=True)
    sectionline("Kalkulator Koreksi Lux", "INTERACTIVE")
    min_x = float(anchors["sensor_lux"].min())
    max_x = float(anchors["sensor_lux"].max())
    x_input = st.number_input("Masukkan pembacaan sensor BH1750 (lux)", value=100.0, step=1.0, min_value=0.0,
                              help="Masukkan angka lux sensor, lalu sistem menghitung dua prediksi otomatis.")
    result_ls = float(model.predict([x_input])[0])
    result_int = float(linear_interpolation([x_input], anchors)[0])
    a, b = st.columns(2)
    a.metric("Koreksi Least Squares", f"{result_ls:.3f} lux")
    if np.isfinite(result_int):
        b.metric("Koreksi Interpolasi", f"{result_int:.3f} lux")
        steps = interpolation_steps(x_input, anchors)
        if steps:
            st.info(
                f"Interpolasi memakai titik ({steps['x0']:.2f}, {steps['y0']:.2f}) "
                f"dan ({steps['x1']:.2f}, {steps['y1']:.2f}). "
                f"Substitusi: {steps['y0']:.2f} + (({steps['y1']:.2f} - {steps['y0']:.2f}) / "
                f"({steps['x1']:.2f} - {steps['x0']:.2f})) × ({x_input:.2f} - {steps['x0']:.2f}) "
                f"= {result_int:.3f} lux."
            )
    else:
        b.metric("Koreksi Interpolasi", "Di luar domain")
        st.warning(f"Interpolasi hanya valid di {min_x:.2f} hingga {max_x:.2f} lux. Tidak dilakukan ekstrapolasi.")
    if result_ls < 0:
        st.warning("Hasil regresi negatif tidak bermakna secara fisik sebagai lux. Jangan gunakan input ini di luar rentang kalibrasi.")


def page_visualization(result: dict) -> None:
    section("Grafik / Visualization", "Visualisasi hasil kalibrasi", "Periksa pola hubungan sensor-referensi dan distribusi residual metode numerik.")
    with st.container(border=True):
        sectionline("Calibration Curve", "COMPARISON PLOT")
        st.plotly_chart(plot_calibration(result), width="stretch", config={"displayModeBar": False})
    col1, col2 = st.columns([1.5, 1], gap="large")
    with col1:
        with st.container(border=True):
            sectionline("Residual Data Pengujian", "ERROR PLOT")
            st.plotly_chart(plot_residuals(result), width="stretch", config={"displayModeBar": False})
    with col2:
        sectionline("Cara Membaca Grafik", "GUIDE")
        st.markdown("""
        <div class="ls-panel">
          <p><b style="color:#10A89A">●</b> <b>Titik hijau</b><br><span class="ls-small">Nilai lux meter yang menjadi referensi.</span></p>
          <p><b style="color:#A3B4CA">━━</b> <b>Garis abu-abu</b><br><span class="ls-small">Sensor asli, tanpa koreksi.</span></p>
          <p><b style="color:#4268E8">━━</b> <b>Garis biru</b><br><span class="ls-small">Prediksi menggunakan interpolasi linear.</span></p>
          <p><b style="color:#F49A4F">━━</b> <b>Garis oranye</b><br><span class="ls-small">Prediksi menggunakan least squares.</span></p>
          <p><b>Residual</b><br><span class="ls-small">Selisih referensi dengan prediksi; lebih dekat ke nol berarti lebih akurat.</span></p>
        </div>
        """, unsafe_allow_html=True)
        st.caption("Interpolasi umumnya melewati titik data latih. Karena itu, metrik utama berasal dari titik pengujian yang dipisahkan.")


def page_evaluation(result: dict) -> None:
    section("Validasi / Evaluation", "Evaluasi akurasi dan residual", "Bandingkan sensor asli, interpolasi, dan least squares menggunakan data pengujian terpisah.")
    st.markdown(f'<div class="ls-info">Evaluasi menggunakan <b>{len(result["test"])} titik data pengujian</b> yang tidak dipakai saat menghitung model. Titik ujung rentang dipertahankan di data kalibrasi agar interpolasi tidak mengekstrapolasi.</div>', unsafe_allow_html=True)
    metric = result["metrics"]
    st.markdown('<div style="height:17px"></div>', unsafe_allow_html=True)
    baseline = float(metric.loc[0, "MAE"])
    best = metric.iloc[int(metric["RMSE"].argmin())]
    improvement = (baseline - float(best["MAE"])) / baseline * 100 if baseline > 0 else np.nan
    b1, b2, b3 = st.columns(3)
    with b1:
        stat("MAE Sensor Asli", f"{baseline:.2f} <span>lx</span>", "Nilai awal pengukuran", AMBER)
    with b2:
        stat("MAE Terbaik", f"{best['MAE']:.2f} <span>lx</span>", f"Metode {best['Metode']}", CYAN)
    with b3:
        stat("Penurunan Error", f"{improvement:.1f}<span>%</span>" if np.isfinite(improvement) else "N/A", "MAE dibanding sensor asli", BLUE)

    st.markdown('<div style="height:18px"></div>', unsafe_allow_html=True)
    with st.container(border=True):
        sectionline("Tabel Perbandingan Metode", "HOLDOUT METRICS")
        st.dataframe(metric.style.format({"MAE": "{:.4f}", "RMSE": "{:.4f}", "MAPE (%)": "{:.3f}", "R²": "{:.5f}"}), hide_index=True, width="stretch")
    st.markdown('<div style="height:15px"></div>', unsafe_allow_html=True)
    sectionline("Rumus Evaluasi", "NUMERICAL VALIDATION")
    st.latex(r"e_i=y_{referensi,i}-\hat{y}_i")
    st.latex(r"MAE=\frac{1}{n}\sum_{i=1}^{n}|e_i|,\qquad RMSE=\sqrt{\frac{1}{n}\sum_{i=1}^{n} e_i^2}")
    st.latex(r"MAPE=\frac{100\%}{n}\sum_{i=1}^{n}\left|\frac{e_i}{y_i}\right| \quad (y_i \ne 0)")
    st.caption("R² bisa negatif pada data pengujian bila model kalah dari prediksi menggunakan rata-rata referensi.")
    st.markdown('<div style="height:13px"></div>', unsafe_allow_html=True)
    sectionline("Residual per Titik Uji", "DETAILED RESULTS")
    subset = result["predictions"].query("kelompok == 'Pengujian'").copy()
    st.dataframe(subset[["sensor_lux", "reference_lux", "interpolasi_lux", "least_squares_lux", "residual_raw", "residual_interpolasi", "residual_least_squares"]].style.format(precision=3), hide_index=True, width="stretch")
    st.download_button(
        "Unduh Evaluasi Lengkap (Excel .xlsx)",
        make_excel(result["predictions"], title="Hasil Evaluasi LightSense", source=source_description(), metrics=result["metrics"]),
        file_name="LightSense_Evaluasi_Lengkap.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def page_engineering(result: dict) -> None:
    section("Interpretasi / Engineering Interpretation", "Makna hasil dalam instrumentasi", "Menghubungkan angka-angka komputasi dengan karakteristik sensor dan batas penerapannya.")
    d = result["cleaned"]
    metrics = result["metrics"]
    winner = metrics.loc[metrics["RMSE"].idxmin(), "Metode"]
    st.markdown(
        '<div class="ls-insight"><div class="ls-insight-label">HASIL INTERPRETASI</div>'
        f'<div class="ls-insight-value">Model terpilih: {escape(str(winner))}</div>'
        '<p>Dipilih berdasarkan RMSE terkecil pada sampel pengujian yang tidak ikut menghitung model.</p></div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div style="height:18px"></div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2, gap="large")
    with c1:
        with st.container(border=True):
            sectionline("Variabel Sistem", "INPUT / OUTPUT")
            st.markdown(f"""
        **Input:** pembacaan sensor BH1750 dalam lux (`sensor_lux`).

        **Output:** hasil kalibrasi atau estimasi lux terkoreksi.

        **Acuan:** pembacaan lux meter (`reference_lux`).

        **Domain observasi:** sensor {d['sensor_lux'].min():.2f}-{d['sensor_lux'].max():.2f} lux, referensi {d['reference_lux'].min():.2f}-{d['reference_lux'].max():.2f} lux.

        **Batas operasi model:** hanya rentang data yang telah diuji. Angka ini bukan spesifikasi maksimum sensor secara umum.
            """)
    with c2:
        with st.container(border=True):
            sectionline("Kesimpulan Pengukuran", "ANALYSIS")
            st.markdown(f"""
        Berdasarkan metrik **RMSE** pada subset pengujian, hasil terkecil saat ini diperoleh oleh **{winner}**.

        Perbedaan dua metode dapat terjadi karena least squares mencari kecenderungan global, sedangkan interpolasi memakai hubungan lokal di antara titik latih.

        Perhatikan residual yang besar atau berpola. Hal ini dapat mengindikasikan keterbatasan model, noise, atau perubahan karakteristik sensor.
            """)
    st.markdown('<div style="height:15px"></div>', unsafe_allow_html=True)
    sectionline("Batas Interpretasi Engineering", "IMPORTANT")
    st.warning("Aplikasi ini mengolah data publik, bukan mengkalibrasi perangkat milik pengguna secara langsung. Tanpa alat referensi dan uji ulang pada unit sensor sebenarnya, hasilnya tidak boleh disebut sertifikat kalibrasi.")
    st.write("**Rekomendasi pengembangan:** tambah pengulangan pengukuran, pengujian pada lampu dengan spektrum berbeda, pengecekan kestabilan dan ketidakpastian lux meter, serta data lebih luas untuk menilai generalisasi.")


def page_report(result: dict) -> None:
    section("Dokumentasi / Report", "Ekspor hasil penelitian", "Buat laporan PDF dari data, rumus, grafik, evaluasi, dan interpretasi yang sedang aktif.")
    left, right = st.columns([1.55, 1], gap="large")
    with left:
        with st.container(border=True):
            sectionline("Konfigurasi Laporan", "PDF GENERATOR")
            title = st.text_input("Judul laporan", value="LightSense: Sistem Kalibrasi Sensor Intensitas Cahaya")
            student = st.text_input("Nama / anggota kelompok", placeholder="Contoh: Nama - NRP")
    with right:
        st.markdown("""
        <div class="ls-panel">
          <div class="ls-eyebrow">REPORT CONTENTS</div>
          <b>Sudah termasuk dalam laporan:</b>
          <p class="ls-small">✓ Identitas laporan dan sumber data<br>
          ✓ Persamaan interpolasi dan least squares<br>
          ✓ Kurva hasil kalibrasi<br>
          ✓ MAE, RMSE, MAPE, R²<br>
          ✓ Interpretasi dan tabel lengkap</p>
        </div>
        """, unsafe_allow_html=True)
    st.markdown('<div style="height:12px"></div>', unsafe_allow_html=True)
    with st.expander("Lihat sumber dataset dan atribusi", expanded=False):
        st.write(source_description())
        if st.session_state.dataset_source == DATA_SOURCE:
            st.markdown("[Baca dokumen penelitian asli](https://repository.dinamika.ac.id/id/eprint/6856/1/19410200003-2023-UNIVERSITASDINAMIKA.pdf)")
        st.caption("Semua perhitungan ulang mengikuti dataset aktif. Pengguna harus memverifikasi kredibilitas data unggahan sendiri.")
    if not title.strip():
        st.warning("Isi judul laporan terlebih dahulu.")
        return
    pdf_bytes = make_pdf(result, title, student, source_description(), st.session_state.dataset_source == DATA_SOURCE)
    d1, d2, d3 = st.columns(3)
    with d1:
        st.download_button("Unduh Laporan PDF", data=pdf_bytes, file_name="LightSense_Laporan_Kalibrasi.pdf", mime="application/pdf", type="primary", width="stretch")
    with d2:
        st.download_button(
            "Unduh PDF via ZIP", data=make_pdf_zip(pdf_bytes),
            file_name="LightSense_Laporan_PDF.zip", mime="application/zip", width="stretch",
            help="Alternatif jika IDM / ekstensi browser mencegat download PDF.",
        )
    with d3:
        st.download_button(
            "Unduh Analisis Excel", data=make_excel(result["predictions"], title=title, source=source_description(), metrics=result["metrics"]),
            file_name="LightSense_Hasil_Analisis.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", width="stretch",
        )
    st.info("Jika unduh PDF menampilkan pop-up IDM 'File wasn't available on site', coba **tahan Alt saat mengeklik tombol unduh** agar IDM tidak mengambil alih, atau pakai **Unduh PDF via ZIP** lalu ekstrak. Jika masih dicegat, nonaktifkan ekstensi **IDM Integration Module** pada browser.")
    st.success(f"Laporan siap: {len(result['cleaned'])} sampel, {len(result['test'])} titik validasi, dua algoritma numerik.")


init_state()
page = navigation()
try:
    results = analyze(st.session_state.current_data)
except ValueError as problem:
    st.error(f"Dataset tidak valid: {problem}")
    st.stop()

if page == "Overview":
    page_overview(results)
elif page == "Data Management":
    page_data_management(results)
elif page == "Numerical Computation":
    page_computation(results)
elif page == "Visualization":
    page_visualization(results)
elif page == "Evaluation":
    page_evaluation(results)
elif page == "Engineering Interpretation":
    page_engineering(results)
elif page == "Report":
    page_report(results)

st.markdown('<div class="ls-footer">LIGHTSENSE  /  ELECTRONICS INSTRUMENTATION  /  NUMERICAL METHODS</div>', unsafe_allow_html=True)
