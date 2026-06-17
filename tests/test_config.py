"""Tests for the config helper module.

TDD: these tests were written RED (before src/config.py existed),
then made GREEN by implementing the helper.

No real network or database access is used — all env vars are
injected/cleared via pytest monkeypatch.
"""

import pytest

# src/ is added to sys.path by the root conftest.py.
from config import req


class TestReq:
    """Tests for the req() configuration helper."""

    def test_returns_value_when_variable_is_present(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_API_KEY", "test-api-key-123")
        result = req("GOOGLE_API_KEY")
        assert result == "test-api-key-123"

    def test_raises_system_exit_when_variable_is_absent(self, monkeypatch):
        monkeypatch.delenv("SOME_MISSING_VAR", raising=False)
        with pytest.raises(SystemExit):
            req("SOME_MISSING_VAR")

    def test_system_exit_message_names_missing_variable(self, monkeypatch):
        var_name = "DATABASE_URL"
        monkeypatch.delenv(var_name, raising=False)
        with pytest.raises(SystemExit) as exc_info:
            req(var_name)
        assert var_name in str(exc_info.value)

    def test_returns_value_for_database_url(self, monkeypatch):
        monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost/db")
        result = req("DATABASE_URL")
        assert result == "postgresql://user:pass@localhost/db"

    def test_returns_value_for_pg_vector_collection_name(self, monkeypatch):
        monkeypatch.setenv("PG_VECTOR_COLLECTION_NAME", "my_collection")
        result = req("PG_VECTOR_COLLECTION_NAME")
        assert result == "my_collection"

    def test_returns_value_for_google_embedding_model(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_EMBEDDING_MODEL", "models/embedding-001")
        result = req("GOOGLE_EMBEDDING_MODEL")
        assert result == "models/embedding-001"

    def test_returns_value_for_pdf_path(self, monkeypatch):
        monkeypatch.setenv("PDF_PATH", "/data/document.pdf")
        result = req("PDF_PATH")
        assert result == "/data/document.pdf"

    def test_raises_system_exit_for_google_api_key_missing(self, monkeypatch):
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        with pytest.raises(SystemExit) as exc_info:
            req("GOOGLE_API_KEY")
        assert "GOOGLE_API_KEY" in str(exc_info.value)

    def test_raises_system_exit_for_pdf_path_missing(self, monkeypatch):
        monkeypatch.delenv("PDF_PATH", raising=False)
        with pytest.raises(SystemExit) as exc_info:
            req("PDF_PATH")
        assert "PDF_PATH" in str(exc_info.value)
