import streamlit as st
import pandas as pd
import sqlite3
import os

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

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
db_path = os.path.join(project_root, "logs_", "traffic_security.db")
db_uri = f"file:{db_path}?mode=ro"

# --- Database Connection ---
def load_data():
    # Ensure this path matches your SecuritySystem db_path
    conn = sqlite3.connect(db_uri, uri=True, timeout=5)
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

st.set_page_config(page_title="NetraFlow", page_icon="👁",layout="wide")
# --- Filtered Data Table ---
st.subheader("Recent Security Logs")
search_query = st.text_input("Search by Type or Color (e.g., 'red truck')")

display_df = df.sort_values(by='timestamp', ascending=False)
if search_query:
    keywords = search_query.lower().split()
    mask = display_df.apply(lambda row: all(
        word in str(row['type']).lower() or word in str(row['color']).lower()
        for word in keywords
    ), axis=1)

    display_df = display_df[mask]

st.dataframe(display_df[['timestamp', 'vehicle_id', 'type', 'color', 'is_suspicious']],
             width='stretch',
             hide_index=True,
             )