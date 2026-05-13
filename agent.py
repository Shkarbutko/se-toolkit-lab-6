import json
import os
import sys
from pathlib import Path
from typing import Any

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


def run_tool(name: str, arguments: dict[str, Any]) -> Any:
    if name == "list_files":
        return list_files()

    if name == "read_file":
        return read_file(arguments["path"])

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
                "You are a documentation agent. "
                "Use the available tools to inspect wiki documentation before answering. "
                "Return a concise answer based on the documentation."
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
                "source": "wiki",
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
                    "name": tool_name,
                    "arguments": arguments,
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
        "source": "wiki",
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
