from fastmcp import FastMCP
import os
import tempfile
import aiosqlite
from datetime import datetime

# Use writable temp directory
DB_PATH = os.path.join(tempfile.gettempdir(), "expenses.db")

mcp = FastMCP("ExpenseTracker")

# -----------------------------
# INIT DATABASE
# -----------------------------
def init_db():
    import sqlite3
    with sqlite3.connect(DB_PATH) as c:
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("""
            CREATE TABLE IF NOT EXISTS expenses(
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
# VALIDATION
# -----------------------------
def validate_date(date_str):
    datetime.strptime(date_str, "%Y-%m-%d")

def validate_amount(amount):
    if float(amount) <= 0:
        raise ValueError("Amount must be > 0")

# -----------------------------
# TOOLS
# -----------------------------
@mcp.tool()
async def add_expense(date: str, amount: float, category: str, subcategory: str = "", note: str = ""):
    validate_date(date)
    validate_amount(amount)

    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO expenses(date, amount, category, subcategory, note) VALUES (?,?,?,?,?)",
            (date, amount, category, subcategory, note),
        )
        await db.commit()
        return {"status": "success", "id": cur.lastrowid}

@mcp.tool()
async def list_expenses(start_date: str, end_date: str):
    validate_date(start_date)
    validate_date(end_date)

    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("""
            SELECT id, date, amount, category, subcategory, note
            FROM expenses
            WHERE date BETWEEN ? AND ?
            ORDER BY date DESC
        """, (start_date, end_date))

        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in await cur.fetchall()]

# -----------------------------
# RUN SERVER
# -----------------------------

if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000)