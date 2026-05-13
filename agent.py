import json
import os
import sys
from pathlib import Path
from typing import Any

import requests
from openai import OpenAI


PROJECT_ROOT = Path(__file__).resolve().parent
WIKI_DIR = PROJECT_ROOT / "wiki"
MAX_TOOL_CALLS = 10


def get_env(name: str, fallback: str | None = None) -> str:
    value = os.environ.get(name)

    if value is None and fallback is not None:
        value = os.environ.get(fallback)

    if not value:
        raise RuntimeError(f"Missing environment variable: {name}")

    return value


def safe_wiki_path(path: str) -> Path:
    requested_path = (WIKI_DIR / path).resolve()

    if not str(requested_path).startswith(str(WIKI_DIR.resolve())):
        raise ValueError("Path traversal is not allowed")

    if not requested_path.is_file():
        raise FileNotFoundError(f"File not found: {path}")

    return requested_path


def list_files() -> list[str]:
    if not WIKI_DIR.exists():
        return []

    files = []

    for file_path in WIKI_DIR.rglob("*"):
        if file_path.is_file():
            files.append(str(file_path.relative_to(WIKI_DIR)))

    return sorted(files)


def read_file(path: str) -> str:
    file_path = safe_wiki_path(path)
    return file_path.read_text(encoding="utf-8")


def query_api(method: str, path: str, body: str | None = None) -> str:
    api_key = get_env("LMS_API_KEY")
    base_url = os.environ.get("AGENT_API_BASE_URL", "http://localhost:42002").rstrip("/")

    if not path.startswith("/"):
        path = "/" + path

    url = f"{base_url}{path}"

    headers = {
        "X-API-Key": api_key,
    }

    json_body = None
    if body:
        json_body = json.loads(body)

    response = requests.request(
        method=method.upper(),
        url=url,
        headers=headers,
        json=json_body,
        timeout=15,
    )

    return json.dumps(
        {
            "status_code": response.status_code,
            "body": response.text,
        },
        ensure_ascii=False,
    )


def run_tool(name: str, arguments: dict[str, Any]) -> Any:
    if name == "list_files":
        return list_files()

    if name == "read_file":
        return read_file(arguments["path"])

    if name == "query_api":
        return query_api(
            method=arguments["method"],
            path=arguments["path"],
            body=arguments.get("body"),
        )

    raise ValueError(f"Unknown tool: {name}")


def get_tools() -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": "list_files",
                "description": "List all available wiki documentation files.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read a file from the wiki documentation directory.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Relative path to a wiki file.",
                        }
                    },
                    "required": ["path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "query_api",
                "description": (
                    "Call the deployed LMS backend API. "
                    "Use this for live system data, item counts, HTTP status codes, "
                    "analytics endpoints, and backend runtime behavior."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "method": {
                            "type": "string",
                            "description": "HTTP method, for example GET or POST.",
                        },
                        "path": {
                            "type": "string",
                            "description": (
                                "API path, for example /items/ or "
                                "/analytics/completion-rate?lab=lab-99."
                            ),
                        },
                        "body": {
                            "type": "string",
                            "description": "Optional JSON request body as a string.",
                        },
                    },
                    "required": ["method", "path"],
                },
            },
        },
    ]


def ask_llm(question: str) -> dict[str, Any]:
    api_key = get_env("LLM_API_KEY")
    base_url = get_env("LLM_API_BASE_URL", "LLM_API_BASE")
    model = get_env("LLM_API_MODEL", "LLM_MODEL")

    client = OpenAI(api_key=api_key, base_url=base_url)

    messages: list[dict[str, Any]] = [
        {
            "role": "system",
            "content": (
                "You are a system agent for the LMS project. "
                "Use read_file for wiki and source-code questions. "
                "Use list_files when you need to discover available files or router modules. "
                "Use query_api for live backend questions, database counts, HTTP status codes, "
                "analytics endpoint behavior, and runtime errors. "
                "For bug diagnosis, first call query_api to observe the error, then read_file "
                "to inspect the relevant source code. "
                "Always answer based on tool results, not guesses."
            ),
        },
        {
            "role": "user",
            "content": question,
        },
    ]

    recorded_tool_calls = []

    for _ in range(MAX_TOOL_CALLS):
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=get_tools(),
            tool_choice="auto",
        )

        message = response.choices[0].message
        messages.append(message.model_dump())

        if not message.tool_calls:
            answer = message.content or ""

            return {
                "answer": answer,
                "source": "system",
                "tool_calls": recorded_tool_calls,
            }

        for tool_call in message.tool_calls:
            tool_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments or "{}")

            try:
                result = run_tool(tool_name, arguments)
            except Exception as error:
                result = {"error": str(error)}

            recorded_tool_calls.append(
                {
                    "tool": tool_name,
                    "args": arguments,
                    "result": json.dumps(result, ensure_ascii=False),
                }
            )

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": tool_name,
                    "content": json.dumps(result, ensure_ascii=False),
                }
            )

    return {
        "answer": "The agent reached the maximum number of tool calls.",
        "source": "system",
        "tool_calls": recorded_tool_calls,
    }


def main() -> None:
    question = " ".join(sys.argv[1:]).strip()

    if not question:
        question = input("Enter your question: ").strip()

    result = ask_llm(question)

    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
