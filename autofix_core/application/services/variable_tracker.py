from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import time
import os
import hashlib
import re
import threading

# Configurable defaults (environment overrides)
SAFE_SERIALIZE_MAX_LEN: int = int(os.getenv("SAFE_SERIALIZE_MAX_LEN", "200"))
SECRET_KEYWORDS = re.compile(r"password|secret|token|passwd", re.I)


def safe_serialize(value: Any, max_len: int = SAFE_SERIALIZE_MAX_LEN) -> str:
    """
    Safely serialize a value for snapshots.

    - Uses repr() but catches exceptions from custom __repr__ implementations.
    - Truncates long outputs to max_len and appends a short fingerprint so changes
      can still be detected without keeping the full payload.
    - Returns a stable string that is safe to store and display.
    """
    try:
        s = repr(value)
    except Exception:
        return "<UNREPRABLE>"

    if len(s) <= max_len:
        return s

    # Truncate and add a short fingerprint to help detect changes
    try:
        h = hashlib.sha256(s.encode("utf-8", errors="ignore")).hexdigest()[:8]
    except Exception:
        h = "unkn"

    return f"{s[:max_len]}...<truncated:{h}>"


def redact_if_sensitive(name: str, value_str: str) -> str:
    """
    Very basic redaction for well-known sensitive variable names.
    This is intentionally conservative; adjust policy to product needs.
    """
    if SECRET_KEYWORDS.search(name):
        return "<REDACTED>"
    return value_str


@dataclass
class VariableSnapshot:
    """Single snapshot of a variable's state."""
    line_number: int
    variable_name: str
    value_str: str
    type_name: str
    timestamp: float = field(default_factory=time.time)


@dataclass
class VariableChange:
    """Represents a change in a variable's value."""
    line_number: int
    variable_name: str
    old_value: str
    new_value: str
    old_type: str
    new_type: str


class DummyLock:
    """A no-op context manager used when thread safety isn't required."""
    def __enter__(self):
        return None

    def __exit__(self, exc_type, exc, tb):
        return False


class VariableTracker:
    """
    Track variable changes throughout code execution.

    Improvements:
    - Uses safe_serialize to avoid executing expensive or unsafe __repr__/__str__
    - Keeps only serialized strings to avoid holding references to large objects
    - Supports caps: max_snapshots and max_changes (eviction of oldest entries)
    - Optional thread-safety via a threading.Lock
    """

    def __init__(
        self,
        max_snapshots: int = int(os.getenv("VARIABLE_TRACKER_MAX_SNAPSHOTS", "50000")),
        max_changes: int = int(os.getenv("VARIABLE_TRACKER_MAX_CHANGES", "10000")),
        safe_serialize_max_len: int = SAFE_SERIALIZE_MAX_LEN,
        thread_safe: bool = True,
    ):
        self.snapshots: List[VariableSnapshot] = []
        self.changes: List[VariableChange] = []
        # store serialized form in previous state to avoid holding large object refs
        self._previous_state: Dict[str, str] = {}
        self.max_snapshots = max_snapshots
        self.max_changes = max_changes
        self.safe_serialize_max_len = safe_serialize_max_len
        self._lock = threading.Lock() if thread_safe else None

    def _lock_ctx(self):
        return self._lock if self._lock is not None else DummyLock()

    def track_line(self, line_number: int, variables: Dict[str, Any]):
        """
        Track variable state after executing a line.

        Args:
            line_number: Current line number
            variables: Current variable state (locals)
        """
        with self._lock_ctx():
            for var_name, value in variables.items():
                # Skip internal variables
                if var_name.startswith("_"):
                    continue

                # Safe serialization and redaction
                value_str = safe_serialize(value, max_len=self.safe_serialize_max_len)
                value_str = redact_if_sensitive(var_name, value_str)
                type_name = type(value).__name__

                # Enforce snapshot cap: evict oldest snapshot if needed
                if len(self.snapshots) >= self.max_snapshots:
                    # Eviction policy: drop oldest snapshot
                    self.snapshots.pop(0)

                snapshot = VariableSnapshot(
                    line_number=line_number,
                    variable_name=var_name,
                    value_str=value_str,
                    type_name=type_name,
                )
                self.snapshots.append(snapshot)

                # Detect changes against serialized previous state
                old_serialized = self._previous_state.get(var_name)
                if old_serialized is not None and old_serialized != value_str:
                    if len(self.changes) >= self.max_changes:
                        self.changes.pop(0)
                    change = VariableChange(
                        line_number=line_number,
                        variable_name=var_name,
                        old_value=old_serialized,
                        new_value=value_str,
                        old_type="",  # we store types only when useful; avoid holding original objects
                        new_type=type_name,
                    )
                    self.changes.append(change)

                # Update previous state (serialized)
                self._previous_state[var_name] = value_str

    def get_variable_history(self, var_name: str) -> List[VariableSnapshot]:
        """Get all snapshots for a specific variable."""
        return [s for s in self.snapshots if s.variable_name == var_name]

    def get_variable_at_line(self, line_number: int) -> Dict[str, str]:
        """Get all variables at a specific line."""
        return {
            s.variable_name: s.value_str
            for s in self.snapshots
            if s.line_number == line_number
        }

    def get_changes_summary(self) -> Dict[str, List[Dict]]:
        """Get summary of all variable changes."""
        summary: Dict[str, List[Dict]] = {}
        for change in self.changes:
            summary.setdefault(change.variable_name, []).append({
                "line": change.line_number,
                "old": change.old_value,
                "new": change.new_value,
                "old_type": change.old_type,
                "new_type": change.new_type,
            })
        return summary

    def to_dict(self) -> Dict:
        """Convert to JSON-serializable dict."""
        return {
            "snapshots": [
                {
                    "line": s.line_number,
                    "variable": s.variable_name,
                    "value": s.value_str,
                    "type": s.type_name,
                    "timestamp": s.timestamp,
                }
                for s in self.snapshots
            ],
            "changes": [
                {
                    "line": c.line_number,
                    "variable": c.variable_name,
                    "old": c.old_value,
                    "new": c.new_value,
                    "type_change": c.old_type != c.new_type,
                }
                for c in self.changes
            ],
            "summary": self.get_changes_summary(),
        }