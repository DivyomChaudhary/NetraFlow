import streamlit as st
import pandas as pd
import sqlite3
import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_experimental.tools import PythonAstREPLTool
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
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


@st.cache_data
def load_data():
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query("SELECT * FROM vehicle_logs", conn)
    conn.close()
    return df


df = load_data()


# --- LangGraph Setup ---
class State(TypedDict):
    messages: Annotated[list, add_messages]

tool = PythonAstREPLTool(locals={"df": df})
llm = ChatGroq(model_name="llama-3.3-70b-versatile", groq_api_key=st.secrets["GROQ_API_KEY"])
llm_with_tools = llm.bind_tools([tool])

system_message = {
    "role": "system",
    "content": "You are a traffic data expert. You have access to a pandas DataFrame named 'df'. Make the conversation abstract and do not mention any underlying variable names like df in the conversation, just pure data and facts"
               "Always use the 'python_repl' tool to inspect 'df' when asked about vehicle logs, counts, or data contents."
}

def chatbot(state: State):
    messages = [system_message] + state["messages"]
    return {"messages": [llm_with_tools.invoke(messages)]}

graph_builder = StateGraph(State)
graph_builder.add_node("chatbot", chatbot)
graph_builder.add_node("tools", ToolNode([tool]))
graph_builder.add_edge(START, "chatbot")
graph_builder.add_conditional_edges("chatbot", lambda state: "tools" if state["messages"][-1].tool_calls else END)
graph_builder.add_edge("tools", "chatbot")
graph = graph_builder.compile()

# --- Memory Management ---
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- Chat Interaction ---
if prompt := st.chat_input("Enter your question"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.spinner('🔍 Analyzing traffic logs...'):
        # Pass the messages correctly formatted
        response = graph.invoke({"messages": st.session_state.messages})
        output_text = response["messages"][-1].content

        st.session_state.messages.append({"role": "assistant", "content": output_text})
        with st.chat_message("assistant"):
            st.markdown(output_text)