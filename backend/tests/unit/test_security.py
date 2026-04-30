from app.core.security import hash_password, verify_password, verify_totp


def test_password_hash_round_trip() -> None:
    hashed = hash_password("correct horse battery staple")
    assert verify_password("correct horse battery staple", hashed)
    assert not verify_password("wrong password", hashed)


def test_totp_rejects_bad_code() -> None:
    assert not verify_totp("JBSWY3DPEHPK3PXP", "000000")

