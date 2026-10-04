import re

def normalize_phone(phone: str) -> str:
    """Normalize Philippine phone numbers by stripping non-digits and standardizing +63 to 0."""
    if not phone:
        return ""
    digits = re.sub(r"\D", "", phone.strip())
    # Standardize Philippine mobile numbers: 639XXXXXXXXX -> 09XXXXXXXXX
    if digits.startswith("63") and len(digits) == 12:
        digits = "0" + digits[2:]
    return digits

def normalize_email(email: str) -> str:
    """Normalize email by trimming whitespace and lowercasing."""
    return email.strip().lower() if email else ""
