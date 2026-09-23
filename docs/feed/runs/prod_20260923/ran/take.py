"""Scratch (not committed): today's snapshot via the approved read-only script. Credential from memory file into env; never printed."""
import os
import re
import runpy
import sys
from pathlib import Path

mem = Path.home() / ".claude/projects/c--dev-PigOS/memory/reference_pigplan_oracle.md"
os.environ["ORACLE_PW"] = re.search(r"user/pw `pksu`/`([^`]+)`", mem.read_text(encoding="utf-8")).group(1)
out = Path(sys.argv[1])
sys.argv = ["feed_source_snapshot_take.py", "--out", str(out / "s.json"), "--meta-out", str(out / "meta.json"),
            "--window-start", "2025-09-01", "--window-end", "2026-09-23", "--today", "2026-09-23"]
runpy.run_path("scripts/feed_source_snapshot_take.py", run_name="__main__")
