"""Utility to index DDL statements into a Chroma collection."""

from pathlib import Path
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import OllamaEmbeddings
from chromadb import Client


def index_ddl(ddl_file: str = "schema/ddl.sql", collection: str = "ddl") -> None:
    """Index ``ddl_file`` into ``collection``."""
    ddl_text = Path(ddl_file).read_text()
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800, chunk_overlap=0, separators=["CREATE TABLE", ";"]
    )
    docs = splitter.create_documents([ddl_text])

    embeddings = OllamaEmbeddings(model="nomic-embed-text")
    chroma = Client().create_collection(collection)

    for i, d in enumerate(docs):
        chroma.add(
            ids=[f"ddl_{i}"],
            documents=[d.page_content],
            embeddings=[embeddings.embed_query(d.page_content)],
            metadatas=[{"source": ddl_file}],
        )
    print(f"Indexed {len(docs)} chunks")


if __name__ == "__main__":
    index_ddl()
