"""Unit tests: AI base abstractions."""

import pytest

from app.ai.base import parse_model_id


class TestParseModelId:
    def test_valid(self):
        assert parse_model_id("openai:gpt-4o") == ("openai", "gpt-4o")

    def test_model_with_colon(self):
        assert parse_model_id("local:llama3:8b") == ("local", "llama3:8b")

    @pytest.mark.parametrize("bad", ["gpt-4o", "openai:", ":model", ""])
    def test_invalid(self, bad: str):
        with pytest.raises(ValueError):
            parse_model_id(bad)
