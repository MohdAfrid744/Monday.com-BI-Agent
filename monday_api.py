import os
import requests
from typing import List, Dict, Any
from config import get_config

MONDAY_API_URL = "https://api.monday.com/v2"


def get_headers() -> Dict[str, str]:
    config = get_config()
    return {
        "Authorization": config.monday_api_token,
        "API-Version": "2024-01",
        "Content-Type": "application/json",
    }


def fetch_boards() -> List[Dict[str, Any]]:
    """Returns a list of all Monday.com boards with their IDs and names."""
    query = "{ boards { id name } }"
    response = requests.post(MONDAY_API_URL, json={"query": query}, headers=get_headers())
    response.raise_for_status()
    data = response.json()
    if "errors" in data:
        raise Exception(f"Monday.com API error: {data['errors']}")
    return data.get("data", {}).get("boards", [])


def get_board_schema(board_id: str) -> List[Dict[str, Any]]:
    """Returns the column definitions (id, title, type) for a given board."""
    query = f"""
    {{
      boards(ids: {board_id}) {{
        name
        columns {{
          id
          title
          type
        }}
      }}
    }}
    """
    response = requests.post(MONDAY_API_URL, json={"query": query}, headers=get_headers())
    response.raise_for_status()
    data = response.json()
    if "errors" in data:
        raise Exception(f"Monday.com API error: {data['errors']}")
    boards = data.get("data", {}).get("boards", [])
    return boards[0].get("columns", []) if boards else []


def query_board_data(board_id: str) -> Dict[str, Any]:
    """
    Returns up to 30 items from a board plus the true total item count.
    
    IMPORTANT for agents/tools:
    - Use `total_items_on_board` for any counting questions (how many rows, totals, etc.)
    - Do NOT count rows in the sample_rows list — it's only a preview, not exhaustive.

    Also returns a `column_map` that maps internal column IDs to human-friendly names
    so downstream tools can display readable column titles to users.
    """
    # First, fetch the board's schema to build a human-friendly column name map
    schema = get_board_schema(board_id)
    column_map = {col["id"]: col.get("title") for col in schema}  # Maps 'status12' -> 'Status'

    query = f"""
    {{
      boards(ids: {board_id}) {{
        items_count
        items_page(limit: 30) {{
          items {{
            id
            name
            column_values {{
              id
              text
            }}
          }}
        }}
      }}
    }}
    """
    response = requests.post(MONDAY_API_URL, json={"query": query}, headers=get_headers())
    response.raise_for_status()
    result = response.json()
    if "errors" in result:
        raise Exception(f"Monday.com API error: {result['errors']}")

    boards = result.get("data", {}).get("boards", [])
    if not boards:
        return {"total_items_on_board": 0, "sample_rows": [], "column_map": column_map}

    board = boards[0]
    total = board.get("items_count", 0)
    items = board.get("items_page", {}).get("items", [])

    sample = []
    for item in items:
        row = {"item_id": item["id"], "Name": item["name"]}
        for col in item.get("column_values", []):
            row[col["id"]] = col.get("text") or None
        sample.append(row)

    return {
        "total_items_on_board": total,
        "note": f"Showing {len(sample)} sample rows out of {total} total. Use total_items_on_board for any counting questions.",
        "sample_rows": sample,
        "column_map": column_map,
    }
