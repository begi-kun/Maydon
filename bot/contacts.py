import re

def verified_contact_phone(sender_id: int, contact_user_id: int | None, phone: str) -> str:
    """Only accept the Telegram contact belonging to the authenticated sender."""
    if not contact_user_id or contact_user_id != sender_id:
        raise ValueError('Share your own Telegram contact')
    normalized = re.sub(r'[\s()-]', '', phone)
    if not re.fullmatch(r'\+?[0-9]{7,15}', normalized):
        raise ValueError('Invalid phone number')
    return '+' + normalized.lstrip('+')
