import streamlit as st
import requests
import uuid

# --- Session ID ---
if "session_id" not in st.session_state:
    st.session_state["session_id"] = str(uuid.uuid4())

if "message_history" not in st.session_state:
    st.session_state["message_history"] = []

st.set_page_config(page_title="FinAgent: AI Financial Assistant", page_icon="💸", layout="wide")

# --- HEADER ---
st.title("FinAgent 💸")
st.markdown("#### Your personal AI-powered financial assistant for tracking expenses, setting goals, and smart money insights!")

# --- SIDEBAR ---
with st.sidebar:
    st.header("About this Project")
    st.markdown("""
    - **Tech Stack:** LangGraph, LangChain, FastAPI, MongoDB, Streamlit  
    - **Features:** Expense tracking, goals, intelligent summaries  
    - [See on LinkedIn](https://www.linkedin.com/in/ujwalmahajan777/)
    """)
    st.header("Try these examples:")
    st.write("- Add an expense (e.g., *I spent 200 rupees on groceries*)")
    st.write("- Set a savings goal (e.g., *I want to save 5000 this month*)")
    st.write("- Show my last month summary")
    st.write("- What's my biggest spending category?")
    st.info("Just type your query below and press Enter!")

# --- CHAT INTERFACE ---
st.divider()
st.subheader("💬 Chat with FinAgent")

def stream_response(prompt):
    response = requests.post(
        "https://finagent-nw1v.onrender.com/chat",
        json={
            "input": prompt,
            "session_id": st.session_state["session_id"]
        },
        stream=True
    )
    buffer = ""
    for chunk in response.iter_content(chunk_size=None):
        token = chunk.decode("utf-8")
        buffer += token
        yield token

# Show chat history
for message in st.session_state["message_history"]:
    with st.chat_message(message["role"]):
        if message["role"] == "assistant":
            st.markdown(f":sparkles: {message['content']}")
        else:
            st.markdown(f"**You:** {message['content']}")

user_input = st.chat_input("Type your financial query here...")

if user_input:
    st.session_state["message_history"].append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(f"**You:** {user_input}")
    with st.chat_message("assistant"):
        # --- FIXED streaming container code ---
        assistant_text = ""
        stream_container = st.empty()
        for streamed_token in stream_response(user_input):
            assistant_text += streamed_token
            stream_container.markdown(f":sparkles: {assistant_text}")
        st.session_state["message_history"].append({"role": "assistant", "content": assistant_text})

st.markdown("---")
st.caption("FinVoice Project • Built with LangGraph, LangChain, FastAPI, Streamlit • [GitHub](https://github.com/Ujwalmahajan777)")
