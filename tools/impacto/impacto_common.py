"""Helpers shared by the Impacto tooling scripts (not a script itself).

The tool scripts have hyphens in their names, so they are loaded by file path. Scripts that need this module put
their own directory on sys.path first (needed because `python -I` does not add it).
"""
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parents[1]
DEFAULT_LOCK = ROOT / "engine/impacto/source-lock.json"
# What the CLIs report instead of raising; anything else is a bug and keeps its traceback.
EXPECTED_ERRORS = (OSError, ValueError, KeyError, TypeError, RuntimeError)


def load_verifier():
    """Load tools/impacto/verify-upstream.py (hyphenated, so not importable by name)."""
    spec = importlib.util.spec_from_file_location("verify_upstream", TOOLS / "verify-upstream.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def atomic_write(path, data):
    """Write bytes to `path` through a temporary file in the same directory and os.replace."""
    path = Path(path)
    descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    except BaseException:
        Path(name).unlink(missing_ok=True)
        raise


def run_cli(action, *, failure, report=None):
    """Run `action()` (returns a JSON-able dict) with the shared reporting convention.

    Success: print the result as JSON (and write it to `report`); returns 0.
    Expected failure: write {"version":1,"clean":false,"error":...} to `report`, message to stderr; returns 1.
    """
    try:
        result = action()
    except EXPECTED_ERRORS as error:
        if report:
            report.parent.mkdir(parents=True, exist_ok=True)
            report.write_text(json.dumps({"version": 1, "clean": False, "error": str(error)},
                                         ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
        print(f"{failure}: {error}", file=sys.stderr)
        return 1
    output = json.dumps(result, ensure_ascii=True, indent=2) + "\n"
    if report:
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(output, encoding="utf-8")
    print(output, end="")
    return 0
