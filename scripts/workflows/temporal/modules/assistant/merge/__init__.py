"""Landing a reviewed PR set, and draining the intake.

A SUBPACKAGE RATHER THAN A PARENT-LEVEL MODULE, and the placement is the gate's
ruling rather than a preference. `workflow-scripts.md` §10.1 rule 3 is that
*"anything at a parent level is shared by definition, so a reader never has to
open a file to learn its scope"* — and today this activity has exactly one
caller, `scripts/helpers/merge-pr.py`, which is an operator entry point outside
the workflow tree. `tracked/intake.py` sits here for the same reason and behind
the same kind of helper.

**When a parent calls it, parent level becomes the correct home** and this
package is what has to be dissolved to put it there — deliberately, and by the
run that adds the second consumer.
"""
