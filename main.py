from fastmcp import FastMCP
import os
import sqlite3
from datetime import datetime

# Database path
DB_PATH = os.path.join(os.path.dirname(__file__), "expenses.db")

# Create MCP instance
mcp = FastMCP(name="Expense Tracker Server")


# -----------------------------
# DATABASE INITIALIZATION
# -----------------------------
def init_db():
    with sqlite3.connect(DB_PATH) as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                subcategory TEXT DEFAULT '',
                note TEXT DEFAULT ''
            )
        """)


init_db()


# -----------------------------
# VALIDATION HELPERS
# -----------------------------
def validate_date(date_str: str):
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        raise ValueError("Date must be in YYYY-MM-DD format")


def validate_amount(amount: float):
    if amount <= 0:
        raise ValueError("Amount must be greater than 0")


def validate_category(category: str):
    if not category:
        raise ValueError("Category is required")


# -----------------------------
# TOOLS
# -----------------------------

# Add Expense
@mcp.tool(name="add_expense", description="Add a new expense.")
def add_expense(date: str, amount: float, category: str, subcategory: str = "", note: str = ""):
    validate_date(date)
    validate_amount(amount)
    validate_category(category)

    with sqlite3.connect(DB_PATH) as c:
        cur = c.execute(
            "INSERT INTO expenses(date, amount, category, subcategory, note) VALUES (?, ?, ?, ?, ?)",
            (date, amount, category, subcategory, note)
        )
        return {"status": "ok", "id": cur.lastrowid}


# List Expenses by Date Range
@mcp.tool(name="list_expenses", description="List expenses within a date range.")
def list_expenses(start_date: str, end_date: str) -> list[dict]:
    validate_date(start_date)
    validate_date(end_date)

    with sqlite3.connect(DB_PATH) as c:
        cur = c.execute("""
            SELECT id, date, amount, category, subcategory, note
            FROM expenses
            WHERE date BETWEEN ? AND ?
            ORDER BY date ASC
        """, (start_date, end_date))

        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]


# Summarize by Category
@mcp.tool(name="summarize_expenses", description="Summarize expenses by category.")
def summarize_expenses(start_date: str, end_date: str, category: str = None) -> list[dict]:
    validate_date(start_date)
    validate_date(end_date)

    query = """
        SELECT category, SUM(amount) as total_amount
        FROM expenses
        WHERE date BETWEEN ? AND ?
    """

    params = [start_date, end_date]

    if category:
        query += " AND category = ?"
        params.append(category)

    query += " GROUP BY category ORDER BY total_amount DESC"

    with sqlite3.connect(DB_PATH) as c:
        cur = c.execute(query, params)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]


# Monthly Summary
@mcp.tool(name="monthly_summary", description="Get total expenses for a given month.")
def monthly_summary(year: int, month: int):
    if month < 1 or month > 12:
        raise ValueError("Month must be between 1 and 12")

    month_str = f"{year:04d}-{month:02d}"

    with sqlite3.connect(DB_PATH) as c:
        cur = c.execute("""
            SELECT SUM(amount)
            FROM expenses
            WHERE strftime('%Y-%m', date) = ?
        """, (month_str,))

        total = cur.fetchone()[0] or 0
        return {"year": year, "month": month, "total": total}


# Top Categories
@mcp.tool(name="top_categories", description="Get top spending categories.")
def top_categories(limit: int = 3):
    with sqlite3.connect(DB_PATH) as c:
        cur = c.execute("""
            SELECT category, SUM(amount) as total
            FROM expenses
            GROUP BY category
            ORDER BY total DESC
            LIMIT ?
        """, (limit,))

        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]


# Delete Expense
@mcp.tool(name="delete_expense", description="Delete an expense by ID.")
def delete_expense(expense_id: int):
    with sqlite3.connect(DB_PATH) as c:
        cur = c.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
        if cur.rowcount == 0:
            return {"status": "not_found"}
        return {"status": "deleted"}


# -----------------------------
# RESOURCES
# -----------------------------

@mcp.resource("expense://categories", mime_type="application/json")
def list_categories():
    with sqlite3.connect(DB_PATH) as c:
        cur = c.execute("SELECT DISTINCT category FROM expenses")
        return [r[0] for r in cur.fetchall()]


# -----------------------------
# RUN SERVER
# -----------------------------

if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000)