# app.py
# Single-Server Queue Simulator — Streamlit App with Professional PDF Download

from dataclasses import dataclass
from typing import List, Optional
import random
import pandas as pd
import streamlit as st
import altair as alt
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable

# --------------------------
# Mapping functions
# --------------------------
def inter_arrival_time_from_rn(rn: int) -> int:
    if rn < 126: return 1
    if rn < 251: return 2
    if rn < 376: return 3
    if rn < 501: return 4
    if rn < 626: return 5
    if rn < 751: return 6
    if rn < 876: return 7
    if rn <= 1000: return 8
    raise ValueError("IAT RN must be in 1..1000")

def service_time_from_rn(rn: int) -> int:
    if rn < 30: return 1
    if rn < 50: return 2
    if rn < 60: return 3
    if rn < 65: return 4
    if rn < 75: return 5
    if rn <= 100: return 6
    raise ValueError("ST RN must be in 1..100")

# --------------------------
# Simulation core
# --------------------------
@dataclass
class SimulationInput:
    n_customers: int
    rn_iat: Optional[List[int]] = None
    rn_st: Optional[List[int]] = None

def simulate_queue(sim_in: SimulationInput) -> pd.DataFrame:
    n = sim_in.n_customers
    if n <= 0:
        raise ValueError("n_customers must be >= 1")

    rn_iat = sim_in.rn_iat if sim_in.rn_iat is not None else [random.randint(1, 1000) for _ in range(n)]
    rn_st  = sim_in.rn_st  if sim_in.rn_st  is not None else [random.randint(1, 100)  for _ in range(n)]
    if len(rn_iat) != n or len(rn_st) != n:
        raise ValueError("Length of rn_iat and rn_st must equal n_customers.")

    iat = [inter_arrival_time_from_rn(x) for x in rn_iat]
    iat[0] = 0
    arrival = [0] * n
    for i in range(1, n):
        arrival[i] = arrival[i-1] + iat[i]
    stime = [service_time_from_rn(x) for x in rn_st]

    tsb, wt, tse, tis, idle = [0]*n, [0]*n, [0]*n, [0]*n, [0]*n
    tse[0] = stime[0]
    tis[0] = stime[0]

    for i in range(1, n):
        prev_tse = tse[i-1]
        tsb[i] = max(prev_tse, arrival[i])
        wt[i]  = tsb[i] - arrival[i]
        tse[i] = tsb[i] + stime[i]
        tis[i] = stime[i] + wt[i]
        idle[i] = max(0, tsb[i] - prev_tse)

    return pd.DataFrame({
        "Cust": range(1, n+1),
        "RN_IAT(1-1000)": rn_iat,
        "IAT": iat,
        "Arrival": arrival,
        "RN_ST(1-100)": rn_st,
        "ST": stime,
        "TSB": tsb,
        "Wait": wt,
        "TSE": tse,
        "TimeInSystem": tis,
        "ServerIdle": idle
    })

# --------------------------
# Helpers
# --------------------------
def parse_csv_ints(s: str) -> List[int]:
    parts = [p.strip() for p in s.replace("\n", ",").split(",")]
    ints = [int(p) for p in parts if p]
    return ints

def compute_summaries(df: pd.DataFrame) -> pd.DataFrame:
    total_service = int(df["ST"].sum())
    total_idle = int(df["ServerIdle"].sum())
    avg_wait = float(df["Wait"].mean())
    max_wait = int(df["Wait"].max())
    util = total_service / (total_service + total_idle) if (total_service + total_idle) > 0 else 0.0
    horizon_end = int(df["TSE"].iloc[-1])
    return pd.DataFrame({
        "Metric": [
            "Average waiting time",
            "Maximum waiting time",
            "Total server idle time",
            "Server utilization (%)",
            "Simulation horizon end (last TSE)"
        ],
        "Value": [
            f"{avg_wait:.2f}",
            f"{max_wait}",
            f"{total_idle}",
            f"{util*100:.2f}%",
            f"{horizon_end}"
        ]
    })

# --------------------------
# PDF Generator with professional header
# --------------------------
def generate_summary_pdf(summary_df: pd.DataFrame) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    # Header styles
    header_style = ParagraphStyle("Header", parent=styles["Heading1"], fontSize=16, leading=20, alignment=1, spaceAfter=10)
    subheader_style = ParagraphStyle("SubHeader", parent=styles["Normal"], fontSize=11, leading=14, alignment=1, spaceAfter=6)

    # University name and separator
    elements.append(Paragraph("<b>Port City International University</b>", header_style))
    elements.append(HRFlowable(width="80%", thickness=1, lineCap='round', color=colors.HexColor("#4b8bbe")))
    elements.append(Spacer(1, 6))

    # Course info
    course_info = """Course Title: <b>Simulation & Modeling Lab</b><br/>
    Course Code: <b>CSE 424</b>"""
    elements.append(Paragraph(course_info, subheader_style))

    # Teacher info
    teacher_info = """<b>Course Teacher:</b><br/>
    Farzina Akther<br/>
    Assistant Professor<br/>
    Department of Computer Science and Engineering<br/>
    Port City International University"""
    elements.append(Paragraph(teacher_info, subheader_style))
    elements.append(Spacer(1, 12))

    # Simulation summary title
    elements.append(HRFlowable(width="50%", thickness=0.8, lineCap='round', color=colors.grey))
    elements.append(Spacer(1, 6))
    elements.append(Paragraph("<b>Simulation Summary</b>", header_style))
    elements.append(Spacer(1, 12))

    # Table
    data = [summary_df.columns.tolist()] + summary_df.values.tolist()
    table = Table(data, colWidths=[3*inch, 2*inch])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4b8bbe")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BACKGROUND", (0, 1), (-1, -1), colors.whitesmoke)
    ]))
    elements.append(table)

    doc.build(elements)
    buffer.seek(0)
    return buffer.read()

# --------------------------
# Streamlit UI
# --------------------------
st.set_page_config(page_title="Single-Server Queue Simulator", page_icon="🧮", layout="wide")
st.title("Single-Server Queue Simulator")
st.caption("Excel-like discrete-event simulation with a clean Streamlit UI.")

with st.sidebar:
    st.header("Controls")
    n_customers = st.number_input("Number of customers", min_value=1, value=10, step=1)
    seed_text = st.text_input("Random seed (optional)", value="")
    if seed_text:
        try:
            random.seed(seed_text)
            st.caption("Seed set for reproducibility.")
        except Exception:
            st.warning("Seed could not be set — proceeding without it.")

    st.divider()
    use_custom = st.toggle("Provide custom RN lists", value=False)
    rn_iat_str, rn_st_str = "", ""
    if use_custom:
        rn_iat_str = st.text_area("RN for IAT (1..1000)", height=120)
        rn_st_str = st.text_area("RN for ST (1..100)", height=120)
    run = st.button("Run Simulation", type="primary")
    reset = st.button("Reset")

if reset:
    st.experimental_rerun()

rows_df = summ_df = None
if run:
    try:
        rn_iat = parse_csv_ints(rn_iat_str) if (use_custom and rn_iat_str.strip()) else None
        rn_st = parse_csv_ints(rn_st_str) if (use_custom and rn_st_str.strip()) else None
        df = simulate_queue(SimulationInput(n_customers=n_customers, rn_iat=rn_iat, rn_st=rn_st))
        rows_df, summ_df = df, compute_summaries(df)
    except Exception as e:
        st.error(f"Error: {e}")

# --------------------------
# Display results
# --------------------------
if rows_df is not None and summ_df is not None:
    c1, c2, c3, c4, c5 = st.columns(5)
    avg_wait = float(rows_df["Wait"].mean())
    max_wait = int(rows_df["Wait"].max())
    total_idle = int(rows_df["ServerIdle"].sum())
    total_service = int(rows_df["ST"].sum())
    utilization = total_service / (total_service + total_idle) if (total_service + total_idle) > 0 else 0.0
    horizon_end = int(rows_df["TSE"].iloc[-1])

    c1.metric("Avg wait", f"{avg_wait:.2f}")
    c2.metric("Max wait", f"{max_wait}")
    c3.metric("Total idle", f"{total_idle}")
    c4.metric("Utilization", f"{utilization*100:.2f}%")
    c5.metric("Horizon end", f"{horizon_end}")

    st.divider()

    left, right = st.columns(2)
    with left:
        st.subheader("Wait time by customer")
        chart_wait = (
            alt.Chart(rows_df)
            .mark_bar()
            .encode(x="Cust:O", y="Wait:Q", tooltip=["Cust", "Wait"])
            .properties(height=300)
        )
        st.altair_chart(chart_wait, use_container_width=True)

    with right:
        st.subheader("Timeline (TSE)")
        chart_tse = (
            alt.Chart(rows_df)
            .mark_line(point=True)
            .encode(x="Cust:O", y="TSE:Q", tooltip=["Cust", "TSE"])
            .properties(height=300)
        )
        st.altair_chart(chart_tse, use_container_width=True)

    st.subheader("Wait time distribution")
    chart_hist = (
        alt.Chart(rows_df)
        .mark_bar()
        .encode(alt.X("Wait:Q", bin=alt.Bin(maxbins=20)), alt.Y("count()"))
        .properties(height=220)
    )
    st.altair_chart(chart_hist, use_container_width=True)

    st.divider()
    st.subheader("Results Table")
    st.dataframe(rows_df, use_container_width=True, hide_index=True)
    st.subheader("Summaries")
    st.table(summ_df)

    st.divider()
    st.subheader("Downloads")

    results_csv = rows_df.to_csv(index=False).encode("utf-8")
    summaries_csv = summ_df.to_csv(index=False).encode("utf-8")
    st.download_button("Download results CSV", data=results_csv, file_name="simulation_results.csv", mime="text/csv")
    st.download_button("Download summaries CSV", data=summaries_csv, file_name="simulation_summaries.csv", mime="text/csv")

    # PDF download button
    pdf_data = generate_summary_pdf(summ_df)
    st.download_button(
        "📄 Download Summary PDF",
        data=pdf_data,
        file_name="simulation_summary.pdf",
        mime="application/pdf"
    )

st.caption("Mapping buckets: IAT RN 1..1000 → 1..8; ST RN 1..100 → 1..6. First arrival starts at time 0.")
