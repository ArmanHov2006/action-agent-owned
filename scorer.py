import sys
from judge import full_judge
def scorer_run(dataset, baseline):
    correct = 0
    for item in dataset:
        if full_judge(item["run"])["pass"] == item["expected"]:
            correct += 1
    if correct < baseline:
        sys.exit(1)
    return correct
