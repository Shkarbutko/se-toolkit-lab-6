import json
import os
import sys

from openai import OpenAI


def get_env(name: str, fallback: str | None = None) -> str:
    value = os.environ.get(name)

    if value is None and fallback is not None:
        value = os.environ.get(fallback)

    if not value:
        raise RuntimeError(f"Missing environment variable: {name}")

    return value


def ask_llm(question: str) -> str:
    api_key = get_env("LLM_API_KEY")
    base_url = get_env("LLM_API_BASE_URL", "LLM_API_BASE")
    model = get_env("LLM_API_MODEL", "LLM_MODEL")

    client = OpenAI(
        api_key=api_key,
        base_url=base_url,
    )

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": question,
            }
        ],
    )

    return response.choices[0].message.content or ""


def main() -> None:
    question = " ".join(sys.argv[1:]).strip()

    if not question:
        question = input("Enter your question: ").strip()

    answer = ask_llm(question)

    result = {
        "answer": answer
    }

    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
