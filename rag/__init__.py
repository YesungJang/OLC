"""Utilities and FastAPI app for the Local RAG server."""

import importlib
import sys

# Use pysqlite3 as sqlite3 backend
import pysqlite3
sys.modules["sqlite3"] = importlib.import_module("pysqlite3")

from .server import create_app

__all__ = ["create_app"]
