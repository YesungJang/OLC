"""Retrieve DDL context chunks from ChromaDB."""

from chromadb import Client
from langchain_community.embeddings import OllamaEmbeddings


class ContextRetriever:
    """Chroma-based DDL context retriever."""

    def __init__(self, collection: str = "ddl", model: str = "nomic-embed-text"):
        self.embeddings = OllamaEmbeddings(model=model)
        self.collection = Client().get_or_create_collection(collection)

    def retrieve(self, question: str, k: int = 4) -> str:
        """Return concatenated DDL chunks relevant to ``question``."""
        q_emb = self.embeddings.embed_query(question)
        res = self.collection.query(query_embeddings=[q_emb], n_results=k, include=["documents"])
        return "\n".join(res["documents"][0]) if res["documents"] else ""
