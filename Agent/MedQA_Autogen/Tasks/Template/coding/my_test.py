def run_tests(candidate):
    answer = candidate.strip().upper()

    # Correct answer injected during task generation
    assert answer == "__ANSWER__", f"Expected: __ANSWER__, Got: {answer}"
