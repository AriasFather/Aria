import json
import sys

import config


def configure_token(token: str, remember: bool, config_path: str = "config.json") -> None:
    if remember and not token:
        raise ValueError("Token is required when remembering it.")
    if remember and config._encrypter is None:
        raise RuntimeError("Token encryption is unavailable; install the cryptography dependency.")

    stored_token = token if remember else ""
    settings = config.Config(config_path)
    settings.set("token", stored_token)

    if remember:
        with open(settings.config_file, "r", encoding="utf-8") as handle:
            saved = json.load(handle).get("token", "")
        if not config._encrypter.is_encrypted(saved):
            raise RuntimeError("The token was not encrypted before saving.")


def main() -> None:
    action = sys.argv[1] if len(sys.argv) > 1 else ""
    if action not in {"save", "clear"}:
        raise ValueError("Expected a save or clear action.")
    token = sys.stdin.readline().rstrip("\r\n")
    configure_token(token, remember=action == "save")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"Token setup failed: {error}", file=sys.stderr)
        raise SystemExit(1)
