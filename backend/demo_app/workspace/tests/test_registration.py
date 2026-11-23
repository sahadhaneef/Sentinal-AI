"""Demo app test fixture ? reproduction and regression verification."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_registration_null_profile():
    """REPRODUCTION FIXTURE: verifies that null profile is safely handled."""
    from src.registration import registration_handler

    result = registration_handler({"profile": None})
    assert "error" not in result, f"Registration failed with error: {result.get('error')}"
    assert result.get("status") == "created", f"Expected status=created, got {result}"
    assert result.get("name") == "Guest", f"Expected default name=Guest, got {result.get('name')}"


def test_existing_profile_smoke():
    """Smoke test: ensure valid registration still works."""
    from src.registration import registration_handler

    result = registration_handler({"profile": {"name": "Alice"}})
    assert "error" not in result, f"Valid registration failed: {result.get('error')}"
    assert result.get("name") == "Alice", f"Expected name=Alice, got {result}"


if __name__ == "__main__":
    test_registration_null_profile()
    test_existing_profile_smoke()
    print("All demo tests passed.")
