"""
vtrace - Reproducible traces for AI-assisted coding

"Git for vibe coding sessions."

Core idea:
    Non-reproducibility stems from lacking a canonical trace.
    We fix this by recording all non-deterministic outputs
    and replaying deterministically.

Usage:
    from vtrace import Logger, replay
    
    # Record a session
    logger = Logger.new_session(model="gpt-4")
    logger.log_llm_call(prompt="...", response="...")
    logger.log_edit(file_path="main.py", diff="...")
    
    # Replay later
    state = replay(logger.session)
"""

from .schema import Session, Event, hash_content, hash_directory
from .logger import Logger, TracedLLM
from .replayer import Replayer, replay, compare_traces

__version__ = "0.1.0"
__all__ = [
    "Session",
    "Event", 
    "Logger",
    "TracedLLM",
    "Replayer",
    "replay",
    "compare_traces",
    "hash_content",
    "hash_directory",
]
