# tools.py - Updated for LangGraph ToolNode compatibility
from typing import Dict, Optional, Any
from pydantic import BaseModel, Field
from langchain_community.tools import DuckDuckGoSearchRun 
from datetime import datetime, timedelta
from pymongo import MongoClient
from bson import ObjectId
import os
from dotenv import load_dotenv
from langchain_core.tools import tool  # <-- MUST HAVE IMPORT
import requests
import yfinance as yf

load_dotenv()

# MongoDB connection
client = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017/"))
db = client["finvoice"]
expenses_collection = db["expenses"]
goals_collection = db["goals"]
# ------------------ SCHEMAS ------------------ #



class AddExpenseInput(BaseModel):
    """Schema for adding an expense"""
    user_id: str 
    amount: float = Field(..., description="The expense amount in Indian Rupees (₹)")
    category: str = Field(..., description="Category of the expense (food, travel, rent, etc.)")
    description: Optional[str] = Field(None, description="Optional description of the expense")

class QueryExpenseInput(BaseModel):
    """Schema for querying expenses"""
    user_id: str 
    category: Optional[str] = Field(None, description="Filter by category if provided")
    period_days: int = Field(30, description="Time window in days to fetch expenses")

# UPDATED SCHEMA FOR ENHANCED TOOL
class ExpenseSummaryInput(BaseModel):
    """Schema for generating expense summary with intelligent feedback"""
    user_id: str 
    period_days: int = Field(30, description="Time window in days to summarize (e.g., 7, 30, 90)")

class AddGoalInput(BaseModel):
    """Schema for adding a financial goal"""
    user_id: str 

# NEW SCHEMA FOR THE ENHANCED RESPONSE STRUCTURE
class ExpenseSummaryOutput(BaseModel):
    """Output schema for enhanced expense summary with feedback"""
    period: str
    total_spent: float
    currency: str
    average_daily_spend: float
    spending_by_category: Dict[str, float]
    category_percentages: Dict[str, float]
    transaction_count: int
    feedback: str  # <-- NEW: Personalized financial advice
    period_days: int



# ------------------ TOOLS (with @tool decorator) ------------------ #

@tool(args_schema=AddExpenseInput)  # <-- DECORATOR ADDED
def add_expense_tool(user_id: str, amount: float, category: str, description: Optional[str] = None) -> Dict[str, Any]:
    """
    Add an expense record to MongoDB for a user. All amounts are in Indian Rupees (₹).
    Returns a standardized response with status, data, and message.
    """
    try:
        # Input validation
        if amount <= 0:
            return {
                "status": "error",
                "data": None,
                "message": f"Failed to add expense: Amount must be positive. Received ₹{amount}."
            }
        
        expense = {
            "user_id": user_id,
            "amount": amount,
            "category": category.lower().strip(),  # Normalize category
            "description": description,
            "date": datetime.now(),
            "created_at": datetime.now()
        }
        
        result = expenses_collection.insert_one(expense)
        
        if result.acknowledged:
            return {
                "status": "success",
                "data": {
                    "expense_id": str(result.inserted_id),
                    "amount": amount,
                    "currency": "INR (₹)",
                    "category": category,
                    "description": description
                },
                "message": f"✅ Successfully added expense of ₹{amount} for '{category}'."
            }
        else:
            return {
                "status": "error",
                "data": None,
                "message": "Failed to add expense: Database write not acknowledged."
            }
            
    except Exception as e:
        return {
            "status": "error",
            "data": None,
            "message": f"Failed to add expense: {str(e)}"
        }

@tool(args_schema=QueryExpenseInput)  # <-- DECORATOR ADDED
def query_expenses_tool(user_id: str, category: Optional[str] = None, period_days: int = 30) -> Dict[str, Any]:
    """
    Fetch user expenses from MongoDB, optionally filtered by category and time period.
    Returns expenses in Indian Rupees (₹).
    """
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=period_days)

        query = {"user_id": user_id, "date": {"$gte": start_date, "$lte": end_date}}
        if category:
            query["category"] = category.lower().strip()  # Normalize for query

        expenses = list(expenses_collection.find(query, {"_id": 0}))
        
        # Convert datetime objects to strings for JSON serialization
        serializable_expenses = []
        for exp in expenses:
            exp_copy = exp.copy()
            for key, value in exp_copy.items():
                if isinstance(value, datetime):
                    exp_copy[key] = value.isoformat()
            serializable_expenses.append(exp_copy)

        total_amount = sum(exp.get("amount", 0) for exp in expenses)
        
        return {
            "status": "success",
            "data": {
                "expenses": serializable_expenses,
                "count": len(expenses),
                "total_amount": total_amount,
                "currency": "INR (₹)",
                "period_days": period_days,
                "category_filter": category
            },
            "message": f"Found {len(expenses)} expenses totaling ₹{total_amount} for the last {period_days} days."
        }
        
    except Exception as e:
        return {
            "status": "error",
            "data": None,
            "message": f"Failed to query expenses: {str(e)}"
        }

@tool(args_schema=ExpenseSummaryInput)
def expense_summary_tool(user_id: str, period_days: int = 30) -> Dict[str, Any]:
    """
    Generate a comprehensive summary of user expenses with personalized feedback 
    and recommendations. All amounts are in Indian Rupees (₹).
    """
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=period_days)

        expenses = list(expenses_collection.find({
            "user_id": user_id,
            "date": {"$gte": start_date, "$lte": end_date}
        }))

        if not expenses:
            return {
                "status": "success",
                "data": {"message": "No expenses found for this period."},
                "message": "You haven't recorded any expenses in the last {period_days} days. Great job saving! 💰"
            }

        # Calculate basic metrics
        total_spent = sum(exp.get("amount", 0) for exp in expenses)
        by_category = {}
        for exp in expenses:
            cat = exp.get("category", "Miscellaneous").lower()
            by_category[cat] = by_category.get(cat, 0) + exp.get("amount", 0)

        average_daily = total_spent / period_days if period_days > 0 else 0
        
        # Calculate percentage breakdown
        category_percentages = {}
        for category, amount in by_category.items():
            category_percentages[category] = (amount / total_spent) * 100

        # Generate intelligent feedback
        feedback = generate_spending_feedback(total_spent, by_category, category_percentages, period_days)

        return {
            "status": "success",
            "data": {
                "period": f"last {period_days} days",
                "total_spent": total_spent,
                "currency": "INR (₹)",
                "average_daily_spend": average_daily,
                "spending_by_category": by_category,
                "category_percentages": category_percentages,
                "transaction_count": len(expenses),
                "feedback": feedback,  # <-- NEW: Personalized feedback
                "period_days": period_days
            },
            "message": feedback  # Also in message for immediate display
        }
        
    except Exception as e:
        return {
            "status": "error",
            "data": None,
            "message": f"Failed to generate expense summary: {str(e)}"
        }


def generate_spending_feedback(total_spent: float, by_category: dict, category_percentages: dict, period_days: int) -> str:
    """
    Generate personalized spending feedback based on financial patterns.
    """
    feedback_points = []
    
    # Budget guidelines (customize these as needed)
    BUDGET_GUIDELINES = {
        "food": 30,       # 30% of income on food
        "transport": 15,  # 15% on transport
        "entertainment": 10,  # 10% on entertainment
        "shopping": 20,   # 20% on shopping
    }
    
    # 1. Overall spending feedback
    if total_spent == 0:
        return "Amazing! You haven't spent anything this period. Your savings must be growing! 🎉"
    
    # 2. Category-specific feedback
    for category, percentage in category_percentages.items():
        recommended_max = BUDGET_GUIDELINES.get(category, 25)  # Default 25% for other categories
        
        if percentage > recommended_max + 10:  # More than 10% over budget
            feedback_points.append(
                f"⚠️ You're spending {percentage:.1f}% on {category}, which is quite high. "
                f"Consider reducing {category} expenses to stay within a healthy budget."
            )
        elif percentage > recommended_max:  # Slightly over budget
            feedback_points.append(
                f"📊 Your {category} spending is {percentage:.1f}%, slightly above the recommended {recommended_max}%. "
                f"Keep an eye on this category."
            )
        elif percentage < recommended_max / 2:  # Very low spending
            feedback_points.append(
                f"✅ Great job keeping {category} expenses low at {percentage:.1f}%! "
                f"You're well under the {recommended_max}% guideline."
            )
    
    # 3. High-spending category warning
    highest_category = max(by_category.items(), key=lambda x: x[1]) if by_category else None
    if highest_category and by_category[highest_category[0]] > total_spent * 0.4:  # >40% on one category
        feedback_points.append(
            f"🚨 {highest_category[0].title()} is your largest expense category at {category_percentages[highest_category[0]]:.1f}%. "
            f"This might be worth reviewing for potential savings."
        )
    
    # 4. General recommendations
    if total_spent > 50000:  # Example threshold
        feedback_points.append("💡 You're spending quite significantly. Consider tracking specific budgets for each category.")
    elif total_spent < 10000:
        feedback_points.append("🌟 Excellent budgeting! Your spending is very controlled and mindful.")
    
    # 5. Add positive reinforcement
    if not feedback_points:  # If everything looks good
        feedback_points.append("✅ Your spending patterns look healthy and balanced across categories! Keep it up! 🎉")
    
    # Compile final feedback
    base_message = f"📈 In the last {period_days} days, you spent ₹{total_spent:,.2f} across {len(by_category)} categories. "
    
    if feedback_points:
        return base_message + " " + " ".join(feedback_points)
    else:
        return base_message + "Your spending patterns look balanced."
    

@tool(args_schema=AddGoalInput)  # <-- DECORATOR ADDED
def add_goal_tool(user_id: str, goal_text: str) -> Dict[str, Any]:
    """
    Add a financial goal for the user to MongoDB.
    """
    try:
        goal = {
            "user_id": user_id,
            "goal_text": goal_text,
            "advice_given": False,
            "created_at": datetime.now()
        }
        
        result = goals_collection.insert_one(goal)
        
        if result.acknowledged:
            return {
                "status": "success",
                "data": {
                    "goal_id": str(result.inserted_id),
                    "goal_text": goal_text
                },
                "message": f"🎯 Goal '{goal_text}' added successfully! You can do it! 💪"
            }
        else:
            return {
                "status": "error",
                "data": None,
                "message": "Failed to add goal: Database write not acknowledged."
            }
            
    except Exception as e:
        return {
            "status": "error",
            "data": None,
            "message": f"Failed to add goal: {str(e)}"
        }

@tool
def get_stock_price(symbol: str) -> dict:
    """
    Fetch latest stock price for a given symbol (e.g. 'AAPL', 'TSLA') 
    using Alpha Vantage with API key in the URL.
    """
    url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey=T2XO8HVZE5ISME5Q"
    r = requests.get(url)
    return r.json()


@tool
def get_stock_info(symbol: str) -> dict:
    """
    Fetch the latest stock price and basic info for a given symbol (e.g. 'AAPL', 'TSLA').
    Uses yfinance (no API key required).
    """
    try:
        stock = yf.Ticker(symbol)
        hist = stock.history(period="5d")  # today's data
        price = hist['Close'].iloc[-1] if not hist.empty else None
        info = stock.info

        return {
            "symbol": symbol.upper(),
            "price": price,
            "longName": info.get("longName"),
            "sector": info.get("sector"),
            "marketCap": info.get("marketCap"),
            "currency": info.get("currency"),
        }
    except Exception as e:
        return {"error": str(e)}
    
   
from langchain_community.utilities import GoogleSerperAPIWrapper
serper = GoogleSerperAPIWrapper()
@tool


def search_with_serper(query: str) -> str:
    """
    Perform a live web search using the Serper.dev API (Google Search).
    
    Why use this tool?
    - Fetches up-to-date information and breaking news not available in your own database.
    - Ideal for retrieving current market updates, stock news, company announcements, and answering open-ended questions.
    - Useful for fact-checking, enriching responses with the latest info, and discovering web sources outside pre-trained data.
    - Supports searching in specific languages and regions. Can return web results, news articles, images, and more.
    
    When to use:
    - The user asks about recent news, global or local events, trending queries, or real-time financial/market data.
    - Examples: "What's the latest update on mutual funds?", "Show me today's stock news", "Recent market headlines", "Who won the award yesterday?"
    """
    return serper.run(query)
    


# ------------------ TOOL REGISTRY (Optional) ------------------ #

# The @tool decorator automatically registers them with LangChain/LangGraph
# But you can keep this registry if you need it for other purposes
TOOLS = {
    "add_expense": add_expense_tool,
    "query_expenses": query_expenses_tool,
    "expense_summary": expense_summary_tool,
    "spending_feedback":generate_spending_feedback,
    "add_goal": add_goal_tool,
    "get_stock_price":get_stock_info,
    "stock_price":get_stock_price,
    "web_search":search_with_serper
}