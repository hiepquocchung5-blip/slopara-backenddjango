import re

def validate_and_identify_operator(phone):
    """
    Validates Myanmar phone number and returns the operator.
    Relaxed for development to allow testing with generic 09 numbers.
    """
    # 1. Strip the prefix safely
    if phone.startswith('+959'):
        phone = phone[4:]
    elif phone.startswith('959'):
        phone = phone[3:]
    elif phone.startswith('09'):
        phone = phone[2:]
    else:
        return False, "Phone number must start with 09, 959, or +959."

    # 2. Basic length validation (7 to 9 digits after prefix is standard)
    if not re.match(r'^\d{7,9}$', phone):
        return False, "Invalid phone number length. Must be 9 to 11 digits total."

    # 3. Identify Operator (Optional, defaults to Unknown/Test)
    operators = {
        'Ooredoo/U9': r'^(94|95|96|97)\d{7}$',
        'Telenor/Atom': r'^(76|77|78|79)\d{7}$',
        'MPT': r'^(42|43|44|45|50|51|52|53|54|55|87|88|89)\d{7}$',
        'Mytel': r'^(66|67|68|69)\d{7}$'
    }

    operator_name = "Unknown / Test Network"
    for op_name, pattern in operators.items():
        if re.match(pattern, phone):
            operator_name = op_name
            break
            
    # 4. Standardize format to 09XXXXXXXX for database consistency
    normalized_phone = f"09{phone}"
    return True, {"operator": operator_name, "normalized": normalized_phone}