# Monday.com BI Agent

This repository contains a lightweight Python-based Business Intelligence (BI) agent that connects directly to a Monday.com account. Executives and founders can ask conversational questions about their  boards, and the agent fetches live data, reasons through the query, and returns a clear answer with a transparent reasoning trace.


---

## 🚀 Features

- **Live data access** – no caching or offline storage; all responses are based on real-time Monday.com API queries.
- **Dynamic schema discovery** – the agent first requests the board's column definitions and adapts to the current column names/IDs automatically.
- **Data quality awareness** – null or missing values are detected; caveats are appended to answers when data is incomplete.
- **Transparent reasoning** – every API call and decision step is shown to the user via a collapsible "trace" panel.
- **Response style toggle** – choose between a **Straight Forward** or **Informative** output mode.
- **Follow‑up suggestions** – after answering a question, the agent proposes related queries you might ask next.

## 📁 Repository Contents

Below is a breakdown of every file in this project:

| File | Purpose |
|------|---------|
| `agent.py` | **Agent core**: Implements the reasoning loop, integrates with Groq for tool-calling, enforces the system prompt rules, tracks data quality, and generates follow-up suggestions. |
| `app.py` | **Streamlit UI**: Manages the web interface, session state, user input/output, tone selection, and displays reasoning traces. |
| `config.py` | **Configuration**: Loads and validates required environment variables (`GROQ_API_KEY`, `MONDAY_API_TOKEN`) and raises errors if they're missing. |
| `data_quality.py` | **Data analysis helpers**: Contains functions to inspect sample rows from Monday.com and generate caveats about null or inconsistent values. |
| `monday_api.py` | **API wrapper**: Provides simple functions (`fetch_boards`, `get_board_schema`, `query_board_data`) that call the Monday.com GraphQL API. |
| `requirements.txt` | Lists the Python packages needed to run the application. |
| `README.md` | This file - setup and usage instructions. |

> There is intentionally **no tests or extra documentation** included in this version; previous development notes were removed to keep the submission focused on core functionality.

## 🛠 Setup

### For Local Development

1. **Download the source code**
   Extract the ZIP file you received.

2. **Create a Python virtual environment** (optional but recommended):
   ```bash
   python -m venv venv
   .\venv\Scripts\activate   # Windows
   # source venv/bin/activate  # macOS/Linux
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Create the .env file** ⚠️ IMPORTANT
   
   You MUST create a `.env` file with your API keys. This file is not included in the repository for security reasons.
   
   ```bash
   # Copy the template
   cp .env.example .env
   ```
   
   Then edit `.env` and add your actual API keys:
   ```text
   GROQ_API_KEY=gsk_abc123xyz...
   MONDAY_API_TOKEN=eyJ...
   ```
   
   **Where to get these keys:**
   - **GROQ_API_KEY**: Create a free account at [console.groq.com](https://console.groq.com/keys)
   - **MONDAY_API_TOKEN**: Log into Monday.com, go to Account → API Tokens, and create a new token

5. **Run the app locally**
   ```bash
   streamlit run app.py
   ```
   A browser window will open at `http://localhost:8501`.

### For Streamlit Cloud Deployment

If deploying to Streamlit Cloud, you do NOT need to create a `.env` file. Instead:

1. Upload the code to GitHub (excluding your local `.env` file)
2. Deploy on [share.streamlit.io](https://share.streamlit.io)
3. Add your API keys in the app's **Settings → Secrets** section

```toml
GROQ_API_KEY = "your_groq_key_here"
MONDAY_API_TOKEN = "your_monday_token_here"
```

### 📋 Monday.com Board Setup

For the agent to work, your Monday.com account must have at least one board with data. The agent is designed to work with boards containing business data (deals, work orders, projects, etc.).

**Option 1: Use Your Existing Boards**
If you already have boards in your Monday.com account, you're ready to go! The agent will automatically discover them when you ask questions.

**Option 2: Import Sample Data**
Two sample Excel files are included that you can import into Monday.com:
- `Deal funnel Data.xlsx` - A sales pipeline/deals board
- `Work_Order_Tracker Data.xlsx` - A work order tracking board

To import these files:
1. Log into Monday.com
2. Click the **+** button in your workspace → **Import** → **From file**
3. Select the Excel file and follow the import wizard
4. Name your board (e.g., "Deals Pipeline" or "Work Orders")
5. Repeat for the second file if desired

Once imported, you can ask questions like:
- "How many deals are in the pipeline?"
- "What is the total value of all deals by owner?"
- "How many work orders are pending?"

## 💡 Usage

- Enter any business question about your Monday.com data in the chat input, for example:
  - "How many active work orders do we have this month?"
  - "What is the total pipeline value by owner?"
  - "Show me the average completion time for tickets in the IT board."
- The agent will display its thinking trace while it fetches schemas and data.
- View the final answer and any follow-up questions suggested below the response.
- Use the sidebar to switch output tone or clear the conversation.

### 📝 Quick Example Walkthrough

Here's what happens when you ask a question:

**You ask:** "How many deals are in the pipeline?"  
**Agent thinks:**
  1. 🔍 Fetches all boards to find the Deals Pipeline
  2. 📋 Requests the board's schema (column names, types)
  3. 📊 Queries the board for items (up to 30 sample rows + total count)
  4. 🧮 Analyzes the data for quality issues (null values, etc.)
  5. ✍️ Formulates the answer

**You see:**
  - Inline status updates: "Calling Tool: `query_board_data(...)`"
  - The final answer: "There are **487** deals in the pipeline."
  - A caveat if needed: "⚠️ Note: 15% of deals are missing a close date."
  - Follow-up suggestions to explore further

### Important rules observed by the agent

The system prompt (inside `agent.py`) enforces several rules to guarantee accuracy:
- Queries must fetch board schema before pulling data.
- Counts use `total_items_on_board` rather than sample length.
- Null values are skipped and reported; percentages always use the total count.
- Ambiguous questions trigger schema review or clarification.
- Data is never hallucinated; if uncertain, the agent will ask for clarification.

## 🛑 Current Limitations

While the agent meets the core requirements, there are a few known constraints:

* **API setup**
  * Requires valid Monday.com and Groq keys; no automated onboarding flow or key rotation logic. A mis‑typed token causes a hard failure on startup.
  * Only two boards (Deals Pipeline and Work Orders) are assumed; queries about other boards will fail unless you modify `agent.py` logic or extend the tool set.
  * The `query_board_data` function pulls only a sample of 30 rows. Large boards may contain more items, so some aggregations are approximate unless the agent queries multiple pages (not implemented).

* **Agent behavior**
  * The reasoning loop has a fixed 10‑iteration limit and may timeout on very convoluted questions.
  * It cannot perform write operations on Monday.com; it is read‑only.
  * No built‑in caching or stateful context beyond the current chat history, so repeated queries cost API calls each time.
  * Error handling is basic—if a tool call returns an unexpected schema or the LLM misinterprets a prompt, the agent may respond with a generic error string.

## � Note: Free Tier Boundaries

This agent is optimized for **free-tier API usage** (Groq free account + Monday.com basic API access). Several boundaries were intentionally set to minimize costs:

- **Fixed 10-iteration limit** – prevents runaway queries that would exceed free tier rate limits
- **30-row sample size** – significantly cheaper than fetching full boards (which can have thousands of rows)
- **No schema caching** – trade-off: simpler code vs higher API cost
- **No concurrent requests** – processes one query at a time to stay within free request limits

**With a paid tier**, these boundaries can be relaxed:

- Increase iteration limit to 20–50 for complex multi-step reasoning
- Fetch full board data (pagination support)
- Implement aggressive schema caching (5–15 min TTL)
- Enable concurrent request handling
- Add write operations with audit trail
- Support unlimited boards (not just two hard-coded ones)

The architecture supports these improvements with minimal refactoring. As usage grows, upgrading to paid APIs unlocks a more powerful, production-grade agent.

Ideas for improving both the environment setup and the agent itself:

* **API & deployment**
  * Add a CLI or web wizard to guide users through obtaining/validating keys and setting the `.env` file.
  * Support for additional boards or generic board discovery so users can ask about any board without code changes.
  * Implement pagination in `query_board_data` to handle boards with more than 30 items and allow precise totals.
  * Add rate‑limit handling and exponential backoff for Monday.com or Groq API throttling.

* **Agent features**
  * Introduce caching layers for schema lookups to reduce redundant requests and speed up conversation turnaround.
  * Expand data quality analysis to include type mismatches (e.g. text in number columns) and outlier detection.
  * Allow the agent to ask clarifying follow‑ups automatically when a question is ambiguous, rather than merely suggesting follow‑ups to the user manually.
  * Add unit and end‑to‑end tests with mocks to ensure the system‑prompt rules are always enforced.
  * Provide an export or downloadable report of the query trace and results for audit purposes.

## 🧁 Deployment

You can deploy this app to [Streamlit Community Cloud](https://streamlit.io/cloud) or any web host that supports Python/Streamlit. Simply push the cleaned repository to a GitHub repo, connect it in the Streamlit dashboard, and set the two environment variables there.

## 🔒 Security

- **Do not commit your `.env` file.** It contains sensitive API keys.
- Use a dedicated Monday.com token with appropriate read access only.

## ✅ Final Notes

This agent demonstrates real‑time tool calling, data‑aware reasoning, and a polished user experience—all built with plain Python. It can serve as the foundation for more comprehensive BI assistants or be extended to additional boards, data sources, or LLM models.
