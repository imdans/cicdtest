import pyotp


def generate_mfa_secret():
    return pyotp.random_base32()


def verify_totp(secret, token):
    try:
        totp = pyotp.TOTP(secret)
        return totp.verify(token, valid_window=1)
    except Exception:
        return False
