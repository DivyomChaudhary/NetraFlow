import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
from datetime import datetime

# --- Page Config ---
st.set_page_config(page_title="NetraFlow", page_icon="👁",layout="wide")
st.sidebar.title("👁 NetraFlow")
st.sidebar.write("Traffic-Aware Security Platform")
st.title("Traffic Security Analytics")
st.markdown("Real-time insights from Edge AI and AWS S3 integration")
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
    
    /* 3. Specifically Target Headers */
    h1, h2, h3, h4, h5, h6 {
        color: #1A202C !important;
    }

    /* 4. Fix Metric Labels & Values (The blue/white issue) */
    [data-testid="stMetricLabel"] {
        color: #4A5568 !important; /* Muted dark gray */
    }
    [data-testid="stMetricValue"] {
        color: #2D3748 !important; /* Bold dark gray */
    }

    /* 5. Make the Sidebar text dark if the background is light */
    [data-testid="stSidebarNav"] span {
        color: #2D3748 !important;
        font-weight: 500;
    }
    </style>
    """, unsafe_allow_html=True)

# --- Database Connection ---
def load_data():
    # Ensure this path matches your SecuritySystem db_path
    conn = sqlite3.connect('logs_/traffic_security.db')
    df = pd.read_sql_query("SELECT * FROM vehicle_logs", conn)
    # Convert timestamp to datetime objects for plotting
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    conn.close()
    return df

try:
    df = load_data()
except Exception as e:
    st.error(f"Could not connect to database: {e}")
    st.stop()

# --- Top Level Metrics ---
total_v = len(df)
suspicious_v = len(df[df['is_suspicious'] == 1])
hazard_rate = (suspicious_v / total_v * 100) if total_v > 0 else 0

m1, m2, m3 = st.columns(3)
m1.metric("Total Vehicles Tracked", total_v)
m2.metric("Security Alerts", suspicious_v, delta_color="inverse")
m3.metric("Suspicion Rate", f"{hazard_rate:.1f}%")

st.divider()

# --- Plotly Insights ---
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Traffic Volume Over Time")
    # Resample to count vehicles per minute/hour
    time_data = df.resample('5s', on='timestamp').count().reset_index()
    fig = px.bar(time_data,
                 x='timestamp',
                 y='id',
                 color='id',
                 color_continuous_scale=px.colors.sequential.Sunsetdark,  # Vibrant Saffron/Purple/Blue
                 title="Traffic Density Analysis",
                 template="presentation")

    fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig, width='stretch')

with col_right:
    st.subheader("Detected Vehicle Colors")
    color_counts = df['color'].value_counts().reset_index()
    # Use actual colors for the pie chart slices!
    fig_pie = px.pie(color_counts, names='color', values='count',
                     template="plotly_dark",
                     hole=0.4,
                     color='color',
                     color_discrete_map={
                         'red': 'red', 'black': 'black', 'white': 'white',
                         'silver': 'silver', 'blue': 'blue', 'green': 'green',
                         'grey':'grey', 'yellow': 'yellow'
                     })
    fig_pie.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig_pie, width='stretch')

    st.divider()
    st.divider()
    st.write("Credits")
    st.write("https://www.vecteezy.com/free-videos/car-pulling-over")
    st.write("https://www.vecteezy.com/free-videos/traffic")