import json
import requests
from groq import Groq
import pandas as pd
from monday_api import fetch_boards, get_board_schema, query_board_data
from config import get_config
from data_quality import analyze_data_quality, generate_caveat_for_answer



TOOLS_MAP = {
    "fetch_boards": fetch_boards,
    "get_board_schema": get_board_schema,
    "query_board_data": query_board_data,
}

SYSTEM_PROMPT = """You are a Business Intelligence Agent connected to a company's live Monday.com data.
You help founders and executives get clear, accurate answers to their business questions.

CRITICAL RULES — FOLLOW THESE WITHOUT EXCEPTION:

1. NEVER fabricate, assume, or guess data values. Every number in your answer must come from an actual tool call in this conversation.
2. NEVER say "let's assume", "for example", or invent sample data. If you lack data, call the tool to get it.

3. MANDATORY tool sequence for any data question:
   a) Call `fetch_boards` to get real board IDs and names
   b) Call `get_board_schema` with the correct numeric board ID — NEVER skip this step
   c) Call `query_board_data` with the correct numeric board ID
   d) Only then calculate and answer using the data you received

4. Board IDs are always numeric integers. Never pass a board name (e.g. "Deals") as a board ID.

5. COUNTING: The `query_board_data` tool returns a `total_items_on_board` field — always use THIS for any question about "how many", totals, or counts. Never count sample_rows as a substitute for the total.

6. CROSS-BOARD QUESTIONS: If the user asks about both boards or asks a general business question, query BOTH the Work Orders board and the Deals Pipeline board, then synthesise the answer.

7. AMBIGUOUS QUERIES: If a question is unclear (e.g. "show me revenue" — which column?), look at the schema first. If there are multiple plausible columns, pick the most relevant one and state your assumption clearly (e.g. "I used the 'Billed Value' column for this calculation").

7. HUMAN‑READABLE NAMES: Tool outputs may include a `column_map` field mapping internal column IDs to their human-friendly titles. Use those titles rather than the raw IDs when writing your answer.

8. DATA QUALITY: Data may be messy — null, empty, or inconsistently formatted values are expected. Always skip nulls in calculations and tell the user how many records had missing data.

9. PERCENTAGES: When calculating percentages, always use `total_items_on_board` as the denominator — not the number of sample rows returned.

10. DATE/TIME FILTERING: If the user asks about a specific time period (e.g. "this quarter", "last month"), filter the sample data by the relevant date fields. Note that you only have access to a sample of 30 rows — state this limitation if it affects the answer.

11. EMPTY BOARDS: If `total_items_on_board` is 0 or `sample_rows` is empty, clearly tell the user the board has no data.

12. NON-DATA QUESTIONS: If the user greets you or asks something unrelated to data (e.g. "how are you?"), respond naturally without calling any tools.

13. BOARD NOT FOUND: If no board name matches the user's question, list the available boards and ask which one they meant.

14. CURRENCY/UNITS: If you encounter numeric values, state the unit or currency if it can be inferred from the column name (e.g. "Rupees", "%"). If it cannot be determined, say so.

15. Always fetch fresh data — do not reuse tool results from a previous question in the conversation.
16. If a tool returns an error, retry once with corrected parameters. If it errors again, explain clearly what went wrong.
"""

GROQ_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "fetch_boards",
            "description": "Returns all Monday.com boards with their IDs and names.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_board_schema",
            "description": "Returns the column definitions for a board. Call this before querying data so you know what each column ID means.",
            "parameters": {
                "type": "object",
                "properties": {
                    "board_id": {
                        "type": "string",
                        "description": "The numeric ID of the Monday.com board.",
                    }
                },
                "required": ["board_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_board_data",
            "description": "Returns the items (rows) from a Monday.com board. Each item contains all its column values.",
            "parameters": {
                "type": "object",
                "properties": {
                    "board_id": {
                        "type": "string",
                        "description": "The numeric ID of the Monday.com board.",
                    }
                },
                "required": ["board_id"],
            },
        },
    },
]


def chat_stream_with_tracing(prompt, conversation_history, trace_callback, tone="Straight Forward"):
    """
    Runs the agent loop with tool-calling and returns the final answer plus
    some follow-up question suggestions.

    Args:
        prompt: The user's question.
        conversation_history: List of message dicts (OpenAI format), maintained across turns.
        trace_callback: Function called with a string each time the agent takes an action.
        tone: "Straight Forward" or "Informative".

    Returns:
        (final_answer: str, updated_conversation_history: list, followups: list[str])
    """
    config = get_config()
    client = Groq(api_key=config.groq_api_key)

    if not conversation_history:
        if tone == "Informative":
            tone_instructions = """

OUTPUT STYLE — INFORMATIVE:
- Explain what each metric means before giving the number.
- Define any business terms in plain language.
- Use headers and bullet points for clarity.
- End with a clear "Key Takeaway" a non-technical person can act on.
"""
        else:
            tone_instructions = """

OUTPUT STYLE — STRAIGHT FORWARD:
- Lead with the number or answer immediately.
- Use bullet points only when listing multiple items.
- No preamble, no filler, no definitions.
- One sentence max for any data quality caveats.
"""
        conversation_history = [{"role": "system", "content": SYSTEM_PROMPT + tone_instructions}]

    conversation_history.append({"role": "user", "content": prompt})
    data_quality_history = []  # Track data quality issues across all queries

    # prepare tools map (currently always uses local function calls)
    config = get_config()
    tools_map = TOOLS_MAP.copy()

    # Agent reasoning loop: up to 10 iterations of thinking and tool calling
    for loop in range(1, 11):
        trace_callback(f"🤔 Thinking (step {loop}/10)...")

        # Keep conversation history manageable for token limits:
        # Always keep system prompt + last 8 user/assistant/tool messages
        system_msgs = [m for m in conversation_history if isinstance(m, dict) and m.get("role") == "system"]
        non_system = [m for m in conversation_history if not (isinstance(m, dict) and m.get("role") == "system")]
        trimmed = system_msgs + (non_system[-8:] if len(non_system) > 8 else non_system)  # Trim oldest messages

        response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=trimmed,
                tools=GROQ_TOOLS,
                tool_choice="auto",
                max_tokens=4096,
                temperature=0.1,
            )

        message = response.choices[0].message
        
        # Store tool_calls for later use
        tool_calls = getattr(message, 'tool_calls', [])
        
        conversation_history.append(message)

        if not tool_calls:
            final_answer = message.content or "I was unable to generate a response."
            
            # Append data quality caveats if any issues were found
            caveat = generate_caveat_for_answer(data_quality_history)
            if caveat:
                final_answer += caveat
            
            # ask for follow-up suggestions from the model
            prompt_follow = (
                "Based on the conversation above and the answer you just gave, "
                "suggest three related, useful follow-up questions the user might ask."
            )
            follow_resp = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=trimmed + [{"role": "user", "content": prompt_follow}],
                    max_tokens=300,
                    temperature=0.7,
                )
                follow_text = follow_resp.choices[0].message.content or ""
                # simple split into list
                followups = [line.strip("-• ") for line in follow_text.splitlines() if line.strip()]
            return final_answer, conversation_history, followups

        for tool_call in message.tool_calls:
            # Extract the function (tool) name and arguments that the LLM chose to call
            func_name = tool_call.function.name
            try:
                # Parse the JSON-formatted arguments the LLM generated
                raw = json.loads(tool_call.function.arguments) if tool_call.function.arguments else {}
                args = raw if isinstance(raw, dict) else {}
            except json.JSONDecodeError:
                args = {}

            # Show the user which tool is being invoked (transparency)
            trace_callback(f"Calling Tool: `{func_name}({args})`")

            # Execute the tool if it exists in our tools_map
            if func_name in tools_map:
                try:
                    result = tools_map[func_name](**args)  # Call the actual function
                    if isinstance(result, pd.DataFrame):
                        result = result.to_dict(orient="records")
                    
                    # Track data quality issues (nulls, missing values) from board queries
                    if func_name == "query_board_data" and isinstance(result, dict):
                        sample_rows = result.get("sample_rows", [])
                        total_count = result.get("total_items_on_board", 0)
                        quality_analysis = analyze_data_quality(sample_rows, total_count)
                        data_quality_history.append(quality_analysis)
                    
                    # Convert to string and truncate if needed for token limits
                    result_str = json.dumps(result, default=str)
                    if len(result_str) > 3000:
                        result_str = result_str[:3000] + "... [truncated]"
                    trace_callback(f"Tool `{func_name}` returned {len(result_str)} chars")
                except Exception as e:
                    result_str = json.dumps({"error": str(e)})
                    trace_callback(f"Tool `{func_name}` error: {e}")
            else:
                result_str = json.dumps({"error": "Unknown tool"})
                trace_callback(f"Unknown tool called: `{func_name}`")

            # Add the tool result to the conversation history so the agent can see and reason about it
            conversation_history.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result_str,
            })

    return "The agent reached its reasoning limit without a final answer.", conversation_history, []
