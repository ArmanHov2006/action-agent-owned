import re

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
