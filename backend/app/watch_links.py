import hashlib
import hmac

from .config import settings


def _sig(log_id: int) -> str:
    key = settings.secret_key.encode()  # ADJUST: use the name of your JWT secret setting
    return hmac.new(key, f"watch:{log_id}".encode(), hashlib.sha256).hexdigest()[:32]


def make_token(log_id: int) -> str:
    return f"{log_id}.{_sig(log_id)}"


def parse_token(token: str) -> int | None:
    log_id, _, sig = token.partition(".")
    if not (log_id.isascii() and log_id.isdigit()):
        return None
    if not hmac.compare_digest(sig.encode(), _sig(int(log_id)).encode()):
        return None
    return int(log_id)


def watch_url(log_id: int) -> str:
    return f"{settings.frontend_url}/watch/{make_token(log_id)}"