Scan the /docs/standards/ directory for all standard definition files. Then review each CLAUDE.md file in the project (root and subdirectories) and update their references to standards.

For each CLAUDE.md:
1. Determine which standards are relevant based on the directory's purpose and context
2. Add references to applicable standards that are missing
3. Remove references to standards that no longer exist or aren't relevant to that directory
4. Do not modify any other content in the CLAUDE.md files

Use this format for references:
"For [topic] standards, refer to docs/standards/[filename]"

Guidelines:
- Be selective — only reference standards that are directly relevant to the code in that directory
- Root CLAUDE.md should reference project-wide standards (code style, git, security) but not module-specific ones
- Subdirectory CLAUDE.md files should reference standards specific to their domain (e.g., /api references API standards, /frontend references UI standards)
- If a directory has no CLAUDE.md but would benefit from standard references, suggest creating one but do not create it without approval

$ARGUMENTS
