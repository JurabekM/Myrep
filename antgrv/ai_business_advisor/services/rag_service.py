import chromadb
from chromadb.config import Settings
import os
from typing import List
from core.config import VECTOR_STORE_PATH
from core.logger import app_logger
from domain.schemas import DocumentChunk

class RAGService:
    def __init__(self):
        try:
            # Initialize local ChromaDB
            self.client = chromadb.PersistentClient(path=str(VECTOR_STORE_PATH))
            # We use a default collection for documents
            self.collection = self.client.get_or_create_collection(name="business_docs")
            app_logger.info("ChromaDB initialized successfully.")
        except Exception as e:
            app_logger.error(f"Failed to initialize ChromaDB: {e}")
            self.client = None
            self.collection = None

    def add_documents(self, chunks: List[DocumentChunk], doc_id_prefix: str):
        if not self.collection:
            app_logger.warning("ChromaDB is not initialized. Cannot add documents.")
            return

        documents = []
        metadatas = []
        ids = []

        for i, chunk in enumerate(chunks):
            documents.append(chunk.text)
            metadatas.append(chunk.metadata)
            ids.append(f"{doc_id_prefix}_{i}")

        try:
            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            app_logger.info(f"Added {len(chunks)} chunks to vector store.")
        except Exception as e:
            app_logger.error(f"Error adding to ChromaDB: {e}")

    def query_context(self, query: str, n_results: int = 3) -> str:
        if not self.collection:
            return ""

        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results
            )
            
            if results['documents'] and results['documents'][0]:
                context_chunks = results['documents'][0]
                return "\n\n---\n\n".join(context_chunks)
            return ""
        except Exception as e:
            app_logger.error(f"Error querying ChromaDB: {e}")
            return ""

rag_service = RAGService()
