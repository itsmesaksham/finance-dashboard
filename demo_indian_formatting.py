#!/usr/bin/env python3
"""
Indian Number Formatting Demo
Shows how the enhanced finance dashboard now uses Indian number system formatting.
"""

from indian_formatting import format_indian_currency, format_indian_number

def demo_indian_formatting():
    print("🇮🇳 INDIAN NUMBER SYSTEM FORMATTING DEMO")
    print("=" * 50)
    print()
    
    # Sample amounts to demonstrate formatting
    sample_amounts = [
        500,
        1500,
        15000,
        150000,
        1500000,
        15000000,
        150000000,
        1500000000
    ]
    
    print("💰 CURRENCY FORMATTING EXAMPLES:")
    print("-" * 35)
    print(f"{'Amount':<12} {'International':<18} {'Indian System':<20}")
    print("-" * 35)
    
    for amount in sample_amounts:
        international = f"₹{amount:,}"
        indian = format_indian_currency(amount)
        print(f"{amount:<12} {international:<18} {indian:<20}")
    
    print()
    print("🔢 NUMBER FORMATTING EXAMPLES:")
    print("-" * 35)
    print(f"{'Number':<12} {'International':<18} {'Indian System':<20}")
    print("-" * 35)
    
    for amount in sample_amounts:
        international = f"{amount:,}"
        indian = format_indian_number(amount)
        print(f"{amount:<12} {international:<18} {indian:<20}")
    
    print()
    print("💡 KEY DIFFERENCES:")
    print("-" * 20)
    print("• International: 1,000 | 10,000 | 100,000 | 1,000,000")
    print("• Indian System: 1,000 | 10,000 | 1,00,000 | 10,00,000")
    print()
    print("📊 IN YOUR DASHBOARD:")
    print("-" * 25)
    print("✅ All amounts now use Indian comma placement")
    print("✅ Hover tooltips show Indian formatted values")
    print("✅ Transaction tables use Indian formatting")
    print("✅ Account summaries use Indian formatting")
    print("✅ Metrics and charts use Indian formatting")
    print()
    print("🎯 EXAMPLES IN CONTEXT:")
    print("-" * 25)
    print(f"• Balance: {format_indian_currency(1234567.89)}")
    print(f"• Large Transfer: {format_indian_currency(5000000)}")
    print(f"• Monthly Expenses: {format_indian_currency(45000)}")
    print(f"• Transaction Count: {format_indian_number(1234)} transactions")

if __name__ == "__main__":
    demo_indian_formatting()
