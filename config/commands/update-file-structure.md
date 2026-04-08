Update the docs/file_structure.txt file to accurately reflect the current state of the project.

Process:
1. Scan the project's actual file and directory structure
2. Compare it against the existing docs/file_structure.txt
3. Update the tree to match reality — add new files/directories, remove deleted ones, update comments

Format rules:
- Use ASCII tree characters (├── │ └──) for the hierarchy
- Add a short comment on the right side (using #) explaining the purpose of each file or directory
- Align comments for readability
- List directories before files at each level
- Include all files and directories that are part of the project

Component boundary rule:
- If a subdirectory or component has its own docs/ folder with its own file_structure.txt, stop at that component's directory name with a comment noting it is self-documenting
- Do not expand into that component's internals — its own file_structure.txt handles that

Preserve any supplementary sections below the tree (e.g., symlink maps, notes) but update them if they are outdated.

Present the updated file_structure.txt for review before writing it.

$ARGUMENTS
