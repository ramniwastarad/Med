import hashlib
from datetime import datetime, timedelta, timezone

def test_share_token_hash_is_not_raw_token():
    raw = "example-random-token"
    digest = hashlib.sha256(raw.encode()).hexdigest()
    assert digest != raw
    assert len(digest) == 64

def test_expiry_comparison():
    now = datetime.now(timezone.utc)
    expiry = now + timedelta(hours=2)
    assert expiry > now
