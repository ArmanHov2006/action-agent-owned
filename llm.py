import json
import os
import time

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
        {"type": "function",
         "function": {
             "name": "askUser",
             "description": "Ask the user a question and get their input.",
             "parameters": {
                 "type": "object",
                 "properties": {"prompt": {"type": "string"}},
                 "required": ["prompt"],
             },
         }
    },
]


def ask(messages, max_retries=3):
    backoff = 1
    for attempt in range(max_retries + 1):
        try:
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
                timeout=30,
            )
        except requests.exceptions.RequestException as e:
            reason = f"request error: {e}"
        else:
            # Transient server-side failures (rate limit / 5xx): worth retrying.
            if response.status_code == 429 or response.status_code >= 500:
                reason = f"HTTP {response.status_code}"
            else:
                data = response.json()
                print(json.dumps(data))
                if response.status_code == 200 and "error" not in data:
                    return data["choices"][0]["message"]
                # Permanent failure (401 bad key, 400 bad request, ...): retry is pointless.
                raise RuntimeError(f"LLM API error: {data.get('error', data)}")

        # Only transient failures reach here.
        if attempt < max_retries:
            print(f"LLM transient failure ({reason}); retry {attempt + 1}/{max_retries} in {backoff}s")
            time.sleep(backoff)
            backoff *= 2
            continue
        raise RuntimeError(f"LLM call failed after {max_retries} retries ({reason})")
