from app.utils.validators import not_empty


def test_validators_not_empty():
    assert not_empty("a") is True
    assert not_empty("  b  ") is True
    assert not_empty("") is False
    assert not_empty("   ") is False
    assert not_empty(None) is False
