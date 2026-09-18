"""Perceptual Hash Dictionary Cache backed by Redis (Task Card T1.4)."""

import json
from pathlib import Path
from typing import Optional
import imagehash
from PIL import Image

try:
    import redis
    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False


class PHashRedisCache:
    """Redis dictionary cache for Stage 1 perceptual hash coarse filtering."""

    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or "redis://localhost:6379/0"
        self._client = None
        self._local_cache: dict[str, str] = {}  # key -> phash hex

        if HAS_REDIS:
            try:
                self._client = redis.Redis.from_url(self.redis_url, decode_responses=True)
                self._client.ping()
            except Exception:
                self._client = None

    def add(self, image_id: str, phash_hex: str) -> None:
        """Store image perceptual hash in Redis and local cache."""
        self._local_cache[image_id] = phash_hex
        if self._client:
            try:
                self._client.hset("traceai:phash_dict", image_id, phash_hex)
            except Exception:
                pass

    def load_dictionary(self, dict_data: dict[str, str]) -> None:
        """Batch load perceptual hash dictionary."""
        self._local_cache.update(dict_data)
        if self._client and dict_data:
            try:
                self._client.hset("traceai:phash_dict", mapping=dict_data)
            except Exception:
                pass

    def get_all(self) -> dict[str, str]:
        """Retrieve full dictionary from Redis (or local cache)."""
        if self._client:
            try:
                data = self._client.hgetall("traceai:phash_dict")
                if data:
                    self._local_cache.update(data)
                    return data
            except Exception:
                pass
        return dict(self._local_cache)

    def query_hamming(
        self,
        query_phash: imagehash.ImageHash,
        max_distance: int = 5,
    ) -> list[tuple[str, int]]:
        """Find all indexed images with Hamming distance <= max_distance.
        
        Returns list of (image_id, hamming_distance) sorted by distance.
        """
        matches = []
        all_hashes = self.get_all()

        for img_id, h_hex in all_hashes.items():
            try:
                target_hash = imagehash.hex_to_hash(h_hex)
                dist = int(query_phash - target_hash)
                if dist <= max_distance:
                    matches.append((img_id, dist))
            except Exception:
                continue

        matches.sort(key=lambda x: x[1])
        return matches
