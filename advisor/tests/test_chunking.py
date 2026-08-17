"""RAG chunking testlari."""

from app.rag.chunking import chunk_legal_text, chunk_recursive


def test_recursive_empty():
    assert chunk_recursive("") == []


def test_recursive_short_single_chunk():
    chunks = chunk_recursive("Qisqa matn.")
    assert len(chunks) == 1


def test_recursive_long_splits():
    chunks = chunk_recursive("Bu jumla. " * 2000, max_tokens=200)
    assert len(chunks) > 1
    assert [c.index for c in chunks] == list(range(len(chunks)))


def test_legal_splits_by_articles():
    text = (
        "1-modda. Umumiy qoidalar\nUshbu qonun faoliyatni tartibga soladi.\n"
        "2-modda. Asosiy tushunchalar\nTadbirkorlik — daromad olishga qaratilgan faoliyat.\n"
        "3-modda. Qonunchilik\nQonun hujjatlari sohani tartibga soladi.\n"
    )
    chunks = chunk_legal_text(text, law_title="Tadbirkorlik to'g'risida", url="https://lex.uz/x")
    articles = [c.metadata.get("article") for c in chunks]
    assert "1-modda" in articles
    assert "2-modda" in articles
    assert all(c.metadata["title"] == "Tadbirkorlik to'g'risida" for c in chunks)


def test_legal_no_articles_fallback():
    chunks = chunk_legal_text("Oddiy matn, moddalar yo'q. " * 20, law_title="Hujjat")
    assert len(chunks) >= 1
