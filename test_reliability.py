import json
import judge


# Runs built to CLEAR provenance + the numeric gate, so the decision lands on
# layer 2 (the LLM). If a run died at provenance/gate, A and B would agree for
# free with no model running — that agreement measures nothing. These reach the
# mock, so the metric measures real judge-vs-judge behavior.
RUN_REACHES_LLM = {
    "goal": ">=200 reviews and >=4.5 stars",
    "collected": [
        {"review_count": 250, "rating": 4.7, "source_url": "amazon.ca/dp/PRODUCT"},
    ],
    "collected_raw": "250 reviews\n4.7 out of 5 stars",
    "page_url": "amazon.ca/dp/PRODUCT",
}
DATASET = [{"run": RUN_REACHES_LLM}]


def test_disagreement_is_recorded(monkeypatch):
    # Mock the one network seam (judge_runs), not requests. Return a JSON string
    # like the real call, and branch on model to FORCE a split: default passes,
    # model_b fails. Two real OpenAI models won't reliably disagree on a clean
    # case, so scripting it here is the only deterministic way to test the path.
    def fake_judge_runs(system_prompt, user_prompt, model="gpt-4o-mini"):
        if model == "gpt-4o-mini":
            return json.dumps({"pass": True, "reason": "identity ok"})
        return json.dumps({"pass": False, "reason": "wrong product"})

    monkeypatch.setattr(judge, "judge_runs", fake_judge_runs)

    result = judge.judge_reliability(DATASET, model_b="gpt-4o")

    assert result["agreement_rate"] == 0.0
    assert len(result["disagreements"]) == 1
    d = result["disagreements"][0]
    # The receipt: run + both full verdicts (reason kept, not just the bool).
    assert d["run"] is RUN_REACHES_LLM
    assert d["a"]["pass"] is True and d["a"]["reason"] == "identity ok"
    assert d["b"]["pass"] is False and d["b"]["reason"] == "wrong product"


def test_agreement_leaves_no_receipt(monkeypatch):
    # Both models return the same verdict -> agreement, empty disagreements.
    def fake_judge_runs(system_prompt, user_prompt, model="gpt-4o-mini"):
        return json.dumps({"pass": True, "reason": "identity ok"})

    monkeypatch.setattr(judge, "judge_runs", fake_judge_runs)

    result = judge.judge_reliability(DATASET, model_b="gpt-4o")

    assert result["agreement_rate"] == 1.0
    assert result["disagreements"] == []


def test_report_renders_disagreement_reasons(monkeypatch):
    def fake_judge_runs(system_prompt, user_prompt, model="gpt-4o-mini"):
        if model == "gpt-4o-mini":
            return json.dumps({"pass": True, "reason": "identity ok"})
        return json.dumps({"pass": False, "reason": "wrong product"})

    monkeypatch.setattr(judge, "judge_runs", fake_judge_runs)

    result = judge.judge_reliability(DATASET, model_b="gpt-4o")
    report = judge.reliability_report(result, model_a="gpt-4o-mini", model_b="gpt-4o")

    assert "Agreement rate: 0%" in report
    assert "wrong product" in report     # B's reason survives into the writeup
    assert "identity ok" in report       # A's reason too
    assert "gpt-4o" in report


def test_empty_dataset_does_not_divide_by_zero():
    result = judge.judge_reliability([], model_b="gpt-4o")
    assert result["agreement_rate"] == 0.0
    assert result["disagreements"] == []
