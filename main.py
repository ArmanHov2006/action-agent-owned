import json

from dotenv import load_dotenv

from llm import ask
from tools import httpGet

load_dotenv()

MAX_STEPS = 20
TOOLS = {"httpGet": httpGet}


def loop(task):
    state = "in_progress"
    i = 0
    messages = [
        {
            "role": "system",
            "content": "You are an autonomous agent. Use tools as needed, then call finish when the task is complete.",
        },
        {"role": "user", "content": task},
    ]

    while i < MAX_STEPS and state != "done":
        response = ask(messages)
        messages.append(response)

        if response.get("tool_calls"):
            for call in response["tool_calls"]:
                args = json.loads(call["function"]["arguments"])
                if call["function"]["name"] == "finish":
                    state = "done"
                    print(f"Finished: {args.get('summary', '(none)')}")
                    break
                fn = TOOLS.get(call["function"]["name"])
                if not fn:
                    result = f"Unknown tool: {call['function']['name']}"
                elif not args.get("url"):
                    result = "Error: missing required argument 'url'"
                else:
                    result = fn(args["url"])
                messages.append({"role": "tool", "tool_call_id": call["id"], "content": str(result)})
        else:
            print(f"Response: {response['content']}")
        i += 1

    if state != "done":
        print("Max steps reached without completing the task.")
    else:
        print("Task completed successfully.")


if __name__ == "__main__":
    loop("Fetch api.github.com with httpGet, tell me the page title, then call finish.")
