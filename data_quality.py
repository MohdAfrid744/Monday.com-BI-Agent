"""
Data quality analysis for Monday.com queries.

Analyzes sample rows for missing/null values, calculates confidence scores,
and generates caveat strings to warn users about data quality issues.
"""

from typing import List, Dict, Any, Tuple
from collections import defaultdict


def analyze_data_quality(sample_rows: List[Dict[str, Any]], total_count: int) -> Dict[str, Any]:
    """
    Analyze sample rows for missing or null values.
    
    Args:
        sample_rows: List of row dicts from a Monday.com board query.
        total_count: The true total count of items on the board (from total_items_on_board).
    
    Returns:
        Dict containing:
        - 'has_issues': bool indicating if any data quality problems were found.
        - 'null_columns': list of (column_id, null_count, null_percentage) tuples.
        - 'sample_size': number of sample rows analyzed.
        - 'total_size': the true total count.
        - 'caveat_text': a string summarizing the issues (empty if no issues).
    """
    if not sample_rows:
        return {
            "has_issues": True,
            "null_columns": [],
            "sample_size": 0,
            "total_size": total_count,
            "caveat_text": "⚠️ No data available on this board."
        }
    
    # Count nulls per column
    null_counts = defaultdict(int)  # Track how many null values each column has
    all_columns = set()  # All column IDs found in the data
    
    for row in sample_rows:
        for column_id, value in row.items():
            if column_id in ("item_id", "Name"):
                continue  # Skip ID and name metadata columns
            all_columns.add(column_id)
            # Check if value is missing (None, empty string, or whitespace)
            if value is None or value == "" or (isinstance(value, str) and value.strip() == ""):
                null_counts[column_id] += 1
    
    sample_size = len(sample_rows)
    
    # Find columns with >20% nulls as significant data quality issues
    problematic_columns = []
    for column_id in all_columns:
        null_count = null_counts.get(column_id, 0)
        # Calculate percentage of missing values in this column
        null_percentage = (null_count / sample_size) * 100 if sample_size > 0 else 0
        
        # Flag if more than 20% of values are missing
        if null_percentage > 20:
            problematic_columns.append((column_id, null_count, null_percentage))
    
    # Generate human-readable caveat text
    caveat_text = ""
    has_issues = len(problematic_columns) > 0
    
    if has_issues:
        caveat_text = "⚠️ **Data Quality Note:**"
        # Sort by highest null percentage first (most critical issues)
        for column_id, null_count, null_percentage in sorted(problematic_columns, key=lambda x: x[2], reverse=True):
            caveat_text += f"\n  - Column '{column_id}': {null_percentage:.0f}% of sampled records are missing values ({null_count}/{sample_size})."
        caveat_text += "\n\nThis may affect the accuracy of calculations. Results above represent the available data."
    
    return {
        "has_issues": has_issues,
        "null_columns": problematic_columns,
        "sample_size": sample_size,
        "total_size": total_count,
        "caveat_text": caveat_text
    }


def generate_caveat_for_answer(data_quality_history: List[Dict[str, Any]]) -> str:
    """
    Generate an aggregated caveat string from all data quality analyses
    performed during a single agent's reasoning.
    
    Args:
        data_quality_history: List of dicts returned by analyze_data_quality().
    
    Returns:
        A combined caveat string, or empty string if no issues.
    """
    if not data_quality_history:
        return ""
    
    # Collect all problematic columns from all queries
    all_caveats = []
    for analysis in data_quality_history:
        if analysis.get("caveat_text"):
            all_caveats.append(analysis["caveat_text"])
    
    if not all_caveats:
        return ""
    
    # Combine: if multiple queries showed issues, mention them all
    if len(all_caveats) == 1:
        return "\n\n" + all_caveats[0]
    else:
        combined = "\n\n⚠️ **Data Quality Notes (Multiple Queries):**"
        for i, caveat in enumerate(all_caveats, 1):
            combined += f"\n\nQuery {i}:\n{caveat}"
        return combined
