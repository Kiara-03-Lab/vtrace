"""
Property-based tests for vtrace.

Key properties to verify:
1. Replay is deterministic (same trace → same result)
2. Replay is idempotent
3. Trace serialization roundtrips correctly
"""

import sys
sys.path.insert(0, '.')

from vtrace import Session, Event, Logger, Replayer, replay


def test_session_roundtrip():
    """Session serializes and deserializes correctly."""
    session = Session(
        session_id="test123",
        model="gpt-4",
        codebase_hash="sha256:abc",
        initial_context="test context"
    )
    session.append(Event(
        type="llm_call",
        timestamp="2024-01-01T00:00:00",
        input="prompt",
        output="response",
        metadata={"temp": 0.5}
    ))
    
    # Roundtrip
    data = session.to_dict()
    restored = Session.from_dict(data)
    
    assert restored.session_id == session.session_id
    assert restored.model == session.model
    assert len(restored.events) == 1
    assert restored.events[0].type == "llm_call"
    assert restored.events[0].output == "response"
    print("✓ test_session_roundtrip")


def test_replay_determinism():
    """Same trace replays to same state."""
    session = Session(
        session_id="det_test",
        model="test",
        codebase_hash="none"
    )
    session.append(Event(
        type="edit",
        timestamp="t1",
        input="file.py",
        output="+print('hello')",
        metadata={}
    ))
    session.append(Event(
        type="llm_call",
        timestamp="t2",
        input="prompt",
        output="response",
        metadata={}
    ))
    
    # Replay twice
    state1 = replay(session)
    state2 = replay(session)
    
    assert state1.files == state2.files
    assert state1.llm_outputs == state2.llm_outputs
    print("✓ test_replay_determinism")


def test_event_ordering():
    """Events maintain order."""
    logger = Logger.new_session(model="test", trace_file="/tmp/test_order.yaml")
    
    logger.log_llm_call(prompt="p1", response="r1")
    logger.log_llm_call(prompt="p2", response="r2")
    logger.log_llm_call(prompt="p3", response="r3")
    
    assert len(logger.session.events) == 3
    assert logger.session.events[0].input == "p1"
    assert logger.session.events[1].input == "p2"
    assert logger.session.events[2].input == "p3"
    print("✓ test_event_ordering")


def test_empty_session():
    """Empty session replays to empty state."""
    session = Session(
        session_id="empty",
        model="test",
        codebase_hash="none"
    )
    
    state = replay(session)
    assert state.files == {}
    assert state.llm_outputs == []
    print("✓ test_empty_session")


def test_logger_persistence():
    """Logger saves to file correctly."""
    import yaml
    
    logger = Logger.new_session(model="gpt-4", trace_file="/tmp/persist_test.yaml")
    logger.log_llm_call(prompt="test", response="result")
    
    # Load and verify
    with open("/tmp/persist_test.yaml") as f:
        data = yaml.safe_load(f)
    
    assert data["model"] == "gpt-4"
    assert len(data["events"]) == 1
    print("✓ test_logger_persistence")


def run_all():
    print("Running vtrace tests...\n")
    test_session_roundtrip()
    test_replay_determinism()
    test_event_ordering()
    test_empty_session()
    test_logger_persistence()
    print("\nAll tests passed!")


if __name__ == "__main__":
    run_all()
