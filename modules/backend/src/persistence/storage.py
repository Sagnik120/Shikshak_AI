import os
from abc import ABC, abstractmethod
from typing import Optional


class StorageAdapter(ABC):
    """Abstract interface for file/binary artifact storage (Contract §14 style)."""

    @abstractmethod
    def put(self, key: str, data: bytes) -> str:
        """Store bytes under key and return persistent path/identifier."""
        pass

    @abstractmethod
    def get(self, key: str) -> Optional[bytes]:
        """Retrieve bytes stored under key, or None if absent."""
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete bytes stored under key. Return True if deleted, False if not found."""
        pass


class LocalStorageAdapter(StorageAdapter):
    """Local filesystem storage adapter for hackathon MVP."""

    def __init__(self, base_dir: str = "data/storage"):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

    def _resolve_path(self, key: str) -> str:
        # Sanitize key to prevent path traversal
        clean_key = os.path.basename(key)
        return os.path.join(self.base_dir, clean_key)

    def put(self, key: str, data: bytes) -> str:
        path = self._resolve_path(key)
        with open(path, "wb") as f:
            f.write(data)
        return path

    def get(self, key: str) -> Optional[bytes]:
        path = self._resolve_path(key)
        if not os.path.exists(path):
            return None
        with open(path, "rb") as f:
            return f.read()

    def delete(self, key: str) -> bool:
        path = self._resolve_path(key)
        if os.path.exists(path):
            os.remove(path)
            return True
        return False
