import pandas as pd

def format_indian_currency(amount):
    """Format currency in Indian number system with proper comma placement"""
    if pd.isna(amount) or amount == 0:
        return "₹0"
    
    # Handle negative numbers
    is_negative = amount < 0
    amount = abs(amount)
    
    # Convert to string and split into integer and decimal parts
    amount_str = f"{amount:.2f}"
    integer_part, decimal_part = amount_str.split('.')
    
    # Indian number system formatting
    if len(integer_part) <= 3:
        # Less than 1000
        formatted = integer_part
    elif len(integer_part) <= 5:
        # Thousands (1,000 to 99,999)
        formatted = f"{integer_part[:-3]},{integer_part[-3:]}"
    elif len(integer_part) <= 7:
        # Lakhs (1,00,000 to 99,99,999)
        formatted = f"{integer_part[:-5]},{integer_part[-5:-3]},{integer_part[-3:]}"
    else:
        # Crores and above (10,000,000+)
        if len(integer_part) <= 9:
            # Up to 99 crores
            formatted = f"{integer_part[:-7]},{integer_part[-7:-5]},{integer_part[-5:-3]},{integer_part[-3:]}"
        else:
            # More than 99 crores - handle in groups of 2 from right after first 7 digits
            crores_part = integer_part[:-7]
            lakhs_thousands = integer_part[-7:]
            
            # Format crores part (add commas every 2 digits from right)
            if len(crores_part) > 2:
                # Insert commas every 2 digits from right in crores
                crores_formatted = ""
                for i, digit in enumerate(reversed(crores_part)):
                    if i > 0 and i % 2 == 0:
                        crores_formatted = "," + crores_formatted
                    crores_formatted = digit + crores_formatted
            else:
                crores_formatted = crores_part
            
            formatted = f"{crores_formatted},{lakhs_thousands[:2]},{lakhs_thousands[2:5]},{lakhs_thousands[5:]}"
    
    # Add decimal part if not .00
    if decimal_part != "00":
        formatted = f"{formatted}.{decimal_part}"
    
    # Add currency symbol and negative sign if needed
    result = f"₹{formatted}"
    if is_negative:
        result = f"-{result}"
    
    return result

def format_indian_number(amount):
    """Format number in Indian system without currency symbol"""
    if pd.isna(amount) or amount == 0:
        return "0"
    
    # Handle negative numbers
    is_negative = amount < 0
    amount = abs(amount)
    
    # Convert to string (no decimal places for counts)
    integer_part = str(int(amount))
    
    # Indian number system formatting
    if len(integer_part) <= 3:
        formatted = integer_part
    elif len(integer_part) <= 5:
        formatted = f"{integer_part[:-3]},{integer_part[-3:]}"
    elif len(integer_part) <= 7:
        formatted = f"{integer_part[:-5]},{integer_part[-5:-3]},{integer_part[-3:]}"
    else:
        # Crores and above (10,000,000+)
        if len(integer_part) <= 9:
            # Up to 99 crores
            formatted = f"{integer_part[:-7]},{integer_part[-7:-5]},{integer_part[-5:-3]},{integer_part[-3:]}"
        else:
            # More than 99 crores
            crores_part = integer_part[:-7]
            lakhs_thousands = integer_part[-7:]
            
            # Format crores part (add commas every 2 digits from right)
            if len(crores_part) > 2:
                crores_formatted = ""
                for i, digit in enumerate(reversed(crores_part)):
                    if i > 0 and i % 2 == 0:
                        crores_formatted = "," + crores_formatted
                    crores_formatted = digit + crores_formatted
            else:
                crores_formatted = crores_part
            
            formatted = f"{crores_formatted},{lakhs_thousands[:2]},{lakhs_thousands[2:5]},{lakhs_thousands[5:]}"
    
    if is_negative:
        formatted = f"-{formatted}"
    
    return formatted
