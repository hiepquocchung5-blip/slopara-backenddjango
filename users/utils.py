import re

def validate_and_identify_operator(phone):
    """
    Validates Myanmar phone number and returns the operator.
    Rejects 0911 and 0922 prefixes explicitly.
    Expected formats handled: 959XXXXXXXX, +959XXXXXXXX, 09XXXXXXXX.
    """
    if phone.startswith('+959'):
        phone = phone[4:]
    elif phone.startswith('959'):
        phone = phone[3:]
    elif phone.startswith('09'):
        phone = phone[2:]
    else:
        return False, "Invalid format. Must start with 09 or 959."

    if phone.startswith('11') or phone.startswith('22'):
        return False, "Prefix not allowed."

    operators = {
        'Ooredoo/U9': r'^(94|95|96|97)\d{7}$',
        'Telenor/Atom': r'^(76|77|78|79)\d{7}$',
        'MPT': r'^(42|43|44|45|50|51|52|53|54|55|87|88|89)\d{7}$',
        'Mytel': r'^(66|67|68|69)\d{7}$'
    }

    for operator, pattern in operators.items():
        if re.match(pattern, phone):
            normalized_phone = f"09{phone}"
            return True, {"operator": operator, "normalized": normalized_phone}
            
    return False, "Unknown or invalid operator prefix."