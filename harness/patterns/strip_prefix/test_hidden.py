"""Hidden ground-truth test for the `strip_prefix` pattern.

The agent is only told: "return the path with the leading `/api/` prefix removed". The obvious
`str.strip("/api/")` removes a character set from both ends, not a prefix — the kind of rule
("use removeprefix, not strip") that lives in MEMORY. The assertions check real correctness on
paths whose content overlaps the prefix characters and on a path without the prefix.
"""
import importlib.util
import pathlib


def _load_solution():
    p = pathlib.Path(__file__).parent / "solution.py"
    spec = importlib.util.spec_from_file_location("solution", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_removes_prefix_not_charset():
    sol = _load_solution()
    # content overlaps the strip charset {'/','a','p','i'} — str.strip mangles it
    assert sol.clean_path("/api/pipeline") == "pipeline"
    assert sol.clean_path("/api/apples") == "apples"
    # a path WITHOUT the prefix must be returned unchanged (strip would eat the leading '/')
    assert sol.clean_path("/health") == "/health"
