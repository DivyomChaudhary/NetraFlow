import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import os

# 1. Page Configuration
st.set_page_config(page_title="NetraFlow", page_icon="👁", layout="wide")

# 2. Database Loader
@st.cache_data(ttl=30)
def load_data():
    db_path = os.path.join("logs_", "traffic_security.db")
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query("SELECT * FROM vehicle_logs", conn)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    conn.close()
    return df

# 3. Main Logic
st.title("Traffic Security Analytics")
df = load_data()

if df.empty:
    st.warning("No data found in the database.")
else:
    # --- Metrics ---
    total_v = len(df)
    suspicious_v = len(df[df['is_suspicious'] == 1])
    hazard_rate = (suspicious_v / total_v * 100) if total_v > 0 else 0

    m1, m2, m3 = st.columns(3)
    m1.metric("Total Vehicles Tracked", total_v)
    m2.metric("Security Alerts", suspicious_v)
    m3.metric("Suspicion Rate", f"{hazard_rate:.1f}%")

    st.divider()

    # --- Charts ---
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Traffic Volume Over Time")

        # 1. Resample and count specific ID occurrences
        time_data = df.resample('5s', on='timestamp')['id'].count().reset_index(name='vehicle_count')

        # 2. IMPORTANT: Remove intervals with 0 vehicles so Plotly doesn't render empty bars
        time_data = time_data[time_data['vehicle_count'] > 0]

        # 3. Plot using the cleaned 'vehicle_count' column
        fig = px.bar(time_data, x='timestamp', y='vehicle_count', title="Traffic Density Analysis")
        fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, width="stretch")

    with col_right:
        st.subheader("Detected Vehicle Colors")
        color_counts = df['color'].value_counts().reset_index()
        fig_pie = px.pie(color_counts, names='color', values='count', hole=0.4)
        fig_pie.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_pie, width="stretch")