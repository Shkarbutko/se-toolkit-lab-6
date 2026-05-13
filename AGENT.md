# Agent Architecture

## Overview

This project implements a simple CLI-based LLM agent.

The agent accepts a question from command-line arguments or stdin, sends the request to an OpenAI-compatible API, and prints the result as JSON.

## Environment Variables

The agent reads configuration from environment variables:

- `LLM_API_KEY`
- `LLM_API_BASE_URL` or `LLM_API_BASE`
- `LLM_API_MODEL` or `LLM_MODEL`

## Components

### agent.py

Responsible for:
- reading environment variables;
- creating the OpenAI client;
- sending requests to the LLM;
- returning JSON output.

## Testing

Regression tests are located in the `tests/` directory.

## Documentation Tools

The agent supports two tools for documentation access:

### list_files

Returns all available files inside the `wiki/` directory.

### read_file

Reads a file from the `wiki/` directory.

Path traversal protection is implemented to prevent access outside the documentation directory.

## Agentic Loop

The agent uses an iterative tool-calling loop with a maximum of 10 tool calls.

The workflow is:

1. Receive a user question.
2. Call the LLM.
3. Execute requested tools.
4. Append tool results to the conversation.
5. Continue until the LLM returns a final answer.

## Output Format

The agent returns JSON with:

- `answer`
- `source`
- `tool_calls`

## System API Tool

The agent also supports a `query_api` tool.

This tool calls the deployed LMS API using:

- `LMS_API_KEY`
- `AGENT_API_BASE_URL`

If `AGENT_API_BASE_URL` is not set, the default value is `http://localhost:42002`.

The tool returns the HTTP status code and response body. It is used for live backend questions, database state, analytics endpoint behavior, and runtime debugging.
