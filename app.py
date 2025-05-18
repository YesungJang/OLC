# --------------------------------------------------------------------------- #
# 0.  標準 sqlite3 → pysqlite3 へ差し替え                                     #
# --------------------------------------------------------------------------- #
import importlib, sys, os, re, threading
import pysqlite3                         # pysqlite3-binary 0.5.2
sys.modules["sqlite3"] = importlib.import_module("pysqlite3")

# --------------------------------------------------------------------------- #
# 1.  FastAPI インスタンス & CORS                                             #
# --------------------------------------------------------------------------- #
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Local RAG Server", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://127.0.0.1:8080"],
    allow_methods=["POST"],
    allow_headers=["*"],
)

# --------------------------------------------------------------------------- #
# 2.  外部ライブラリ                                                          #
# --------------------------------------------------------------------------- #
from pathlib import Path
from watchfiles import watch

from pydantic import BaseModel
from chromadb import Client
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.llms import Ollama
import sqlparse, textwrap

# --------------------------------------------------------------------------- #
# 3.  RAG コンポーネント                                                      #
# --------------------------------------------------------------------------- #
chroma = Client().get_or_create_collection("ddl")
emb    = OllamaEmbeddings(model="nomic-embed-text")
llm    = Ollama(model="llama3:8b", temperature=0)

# -- プロンプトファイル設定 -------------------------------------------------- #
PROMPT_DIR   = Path(__file__).parent / "prompts"
DEFAULT_PATH = PROMPT_DIR / "system_mysql.txt"
SYSTEM_PATH  = Path(os.getenv("RAG_SYSTEM_PROMPT", DEFAULT_PATH))

def load_system_prompt() -> str:
    if not SYSTEM_PATH.exists():
        raise FileNotFoundError(f"Prompt file not found: {SYSTEM_PATH}")
    return SYSTEM_PATH.read_text(encoding="utf-8").strip()

SYSTEM_TEXT = load_system_prompt()  # 初回ロード

# -- watchfiles でホットリロード ------------------------------------------- #
def _watch_prompt():
    for _ in watch(str(SYSTEM_PATH)):
        global SYSTEM_TEXT
        SYSTEM_TEXT = load_system_prompt()
        print(f"[Prompt] reloaded → {SYSTEM_PATH}")

threading.Thread(target=_watch_prompt, daemon=True).start()

# -- LangChain 用テンプレート（system だけ動的） ---------------------------- #
from langchain_core.prompts import PromptTemplate

TEMPLATE = PromptTemplate(
    template=textwrap.dedent("""\
        {system}

        ### User Request
        {question}

        ### Relevant DDL
        {context}
    """),
    input_variables=["system", "question", "context"],
)

# --------------------------------------------------------------------------- #
# 4.  I/O スキーマ                                                            #
# --------------------------------------------------------------------------- #
class Query(BaseModel):
    question: str

# --------------------------------------------------------------------------- #
# 5.  DDL コンテキスト取得                                                    #
# --------------------------------------------------------------------------- #
def retrieve_ctx(question: str, k: int = 4) -> str:
    q_emb = emb.embed_query(question)
    res   = chroma.query(query_embeddings=[q_emb], n_results=k, include=["documents"])
    return "\n".join(res["documents"][0]) if res["documents"] else ""

# -- フェンス除去ユーティリティ --------------------------------------------- #
_fence_start = re.compile(r"^```[\w]*\n?", re.S)
_fence_end   = re.compile(r"```$", re.S)

def strip_md_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = _fence_start.sub("", text)
        text = _fence_end.sub("", text).strip()
    return text

# --------------------------------------------------------------------------- #
# 6.  エンドポイント                                                          #
# --------------------------------------------------------------------------- #
@app.post("/query")
def query(q: Query):
    ctx   = retrieve_ctx(q.question)
    prompt= TEMPLATE.format(system=SYSTEM_TEXT, question=q.question, context=ctx)
    raw   = llm.invoke(prompt)

    sql_plain = strip_md_fence(raw)
    sql_fmt   = sqlparse.format(sql_plain, strip_comments=True).strip()

    first_token = re.sub(r"^[\s:>\-]+", "", sql_fmt.lstrip()).split()[0].lower()
    
    # if first_token not in {"select", "insert", "update", "delete", "with", "create", "alter"}:
    #     raise HTTPException(status_code=422, detail="LLM did not return valid SQL")

    return {"sql": sql_fmt, "ddl_context": ctx}
