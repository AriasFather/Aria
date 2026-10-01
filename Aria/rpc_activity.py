"""Shared RPC catalog, parser, builder, and rotation helpers for Aria."""

import shlex
import time
from urllib.parse import urlparse


RPC_TYPE_GROUPS = {
    "music": ("spotify", "soundcloud", "listening"),
    "video": ("youtube", "watching", "crunchyroll"),
    "activity": ("playing", "streaming", "listening", "watching", "competing"),
    "platform": ("xbox", "playstation", "vrchat", "metaquest", "roblox", "vscode", "browser"),
    "custom": ("custom_status", "custom"),
}

RPC_TYPE_ALIASES = {
    "ps4": "playstation",
    "ps5": "playstation",
    "golive": "streaming",
    "watch": "watching",
    "game": "playing",
    "customstatus": "custom_status",
    "yt": "youtube",
}

RPC_ACTIVITY_TYPES = {
    "playing": 0,
    "streaming": 1,
    "listening": 2,
    "watching": 3,
    "competing": 5,
}

RPC_APP_IDS = {
    "spotify": "3201606009684",
    "youtube": "111299001912",
    "soundcloud": "451016423729692673",
    "xbox": "622174530214821906",
    "playstation": "1470539864909943067",
    "crunchyroll": "981509069309354054",
    "vrchat": "1498387526501535835",
    "metaquest": "1418873561485504553",
    "roblox": "366959252047237121",
    "vscode": "383226320970055681",
    "browser": "485951488964247552",
    "generic": "367827983903490050",
    "listening": "534203414247112723",
    "streaming": "111299001912",
}

RPC_TYPES = (
    "custom_status", "playing", "watching", "listening", "streaming",
    "competing", "spotify", "youtube", "soundcloud", "xbox", "playstation",
    "crunchyroll", "vrchat", "metaquest", "roblox", "vscode", "browser",
    "custom", "clear",
)

ROTATABLE_FIELDS = (
    "text", "state", "details", "name", "song", "artist", "album",
    "track", "title", "context", "channel", "video_title", "channel_name",
    "anime_title", "episode_title", "game_name", "large_text", "small_text",
    "image_url", "imglink", "small_image_url", "small_imglink",
)

_PROVIDER_CONFIG = {
    "spotify": {"type": 2, "name": "Spotify", "app": "spotify"},
    "youtube": {"type": 3, "name": "YouTube", "app": "youtube"},
    "soundcloud": {"type": 2, "name": "SoundCloud", "app": "soundcloud", "asset": "soundcloud"},
    "xbox": {"type": 0, "name": "Game", "app": "xbox", "platform": "xbox"},
    "playstation": {"type": 0, "name": "Game", "app": "playstation", "platform": "ps5"},
    "crunchyroll": {"type": 3, "name": "Crunchyroll", "app": "crunchyroll"},
    "vrchat": {"type": 0, "name": "VRChat", "app": "vrchat", "platform": "meta_quest"},
    "metaquest": {"type": 0, "name": "Meta Quest", "app": "metaquest", "platform": "meta_quest"},
    "roblox": {"type": 0, "name": "Roblox", "app": "roblox", "asset": "roblox"},
    "vscode": {"type": 0, "name": "Visual Studio Code", "app": "vscode", "asset": "code"},
    "browser": {"type": 0, "name": "Browser", "app": "browser", "asset": "browser"},
}


def parse_rpc_key_values(text):
    values = {}
    try:
        tokens = shlex.split(str(text or ""))
    except ValueError:
        tokens = str(text or "").split()
    for token in tokens:
        if "=" not in token:
            continue
        key, value = token.split("=", 1)
        key = key.strip().lower()
        value = value.strip()
        if key in {"buttons", "button_urls"}:
            values.setdefault(key, []).extend(part.strip() for part in value.split(",") if part.strip())
        elif key:
            values[key] = value
    return values


def split_rotatable_activity(values, fields=ROTATABLE_FIELDS):
    """Expand comma-separated values into cyclic activity variants."""
    values = dict(values or {})
    split_values = {
        field: [part.strip() for part in str(values[field]).split(",")]
        for field in fields
        if values.get(field) and "," in str(values[field])
    }
    if not split_values:
        return [values]
    count = max(len(parts) for parts in split_values.values())
    variants = []
    for index in range(count):
        variant = dict(values)
        for field, parts in split_values.items():
            variant[field] = parts[index % len(parts)]
        variants.append(variant)
    return variants


def _stream_url(value):
    url = str(value or "https://twitch.tv/discord").strip()
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    allowed = {
        "twitch.tv", "www.twitch.tv", "twitch.com", "www.twitch.com",
        "youtube.com", "www.youtube.com", "youtu.be",
    }
    if parsed.scheme not in {"http", "https"} or host not in allowed:
        raise ValueError("stream_url must be a Twitch or YouTube URL")
    return url


def build_rpc_activity(rpc_type, values, resolve_asset=None, now_ms=None, provider_configs=None):
    """Build one Discord activity from a Beyond-style RPC command dictionary."""
    rpc_type = str(rpc_type or "").lower()
    rpc_type = RPC_TYPE_ALIASES.get(rpc_type, rpc_type)
    values = dict(values) if isinstance(values, dict) else {}
    if rpc_type == "clear":
        return None

    if rpc_type == "custom_status":
        text = str(values.get("text") or values.get("state") or "").strip()
        if not text and str(values.get("invisible", "")).lower() not in {"true", "1", "yes"}:
            raise ValueError("custom_status requires text=<status>")
        activity = {
            "type": 4,
            "name": "Custom Status",
            "state": "\u200e" if str(values.get("invisible", "")).lower() in {"true", "1", "yes"} else text[:128],
        }
        emoji = str(values.get("emoji") or "").strip()
        if emoji:
            activity["emoji"] = {"name": emoji[:32], "id": None, "animated": False}
        return activity

    provider = _PROVIDER_CONFIG.get(rpc_type)
    if provider is None and isinstance(provider_configs, dict):
        config = provider_configs.get(rpc_type)
        if isinstance(config, dict):
            provider = {
                "type": int(config.get("type", 0)),
                "name": str(config.get("name") or rpc_type.title()),
                "app": rpc_type,
                "application_id": str(config.get("application_id") or ""),
                "asset": config.get("asset"),
                "default_button": config.get("default_button"),
                "default_url": config.get("default_url"),
            }
    if rpc_type == "custom":
        try:
            activity_type = int(values.get("activity_type", 0))
        except (TypeError, ValueError) as exc:
            raise ValueError("activity_type must be 0, 1, 2, 3, or 5") from exc
        app_key = "generic"
        name = str(values.get("name") or "Activity").strip()
    elif provider:
        activity_type = provider["type"]
        app_key = provider["app"]
        name = str(values.get("name") or values.get("game_name") or provider["name"]).strip()
    else:
        activity_type = RPC_ACTIVITY_TYPES.get(rpc_type)
        app_key = rpc_type if rpc_type in RPC_APP_IDS else "generic"
        name = str(values.get("name") or "Activity").strip()

    if activity_type not in {0, 1, 2, 3, 5}:
        raise ValueError(f"Unsupported RPC type: {rpc_type}")
    if not name:
        raise ValueError("name is required")

    app_id = str(
        values.get("app_id")
        or (provider or {}).get("application_id")
        or RPC_APP_IDS.get(app_key, RPC_APP_IDS["generic"])
    ).strip()
    if not app_id.isdigit():
        raise ValueError("app_id must contain only digits")
    activity = {"type": activity_type, "name": name[:128], "application_id": app_id}

    details = values.get("details") or values.get("video_title") or values.get("episode_title")
    if rpc_type in {"spotify", "soundcloud"}:
        details = details or values.get("song") or values.get("track") or values.get("title")
    if rpc_type == "youtube":
        details = details or values.get("title")
    if rpc_type == "crunchyroll":
        details = details or values.get("episode_title") or values.get("anime_title") or values.get("title")
    state = values.get("state") or values.get("channel_name") or values.get("channel")
    if rpc_type == "spotify":
        state = state or values.get("artist")
    if rpc_type == "youtube":
        state = state or values.get("channel")
    if rpc_type == "crunchyroll":
        state = state or values.get("anime_title") or values.get("series")
    if details:
        activity["details"] = str(details)[:128]
    if state:
        activity["state"] = str(state)[:128]

    platform = values.get("platform") or (provider or {}).get("platform")
    if platform:
        activity["platform"] = str(platform)[:32]
    if rpc_type == "vrchat":
        activity["session_id"] = str(values.get("session_id") or format(int(time.time() * 1000), "x"))
        activity["content_classification"] = {"loaded": True, "data": None}
        activity.setdefault("state", "")
    if rpc_type == "xbox":
        activity["platform"] = "xbox"
    if provider and provider.get("platform"):
        activity["platform"] = str(values.get("platform") or provider["platform"])

    timestamp_now = int(now_ms if now_ms is not None else time.time() * 1000)
    try:
        elapsed = max(0.0, float(values.get("elapsed_minutes") or 0))
        total_raw = values.get("total_minutes")
        default_total = 3.5 if rpc_type == "spotify" else 10 if rpc_type == "youtube" else 24 if rpc_type == "crunchyroll" else None
        total = float(total_raw) if total_raw not in (None, "") else default_total
    except (TypeError, ValueError) as exc:
        raise ValueError("elapsed_minutes and total_minutes must be numbers") from exc
    start_ms = timestamp_now - int(elapsed * 60000)
    if total is not None:
        if total <= 0:
            raise ValueError("total_minutes must be greater than zero")
        activity["timestamps"] = {"start": start_ms, "end": start_ms + int(total * 60000)}
    else:
        activity["timestamps"] = {"start": timestamp_now}

    if rpc_type == "spotify":
        track_id = "0VjIjW4GlUZAMYd2vXMi3b"
        activity.update({
            "sync_id": track_id,
            "session_id": str(values.get("session_id") or f"spotify:{track_id}"),
            "party": {"id": f"spotify:{track_id}", "size": [1, 1]},
            "secrets": {"join": track_id, "spectate": track_id, "match": track_id},
            "instance": True,
            "flags": 48,
            "metadata": {
                "context_uri": f"spotify:album:{values.get('album_id', '4yP0hdKOZPNshxUOjY0cZj')}",
                "album_id": str(values.get("album_id") or "4yP0hdKOZPNshxUOjY0cZj"),
                "artist_ids": [str(values.get("artist_id") or "1Xyo4u8uXC1ZmMpatF05PJ")],
                "track_id": track_id,
            },
        })

    if rpc_type == "soundcloud":
        activity["name"] = "SoundCloud"
        activity["details"] = str(values.get("track") or details or name)[:128]
        if values.get("artist") or state:
            activity["state"] = str(values.get("artist") or state)[:128]

    if activity_type == 1:
        activity["url"] = _stream_url(values.get("stream_url") or values.get("url"))

    assets = {}
    image_fields = (
        ("large_image", "imglink", "image_url", "image", "large_text"),
        ("small_image", "small_imglink", "small_image_url", "small_image", "small_text"),
    )
    for target, *sources in image_fields:
        label_field = sources.pop()
        raw = next((values.get(source) for source in sources if values.get(source)), "")
        raw = str(raw or "").strip()
        if not raw and target == "large_image":
            raw = str((provider or {}).get("asset") or "").strip()
        if raw and resolve_asset and raw.startswith(("http://", "https://", "mp:", "attachments/")):
            try:
                raw = resolve_asset(raw, app_id)
            except TypeError:
                raw = resolve_asset(raw)
        if not raw and target == "large_image":
            raw = str((provider or {}).get("asset") or "").strip()
        if raw:
            assets[target] = raw
        default_label = name if target == "large_image" and rpc_type == "vrchat" else ""
        label = str(values.get(label_field) or default_label).strip()
        if raw and label:
            assets[label_field] = label[:128]
    if assets:
        activity["assets"] = assets

    buttons = values.get("buttons") or []
    button_urls = values.get("button_urls") or []
    if isinstance(buttons, str):
        buttons = [part.strip() for part in buttons.split(",") if part.strip()]
    if isinstance(button_urls, str):
        button_urls = [part.strip() for part in button_urls.split(",") if part.strip()]
    normalized_buttons = []
    normalized_urls = []
    for button in buttons:
        if isinstance(button, dict):
            normalized_buttons.append(str(button.get("label") or "Link").strip())
            normalized_urls.append(str(button.get("url") or "").strip())
        else:
            normalized_buttons.append(str(button).strip())
    if not button_urls:
        button_urls = normalized_urls
    pairs = [(label, url) for label, url in zip(normalized_buttons, button_urls) if label and url][:2]
    if pairs:
        activity["buttons"] = [label[:32] for label, _ in pairs]
        activity.setdefault("metadata", {})["button_urls"] = [url for _, url in pairs]
    elif provider and provider.get("default_button") and provider.get("default_url"):
        activity["buttons"] = [str(provider["default_button"])[:32]]
        activity.setdefault("metadata", {})["button_urls"] = [str(provider["default_url"])]

    party_current = values.get("party_cur") or values.get("party_current")
    party_max = values.get("party_max")
    if party_current not in (None, "") and party_max not in (None, ""):
        try:
            current_size, max_size = int(party_current), int(party_max)
        except (TypeError, ValueError) as exc:
            raise ValueError("party_cur and party_max must be integers") from exc
        if current_size < 0 or max_size < 1 or current_size > max_size:
            raise ValueError("party_cur and party_max must describe a valid party size")
        activity["party"] = {"id": f"{rpc_type}-party", "size": [current_size, max_size]}

    if str(values.get("spoof", "")).lower() in {"true", "1", "yes"} and activity_type != 1:
        activity["type"] = 1
        activity["url"] = _stream_url(values.get("stream_url") or "https://twitch.tv/discord")
    return activity