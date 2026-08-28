---
id: C-jp5gt9tm
title: A gated phase whose gate changes the shape of the work carries one figure that hides a two-to-one swing, and the parser cannot read a range
status: open
count: 1
filed: 2026-08-28
filed_by: review-pr
component: workflow-decomposition
size: 
decision: 
---

**PROPOSAL — a stated convention for sizing a phase whose gate changes what the work IS.**

**Raised by `plan-verify` on PR #145**, sizing *Managed configuration, and whose tier wins*:

> *"The brief says to size a gated phase 'on what it will cost when it starts'. For [that phase] the figure swings roughly two-to-one on the third gate's answer (adopt the vendor tier versus write one), and a single number hides that."*

**Why a range is not the answer, and this is settled ground:** nothing sums a range in code, and the operator ruled single figures for the sprint header on exactly that basis (2026-08-28, mirrored from MDC). Re-introducing one here pushes the same defect down a level.

**Consequence:** a phase sized at the midpoint of a two-to-one swing is wrong in both branches, and the sprint total that absorbs it carries a confidence it has not earned — with nothing on the page saying so.

**Remedy:** a required **"swings on"** clause beside the figure — the gate, and what the figure becomes under each answer. Prose beside a single parseable number, so the parser is unaffected and the reader is not misled.
