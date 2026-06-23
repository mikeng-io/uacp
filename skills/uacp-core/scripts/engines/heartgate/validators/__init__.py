"""Heartgate validators — the gate's Checks, one module per cohesive check-group.

Each module holds the pure logic for a group of transition/closure checks that
``engines/heartgate/heartgate.py`` (the hub) orchestrates. Carved out of the
``Heartgate`` god-class across the A3.1+ increments (design/graph-engine nodes
30/31/32). Validators import ``..models``, ``.helpers``, ``engines.io``, and
domain leaves — never an outer ring (node 32 §1).
"""

from __future__ import annotations
