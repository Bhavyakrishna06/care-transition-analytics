import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import timedelta

# ==========================================
# 1. PAGE CONFIGURATION & DATA GENERATION
# ==========================================
st.set_page_config(page_title="Care Transition Efficiency Analytics", layout="wide")

@st.cache_data
def generate_mock_data():
    """Generates synthetic dataset matching the UAC Care Pipeline requirements."""
    dates = pd.date_range(start="2023-01-01", end="2024-01-01")
    np.random.seed(42)
    
    # Simulate flow mechanics
    apprehended = np.random.normal(300, 50, size=len(dates)).astype(int)
    transferred = (apprehended * np.random.uniform(0.70, 0.95, size=len(dates))).astype(int)
    discharged = (transferred * np.random.uniform(0.65, 0.90, size=len(dates))).astype(int)
    
    # Simulate cumulative accumulations (stock variables)
    cbp_custody = 1000 + np.cumsum(apprehended) - np.cumsum(transferred)
    hhs_care = 5000 + np.cumsum(transferred) - np.cumsum(discharged)
    
    df = pd.DataFrame({
        "Date": dates,
        "Children apprehended and placed in CBP custody": apprehended,
        "Children in CBP custody": cbp_custody,
        "Children transferred out of CBP custody": transferred,
        "Children in HHS Care": hhs_care,
        "Children discharged from HHS Care": discharged
    })
    
    # Calculate Derived Metrics
    df['Transfer Efficiency Ratio'] = df['Children transferred out of CBP custody'] / df['Children in CBP custody']
    df['Discharge Effectiveness'] = df['Children discharged from HHS Care'] / df['Children in HHS Care']
    df['Pipeline Throughput Rate'] = df['Children discharged from HHS Care'] / df['Children apprehended and placed in CBP custody']
    df['Backlog Accumulation Rate'] = df['Children apprehended and placed in CBP custody'] - df['Children discharged from HHS Care']
    
    return df

df = generate_mock_data()

# ==========================================
# 2. SIDEBAR CONTROLS & FILTERS
# ==========================================
st.sidebar.header("Pipeline Controls")

# Date Range Selection
min_date = df["Date"].min().date()
max_date = df["Date"].max().date()
date_range = st.sidebar.slider("Select Date Range", min_value=min_date, max_value=max_date, value=(min_date, max_date))

filtered_df = df[(df["Date"].dt.date >= date_range[0]) & (df["Date"].dt.date <= date_range[1])].copy()

# Metric Toggles
st.sidebar.subheader("Metric Toggles")
show_transfer_eff = st.sidebar.checkbox("Show Transfer Efficiency", value=True)
show_discharge_eff = st.sidebar.checkbox("Show Discharge Effectiveness", value=True)

# Threshold Alerts
st.sidebar.subheader("Alert Thresholds")
eff_threshold = st.sidebar.slider("Efficiency Alert Threshold (%)", 0, 10, 2) / 100.0

# ==========================================
# 3. EXECUTIVE SUMMARY (KPIs)
# ==========================================
st.title("Care Transition Efficiency & Placement Outcome Analytics")
st.markdown("Monitor the efficiency of the UAC care pipeline from CBP apprehension to HHS discharge and sponsor reunification.")

kpi1, kpi2, kpi3, kpi4 = st.columns(4)
with kpi1:
    avg_transfer = filtered_df['Transfer Efficiency Ratio'].mean()
    st.metric("Avg Transfer Efficiency", f"{avg_transfer:.2%}", help="Transfers ÷ CBP Custody")
with kpi2:
    avg_discharge = filtered_df['Discharge Effectiveness'].mean()
    st.metric("Avg Discharge Effectiveness", f"{avg_discharge:.2%}", help="Discharges ÷ HHS Care")
with kpi3:
    avg_throughput = filtered_df['Pipeline Throughput Rate'].mean()
    st.metric("Pipeline Throughput", f"{avg_throughput:.2%}", help="Total Exits ÷ Total Entries")
with kpi4:
    total_backlog = filtered_df['Backlog Accumulation Rate'].sum()
    st.metric("Total Backlog Accumulated", f"{total_backlog:,.0f}", help="Inflow minus Outflow in period")

st.divider()

# ==========================================
# 4. CARE PIPELINE FLOW VISUALIZATION (SANKEY)
# ==========================================
st.subheader("Aggregate Care Pipeline Flow")
total_apprehended = filtered_df["Children apprehended and placed in CBP custody"].sum()
total_transferred = filtered_df["Children transferred out of CBP custody"].sum()
total_discharged = filtered_df["Children discharged from HHS Care"].sum()

fig_sankey = go.Figure(data=[go.Sankey(
    node = dict(
      pad = 15, thickness = 20,
      line = dict(color = "black", width = 0.5),
      label = ["CBP Custody (Intake)", "HHS Care (Transfer)", "Sponsor Placement (Discharge)"],
      color = ["#EF553B", "#636EFA", "#00CC96"]
    ),
    link = dict(
      source = [0, 1], # CBP -> HHS, HHS -> Sponsor
      target = [1, 2],
      value = [total_transferred, total_discharged],
      color = ["rgba(99, 110, 250, 0.4)", "rgba(0, 204, 150, 0.4)"]
    ))])
fig_sankey.update_layout(height=400, margin=dict(l=0, r=0, t=30, b=0))
st.plotly_chart(fig_sankey, use_container_width=True)

# ==========================================
# 5. EFFICIENCY & BOTTLENECK PANELS
# ==========================================
col1, col2 = st.columns(2)

with col1:
    st.subheader("Transfer & Discharge Efficiency Trends")
    fig_eff = go.Figure()
    if show_transfer_eff:
        fig_eff.add_trace(go.Scatter(x=filtered_df["Date"], y=filtered_df["Transfer Efficiency Ratio"], 
                                     mode='lines', name='Transfer Efficiency', line=dict(color='#636EFA')))
    if show_discharge_eff:
        fig_eff.add_trace(go.Scatter(x=filtered_df["Date"], y=filtered_df["Discharge Effectiveness"], 
                                     mode='lines', name='Discharge Effectiveness', line=dict(color='#00CC96')))
    
    # Threshold Line
    fig_eff.add_hline(y=eff_threshold, line_dash="dot", annotation_text=f"Alert Threshold ({eff_threshold:.1%})", line_color="red")
    fig_eff.update_layout(yaxis_tickformat='.1%', height=400, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    st.plotly_chart(fig_eff, use_container_width=True)

with col2:
    st.subheader("Backlog Accumulation Detection")
    # Color bars red if backlog is positive, green if negative (clearing backlog)
    filtered_df['Backlog Color'] = np.where(filtered_df['Backlog Accumulation Rate'] > 0, '#EF553B', '#00CC96')
    
    fig_backlog = go.Figure(data=[
        go.Bar(
            x=filtered_df['Date'], 
            y=filtered_df['Backlog Accumulation Rate'],
            marker_color=filtered_df['Backlog Color'],
            name='Daily Backlog'
        )
    ])
    fig_backlog.update_layout(height=400, yaxis_title="Cases Accumulated (Apprehended - Discharged)")
    st.plotly_chart(fig_backlog, use_container_width=True)

# ==========================================
# 6. OUTCOME TREND ANALYSIS
# ==========================================
st.subheader("System Load vs. Placement Outcomes")
fig_outcomes = go.Figure()
fig_outcomes.add_trace(go.Scatter(
    x=filtered_df["Date"], y=filtered_df["Children in HHS Care"],
    fill='tozeroy', mode='none', name='Active HHS Care Load', fillcolor='rgba(99, 110, 250, 0.2)'
))
fig_outcomes.add_trace(go.Scatter(
    x=filtered_df["Date"], y=filtered_df["Children discharged from HHS Care"],
    mode='lines', name='Successful Sponsor Placements (Discharges)', line=dict(color='#00CC96', width=3)
))
fig_outcomes.update_layout(height=450, yaxis_title="Number of Children", hovermode="x unified")
st.plotly_chart(fig_outcomes, use_container_width=True)