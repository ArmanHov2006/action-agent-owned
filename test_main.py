from main import collected_raw_from


def test_collected_raw_is_tool_only():
    messages = [
        {"role": "system", "content": "You are an agent."},
        {"role": "user", "content": "How many reviews does it have?"},
        # Model CLAIM — invented number. Must NOT reach collected_raw.
        {"role": "assistant", "content": "It has 50 reviews and 4.9 stars."},
        # Real fetched bytes. Must reach collected_raw.
        {"role": "tool", "tool_call_id": "c1", "content": "18.2K global ratings\n4.6 out of 5 stars"},
    ]
    raw = collected_raw_from(messages)

    assert "18.2K" in raw, "tool content must be included"
    assert "4.6" in raw, "tool content must be included"
    assert "50 reviews" not in raw, "assistant claim must be excluded"
    assert "4.9" not in raw, "assistant claim must be excluded"
    print("test_collected_raw_is_tool_only: PASS")


if __name__ == "__main__":
    test_collected_raw_is_tool_only()
