from judge import provenance_filter


def test_substring_number_does_not_ground():
    # "50" is NOT on the page — only "150" is. A hallucinated review_count of 50
    # must not ground itself against the "50" living inside "150".
    run = {
        "goal": ">=200 reviews and >=4.5 stars",
        "collected": [
            {"review_count": 50, "rating": 4.6, "source_url": "amazon.ca/dp/FAKE"},
        ],
        "collected_raw": "150 global ratings\n4.6 out of 5 stars",
    }
    result = provenance_filter(run)
    assert result["pass"] is False, f"expected row dropped as hallucinated, got {result}"


if __name__ == "__main__":
    test_substring_number_does_not_ground()
    print("test_substring_number_does_not_ground: PASS")
