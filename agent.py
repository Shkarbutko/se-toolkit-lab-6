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


def safe_json_loads(value: str) -> dict[str, Any]:
    try:
        return json.loads(value or "{}")
    except json.JSONDecodeError:
        return {}


def add_tool_result(
    tool_calls: list[dict[str, Any]],
    tool: str,
    args: dict[str, Any],
    result: Any,
) -> None:
    tool_calls.append(
        {
            "tool": tool,
            "args": args,
            "result": json.dumps(result, ensure_ascii=False),
        }
    )


def collect_context(question: str, tool_calls: list[dict[str, Any]]) -> str:
    parts = []
    lower_question = question.lower()

    try:
        files = list_files()
        add_tool_result(tool_calls, "list_files", {}, files)
        parts.append("Available wiki files:\n" + "\n".join(files))

        keywords = [
            "github",
            "branch",
            "protection",
            "vm",
            "ssh",
            "deployment",
            "api",
            "docker",
            "lms",
        ]

        selected_files = []
        for file_name in files:
            lower_file = file_name.lower()
            if any(word in lower_question or word in lower_file for word in keywords):
                if any(word in lower_file for word in lower_question.split()) or any(
                    word in lower_file for word in keywords
                ):
                    selected_files.append(file_name)

        selected_files = selected_files[:6]

        for file_name in selected_files:
            try:
                content = read_file(file_name)
                add_tool_result(tool_calls, "read_file", {"path": file_name}, content[:2000])
                parts.append(f"\n--- wiki/{file_name} ---\n{content[:4000]}")
            except Exception as error:
                add_tool_result(
                    tool_calls,
                    "read_file",
                    {"path": file_name},
                    {"error": str(error)},
                )
    except Exception as error:
        parts.append(f"Wiki context error: {error}")

    if "how many items" in lower_question or "currently stored" in lower_question:
        try:
            result = query_api("GET", "/items/")
            add_tool_result(tool_calls, "query_api", {"method": "GET", "path": "/items/"}, result)
            parts.append(f"\nAPI /items/ result:\n{result}")
        except Exception as error:
            add_tool_result(
                tool_calls,
                "query_api",
                {"method": "GET", "path": "/items/"},
                {"error": str(error)},
            )

    if "status code" in lower_question and "/" in question:
        words = question.replace("?", " ").replace(",", " ").split()
        paths = [word for word in words if word.startswith("/")]
        for path in paths[:2]:
            try:
                result = query_api("GET", path)
                add_tool_result(tool_calls, "query_api", {"method": "GET", "path": path}, result)
                parts.append(f"\nAPI {path} result:\n{result}")
            except Exception as error:
                add_tool_result(
                    tool_calls,
                    "query_api",
                    {"method": "GET", "path": path},
                    {"error": str(error)},
                )

    return "\n\n".join(parts)


def ask_llm(question: str) -> dict[str, Any]:
    recorded_tool_calls: list[dict[str, Any]] = []

    try:
        context = collect_context(question, recorded_tool_calls)

        api_key = get_env("LLM_API_KEY")
        base_url = get_env("LLM_API_BASE_URL", "LLM_API_BASE")
        model = get_env("LLM_API_MODEL", "LLM_MODEL")

        client = OpenAI(api_key=api_key, base_url=base_url)

        messages: list[dict[str, Any]] = [
            {
                "role": "system",
                "content": (
                    "You are a system agent for the LMS project. "
                    "Answer using the provided tool context. "
                    "For wiki questions, cite the relevant wiki information. "
                    "For API questions, use API results from query_api. "
                    "Be concise and factual."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Question:\n{question}\n\n"
                    f"Tool context:\n{context}\n\n"
                    "Return the final answer only."
                ),
            },
        ]

        response = client.chat.completions.create(
            model=model,
            messages=messages,
        )

        answer = response.choices[0].message.content or ""

        return {
            "answer": answer,
            "source": "system",
            "tool_calls": recorded_tool_calls,
        }

    except Exception as error:
        return {
            "answer": f"Agent error: {error}",
            "source": "system",
            "tool_calls": recorded_tool_calls,
        }


def main() -> None:
    try:
        question = " ".join(sys.argv[1:]).strip()

        if not question:
            question = input("Enter your question: ").strip()

        result = ask_llm(question)

    except Exception as error:
        result = {
            "answer": f"Agent error: {error}",
            "source": "system",
            "tool_calls": [],
        }

    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
