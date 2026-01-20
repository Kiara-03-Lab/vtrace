#!/usr/bin/env python3
"""
Demo: Prove reproducibility works.

This script:
1. Creates a session with some events
2. Replays it
3. Shows the replay produces deterministic results
"""

import sys
sys.path.insert(0, '.')

from vtrace import Logger, Replayer, replay


def main():
    print("=" * 60)
    print("vtrace Demo: Reproducible AI Coding Traces")
    print("=" * 60)
    
    # 1. Create a new session
    print("\n[1] Creating new session...")
    logger = Logger.new_session(
        model="gpt-4-turbo",
        trace_file="demo_trace.yaml",
        initial_context="Building a calculator app"
    )
    print(f"    Session ID: {logger.session.session_id}")
    
    # 2. Simulate some vibe-coding events
    print("\n[2] Recording events...")
    
    # LLM call: ask for code
    logger.log_llm_call(
        prompt="Write a Python function to add two numbers",
        response="""def add(a: int, b: int) -> int:
    \"\"\"Add two numbers.\"\"\"
    return a + b""",
        temperature=0.2
    )
    print("    Logged: LLM call (add function)")
    
    # Edit: create the file
    logger.log_edit(
        file_path="calc.py",
        diff="""+def add(a: int, b: int) -> int:
+    \"\"\"Add two numbers.\"\"\"
+    return a + b"""
    )
    print("    Logged: Edit (calc.py created)")
    
    # Tool call: run tests
    logger.log_tool_call(
        tool_name="pytest",
        args="-v calc.py",
        output="PASSED: test_add"
    )
    print("    Logged: Tool call (pytest)")
    
    # Another LLM call
    logger.log_llm_call(
        prompt="Add a subtract function",
        response="""def subtract(a: int, b: int) -> int:
    \"\"\"Subtract b from a.\"\"\"
    return a - b""",
        temperature=0.2
    )
    print("    Logged: LLM call (subtract function)")
    
    # Another edit
    logger.log_edit(
        file_path="calc.py",
        diff="""+def subtract(a: int, b: int) -> int:
+    \"\"\"Subtract b from a.\"\"\"
+    return a - b"""
    )
    print("    Logged: Edit (calc.py updated)")
    
    print(f"\n    Total events: {logger.event_count}")
    
    # 3. Show the trace file
    print("\n[3] Trace file contents:")
    print("-" * 40)
    with open("demo_trace.yaml") as f:
        content = f.read()
        # Show first 1500 chars
        print(content[:1500])
        if len(content) > 1500:
            print("    ... (truncated)")
    print("-" * 40)
    
    # 4. Replay the session
    print("\n[4] Replaying session...")
    state = replay(logger.session, workspace="./replay_output")
    
    print(f"    Replayed {len(logger.session.events)} events")
    print(f"    Files created: {list(state.files.keys())}")
    print(f"    LLM outputs captured: {len(state.llm_outputs)}")
    print(f"    Tool outputs captured: {len(state.tool_outputs)}")
    
    # 5. Show replayed file content
    print("\n[5] Replayed file content (calc.py):")
    print("-" * 40)
    print(state.files.get("calc.py", "(no content)"))
    print("-" * 40)
    
    # 6. Prove determinism: replay again
    print("\n[6] Proving determinism (replay again)...")
    state2 = replay(logger.session)
    
    if state.files == state2.files:
        print("    ✓ PASS: Identical file state on second replay")
    else:
        print("    ✗ FAIL: States differ!")
    
    if state.llm_outputs == state2.llm_outputs:
        print("    ✓ PASS: Identical LLM outputs on second replay")
    else:
        print("    ✗ FAIL: LLM outputs differ!")
    
    print("\n" + "=" * 60)
    print("Demo complete. Key insight:")
    print("  Replay uses RECORDED outputs, not re-sampling.")
    print("  Therefore: deterministic regardless of model randomness.")
    print("=" * 60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
