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
