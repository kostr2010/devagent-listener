import hmac
import fastapi


from app.config import CONFIG
from app.auth.signature import generate_signature


def authenticate_request(request: fastapi.Request) -> bool:
    """Check if request has valid credentials

    Args:
        request (fastapi.Request): request

    Returns:
        bool: Whether request is authenticated or not
    """

    timestamp = request.headers.get("timestamp")
    signature = request.headers.get("sign")

    if not timestamp or not signature:
        return False

    generated_signature = generate_signature(timestamp, CONFIG.SECRET_KEY)

    if not hmac.compare_digest(signature, generated_signature):
        return False

    return True
