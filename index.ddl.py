from pathlib import Path
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import OllamaEmbeddings
from chromadb import Client

# DDL
ddl_file = "schema/ddl.sql"        
ddl_text = Path(ddl_file).read_text()

# テーブル単位で分割
splitter = RecursiveCharacterTextSplitter(
    chunk_size=800, chunk_overlap=0, separators=["CREATE TABLE", ";"]
)
docs = splitter.create_documents([ddl_text])

embeddings = OllamaEmbeddings(model="nomic-embed-text")  # 8-bit埋め込みモデル
chroma = Client().create_collection("ddl")

for i, d in enumerate(docs):
    chroma.add(
        ids=[f"ddl_{i}"],
        documents=[d.page_content],
        embeddings=[embeddings.embed_query(d.page_content)],
        metadatas=[{"source": ddl_file}]
    )
print(f"Indexed {len(docs)} chunks")
