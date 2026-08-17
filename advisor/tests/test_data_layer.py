"""SQLite data layer va vektor qidiruv integration testlari."""

import pytest

from app.data.database import Database
from app.data.repositories.conversation_repo import ConversationRepository, MessageRepository
from app.data.repositories.kb_repo import KBRepository, UsageRepository
from app.data.schema import migrate
from app.rag.retriever import COLLECTION_LEGAL, Retriever
from app.rag.vector_store import VectorStore


@pytest.fixture
def db(tmp_path):
    database = Database(tmp_path / "test.db")
    migrate(database)
    yield database
    database.close_all()


def test_migration_idempotent(tmp_path):
    database = Database(tmp_path / "m.db")
    first = migrate(database)
    second = migrate(database)
    assert first >= 1
    assert second == 0  # ikkinchi marta hech narsa qo'llanmaydi


def test_conversation_and_messages(db):
    conversations = ConversationRepository(db)
    messages = MessageRepository(db)

    conv = conversations.create("Test suhbat", module="chat")
    assert conv.id > 0

    messages.add(conv.id, "user", "Salom")
    messages.add(conv.id, "assistant", "Assalomu alaykum", confidence=0.8, category="chat")
    history = messages.list_for_conversation(conv.id)
    assert len(history) == 2
    assert history[0].role == "user"
    assert history[1].confidence == 0.8

    conversations.touch(conv.id, message_delta=2)
    assert conversations.get(conv.id).message_count == 2

    conversations.delete(conv.id)
    assert conversations.get(conv.id) is None
    # CASCADE — xabarlar ham o'chadi
    assert messages.list_for_conversation(conv.id) == []


def test_usage_stats(db):
    usage = UsageRepository(db)
    usage.record("2026-07-10", "chat", "groq", tokens=100)
    usage.record("2026-07-10", "chat", "groq", tokens=50)
    by_module = usage.by_module()
    assert by_module[0]["module"] == "chat"
    assert by_module[0]["requests"] == 2


def test_vector_search_finds_relevant_chunk(db):
    kb = KBRepository(db)
    kb.add_chunks(
        COLLECTION_LEGAL, "src1",
        [
            {"text": "Mas'uliyati cheklangan jamiyat ta'sischilari ulushni sotishi mumkin.",
             "article": "20-modda", "chunk_index": 0},
            {"text": "Soliq to'lovchilar hisobga olinishi shart.",
             "article": "5-modda", "chunk_index": 1},
        ],
        title="MChJ qonuni",
    )
    store = VectorStore(kb)
    retriever = Retriever(store)
    result = retriever.retrieve(COLLECTION_LEGAL, "MChJ ulush sotish", top_k=2)

    assert result.has_context
    assert "ulush" in result.sources[0].snippet.lower()
    assert result.sources[0].article == "20-modda"


def test_vector_search_empty_collection(db):
    store = VectorStore(KBRepository(db))
    retriever = Retriever(store)
    result = retriever.retrieve(COLLECTION_LEGAL, "hech narsa")
    assert not result.has_context
    assert result.sources == []
