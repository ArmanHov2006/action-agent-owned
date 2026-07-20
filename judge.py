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

def extract_fields(data: list[dict]) -> list[dict]:
    # One candidate per row, index-aligned to data. No merge: each row is
    # judged whole so a strong row can't be clobbered by a weak later row.
    candidates = []
    for row in data:
        fields = {}
        review_count = row.get("review_count")
        rating = row.get("rating")
        if review_count is not None:
            fields["review_count"] = to_number(review_count)
        if rating is not None:
            fields["rating"] = to_number(rating)
        candidates.append(fields)
    return candidates

def meets_thresholds(fields: dict, thresholds: dict) -> bool:
    for key, threshold in thresholds.items():
        if key not in fields or fields[key] < threshold:
            return False
    return True

def judge(run):
    thresholds = parse_thresholds(run["goal"])
    if not thresholds:
        return {"correct": False, "reason": "no parseable thresholds in goal"}
    candidates = extract_fields(run["collected"])
    last_reason = "no rows collected"
    # Gate passes if ANY single row clears every threshold on its own.
    for i, fields in enumerate(candidates):
        reason = None
        for name, minval in thresholds.items():
            got = fields.get(name)
            if got is None:
                reason = f"no {name}"; break
            if got < minval:
                reason = f"{name} {got:g} < {minval:g}"; break
        if reason is None:
            return {"correct": True, "reason": "gate passed", "winner": i}
        last_reason = reason
    return {"correct": False, "reason": last_reason}

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

def _grounded_in(value, raw):
    # Plain "in" substring check lets "50" match inside "150". Require the
    # number not be flanked by more digits, so it can't hide inside a longer one.
    pattern = r"(?<!\d)" + re.escape(str(value)) + r"(?!\d)"
    return re.search(pattern, raw) is not None

def provenance_filter(run):
    if not run.get("collected"):
        return {"pass": False, "reason": "no rows collected"}

    raw = run.get("collected_raw", "")
    survivors = []
    for row in run["collected"]:
        values = [row[k] for k in ("review_count", "rating") if k in row]
        grounded = all(_grounded_in(value, raw) for value in values)
        if grounded:
            survivors.append(row)
    if not survivors:
        return {"pass": False, "reason": "all rows hallucinated"}
    # No mutation: hand survivors back in the result dict. The caller builds a
    # fresh run from them, so run["collected"] here stays untouched.
    return {"pass": True, "reason": f"{len(survivors)} rows grounded in raw text",
            "survivors": survivors}

def full_judge(run):
    prov = provenance_filter(run)
    if not prov["pass"]: return prov
    # Gate a clone carrying only the grounded rows — never mutate the caller's run.
    judged = {**run, "collected": prov["survivors"]}
    # Layer 1: deterministic numeric gate. If numbers fail, done — no LLM, no cost.
    gate = judge(judged)
    if not gate["correct"]:
        return {"pass": False, "reason": gate["reason"]}

    # Only the winning row's identity reaches layer 2 — the LLM judges the row
    # that actually cleared the gate, not the accessory that rode alongside it.
    # Strip numbers before they ever reach the LLM. Whitelist = default-deny:
    # only JUDGMENT_FIELDS survive, so review_count/rating cannot leak.
    winner = judged["collected"][gate["winner"]]
    stripped = {k: winner[k] for k in JUDGMENT_FIELDS if k in winner}
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
       "collected": [
           {"review_count": "18.2K", "rating": 4.6, "source_url": "amazon.ca/dp/PRODUCT"},
           {"review_count": 50, "rating": 4.9, "source_url": "amazon.ca/dp/ACCESSORY"},
       ],
       "collected_raw": (
           "ErgoDesk Pro Standing Desk Converter\n"
           "Visit the ErgoDesk Store\n"
           "4.6 out of 5 stars\n"
           "18.2K global ratings\n"
           "Price: $289.00  In stock, ships from and sold by ErgoDesk\n"
           "Height-adjustable riser, holds up to two monitors."
       )}
    # Case A — mixed run (PRODUCT grounded, ACCESSORY fake)
    result = provenance_filter(run)
    print(result)                                        # expect pass: True, "1 rows grounded"
    print([r["source_url"] for r in result["survivors"]])  # expect ONLY .../PRODUCT
    print([r["source_url"] for r in run["collected"]])      # unchanged: BOTH rows (no mutation)

    # Case B — all hallucinated (numbers absent from collected_raw)
    fake_run = {"goal": " >=200 reviews and >=4.5 stars",
       "collected": [
           {"review_count": 999, "rating": 3.1, "source_url": "amazon.ca/dp/PRODUCT"},
           {"review_count": "7.7K", "rating": 3.3, "source_url": "amazon.ca/dp/ACCESSORY"},
       ],
       "collected_raw": run["collected_raw"]}   # same page text; these numbers aren't in it
    print(provenance_filter(fake_run))                   # expect pass: False, "all rows hallucinated"
