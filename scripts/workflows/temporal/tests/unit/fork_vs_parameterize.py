"""THE RULING PROCEDURE for a drifted pair, and the `_minor` tier contract.

READ THIS WHEN A DUPLICATION OR DRIFT GUARD FAILS. It is placed here, beside
the guards, rather than in `docs/standards/workflow-scripts.md`, because a
ruling is made at the moment a guard goes red and a standard is not what anyone
opens then. The standard states the RULE (a block with two consumers is
promoted); this states the PROCEDURE for the half a test may not decide.

WHY A PERSON RULES AND A TEST NEVER DOES. Two reasons, and the second closes it.
Intent is defined in the clone literature as the developer's AWARENESS of the
other copy — a property of a person, not of a text — so every artifact-only
method estimates a correlate. And the correlate is weak: the one field study
that measured inter-rater agreement on exactly this classification reports
kappa = 0.271, "fair" by convention, and that is the CEILING on any rule built
from the same signals. A gate that scores a pair and acts on the score asserts a
confidence nobody has measured above fair. A detector may SURFACE a pair; it may
not rule on one.

---------------------------------------------------------------------------
FOUR SHORT-CIRCUITS. Apply these FIRST. They keep the procedure from being run
on pairs that need no ruling at all.
---------------------------------------------------------------------------

  SC1  BYTE-IDENTICAL          the verbatim ratchet already decided it; promote.
  SC2  RATIONALE IS WRITTEN     signal 4 short-circuits the other three.
  SC3  GENUINELY DIFFERENT JOBS a child doing different work may legitimately
                                repeat or vary a sentence.
  SC4  SHORT-LIVED COPIES       a tree under active decomposition may diverge on
                                its own before a reconciliation would pay.

---------------------------------------------------------------------------
FOUR SIGNALS, IN ORDER. Stop at the first that decides.
---------------------------------------------------------------------------

  S1  FIT TO REFERENT      Does each copy still fit ITS OWN child - its stage
                           numbering, the artifacts it names, the job that child
                           does? The copy naming things its host does not have is
                           the mis-maintained one.
  S2  CONTEXT SIMILARITY   How alike are the two children's jobs, names, inputs
      OF THE TWO SITES     and surroundings? Alike => co-evolution is required =>
                           a divergence is NEGLECTED. Unlike => independence is
                           legitimate => DELIBERATE.
  S3  DRIFT PATTERN        Are the differences confined to named entities and
      (NEVER MAGNITUDE)    parameters, or are they whole blocks present in one
                           copy and absent from the other? The first is
                           parameterization; the second is the reportable class.
  S4  STATED RATIONALE     Does either copy say, in its own text, WHY it differs?

SIGNAL 4 IS ASYMMETRIC AND THE ASYMMETRY IS THE POINT. A stated rationale is
evidence FOR deliberation. Silence is NOT evidence for accident — it only
removes the cheapest signal and forces the reviewer down to S1-S3.

ABSENCE YIELDS `UNRULED`, NEVER `DELIBERATE`. The literature, unable to reach an
author, defaults to calling an unexplained difference intentional; that default
is conservative for a research hypothesis and INVERTED for us. A neglected copy
misread as a deliberate variant is the exact defect this repo has already paid
for. Where a signal is genuinely absent, the honest output is UNRULED.

NEVER REASON FROM SIMILARITY MAGNITUDE. Drift PATTERN is a signal the field
uses; drift MAGNITUDE is one no source uses. Two copies differing only in named
entities and two copies missing a whole block can sit at the same score. This
repo learned it the expensive way: the standard once carried three named
similarity figures and two of the three were falsified by the promotions in the
very pull request that wrote them. `ruling_defects()` below fails a ruling whose
reasoning contains one — a figure attached to a similarity claim, or any
percentage. It does NOT ban numbers: a ruling citing this module's own kappa,
or a consumer count, is citing evidence rather than substituting for it.

---------------------------------------------------------------------------
VALIDATED BEFORE IT WAS TRUSTED, AND IT DID NOT PASS.
---------------------------------------------------------------------------

`docs/development/workflow-decomposition/fork_vs_parameterize_blind_trial.md`
records a blind trial of this procedure on seven drifted pairs: two raters with
no shell (so history was unreachable, not merely forbidden), classifications
sealed in a commit before any history was read, then scored against a mechanical
co-evolution audit.

  * Inter-rater kappa was **0.000** — at or below the field's 0.271 benchmark.
  * The two raters DISAGREED on which failure they were looking at, not merely
    on how confident to be.
  * One rater returned DELIBERATE on all seven, which is the field default this
    procedure explicitly forbids, and was wrong on exactly the pair where the
    default is wrong.

SO THE GRANULARITY MOVED. Per-pair ruling is not reproducible here and this
module does not pretend otherwise: rulings are made **per FAMILY of guidance**,
using the contract below, and a per-pair verdict is advisory. That is the
outcome the phase's requirement 3 was written to permit.

---------------------------------------------------------------------------
THE `_minor` TIER CONTRACT. What a minor tier's prompt is FOR.
---------------------------------------------------------------------------

Stated because nothing did, and its absence is why three correction passes on
one pull request answered the same reconciliation question three different ways.
"Less thorough" is not a contract; these categories are.

A category is TIER-INVARIANT when a run of either tier is doing the same thing
and a difference between the tiers would mean the two are running different
rules. It is TIER-SCOPED when the difference IS the tier.

`ruling_defects()` requires every family ruling to name one of these, so a
reconciliation is a lookup rather than an argument.
"""
from __future__ import annotations

import re

#: A ruling's verdict. `UNRULED` is a real outcome, not a failure to answer.
VERDICTS = ("PROMOTE", "DELIBERATE", "UNRULED")

#: The short-circuits, applied before any signal.
SHORT_CIRCUITS = {
    "SC1": "byte-identical — the verbatim ratchet already decided it",
    "SC2": "the rationale is already written down",
    "SC3": "the two children genuinely do different jobs",
    "SC4": "the copies are short-lived",
}

#: The four signals, in the order they are applied.
SIGNALS = {
    "S1": "fit to referent",
    "S2": "context similarity of the two sites",
    "S3": "drift pattern, never magnitude",
    "S4": "stated rationale in the artifact",
}

#: Categories of guidance that are the SAME in a major tier and its `_minor`
#: sibling. A difference here means the two tiers are running different rules,
#: which is the defect, not the design.
TIER_INVARIANT = {
    "operational-safety":
        "what a run may and may not do to the tree, the branch or the remote — "
        "worktree discipline, push discipline, destructive-command rules. A "
        "cheaper run is not a run permitted to be less careful.",
    "evidence-discipline":
        "how a claim is established before it is written down — verify by "
        "fetch, probe before asserting, name what you observed rather than "
        "that you checked. Scope changes what is examined, never what counts "
        "as having examined it.",
    "finding-disposition":
        "what may be done with a finding once it exists — the closed verb list, "
        "apply-the-remedy-you-wrote, rejection-with-reasoning, and the bar on "
        "another run's 'pre-existing'. A finding disposed under a different "
        "rule in each tier is the same finding getting two answers.",
    "orchestration-mechanics":
        "the orchestrator/agent split itself — who executes and who reads, and "
        "that a foreground dispatch is what keeps a headless run alive. True of "
        "one agent and of five.",
    "stage-ordering":
        "that stages run in order and a skipped stage is declared. The number "
        "of stages is tier-scoped; that they are ordered is not.",
}

#: Categories that legitimately differ between the tiers. This is the axis both
#: refine workflows' own comments already name: how many lenses a pass runs.
TIER_SCOPED = {
    "review-depth":
        "how many review lenses run and which agents are dispatched, including "
        "any text that ENUMERATES that roster.",
    "tier-identity":
        "the names a tier calls itself — workflow key, commit-message prefix, "
        "turn cap, the sentence describing the tier's scope.",
    "artifact-shape":
        "what the run is expected to produce and how many artifacts, where the "
        "tier's whole premise is fewer of them.",
}

# A SIMILARITY MAGNITUDE, which is a number STANDING IN FOR the reasoning — not
# every number. The first version banned any bare `0.xxx` and so rejected a
# ruling that cited this module's own strongest evidence: `kappa = 0.271` and the
# measured `0.000` are the reason per-pair ruling was retired, and an author
# whose only exits are to delete the evidence or spell it as a word will delete
# it. So the ban is on a figure ATTACHED TO A SIMILARITY CLAIM, in either order,
# plus any percentage — the form nobody writes except to score two copies.
# `(?<![A-Za-z-])` is load-bearing: the procedure's OWN vocabulary is full of
# digits glued to letters — `S2`, `SC3`, a `C-115` candidate id — and without it
# every ruling that names the signal that decided it reads as a magnitude,
# which is every well-formed ruling there is.
_NUMBER = r"(?<![A-Za-z-])\d"
_SIMILARITY = r"(?:similar\w*|ratio|alike|overlap\w*)"
_MAGNITUDE = re.compile(
    rf"{_NUMBER}[\d.]*\s*%"
    rf"|{_SIMILARITY}[^.\n]{{0,40}}{_NUMBER}"
    rf"|{_NUMBER}[^.\n]{{0,40}}{_SIMILARITY}",
    re.IGNORECASE,
)


def ruling_defects(ruling: str) -> list[str]:
    """Everything wrong with one written ruling. Empty means it is well-formed.

    Split from the assertion so a control can drive it with synthetic rulings —
    the real corpus can only ever exercise the passing branch, and a validator
    whose failing path has never run is one nobody has seen work.
    """
    problems = []
    if not any(ruling.startswith(v + " ") for v in VERDICTS):
        problems.append(
            f"must OPEN with one of {VERDICTS} followed by a space; got {ruling[:40]!r}"
        )
    if not any(k in ruling for k in (*SHORT_CIRCUITS, *SIGNALS)):
        problems.append(
            "names no deciding signal or short-circuit — a ruling without one is "
            "a verdict, and the phase's requirement is that the SIGNAL be written down"
        )
    if not any(c in ruling for c in (*TIER_INVARIANT, *TIER_SCOPED)):
        problems.append(
            "names no category from the tier contract, so the next reconciliation "
            "re-argues it from first principles"
        )
    if _MAGNITUDE.search(ruling):
        problems.append(
            "contains a similarity magnitude. Drift PATTERN is a signal; drift "
            "MAGNITUDE is one no source uses, and a ruling that reaches for a "
            "percentage was made on the wrong evidence"
        )
    return problems


#: The convention that CREATES signal 4 rather than recovering it. A deliberate
#: variant carries one line saying why, where the variant lives — the cheapest
#: of the four signals and the only one that can be manufactured.
VARIANT_RATIONALE = re.compile(
    r"differs from\s+`?[\w./-]+`?\s+because\s+\S", re.IGNORECASE
)
