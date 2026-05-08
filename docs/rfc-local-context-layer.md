# RFC: Mnemolens Local Context Layer

**Status**: Draft
**Author**: Nigel Wei
**Date**: 2026-05-08

---

## Summary

Mnemolens is observable long-term memory for AI development tools. It stores compact
semantic, episodic, and procedural context plus retrieval traces so tools like Codex can
work with durable local context without turning that context into hidden model state.

Long-term memory is the capability; observability is the differentiator. Mnemolens is
not just a place where agents store facts. It is a local context layer that shows what
was retrieved, why it was retrieved, and how the user can correct it.

The MVP starts as a plug-and-play Codex plugin backed by SQLite and exposed through a
local FastMCP server. It should work without a hosted backend, account system, Postgres
server, or cloud embedding dependency.

---

## Product Thesis

AI coding tools need long-term memory, but memory is only trustworthy when it is
observable. Useful context is small, local, inspectable, and grounded in evidence. Bad
context is broad, stale, invisible, and hard to correct.

Mnemolens should be the local infrastructure layer that makes context usable:

- retrieve the few context records that matter for the current repo and task
- show why context matched the current request
- record selected context during retrieval without a second usage update
- let the user inspect, create, and delete atomic context records
- keep the trust boundary local by default

The capability is that the assistant can remember useful long-term context. The
differentiator is that the user can debug the context pipeline.

---

## Positioning

### What Mnemolens Is

- Observable long-term memory for AI development tools.
- A local context layer for AI development tools.
- A SQLite-backed workbench for project and user context.
- A trace system for context retrieval and usage.
- A Codex plugin that makes local context available through MCP tools.
- A maintenance workflow for reviewing weak, duplicate, or replaceable records.

### What Mnemolens Is Not

- A replacement for every native model memory feature.
- A transcript archive.
- A hosted knowledge base in the MVP.
- A general personal CRM.
- A system that asks users to trust invisible context.

### Language

Prefer:

- context layer
- context records
- retrieval traces
- local context
- local workbench
- inspectable context

Use "memory" only when referring to the current storage primitive, existing MCP tool
names, or the table/API shape already implemented.

---

## Target Users

### Primary User

An engineer who uses Codex across local repositories and wants the tool to pick up stable
project context without repeating setup instructions every session.

Examples:

- Semantic: "This repo uses FastMCP for the local server."
- Semantic: "Use indexed SQLite search only; do not add SQL LIKE fallback."
- Procedural: "Run the repo-standard test command before summarizing changes."
- Procedural: "When resolving conflicts, inspect both sides before staging."
- Episodic: "The last router-auth merge kept the branch version after ancestry checks."

### Secondary User

A power user or team lead who wants to inspect the context that shaped an AI tool's work
before trusting the result or delegating follow-up tasks.

---

## Core Use Cases

### 1. Retrieve Local Context

When a user asks Codex to work, Mnemolens retrieves local context for that user:

- package manager and setup commands
- semantic project context
- episodic prior work and corrections
- procedural workflow conventions
- repo-specific conventions
- known CI, deployment, or local setup caveats

The value is less repeated explanation and fewer wrong assumptions.

### 2. Explain Tool Behavior

After a response, the user can inspect:

- which records were retrieved
- why each record matched
- the score or match reason from vector, FTS5, or trigram search
- which records were selected into the retrieval trace

This turns context from prompt-hidden state into debuggable project state.

### 3. Maintain Context Quality

Users should be able to list, inspect, create, and delete records directly. Records are
atomic: there is no edit path. If a record needs to be merged or replaced, delete the
old row and create a new row.

The `/dream` maintenance workflow reviews the current store and produces a report for:

- duplicate records
- weak records with little evidence
- records that should be replaced
- cleanup actions that should be reviewed as delete-then-create operations

### 4. Capture Durable Corrections

When the user corrects the AI tool in a way that will matter later, Mnemolens can store
that episode as a local context record. The record becomes usable immediately, while
later maintenance can replace it by deleting the old record and creating a better one.

---

## MVP Architecture

```text
Codex
  |
  | plugin skill + MCP tools
  v
Mnemolens Codex Plugin
  |
  | starts local server over stdio
  v
Local FastMCP Server
  |
  | reads/writes
  v
SQLite database
  |
  +-- context records
  +-- evidence for inspection
  +-- retrieval traces
  +-- maintenance reports
```

The current implementation names the storage primitive `memory` in tool and table names.
That is acceptable for the MVP. Product documentation should present the wider concept
as local context infrastructure, with memory as an implementation detail.

---

## Retrieval Requirements

Mnemolens should use indexed retrieval only:

- vector search for semantic recall
- SQLite FTS5 for exact tokens and identifiers
- SQLite FTS5 trigram tokenizer for fuzzy text matching

Raw SQL substring matching with `LIKE` or wildcard table scans is not an acceptable
fallback. If required SQLite search capabilities are missing, startup should fail rather
than silently degrading retrieval quality.

The MVP should stay local to one user. It does not need `scope_type`, `scope_key`,
workspace-level filtering, global records, or shared/team scopes yet.

## Category Model

Mnemolens should keep the top-level category system small:

- `semantic`: stable knowledge about a project, user, domain, dependency, command, or
  concept
- `episodic`: prior events, corrections, incidents, debugging outcomes, merge outcomes,
  or task history that may matter later
- `procedural`: reusable workflows, operating instructions, style conventions, and
  step-by-step preferences

These categories are intentionally broad. More specific labels should live in tags or
metadata rather than becoming new top-level categories.

---

## MCP Surface

The current tool names can remain memory-oriented while the product framing shifts:

| Tool | Context-layer role |
|------|--------------------|
| `mnemolens_search_memories` | Retrieve usable context and record selected results in a trace |
| `mnemolens_create_memory` | Create an immediately usable context record |
| `mnemolens_list_memories` | Inspect records by category |
| `mnemolens_get_memory` | Read one record |
| `mnemolens_delete_memory` | Delete one record |
| `mnemolens_get_trace` | Inspect one retrieval trace |
| `mnemolens_dream` | Generate a context-quality maintenance report |

Renaming tools can wait until there is a compatibility plan. The near-term priority is
clear docs and stable local behavior.

---

## Phased Plan

### Phase 0: Local Plugin Baseline

- Codex plugin manifest
- FastMCP server over stdio
- SQLite database and schema
- FTS5 and trigram startup checks
- Basic CRUD and retrieval tools
- Local bootstrap, dev, test, and database inspection commands

### Phase 1: Useful Context

- Local single-user store
- Categories for semantic, episodic, and procedural context
- Hybrid vector, FTS5, and trigram ranking
- Immediate writes from explicit user requests or useful corrections
- Atomic rows with no edits; replacement means delete then create
- Direct table inspection through SQLite

### Phase 2: Observability

- Retrieval trace recording
- Per-mode retrieval scores
- Evidence available for inspection, not included in recall payloads
- Trace inspection through MCP and workbench views

### Phase 3: Maintenance

- `/dream` reports for duplicates, weak records, and replacements
- Reviewable cleanup actions
- Export/import JSON
- Optional migration path if tool names shift from memory to context

### Phase 4: Optional Expansion

- Local web workbench
- Advanced vector indexing
- Team or shared scopes, if there is demand
- Hosted sync only if it does not compromise the local-first trust boundary

---

## Key Decisions

### 1. Observable Long-Term Memory

**Decision**: Position Mnemolens as observable long-term memory and local context
infrastructure for AI development tools.

**Rationale**: Long-term memory is the capability users understand and need.
Observability is the reason Mnemolens is more trustworthy than hidden model state or a
plain memory store. This framing keeps retrieval, inspection, traceability, and user
control at the center while still being clear that the system provides durable memory.

### 2. SQLite By Default

**Decision**: Use SQLite for the MVP.

**Rationale**: The product should be plug-and-play, inspectable, and easy to delete or
back up. Requiring infrastructure would weaken the local-first promise.

### 3. Observability Is First-Class

**Decision**: Retrieval traces, evidence, and cleanup reports are product
features, not internal logs.

**Rationale**: Users need to debug why an AI tool behaved a certain way. Invisible context
is hard to trust.

### 4. Keep Current Tool Names For Now

**Decision**: Keep the `mnemolens_*_memory` tool names in the MVP.

**Rationale**: The implementation already works, and renaming the API would add migration
risk before the product vocabulary is stable. Documentation can describe those tools as
managing context records.

### 5. Atomic Records

**Decision**: Context records are immutable after creation.

**Rationale**: Immutable rows keep the hot path simple and make cleanup auditable. If a
record is stale, duplicated, or too broad, `/dream` should propose deleting the old row
and creating a replacement row rather than editing in place.

---

## Open Questions

1. Should the storage primitive eventually be renamed from memory to context record?
2. Should the workbench be served by the MCP server or built as a separate local app?
3. What minimum trace metadata is useful when Codex does not expose response IDs?
4. Should `/dream` ever apply cleanup automatically, or always produce reviewable plans?
5. How should existing Codex memory files be imported without carrying stale context
   forward?

---

## Success Metrics

- Users repeat fewer repo setup instructions.
- Users can identify which context influenced an AI tool response.
- Users can correct stale context through delete-then-create replacements.
- Retrieval stays fast for at least 5,000 local records.
- The plugin works from a clean install without Postgres or cloud services.
- The product is understandable as long-term memory whose differentiator is observability.
