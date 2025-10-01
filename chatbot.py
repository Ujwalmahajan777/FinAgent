# chatbot.py - Fixed version with proper tool binding
import speech_recognition as sr
import tempfile
import os
import sqlite3
from gtts import gTTS
import pygame
from typing import TypedDict, Annotated

from langgraph.graph import StateGraph, START, END
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.checkpoint.mongodb import MongoDBSaver
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from dotenv import load_dotenv
from pymongo import MongoClient
import os


# Import your tools - THEY MUST BE @tool DECORATED
from tool import add_expense_tool, query_expenses_tool, expense_summary_tool, add_goal_tool ,generate_spending_feedback,get_stock_price,search_with_serper

load_dotenv()

# -------------------
# 1. LLM with Tools
# -------------------
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# Create tools list and bind to LLM
tools = [add_expense_tool, query_expenses_tool, expense_summary_tool, add_goal_tool,generate_spending_feedback,get_stock_price,search_with_serper]
llm_with_tools = llm.bind_tools(tools)  # <- CRITICAL: This enables tool calling

# -------------------
# 2. State
# -------------------
class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

# -------------------
# 3. Nodes
# -------------------
def chat_node(state: ChatState):
    """LLM node that may answer or request a tool call."""
    messages = state["messages"]
    response = llm_with_tools.invoke(messages)  # <- Use the tool-enabled LLM
    return {"messages": [response]}

tool_node = ToolNode(tools)


# -------------------
# 5. MongoDB Checkpointer - CORRECT IMPLEMENTATION
# -------------------
from pymongo import MongoClient
from langgraph.checkpoint.mongodb import MongoDBSaver

MONGODB_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = "finvoice"

client = MongoClient(MONGODB_URI)
checkpointer = MongoDBSaver(client[DB_NAME], "graph_checkpoints")
    
    

# -------------------
# 6. Graph Construction
# -------------------
graph = StateGraph(ChatState)
graph.add_node("chat_node", chat_node)
graph.add_node("tools", tool_node)

graph.add_edge(START, "chat_node")
graph.add_conditional_edges("chat_node", tools_condition)
graph.add_edge("tools", "chat_node")

agent = graph.compile(checkpointer=checkpointer)

# -------------------
# 7. Main Execution Loop
# -------------------

from langchain_core.messages import HumanMessage, SystemMessage

def process_input_stream(user_text: str,session_id:str):
    system_message = SystemMessage(content="""You are FinVoice, a helpful AI assistant. The current user's ID is always available as thread_id in your configuration.
Whenever you call any tool, always set user_id = thread_id (you do not need to ask the user).""")
    input_payload = {
        "messages": [system_message, HumanMessage(content=user_text)]
    }
    config = {"configurable": {"thread_id": session_id, "checkpoint_ns": "finvoice_ai"}}
    try:
        for message_chunk, metadata in agent.stream(input_payload, config=config, stream_mode="messages"):
            content = getattr(message_chunk, "content", None)
            if content:
                yield content
    except Exception as e:
        yield "Error during streaming: " + str(e)

if __name__ == "__main__":
    from langchain_core.messages import HumanMessage, SystemMessage

    def run_stream_in_terminal():
        print("FinVoice: Streaming Chatbot\nType 'exit' to quit.\n")
        while True:
            user_text = input("You: ").strip()
            if user_text.lower() in {"exit", "quit"}:
                print("Goodbye!")
                break

            system_message = SystemMessage(content="""You are FinVoice, an expert AI financial assistant for Indian users.

Core Instructions:

For every user interaction, your core goal is to be clear, friendly, and professional.

Always keep data private: only use the current session’s ID (thread_id from your configuration) for all actions on behalf of this user. Never leak information between users or sessions.

If a user asks for their name, transactional, or goal history, use only their own data (from their current session/user id).

Never ask the user for their user ID; you already have it as thread_id in your config context.

On Tool Usage:

Use the built-in tools (add_expensetool, query_expensestool, expense_summary_tool, add_goal_tool, and others) as needed, always passing user_id=thread_id automatically in every tool call.

When a tool returns data, never show raw code, JSON, or technical fields. Instead, always summarize or rephrase results conversationally, naturally, and helpfully.

For summaries, highlight total spending, categories, and give actionable feedback in simple language.

Conversational Behavior:

Answer followup questions naturally, as a real assistant would.

Offer insights, suggestions, or ask clarifying questions—but don't require extra info if not needed.

Respect user privacy and don’t mention implementation/technical details.

General:

All responses should be easy for a layperson to understand, concise, and relevant to the query.

Amounts and currency are always in Indian Rupees (₹).

If unsure or when data is not found, explain helpfully what actions the user can take.

Examples of Tone:

Instead of raw data, say:
"In the last 30 days, you spent ₹6300—mainly on food and travel. Great job managing your entertainment budget!"

When adding an expense/goal:
"Got it—I've added your expense. Would you like to see your updated spending summary or set a new goal?""")

            input_payload = {
                "messages": [system_message, HumanMessage(content=user_text)]
            }
            config = {"configurable": {"thread_id": "demo_user", "checkpoint_ns": "finvoice_ai"}}

            try:
                print("AI: ", end="", flush=True)
                # This is the recommended streaming pattern per docs and your version
                for message_chunk, metadata in agent.stream(input_payload, config=config, stream_mode="messages"):
                    content = getattr(message_chunk, "content", None)
                    if content:
                        print(content, end="", flush=True)
                print()  # For new line after streaming output
            except Exception as e:
                print("\nError during streaming:", str(e))