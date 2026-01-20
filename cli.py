#!/usr/bin/env python3
"""
vtrace - CLI

Commands:
    vtrace new       Start a new session
    vtrace log       Log an event manually
    vtrace replay    Replay a session
    vtrace show      Show session contents
    vtrace diff      Compare two sessions
"""

import argparse
import sys
import yaml
from pathlib import Path

from .schema import Session, hash_directory
from .logger import Logger
from .replayer import Replayer, compare_traces


def cmd_new(args):
    """Start a new recording session."""
    logger = Logger.new_session(
        model=args.model,
        codebase_path=args.codebase,
        trace_file=args.output,
        initial_context=args.context or "",
    )
    print(f"Session created: {logger.session.session_id}")
    print(f"Trace file: {logger.trace_file}")
    return 0


def cmd_log(args):
    """Log an event to existing session."""
    logger = Logger.load(args.trace)
    
    if args.type == "llm":
        prompt = args.input or input("Prompt: ")
        response = args.data or input("Response: ")
        logger.log_llm_call(prompt=prompt, response=response)
        
    elif args.type == "tool":
        tool = args.tool or input("Tool name: ")
        tool_args = args.input or input("Args: ")
        output = args.data or input("Output: ")
        logger.log_tool_call(tool_name=tool, args=tool_args, output=output)
        
    elif args.type == "edit":
        file_path = args.input or input("File path: ")
        diff = args.data or input("Diff: ")
        logger.log_edit(file_path=file_path, diff=diff)
    
    print(f"Event logged. Total events: {logger.event_count}")
    return 0


def cmd_replay(args):
    """Replay a session."""
    logger = Logger.load(args.trace)
    
    with Replayer(logger.session, workspace=args.workspace) as replayer:
        if args.step:
            # Interactive step mode
            while True:
                event = replayer.step()
                if event is None:
                    print("End of trace.")
                    break
                print(f"[{replayer.state.event_index}] {event.type}")
                print(f"  Input: {str(event.input)[:60]}...")
                print(f"  Output: {str(event.output)[:60]}...")
                if input("Continue? [Y/n] ").lower() == 'n':
                    break
        else:
            state = replayer.replay_all()
            print(f"Replayed {len(logger.session.events)} events")
            print(f"Files in workspace: {list(state.files.keys())}")
            print(f"Workspace: {replayer.workspace}")
            
            if args.workspace:
                print(f"\nFiles written to: {args.workspace}")
    
    return 0


def cmd_show(args):
    """Show session contents."""
    logger = Logger.load(args.trace)
    s = logger.session
    
    print(f"Session ID: {s.session_id}")
    print(f"Model: {s.model}")
    print(f"Codebase hash: {s.codebase_hash}")
    print(f"Created: {s.created_at}")
    print(f"Events: {len(s.events)}")
    print()
    
    if args.events or args.verbose:
        for i, e in enumerate(s.events):
            print(f"[{i}] {e.type} @ {e.timestamp}")
            if args.verbose:
                print(f"    Input: {e.input}")
                print(f"    Output: {str(e.output)[:200]}...")
                print()
    
    return 0


def cmd_diff(args):
    """Compare two sessions."""
    s1 = Logger.load(args.trace1).session
    s2 = Logger.load(args.trace2).session
    
    result = compare_traces(s1, s2)
    
    print(f"Event counts: {result['event_count'][0]} vs {result['event_count'][1]}")
    print(f"Model match: {result['model_match']}")
    
    if result['event_diffs']:
        print(f"\nDifferences found: {len(result['event_diffs'])}")
        for d in result['event_diffs'][:10]:  # Show first 10
            print(f"  [{d['index']}] {d['type']}")
    else:
        print("\nTraces are identical.")
    
    return 0


def main():
    parser = argparse.ArgumentParser(
        prog='vtrace',
        description='Reproducible traces for AI-assisted coding'
    )
    subparsers = parser.add_subparsers(dest='command', required=True)
    
    # new
    p_new = subparsers.add_parser('new', help='Start new session')
    p_new.add_argument('-m', '--model', default='unknown', help='Model identifier')
    p_new.add_argument('-c', '--codebase', help='Path to codebase')
    p_new.add_argument('-o', '--output', help='Output trace file')
    p_new.add_argument('--context', help='Initial context')
    
    # log
    p_log = subparsers.add_parser('log', help='Log an event')
    p_log.add_argument('trace', help='Trace file')
    p_log.add_argument('-t', '--type', choices=['llm', 'tool', 'edit'], required=True)
    p_log.add_argument('-i', '--input', help='Input/prompt')
    p_log.add_argument('-d', '--data', help='Output/response/diff')
    p_log.add_argument('--tool', help='Tool name (for tool calls)')
    
    # replay
    p_replay = subparsers.add_parser('replay', help='Replay a session')
    p_replay.add_argument('trace', help='Trace file')
    p_replay.add_argument('-w', '--workspace', help='Output workspace directory')
    p_replay.add_argument('-s', '--step', action='store_true', help='Step through interactively')
    
    # show
    p_show = subparsers.add_parser('show', help='Show session info')
    p_show.add_argument('trace', help='Trace file')
    p_show.add_argument('-e', '--events', action='store_true', help='List events')
    p_show.add_argument('-v', '--verbose', action='store_true', help='Show full event details')
    
    # diff
    p_diff = subparsers.add_parser('diff', help='Compare two sessions')
    p_diff.add_argument('trace1', help='First trace file')
    p_diff.add_argument('trace2', help='Second trace file')
    
    args = parser.parse_args()
    
    commands = {
        'new': cmd_new,
        'log': cmd_log,
        'replay': cmd_replay,
        'show': cmd_show,
        'diff': cmd_diff,
    }
    
    return commands[args.command](args)


if __name__ == '__main__':
    sys.exit(main())
