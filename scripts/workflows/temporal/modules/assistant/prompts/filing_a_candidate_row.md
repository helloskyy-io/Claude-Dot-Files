**FILING A CANDIDATE ROW — the two steps, and the second one is why runs push red.**

1. **Append the row inside the table block**, with no blank line before it. A row separated from the table by a newline is not part of the table — it renders as a paragraph and two guards fire on it.
2. **THEN UPDATE THE DERIVED DECLARATIONS THAT COUNT IT.** `candidates.md` § *Where things stand* states the untriaged total and the id range, and a test DERIVES both from the table and fails when the prose disagrees. Appending a row changes both. **A run that files a correct row and stops here has pushed a red suite**, which reads as a broken change rather than a finished one.

**Run the suite before you commit.** These two guards are cheap to trip and their messages name the exact remedy; neither is discoverable by reading the file you are editing.
