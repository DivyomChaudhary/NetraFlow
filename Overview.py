import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import os

# 1. Page Configuration
st.set_page_config(page_title="NetraFlow", page_icon="👁", layout="wide")
st.markdown("""
    <style>
    /* Main Background with a soft warm tint */
    .stApp {
        background-color: #FFF9F2; 
    }
    /* Colorful header for the sidebar */
    [data-testid="stSidebar"] {
        background-image: linear-gradient(#2E3192, #1BFFFF);
        color: white;
    }
    /* Metric Cards Styling */
    [data-testid="stMetric"] {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 15px;
        box-shadow: 5px 5px 15px rgba(0,0,0,0.05);
        border-left: 5px solid #FF9933; /* Saffron accent */
    }
    /* Force text to be Dark Gray/Black */
    header{
    background-color: #FFF9F2 !important;
    color: #000000 !important;
    font-family: 'Inter', sans-serif;
    }
    [data-testid="stIconMaterial"]{
    color: rgba(0,0,0) !important;
    background-color: rgba(0,0,0,0) !important;
    }
    .st-emotion-cache{
    color: #000000 !important;
    }

    /* Specifically Target Headers */
    h1, h2, h3, h4, h5, h6 {
        color: #1A202C !important;
    }

    /* Fix Metric Labels & Values */
    [data-testid="stMetricLabel"] {
        color: #4A5568 !important; /* Muted dark gray */
    }
    [data-testid="stMetricValue"] {
        color: #2D3748 !important; /* Bold dark gray */
    }

    /* Make the Sidebar text dark if the background is light */
    [data-testid="stSidebarNav"] span {
        color: #2D3748 !important;
        font-weight: 500;
    }
    </style>
    """, unsafe_allow_html=True)

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
        fig = px.bar(time_data,
                     x='timestamp',
                     y='vehicle_count',
                     title="Traffic Density Analysis",
                     template="presentation",
                     labels={'timestamp': 'Date and Time', 'vehicle_count': 'No. of Vehicles'})
        fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, width="stretch")

    with col_right:
        st.subheader("Speed Distribution")

        bins = [0, 10, 20, 30, 40, 50, float('inf')]
        labels = ['0-10', '10-20', '20-30', '30-40', '40-50', '50+']

        # Categorize the max_speed
        df['speed_group'] = pd.cut(df['speed'], bins=bins, labels=labels)
        speed_counts = df['speed_group'].value_counts().sort_index().reset_index()
        speed_counts.columns = ['Speed Range', 'Count']

        color_map = {
            '0-10': '#22c55e',  # Green (Safe)
            '10-20': '#a3e635',  # Light Green
            '20-30': '#fbbf24',  # Yellow/Amber
            '30-40': '#f97316',  # Orange
            '40-50': '#ef4444',  # Red
            '50+': '#991b1b'  # Dark Red (High Alert)
        }

        # Donut Chart
        fig_speed = px.pie(speed_counts,
                           names='Speed Range',
                           values='Count',
                           hole=0.4,
                           template="plotly_white",
                           color='Speed Range',
                           color_discrete_map=color_map)  # Map ranges to colors

        # Transparent Background
        fig_speed.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            margin=dict(t=20, b=20, l=20, r=20),
        )
        # Remove the useless scale traces
        fig_speed.update_traces(textinfo="percent",
                                textposition="inside",
                                hoverinfo="label+value",
                                textfont_size=15)

        st.plotly_chart(fig_speed, width="stretch")