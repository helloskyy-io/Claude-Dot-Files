"""The viewer — Pages 2 and 3, served by ``planning-ui.sh serve``.

Everything here is served as-is: ``index.html`` is the one page,
``viewer/`` is the view written with ``React.createElement`` (no JSX, no
bundler, no build step), and ``vendor/`` is the third-party module set
fetched once from esm.sh and committed with its manifest. ``vendor_fetch.py``
is how the set is regenerated, by hand.

The Python that FEEDS the viewer is not here: ``planning_ui/views/`` derives its
inputs from the same extraction the committed artifacts come from, and
``planning_ui/serve.py`` is the process that serves both. This package holds no
Python that runs at view time.
"""
