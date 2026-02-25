"""
Expense Tracker MCP Server
---------------------------
Async FastMCP server with:
- SQLite (async via aiosqlite)
- Full CRUD operations
- Aggregation tools
- Resource endpoint
- Cloud safe (temp DB path)

Author: Muazam Abbas 😎
"""

from fastmcp import FastMCP
import os
import tempfile
import aiosqlite
from datetime import datetime

# --------------------------------------------------
# DATABASE CONFIG
# --------------------------------------------------

# Cloud-safe writable path
DB_PATH = os.path.join(tempfile.gettempdir(), "expenses.db")

# Create MCP server instance
mcp = FastMCP("ExpenseTracker")

# Global async DB connection
db: aiosqlite.Connection | None = None


# --------------------------------------------------
# MCP LIFECYCLE EVENTS (IMPORTANT FOR CLOUD)
# --------------------------------------------------

@mcp.on_startup
async def on_startup():
    """
    Runs automatically when MCP server starts.
    Initializes database connection + table.
    """
    global db

    db = await aiosqlite.connect(DB_PATH)

    await db.execute("PRAGMA journal_mode=WAL")

    await db.execute("""
        CREATE TABLE IF NOT EXISTS expenses(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            subcategory TEXT DEFAULT '',
            note TEXT DEFAULT ''
        )
    """)

    await db.commit()


@mcp.on_shutdown
async def on_shutdown():
    """
    Runs automatically when MCP server shuts down.
    """
    global db
    if db:
        await db.close()


# --------------------------------------------------
# VALIDATION HELPERS
# --------------------------------------------------

def validate_date(date_str: str):
    """Ensure date format YYYY-MM-DD"""
    datetime.strptime(date_str, "%Y-%m-%d")


def validate_amount(amount: float):
    """Ensure amount is positive"""
    if amount <= 0:
        raise ValueError("Amount must be greater than 0")


# --------------------------------------------------
# TOOL: Add Expense
# --------------------------------------------------

@mcp.tool()
async def add_expense(
    date: str,
    amount: float,
    category: str,
    subcategory: str = "",
    note: str = ""
):
    validate_date(date)
    validate_amount(amount)

    cur = await db.execute(
        "INSERT INTO expenses(date, amount, category, subcategory, note) VALUES (?,?,?,?,?)",
        (date, amount, category, subcategory, note),
    )
    await db.commit()

    return {"status": "success", "id": cur.lastrowid}


# --------------------------------------------------
# TOOL: List Expenses
# --------------------------------------------------

@mcp.tool()
async def list_expenses(start_date: str, end_date: str):
    validate_date(start_date)
    validate_date(end_date)

    cur = await db.execute("""
        SELECT id, date, amount, category, subcategory, note
        FROM expenses
        WHERE date BETWEEN ? AND ?
        ORDER BY date DESC
    """, (start_date, end_date))

    rows = await cur.fetchall()
    cols = [d[0] for d in cur.description]

    return [dict(zip(cols, r)) for r in rows]


# --------------------------------------------------
# TOOL: Delete Expense
# --------------------------------------------------

@mcp.tool()
async def delete_expense(expense_id: int):

    cur = await db.execute(
        "DELETE FROM expenses WHERE id = ?",
        (expense_id,)
    )
    await db.commit()

    if cur.rowcount == 0:
        return {"status": "error", "message": "Expense not found"}

    return {"status": "success", "deleted_id": expense_id}


# --------------------------------------------------
# TOOL: Update Expense
# --------------------------------------------------

@mcp.tool()
async def update_expense(
    expense_id: int,
    date: str,
    amount: float,
    category: str,
    subcategory: str = "",
    note: str = ""
):

    validate_date(date)
    validate_amount(amount)

    cur = await db.execute("""
        UPDATE expenses
        SET date=?, amount=?, category=?, subcategory=?, note=?
        WHERE id=?
    """, (date, amount, category, subcategory, note, expense_id))

    await db.commit()

    if cur.rowcount == 0:
        return {"status": "error", "message": "Expense not found"}

    return {"status": "success", "updated_id": expense_id}


# --------------------------------------------------
# TOOL: Summary By Category
# --------------------------------------------------

@mcp.tool()
async def summary_by_category(start_date: str, end_date: str):

    validate_date(start_date)
    validate_date(end_date)

    cur = await db.execute("""
        SELECT category, SUM(amount) as total
        FROM expenses
        WHERE date BETWEEN ? AND ?
        GROUP BY category
        ORDER BY total DESC
    """, (start_date, end_date))

    rows = await cur.fetchall()

    return [
        {"category": r[0], "total": r[1]}
        for r in rows
    ]


# --------------------------------------------------
# RESOURCE: Monthly Summary
# --------------------------------------------------

@mcp.resource("monthly-summary")
async def monthly_summary(year: int, month: int):

    start = f"{year}-{month:02d}-01"

    if month == 12:
        end = f"{year+1}-01-01"
    else:
        end = f"{year}-{month+1:02d}-01"

    cur = await db.execute("""
        SELECT SUM(amount)
        FROM expenses
        WHERE date >= ? AND date < ?
    """, (start, end))

    result = await cur.fetchone()

    return {
        "year": year,
        "month": month,
        "total_spent": result[0] or 0
    }


# --------------------------------------------------
# LOCAL RUN (Cloud ignores this)
# --------------------------------------------------

if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000)