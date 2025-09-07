import pandas as pd
import os
import re
from datetime import datetime

def safe_float(value):
    """Safely convert a value to float, handling Indian number formats, empty strings, NaN, etc."""
    if pd.isna(value) or value == "":
        return 0.0
    try:
        # Remove commas, quotes, and handle Indian number formatting
        if isinstance(value, str):
            value = value.replace(",", "").replace("\"", "").strip()
            # Handle negative values in parentheses
            if value.startswith("(") and value.endswith(")"):
                value = "-" + value[1:-1]
            # Handle Indian currency symbols
            value = value.replace("₹", "").replace("Rs.", "").replace("Rs", "").strip()
        return float(value)
    except (ValueError, TypeError):
        return 0.0

def parse_date(date_str, bank=None):
    """Parse date string in various formats with bank-specific handling"""
    if pd.isna(date_str) or date_str == "":
        return ""
    
    date_str = str(date_str).strip()
    
    # Bank-specific date formats
    if bank and bank.upper() == "SBI":
        # SBI uses DD-MMM-YY format (e.g., 26-Apr-23)
        date_formats = ["%d-%b-%y"]
    elif bank and bank.upper() == "HDFC":
        # HDFC uses DD/MM/YY format (e.g., 01/04/23)
        date_formats = ["%d/%m/%y"]
    else:
        # Common date formats for other banks
        date_formats = [
            "%d-%b-%y",    # 05-Apr-22
            "%d-%m-%Y",    # 05-04-2022
            "%d/%m/%Y",    # 05/04/2022
            "%Y-%m-%d",    # 2022-04-05
            "%d-%m-%y",    # 05-04-22
            "%d/%m/%y",    # 05/04/22
        ]
    
    for fmt in date_formats:
        try:
            parsed_date = datetime.strptime(date_str, fmt)
            return parsed_date.strftime("%d-%m-%Y")
        except ValueError:
            continue
    
    return date_str  # Return original if no format matches

def detect_inter_person_transfer(description):
    """Detect if a transaction is likely an inter-person transfer"""
    transfer_keywords = [
        "transfer", "imps", "neft", "rtgs", "upi", "paytm", "phonepe", 
        "gpay", "google pay", "paym", "bharatpe", "mobikwik"
    ]
    
    description_lower = description.lower()
    return any(keyword in description_lower for keyword in transfer_keywords)

def clean_description(description):
    """Clean and standardize transaction descriptions"""
    if pd.isna(description):
        return ""
    
    description = str(description).strip()
    
    # Remove excessive whitespace
    description = re.sub(r'\s+', ' ', description)
    
    # Remove common bank codes and format patterns
    description = re.sub(r'--+', '', description)
    description = re.sub(r'\*+', '', description)
    
    return description

def extract_mod_balance(file_path):
    """Extract MOD balance from SBI CSV file header"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f):
                if line_num > 20:  # Stop after header section
                    break
                if 'MOD Balance' in line:
                    # Extract the balance value from the line using regex
                    # Format: MOD Balance      :,"11,21,000.00",,,,,
                    import re
                    match = re.search(r'"([0-9,]+\.?[0-9]*)"', line)
                    if match:
                        balance_str = match.group(1)
                        # Handle Indian number format: "11,21,000.00" -> 1121000.00
                        return safe_float(balance_str)
    except Exception as e:
        print(f"Error extracting MOD balance from {file_path}: {e}")
    return 0.0

def is_sweep_transaction(description):
    """Check if a transaction is a sweep transaction"""
    if pd.isna(description):
        return False
    
    description_upper = description.upper()
    sweep_keywords = [
        'DEBIT SWEEP',
        'TRANSFER CREDIT-',
        'SWEEP TO',
        'SWEEP FROM'
    ]
    
    return any(keyword in description_upper for keyword in sweep_keywords)

def process_sweep_transactions(df, mod_balance):
    """Process sweep transactions by removing them and adjusting subsequent balances"""
    if df.empty or 'is_sweep' not in df.columns:
        return df
    
    # Create a copy to avoid modifying original
    df_processed = df.copy()
    
    # Track sweep balance changes
    sweep_balance = mod_balance
    balance_adjustment = 0.0
    
    # Process each transaction
    for idx, row in df_processed.iterrows():
        if row['is_sweep']:
            # Calculate sweep amount
            sweep_amount = row['debit'] if row['debit'] > 0 else row['credit']
            
            # Update sweep balance
            if 'DEBIT SWEEP' in row['description'].upper():
                # Money going to sweep account
                sweep_balance += sweep_amount
                balance_adjustment -= sweep_amount
            elif 'TRANSFER CREDIT-SWEEP' in row['description'].upper():
                # Money coming from sweep account
                sweep_balance -= sweep_amount
                balance_adjustment += sweep_amount
            
            # Mark for removal
            df_processed.loc[idx, 'remove'] = True
        else:
            # Apply accumulated balance adjustment to non-sweep transactions
            if balance_adjustment != 0:
                df_processed.loc[idx, 'balance'] += balance_adjustment
                balance_adjustment = 0.0  # Reset after applying
    
    # Remove sweep transactions - fix the boolean logic
    df_processed = df_processed[df_processed.get('remove', False) != True]
    
    # Drop temporary columns
    df_processed = df_processed.drop(columns=['is_sweep', 'remove'], errors='ignore')
    
    return df_processed

def parse_csv(file_path):
    """Enhanced CSV parser for various bank statement formats"""
    try:
        # Extract owner + bank from file name convention: Owner_Bank.csv
        base = os.path.basename(file_path)
        name_parts = os.path.splitext(base)[0].split("_")
        
        if len(name_parts) >= 2:
            owner = name_parts[0]
            bank = name_parts[1]
        else:
            owner = name_parts[0]
            bank = "Unknown"
        
        # Extract MOD balance for SBI (sweep account balance)
        mod_balance = 0.0
        if bank.upper() == "SBI":
            mod_balance = extract_mod_balance(file_path)
            # Store sweep balance in database
            from src.database.db import update_sweep_balance
            statement_date = os.path.splitext(os.path.basename(file_path))[0].split("_")[-1]  # Extract year from filename
            update_sweep_balance(owner, bank, statement_date, mod_balance)

        # Try different encodings and handle bank-specific row skipping
        encodings = ['utf-8', 'latin1', 'cp1252']
        df = None
        
        # Determine skip rows based on bank
        skip_rows = 20 if bank.upper() in ["SBI", "HDFC"] else 0
        
        for encoding in encodings:
            try:
                df = pd.read_csv(file_path, encoding=encoding, skiprows=skip_rows)
                break
            except UnicodeDecodeError:
                continue
        
        if df is None:
            raise ValueError(f"Could not read file {file_path} with any encoding")
        
        # Lowercase + strip spaces for easier matching
        df.columns = df.columns.str.strip().str.lower()

        # Bank-specific column mapping
        if bank.upper() == "SBI":
            col_map = {
                "date": ["txn date"],
                "description": ["description"],
                "debit": ["debit"],
                "credit": ["credit"],
                "balance": ["balance"]
            }
        elif bank.upper() == "HDFC":
            col_map = {
                "date": ["date"],
                "description": ["narration"],
                "debit": ["withdrawal amt."],
                "credit": ["deposit amt."],
                "balance": ["closing balance"]
            }
        else:
            # Generic column mapping for other banks
            col_map = {
                "date": [
                    "date", "txn date", "transaction date", "value date", 
                    "posting date", "effective date", "trans date"
                ],
                "description": [
                    "description", "narration", "remarks", "transaction details",
                    "particulars", "transaction description", "details"
                ],
                "debit": [
                    "debit", "withdrawal amt.", "withdrawal amount", "debit amount",
                    "dr amount", "withdrawal", "paid out", "debit amt"
                ],
                "credit": [
                    "credit", "deposit amt.", "deposit amount", "credit amount",
                    "cr amount", "deposit", "paid in", "credit amt"
                ],
                "balance": [
                    "balance", "balance amt.", "available balance", "closing balance",
                    "running balance", "bal amount", "balance amount"
                ]
            }

        # Find and map columns
        std_cols = {}
        for std, possibles in col_map.items():
            for p in possibles:
                if p in df.columns:
                    std_cols[std] = p
                    break

        # Rename only available columns
        df = df.rename(columns={v: k for k, v in std_cols.items() if v in df.columns})

        # Fill missing debit/credit columns if not present
        if "debit" not in df.columns:
            df["debit"] = 0.0
        if "credit" not in df.columns:
            df["credit"] = 0.0

        # Clean and process data
        if "date" in df.columns:
            df["date"] = df["date"].apply(lambda x: parse_date(x, bank))
        
        if "description" in df.columns:
            df["description"] = df["description"].apply(clean_description)
            # Add transfer flag
            df["is_transfer"] = df["description"].apply(detect_inter_person_transfer)
            # Add sweep flag
            df["is_sweep"] = df["description"].apply(is_sweep_transaction)

        # Convert numeric columns
        for col in ["debit", "credit", "balance"]:
            if col in df.columns:
                df[col] = df[col].apply(safe_float)
        
        # Handle sweep transactions for SBI
        if bank.upper() == "SBI" and "is_sweep" in df.columns:
            df = process_sweep_transactions(df, mod_balance)

        # Remove rows with invalid or missing essential data
        df = df.dropna(subset=["date"])
        df = df[df["date"] != ""]

        # Sort by date and standardize format
        try:
            # Try to parse dates consistently
            df["date"] = pd.to_datetime(df["date"], format="%d-%m-%Y", dayfirst=True, errors='coerce')
            df = df.dropna(subset=["date"])  # Remove invalid dates
            df = df.sort_values("date")
            df["date"] = df["date"].dt.strftime("%d-%m-%Y")
        except Exception:
            try:
                # Fallback to more flexible parsing
                df["date"] = pd.to_datetime(df["date"], dayfirst=True, errors='coerce')
                df = df.dropna(subset=["date"])
                df = df.sort_values("date")
                df["date"] = df["date"].dt.strftime("%d-%m-%Y")
            except Exception:
                # If all else fails, keep original format
                pass

        # Convert to tuples for DB insertion
        records = []
        for _, row in df.iterrows():
            record = (
                row.get("date", ""),
                owner,
                bank,
                row.get("description", ""),
                safe_float(row.get("debit", 0)),
                safe_float(row.get("credit", 0)),
                safe_float(row.get("balance", 0))
            )
            records.append(record)
        
        return records
    
    except Exception as e:
        print(f"Error parsing {file_path}: {str(e)}")
        return []

def validate_data_integrity(df):
    """Validate data integrity and highlight potential issues"""
    issues = []
    
    if df is None or df.empty:
        return ["No data found"]
    
    # Check for missing dates
    missing_dates = df["date"].isna().sum()
    if missing_dates > 0:
        issues.append(f"{missing_dates} transactions have missing dates")
    
    # Check for suspicious balance patterns
    if "balance" in df.columns:
        balance_jumps = df["balance"].diff().abs()
        large_jumps = balance_jumps > balance_jumps.quantile(0.95)
        if large_jumps.sum() > 0:
            issues.append(f"{large_jumps.sum()} potentially suspicious balance changes detected")
    
    # Check for duplicate transactions
    duplicates = df.duplicated(subset=["date", "description", "debit", "credit"]).sum()
    if duplicates > 0:
        issues.append(f"{duplicates} potential duplicate transactions found")
    
    return issues if issues else ["Data integrity looks good"]
