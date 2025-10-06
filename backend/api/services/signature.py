from __future__ import annotations

from typing import Optional

import hmac
from hashlib import sha256


def verify_signature(secret: Optional[str], payload: bytes, signature: Optional[str]) -> bool:
    if not secret or not signature:
        return False
    digest = hmac.new(secret.encode('utf-8'), payload, sha256).hexdigest()
    expected = signature.lower().strip()
    return hmac.compare_digest(digest, expected)
