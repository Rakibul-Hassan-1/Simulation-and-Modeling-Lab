import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px

# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------
def build_cdf(prob_dict):
    """
    Take a dict {value: prob} and return a sorted list of
    (upper_cumulative_prob, value) for inverse-transform sampling.
    """
    items = sorted(prob_dict.items(), key=lambda x: x[0])
    cdf = []
    cumulative = 0.0
    for value, p in items:
        cumulative += p
        cdf.append((cumulative, value))
    # Small numerical correction
    if abs(cumulative - 1.0) > 1e-6:
        raise ValueError("Probabilities must sum to 1. Got {:.4f}".format(cumulative))
    return cdf


def sample_from_cdf(cdf, u):
    """
    Given a CDF list and a uniform u in [0,1), return the corresponding value.
    """
    for upper_p, value in cdf:
        if u <= upper_p:
            return value
    # Fallback (due to numerical error): return last value
    return cdf[-1][1]


def simulate_newspaper_selling(
    n_days,
    order_quantity,
    selling_price,
    cost_price,
    salvage_price,
    day_type_probs,
    demand_distributions,
    include_lost_profit=True,
    seed=None,
):
    """
    Monte Carlo simulation of the newspaper selling problem.

    Parameters
    ----------
    n_days : int
        Number of simulated days.
    order_quantity : int
        Number of newspapers purchased each day.
    selling_price : float
        Selling price per newspaper.
    cost_price : float
        Purchase cost per newspaper.
    salvage_price : float
        Salvage value per unsold newspaper.
    day_type_probs : dict
        e.g. {"Good": 0.35, "Fair": 0.45, "Poor": 0.20}
    demand_distributions : dict of dict
        demand_distributions[day_type] = {demand_level: prob, ...}
    include_lost_profit : bool
        Whether to subtract lost profit (underage) from daily profit.
    seed : int or None
        Random seed for reproducibility.

    Returns
    -------
    df : pandas.DataFrame
        Detailed simulation results per day.
    """
    rng = np.random.default_rng(seed)

    # Build CDFs for day type & demand distributions
    type_cdf = build_cdf(day_type_probs)
    demand_cdfs = {
        day_type: build_cdf(dist) for day_type, dist in demand_distributions.items()
    }

    records = []

    underage_profit_per_unit = selling_price - cost_price

    for day in range(1, n_days + 1):
        # Random digit for type of day
        u_type = rng.random()
        day_type = sample_from_cdf(type_cdf, u_type)

        # Random digit for demand (conditional on day type)
        u_dem = rng.random()
        demand = sample_from_cdf(demand_cdfs[day_type], u_dem)

        sold = min(demand, order_quantity)
        unsold = max(order_quantity - demand, 0)
        unmet = max(demand - order_quantity, 0)

        revenue = sold * selling_price
        cost = order_quantity * cost_price
        salvage = unsold * salvage_price
        lost_profit = unmet * underage_profit_per_unit

        if include_lost_profit:
            daily_profit = revenue + salvage - cost - lost_profit
        else:
            daily_profit = revenue + salvage - cost

        records.append(
            {
                "Day": day,
                "Random for Type": u_type,
                "Type of Day": day_type,
                "Random for Demand": u_dem,
                "Demand": demand,
                "Ordered": order_quantity,
                "Sold": sold,
                "Unsold": unsold,
                "Unmet": unmet,
                "Revenue": revenue,
                "Cost": cost,
                "Salvage": salvage,
                "Lost Profit": lost_profit,
                "Daily Profit": daily_profit,
            }
        )

    df = pd.DataFrame.from_records(records)
    df["Cumulative Profit"] = df["Daily Profit"].cumsum()
    return df


# -------------------------------------------------------------------
# Default problem parameters (taken from your screenshot)
# -------------------------------------------------------------------
DEFAULT_DAY_TYPE_PROBS = {
    "Good": 0.35,
    "Fair": 0.45,
    "Poor": 0.20,
}

# Demand levels and probabilities for each type of day
# (Rows: demand levels; columns: Good/Fair/Poor)
DEFAULT_DEMAND_DISTRIBUTIONS = {
    "Good": {40: 0.03, 50: 0.05, 60: 0.15, 70: 0.20, 80: 0.35, 90: 0.15, 100: 0.07},
    "Fair": {40: 0.10, 50: 0.18, 60: 0.40, 70: 0.20, 80: 0.08, 90: 0.04, 100: 0.00},
    "Poor": {40: 0.44, 50: 0.22, 60: 0.16, 70: 0.12, 80: 0.06, 90: 0.00, 100: 0.00},
}


# -------------------------------------------------------------------
# Streamlit UI
# -------------------------------------------------------------------
st.set_page_config(
    page_title="Newspaper Selling (Newsboy) Simulation",
    layout="wide",
)

st.title("📰 Newspaper Selling Problem – Monte Carlo Simulation")

st.markdown(
    """
This app simulates the classic **newspaper selling (newsboy) problem**.

You can set:
- The probabilities of a Good/Fair/Poor day  
- The demand distribution for each type of day  
- Economic parameters (selling price, cost, salvage, etc.)  

and then see tables, summary statistics, and multiple graphs.
"""
)

# -------------------------------------------------------------------
# Sidebar controls
# -------------------------------------------------------------------
st.sidebar.header("Simulation Settings")

n_days = st.sidebar.number_input(
    "Number of days to simulate", min_value=1, max_value=100000, value=1000, step=100
)

order_quantity = st.sidebar.number_input(
    "Order quantity (newspapers per day)", min_value=1, max_value=500, value=70, step=1
)

st.sidebar.subheader("Economic Parameters")
selling_price = st.sidebar.number_input(
    "Selling price per newspaper",
    min_value=0.0,
    value=0.50,
    step=0.05,
    format="%.2f",
)
cost_price = st.sidebar.number_input(
    "Cost price per newspaper",
    min_value=0.0,
    value=0.33,
    step=0.01,
    format="%.2f",
)
salvage_price = st.sidebar.number_input(
    "Salvage value per unsold paper",
    min_value=0.0,
    value=0.05,
    step=0.01,
    format="%.2f",
)

include_lost_profit = st.sidebar.checkbox(
    "Subtract lost profit (underage cost) from daily profit?", value=True
)

seed = st.sidebar.number_input(
    "Random seed (for reproducibility)", min_value=0, max_value=10_000_000, value=42
)

# Day type probabilities
st.sidebar.subheader("Type of Day Probabilities")
good_prob = st.sidebar.number_input(
    "Good day probability", min_value=0.0, max_value=1.0, value=0.35, step=0.01
)
fair_prob = st.sidebar.number_input(
    "Fair day probability", min_value=0.0, max_value=1.0, value=0.45, step=0.01
)
poor_prob = st.sidebar.number_input(
    "Poor day probability", min_value=0.0, max_value=1.0, value=0.20, step=0.01
)

total_prob = good_prob + fair_prob + poor_prob
if abs(total_prob - 1.0) > 1e-6:
    st.sidebar.warning(
        f"Good + Fair + Poor probabilities should sum to 1. Currently: {total_prob:.2f}"
    )

day_type_probs = {
    "Good": good_prob,
    "Fair": fair_prob,
    "Poor": poor_prob,
}

# -------------------------------------------------------------------
# Demand distributions editor
# -------------------------------------------------------------------
st.header("Demand Distributions (like your Excel table)")

st.markdown(
    """
Below is the default demand distribution table (rows = demand levels, columns = probabilities
conditional on the type of day). You can edit the values if you want a different scenario
(ensure each column sums to 1).
"""
)

# Build table for editing
dem_levels = sorted(list(DEFAULT_DEMAND_DISTRIBUTIONS["Good"].keys()))
data = {
    "Demand": dem_levels,
    "Good": [DEFAULT_DEMAND_DISTRIBUTIONS["Good"][d] for d in dem_levels],
    "Fair": [DEFAULT_DEMAND_DISTRIBUTIONS["Fair"][d] for d in dem_levels],
    "Poor": [DEFAULT_DEMAND_DISTRIBUTIONS["Poor"][d] for d in dem_levels],
}
dem_table = pd.DataFrame(data)

edited_table = st.data_editor(
    dem_table,
    use_container_width=True,
    num_rows="fixed",
    key="demand_editor",
)

# Convert edited table back into dict-of-dict format
demand_distributions = {
    "Good": {int(row["Demand"]): float(row["Good"]) for _, row in edited_table.iterrows()},
    "Fair": {int(row["Demand"]): float(row["Fair"]) for _, row in edited_table.iterrows()},
    "Poor": {int(row["Demand"]): float(row["Poor"]) for _, row in edited_table.iterrows()},
}

# Quick probability checks
check_cols = []
for col in ["Good", "Fair", "Poor"]:
    s = edited_table[col].sum()
    check_cols.append(f"{col}: {s:.3f}")

st.caption("Column probability sums → " + " | ".join(check_cols))

# -------------------------------------------------------------------
# Run simulation
# -------------------------------------------------------------------
with st.spinner("Running simulation..."):
    df = simulate_newspaper_selling(
        n_days=n_days,
        order_quantity=order_quantity,
        selling_price=selling_price,
        cost_price=cost_price,
        salvage_price=salvage_price,
        day_type_probs=day_type_probs,
        demand_distributions=demand_distributions,
        include_lost_profit=include_lost_profit,
        seed=seed,
    )

# -------------------------------------------------------------------
# Layout with tabs
# -------------------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs(
    ["📋 Simulation table", "📊 Summary stats", "📈 Graphs", "🔎 Distribution details"]
)

# -------------------------------------------------------------------
# Tab 1: Table
# -------------------------------------------------------------------
with tab1:
    st.subheader("Daily Simulation Table")
    st.dataframe(df, use_container_width=True, height=450)
    st.download_button(
        "Download table as CSV",
        data=df.to_csv(index=False),
        file_name="newspaper_simulation.csv",
        mime="text/csv",
    )

# -------------------------------------------------------------------
# Tab 2: Summary stats
# -------------------------------------------------------------------
with tab2:
    st.subheader("Summary Statistics")

    avg_profit = df["Daily Profit"].mean()
    std_profit = df["Daily Profit"].std()
    total_profit = df["Daily Profit"].sum()
    avg_demand = df["Demand"].mean()
    stockout_rate = (df["Unmet"] > 0).mean()
    scrap_rate = (df["Unsold"] > 0).mean()

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.metric("Average daily profit", f"{avg_profit:,.2f}")
        st.metric("Total profit", f"{total_profit:,.2f}")
    with col_b:
        st.metric("Std dev of daily profit", f"{std_profit:,.2f}")
        st.metric("Average demand", f"{avg_demand:,.2f}")
    with col_c:
        st.metric("Stockout rate", f"{100*stockout_rate:,.1f}%")
        st.metric("Scrap (unsold) rate", f"{100*scrap_rate:,.1f}%")

    st.markdown("---")
    st.markdown("#### Profit by Type of Day")
    group_type = df.groupby("Type of Day")["Daily Profit"].agg(
        ["mean", "std", "count", "sum"]
    )
    st.dataframe(group_type, use_container_width=True)

# -------------------------------------------------------------------
# Tab 3: Graphs (commonly used analysis charts)
# -------------------------------------------------------------------
with tab3:
    st.subheader("Graphical Analysis")

    # 1. Line chart – cumulative profit over days
    fig_cum = px.line(
        df,
        x="Day",
        y="Cumulative Profit",
        title="Cumulative Profit over Time",
    )
    st.plotly_chart(fig_cum, use_container_width=True)

    # 2. Histogram – distribution of daily profits
    fig_hist = px.histogram(
        df,
        x="Daily Profit",
        nbins=30,
        title="Histogram of Daily Profit",
    )
    st.plotly_chart(fig_hist, use_container_width=True)

    # 3. Boxplot – daily profit by type of day
    fig_box = px.box(
        df,
        x="Type of Day",
        y="Daily Profit",
        title="Daily Profit by Type of Day",
    )
    st.plotly_chart(fig_box, use_container_width=True)

    # 4. Bar chart – demand frequency
    fig_dem_bar = px.bar(
        df["Demand"].value_counts().sort_index().rename_axis("Demand").reset_index(name="Frequency"),
        x="Demand",
        y="Frequency",
        title="Demand Level Frequency",
    )
    st.plotly_chart(fig_dem_bar, use_container_width=True)

    # 5. Pie chart – proportion of day types
    fig_pie = px.pie(
        df,
        names="Type of Day",
        title="Proportion of Good / Fair / Poor Days",
    )
    st.plotly_chart(fig_pie, use_container_width=True)

# -------------------------------------------------------------------
# Tab 4: Distribution details
# -------------------------------------------------------------------
with tab4:
    st.subheader("Day-Type Probabilities")
    st.write(pd.DataFrame.from_dict(day_type_probs, orient="index", columns=["Probability"]))

    st.subheader("Demand Distributions (Final)")
    st.dataframe(edited_table, use_container_width=True)

    st.markdown(
    """
### **Interpretation Notes**

- **Lost Profit** is calculated as:  
  \n
  **Lost Profit = (Selling Price − Cost Price) × Unmet Demand**

- If **“Subtract lost profit”** is checked, the daily profit is:  
  \n
  **Daily Profit = Revenue + Salvage − Cost − Lost Profit**

- Otherwise:  
  \n
  **Daily Profit = Revenue + Salvage − Cost**
"""
)
