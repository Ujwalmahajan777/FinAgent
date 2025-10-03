
FinAgent
FinAgent is an agentic, autonomous financial intelligence system, built for anyone interested in AI, tech, and real-world automation.

🧠 How FinAgent Works: Agentic Workflow
See a visual workflow of FinAgent’s mechanism here:
FinAgent Agentic Workflow ([click here for workflow](https://drive.google.com/file/d/1czSsVaLJ2hWAwixDMiEtsPQTehPB-Mhg/view?usp=drive_link))

Project Functionality (Explained via Workflow)
User Interaction:
Users interact via a web UI or API, submitting natural language queries (like adding expenses, setting goals, checking stock info, or web searches).

Agent Core:

Implemented using LangChain and LangGraph for reasoning and workflow orchestration.

The agent interprets the query, classifies the task, and autonomously selects the correct tool/resource.

Task Routing and Resource Usage:

Expense & Goal Management:
Uses MongoDB for secure, persistent storage and queries.

Stock Market Data:
Fetches real-time prices/news via yFinance and AlphaVantage APIs.

Web Search:
Utilizes the Serper.dev API to search for trending news and information.

Agentic Decider:
The agent selects and orchestrates these tools dynamically—no hardcoded logic.

Results Handling:

The agent collects responses, formats them, and delivers user-friendly results via the interface.

🛠 Technology Mapping
Task Type	Tech Used	What It Does
Expense/Goal Mgmt	MongoDB	Stores, retrieves, and summarizes transactions/goals
Stock Data	yFinance / AlphaVantage	Calls API for real-time market info
Web Search	Serper.dev API (prebuilt tool)	Gets latest news, answers, or trending content
Agentic Core	LangChain, LangGraph	Orchestrates reasoning, logic, and tool selection
User Interaction	Streamlit, FastAPI	Chat & API interfaces for easy access
🌟 What Makes FinAgent Special
Agentic Intelligence:
The system is not just a set of functions—it’s an autonomous agent that understands user intent and orchestrates tools as needed.

Flexible & Extensible:
Easily integrate additional tools or APIs with minimal changes.

Real Utility:
Automates typical financial activities and live data retrieval in one AI-driven package.

⚡ Quickstart
Clone and install dependencies:

bash
git clone https://github.com/YOUR_USERNAME/finagent.git
cd finagent
pip install -r requirements.txt
Add configuration for API keys in a .env file

Start the interface:

bash
streamlit run streamlit.py
or

bash
uvicorn main:app --reload
🤝 Contributing & License
Open to all contributors; fork, branch, and send a PR.
