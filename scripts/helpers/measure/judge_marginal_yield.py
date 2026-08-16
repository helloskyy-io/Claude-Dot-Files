"""Does the separate review pass find anything the producing run had not already said?

THE QUESTION, AND WHY IT IS WORTH ANSWERING. Every build run ends by posting a
Post-Run Reflection — its own account of what went wrong, what it nearly missed,
and what it could not chase. A separate `review-pr` run then reads the PR cold
and posts a disposition with its own findings. That second run costs a full
dispatch. **If most of its findings are restatements of what the first run
already confessed, the marginal yield is low and the cost is not obviously
earned.**

WHAT THIS MEASURES. For every PR carrying BOTH channels, each disposition
finding is classified:

    ECHOED  — the reflection already said it, in the reflection's own words
    NEW     — the judge found something the run did not disclose

The rate of NEW is the judge's marginal yield.

WHAT THIS CANNOT MEASURE, STATED BECAUSE THE FIGURE IS USELESS WITHOUT IT:

  1. **Matching is lexical, not semantic.** A finding and a reflection bullet
     describing the same defect in different words score as NEW. **This biases
     the yield UPWARD** — the true echo rate is at least what is reported.
  2. **A reflection is written to be read.** A run that discloses well makes the
     judge look redundant; a run that buries makes it look essential. The figure
     measures the PAIR, never the judge alone.
  3. **It says nothing about severity.** One NEW finding that stops a bad merge
     is worth more than nine ECHOED ones, and this counts them equally.
  4. **The denominator is what exists, not what was asked for.** The sprint item
     said 30 PRs; the archive holds fewer with both channels. Printed below.

So: read a LOW new-rate as evidence worth investigating, never as a verdict. The
decision this informs is whether to look harder, not whether to delete a pass.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys

# Words that carry no signal about WHAT a finding is about.
STOP = set("""a an the and or but if then than that this these those is are was were be been being
of to in on at by for with from into over under as it its it's not no nor so such only own same
very can will just don should now which who whom what when where why how all any both each few
more most other some there here they them their we you your i me my he she his her one two
run runs ran running pr prs finding findings review reviews reviewed pass passes""".split())


def sig(text: str) -> set[str]:
    """Significant tokens — lowercase words, stopwords and short noise dropped."""
    return {w for w in re.findall(r"[a-z_][a-z0-9_]{2,}", text.lower()) if w not in STOP}


def comments(pr: int) -> list[str]:
    raw = subprocess.run(["gh", "pr", "view", str(pr), "--json", "comments"],
                         capture_output=True, text=True).stdout
    if not raw.strip():
        return []
    return [c.get("body") or "" for c in json.loads(raw).get("comments", [])]


def findings(bodies: list[str]) -> list[str]:
    """Finding titles from every fenced `pr_review:` block carrying a run_id."""
    out = []
    for b in bodies:
        for m in re.finditer(r"```ya?ml\s*\n(pr_review:.*?)\n```", b, re.S):
            block = m.group(1)
            if not re.search(r"^\s*run_id:\s*[0-9a-f]{32}\s*$", block, re.M):
                continue          # not a review pass — see review_pr_activities
            out += re.findall(r"^\s*(?:-\s*)?title:\s*(.+?)\s*$", block, re.M)
    return out


def reflection_bullets(bodies: list[str]) -> list[set[str]]:
    """The producing run's self-disclosure, ONE BULLET AT A TIME.

    MATCHING AGAINST THE WHOLE TEXT WAS THE SECOND BUG AND IT READ AS A RESULT.
    A finding title holds a handful of significant words; a reflection holds
    thousands. Requiring a third of the title's words to appear ANYWHERE in that
    bag is satisfied by chance, and the measurement duly reported 97% echoed.
    A single bullet must cover the title, which is what "the run already said
    this" actually means.

    A COMMENT CARRYING A `pr_review:` BLOCK IS THE JUDGE'S AND IS EXCLUDED
    ENTIRELY. The first version of this function did not exclude it, and a
    disposition comment contains its own Decision Log — so every finding matched
    itself and the measurement reported 100% echoed, 0% new. A figure that
    cannot come out any other way is not a measurement.
    """
    out = []
    for b in bodies:
        if re.search(r"```ya?ml\s*\npr_review:", b, re.S):
            continue          # the judge's comment, not the run's
        for m in re.finditer(r"(?:Post-Run Reflection|Decision Log)(.*?)(?=\n## |\Z)", b, re.S):
            for line in m.group(1).split("\n"):
                line = line.strip()
                if line.startswith(("-", "*")) and len(line) > 40:
                    out.append(sig(line))
    return [s for s in out if s]


# An overlap this large between a finding title and the run's own words is a
# restatement rather than a coincidence. Tuned by hand against a sample and
# stated so a later pass can disagree with a number rather than with a vibe.
ECHO_THRESHOLD = 0.34


def main(lo: int = 40, hi: int = 96) -> int:
    rows, echoed, new = [], 0, 0
    for pr in range(lo, hi):
        bodies = comments(pr)
        if not bodies:
            continue
        fs = findings(bodies)
        bullets = reflection_bullets(bodies)
        if not fs or not bullets:
            continue
        e = n = 0
        for title in fs:
            t = sig(title)
            if t and any(len(t & b) / len(t) >= ECHO_THRESHOLD for b in bullets):
                e += 1
            else:
                n += 1
        rows.append((pr, len(fs), e, n))
        echoed += e
        new += n

    total = echoed + new
    print("# The judge's marginal yield — disposition findings the run had NOT already disclosed\n")
    print(f"  PRs carrying BOTH channels : {len(rows)}   <- THE DENOMINATOR")
    print(f"  disposition findings       : {total}")
    if not total:
        print("  no findings to classify")
        return 0
    print(f"  ECHOED by the reflection   : {echoed}  ({echoed/total*100:.0f}%)")
    print(f"  NEW to the judge           : {new}  ({new/total*100:.0f}%)   <- the marginal yield")
    print(f"\n  echo threshold             : {ECHO_THRESHOLD}"
          f"  (share of a title's words ONE reflection bullet also used)")
    print("\n  THE FIGURE'S OWN LIMIT: matching is LEXICAL. The same defect described in")
    print("  different words counts as NEW, so the true echo rate is AT LEAST the one")
    print("  above and the yield is AT MOST the one above. Severity is not weighted —")
    print("  one NEW finding that stops a bad merge counts the same as nine echoes.\n")
    print("  Per-PR:")
    print(f"    {'pr':>5} {'findings':>9} {'echoed':>7} {'new':>5}")
    for pr, f, e, n in rows:
        print(f"    {pr:>5} {f:>9} {e:>7} {n:>5}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
