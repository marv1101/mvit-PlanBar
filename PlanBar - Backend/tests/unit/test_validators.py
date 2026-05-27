from app.utils.validators import validate_email, validate_hex_color


def test_validate_email_valid():
    assert validate_email("user@example.com") is True


def test_validate_email_invalid():
    assert validate_email("not-an-email") is False


def test_validate_hex_color_valid():
    assert validate_hex_color("#FF5733") is True


def test_validate_hex_color_lowercase():
    assert validate_hex_color("#aabbcc") is True


def test_validate_hex_color_invalid():
    assert validate_hex_color("red") is False


def test_validate_hex_color_no_hash():
    assert validate_hex_color("FFFFFF") is False
