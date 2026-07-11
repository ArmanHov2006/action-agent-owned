import os
import re
import json
import requests
from dotenv import load_dotenv

JUDGMENT_FIELDS = {"source_url"}   # whitelist: only these keys reach the LLM

load_dotenv()

def parse_thresholds(goal):
    thr = {}                         # empty dict, fill as you find things

    m = re.search(r"(\d+) reviews", goal)
    if m:  thr["review_count"] = float(m.group(1))

    m = re.search(r"(\d+\.?\d*) stars", goal)
    if m:  thr["rating"] = float(m.group(1))

    return thr

def to_number(num):
    s = str(num).lower().replace(",", "").replace("$", "")
    if isinstance(num, (int, float)):
        return float(num)
    elif re.search(r"\d+k", s):
        return float(s.replace("k", "")) * 1000
    elif re.search(r"\d+m", s):
        return float(s.replace("m", "")) * 1000000
    elif re.search(r"\d+\.?\d*", s):
        return float(s)
    return None

def extract_fields(data: list[dict]) -> dict:
    fields = {}
    for review_count, rating in [(r.get("review_count"), r.get("rating")) for r in data]:
        if review_count is not None:
            fields["review_count"] = to_number(review_count)
        if rating is not None:
            fields["rating"] = to_number(rating)
    return fields

def meets_thresholds(fields: dict, thresholds: dict) -> bool:
    for key, threshold in thresholds.items():
        if key not in fields or fields[key] < threshold:
            return False
    return True

def judge(run):
    thresholds = parse_thresholds(run["goal"])
    fields = extract_fields(run["collected"])
    for name, minval in thresholds.items():
        got = fields.get(name)
        if got is None:   return {"correct": False, "reason": f"no {name}"}
        if got < minval:  return {"correct": False, "reason": f"{name} {got:g} < {minval:g}"}
    return {"correct": True, "reason": "gate passed"}

def judge_runs(system_prompt, user_prompt):
    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}",
                },
                json={
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                },
                timeout=30,
            )
    resp = response.json()
    return resp["choices"][0]["message"]["content"]

JUDGE_SYSTEM_PROMPT = (
    "You are a judge deciding whether a run met its goal.\n"
    "\n"
    "1. Read the goal and identify each numeric threshold it requires "
    "(for example: at least 100 reviews, rating of at least 4.0 stars).\n"
    "2. Read the numbers the run actually collected. For each threshold, "
    "compare the collected number against the required number. The run passes "
    "only if every collected number meets or exceeds its threshold.\n"
    "3. Return only JSON: {\"pass\": bool, \"reason\": str}. "
    "In reason, name each number, its threshold, and whether it passed. "
    "Output nothing outside the JSON."
)

JUDGE_SYSTEM_PROMPT_R9 = (
    "You are a judge deciding whether a run met its goal.\n"
    "\n"
    "The numeric thresholds have ALREADY been verified by Python code. "
    "Do NOT recheck, recompute, or compare any numbers. Assume every number "
    "already passes its threshold. Any arithmetic is not your job.\n"
    "\n"
    "Judge only two things:\n"
    "1. Identity: is the source page the real, correct product the goal is "
    "about? (e.g. does the source_url point to that exact product, not a "
    "different item, category page, or unrelated listing.)\n"
    "2. Relevance: does the collected data actually describe that product and "
    "match what the goal asked for? (right kind of data, not stale, not for a "
    "variant or a different region.)\n"
    "\n"
    "Return only JSON: {\"pass\": bool, \"reason\": str}. Here pass means the "
    "identity and relevance checks hold — not that the numbers hold. "
    "In reason, state the identity and relevance verdicts. "
    "Output nothing outside the JSON."
)

def full_judge(run):
    # Layer 1: deterministic numeric gate. If numbers fail, done — no LLM, no cost.
    gate = judge(run)
    if not gate["correct"]:
        return {"pass": False, "reason": gate["reason"]}

    # Strip numbers before they ever reach the LLM. Whitelist = default-deny:
    # only JUDGMENT_FIELDS survive, so review_count/rating cannot leak.
    stripped = [
        {k: row[k] for k in JUDGMENT_FIELDS if k in row}
        for row in run["collected"]
    ]
    # Goal text still holds the threshold numbers ("200 reviews"), on purpose.
    # Not a leak: the LLM has no collected numbers to compare them against, so it
    # can't recheck arithmetic. And relevance judging needs to know what was asked.
    user_prompt = f"Goal: {run['goal']}\nCollected data: {stripped}"

    # Layer 2: LLM judges identity + relevance only. Returns a JSON string.
    raw = judge_runs(JUDGE_SYSTEM_PROMPT_R9, user_prompt)
    verdict = json.loads(raw)

    # Final: gate already passed here, so overall pass hinges on the LLM verdict.
    return {"pass": bool(verdict["pass"]), "reason": verdict["reason"]}


if __name__ == "__main__":
    run = {"goal": " >=200 reviews and >=4.5 stars",
       "collected": [{"review_count": "18.2K", "rating": 4.6, "source_url": "amazon.ca/dp/X"}]}
    print(full_judge(run))
