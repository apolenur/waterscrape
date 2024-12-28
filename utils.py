import re
from typing import Tuple, List

def validate_addresses(addresses: List[str]) -> Tuple[List[str], List[str]]:
    """
    Validates a list of Baltimore addresses.
    
    Args:
        addresses: List of address strings to validate
        
    Returns:
        Tuple of (valid_addresses, invalid_addresses)
    """
    valid_addresses = []
    invalid_addresses = []
    
    for address in addresses:
        # Basic address validation for Baltimore
        # This is a simple validation - could be enhanced based on specific requirements
        if (
            re.match(r'^\d+\s+[A-Za-z0-9\s\.,]+$', address) and
            len(address) >= 5
        ):
            valid_addresses.append(address)
        else:
            invalid_addresses.append(address)
    
    return valid_addresses, invalid_addresses

def format_currency(value: str) -> str:
    """
    Formats a currency value consistently.
    
    Args:
        value: String representing a currency amount
        
    Returns:
        Formatted currency string
    """
    if value == 'N/A':
        return value
    
    try:
        # Remove any existing currency symbols and commas
        clean_value = value.replace('$', '').replace(',', '').strip()
        
        # Convert to float and format
        amount = float(clean_value)
        return f"${amount:,.2f}"
    except (ValueError, AttributeError):
        return value
