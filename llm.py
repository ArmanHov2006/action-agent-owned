import json
import os

import requests

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "httpGet",
            "description": "Fetch contents of a URL over HTTP GET.",
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string"}},
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "finish",
            "description": "Call this once the task is fully complete.",
            "parameters": {
                "type": "object",
                "properties": {"summary": {"type": "string"}},
                "required": ["summary"],
            },
        },
    },
]


def ask(messages):
    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}",
        },
        json={
            "model": "gpt-4o-mini",
            "messages": messages,
            "tools": TOOLS,
        },
    )
    data = response.json()
    print(json.dumps(data))
    if response.status_code != 200 or "error" in data:
        raise RuntimeError(f"LLM API error: {data.get('error', data)}")
    return data["choices"][0]["message"]
