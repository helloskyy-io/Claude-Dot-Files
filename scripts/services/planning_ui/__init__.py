"""The planning-corpus viewer, hosted in the tooling and run against any
planning repository.

Reads a repository's planning corpus and derives its views into
``development/derived/`` there. ``scripts/services/planning-ui.sh`` (beside
this package) writes them; ``--check`` fails when they drift; ``serve``
draws them. Which repository is ``--repo-root``, or the directory the
launcher is run from, and ``plan_extractor.contract`` says whether it is a
planning repository at all.

Admitted by the planning repository's ``repo_layout.md`` §1.1, which states
the five conditions this package holds to. **They are not restated here** — a
second copy of a binding rule drifts from it, and this docstring proved that
by getting one of the five wrong within a day of being written.
"""
