"""Unit tests: RAG chunking."""

from app.rag.chunking import chunk_legal_text, chunk_recursive


class TestRecursiveChunking:
    def test_empty_text(self):
        assert chunk_recursive("") == []

    def test_short_text_single_chunk(self):
        chunks = chunk_recursive("Qisqa matn.")
        assert len(chunks) == 1
        assert chunks[0].text == "Qisqa matn."

    def test_long_text_splits(self):
        text = "Bu jumla. " * 2000
        chunks = chunk_recursive(text, max_tokens=200)
        assert len(chunks) > 1
        # Every chunk within limit (with tolerance for overlap tail)
        assert all(len(c.text) <= 200 * 3.5 * 1.5 for c in chunks)

    def test_metadata_propagates(self):
        chunks = chunk_recursive("matn " * 100, base_metadata={"title": "Test"})
        assert all(c.metadata["title"] == "Test" for c in chunks)

    def test_indexes_sequential(self):
        chunks = chunk_recursive("So'z " * 5000, max_tokens=150)
        assert [c.index for c in chunks] == list(range(len(chunks)))


class TestLegalChunking:
    def test_splits_by_articles(self):
        text = (
            "1-modda. Umumiy qoidalar\nUshbu qonun tadbirkorlik faoliyatini tartibga soladi.\n"
            "2-modda. Asosiy tushunchalar\nTadbirkorlik — daromad olishga qaratilgan faoliyat.\n"
            "3-modda. Qonunchilik\nQonun hujjatlari ushbu sohani tartibga soladi.\n"
        )
        chunks = chunk_legal_text(text, law_title="Tadbirkorlik to'g'risida", url="https://lex.uz/x")
        articles = [c.metadata.get("article") for c in chunks]
        assert "1-modda" in articles
        assert "2-modda" in articles
        assert "3-modda" in articles
        assert all(c.metadata["law_title"] == "Tadbirkorlik to'g'risida" for c in chunks)

    def test_no_articles_falls_back(self):
        text = "Oddiy hujjat matni, moddalar yo'q. " * 20
        chunks = chunk_legal_text(text, law_title="Hujjat")
        assert len(chunks) >= 1
        assert chunks[0].metadata["law_title"] == "Hujjat"

    def test_russian_articles(self):
        text = (
            "Статья 1. Общие положения\nНастоящий закон регулирует отношения.\n"
            "Статья 2. Основные понятия\nПредпринимательство — деятельность.\n"
        )
        chunks = chunk_legal_text(text, law_title="Закон")
        assert any(c.metadata.get("article") for c in chunks)
