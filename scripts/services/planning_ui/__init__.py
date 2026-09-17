"""The corpus viewer for this planning repository.

Reads the planning corpus and derives the views in ``generated/``.
``python -m planning_ui`` writes them; ``--check`` fails when they drift.

Admitted by ``standards/architecture/repo_layout.md`` §1.1, which states the
five conditions this package holds to. **They are not restated here** — a
second copy of a binding rule drifts from it, and this docstring proved that
by getting one of the five wrong within a day of being written.
"""
