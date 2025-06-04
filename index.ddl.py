"""Legacy script for indexing DDL statements.

Executing this file maintains compatibility with the original command
``python index.ddl.py``. The implementation resides in :mod:`rag.ddl_indexer`.
"""

from rag.ddl_indexer import index_ddl

if __name__ == "__main__":
    index_ddl()
