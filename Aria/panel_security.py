"""Security helpers for the Aria web panel."""

import os
import secrets
from typing import Union


def load_panel_secret_key(base_dir: str) -> Union[str, bytes]:
    configured_secret = os.environ.get("ARIA_WEBPANEL_SECRET")
    if configured_secret:
        return configured_secret

    secret_path = os.path.join(base_dir, ".aria_webpanel_secret")

    def read_key() -> bytes:
        with open(secret_path, "rb") as secret_file:
            secret_key = secret_file.read()
        if len(secret_key) < 32:
            raise RuntimeError(f"Dashboard session key is invalid: {secret_path}")
        return secret_key

    try:
        return read_key()
    except FileNotFoundError:
        pass

    secret_key = secrets.token_bytes(32)
    try:
        descriptor = os.open(secret_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return read_key()

    with os.fdopen(descriptor, "wb") as secret_file:
        secret_file.write(secret_key)
    return secret_key