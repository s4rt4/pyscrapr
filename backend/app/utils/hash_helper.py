"""Hash utilities."""
import hashlib


def sha1_bytes(data: bytes) -> str:
    return hashlib.sha1(data).hexdigest()
