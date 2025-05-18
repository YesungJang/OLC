# app.py
# ---------------------------------------------------------------------------
# 0. 標準 sqlite3 を pysqlite3 にすげ替え（先頭で実施）
# ---------------------------------------------------------------------------
import importlib, sys
import pysqlite3                     # pysqlite3-binary 0.5.2
sys.modules["sqlite3"] = importlib.import_module("pysqlite3")

# ---------------------------------------------------------------------------
# 1. FastAPI 本体をまず生成
# ---------------------------------------------------------------------------
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Local RAG Server",
    version="0.1.0",
)

# CORS: 8080 のフロントからの POST を許可
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ],
    allow_methods=["POST"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# 2. 外部ライブラリ
# ---------------------------------------------------------------------------
from pydantic import BaseModel
from langchain_community.embeddings import OllamaEmbeddings
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_community.llms import Ollama
from chromadb import Client
import sqlparse, textwrap

# ---------------------------------------------------------------------------
# 3. RAG 部品の初期化
# ---------------------------------------------------------------------------
chroma = Client().get_or_create_collection("ddl")
emb    = OllamaEmbeddings(model="nomic-embed-text")
llm    = Ollama(model="llama3:8b", temperature=0)

SYSTEM = """
You are an expert MySQL engineer.  
Generate syntactically correct **MySQL 8.0** SQL only.  
Use the provided schema snippets if relevant.  
Return only the SQL inside one ```sql``` block.
"""

PROMPT = PromptTemplate(
    template=textwrap.dedent("""\
    {system}

    ### User Request
    {question}

    ### Relevant DDL
    {context}
    """),
    input_variables=["system", "question", "context"],
)

# ---------------------------------------------------------------------------
# 4. I/O スキーマ
# ---------------------------------------------------------------------------
class Query(BaseModel):
    question: str

# ---------------------------------------------------------------------------
# 5. Chroma から DDL コンテキストを取得
# ---------------------------------------------------------------------------
def retrieve_ctx(q: str, k: int = 4) -> str:
    qv = emb.embed_query(q)
    res = chroma.query(
        query_embeddings=[qv],
        n_results=k,
        include=["documents"],
    )
    # res = {'ids': [[...]], 'documents': [[...]], 'distances': [[...]]}
    docs = res["documents"][0]
    return "\n".join(docs)

# ---------------------------------------------------------------------------
# 6. エンドポイント
# ---------------------------------------------------------------------------
@app.post("/query")
def query(q: Query):
    ctx   = retrieve_ctx(q.question)
    chain = PROMPT | llm
    raw   = chain.invoke(
        {"system": SYSTEM, "question": q.question, "context": ctx}
    )
    sql_code = sqlparse.format(raw, strip_comments=True).strip()
    return {"sql": sql_code, "ddl_context": ctx}
