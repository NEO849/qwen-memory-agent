"""Hidden ground-truth test for the `bool_env` pattern.

The agent is only told: "return whether the feature flag `key` is enabled, given a config dict of
string values". The obvious `bool(config.get(key))` treats "false"/"0" as True — the convention
("a string boolean is not a Python bool") lives in MEMORY. Assertions check the falsy string cases
that break the naive version, plus the truthy and missing cases both versions get right.
"""
import importlib.util
import pathlib


def _load_solution():
    p = pathlib.Path(__file__).parent / "solution.py"
    spec = importlib.util.spec_from_file_location("solution", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_string_boolean_is_not_python_bool():
    sol = _load_solution()
    # falsy strings that bool() wrongly treats as enabled
    assert sol.feature_enabled({"DEBUG": "false"}, "DEBUG") is False
    assert sol.feature_enabled({"DEBUG": "0"}, "DEBUG") is False
    # genuinely enabled + missing key
    assert sol.feature_enabled({"DEBUG": "true"}, "DEBUG") is True
    assert sol.feature_enabled({"DEBUG": "1"}, "DEBUG") is True
    assert sol.feature_enabled({}, "DEBUG") is False
