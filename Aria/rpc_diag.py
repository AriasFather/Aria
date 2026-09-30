"""Check local dependencies and interfaces used by Aria RPC image uploads."""

import sys


def main() -> int:
    print("=" * 56)
    print(" Aria RPC image-upload diagnostic")
    print("=" * 56)
    print("python:", sys.executable)
    print("modifyself: not used by this project's RPC image uploader")

    ok = True
    try:
        import header_spoofer
        from api_client import DiscordAPIClient
    except Exception as exc:
        print("Aria RPC imports FAILED:", repr(exc))
        return 1

    session_class = getattr(header_spoofer, "Session", None)
    if session_class is None:
        ok = False
        print("HTTP session:       MISSING")
    else:
        session_module = getattr(session_class, "__module__", "unknown")
        print(f"HTTP session:       OK ({session_module})")
        for method in ("get", "post"):
            available = callable(getattr(session_class, method, None))
            print(f"session.{method:15s}: {'OK' if available else 'MISSING'}")
            ok = ok and available

    spoofer_class = getattr(header_spoofer, "HeaderSpoofer", None)
    profile_class = getattr(header_spoofer, "BrowserProfile", None)
    checks = {
        "HeaderSpoofer class": spoofer_class is not None,
        "get_protected_headers": callable(getattr(spoofer_class, "get_protected_headers", None)),
        "_create_session": callable(getattr(spoofer_class, "_create_session", None)),
        "BrowserProfile class": profile_class is not None,
    }

    profile = None
    if profile_class is not None:
        try:
            profile = profile_class()
        except Exception as exc:
            print("BrowserProfile init: MISSING ->", repr(exc))
            ok = False

    if profile is not None:
        for attr in ("user_agent", "browser_version", "locale", "os", "browser"):
            checks[f"profile.{attr}"] = hasattr(profile, attr)

    for name, available in checks.items():
        print(f"{name:24s}: {'OK' if available else 'MISSING'}")
        ok = ok and available

    api_checks = {
        "DiscordAPIClient.request": callable(getattr(DiscordAPIClient, "request", None)),
        "DiscordAPIClient.create_dm": callable(getattr(DiscordAPIClient, "create_dm", None)),
        "DiscordAPIClient.get_user_info": callable(getattr(DiscordAPIClient, "get_user_info", None)),
    }
    for name, available in api_checks.items():
        print(f"{name:24s}: {'OK' if available else 'MISSING'}")
        ok = ok and available

    print("-" * 56)
    if ok:
        print("RESULT: local RPC image-upload dependencies and interfaces are available.")
        print("This does not test Discord authentication, external asset permissions, or network access.")
        return 0

    print("RESULT: one or more local RPC image-upload dependencies or interfaces are missing.")
    print("Install the project's requirements, then run this diagnostic again.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
