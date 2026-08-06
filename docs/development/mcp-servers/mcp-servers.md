# MCP Servers

**Notes predating planning.** This sprint has been untouched since April and nothing depends on it. What follows is reference material collected at the time, moved here out of the sprint plan. It is not a plan — when the sprint is picked up, planning starts fresh and this becomes input.

## Scopes

- **User scope** (`~/.claude.json`): personal API keys and tokens. NOT synced by this repo, because it contains secrets.
- **Project scope** (`.mcp.json` in repo root): shared server definitions, committed to git. No secrets — use `${env:VAR_NAME}`.
- **Local scope** (default): only on the current machine. Good for experimental servers.

## Transports

stdio (local process, most common), HTTP (remote and cloud services, recommended for new servers), SSE (deprecated — use HTTP).

## Docker

MCP servers can run as containers, which buys isolation and reproducibility. Useful for servers with complex dependencies or a specific runtime. Under Docker Desktop the server runs inside the container and communicates over stdio or HTTP.

## Standing considerations

- **`gh` CLI already covers the common ground** — PR creation and simple operations, at lower context cost than a GitHub MCP server. The rule to test when this is picked up: `gh` for high-frequency simple operations, MCP for complex structured queries (reading PR comments programmatically, triaging issues with structured data, cross-repo queries).
- **Each server has a context cost.** Adding several at once is how that cost stops being visible.
- Candidate servers noted in April: Playwright (browser testing), Sentry (error monitoring), PostgreSQL/Supabase, Linear/Jira.
