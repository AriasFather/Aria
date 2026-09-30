import base64
from urllib.parse import urlparse

import requests


MAX_AVATAR_BYTES = 10 * 1024 * 1024

_IMAGE_SIGNATURES = (
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"GIF87a", "image/gif"),
    (b"GIF89a", "image/gif"),
)


def image_to_data_uri(image_bytes: bytes) -> str:
    """Validate a supported image and return a correctly typed data URI."""
    if not isinstance(image_bytes, bytes) or not image_bytes:
        raise ValueError("The downloaded file is empty")
    if len(image_bytes) > MAX_AVATAR_BYTES:
        raise ValueError("The image exceeds the 10 MiB avatar size limit")

    mime_type = None
    for signature, candidate_type in _IMAGE_SIGNATURES:
        if image_bytes.startswith(signature):
            mime_type = candidate_type
            break

    if mime_type is None and len(image_bytes) >= 12:
        if image_bytes[:4] == b"RIFF" and image_bytes[8:12] == b"WEBP":
            mime_type = "image/webp"

    if mime_type is None:
        raise ValueError("Unsupported image format; use PNG, JPEG, GIF, or WebP")

    encoded = base64.b64encode(image_bytes).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def download_avatar_data_uri(image_url: str) -> str:
    """Download an HTTPS image without using the authenticated Discord session."""
    parsed_url = urlparse(str(image_url or "").strip())
    if (
        parsed_url.scheme != "https"
        or not parsed_url.hostname
        or parsed_url.username
        or parsed_url.password
    ):
        raise ValueError("Provide a public HTTPS image URL")

    response = requests.get(
        parsed_url.geturl(),
        headers={"Accept": "image/png,image/jpeg,image/gif,image/webp"},
        timeout=15,
        stream=True,
        allow_redirects=False,
    )
    try:
        if response.status_code != 200:
            raise ValueError(f"Image download failed (HTTP {response.status_code})")

        try:
            content_length = int(response.headers.get("Content-Length") or 0)
        except (TypeError, ValueError):
            content_length = 0
        if content_length > MAX_AVATAR_BYTES:
            raise ValueError("Image exceeds the 10 MiB avatar size limit")

        chunks = []
        downloaded = 0
        for chunk in response.iter_content(chunk_size=64 * 1024):
            if not chunk:
                continue
            downloaded += len(chunk)
            if downloaded > MAX_AVATAR_BYTES:
                raise ValueError("Image exceeds the 10 MiB avatar size limit")
            chunks.append(chunk)

        return image_to_data_uri(b"".join(chunks))
    finally:
        response.close()