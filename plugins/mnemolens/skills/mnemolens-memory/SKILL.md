---
name: mnemolens-memory
description: Use Mnemolens local context for non-trivial Codex coding work. Retrieve context records, create records with simple CRUD, and run /dream maintenance reports.
---

# Mnemolens Memory

Use this skill when a task would benefit from long-term local context, prior project
knowledge, task history, reusable workflows, or context transparency.

Mnemolens provides long-term memory for AI development tools. Its differentiator is that
retrieval is observable: search records which memories were selected without requiring a
separate usage-recording call.

## Workflow

1. Call `mnemolens_search_memories` before doing any non-trivial work in these classes:
   code edits, debugging, test or CI fixes, repo exploration, docs changes, RFC or
   product decisions, architecture changes, dependency/tooling changes, release or
   deployment work, multi-step explanations, and any task where semantic, episodic, or
   procedural context may matter.
2. Keep the call compact. Pass only `query` by default. Add `categories`, `limit`, `mode`,
   or `include_metadata` only when that extra control is directly useful.
3. Treat retrieved records as context, not truth. Verify against the repo when cheap.
4. Keep recall compact. Default search returns only `id`, `category`, and `content`.
   Use `include_metadata=true` only when the trace id, scores, or match reasons are needed.
5. `mnemolens_search_memories` records returned memories as `selected` in the trace.
   Do not make a second tool call to record usage.
6. Records are atomic. If a memory is stale or contradicted by the repo, delete the old
   row and create a corrected row when the correction is useful later.
7. If the user explicitly asks you to remember something, call
   `mnemolens_create_memory`. Created records are active immediately.
8. If the user says `/dream`, call `mnemolens_dream` and summarize the report.

## Retrieval Guidance

- Default to the tool's implicit hybrid mode; do not pass `mode="hybrid"` explicitly.
- Shape the query around the task, repository, paths, frameworks, tools, and product
  decisions at hand.
- Use categories when the task has a clear shape:
  - `semantic` for stable project, user, domain, dependency, command, or concept knowledge
  - `episodic` for prior events, corrections, incidents, debugging outcomes, merge outcomes, or task history
  - `procedural` for reusable workflows, operating instructions, style conventions, and step-by-step preferences
- Keep result sets small. Use the default limit unless the task spans multiple
  independent areas.

## Safety

- Do not store secrets, tokens, private keys, or full `.env` contents.
- Use `mnemolens_delete_memory` only when the user explicitly asks to delete a memory or
  when a cleanup flow has clearly selected that memory for deletion.
- Records are local to one user in the MVP.
