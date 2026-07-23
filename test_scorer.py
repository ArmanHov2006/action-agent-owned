import pytest
import scorer
def test_scorer():
    # run1: hallucinated substring — collected 50 but only "150" is on the page,
    # so 50 does not ground. Expected dropped (False).
    run1 = {
        "goal": ">=200 reviews and >=4.5 stars",
        "collected": [
            {"review_count": 50, "rating": 4.6, "source_url": "amazon.ca/dp/FAKE"},
        ],
        "collected_raw": "150 global ratings\n4.6 out of 5 stars",
        "page_url": "amazon.ca/dp/FAKE",
    }


    # run3: numbers ground fine, but source_url is offsite (walmart) vs the page
    # actually fetched (amazon). Expected dropped (False).
    run3 = {
        "goal": ">=200 reviews and >=4.5 stars",
        "collected": [
            {"review_count": 250, "rating": 4.7, "source_url": "walmart.ca/blender"},
        ],
        "collected_raw": "250 reviews\n4.7 out of 5 stars",
        "page_url": "amazon.ca/dp/PRODUCT",
    }
    dataset = [
    {"run": run1, "expected": False},
    {"run": run3, "expected": False},
    ]
    with pytest.raises(SystemExit) as e:
        scorer.scorer_run(dataset, baseline=3)
    assert e.value.code != 0

