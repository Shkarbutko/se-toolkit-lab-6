# Task 2 Plan

## Goal

Extend the CLI agent so it can answer questions using project wiki documentation.

## Steps

1. Add two tools: `list_files` and `read_file`.
2. Protect file access from path traversal.
3. Register tools as OpenAI-compatible function schemas.
4. Implement an agentic loop with a maximum of 10 tool calls.
5. Store all tool calls in the output JSON.
6. Return `answer`, `source`, and `tool_calls`.
7. Update `AGENT.md`.
8. Add regression tests for tool usage.
