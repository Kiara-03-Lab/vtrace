"""
vtrace - Reproducible traces for AI-assisted coding

Core schema definitions for the event trace system.
"""

from dataclasses import dataclass, field, asdict
from typing import Literal, Any
from datetime import datetime
import hashlib
import json


EventType = Literal["llm_call", "tool_call", "edit"]


@dataclass
class Event:
    """A single event in the trace."""
    type: EventType
    timestamp: str
    input: Any
    output: Any
    metadata: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, d: dict) -> "Event":
        return cls(**d)


@dataclass
class Session:
    """
    A reproducible session: S = (M, P₀, Σ, C₀)
    
    Where:
      M  = model identifier + version
      P₀ = initial prompt/context
      Σ  = ordered event trace
      C₀ = initial codebase hash
    """
    session_id: str
    model: str
    codebase_hash: str
    initial_context: str = ""
    events: list[Event] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def append(self, event: Event) -> None:
        """Append event to trace (monoid operation)."""
        self.events.append(event)
    
    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "model": self.model,
            "codebase_hash": self.codebase_hash,
            "initial_context": self.initial_context,
            "created_at": self.created_at,
            "events": [e.to_dict() for e in self.events],
        }
    
    @classmethod
    def from_dict(cls, d: dict) -> "Session":
        events = [Event.from_dict(e) for e in d.get("events", [])]
        return cls(
            session_id=d["session_id"],
            model=d["model"],
            codebase_hash=d["codebase_hash"],
            initial_context=d.get("initial_context", ""),
            created_at=d.get("created_at", ""),
            events=events,
        )


def hash_content(content: str | bytes) -> str:
    """SHA256 hash of content."""
    if isinstance(content, str):
        content = content.encode()
    return f"sha256:{hashlib.sha256(content).hexdigest()[:16]}"


def hash_directory(path: str) -> str:
    """Hash a directory's content (simplified: just hash file listing)."""
    import os
    parts = []
    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        for f in sorted(files):
            if not f.startswith('.'):
                fpath = os.path.join(root, f)
                try:
                    with open(fpath, 'rb') as fp:
                        parts.append(f"{fpath}:{hashlib.sha256(fp.read()).hexdigest()[:8]}")
                except:
                    pass
    return hash_content("\n".join(parts))
