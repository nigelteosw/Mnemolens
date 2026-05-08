# MCP API

The Mnemolens MCP server exposes a small CRUD API plus retrieval tracing and cleanup for
local context records.

The current tool names use "memory" because that is the implemented storage primitive.
Treat each memory row as an inspectable context record.

## Create

`mnemolens_create_memory`

Creates an active context record and indexes it immediately.

Arguments:

- `category`: one of `semantic`, `episodic`, `procedural`
- `content`: context record text
- `evidence`: optional source quote, summary, or reason this record is useful

## Read

`mnemolens_get_memory`

Fetches one context record by id.

`mnemolens_list_memories`

Lists records by optional `category` and `limit`.

`mnemolens_search_memories`

Retrieves usable context for a task and creates a retrieval trace. Returned records are
written to the trace with `usage_status = selected`.

Default results are intentionally compact:

```json
{
  "memories": [
    {
      "id": "memory-id",
      "category": "semantic",
      "content": "Context record text."
    }
  ]
}
```

Set `include_metadata` to `true` when debugging retrieval. That adds the trace id, search
mode, confidence, scores, match reasons, and usage status to the response.

## Delete

`mnemolens_delete_memory`

Deletes one context record by id. Records are atomic, so replacement means deleting the
old record and creating a new one.

## Trace

`mnemolens_get_trace`

Reads a retrieval trace by id.

## Cleanup

`mnemolens_dream`

Runs deterministic cleanup planning and writes a maintenance report.
