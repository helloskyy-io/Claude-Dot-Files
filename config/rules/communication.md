# Communication

- Don't add docstrings, comments, or type annotations to code you didn't change.
- Ask before making changes beyond what was requested.

## Asking the operator for a call — the protocol, in order

**This protocol exists because it kept being taught in conversation and dying there.** The operator has given it more than once; every session that never saw those messages reverts to handing them a decision written in private vocabulary. Written here, it reloads.

**1 · Run the lenses before you ask, not after.** `/decide` on the question as posed — the five whys, looking for the upstream choice that makes the fork disappear — then `/best-practices` on whatever question survives. Most calls dissolve here. A fork that dissolves is not a call; it is work, so do it and say what you did.

**2 · If it does not dissolve, write the explanation for someone with none of your context.** They have not read the file, do not know what the function is called, were not in the run that surfaced it, and are not going to look. Everything they need is in what you write or it is not available to them.

**3 · Put your recommendation at the end, and say it came from the lenses.** Not a menu handed over with a shrug. You did the work; say which way you would go and why. The operator overrules or accepts, and either takes them ten seconds instead of an hour.

## Writing the explanation

**Define any term that is not ordinary English, the first time you use it, in the same sentence.** Not a glossary at the end, not on second use. This includes vocabulary this codebase invented — a *vacuity floor*, a *one-way door*, a *carrier*, a *seam* — and every abbreviation, including the ones in the tree.

**Never invent shorthand mid-explanation.** If you catch yourself compressing a concept into a phrase to save words, you have started writing for yourself. Spend the words.

**Say what happens, not what class it is.** *"A dependency edge, not a seam"* tells the reader nothing. *"The button in the interface doesn't change how this gets built"* is the same sentence with the meaning left in. When describing an option, say what it costs and what breaks if it is wrong — never what category it belongs to.

**Lead with the decision, then the reasoning.** The first line says what is being decided and what you would do. Everything after is support. A reader who stops after one line should still have the answer.

**Do not re-ask what has been ruled.** Search the conversation and the corpus first. A question the operator has already answered spends their attention re-deciding, and it reads as not listening — because it is.

**Length is not the problem and brevity is not the fix.** A short explanation in shorthand is worse than a long one in plain words. Write as much as the reader needs and no jargon at all.

**Breaking it looks like:** a decision handed over without the lenses having been run; an explanation that assumes the reader has read the code; a term used before it is defined; a request for a ruling the operator has already given; a recommendation withheld because "it is the operator's call" — it is, and they still want yours.
