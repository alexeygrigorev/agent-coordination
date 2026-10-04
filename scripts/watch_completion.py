#!/usr/bin/env python3
"""Deterministic completion watch. No model polling.

Prints ACTION_REQUIRED when an executor session leaves running/working,
or when a named artifact appears. Silent otherwise.
"""
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sessions():
    proc = subprocess.run(
        ["aplexer", "list", "--json"],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    if proc.returncode:
        return []
    data = json.loads(proc.stdout or "[]")
    return data if isinstance(data, list) else data.get("sessions", [])


def main():
    tags = sys.argv[1:] or ["ac-relay-exec", "ac-adapter-exec", "ac-reviewer"]
    artifact = ROOT / ".local" / "executor-status.json"
    prev = {tag: None for tag in tags}
    while True:
        live = {s.get("tag"): s for s in sessions() if s.get("tag") in tags}
        for tag in tags:
            rec = live.get(tag)
            state = None if rec is None else rec.get("reported_state") or rec.get("phase")
            if prev[tag] in {"working", "running", None} and rec is None and prev[tag] is not None:
                print(f"ACTION_REQUIRED: {tag} session gone")
            elif prev[tag] in {"working", "running"} and state not in {"working", "running", None}:
                print(f"ACTION_REQUIRED: {tag} {prev[tag]} -> {state}")
            prev[tag] = "running" if rec and rec.get("phase") == "running" else state
        if artifact.exists():
            print(f"ACTION_REQUIRED: artifact {artifact}")
            artifact = artifact.with_suffix(".seen")
        time.sleep(30)


if __name__ == "__main__":
    main()
