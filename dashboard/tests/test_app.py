import json
import pytest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path
import os
import tempfile

# We need to mock streamlit at the top level because dashboard.app does things on import.
# However, to avoid leaking this mock to other test files, we should save the original modules
# and restore them during module teardown.

original_streamlit = sys.modules.get('streamlit')
original_pandas = sys.modules.get('pandas')

mock_st = MagicMock()
mock_st.columns.return_value = (MagicMock(), MagicMock(), MagicMock(), MagicMock())
mock_st.selectbox.return_value = 0
def dummy_cache(ttl=None):
    def decorator(func):
        func.__wrapped__ = func
        return func
    return decorator
mock_st.cache_data = dummy_cache

sys.modules['streamlit'] = mock_st
sys.modules['pandas'] = MagicMock()

def teardown_module(module):
    """Restore original modules after tests in this file run."""
    if original_streamlit is None:
        sys.modules.pop('streamlit', None)
    else:
        sys.modules['streamlit'] = original_streamlit

    if original_pandas is None:
        sys.modules.pop('pandas', None)
    else:
        sys.modules['pandas'] = original_pandas

# Create an actual dummy file so os.stat works when the app module executes top level code!
with tempfile.TemporaryDirectory() as d:
    dummy_dir = Path(d)
    dummy_file = dummy_dir / "run-dummy.json"
    dummy_file.write_text(json.dumps({"run_id": "test", "total": 0, "passed": 0, "failed": 0, "results": []}))

    with patch("pathlib.Path.exists", return_value=True):
        with patch("pathlib.Path.glob", return_value=[dummy_file]):
            from dashboard.app import load_runs

def test_load_runs_dir_not_exists(tmp_path):
    with patch("dashboard.app.RESULTS_DIR", tmp_path / "nonexistent"):
        func = load_runs.__wrapped__ if hasattr(load_runs, '__wrapped__') else load_runs
        result = func(n=10)
        assert result == []

def test_load_runs_empty_dir(tmp_path):
    with patch("dashboard.app.RESULTS_DIR", tmp_path):
        func = load_runs.__wrapped__ if hasattr(load_runs, '__wrapped__') else load_runs
        result = func(n=10)
        assert result == []

def test_load_runs_valid_files(tmp_path):
    with patch("dashboard.app.RESULTS_DIR", tmp_path):
        run1_data = {"run_id": "1", "data": "first"}
        run2_data = {"run_id": "2", "data": "second"}
        run3_data = {"run_id": "3", "data": "third"}

        file1 = tmp_path / "run-1.json"
        file1.write_text(json.dumps(run1_data))

        file2 = tmp_path / "run-2.json"
        file2.write_text(json.dumps(run2_data))

        file3 = tmp_path / "run-3.json"
        file3.write_text(json.dumps(run3_data))

        import time
        now = time.time()
        os.utime(file1, (now - 100, now - 100))
        os.utime(file2, (now - 50, now - 50))
        os.utime(file3, (now, now))

        func = load_runs.__wrapped__ if hasattr(load_runs, '__wrapped__') else load_runs
        result = func(n=2)
        assert len(result) == 2
        assert result[0]["run_id"] == "3"
        assert result[1]["run_id"] == "2"

def test_load_runs_ignores_invalid_files(tmp_path):
    with patch("dashboard.app.RESULTS_DIR", tmp_path):
        valid_data = {"run_id": "1", "valid": True}
        valid_file = tmp_path / "run-1.json"
        valid_file.write_text(json.dumps(valid_data))

        invalid_file = tmp_path / "run-2.json"
        invalid_file.write_text("{invalid json")

        other_file = tmp_path / "other.json"
        other_file.write_text(json.dumps({"should_be": "ignored"}))

        import time
        now = time.time()
        os.utime(valid_file, (now, now))
        os.utime(invalid_file, (now + 10, now + 10))

        func = load_runs.__wrapped__ if hasattr(load_runs, '__wrapped__') else load_runs
        result = func(n=10)

        assert len(result) == 1
        assert result[0]["run_id"] == "1"
