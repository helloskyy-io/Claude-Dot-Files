---
name: my-document-intelligence
description: Retrieve and reference the user's own personal stored documents from their connected Google Drive. Trigger this skill specifically when the user says "my document intelligence" (or invokes the /my-document-intelligence slash command). This is the deliberate, unambiguous trigger phrase chosen by the user to avoid false positives. Do NOT trigger for generic information requests, web-search-style questions, or general knowledge — this skill is exclusively for the user's curated personal document library, invoked on purpose.
---

# My Document Intelligence

This skill connects you to the user's personal document library so your answers can be grounded in their actual stored notes, data, and reference material — not just general knowledge or the web.

## Trigger

This skill is invoked intentionally, not automatically. It fires when the user says **"my document intelligence"** or uses the **`/my-document-intelligence`** slash command. The phrasing is deliberately specific so it never collides with web search or general questions. If the user hasn't used that phrase or command, don't invoke this skill.

## Where the documents live

- All referenceable documents live in the user's connected **Google Drive** (via the Google Drive MCP connector).
- They are stored under a single root folder named **`Claude`**.
- Unless the user explicitly directs you elsewhere ("look in my Work drive", "check the Shared folder"), treat the `Claude` folder as the only location to search. Do not wander the rest of the Drive.

## How to use this skill

### Step 1: Read the index first
At the root of the `Claude` folder there is an index file named **`_INDEX.md`**. It lists every file and subfolder with a name and a one-line description of its contents. **Always read this index first.** It is the map — reading it tells you what exists and where, so you can fetch only what's relevant instead of blindly searching the whole folder.

If you can't find `_INDEX.md`, fall back to listing/searching the `Claude` folder directly, and gently let the user know the index is missing so they can create or repair it.

### Step 2: Identify what's relevant
Using the user's request and the index, decide which document(s) actually bear on the question. The folder is organized into topical subfolders. Match the user's topic to the right subfolder and file.

### Step 3: Retrieve and ground your answer
- If one document is clearly the right source, read it and answer from it.
- If a few documents are plausibly relevant and the files are short, read them all and synthesize.
- If it's genuinely ambiguous which of several documents the user means, briefly list what you found and let them narrow it. Don't make them guess what you found.

### Step 4: Be explicit about your source
When you answer from a retrieved document, make it clear you're drawing on their stored file (e.g. "According to your workout doc...") so the user knows the answer is grounded in their own data.

## Maintaining the index

The index file is what makes this skill fast and accurate, so keep it current.

- When the user adds a new document to the `Claude` folder, remind them (or offer) to add a corresponding entry to `_INDEX.md`: path, name, and a one-line description.
- When a document is renamed, moved, or deleted, update the index entry to match.
- A good index entry looks like: `Health and Fitness/Puma Workout — Puma's current lifting split, exercises, sets, and reps.`
- If you notice the index and the actual folder contents have drifted out of sync, point it out so it can be corrected.

## Scope notes

- This skill is about the user's **own curated documents**. It is not a replacement for web search (current events, external facts) or built-in knowledge (general explanations). Don't force a document lookup where another tool fits better.
- Write access to the Drive may be restricted to read/search only. If asked to create or modify a file and you lack permission, say so plainly rather than failing silently.
- Designed to extend beyond Google Drive later (other stores, other connectors). Keep the language about "the user's document library" general where possible, with Google Drive as the current backing store.
