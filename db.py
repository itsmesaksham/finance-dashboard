import sqlite3
import pandas as pd

DB_NAME = "finance.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Create transactions table
    c.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            owner TEXT,
            bank TEXT,
            description TEXT,
            debit REAL,
            credit REAL,
            balance REAL
        )
    """)
    
    # Create sweep balance adjustments table
    c.execute("""
        CREATE TABLE IF NOT EXISTS sweep_adjustments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            owner TEXT,
            amount REAL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()

def insert_transactions(transactions):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.executemany("""
        INSERT INTO transactions (date, owner, bank, description, debit, credit, balance)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, transactions)
    conn.commit()
    conn.close()

def fetch_all():
    conn = sqlite3.connect(DB_NAME)
    df = None
    try:
        df = pd.read_sql_query("SELECT * FROM transactions ORDER BY date, id", conn)
    finally:
        conn.close()
    return df

def add_sweep_balance_adjustment(date, owner, amount, description):
    """Add a sweep balance adjustment"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        INSERT INTO sweep_adjustments (date, owner, amount, description)
        VALUES (?, ?, ?, ?)
    """, (date, owner, amount, description))
    conn.commit()
    conn.close()

def get_sweep_balance_adjustments():
    """Get all sweep balance adjustments"""
    conn = sqlite3.connect(DB_NAME)
    df = None
    try:
        df = pd.read_sql_query("SELECT * FROM sweep_adjustments ORDER BY date", conn)
    finally:
        conn.close()
    return df

def delete_sweep_adjustment(adjustment_id):
    """Delete a sweep balance adjustment"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM sweep_adjustments WHERE id = ?", (adjustment_id,))
    conn.commit()
    conn.close()

def get_account_balances():
    """Get latest balance for each account"""
    conn = sqlite3.connect(DB_NAME)
    df = None
    try:
        df = pd.read_sql_query("""
            SELECT owner, bank, balance, date
            FROM transactions t1
            WHERE date = (
                SELECT MAX(date) 
                FROM transactions t2 
                WHERE t2.owner = t1.owner AND t2.bank = t1.bank
            )
            ORDER BY owner, bank
        """, conn)
    finally:
        conn.close()
    return df

def get_inter_person_transfers():
    """Identify potential inter-person transfers based on matching amounts and dates"""
    conn = sqlite3.connect(DB_NAME)
    df = None
    try:
        df = pd.read_sql_query("""
            SELECT 
                t1.date, t1.owner as from_owner, t1.bank as from_bank,
                t2.owner as to_owner, t2.bank as to_bank,
                t1.debit as amount,
                t1.description as from_description,
                t2.description as to_description
            FROM transactions t1
            JOIN transactions t2 ON 
                t1.date = t2.date 
                AND t1.debit = t2.credit 
                AND t1.owner != t2.owner
                AND t1.debit > 0
            ORDER BY t1.date DESC
        """, conn)
    finally:
        conn.close()
    return df
