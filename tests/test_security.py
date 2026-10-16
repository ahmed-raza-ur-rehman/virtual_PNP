from pnp.security.secure_boot import sign_firmware, verify_firmware


def test_sign_verify():
    data = b"firmware"
    key = b"secret"
    sig = sign_firmware(data, key)
    assert verify_firmware(data, key, sig)
    assert not verify_firmware(data, key, b"bad")
