import hmac
import hashlib
import base64


def generate_signature(timestamp: str, key: str) -> str:
    hash = hmac.new(
        key=key.encode("utf-8"),
        msg=f"{timestamp}:{key}".encode("utf-8"),
        digestmod=hashlib.sha256,
    )

    hexdigest = hash.hexdigest().encode("utf-8")

    encoded_digest = base64.urlsafe_b64encode(hexdigest).decode("utf-8")

    return encoded_digest
