"""Oracle engine for UACP — retrieval aggregator with per-phase gating.

Public corpus-write API: out-of-package callers (e.g. the governed
``uacp_corpus_write`` tool handler) reach the corpus ONLY through this
package-level ``write_corpus`` — never by importing the private
``corpus_writer`` module or touching corpus paths / (de)serialization
directly (the data-ownership boundary, tests/unit/uacp_oracle/test_corpus_boundary.py).
"""

from engines.oracle.corpus_writer import write_corpus

__all__ = ["write_corpus"]
