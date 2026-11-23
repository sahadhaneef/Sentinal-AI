"""Demo application ? Registration API sample.

This is the ONLY application that SENTINEL AI is allowed to patch.
It contains a deliberately introduced NullReferenceError for the demo.
"""


def register_user(payload: dict) -> dict:
    """Register a user. BUG: does not guard against missing profile."""
    # BUG: This line will raise KeyError/AttributeError when profile is None
    name = payload["profile"]["name"]
    return create_user(name)


def create_user(name: str) -> dict:
    return {"status": "created", "name": name}


def registration_handler(request_body: dict) -> dict:
    """HTTP handler for registration endpoint."""
    try:
        return register_user(request_body)
    except (KeyError, TypeError, AttributeError) as e:
        return {"error": f"Registration failed: {e}"}


if __name__ == "__main__":
    # Reproduce the bug
    print("Test 1 ? missing profile (will fail):")
    result = registration_handler({"user_id": "u001"})  # No profile key
    print(result)

    print("Test 2 ? null profile (will fail):")
    result2 = registration_handler({"profile": None})
    print(result2)

    print("Test 3 ? valid profile (will pass):")
    result3 = registration_handler({"profile": {"name": "Alice"}})
    print(result3)
