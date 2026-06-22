from nacl.exceptions import BadSignatureError
from nacl.signing import VerifyKey


def verify_telnyx_signature(public_key_hex: str, timestamp: str, signature_hex: str, body: bytes) -> bool:
    if not public_key_hex:
        return True
    if not timestamp or not signature_hex:
        return False

    try:
        verify_key = VerifyKey(bytes.fromhex(public_key_hex))
        signature = bytes.fromhex(signature_hex)
    except ValueError:
        return False

    candidates = [
        timestamp.encode("utf-8") + b"." + body,
        timestamp.encode("utf-8") + b"|" + body,
        timestamp.encode("utf-8") + body,
        body,
    ]
    for candidate in candidates:
        try:
            verify_key.verify(candidate, signature)
            return True
        except BadSignatureError:
            continue
    return False

