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


def test_offsite_source_url_dropped():
    # Numbers ground fine (250, 4.7 are on the page) but source_url points at a
    # DIFFERENT site (walmart.ca) than the page actually fetched (amazon.ca).
    # Piece 6: fake provenance must be dropped even when the numbers check out.
    run = {
        "goal": ">=200 reviews and >=4.5 stars",
        "collected": [
            {"review_count": 250, "rating": 4.7, "source_url": "walmart.ca/blender"},
        ],
        "collected_raw": "250 reviews\n4.7 out of 5 stars",
        "page_url": "amazon.ca/dp/PRODUCT",
    }
    result = provenance_filter(run)
    assert result["pass"] is False, f"expected offsite row dropped, got {result}"


def test_same_domain_survives():
    # Same numbers, but source_url matches the fetched page's domain -> survives.
    # Proves piece 6 gates on domain only; it does not over-drop honest rows.
    run = {
        "goal": ">=200 reviews and >=4.5 stars",
        "collected": [
            {"review_count": 250, "rating": 4.7, "source_url": "amazon.ca/dp/PRODUCT"},
        ],
        "collected_raw": "250 reviews\n4.7 out of 5 stars",
        "page_url": "amazon.ca/dp/PRODUCT",
    }
    result = provenance_filter(run)
    assert result["pass"] is True, f"expected same-domain row to survive, got {result}"


def test_scheme_differs_same_host_survives():
    # source_url carries https://, page_url is bare. domain_of normalizes the
    # scheme away, so both resolve to amazon.ca -> same host -> survives.
    run = {
        "goal": ">=200 reviews and >=4.5 stars",
        "collected": [
            {"review_count": 250, "rating": 4.7, "source_url": "https://amazon.ca/dp/X"},
        ],
        "collected_raw": "250 reviews\n4.7 out of 5 stars",
        "page_url": "amazon.ca/dp/X",
    }
    result = provenance_filter(run)
    assert result["pass"] is True, f"expected scheme-only diff to survive, got {result}"


if __name__ == "__main__":
    test_substring_number_does_not_ground()
    test_offsite_source_url_dropped()
    test_same_domain_survives()
    test_scheme_differs_same_host_survives()
    print("all provenance tests: PASS")
