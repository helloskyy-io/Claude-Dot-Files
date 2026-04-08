Analyze this project's codebase and create CLAUDE.md files for the project root and all major directories.

For each CLAUDE.md:

1. **Project root CLAUDE.md** should include:
   - Project name and brief description
   - Tech stack and key dependencies
   - How to run, build, and test the project
   - Project-wide conventions and patterns
   - References to applicable project-wide standards from /docs/standards/

2. **Subdirectory CLAUDE.md files** should include:
   - Purpose of this directory
   - Key patterns and conventions specific to this area
   - Important files and their roles
   - References to applicable standards from /docs/standards/

Use this format for standard references:
"For [topic] standards, refer to docs/standards/[filename]"

Guidelines:
- Only reference standards that are directly relevant to the directory's context
- Keep each CLAUDE.md focused and concise — this is a quick-reference for Claude, not full documentation
- Derive information from the actual code, not assumptions — read the files before writing about them
- Do not overwrite existing CLAUDE.md files — if one already exists, report what you would change and ask for approval
- Present all proposed CLAUDE.md files for review before creating them

$ARGUMENTS
