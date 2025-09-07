#!/usr/bin/env python3
"""
Data validation script for the Finance Dashboard
This script checks and cleans your CSV data before importing.
"""

import pandas as pd
import os
import glob
from parser import parse_csv

def validate_csv_files():
    """Validate all CSV files in the data directory"""
    print("🔍 Validating CSV files...")
    print("=" * 40)
    
    files = glob.glob("data/*.csv")
    
    if not files:
        print("❌ No CSV files found in the data/ directory")
        return
    
    for file_path in files:
        print(f"\n📁 Checking: {os.path.basename(file_path)}")
        
        try:
            # Try to parse with our enhanced parser
            records = parse_csv(file_path)
            
            if records:
                print(f"  ✅ Successfully parsed {len(records)} records")
                
                # Check for data quality issues
                df = pd.DataFrame(records, columns=['date', 'owner', 'bank', 'description', 'debit', 'credit', 'balance'])
                
                # Date validation
                try:
                    pd.to_datetime(df['date'], format='%d-%m-%Y', dayfirst=True, errors='raise')
                    print("  ✅ All dates are valid")
                except:
                    invalid_dates = df[pd.to_datetime(df['date'], format='%d-%m-%Y', dayfirst=True, errors='coerce').isna()]
                    print(f"  ⚠️  {len(invalid_dates)} records have invalid dates")
                
                # Numeric validation
                numeric_issues = 0
                for col in ['debit', 'credit', 'balance']:
                    non_numeric = df[pd.to_numeric(df[col], errors='coerce').isna() & (df[col] != 0)]
                    if len(non_numeric) > 0:
                        numeric_issues += len(non_numeric)
                
                if numeric_issues == 0:
                    print("  ✅ All numeric values are valid")
                else:
                    print(f"  ⚠️  {numeric_issues} records have invalid numeric values")
                
                # Balance consistency check
                if len(df) > 1:
                    balance_changes = df['balance'].diff().abs()
                    large_changes = balance_changes > balance_changes.quantile(0.95)
                    if large_changes.sum() > 0:
                        print(f"  ⚠️  {large_changes.sum()} potentially suspicious balance changes")
                    else:
                        print("  ✅ Balance changes look consistent")
                
            else:
                print("  ❌ Failed to parse any records")
                
        except Exception as e:
            print(f"  ❌ Error: {str(e)}")
    
    print("\n" + "=" * 40)
    print("✅ Validation complete!")

def clean_csv_file(file_path):
    """Clean a specific CSV file"""
    print(f"🧹 Cleaning: {os.path.basename(file_path)}")
    
    try:
        # Read the original file
        df = pd.read_csv(file_path)
        original_count = len(df)
        
        # Clean column names
        df.columns = df.columns.str.strip().str.lower()
        
        # Remove completely empty rows
        df = df.dropna(how='all')
        
        # Create backup
        backup_path = file_path + '.backup'
        df.to_csv(backup_path, index=False)
        
        print(f"  📊 Original: {original_count} rows")
        print(f"  📊 Cleaned: {len(df)} rows")
        print(f"  💾 Backup saved as: {os.path.basename(backup_path)}")
        
        # Save cleaned file
        df.to_csv(file_path, index=False)
        print(f"  ✅ Cleaned file saved")
        
    except Exception as e:
        print(f"  ❌ Error cleaning file: {str(e)}")

if __name__ == "__main__":
    print("🔧 Finance Dashboard - Data Validation Tool")
    print("=" * 50)
    
    if not os.path.exists("data"):
        print("❌ Data directory not found. Please create a 'data/' folder and add your CSV files.")
    else:
        validate_csv_files()
        
        print("\n🔧 Would you like to clean the CSV files? (This will create backups)")
        response = input("Enter 'y' to proceed: ").lower().strip()
        
        if response == 'y':
            files = glob.glob("data/*.csv")
            for file_path in files:
                clean_csv_file(file_path)
            print("\n✅ All files have been cleaned!")
        else:
            print("📋 Skipping cleanup. Files remain unchanged.")
