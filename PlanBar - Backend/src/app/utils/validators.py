import re


EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
HEX_COLOR_REGEX = re.compile(r"^#[0-9a-fA-F]{6}$")


def validate_email(email: str) -> bool:
    return bool(EMAIL_REGEX.match(email))


def validate_hex_color(color: str) -> bool:
    return bool(HEX_COLOR_REGEX.match(color))
