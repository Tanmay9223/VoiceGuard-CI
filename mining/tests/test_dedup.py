import pytest
from unittest.mock import patch, MagicMock

from mining.dedup import VectorDB

def test_vectordb_init_malformed_json(tmp_path, caplog):
    # Create a temporary file with malformed JSON
    db_file = tmp_path / "vector_db.json"
    db_file.write_text("invalid json")

    # Patch DB_PATH to point to the temporary file
    with patch("mining.dedup.DB_PATH", db_file):
        # Initialize VectorDB
        llm_mock = MagicMock()
        db = VectorDB(llm=llm_mock)

        # Assert that an error was logged
        assert "Failed to load vector DB:" in caplog.text

        # Assert that the cache is empty
        assert db._cache == {}
