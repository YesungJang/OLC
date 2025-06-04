"""FastAPI application for the Local RAG server."""

import textwrap
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langchain_community.llms import Ollama
from langchain_core.prompts import PromptTemplate
import sqlparse
from pydantic import BaseModel

from .prompt import PromptManager
from .context import ContextRetriever
from .utils import strip_md_fence


def create_app() -> FastAPI:
    """Return a configured FastAPI application."""
    app = FastAPI(title="Local RAG Server", version="0.2.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:8080", "http://127.0.0.1:8080"],
        allow_methods=["POST"],
        allow_headers=["*"],
    )

    retriever = ContextRetriever()
    prompt_mgr = PromptManager()
    prompt_mgr.start_watcher()
    llm = Ollama(model="llama3:8b", temperature=0)

    template = PromptTemplate(
        template=textwrap.dedent(
            """\
            {system}

            ### User Request
            {question}

            ### Relevant DDL
            {context}
            """
        ),
        input_variables=["system", "question", "context"],
    )

    class Query(BaseModel):
        question: str

    @app.post("/query")
    def query(q: Query):
        ctx = retriever.retrieve(q.question)
        prompt = template.format(
            system=prompt_mgr.text, question=q.question, context=ctx
        )
        raw = llm.invoke(prompt)
        sql_plain = strip_md_fence(raw)
        sql_fmt = sqlparse.format(sql_plain, strip_comments=True).strip()
        return {"sql": sql_fmt, "ddl_context": ctx}

    return app
