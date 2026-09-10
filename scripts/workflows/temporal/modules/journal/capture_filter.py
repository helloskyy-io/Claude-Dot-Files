"""Secrets are kept out at APPEND time — before any byte reaches the journal root.

REQUIREMENT 10, AND THE TIMING IS THE REQUIREMENT. The journal is immutable and
nothing removes a file from inside a bag except a redaction, so **capture is the
only point in the lifecycle where a secret can be cheaply kept out.** After Phase
4 wires the rebuild test to a gate, removing a payload file is a gate change;
after Phase 7 it is a bucket-wide purge. Phase 5's retention budget is not a
control here — it is a size limit, not an age limit, so how long a leaked byte
survives is unknown rather than bounded.

⚠ "AT APPEND" AND NOT "BEFORE SEALED", AND THE DISTINCTION IS LOAD-BEARING UNDER
WRITE-AHEAD ORDERING. `exit_record._redact` already drops tool input *"at READ
TIME, so there is no copy to leak"* — but that control guards a DISPLAY surface.
The journal is a durable one, and under write-ahead ordering it receives every
payload FIRST. Filtering "before sealed" would therefore leave unfiltered bytes
sitting in appended event files for the whole life of the run; and filtering them
AT seal time would change written events, which requirement 8 forbids outright.

**THE FILTER CANNOT RUN RETROACTIVELY.** Redaction (Phase 1's event class) is the
only after-the-fact path, and it is for what gets through. This is the cheap
gate; that is the incident response.

**IT EMITS A PLACEHOLDER**, so the record stays complete about the *fact* of a
removal rather than silently shorter. `events.redaction_placeholder_event` is
that record, and it carries the byte count and the RULE NAME — never what the
rule matched, which is the secret.

⚠ WHAT THIS DOES NOT LOOK AT, stated in the module rather than discovered later.
A pattern filter sees the shapes it was given. It does not see a credential with
no distinguishing shape (a bare password, an eight-character API key), it does
not see one split across two lines by a wrapping terminal, and it does not see
one that is base64 of something it would otherwise catch. It is a floor, and the
component's real control for what gets past it is Phase 1's redaction. Any claim
stronger than "these named shapes do not reach the root" is a claim this module
cannot support.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

__all__ = ["Rule", "RULES", "FilterResult", "filter_capture",
           "placeholder_for"]

def placeholder_for(rule: str) -> str:
    """What a matched span is replaced BY.

    Self-describing: a reader of a journal event must be able to tell "a filter
    fired here" from "the run authored the literal word REDACTED", and a marker
    naming the RULE that fired is what makes the first readable without leaking
    the second.

    A FUNCTION AND NOT A STRING TEMPLATE, because `test_journal_tag_lines.py`
    sweeps this package for tag-line composition and refuses the `str` templating
    method outright — such a call is invisible to a sweep that reads f-strings,
    and this package's rule is that a composition the sweep cannot see does not
    get to exist. The sweep is aimed at `bag-info.txt` lines and this is not one;
    the refusal is still correct, because "it happens not to be a tag line today"
    is precisely the reasoning that lets the next one in.

    ⚠ AND THE SPELLING IS AVOIDED IN THIS DOCSTRING TOO, which is not fussiness:
    the sweep reads the whole file, so naming the method literally here would
    keep this module red while the code was already correct — the assertion's
    population including the text that makes the claim about it.
    """
    return f"[FILTERED:{rule}]"


@dataclass(frozen=True)
class Rule:
    """One named credential shape.

    THE NAME IS PUBLISHED AND THE MATCH IS NOT. A placeholder and a placeholder
    event both carry `name`; neither ever carries the matched text. That is what
    lets an operator distinguish "a GitHub token pattern fired" from "an
    over-broad rule is eating legitimate content" without the record carrying
    either.
    """

    name: str
    pattern: re.Pattern[str]


#: The shapes this fleet actually handles, and nothing speculative. Each is a
#: PREFIXED, self-identifying credential format — which is the class a pattern
#: filter can catch honestly, and the class this repo's own `.env`, `gh` auth and
#: 1Password references are drawn from. An entropy heuristic was considered and
#: rejected: it fires on git SHAs, on `sha256` manifest lines and on every
#: `event_id` in the journal's own events, so it would filter the record's own
#: identity fields and report a leak on every bag.
#:
#: `\A…\Z` IS NOT USED HERE ON PURPOSE — unlike every other regex in this
#: package, these are SEARCHED within a body of text rather than matched against
#: a whole line, so an anchor would make every one of them dead. That is the
#: opposite of the `test_journal_regex_anchors.py` case, which is about
#: validators that look anchored and are not; these do not look anchored.
RULES: tuple[Rule, ...] = (
    Rule("github-token", re.compile(r"gh[pousr]_[A-Za-z0-9]{16,255}")),
    Rule("github-pat", re.compile(r"github_pat_[A-Za-z0-9_]{20,255}")),
    Rule("aws-access-key", re.compile(r"(?:AKIA|ASIA)[0-9A-Z]{16}")),
    Rule("openai-key", re.compile(r"sk-[A-Za-z0-9_-]{20,}")),
    Rule("anthropic-key", re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}")),
    Rule("slack-token", re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}")),
    Rule("google-api-key", re.compile(r"AIza[A-Za-z0-9_-]{35}")),
    Rule("private-key-block",
         re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?"
                    r"-----END [A-Z ]*PRIVATE KEY-----")),
    Rule("bearer-header",
         re.compile(r"(?i:authorization:\s*bearer\s+)[A-Za-z0-9._~+/=-]{12,}")),
    Rule("url-embedded-credential",
         re.compile(r"(?i:https?://)[^\s:/@]+:[^\s:/@]+@")),
)


@dataclass(frozen=True)
class FilterResult:
    """What came out, what was removed, and by which rules.

    `removed_bytes` IS MEASURED ON THE INPUT, NOT ON THE DIFFERENCE. A
    placeholder is usually shorter than the secret it replaced but it need not
    be, and a length difference would report a NEGATIVE removal for a short
    token — a number that reads as "the filter added content". The question the
    record has to answer is *how many bytes of original content did not reach
    the journal*, which is the sum of the matched spans.
    """

    text: str
    removed_bytes: int
    rules_fired: tuple[str, ...]

    @property
    def fired(self) -> bool:
        """DERIVED, NEVER STORED, for the reason `BagReport.ok` is derived: a
        stored flag makes a result constructible that disagrees with its own
        contents, and the disagreement this one would hide is "the filter fired
        and the record says it did not"."""
        return bool(self.rules_fired)


def filter_capture(text: str) -> FilterResult:
    """Replace every known credential shape, and report what was removed.

    TOTAL OVER ITS INPUT — it never raises, and that is a requirement rather than
    a convenience. This runs on the append path of a component whose entire
    thesis is that a failed write must not be silent; a filter that raised on
    some input would convert a leak into a crash on the one path that is supposed
    to keep running. Every failure mode here is "a rule did not match", which is
    the honest boundary stated in the module docstring.

    RULES ARE APPLIED IN ORDER AND THE ORDER IS LOAD-BEARING FOR EXACTLY ONE
    PAIR: `anthropic-key` is a prefix-extension of `openai-key`'s `sk-` shape, so
    the more specific one is listed second and would never fire if the general
    one had already consumed its text. It is applied to the OUTPUT of the
    previous rule, so `sk-ant-…` is reported as `openai-key`. That is a KNOWN
    MISLABEL rather than a leak — both rules remove the same span, so no byte
    reaches the root either way — and it is stated because the alternative
    (matching all rules against the original text and merging spans) buys a
    better label at the cost of overlap arithmetic on the failure path.
    """
    fired: list[str] = []
    removed = 0
    out = text
    for rule in RULES:
        matches = list(rule.pattern.finditer(out))
        if not matches:
            continue
        fired.append(rule.name)
        removed += sum(len(m.group(0)) for m in matches)
        out = rule.pattern.sub(placeholder_for(rule.name), out)
    return FilterResult(text=out, removed_bytes=removed,
                        rules_fired=tuple(fired))
