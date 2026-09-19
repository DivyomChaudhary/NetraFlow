import streamlit as st
import pandas as pd
import sqlite3
import os
import json
from dotenv import load_dotenv
from groq import Groq
from pydantic import BaseModel, ConfigDict

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
    h1, h2, h3, h4, h5, h6 {
        color: #1A202C !important;
    }
    [data-testid="stMetricLabel"] {
        color: #4A5568 !important;
    }
    [data-testid="stMetricValue"] {
        color: #2D3748 !important;
    }
    [data-testid="stSidebarNav"] span {
        color: #2D3748 !important;
        font-weight: 500;
    }
    </style>
    """, unsafe_allow_html=True)

st.set_page_config(page_title="NetraFlow", page_icon="👁", layout="wide")
st.title("Ask AI")

# --- Database Setup ---
db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "logs_", "traffic_security.db")
db_uri = f"file:{db_path}?mode=ro"

TABLE_NAME = "vehicle_logs"


@st.cache_data
def load_schema():
    """Read the real column names/types from the db so the model never guesses them."""
    conn = sqlite3.connect(db_uri, uri=True, timeout=5)
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({TABLE_NAME})")
    columns = cursor.fetchall()  # (cid, name, type, notnull, dflt_value, pk)
    conn.close()
    return [{"name": c[1], "type": c[2]} for c in columns]


@st.cache_data
def load_data():
    conn = sqlite3.connect(db_uri, uri=True, timeout=5)
    df = pd.read_sql_query(f"SELECT * FROM {TABLE_NAME}", conn)
    conn.close()
    return df


if not os.path.exists(db_path):
    st.error(f"Database not found at: {db_path}")
    st.stop()

schema = load_schema()
df = load_data()
schema_str = "\n".join(f"- {c['name']} ({c['type']})" for c in schema)

# --- Groq client (uses GROQ_API_KEY from your .env / environment) ---
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

MODEL = "openai/gpt-oss-120b"


class SQLQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")  # required so Groq's strict JSON-schema mode accepts it
    can_answer: bool  # False when the question can't be answered from this table
    sql: str          # empty string when can_answer is False
    explanation: str  # if can_answer is False, a short friendly reason instead


def build_history_context(history: list, max_turns: int = 4) -> str:
    """Summarize recent Q&A turns so follow-up questions (e.g. 'what about white ones?')
    have something to refer back to."""
    if not history:
        return ""
    lines = ["Recent conversation, for context on follow-up questions (most recent last):"]
    for turn in history[-max_turns:]:
        lines.append(f"- Q: {turn['question']}")
        if turn["can_answer"]:
            lines.append(f"  A: ran `{turn['sql']}` -- {turn['explanation']}")
        else:
            lines.append(f"  A: could not be answered -- {turn['explanation']}")
    return "\n".join(lines)


def generate_sql(question: str, history: list) -> SQLQuery:
    history_context = build_history_context(history)

    system_prompt = f"""You are a SQL expert working with a single SQLite table.

Table: {TABLE_NAME}
Columns:
{schema_str}

Rules:
- Only ever write a single read-only SELECT statement against the {TABLE_NAME} table.
- Never write INSERT, UPDATE, DELETE, DROP, ALTER, ATTACH, PRAGMA or any statement that
  is not a SELECT.
- Use only the columns listed above; do not invent columns or tables.
- Keep the query as simple as possible while still answering the question.
- The user may ask short follow-up questions that only make sense given the recent
  conversation below (e.g. "what about white ones?" after asking about black cars).
  Use that context to write a complete, standalone SQL query for the current question.

If the question cannot be answered by querying this table -- for example it asks about
who you are, how you were built, unrelated general knowledge, or anything with no
relationship to vehicle/traffic/security log data -- set can_answer to false, leave sql
as an empty string, and put a short, friendly, one- or two-sentence explanation of what
this tool can help with instead in the explanation field. Do not try to force an answer
with irrelevant or empty SQL.

{history_context}
"""

    response = client.chat.completions.create(
        model=MODEL,
        temperature=0,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "sql_query",
                "strict": True,
                "schema": SQLQuery.model_json_schema(),
            },
        },
    )
    raw = response.choices[0].message.content
    return SQLQuery.model_validate(json.loads(raw))


def is_safe_select(sql: str) -> bool:
    """Belt-and-braces guard on top of the read-only sqlite connection."""
    lowered = sql.strip().lower()
    forbidden = ("insert", "update", "delete", "drop", "alter", "attach", "pragma", "create")
    return lowered.startswith("select") and not any(k in lowered for k in forbidden)


def run_query(sql: str) -> pd.DataFrame:
    conn = sqlite3.connect(db_uri, uri=True, timeout=5)
    try:
        return pd.read_sql_query(sql, conn)
    finally:
        conn.close()


# --- UI ---
with st.expander("Preview loaded data"):
    st.dataframe(df.head(20), use_container_width=True)

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []  # list of dicts, one per Q&A turn

if st.session_state.chat_history:
    if st.button("🗑️ Clear conversation"):
        st.session_state.chat_history = []
        st.rerun()


def render_answer(turn: dict):
    """Renders one assistant turn the same way whether it's replayed from
    history or just generated, so past and new answers look identical."""
    if not turn["can_answer"]:
        st.info(
            f" {turn['explanation']}\n\n"
            "Try something like *\"How many vehicles were flagged as "
            "suspicious today?\"* or *\"What's the average speed of trucks?\"*"
        )
        return

    st.markdown(f"*{turn['explanation']}*")
    result_df = turn["result_df"]

    if result_df.shape == (1, 1):
        label = result_df.columns[0].replace("_", " ").title()
        value = result_df.iloc[0, 0]
        if isinstance(value, float):
            value = round(value, 2)
        st.metric(label=label, value=value)
    elif result_df.empty:
        st.info("No matching records found for that question.")
    else:
        n = len(result_df)
        st.caption(f"{n} result{'s' if n != 1 else ''} found")
        st.dataframe(result_df, use_container_width=True, hide_index=True)

    with st.expander("🔍 View the generated SQL query"):
        st.code(turn["sql"], language="sql")


# Replay the conversation so far
for turn in st.session_state.chat_history:
    with st.chat_message("user"):
        st.write(turn["question"])
    with st.chat_message("assistant"):
        render_answer(turn)

# st.chat_input submits on Enter natively (no separate button needed) and
# clears itself automatically after each question.
question = st.chat_input("Ask a question about your traffic/security logs...")

if question:
    with st.chat_message("user"):
        st.write(question)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                result = generate_sql(question, st.session_state.chat_history)

                turn = {
                    "question": question,
                    "can_answer": result.can_answer,
                    "sql": result.sql,
                    "explanation": result.explanation,
                    "result_df": None,
                }

                if result.can_answer and not is_safe_select(result.sql):
                    turn["can_answer"] = False
                    turn["explanation"] = (
                        "I generated something that wasn't a safe, read-only query, "
                        "so I didn't run it. Try rephrasing your question."
                    )
                elif result.can_answer:
                    turn["result_df"] = run_query(result.sql)

                render_answer(turn)
                st.session_state.chat_history.append(turn)

            except json.JSONDecodeError:
                st.error("The model didn't return valid JSON. Please try rephrasing your question.")
            except sqlite3.Error as e:
                st.error(f"The generated SQL failed against the database: {e}")
            except Exception as e:
                st.error(f"Something went wrong: {e}")