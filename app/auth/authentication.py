import hmac
import hashlib
import fastapi
import base64


from app.config import CONFIG


def authenticate_request(request: fastapi.Request) -> bool:
    """Check if request has valid credentials

    Args:
        request (fastapi.Request): request

    Returns:
        bool: Whether request is authenticated or not
    """

    timestamp = request.headers.get("timestamp")
    signature = request.headers.get("sign")

    print(timestamp)

    if not timestamp or not signature:
        return False

    generated_signature = generate_signature(timestamp, CONFIG.SECRET_KEY)

    print(signature)
    print(generated_signature)

    if not hmac.compare_digest(signature, generated_signature):
        return False

    return True


def generate_signature(timestamp: str, key: str) -> str:
    hash = hmac.new(
        key=key.encode("utf-8"),
        msg=f"{timestamp}:{key}".encode("utf-8"),
        digestmod=hashlib.sha256,
    )

    hexdigest = hash.hexdigest().encode("utf-8")

    encoded_digest = base64.urlsafe_b64encode(hexdigest).decode("utf-8")

    return encoded_digest
