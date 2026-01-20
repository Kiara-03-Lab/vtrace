"""
vtrace - Tests

Property-based tests for replay correctness.

Key properties:
1. Replay is deterministic: replay(S) == replay(S)
2. Trace is complete: all info needed for replay is in trace
3. Idempotence: applying same trace twice gives same result
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.schema import Session, Event, llm_call, tool_call, edit
from src.logger import TraceLogger
from src.replayer import Replayer, replay_session, compare_sessions


def test_schema_roundtrip():
    """Test that session serializes and deserializes correctly."""
    session = Session(
        session_id="test-123",
        model="gpt-4",
        initial_prompt="Test session",
        codebase_hash="sha256:abc123"
    )
    session.append(llm_call("Hello", "Hi there!", model="gpt-4", temperature=0.2))
    session.append(tool_call("pytest", "-v", "PASSED"))
    session.append(edit("main.py", "- old\n+ new"))
    
    # Roundtrip through YAML
    yaml_str = session.to_yaml()
    restored = Session.from_yaml(yaml_str)
    
    assert restored.session_id == session.session_id
    assert restored.model == session.model
    assert len(restored.events) == 3
    assert restored.events[0].type == "llm_call"
    assert restored.events[1].type == "tool_call"
    assert restored.events[2].type == "edit"
    
    print("✓ Schema roundtrip test passed")


def test_replay_determinism():
    """Test that replaying the same session gives identical results."""
    session = Session(
        session_id="det-test",
        model="test",
        initial_prompt="",
        codebase_hash="none"
    )
    session.append(llm_call("prompt1", "response1"))
    session.append(edit("file.txt", "content"))
    session.append(tool_call("echo", "hello", "hello"))
    
    result1 = replay_session(session)
    result2 = replay_session(session)
    
    assert result1.final_state.files == result2.final_state.files
    assert result1.final_state.llm_responses == result2.final_state.llm_responses
    assert result1.final_state.tool_outputs == result2.final_state.tool_outputs
    
    print("✓ Replay determinism test passed")


def test_replay_llm_memoization():
    """Test that LLM calls are memoized (use recorded output)."""
    session = Session(
        session_id="memo-test",
        model="test",
        initial_prompt="",
        codebase_hash="none"
    )
    session.append(llm_call("What is 2+2?", "4"))
    session.append(llm_call("What is 3+3?", "6"))
    
    result = replay_session(session)
    
    # Replay should use recorded responses, not call LLM
    assert result.final_state.llm_responses == ["4", "6"]
    
    print("✓ LLM memoization test passed")


def test_edit_application():
    """Test that edits are applied correctly."""
    session = Session(
        session_id="edit-test",
        model="test",
        initial_prompt="",
        codebase_hash="none"
    )
    # Simple replacement (no diff markers)
    session.append(edit("new_file.py", "def hello():\n    print('hello')"))
    
    result = replay_session(session)
    
    assert "new_file.py" in result.final_state.files
    assert "def hello():" in result.final_state.files["new_file.py"]
    
    print("✓ Edit application test passed")


def test_session_comparison():
    """Test session comparison for equivalence."""
    s1 = Session(
        session_id="s1",
        model="test",
        initial_prompt="",
        codebase_hash="none"
    )
    s1.append(edit("file.txt", "hello"))
    
    s2 = Session(
        session_id="s2",  # Different ID
        model="test",
        initial_prompt="",
        codebase_hash="none"
    )
    s2.append(edit("file.txt", "hello"))  # Same edit
    
    comparison = compare_sessions(s1, s2)
    assert comparison["equivalent"] == True
    
    # Now make s2 different
    s3 = Session(
        session_id="s3",
        model="test",
        initial_prompt="",
        codebase_hash="none"
    )
    s3.append(edit("file.txt", "world"))  # Different content
    
    comparison2 = compare_sessions(s1, s3)
    assert comparison2["equivalent"] == False
    
    print("✓ Session comparison test passed")


def test_logger():
    """Test the trace logger."""
    import tempfile
    import os
    
    with tempfile.TemporaryDirectory() as tmpdir:
        trace_path = os.path.join(tmpdir, "trace.yaml")
        
        logger = TraceLogger(
            session_id="logger-test",
            model="test-model"
        )
        
        logger.log_llm_call("Hello", "Hi!")
        logger.log_tool_call("echo", "test", "test")
        logger.log_edit("test.py", "print('hello')")
        
        logger.save(trace_path)
        
        # Verify file exists and can be loaded
        assert os.path.exists(trace_path)
        
        from src.logger import load_session
        loaded = load_session(trace_path)
        
        assert loaded.session_id == "logger-test"
        assert len(loaded.events) == 3
        
    print("✓ Logger test passed")


def test_trace_hash_consistency():
    """Test that trace hashes are consistent."""
    session = Session(
        session_id="hash-test",
        model="test",
        initial_prompt="test",
        codebase_hash="abc"
    )
    session.append(llm_call("p", "r"))
    
    hash1 = session.trace_hash()
    hash2 = session.trace_hash()
    
    assert hash1 == hash2
    
    # Different content should give different hash
    session.append(llm_call("p2", "r2"))
    hash3 = session.trace_hash()
    
    assert hash1 != hash3
    
    print("✓ Trace hash consistency test passed")


def run_all_tests():
    """Run all tests."""
    print("Running vtrace tests...\n")
    
    test_schema_roundtrip()
    test_replay_determinism()
    test_replay_llm_memoization()
    test_edit_application()
    test_session_comparison()
    test_logger()
    test_trace_hash_consistency()
    
    print("\n✅ All tests passed!")


if __name__ == "__main__":
    run_all_tests()
