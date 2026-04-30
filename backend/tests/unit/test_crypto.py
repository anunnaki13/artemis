from app.core.crypto import decrypt_secret, encrypt_secret, mask_secret


def test_encrypt_decrypt_secret_round_trip() -> None:
    encrypted = encrypt_secret("super-secret-value")
    assert encrypted != "super-secret-value"
    assert decrypt_secret(encrypted) == "super-secret-value"


def test_mask_secret() -> None:
    assert mask_secret(None) is None
    assert mask_secret("short") == "****"
    assert mask_secret("abcd1234wxyz") == "abcd****wxyz"
