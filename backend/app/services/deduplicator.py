"""In-memory hash-based deduplicator — used during a single job run."""


class Deduplicator:
    def __init__(self) -> None:
        self._seen_urls: set[str] = set()
        self._seen_hashes: set[str] = set()

    def seen_url(self, url: str) -> bool:
        if url in self._seen_urls:
            return True
        self._seen_urls.add(url)
        return False

    def seen_hash(self, sha1: str) -> bool:
        if sha1 in self._seen_hashes:
            return True
        self._seen_hashes.add(sha1)
        return False
