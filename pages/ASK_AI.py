import streamlit as st
import pandas as pd
import sqlite3
import os
from dotenv import load_dotenv
from groq import Groq
from pydantic import BaseModel
import json
from typing import Annotated, TypedDict

load_dotenv()
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

st.set_page_config(page_title="NetraFlow", page_icon="👁", layout="wide")
st.title('ASK AI')

# --- Styles (Kept as you had them) ---
st.markdown("""<style>/* ... your existing CSS ... */</style>""", unsafe_allow_html=True)

# --- Database Setup ---
db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "logs_", "traffic_security.db")
db_uri = f"file:{db_path}?mode=ro"

@st.cache_data
def load_data():
    conn = sqlite3.connect(db_uri, uri=True, timeout=5)
    df = pd.read_sql_query("SELECT * FROM vehicle_logs", conn)
    conn.close()
    return df

df = load_data()

client = Groq()

class ValidationStatus(BaseModel):
    is_valid: bool
    syntax_errors: list[str]

response = client.chat.completions.create(
    model="openai/gpt-oss-120b",
    messages=[
        {
            "role": "system",
            "content": "You are a SQL expert. Generate structured SQL queries from natural language descriptions with proper syntax validation and metadata.",
        },
        {"role": "user", "content": "Find all customers who made orders over $500 in the last 30 days, show their name, email, and total order amount"},
    ],
