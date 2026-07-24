import os
import re
import math
import json
import requests
from dotenv import load_dotenv
import random

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

def judge_runs(system_prompt, user_prompt, model="gpt-4o-mini"):
    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}",
                },
                json={
                    "model": model,
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

def domain_of(url):
    if url.startswith("https://"):
        url = url[8:]
    if url.startswith("http://"):
        url = url[7:]
    url = url.split("/")[0]
    return url

def provenance_filter(run):
    if not run.get("collected"):
        return {"pass": False, "reason": "no rows collected"}

    page_url = run.get("page_url", "")
    raw = run.get("collected_raw", "")
    survivors = []
    for row in run["collected"]:
        values = [row[k] for k in ("review_count", "rating") if k in row]
        grounded = all(_grounded_in(value, raw) for value in values)
        if grounded and domain_of(row["source_url"]) == domain_of(page_url):
            survivors.append(row)
    if not survivors:
        return {"pass": False, "reason": "all rows hallucinated"}
    # No mutation: hand survivors back in the result dict. The caller builds a
    # fresh run from them, so run["collected"] here stays untouched.
    return {"pass": True, "reason": f"{len(survivors)} rows grounded in raw text",
            "survivors": survivors}

def full_judge(run, model="gpt-4o-mini"):
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
    raw = judge_runs(JUDGE_SYSTEM_PROMPT_R9, user_prompt, model=model)
    verdict = json.loads(raw)

    # Final: gate already passed here, so overall pass hinges on the LLM verdict.
    return {"pass": bool(verdict["pass"]), "reason": verdict["reason"]}


def judge_reliability(dataset, model_b):
    agree = 0
    disagreements = []
    pairs = []                              # 1. start an empty list, before the loop
    for item in dataset:
        run = item["run"]
        a = full_judge(run)
        b = full_judge(run, model=model_b)
        pairs.append((a["pass"], b["pass"]))    # 2. append the (A pass, B pass) tuple each loop
        if a["pass"] == b["pass"]:
            agree += 1
        else:
            disagreements.append({"run": run, "a": a, "b": b})
    total = len(dataset)
    rate = agree / total if total else 0.0
    m = [[0, 0], [0, 0]]
    for (av, bv) in pairs:
        m[0 if av else 1][0 if bv else 1] += 1
    kappa = cohen_kappa(m)  # 3. tally pairs → 2×2 (grammar above), then cohen_kappa(that)
    return {"agreement_rate": rate, "disagreements": disagreements, "kappa": kappa, "pairs": pairs}

def reliability_report(result, model_a="gpt-4o-mini", model_b=None):
    # Turn judge_reliability's output into a markdown failure-modes writeup.
    # The disagreements list IS the writeup; this just formats it.
    lines = []
    lines.append("# Judge reliability report")
    lines.append("")
    lines.append(f"- Judge A: `{model_a}`")
    if model_b:
        lines.append(f"- Judge B: `{model_b}`")
    lines.append(f"- Agreement rate: {result['agreement_rate']:.0%}")
    lines.append(f"- Disagreements: {len(result['disagreements'])}")
    lines.append("")
    if not result["disagreements"]:
        lines.append("No disagreements. Either the judges are aligned or the "
                     "dataset never reached layer 2.")
        return "\n".join(lines)
    lines.append("## Disagreements (where A and B split)")
    for i, d in enumerate(result["disagreements"], 1):
        goal = d["run"].get("goal", "(no goal)")
        lines.append("")
        lines.append(f"### {i}. {goal.strip()}")
        lines.append(f"- A ({model_a}): pass={d['a']['pass']} — {d['a']['reason']}")
        b_model = model_b or "model_b"
        lines.append(f"- B ({b_model}): pass={d['b']['pass']} — {d['b']['reason']}")
    return "\n".join(lines)


if __name__ == "__main__":
    run = {"goal": " >=200 reviews and >=4.5 stars",
       "page_url": "amazon.ca/dp/PRODUCT",
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

def cohen_kappa(confusion_matrix):
    total = sum(sum(row) for row in confusion_matrix)
    if total == 0:
        return 0.0
    p_o = sum(confusion_matrix[i][i] for i in range(len(confusion_matrix))) / total
    row_sums = [sum(row) for row in confusion_matrix]
    col_sums = [sum(confusion_matrix[i][j] for i in range(len(confusion_matrix))) for j in range(len(confusion_matrix[0]))]
    p_e = sum((row_sums[i] * col_sums[i]) for i in range(len(row_sums))) / (total ** 2)
    if p_e == 1:
        return float('nan')     # kappa undefined: one class only, no chance floor to correct
    return (p_o - p_e) / (1 - p_e)

def kappa_bootstrap_ci(pairs, n=10000, seed=None):

    if seed is not None:
        random.seed(seed)
    kappa_values = []
    for _ in range(n):
        sample = [random.choice(pairs) for _ in range(len(pairs))]
        m = [[0, 0], [0, 0]]
        for (av, bv) in sample:
            m[0 if av else 1][0 if bv else 1] += 1
        kappa_values.append(cohen_kappa(m))
    kappa_values = [k for k in kappa_values if not math.isnan(k)]  # drop nans (undefined-kappa samples)
    kappa_values.sort()
    if not kappa_values: raise ValueError("No valid kappa values to compute confidence interval.")
    index_lo = int(0.025 * len(kappa_values))
    index_hi = int(0.975 * len(kappa_values))
    return kappa_values[index_lo], kappa_values[index_hi]


if __name__ == "__main__":
    pairs = [(1,1),(1,0),(0,0),(1,1),(1,1),(0,0),(1,0),(0,0)]   # any real mix
    m = [[0, 0], [0, 0]]
    for (av, bv) in pairs:
        m[0 if av else 1][0 if bv else 1] += 1
    lo, hi = kappa_bootstrap_ci(pairs, seed=42)
    print(f"kappa = {cohen_kappa(m):.2f} [{lo:.2f}, {hi:.2f}]")
