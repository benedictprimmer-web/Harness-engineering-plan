# MCP Server Integration

## What MCP Is

The Model Context Protocol (MCP) is an open standard that lets you extend Claude with additional tools beyond its built-in set (Bash, Read, Edit, Write, etc.). An MCP server is a subprocess that Claude communicates with to access those tools.

Common uses:
- **GitHub MCP**: read/write PRs, issues, comments, file contents without shell commands
- **Postgres/SQLite MCP**: run database queries directly
- **Filesystem MCP**: scoped file access with a custom permission model
- **Browser MCP**: headless browser control for testing or scraping
- **Custom MCPs**: wrap your own internal APIs or services

## When to Use MCP vs. Bash

| Situation | Use |
|-----------|-----|
| Need GitHub API (PRs, issues, reviews) | GitHub MCP |
| Need to run ad-hoc SQL queries | DB MCP |
| Standard shell commands (git, npm, python) | Bash tool |
| Reading/editing files in the project | Read/Edit tools |
| Calling your own internal REST API | Custom MCP or Bash+curl |
| One-off CLI tools | Bash tool |

Prefer MCP when: the operation is high-level, structured, and benefits from typed input/output. Prefer Bash when: you're just running a command and the output is what matters.

## Configuration in settings.json

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_TOKEN": "${GITHUB_TOKEN}"
      }
    },
    "postgres": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-postgres", "${DATABASE_URL}"]
    },
    "filesystem": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "/path/to/allowed/directory"
      ]
    }
  }
}
```

The `${VAR_NAME}` syntax interpolates environment variables. Never hard-code tokens.

## Common MCP Servers

### GitHub MCP
```json
"github": {
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-github"],
  "env": { "GITHUB_TOKEN": "${GITHUB_TOKEN}" }
}
```
Tools provided: create/read/update issues, PRs, comments, files, branches, search.

**When to add it**: any project where Claude will interact with GitHub — not just local code changes, but also PR reviews, issue triage, CI status checks.

### PostgreSQL MCP
```json
"postgres": {
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-postgres"],
  "env": { "POSTGRES_CONNECTION_STRING": "${DATABASE_URL}" }
}
```
Tools provided: execute queries, list tables, describe schema.

**Warning**: only point this at dev/staging databases. Add a deny rule for destructive SQL if needed.

### SQLite MCP
```json
"sqlite": {
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-sqlite", "./data/local.db"]
}
```

### Filesystem MCP (Scoped Access)
```json
"filesystem": {
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-filesystem", "./data"]
}
```
Useful for letting Claude access large file trees outside the main project directory (e.g., a data directory) without full Bash access.

## Custom MCP Servers

For internal APIs or project-specific tools, you can write your own MCP server. The SDK supports Python and TypeScript.

### Minimal Python MCP Server

```python
# .claude/mcp-servers/project-tools/server.py
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

app = Server("project-tools")

@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="get_deployment_status",
            description="Get the current deployment status for an environment",
            inputSchema={
                "type": "object",
                "properties": {
                    "environment": {"type": "string", "enum": ["dev", "staging", "prod"]}
                },
                "required": ["environment"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if name == "get_deployment_status":
        env = arguments["environment"]
        # Call your internal API here
        status = fetch_deployment_status(env)
        return [types.TextContent(type="text", text=str(status))]

if __name__ == "__main__":
    import asyncio
    asyncio.run(stdio_server(app))
```

Register it in settings.json:
```json
"project-tools": {
  "command": "python",
  "args": [".claude/mcp-servers/project-tools/server.py"]
}
```

## Security Considerations

1. **Token scoping**: use the minimum required token scope. For read-only GitHub access, use a token with only `repo:read` permissions.

2. **Never commit tokens**: always use `${ENV_VAR}` references. Add a pre-commit check if needed.

3. **Database access**: point MCP database servers at dev/local databases only. Use a read-only database user where possible.

4. **Custom server validation**: if building a custom MCP server, validate all inputs before executing any system commands. MCP servers run with your user's full permissions.

5. **`enableAllProjectMcpServers`**: default is `false`. This means MCP servers in project settings require user confirmation on first use. Set to `true` only for trusted, well-reviewed project settings files.

## MCP + Hooks Together

A common pattern is using MCP for read operations and hooks for write operations that need guardrails:

```
Claude wants to close a GitHub issue
    │
    ├── MCP: read the issue and PR details (fast, safe)
    │
    ├── PreToolUse hook checks: is this issue linked to a production incident?
    │   If yes → block and ask human to confirm
    │
    └── MCP: close the issue
```

This gives you the productivity of MCP's structured tools with the safety of hook-based guardrails.
