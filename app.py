"""Legacy entrypoint for the Local RAG server.

This module exposes the FastAPI ``app`` object so existing commands like
``uvicorn app:app`` continue to work. The server implementation lives in
:mod:`rag.server`.
"""

from rag import create_app

app = create_app()
