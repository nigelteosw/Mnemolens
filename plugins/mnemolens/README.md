# Mnemolens Codex Plugin

Mnemolens is a local-first context layer for Codex and other AI development tools. It
exposes a FastMCP server backed by SQLite so Codex can retrieve local context, record
usage traces, manage context records through simple CRUD tools, and run `/dream`
maintenance reports.

The current MCP tool names use "memory" because that is the implemented storage
primitive. Product docs should treat those memories as local context records, not as the
whole product identity.

See also:

- [RFC: Local context layer](../../docs/rfc-local-context-layer.md)
- [Context record lifecycle](../../docs/memory-lifecycle.md)
- [MCP API](../../docs/mcp-api.md)

## Local Server

The plugin starts the server through:

```bash
plugins/mnemolens/scripts/mnemolens-mcp
```

## Install From GitHub

After the repository is published, users can add the marketplace directly:

```bash
codex plugin marketplace add nigelteosw/Mnemolens
```

Then restart Codex and install or enable the `Mnemolens` plugin. The plugin runs locally:
the MCP server is started on the user's machine and stores data in local SQLite. GitHub is
only the distribution path.

On first start, the launcher uses `uv` when available. Without `uv`, it creates a
plugin-local virtual environment and installs the server package automatically.

To pull a newer version after this marketplace has already been added:

```bash
codex plugin marketplace upgrade mnemolens
```

## First-Time Local Development

Preferred path with `uv`:

```bash
brew install uv
make bootstrap
```

Without `uv`, the same bootstrap script creates a plugin-local virtual environment at
`plugins/mnemolens/server/.venv` and installs the server package there:

```bash
make bootstrap
```

After bootstrap, Codex can start the MCP server with `scripts/mnemolens-mcp`.
From the repo root, `make dev` runs the server through `uv` and `make mcp` runs the same
launcher Codex uses.

Default database path:

```bash
~/.codex/mnemolens/mnemolens.sqlite3
```

Override with:

```bash
MNEMOLENS_DB_PATH=/path/to/mnemolens.sqlite3
```

## Development

From the server directory:

```bash
uv run pytest
```

The server uses SQLite FTS5 and the FTS5 trigram tokenizer. Startup fails if either
capability is unavailable.

## Inspecting Tables

From the repo root:

```bash
make inspect-db
```

Then in `sqlite3`:

```sql
.tables
.schema memories
.headers on
.mode box
```
