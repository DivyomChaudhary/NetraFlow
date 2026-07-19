import streamlit as st
import pandas as pd
import sqlite3
import os
import boto3
from dotenv import load_dotenv

st.set_page_config(page_title="NetraFlow", page_icon="👁",layout="wide")

st.subheader("🖼️ Object Vault")
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

# Force the loader to look in the parent directory (project root)
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
load_dotenv(os.path.join(project_root, '.env'))
db_path = os.path.join(project_root, "logs_", "traffic_security.db")
db_uri = f"file:{db_path}?mode=ro"

# 1. Fetch data
conn = sqlite3.connect(db_uri, uri=True, timeout=10)
df = pd.read_sql_query("SELECT * FROM vehicle_logs WHERE is_suspicious = 1", conn)
conn.close()

def get_presigned_url(s3_key):
    s3_client = boto3.client(
            's3',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY'),
            aws_secret_access_key=os.getenv('AWS_SECRET_KEY')
    )
    return s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': os.getenv('BUCKET_NAME'), 'Key': s3_key},
            ExpiresIn=600  # URL expires in 10 mins
    )


# 2. Check if data exists BEFORE defining columns
if df.empty:
    st.info("No suspicious activity recorded yet. S3 gallery is empty.")
else:
    # DEFINING COLS HERE ensures it is resolved before the loop starts
    cols = st.columns(3)

    for idx, row in df.iterrows():
        # Using modulo (%) ensures we cycle through cols[0], cols[1], cols[2]
        col_index = idx % 3

        with cols[col_index]:
            bucket = os.getenv('BUCKET_NAME')
            file_key = row.get('s3_key', None)  # .get prevents crash if column missing

            if file_key:
                img_url = get_presigned_url(file_key)
                st.image(img_url, width='stretch')
                st.caption(f" {row['color']} {row['type']} | {row['timestamp']}")
            else:
                st.warning(f"No image key for ID {row['vehicle_id']}")