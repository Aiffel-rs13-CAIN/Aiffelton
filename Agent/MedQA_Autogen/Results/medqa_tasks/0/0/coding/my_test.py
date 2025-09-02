def run_tests(candidate):
    answer = candidate.strip().upper()

    # Correct answer injected during task generation
    assert answer == "C", f"Expected: C, Got: {answer}"
