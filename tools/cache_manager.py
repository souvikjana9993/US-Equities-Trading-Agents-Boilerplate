import time
from typing import Dict, Any, Optional

class ResearchCache:
    def __init__(self, expiry_seconds: int = 3600):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.expiry_seconds = expiry_seconds

    def _get_key(self, ticker: str, period: str) -> str:
        return f"{ticker.upper()}_{period}"

    def get(self, ticker: str, period: str) -> Optional[Any]:
        key = self._get_key(ticker, period)
        if key in self.cache:
            entry = self.cache[key]
            if time.time() - entry["timestamp"] < self.expiry_seconds:
                return entry["data"]
            else:
                del self.cache[key]
        return None

    def set(self, ticker: str, period: str, data: Any):
        key = self._get_key(ticker, period)
        self.cache[key] = {
            "data": data,
            "timestamp": time.time()
        }

# Global cache instance
global_research_cache = ResearchCache()
