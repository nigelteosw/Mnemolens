# Context Record Lifecycle

Mnemolens keeps the hot path simple: Codex can write compact context records directly,
and those records are usable immediately.

The current implementation calls these records "memories" in the SQLite schema and MCP
tool names. That name is an implementation detail. Product-facing docs should frame
Mnemolens as a local context layer with inspectable records and traces.

## Hot Path

When Codex learns something worth preserving as local context, it calls
`mnemolens_create_memory`. The record is inserted, indexed for retrieval, and available
to later `mnemolens_search_memories` calls.

The hot path should capture small useful semantic, episodic, and procedural context.
Evidence can be stored for later inspection, but recall should return only compact
context and ranking metadata.

## CRUD

The MCP surface is intentionally plain:

- `mnemolens_create_memory` creates an active context record.
- `mnemolens_get_memory` reads one record by id.
- `mnemolens_list_memories` reads records by category and limit.
- `mnemolens_delete_memory` deletes one record by id.

Records are atomic. There is no update tool. If a record needs to be merged, narrowed,
or replaced, delete the old row and create a new row.

`mnemolens_search_memories` is the retrieval path. It records returned context as
`selected` in the retrieval trace during the search call. There is no separate public
usage-recording step; selection is the usage event that Mnemolens records.

## Dream Cleanup

`/dream` is the maintenance path. It audits active records after the hot path has
collected them.

The cleanup report should help with:

- duplicate records
- weak records with low confidence or little evidence
- records that should be replaced
- cleanup actions that should delete old rows and create replacements

The current MVP writes a report and does not apply cleanup automatically. That keeps
writes cheap during normal work while leaving delete-then-create decisions inspectable.
