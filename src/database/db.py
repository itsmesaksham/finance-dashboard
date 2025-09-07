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
    """Identify inter-bank transfers - between same person's different banks or between different persons"""
    conn = sqlite3.connect(DB_NAME)
    df = None
    try:
        # First try to find exact matches between different accounts (different owners OR different banks)
        df = pd.read_sql_query("""
            SELECT 
                t1.date, t1.owner as from_owner, t1.bank as from_bank,
                t2.owner as to_owner, t2.bank as to_bank,
                t1.debit as amount,
                t1.description as from_description,
                t2.description as to_description,
                CASE 
                    WHEN t1.owner = t2.owner THEN 'Inter-Bank (Same Person)'
                    ELSE 'Inter-Person Transfer'
                END as transfer_type
            FROM transactions t1
            JOIN transactions t2 ON 
                t1.date = t2.date 
                AND t1.debit = t2.credit 
                AND (t1.owner != t2.owner OR t1.bank != t2.bank)
                AND t1.debit > 0
            ORDER BY t1.date DESC
        """, conn)
        
        # If no exact matches found, detect based on transfer patterns in descriptions
        if df is None or df.empty:
            df = pd.read_sql_query("""
                SELECT 
                    date, owner as from_owner, bank as from_bank,
                    CASE 
                        WHEN description LIKE '%TO TRANSFER%' AND description LIKE '%HDFC%' THEN owner
                        WHEN description LIKE '%TO TRANSFER%' AND description LIKE '%SBI%' THEN owner
                        WHEN description LIKE '%BY TRANSFER%' AND description LIKE '%HDFC%' THEN owner
                        WHEN description LIKE '%BY TRANSFER%' AND description LIKE '%SBI%' THEN owner
                        WHEN description LIKE '%UPI%' AND description LIKE '%/HDFC/%' THEN 'External Person'
                        WHEN description LIKE '%UPI%' AND description LIKE '%/SBI/%' THEN 'External Person'
                        WHEN description LIKE '%IMPS%' THEN 'External Person'
                        WHEN description LIKE '%NEFT%' AND description LIKE '%PUNB%' THEN 'External Person'
                        WHEN description LIKE '%NEFT%' AND description LIKE '%YESB%' THEN 'External Person'
                        ELSE 'Unknown Recipient'
                    END as to_owner,
                    CASE 
                        WHEN description LIKE '%HDFC%' THEN 'HDFC'
                        WHEN description LIKE '%SBI%' THEN 'SBI'
                        WHEN description LIKE '%PUNB%' THEN 'Punjab National Bank'
                        WHEN description LIKE '%YESB%' THEN 'Yes Bank'
                        WHEN description LIKE '%ICICI%' THEN 'ICICI'
                        WHEN description LIKE '%AXIS%' THEN 'Axis Bank'
                        ELSE 'Unknown Bank'
                    END as to_bank,
                    CASE 
                        WHEN debit > 0 THEN debit 
                        ELSE credit 
                    END as amount,
                    description as from_description,
                    '' as to_description,
                    CASE 
                        WHEN description LIKE '%TO TRANSFER%' OR description LIKE '%BY TRANSFER%' THEN 
                            CASE 
                                WHEN owner = CASE 
                                    WHEN description LIKE '%HDFC%' THEN owner
                                    WHEN description LIKE '%SBI%' THEN owner
                                    ELSE 'External Person'
                                END THEN 'Inter-Bank (Same Person)'
                                ELSE 'Inter-Person Transfer'
                            END
                        ELSE 'Inter-Bank Transfer'
                    END as transfer_type
                FROM transactions 
                WHERE (description LIKE '%TRANSFER%' 
                       OR description LIKE '%UPI%' 
                       OR description LIKE '%IMPS%' 
                       OR description LIKE '%NEFT%'
                       OR description LIKE '%RTGS%')
                AND (debit > 0 OR credit > 0)
                ORDER BY date DESC
            """, conn)
    finally:
        conn.close()
    return df

def get_transfer_patterns():
    """Get transfer patterns and statistics for inter-bank transfers"""
    conn = sqlite3.connect(DB_NAME)
    try:
        # Count transfers by type
        transfer_types = pd.read_sql_query("""
            SELECT 
                CASE 
                    WHEN description LIKE '%TO TRANSFER%' THEN 'Outgoing Transfer'
                    WHEN description LIKE '%BY TRANSFER%' THEN 'Incoming Transfer'
                    WHEN description LIKE '%UPI%' THEN 'UPI Transfer'
                    WHEN description LIKE '%IMPS%' THEN 'IMPS Transfer'
                    WHEN description LIKE '%NEFT%' THEN 'NEFT Transfer'
                    WHEN description LIKE '%RTGS%' THEN 'RTGS Transfer'
                    ELSE 'Other Transfer'
                END as transfer_method,
                COUNT(*) as count,
                SUM(CASE WHEN debit > 0 THEN debit ELSE credit END) as total_amount,
                AVG(CASE WHEN debit > 0 THEN debit ELSE credit END) as avg_amount
            FROM transactions 
            WHERE (description LIKE '%TRANSFER%' 
                   OR description LIKE '%UPI%' 
                   OR description LIKE '%IMPS%' 
                   OR description LIKE '%NEFT%'
                   OR description LIKE '%RTGS%')
            AND (debit > 0 OR credit > 0)
            GROUP BY transfer_method
            ORDER BY count DESC
        """, conn)
        
        # Count by bank mentions in descriptions
        bank_transfers = pd.read_sql_query("""
            SELECT 
                CASE 
                    WHEN description LIKE '%HDFC%' THEN 'HDFC Bank'
                    WHEN description LIKE '%SBI%' THEN 'State Bank of India'
                    WHEN description LIKE '%ICICI%' THEN 'ICICI Bank'
                    WHEN description LIKE '%AXIS%' THEN 'Axis Bank'
                    WHEN description LIKE '%PUNB%' THEN 'Punjab National Bank'
                    WHEN description LIKE '%YESB%' THEN 'Yes Bank'
                    WHEN description LIKE '%KOTAK%' THEN 'Kotak Bank'
                    ELSE 'Other/Unknown Bank'
                END as bank_name,
                COUNT(*) as transfer_count,
                SUM(CASE WHEN debit > 0 THEN debit ELSE credit END) as total_amount
            FROM transactions 
            WHERE (description LIKE '%TRANSFER%' 
                   OR description LIKE '%UPI%' 
                   OR description LIKE '%IMPS%' 
                   OR description LIKE '%NEFT%'
                   OR description LIKE '%RTGS%')
            AND (debit > 0 OR credit > 0)
            GROUP BY bank_name
            ORDER BY transfer_count DESC
        """, conn)
        
        # Transfer direction analysis
        direction_analysis = pd.read_sql_query("""
            SELECT 
                CASE 
                    WHEN debit > 0 THEN 'Outgoing'
                    WHEN credit > 0 THEN 'Incoming'
                    ELSE 'Unknown'
                END as direction,
                COUNT(*) as count,
                SUM(CASE WHEN debit > 0 THEN debit ELSE credit END) as total_amount,
                AVG(CASE WHEN debit > 0 THEN debit ELSE credit END) as avg_amount
            FROM transactions 
            WHERE (description LIKE '%TRANSFER%' 
                   OR description LIKE '%UPI%' 
                   OR description LIKE '%IMPS%' 
                   OR description LIKE '%NEFT%'
                   OR description LIKE '%RTGS%')
            AND (debit > 0 OR credit > 0)
            GROUP BY direction
            ORDER BY count DESC
        """, conn)
        
        return {
            'transfer_types': transfer_types,
            'bank_transfers': bank_transfers,
            'direction_analysis': direction_analysis
        }
    finally:
        conn.close()


def get_all_transfer_transactions():
    """Get all transfer transactions as a DataFrame for detailed analysis"""
    conn = sqlite3.connect(DB_NAME)
    try:
        df = pd.read_sql_query("""
            SELECT 
                date, owner, bank, 
                CASE 
                    WHEN debit > 0 THEN debit 
                    ELSE 0 
                END as debit,
                CASE 
                    WHEN credit > 0 THEN credit 
                    ELSE 0 
                END as credit,
                balance, description,
                CASE 
                    WHEN description LIKE '%TO TRANSFER%' THEN 'Outgoing Transfer'
                    WHEN description LIKE '%BY TRANSFER%' THEN 'Incoming Transfer'
                    WHEN description LIKE '%UPI%' THEN 'UPI Transfer'
                    WHEN description LIKE '%IMPS%' THEN 'IMPS Transfer'
                    WHEN description LIKE '%NEFT%' THEN 'NEFT Transfer'
                    WHEN description LIKE '%RTGS%' THEN 'RTGS Transfer'
                    ELSE 'Other Transfer'
                END as transfer_method,
                CASE 
                    WHEN debit > 0 THEN 'Outgoing'
                    WHEN credit > 0 THEN 'Incoming'
                    ELSE 'Unknown'
                END as direction
            FROM transactions 
            WHERE (description LIKE '%TRANSFER%' 
                   OR description LIKE '%UPI%' 
                   OR description LIKE '%IMPS%' 
                   OR description LIKE '%NEFT%'
                   OR description LIKE '%RTGS%')
            AND (debit > 0 OR credit > 0)
            ORDER BY date DESC
        """, conn)
        return df
    finally:
        conn.close()


def purge_all_data():
    """Delete all transaction data from the database"""
    conn = sqlite3.connect(DB_NAME)
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM transactions")
        cursor.execute("DELETE FROM sweep_adjustments")
        conn.commit()
        return cursor.rowcount
    finally:
        conn.close()


def get_transaction_count():
    """Get the total number of transactions in the database"""
    conn = sqlite3.connect(DB_NAME)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM transactions")
        return cursor.fetchone()[0]
    finally:
        conn.close()


def check_duplicate_transactions(records):
    """Check if any of the provided records already exist in the database"""
    if not records:
        return 0
    
    conn = sqlite3.connect(DB_NAME)
    try:
        cursor = conn.cursor()
        duplicates = 0
        
        for record in records:
            # Records are tuples: (date, owner, bank, description, debit, credit, balance)
            cursor.execute("""
                SELECT COUNT(*) FROM transactions 
                WHERE date = ? AND owner = ? AND bank = ? AND description = ? AND debit = ? AND credit = ?
            """, (record[0], record[1], record[2], record[3], record[4], record[5]))
            
            if cursor.fetchone()[0] > 0:
                duplicates += 1
        
        return duplicates
    finally:
        conn.close()
