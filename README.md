# vtrace

**Reproducible traces for AI-assisted coding.**

> "Git for vibe coding sessions."

## The Problem

AI-assisted coding sessions are non-reproducible. You can't:
- Replay what happened
- Debug why something broke
- Share exact workflows
- Audit AI decisions

## The Solution

We make sessions reproducible by recording the **exact semantic trace** of:
- LLM calls (prompt + full response)
- Tool calls (command + output)
- Code edits (file + diff)

Then replay deterministically — no re-sampling required.

## Core Insight

**Non-reproducibility = missing trace, not stochasticity.**

If you capture all non-deterministic outputs, replay becomes a pure fold:

```
Replay(S) := fold(Apply, C₀, Σ)
```

Where `Σ` is the ordered event trace.

## Quick Start

```bash
pip install -e .
python demo.py
```

## Usage

### Python API

```python
from vtrace import Logger, replay

# Record a session
logger = Logger.new_session(model="gpt-4")
logger.log_llm_call(prompt="Write add function", response="def add(a,b): return a+b")
logger.log_edit(file_path="math.py", diff="+def add(a,b): return a+b")

# Replay deterministically
state = replay(logger.session)
print(state.files)  # {'math.py': 'def add(a,b): return a+b'}
```

### CLI

```bash
vtrace new -m gpt-4              # Start session
vtrace show session.yaml -v      # View events
vtrace replay session.yaml       # Replay
vtrace diff s1.yaml s2.yaml      # Compare
```

## License

MIT
