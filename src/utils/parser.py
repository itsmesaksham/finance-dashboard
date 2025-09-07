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

def parse_date(date_str):
    """Parse date string in various formats"""
    if pd.isna(date_str) or date_str == "":
        return ""
    
    date_str = str(date_str).strip()
    
    # Common date formats
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

        # Try different encodings
        encodings = ['utf-8', 'latin1', 'cp1252']
        df = None
        
        for encoding in encodings:
            try:
                df = pd.read_csv(file_path, encoding=encoding)
                break
            except UnicodeDecodeError:
                continue
        
        if df is None:
            raise ValueError(f"Could not read file {file_path} with any encoding")

        # Lowercase + strip spaces for easier matching
        df.columns = df.columns.str.strip().str.lower()

        # Enhanced column mapping for different bank formats
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
            df["date"] = df["date"].apply(parse_date)
        
        if "description" in df.columns:
            df["description"] = df["description"].apply(clean_description)
            # Add transfer flag
            df["is_transfer"] = df["description"].apply(detect_inter_person_transfer)

        # Convert numeric columns
        for col in ["debit", "credit", "balance"]:
            if col in df.columns:
                df[col] = df[col].apply(safe_float)

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
        except:
            try:
                # Fallback to more flexible parsing
                df["date"] = pd.to_datetime(df["date"], dayfirst=True, errors='coerce')
                df = df.dropna(subset=["date"])
                df = df.sort_values("date")
                df["date"] = df["date"].dt.strftime("%d-%m-%Y")
            except:
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
