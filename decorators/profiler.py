"""
Profiler decorator — logs execution time, CPU usage, and memory usage
to a uniquely-named JSON log file per runtime session.
"""

import time
import json
import psutil
import uuid
import threading
from pathlib import Path


class Profiler:
    """A simple profiler that logs function execution details to a file."""
    
    def __init__(self, log_dir="decorators/logs"):
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)

        # Generate unique file: profile_<timestamp>_<random>.log
        random_id = uuid.uuid4().hex[:8]
        timestamp = int(time.time())
        self.log_path = log_dir / f"profile_{timestamp}_{random_id}.log"

        self.lock = threading.Lock()

        # Initialize file
        self.log_path.write_text("[]", encoding="utf-8")

    def _append(self, record):
        with self.lock:
            try:
                data = json.loads(self.log_path.read_text())
            except Exception:
                data = []

            data.append(record)
            self.log_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def record(self, name, start, end, meta=None):
        """Record a profiling entry."""
        duration_ms = (end - start) * 1000
        process = psutil.Process()

        record = {
            "timestamp": time.time(),
            "name": name,
            "duration_ms": round(duration_ms, 3),
            "cpu_percent": process.cpu_percent(interval=None),
            "memory_mb": round(process.memory_info().rss / 1e6, 3),
            "meta": meta or {},
        }

        self._append(record)


# Global profiler instance
profiler = Profiler()


def profile(name=None, meta_fn=None):
    """
    Decorator that logs timing + CPU/memory usage.
    """
    def wrapper(fn):
        def inner(*args, **kwargs):
            start = time.time()
            try:
                result = fn(*args, **kwargs)
                return result
            finally:
                end = time.time()
                meta = meta_fn(result, *args, **kwargs) if meta_fn else None
                profiler.record(name or fn.__name__, start, end, meta)
        return inner
    return wrapper
