# app.py
# Single-Server Queue Simulator — Streamlit App
# ---------------------------------------------
# Features:
# - Clean UI with sidebar controls
# - Provide custom RN lists (textarea) or random generation
# - Optional seed for reproducibility
# - KPI cards (avg wait, max wait, idle, utilization, horizon end)
# - Charts (Wait by customer, TSE timeline, Wait histogram)
# - Results table
# - CSV download buttons (results & summaries)
#
# Run:
#   pip install streamlit pandas altair
#   streamlit run app.py

from dataclasses import dataclass
from typing import List, Optional
import random
import pandas as pd
import streamlit as st
import altair as alt

# --------------------------
# Mapping functions (Excel logic, inclusive final bucket)
# --------------------------
def inter_arrival_time_from_rn(rn: int) -> int:
    # 1..1000 -> IAT
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
    # 1..100 -> ST
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
    rn_iat: Optional[List[int]] = None    # values 1..1000
    rn_st: Optional[List[int]] = None     # values 1..100

def simulate_queue(sim_in: SimulationInput) -> pd.DataFrame:
    n = sim_in.n_customers
    if n <= 0:
        raise ValueError("n_customers must be >= 1")

    # Generate RN if not provided
    rn_iat = sim_in.rn_iat if sim_in.rn_iat is not None else [random.randint(1, 1000) for _ in range(n)]
    rn_st  = sim_in.rn_st  if sim_in.rn_st  is not None else [random.randint(1, 100)  for _ in range(n)]
    if len(rn_iat) != n or len(rn_st) != n:
        raise ValueError("Length of rn_iat and rn_st must equal n_customers.")

    # Inter-arrival times from RN (we’ll override first to 0)
    iat = [inter_arrival_time_from_rn(x) for x in rn_iat]
    iat[0] = 0  # First customer starts the system

    # Arrival times: first = 0; then cumulative
    arrival = [0] * n
    for i in range(1, n):
        arrival[i] = arrival[i-1] + iat[i]

    # Service times from RN
    st = [service_time_from_rn(x) for x in rn_st]

    # Time Service Begin (TSB), Waiting Time (WT), Time Service End (TSE),
    # Time in System (TIS), Server Idle (IDLE)
    tsb = [0] * n
    wt  = [0] * n
    tse = [0] * n
    tis = [0] * n
    idle = [0] * n

    # First customer (all zeros except ST & TSE)
    tse[0] = st[0]  # starts at 0, ends at ST[0]
    tis[0] = st[0]  # wait 0 + service

    # Rest of customers
    for i in range(1, n):
        prev_tse = tse[i-1]
        tsb[i] = max(prev_tse, arrival[i])
        wt[i]  = tsb[i] - arrival[i]
        tse[i] = tsb[i] + st[i]
        tis[i] = st[i] + wt[i]
        idle[i] = max(0, tsb[i] - prev_tse)  # server idle gap before starting i

    df = pd.DataFrame({
        "Cust": range(1, n+1),
        "RN_IAT(1-1000)": rn_iat,
        "IAT": iat,
        "Arrival": arrival,
        "RN_ST(1-100)": rn_st,
        "ST": st,
        "TSB": tsb,
        "Wait": wt,
        "TSE": tse,
        "TimeInSystem": tis,
        "ServerIdle": idle
    })
    return df

# --------------------------
# Helpers
# --------------------------
def parse_csv_ints(s: str) -> List[int]:
    parts = [p.strip() for p in s.replace("\n", ",").split(",")]
    ints: List[int] = []
    for p in parts:
        if p == "":
            continue
        ints.append(int(p))
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
            "Simulation horizon end (last TSE)",
        ],
        "Value": [
            f"{avg_wait:.2f}",
            f"{max_wait}",
            f"{total_idle}",
            f"{util*100:.2f}%",
            f"{horizon_end}",
        ],
    })

# --------------------------
# Streamlit UI
# --------------------------
st.set_page_config(page_title="Single-Server Queue Simulator", page_icon="🧮", layout="wide")

st.markdown("""
# Single-Server Queue Simulator
Excel-like discrete-event simulation with a clean Streamlit UI.
""")

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
    use_custom = st.toggle("Provide custom RN lists", value=False, help="If off, RN lists are generated randomly.")

    rn_iat_str = ""
    rn_st_str = ""
    if use_custom:
        rn_iat_str = st.text_area("RN for IAT (1..1000)", placeholder="e.g. 12, 845, 310, 999, ...", height=120)
        rn_st_str  = st.text_area("RN for ST (1..100)",  placeholder="e.g. 5, 88, 60, 17, ...", height=120)
        st.caption("Comma or newline separated. Lengths must equal the number of customers.")

    run = st.button("Run Simulation", type="primary")
    reset = st.button("Reset")

if reset:
    st.experimental_rerun()

rows_df: Optional[pd.DataFrame] = None
summ_df: Optional[pd.DataFrame] = None

if run:
    try:
        rn_iat = parse_csv_ints(rn_iat_str) if (use_custom and rn_iat_str.strip()) else None
        rn_st  = parse_csv_ints(rn_st_str)  if (use_custom and rn_st_str.strip())  else None
        if use_custom:
            if rn_iat is None or rn_st is None:
                st.error("Both RN lists are required when 'Provide custom RN lists' is ON.")
                st.stop()
            if len(rn_iat) != n_customers or len(rn_st) != n_customers:
                st.error(f"Provided RN lengths (IAT={len(rn_iat)}, ST={len(rn_st)}) do not match n={n_customers}.")
                st.stop()
        df = simulate_queue(SimulationInput(n_customers=n_customers, rn_iat=rn_iat, rn_st=rn_st))
        rows_df = df
        summ_df = compute_summaries(df)
    except Exception as e:
        st.error(f"Error: {e}")

# Show output
if rows_df is not None and summ_df is not None:
    # KPIs
    c1, c2, c3, c4, c5 = st.columns(5)
    # Extract values cleanly
    avg_wait = float(rows_df["Wait"].mean())
    max_wait = int(rows_df["Wait"].max())
    total_idle = int(rows_df["ServerIdle"].sum())
    total_service = int(rows_df["ST"].sum())
    utilization = (total_service / (total_service + total_idle)) if (total_service + total_idle) > 0 else 0.0
    horizon_end = int(rows_df["TSE"].iloc[-1])

    c1.metric("Avg wait", f"{avg_wait:.2f}")
    c2.metric("Max wait", f"{max_wait}")
    c3.metric("Total idle", f"{total_idle}")
    c4.metric("Utilization", f"{utilization*100:.2f}%")
    c5.metric("Horizon end", f"{horizon_end}")

    st.divider()

    # Charts
    left, right = st.columns(2)

    with left:
        st.subheader("Wait time by customer")
        chart_wait = (
            alt.Chart(rows_df)
            .mark_bar()
            .encode(x=alt.X("Cust:O", title="Customer"), y=alt.Y("Wait:Q", title="Wait"), tooltip=["Cust", "Wait"])
            .properties(height=300)
        )
        st.altair_chart(chart_wait, use_container_width=True)

    with right:
        st.subheader("Timeline (TSE)")
        chart_tse = (
            alt.Chart(rows_df)
            .mark_line(point=True)
            .encode(x=alt.X("Cust:O", title="Customer"), y=alt.Y("TSE:Q", title="TSE"), tooltip=["Cust", "TSE"])
            .properties(height=300)
        )
        st.altair_chart(chart_tse, use_container_width=True)

    st.subheader("Wait time distribution")
    chart_hist = (
        alt.Chart(rows_df)
        .mark_bar()
        .encode(
            alt.X("Wait:Q", bin=alt.Bin(maxbins=20), title="Wait"),
            alt.Y("count()", title="Count"),
            tooltip=[alt.Tooltip("count()", title="Count")]
        )
        .properties(height=220)
    )
    st.altair_chart(chart_hist, use_container_width=True)

    st.divider()

    # Tables
    st.subheader("Results Table")
    st.dataframe(rows_df, use_container_width=True, hide_index=True)

    st.subheader("Summaries")
    st.table(summ_df)

    # Downloads
    st.divider()
    st.subheader("Downloads")
    results_csv = rows_df.to_csv(index=False).encode("utf-8")
    summaries_csv = summ_df.to_csv(index=False).encode("utf-8")
    st.download_button("Download results CSV", data=results_csv, file_name="simulation_results.csv", mime="text/csv")
    st.download_button("Download summaries CSV", data=summaries_csv, file_name="simulation_summaries.csv", mime="text/csv")

# Footer
st.caption("Mapping buckets: IAT RN 1..1000 → 1..8; ST RN 1..100 → 1..6. First arrival starts at time 0.")
