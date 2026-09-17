"""No package attribute shadows a submodule of the same name.

The class guard behind one instance: ``planning_ui.views`` re-exported its
``neighbourhood()`` query, so ``import planning_ui.views.neighbourhood as nb``
bound the FUNCTION and every test had to route through ``importlib``. A
package that names a function like one of its modules hands that trap to the
next caller; this test fails on the next one rather than waiting for a reader
to trip over it.
"""
from __future__ import annotations

import importlib
import inspect
import pkgutil

import planning_ui

#: Shadows that predate this guard and are fenced from the change that added
#: it: `planning_ui.decisions` re-exports `derive()` over `decisions/derive.py`.
#: Named, not hidden — remove the entry when that package is corrected, and
#: add nothing here without the same sentence.
KNOWN_SHADOWS = {("planning_ui.decisions", "derive")}


def _packages():
    yield planning_ui
    for info in pkgutil.walk_packages(planning_ui.__path__, prefix="planning_ui."):
        if info.ispkg and ".tests" not in info.name:
            yield importlib.import_module(info.name)


def test_no_package_attribute_shadows_a_submodule():
    shadows = set()
    packages = set()
    for pkg in _packages():
        packages.add(pkg.__name__)
        for info in pkgutil.iter_modules(pkg.__path__):
            attr = getattr(pkg, info.name, None)
            if attr is None or inspect.ismodule(attr):
                continue
            shadows.add((pkg.__name__, info.name))
    # Positive control: the walk reached every package that has an __init__.py.
    # A package that lost its __init__.py becomes a namespace package pkgutil
    # does not traverse, and would drop out of here silently otherwise.
    assert packages == {
        "planning_ui", "planning_ui.decisions", "planning_ui.plan_extractor", "planning_ui.renderers", "planning_ui.views",
    }
    assert shadows == KNOWN_SHADOWS, (
        f"a package attribute shadows a submodule: {sorted(shadows - KNOWN_SHADOWS)} — "
        "`import <package>.<name> as m` would bind the attribute, not the module"
    )
