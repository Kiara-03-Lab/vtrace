"""
vtrace - Event Logger

Captures events and appends to the session trace.
"""

from datetime import datetime
from pathlib import Path
import json
import yaml
import os

from .schema import Session, Event, hash_content, hash_directory


class Logger:
    """
    Append-only event logger.
    
    Maintains the invariant: all non-deterministic outputs are captured.
    """
    
    def __init__(self, session: Session, trace_file: Path | str | None = None):
        self.session = session
        self.trace_file = Path(trace_file) if trace_file else None
        
        if self.trace_file:
            self.trace_file.parent.mkdir(parents=True, exist_ok=True)
            self._save()
    
    @classmethod
    def new_session(
        cls,
        model: str,
        codebase_path: str | None = None,
        trace_file: str | None = None,
        initial_context: str = "",
    ) -> "Logger":
        """Start a new recording session."""
        import uuid
        
        session_id = str(uuid.uuid4())[:8]
        codebase_hash = hash_directory(codebase_path) if codebase_path else "none"
        
        session = Session(
            session_id=session_id,
            model=model,
            codebase_hash=codebase_hash,
            initial_context=initial_context,
        )
        
        if trace_file is None:
            trace_file = f".vtrace/{session_id}.yaml"
        
        return cls(session, trace_file)
    
    @classmethod
    def load(cls, trace_file: str | Path) -> "Logger":
        """Load existing session from trace file."""
        trace_file = Path(trace_file)
        with open(trace_file) as f:
            data = yaml.safe_load(f)
        session = Session.from_dict(data)
        return cls(session, trace_file)
    
    def _save(self) -> None:
        """Persist session to disk."""
        if self.trace_file:
            with open(self.trace_file, 'w') as f:
                yaml.dump(self.session.to_dict(), f, default_flow_style=False, sort_keys=False)
    
    def _now(self) -> str:
        return datetime.utcnow().isoformat()
    
    def log_llm_call(
        self,
        prompt: str,
        response: str,
        temperature: float = 0.0,
        **kwargs
    ) -> Event:
        """
        Log an LLM call.
        
        Captures the full response (non-deterministic output).
        """
        event = Event(
            type="llm_call",
            timestamp=self._now(),
            input=prompt,
            output=response,
            metadata={
                "temperature": temperature,
                "response_hash": hash_content(response),
                **kwargs
            }
        )
        self.session.append(event)
        self._save()
        return event
    
    def log_tool_call(
        self,
        tool_name: str,
        args: dict | str,
        output: str,
        **kwargs
    ) -> Event:
        """
        Log a tool call (e.g., pytest, grep, shell command).
        """
        event = Event(
            type="tool_call",
            timestamp=self._now(),
            input={"tool": tool_name, "args": args},
            output=output,
            metadata=kwargs
        )
        self.session.append(event)
        self._save()
        return event
    
    def log_edit(
        self,
        file_path: str,
        diff: str,
        **kwargs
    ) -> Event:
        """
        Log a code edit.
        """
        event = Event(
            type="edit",
            timestamp=self._now(),
            input=file_path,
            output=diff,
            metadata=kwargs
        )
        self.session.append(event)
        self._save()
        return event
    
    @property
    def event_count(self) -> int:
        return len(self.session.events)


# Convenience wrapper for LLM calls
class TracedLLM:
    """
    Wrapper that intercepts LLM calls and logs them.
    
    Usage:
        logger = Logger.new_session(model="gpt-4")
        llm = TracedLLM(logger, actual_llm_function)
        response = llm("Write a function...")
    """
    
    def __init__(self, logger: Logger, llm_fn):
        self.logger = logger
        self.llm_fn = llm_fn
    
    def __call__(self, prompt: str, **kwargs) -> str:
        response = self.llm_fn(prompt, **kwargs)
        self.logger.log_llm_call(
            prompt=prompt,
            response=response,
            **kwargs
        )
        return response
