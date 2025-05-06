from fastapi import FastAPI
from pydantic import BaseModel
from langchain_community.embeddings import OllamaEmbeddings
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_community.llms import Ollama
from chromadb import Client
import sqlparse, textwrap

app, chroma = FastAPI(), Client().get_or_create_collection("ddl")
emb = OllamaEmbeddings(model="nomic-embed-text")
llm = Ollama(model="llama3:8b", temperature=0)

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

class Query(BaseModel):
    question: str

def retrieve_ctx(q: str, k=4):
    qv = emb.embed_query(q)
    ids, docs, _ = chroma.query(
        query_embeddings=[qv], n_results=k, include=["documents"]
    )
    return "\n".join(docs[0])

@app.post("/query")
def query(q: Query):
    ctx = retrieve_ctx(q.question)
    chain = PROMPT | llm
    raw = chain.invoke({"system": SYSTEM, "question": q.question, "context": ctx})
    sql_code = sqlparse.format(raw, strip_comments=True).strip()
    return {"sql": sql_code, "ddl_context": ctx}
