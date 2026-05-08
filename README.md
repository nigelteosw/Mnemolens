# Mnemolens

Mnemolens is a local-first context layer for AI development tools. The current
implementation lives in `plugins/mnemolens` and provides a Codex plugin with a FastMCP
server backed by SQLite.

It stores compact local context, retrieves it for coding tasks, records retrieval
traces, and keeps the data inspectable through local tools. The current API still uses
the word "memory" for the storage primitive, but the product direction is broader than
agent long-term memory.

## Docs

- [RFC: Local context layer](docs/rfc-local-context-layer.md)
- [Context record lifecycle](docs/memory-lifecycle.md)
- [MCP API](docs/mcp-api.md)

## First-Time Local Setup

Preferred:

```bash
brew install uv
make bootstrap
```

Fallback without `uv`:

```bash
make bootstrap
```

The fallback creates a plugin-local virtual environment at:

```bash
plugins/mnemolens/server/.venv
```

The MCP launcher is:

```bash
make mcp
```

For development with `uv`:

```bash
make dev
```

`make dev` runs the FastMCP stdio server through `uv`. It is meant for MCP clients that
spawn the process, so it will wait on stdio.

Run tests with:

```bash
make test
```

## Use With Codex

This repo includes a local Codex plugin marketplace entry:

```bash
.agents/plugins/marketplace.json
```

The marketplace points Codex at:

```bash
plugins/mnemolens
```

First install the server dependencies:

```bash
make bootstrap
```

Then restart Codex from this repo so it can discover the local marketplace. Install or
enable the `Mnemolens` plugin in Codex. Codex will start the MCP server through the
plugin config:

```bash
plugins/mnemolens/scripts/mnemolens-mcp
```

To verify the launcher yourself:

```bash
make mcp
```

That command starts a stdio MCP server, so it waits for an MCP client and may look idle.

## Inspect The SQLite Database

Open the local database with:

```bash
make inspect-db
```

Useful commands inside `sqlite3`:

```sql
.tables
.schema memories
.headers on
.mode box

SELECT id, category, confidence, content
FROM memories
ORDER BY created_at DESC
LIMIT 20;
```

The default SQLite database path is:

```bash
~/.codex/mnemolens/mnemolens.sqlite3
```
