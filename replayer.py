"""
vtrace - Deterministic Replayer

Replay(S) := fold(Apply, C₀, Σ)

Key insight: We don't re-sample from the model.
We replay the recorded outputs deterministically.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable
import subprocess
import tempfile
import shutil
import os

from .schema import Session, Event


@dataclass
class ReplayState:
    """
    State maintained during replay.
    
    Represents the codebase at any point in the trace.
    """
    workspace: Path
    files: dict[str, str] = field(default_factory=dict)
    llm_outputs: list[str] = field(default_factory=list)
    tool_outputs: list[str] = field(default_factory=list)
    event_index: int = 0
    
    def get_file(self, path: str) -> str | None:
        return self.files.get(path)
    
    def set_file(self, path: str, content: str) -> None:
        self.files[path] = content
        # Also write to workspace
        fpath = self.workspace / path
        fpath.parent.mkdir(parents=True, exist_ok=True)
        fpath.write_text(content)


def apply_diff(content: str, diff: str) -> str:
    """
    Apply a unified diff to content.
    
    Simplified: handles basic +/- line format.
    For production, use proper diff library.
    """
    lines = content.split('\n') if content else []
    result = []
    
    for diff_line in diff.split('\n'):
        if diff_line.startswith('@@'):
            continue
        elif diff_line.startswith('-') and not diff_line.startswith('---'):
            # Remove line (skip it in output)
            old_line = diff_line[1:].strip()
            # Find and remove from lines
            for i, line in enumerate(lines):
                if line.strip() == old_line:
                    lines.pop(i)
                    break
        elif diff_line.startswith('+') and not diff_line.startswith('+++'):
            # Add line
            result.append(diff_line[1:])
        elif not diff_line.startswith('\\'):
            # Context line
            pass
    
    # Simple approach: just use the + lines as new content
    if result:
        return '\n'.join(result)
    return content


class Replayer:
    """
    Deterministic replay of a session trace.
    
    Theorem (informal):
        If Σ is complete and ordered, Replay(S) produces
        identical state regardless of when it's executed.
    
    Proof sketch:
        - LLM calls use memoized outputs (not re-sampled)
        - Tool calls use recorded outputs
        - Edits are deterministic transformations
        Therefore, fold(Apply, C₀, Σ) is deterministic.
    """
    
    def __init__(self, session: Session, workspace: Path | str | None = None):
        self.session = session
        
        if workspace:
            self.workspace = Path(workspace)
            self.workspace.mkdir(parents=True, exist_ok=True)
            self._temp_dir = None
        else:
            self._temp_dir = tempfile.mkdtemp(prefix="vtrace_replay_")
            self.workspace = Path(self._temp_dir)
        
        self.state = ReplayState(workspace=self.workspace)
        self.handlers: dict[str, Callable[[Event, ReplayState], None]] = {
            "llm_call": self._apply_llm_call,
            "tool_call": self._apply_tool_call,
            "edit": self._apply_edit,
        }
    
    def _apply_llm_call(self, event: Event, state: ReplayState) -> None:
        """
        Apply LLM call: just record the output (no re-sampling).
        """
        state.llm_outputs.append(event.output)
    
    def _apply_tool_call(self, event: Event, state: ReplayState) -> None:
        """
        Apply tool call: record the output (don't re-execute).
        
        Note: We could optionally re-execute and verify,
        but that breaks determinism if tools have side effects.
        """
        state.tool_outputs.append(event.output)
    
    def _apply_edit(self, event: Event, state: ReplayState) -> None:
        """
        Apply edit: transform file state.
        """
        file_path = event.input
        diff = event.output
        
        current = state.get_file(file_path) or ""
        new_content = apply_diff(current, diff)
        state.set_file(file_path, new_content)
    
    def step(self) -> Event | None:
        """
        Apply next event in trace.
        
        Returns the applied event, or None if trace exhausted.
        """
        if self.state.event_index >= len(self.session.events):
            return None
        
        event = self.session.events[self.state.event_index]
        handler = self.handlers.get(event.type)
        
        if handler:
            handler(event, self.state)
        
        self.state.event_index += 1
        return event
    
    def replay_all(self) -> ReplayState:
        """
        Replay entire trace: fold(Apply, C₀, Σ)
        
        Returns final state.
        """
        while self.step() is not None:
            pass
        return self.state
    
    def replay_to(self, index: int) -> ReplayState:
        """
        Replay up to (but not including) event at index.
        
        Useful for debugging: "what was state before event N?"
        """
        while self.state.event_index < index:
            if self.step() is None:
                break
        return self.state
    
    def cleanup(self) -> None:
        """Clean up temporary workspace."""
        if self._temp_dir and os.path.exists(self._temp_dir):
            shutil.rmtree(self._temp_dir)
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.cleanup()


def replay(session: Session, workspace: Path | str | None = None) -> ReplayState:
    """
    Convenience function: replay entire session.
    
    Usage:
        state = replay(session)
        print(state.files)
    """
    with Replayer(session, workspace) as r:
        return r.replay_all()


def compare_traces(s1: Session, s2: Session) -> dict:
    """
    Compare two session traces.
    
    Returns dict describing differences.
    """
    diffs = {
        "event_count": (len(s1.events), len(s2.events)),
        "model_match": s1.model == s2.model,
        "event_diffs": []
    }
    
    for i, (e1, e2) in enumerate(zip(s1.events, s2.events)):
        if e1.type != e2.type:
            diffs["event_diffs"].append({
                "index": i,
                "type": "type_mismatch",
                "values": (e1.type, e2.type)
            })
        elif e1.output != e2.output:
            diffs["event_diffs"].append({
                "index": i,
                "type": "output_mismatch",
                "event_type": e1.type
            })
    
    return diffs
