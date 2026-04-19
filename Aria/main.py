import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

# Suppress SSL warnings for cleaner output
import warnings
warnings.filterwarnings('ignore', message='.*InsecureRequestWarning.*')

# Also disable urllib3 warnings specifically
try:
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except ImportError:
    pass

bot = None
web_panel = None

import importlib

import re
import threading
import time
import random
import json
from urllib.parse import quote as _url_quote

try:
    import aiohttp  # type: ignore[import-untyped]
except ImportError:
    aiohttp = None
import base64
import importlib
import formatter as fmt

try:
    from utils.general import is_valid_emoji
except ImportError:
    def is_valid_emoji(token):
        return False

web_panel = None

from bot import DiscordBot
from config import Config
from voice import SimpleVoice
from backup import BackupManager
from moderation import ModerationManager
from error_handler import error_guard
from host import host_manager
from afk_system import afk_system
from anti_gc_trap import AntiGCTrap
from GitHub import GitHubUpdater
from superreact import SuperReactClient, super_react_client
from history_manager import HistoryManager
from account_data_manager import AccountDataManager
from badge_scraper import BadgeScraper
from discord_api_types import ActivityType, RelationshipType
from format_bootstrap import install_global_formatter
from quest import QuestSystem
from developer import DeveloperTools
from command_integration import integrate_command_engine
import sys
import os

# Add the `/workspaces/Aria/Aria` directory to the Python module search path
sys.path.append(os.path.dirname(__file__))

import sys
import os

# Add the `/workspaces/Aria/Aria` directory to the Python module search path
sys.path.append(os.path.dirname(__file__))

from webpanel import WebPanel
try:
    from message_db import MessageDatabase
except ImportError:
    from Aria.message_db import MessageDatabase

if os.environ.get('HOSTED_TOKEN') == 'true':
    HOSTED_MODE = True
else:
    HOSTED_MODE = False

def protected_main():
    error_guard.safe_execute(main)

def delete_after_delay(api, channel_id, message_id, delay=None):
    def delete():
        resolved_delay = delay
        if resolved_delay is None:
            resolved_delay = getattr(api, "_default_delete_delay", 3.0)
        try:
            resolved_delay = max(0.03, float(resolved_delay or 0.0))
        except Exception:
            resolved_delay = 3.0
        time.sleep(resolved_delay)
        api.delete_message(channel_id, message_id)
    threading.Thread(target=delete, daemon=True).start()

def delete_command_message(api, channel_id, message_id):
    try:
        api.delete_message(channel_id, message_id)
    except:
        pass

# Spotify spoofing ID pools — varied so repeated calls look different
_SPOTIFY_TRACKS = [
    "0VjIjW4GlUZAMYd2vXMi3b", "4iJyoBOLtHqaWYs3vyWF1a", "1r9xUipOqoNwggBpENDsvJ",
    "7qiZfU4dY1lWllzX7mPBI3", "0tgVpDi06FyKpA1z0VMD4v", "2takcwOaAZWiXQijPHIx7B",
    "3n3Ppam7vgaVa1iaRUIOKE", "4cOdK2wGLETKBW3PvgPWqT", "1lNuQWb9O3GBK1UhFTMPnP",
]
_SPOTIFY_ALBUMS = [
    "4yP0hdKOZPNshxUOjY0cZj", "0ETFjACtuP2ADo6LFhL6HN", "5ms2BpQWqHnOkx8RQIQW0S",
    "3T4tUhGYeRNVUGevb0wThu", "1RM6MGv6bcl6NvOHSCxfti", "4Gfnly5CzMJQqkUFoAi9h0",
]
_SPOTIFY_ARTISTS = [
    "1Xyo4u8uXC1ZmMpatF05PJ", "3TVXtAsR1Inumwj472S9r4", "1uNFoZAHBGtllmzznpCI3i",
    "06HL4z0CvFAxyc27GXpf02", "4oUHIQIBe0LHzYfvXNW4QM", "3fMbdgg4jU18AjLCKBhRSm",
]

_CDN_RE = re.compile(
    r"https?://(?:cdn\.discordapp\.com|media\.discordapp\.net)/attachments/(\d+)/(\d+)/([^?#]+)"
)
_CT_EXT = {
    "image/jpeg": "jpg", "image/jpg": "jpg", "image/png": "png",
    "image/gif": "gif", "image/webp": "webp", "image/avif": "avif",
}
_RPC_ASSET_CACHE = {}


def _rpc_asset_cache_key(image_url, application_id=None):
    return f"{application_id or ''}::{str(image_url or '')}"


def _normalize_rpc_application_id(application_id):
    app_id = str(application_id or "").strip()
    return app_id if app_id.isdigit() else None


def _normalize_rpc_image_input(image_url):
    if image_url is None:
        return None
    value = str(image_url).strip()
    return value or None


def _rpc_feedback_channel_id(bot):
    return getattr(bot, "last_command_channel", None) or getattr(bot, "default_channel", None) or None


def _notify_rpc_issue(bot, message):
    channel_id = _rpc_feedback_channel_id(bot)
    if not channel_id:
        return
    try:
        bot.api.send_message(channel_id, message)
    except Exception:
        pass


def _get_cached_rpc_asset(image_url, application_id=None):
    cached = _RPC_ASSET_CACHE.get(_rpc_asset_cache_key(image_url, application_id))
    if not isinstance(cached, dict):
        return None
    asset_key = cached.get("asset_key")
    if isinstance(asset_key, str) and asset_key:
        return asset_key
    return None


def _store_cached_rpc_asset(image_url, asset_key, channel_id=None, message_id=None, application_id=None):
    if not image_url or not asset_key:
        return
    _RPC_ASSET_CACHE[_rpc_asset_cache_key(image_url, application_id)] = {
        "asset_key": str(asset_key),
        "channel_id": str(channel_id) if channel_id else None,
        "message_id": str(message_id) if message_id else None,
        "application_id": str(application_id) if application_id else None,
        "cached_at": time.time(),
    }


def register_external_rpc_asset(api, application_id, image_url):
    image_url = _normalize_rpc_image_input(image_url)
    application_id = _normalize_rpc_application_id(application_id)
    if not image_url or not application_id:
        return None
    cached_asset = _get_cached_rpc_asset(image_url, application_id)
    if cached_asset:
        return cached_asset

    try:
        response = api.request(
            "POST",
            f"/applications/{application_id}/external-assets",
            data={"urls": [image_url]},
        )
        if not response or response.status_code not in (200, 201):
            return None
        payload = response.json()
        if isinstance(payload, dict):
            payload = payload.get("external_assets") or payload.get("assets") or []
        if isinstance(payload, list) and payload:
            asset_path = payload[0].get("external_asset_path") or payload[0].get("asset_path")
            if asset_path:
                asset_key = f"mp:{asset_path}"
                _store_cached_rpc_asset(image_url, asset_key, application_id=application_id)
                return asset_key
    except Exception as e:
        print(f"[rpc asset] register error: {e}")
    return None

def upload_image_to_discord(api, image_url, application_id=None):
    """Upload an external image to Discord via DM and return an mp:attachments/ asset key."""
    try:
        image_url = _normalize_rpc_image_input(image_url)
        application_id = _normalize_rpc_application_id(application_id)
        if not image_url:
            return None
        cached_asset = _get_cached_rpc_asset(image_url, application_id)
        if cached_asset:
            return cached_asset

        response = api.session.get(image_url, timeout=15)
        if response.status_code != 200:
            return None

        image_bytes = response.content
        ct = response.headers.get("Content-Type", "").split(";")[0].strip()
        ct_ext = _CT_EXT.get(ct, "png")
        raw_name = image_url.split("/")[-1].split("?")[0]
        filename = raw_name if ("." in raw_name and len(raw_name) <= 50) else f"asset.{ct_ext}"

        if not getattr(api, "user_id", None):
            api.get_user_info(force=False)

        dm = api.create_dm(api.user_id)
        if not dm or "id" not in dm:
            return None

        files = {"file": (filename, image_bytes, ct or "application/octet-stream")}
        headers = api.header_spoofer.get_protected_headers(api.token)

        upload_response = api.session.post(
            f"https://discord.com/api/v9/channels/{dm['id']}/messages",
            headers=headers,
            files=files,
            timeout=20,
        )

        if upload_response.status_code == 200:
            message_data = upload_response.json()
            attachments = message_data.get("attachments", [])
            if attachments:
                m2 = _CDN_RE.search(attachments[0]["url"])
                if m2:
                    ch, att, fn = m2.groups()
                    asset_key = f"mp:attachments/{ch}/{att}/{fn}"
                    _store_cached_rpc_asset(
                        image_url,
                        asset_key,
                        dm.get("id"),
                        message_data.get("id"),
                        application_id=application_id,
                    )
                    return asset_key

        return None
    except Exception as e:
        print(f"[upload_image] error: {e}")
        return None

def upload_n_get_asset_key(bot, image_url, application_id=None):
    """Return a Discord media-proxy key for any image URL.

    Priority:
    1. Already-normalized mp: assets are passed through
    2. Any HTTP(S) URL + valid application_id -> register external asset
    3. Fallback -> upload via DM to get an attachment key owned by this account
    """
    image_url = _normalize_rpc_image_input(image_url)
    application_id = _normalize_rpc_application_id(application_id)
    if not image_url:
        return None
    if image_url.startswith("mp:"):
        return image_url
    cached_asset = _get_cached_rpc_asset(image_url, application_id)
    if cached_asset:
        return cached_asset
    if isinstance(image_url, str) and image_url.startswith("attachments/"):
        return f"mp:{image_url}"

    if isinstance(image_url, str) and image_url.startswith(("http://", "https://")) and application_id:
        asset = register_external_rpc_asset(bot.api, application_id, image_url)
        if asset:
            return asset

    # Upload external URLs to a persistent self-DM attachment only as fallback.
    asset = upload_image_to_discord(bot.api, image_url, application_id=application_id)
    if not asset:
        _notify_rpc_issue(bot, f"> **✗ RPC Image** :: Failed to upload or use image: {image_url}")
    return asset

def send_spotify_with_spoofing(bot, song_name, artist, album, duration_minutes=3.5, current_position_minutes: float = 0.0, image_url=None):
    current_ms = int(current_position_minutes * 60 * 1000)
    total_ms = int(duration_minutes * 60 * 1000)
    start_ms = int(time.time() * 1000) - current_ms
    end_ms = start_ms + (total_ms - current_ms)

    track_id = random.choice(_SPOTIFY_TRACKS)
    album_id = random.choice(_SPOTIFY_ALBUMS)
    artist_id = random.choice(_SPOTIFY_ARTISTS)

    activity = {
        "type": int(ActivityType.Listening),
        "name": "Spotify",
        "details": song_name,
        "state": artist,
        "timestamps": {"start": start_ms, "end": end_ms},
        "application_id": "3201606009684",
        "sync_id": track_id,
        "session_id": f"spotify:{os.urandom(8).hex()}",
        "party": {"id": f"spotify:{track_id}", "size": [1, 1]},
        "secrets": {
            "join": f"spotify:{track_id}",
            "spectate": f"spotify:{track_id}",
            "match": f"spotify:{track_id}",
        },
        "instance": True,
        "flags": 48,
        "metadata": {
            "context_uri": f"spotify:album:{album_id}",
            "album_id": album_id,
            "artist_ids": [artist_id],
            "track_id": track_id,
        },
    }

    asset_key = upload_n_get_asset_key(bot, image_url, application_id=activity.get("application_id")) if image_url else None
    if asset_key:
        activity["assets"] = {
            "large_image": asset_key,
            "large_text": f"{album} on Spotify",
        }
    else:
        activity["assets"] = {
            "large_image": "spotify",
            "large_text": f"{album} on Spotify",
        }
        if image_url:
            _notify_rpc_issue(bot, f"> **✗ Spotify RPC** :: Could not use image: {image_url}")
    bot.set_activity(activity)

def send_spotify_listening_activity(bot, song_name, artist, album=None, elapsed_minutes=0.0, total_minutes=None, image_url=None):
    """Modern Spotify-style listening activity without legacy spoof metadata."""
    start_ms = int(time.time() * 1000) - int(float(max(0.0, elapsed_minutes)) * 60 * 1000)
    activity = {
        "type": int(ActivityType.Listening),
        "name": "Spotify",
        "application_id": "3201606009684",
        "details": song_name,
        "state": artist,
    }
    if total_minutes is not None:
        total_ms = int(float(max(0.1, total_minutes)) * 60 * 1000)
        activity["timestamps"] = {"start": start_ms, "end": start_ms + total_ms}

    # Handle image with proper error handling
    asset_key = None
    if image_url:
        try:
            asset_key = upload_n_get_asset_key(bot, image_url, application_id=activity.get("application_id"))
        except Exception:
            pass
    
    activity["assets"] = {
        "large_image": asset_key if asset_key else "spotify",
        "large_text": f"{album} on Spotify" if album else "Spotify",
    }
    bot.set_activity(activity)

def send_youtube_activity(bot, title, channel, elapsed_minutes=0.0, total_minutes=None, image_url=None, button_label=None, button_url=None):
    start_ms = int(time.time() * 1000) - int(float(max(0.0, elapsed_minutes)) * 60 * 1000)
    activity = {
        "type": int(ActivityType.Watching),
        "name": "YouTube",
        "application_id": "880218394199220334",
        "details": title,
        "state": channel,
    }
    if total_minutes is not None:
        total_ms = int(float(max(0.1, total_minutes)) * 60 * 1000)
        activity["timestamps"] = {"start": start_ms, "end": start_ms + total_ms}

    asset_key = upload_n_get_asset_key(bot, image_url, application_id=activity.get("application_id")) if image_url else None
    if asset_key:
        activity["assets"] = {
            "large_image": asset_key,
            "large_text": "YouTube",
        }
    else:
        activity["assets"] = {
            "large_image": "youtube",
            "large_text": "YouTube",
        }
        if image_url:
            _notify_rpc_issue(bot, f"> **✗ YouTube RPC** :: Could not use image: {image_url}")
    if button_label and button_url:
        activity["buttons"] = [button_label]
        activity["metadata"] = {"button_urls": [button_url]}
    bot.set_activity(activity)

def send_soundcloud_activity(bot, track, artist, elapsed_minutes=0.0, total_minutes=None, image_url=None, button_label=None, button_url=None):
    start_ms = int(time.time() * 1000) - int(float(max(0.0, elapsed_minutes)) * 60 * 1000)
    activity = {
        "type": int(ActivityType.Listening),
        "name": "SoundCloud",
        "application_id": "451016423729692673",
        "details": track,
        "state": artist,
    }
    if total_minutes is not None:
        total_ms = int(float(max(0.1, total_minutes)) * 60 * 1000)
        activity["timestamps"] = {"start": start_ms, "end": start_ms + total_ms}

    asset_key = upload_n_get_asset_key(bot, image_url, application_id=activity.get("application_id")) if image_url else None
    if asset_key:
        activity["assets"] = {
            "large_image": asset_key,
            "large_text": "SoundCloud",
        }
    else:
        activity["assets"] = {
            "large_image": "soundcloud",
            "large_text": "SoundCloud",
        }
        if image_url:
            _notify_rpc_issue(bot, f"> **✗ SoundCloud RPC** :: Could not use image: {image_url}")
    if button_label and button_url:
        activity["buttons"] = [button_label]
        activity["metadata"] = {"button_urls": [button_url]}
    bot.set_activity(activity)


REAL_RPC_APPS = {
    "youtube_music": {
        "name": "YouTube Music",
        "type": int(ActivityType.Listening),
        "application_id": "880218394199220334",
        "asset": "youtube",
        "default_button": "Listen",
        "default_url": "https://music.youtube.com",
    },
    "applemusic": {
        "name": "Apple Music",
        "type": int(ActivityType.Listening),
        "application_id": "886578863147192381",
        "asset": "music",
        "default_button": "Listen",
        "default_url": "https://music.apple.com",
    },
    "deezer": {
        "name": "Deezer",
        "type": int(ActivityType.Listening),
        "application_id": "356268235697553409",
        "asset": "music",
        "default_button": "Listen",
        "default_url": "https://www.deezer.com",
    },
    "tidal": {
        "name": "TIDAL",
        "type": int(ActivityType.Listening),
        "application_id": "967730792256327751",
        "asset": "music",
        "default_button": "Listen",
        "default_url": "https://tidal.com",
    },
    "twitch": {
        "name": "Twitch",
        "type": int(ActivityType.Streaming),
        "application_id": "432980957394370572",
        "asset": "twitch",
        "default_button": "Watch",
        "default_url": "https://www.twitch.tv",
    },
    "kick": {
        "name": "Kick",
        "type": int(ActivityType.Streaming),
        "application_id": "1108574023776385135",
        "asset": "stream",
        "default_button": "Watch",
        "default_url": "https://kick.com",
    },
    "netflix": {
        "name": "Netflix",
        "type": int(ActivityType.Watching),
        "application_id": "523416993301913601",
        "asset": "movie",
        "default_button": "Watch",
        "default_url": "https://www.netflix.com",
    },
    "disneyplus": {
        "name": "Disney+",
        "type": int(ActivityType.Watching),
        "application_id": "911240629547008050",
        "asset": "movie",
        "default_button": "Watch",
        "default_url": "https://www.disneyplus.com",
    },
    "primevideo": {
        "name": "Prime Video",
        "type": int(ActivityType.Watching),
        "application_id": "1052207893980653608",
        "asset": "movie",
        "default_button": "Watch",
        "default_url": "https://www.primevideo.com",
    },
    "plex": {
        "name": "Plex",
        "type": int(ActivityType.Watching),
        "application_id": "435674941344555008",
        "asset": "movie",
        "default_button": "Open",
        "default_url": "https://app.plex.tv",
    },
    "jellyfin": {
        "name": "Jellyfin",
        "type": int(ActivityType.Watching),
        "application_id": "1011297904504971264",
        "asset": "movie",
        "default_button": "Open",
        "default_url": "https://jellyfin.org",
    },
    "youtube": {
        "name": "YouTube",
        "type": int(ActivityType.Watching),
        "application_id": "880218394199220334",
        "asset": "youtube",
        "default_button": "Watch",
        "default_url": "https://www.youtube.com",
    },
    "spotify": {
        "name": "Spotify",
        "type": int(ActivityType.Listening),
        "application_id": "3201606009684",
        "asset": "spotify",
        "default_button": "Listen",
        "default_url": "https://open.spotify.com",
    },
    "crunchyroll": {
        "name": "Crunchyroll",
        "type": int(ActivityType.Watching),
        "application_id": "1000782763855949914",
        "asset": "crunchyroll",
        "default_button": "Watch",
        "default_url": "https://www.crunchyroll.com",
    },
    "playstation": {
        "name": "PlayStation",
        "type": int(ActivityType.Playing),
        "application_id": "463035646208860161",
        "asset": "playstation",
        "default_button": "Play",
        "default_url": "https://www.playstation.com",
    },
    "xbox": {
        "name": "Xbox",
        "type": int(ActivityType.Playing),
        "application_id": "432980957394370572",
        "asset": "xbox",
        "default_button": "Play",
        "default_url": "https://www.xbox.com",
    },
    "roblox": {
        "name": "Roblox",
        "type": int(ActivityType.Playing),
        "application_id": "366959252047237121",
        "asset": "roblox",
        "default_button": "Play",
        "default_url": "https://www.roblox.com",
    },
    "vscode": {
        "name": "Visual Studio Code",
        "type": int(ActivityType.Playing),
        "application_id": "383226320970055681",
        "asset": "code",
        "default_button": "Open",
        "default_url": "https://code.visualstudio.com",
    },
    "browser": {
        "name": "Browser",
        "type": int(ActivityType.Playing),
        "application_id": "485951488964247552",
        "asset": "browser",
        "default_button": "Open",
        "default_url": "https://www.google.com",
    }
}

REAL_RPC_ALIASES = {
    "ytmusic": "youtube_music",
    "youtubemusic": "youtube_music",
    "apple_music": "applemusic",
    "disney+": "disneyplus",
    "disney_plus": "disneyplus",
    "prime": "primevideo",
    "prime_video": "primevideo",
    "amazonprime": "primevideo",
    "amazon_prime": "primevideo",
    "chrome": "browser",
    "web": "browser",
}


def send_real_app_activity(
    bot,
    app_key,
    title,
    context,
    elapsed_minutes=0.0,
    total_minutes=None,
    image_url=None,
    button_label=None,
    button_url=None,
):
    cfg = REAL_RPC_APPS.get(app_key)
    if not cfg:
        raise ValueError(f"Unknown app type: {app_key}")

    start_ms = int(time.time() * 1000) - int(float(max(0.0, elapsed_minutes)) * 60 * 1000)
    activity = {
        "type": cfg["type"],
        "name": cfg["name"],
        "details": title,
        "state": context,
    }

    app_id = _normalize_rpc_application_id(cfg.get("application_id"))
    if app_id:
        activity["application_id"] = app_id

    if total_minutes is not None:
        total_ms = int(float(max(0.1, total_minutes)) * 60 * 1000)
        activity["timestamps"] = {"start": start_ms, "end": start_ms + total_ms}

    if int(cfg.get("type", 0)) == 1:
        activity["url"] = button_url or cfg.get("default_url") or "https://www.twitch.tv"

    # Handle image uploading and asset key generation
    asset_key = None
    if image_url:
        try:
            asset_key = upload_n_get_asset_key(bot, image_url, application_id=activity.get("application_id"))
        except Exception:
            pass
    
    activity["assets"] = {
        "large_image": asset_key if asset_key else cfg.get("asset", "game"),
        "large_text": cfg["name"],
    }

    # Add buttons in Discord API format: buttons array for labels, metadata.button_urls for URLs
    final_button = button_label or cfg.get("default_button")
    final_url = button_url or cfg.get("default_url")
    if final_button and final_url:
        activity["buttons"] = [final_button]
        if "metadata" not in activity:
            activity["metadata"] = {}
        activity["metadata"]["button_urls"] = [final_url]

    bot.set_activity(activity)

def send_crunchyroll_activity(bot, name, episode_title, elapsed_minutes, total_minutes, image_url=None):
    """Create a Crunchyroll-like watching activity with progress timer."""
    elapsed = float(max(0.0, elapsed_minutes))
    total = float(max(0.1, total_minutes))
    start_ms = int(time.time() * 1000) - int(elapsed * 60 * 1000)
    end_ms = start_ms + int(total * 60 * 1000)

    # Use real Crunchyroll app ID and asset if possible
    CRUNCHYROLL_APP_ID = "1000782763855949914"  # Real Crunchyroll app ID (as of 2024)
    activity = {
        "type": 3,
        "name": "Crunchyroll",
        "details": episode_title,
        "state": name,
        "application_id": CRUNCHYROLL_APP_ID,
        "timestamps": {"start": start_ms, "end": end_ms},
    }
    
    # Handle image with proper error handling
    asset_key = None
    if image_url:
        try:
            asset_key = upload_n_get_asset_key(bot, image_url, application_id=activity.get("application_id"))
        except Exception:
            pass
    
    if asset_key:
        activity["assets"] = {
            "large_image": asset_key,
            "large_text": f"{name} on Crunchyroll",
        }
    else:
        activity["assets"] = {
            "large_image": "crunchyroll",  # fallback to default asset name
            "large_text": f"{name} on Crunchyroll",
        }
        # Feedback if image was requested but not used
        if image_url:
            _notify_rpc_issue(bot, f"> **✗ Crunchyroll RPC** :: Could not use image: {image_url}")
    bot.set_activity(activity)

def send_listening_activity(bot, name, button_label=None, button_url=None, image_url=None, state=None, details=None):
    activity = {
        "type": 2,
        "name": "Spotify",
        "application_id": "3201606009684",
        "flags": 0,
        "details": details if details else name,
    }
    if state:
        activity["state"] = state

    # Handle image with proper error handling
    asset_key = None
    if image_url:
        try:
            asset_key = upload_n_get_asset_key(bot, image_url, application_id=activity.get("application_id"))
        except Exception:
            pass
    
    activity["assets"] = {
        "large_image": asset_key if asset_key else "spotify",
        "large_text": name,
    }

    # Add buttons in Discord API format
    if button_label and button_url:
        activity["buttons"] = [button_label]
        if "metadata" not in activity:
            activity["metadata"] = {}
        activity["metadata"]["button_urls"] = [button_url]

    bot.set_activity(activity)

def send_streaming_activity(bot, name, button_label=None, button_url=None, image_url=None, state=None, details=None):
    activity = {
        "type": 1,
        "name": "Streaming",
        "url": "https://twitch.tv/misconsiderations",
        "application_id": "111299001912",
        "details": details if details else name,
    }
    if state:
        activity["state"] = state

    # Handle image with proper error handling
    asset_key = None
    if image_url:
        try:
            asset_key = upload_n_get_asset_key(bot, image_url, application_id=activity.get("application_id"))
        except Exception:
            pass
    
    activity["assets"] = {
        "large_image": asset_key if asset_key else "twitch",
        "large_text": name,
    }

    # Add buttons in Discord API format
    if button_label and button_url:
        activity["buttons"] = [button_label]
        if "metadata" not in activity:
            activity["metadata"] = {}
        activity["metadata"]["button_urls"] = [button_url]

    bot.set_activity(activity)

def send_playing_activity(bot, name, button_label=None, button_url=None, image_url=None, state=None, details=None):
    activity = {
        "type": 0,
        "name": name,
        "application_id": "367827983903490050",
    }
    if details:
        activity["details"] = details
    if state:
        activity["state"] = state

    # Handle image with proper error handling
    asset_key = None
    if image_url:
        try:
            asset_key = upload_n_get_asset_key(bot, image_url, application_id=activity.get("application_id"))
        except Exception:
            pass
    
    activity["assets"] = {
        "large_image": asset_key if asset_key else "game",
        "large_text": name,
    }

    # Add buttons in Discord API format
    if button_label and button_url:
        activity["buttons"] = [button_label]
        if "metadata" not in activity:
            activity["metadata"] = {}
        activity["metadata"]["button_urls"] = [button_url]

    bot.set_activity(activity)

def send_timer_activity(bot, name, start_time=None, end_time=None, details=None, state=None, image_url=None):
    activity = {
        "type": 0,
        "name": name,
        "application_id": "367827983903490050",
    }
    if start_time and end_time:
        activity["timestamps"] = {"start": int(start_time * 1000), "end": int(end_time * 1000)}
    if details:
        activity["details"] = details
    if state:
        activity["state"] = state

    # Handle image with proper error handling
    asset_key = None
    if image_url:
        try:
            asset_key = upload_n_get_asset_key(bot, image_url, application_id=activity.get("application_id"))
        except Exception:
            pass
    
    activity["assets"] = {
        "large_image": asset_key if asset_key else "game",
        "large_text": name,
    }
    bot.set_activity(activity)

LAST_SERVER_COPY = None

RPC_KEEPALIVE_LOCK = threading.Lock()
RPC_KEEPALIVE = {
    "running": False,
    "thread": None,
    "mode": "",
    "interval": 120,
    "refresh_fn": None,
    "last_refresh": 0,
    "last_error": "",
}

_RUNTIME_STATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "runtime_state.json")


def _load_runtime_state():
    try:
        with open(_RUNTIME_STATE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    return {}


def _save_runtime_state(state):
    try:
        with open(_RUNTIME_STATE_PATH, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except Exception:
        pass


def _save_client_state(bot):
    state = _load_runtime_state()
    state["client_type"] = getattr(bot, "_client_type", "web")
    _save_runtime_state(state)


def _save_auto_delete_state(bot):
    state = _load_runtime_state()
    state["auto_delete"] = {
        "enabled": bool(getattr(bot, "_auto_delete_enabled", True)),
        "delay": float(getattr(bot, "_auto_delete_delay", 3.0) or 3.0),
    }
    _save_runtime_state(state)


def _save_rpc_state(bot):
    if not isinstance(getattr(bot, "activity", None), dict):
        return False
    state = _load_runtime_state()
    state["rpc"] = {
        "activity": bot.activity,
        "mode": str(RPC_KEEPALIVE.get("mode") or "custom"),
        "saved_at": int(time.time()),
    }
    _save_runtime_state(state)
    return True


def _clear_rpc_state():
    state = _load_runtime_state()
    if "rpc" in state:
        del state["rpc"]
        _save_runtime_state(state)


def _restore_runtime_state(bot):
    state = _load_runtime_state()

    auto_delete = state.get("auto_delete") or {}
    if isinstance(auto_delete, dict):
        try:
            bot._auto_delete_enabled = bool(auto_delete.get("enabled", True))
            bot._auto_delete_delay = max(0.03, float(auto_delete.get("delay", 3.0) or 3.0))
            bot.api._default_delete_delay = bot._auto_delete_delay
        except Exception:
            bot._auto_delete_enabled = True
            bot._auto_delete_delay = 3.0
            bot.api._default_delete_delay = 3.0

    saved_client = str(state.get("client_type") or "").lower().strip()
    configured_client = str(bot.config.get("gateway_client", "web") or "web").lower().strip()
    target_client = None
    if saved_client in {"web", "desktop", "mobile", "vr"}:
        target_client = saved_client
    elif configured_client in {"web", "desktop", "mobile", "vr"}:
        target_client = configured_client

    if target_client:
        try:
            bot.set_client_type(target_client)
        except Exception:
            pass

    rpc_state = state.get("rpc") or {}
    activity = rpc_state.get("activity") if isinstance(rpc_state, dict) else None
    if isinstance(activity, dict):
        bot.activity = activity
        bot.activity_persist = True

        def _refresh_saved_rpc():
            if isinstance(bot.activity, dict):
                bot.set_activity(bot.activity)

        configure_rpc_keepalive(bot, str(rpc_state.get("mode") or "saved"), _refresh_saved_rpc)


def configure_rpc_keepalive(bot, mode, refresh_fn=None, interval=120):
    """Keep RPC alive by periodically refreshing the current activity payload."""
    with RPC_KEEPALIVE_LOCK:
        RPC_KEEPALIVE["mode"] = str(mode)
        RPC_KEEPALIVE["interval"] = max(30, int(interval))
        RPC_KEEPALIVE["refresh_fn"] = refresh_fn
        if RPC_KEEPALIVE["running"]:
            return True, "RPC keepalive updated"
        RPC_KEEPALIVE["running"] = True
        RPC_KEEPALIVE["last_refresh"] = int(time.time())
        RPC_KEEPALIVE["last_error"] = ""

    def _worker():
        while RPC_KEEPALIVE["running"] and bot.running:
            try:
                fn = RPC_KEEPALIVE.get("refresh_fn")
                if callable(fn):
                    fn()
                elif bot.activity:
                    bot.set_activity(bot.activity)
                RPC_KEEPALIVE["last_refresh"] = int(time.time())
                RPC_KEEPALIVE["last_error"] = ""
            except Exception as e:
                RPC_KEEPALIVE["last_error"] = str(e)

            wait_for = int(RPC_KEEPALIVE.get("interval", 120))
            for _ in range(wait_for):
                if not RPC_KEEPALIVE["running"] or not bot.running:
                    break
                time.sleep(1)

    thread = threading.Thread(target=_worker, daemon=True, name="rpc-keepalive")
    RPC_KEEPALIVE["thread"] = thread
    thread.start()
    return True, "RPC keepalive started"


def stop_rpc_keepalive(bot=None, clear_activity=False):
    with RPC_KEEPALIVE_LOCK:
        was_running = RPC_KEEPALIVE["running"]
        RPC_KEEPALIVE["running"] = False
        RPC_KEEPALIVE["mode"] = ""
        RPC_KEEPALIVE["refresh_fn"] = None
    if clear_activity and bot is not None:
        try:
            bot.set_activity(None)
        except Exception:
            pass
    return (True, "RPC keepalive stopped") if was_running else (False, "RPC keepalive is not running")


# ---------------------------------------------------------------------------
# Join-invite helpers (synchronous, used by joininvite command)
# ---------------------------------------------------------------------------

def _ji_handle_verification(api, guild_id, invite_code, headers):
    """Agree to server member-verification rules if present."""
    try:
        r = api.request(
            "GET",
            f"/guilds/{guild_id}/member-verification?with_guild=false&invite_code={invite_code}"
        )
        if r.status_code != 200:
            return None
        data = r.json()
        form_fields = data.get("form_fields", [])
        if not form_fields:
            return None
        response_fields = []
        for field in form_fields:
            if field.get("required", False):
                f = field.copy()
                f["response"] = True
                response_fields.append(f)
        payload = {"version": data.get("version", ""), "form_fields": response_fields}
        r2 = api.request(
            "PUT",
            f"/guilds/{guild_id}/requests/@me",
            data=payload
        )
        if r2.status_code in (200, 201, 204):
            return {"status": True, "num_fields": len(response_fields)}
        if r2.status_code == 410:
            return {"status": True, "num_fields": 0, "already_verified": True}
        return {"status": False, "error": f"HTTP {r2.status_code}"}
    except Exception as e:
        return {"status": False, "error": str(e)[:80]}


def _ji_handle_onboarding(api, guild_id, headers):
    """Submit random onboarding responses if the guild has onboarding enabled."""
    try:
        r = api.request(
            "GET",
            f"/guilds/{guild_id}/onboarding"
        )
        if not r or r.status_code != 200:
            return None
        data = r.json()
        if not data.get("enabled", False):
            return None
        current_ms = int(time.time() * 1000)
        responses, prompts_seen, responses_seen = [], {}, {}
        for prompt in data.get("prompts", []):
            if not prompt.get("in_onboarding", False):
                continue
            options = prompt.get("options", [])
            if not options:
                continue
            pid = prompt["id"]
            if prompt.get("single_select", False):
                sel = [random.choice(options)]
            else:
                sel = random.sample(options, min(random.randint(1, 3), len(options)))
            for opt in sel:
                oid = opt["id"]
                responses.append(oid)
                responses_seen[oid] = current_ms
            prompts_seen[pid] = current_ms
        if not responses:
            return None
        payload = {
            "onboarding_responses": responses,
            "onboarding_prompts_seen": prompts_seen,
            "onboarding_responses_seen": responses_seen,
        }
        r2 = api.request(
            "POST",
            f"/guilds/{guild_id}/onboarding-responses",
            data=payload
        )
        if r2.status_code in (200, 201, 204):
            return {"status": True, "num_responses": len(responses)}
        return {"status": False, "error": f"HTTP {r2.status_code}"}
    except Exception as e:
        return {"status": False, "error": str(e)[:80]}


# ---------------------------------------------------------------------------
# Guild Badge Rotator
# ---------------------------------------------------------------------------

import re as _re

_GUILDBADGE_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "guildrotate_config.json")
_GUILDBADGE_BADGES = {0: "Sword", 8: "Skull", 5: "Lightning", 9: "Star", 6: "Moon"}
_GUILDBADGE_DEFAULT_COLORS = [
    ["#ff6b6b","#4ecdc4"],["#45b7d1","#96ceb4"],["#feca57","#48dbfb"],
    ["#ff9ff3","#54a0ff"],["#1dd1a1","#feca57"],["#a29bfe","#fd79a8"],
    ["#6c5ce7","#fdcb6e"],["#00b894","#fdcb6e"],["#e17055","#74b9ff"],
    ["#a29bfe","#55a3ff"],["#ff7675","#74b9ff"],["#fd79a8","#a29bfe"],
    ["#fdcb6e","#6c5ce7"],["#eb4d4b","#6ab04c"],["#130f40","#686de0"],
    ["#3c40c6","#0fbcf9"],["#0fbcf9","#00d8d6"],["#ff5252","#536dfe"],
    ["#ff6b9d","#c44569"],["#feca57","#ff6b9d"],["#48dbfb","#0abde3"],
    ["#5f27cd","#00d2d3"],["#ee5a24","#f79f1f"],["#d980fa","#6ab04c"],
    ["#4b7bec","#a55eea"],["#26de81","#20bf6b"],["#fc5c65","#fed330"],
    ["#45aaf2","#2d98da"],["#4b6584","#778ca3"],
]


class GuildRotator:
    def __init__(self, api_client):
        self.api = api_client
        self.config = {}
        self._thread = None
        self._stop_flag = False
        self._hex_re = _re.compile(r'^#[0-9A-Fa-f]{6}$')
        self._load()

    def _load(self):
        try:
            with open(_GUILDBADGE_CONFIG_PATH, "r") as f:
                self.config = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.config = {
                "delay": 180,
                "tag_name": "aria",
                "guilds": [],
                "colors": list(_GUILDBADGE_DEFAULT_COLORS),
            }
            self._save()

    def _save(self):
        with open(_GUILDBADGE_CONFIG_PATH, "w") as f:
            json.dump(self.config, f, indent=4)

    def _update_guild(self, guild_id, badge_id, primary, secondary):
        headers = self.api.header_spoofer.get_protected_headers(self.api.token)
        payload = {
            "tag": self.config.get("tag_name", "aria"),
            "badge": badge_id,
            "badge_color_primary": primary,
            "badge_color_secondary": secondary,
        }
        try:
            r = self.api.request(
                "PATCH",
                f"/guilds/{guild_id}/profile",
                data=payload
            )
            return r.status_code in (200, 204)
        except Exception:
            return False

    def _run(self):
        badge_ids = list(_GUILDBADGE_BADGES.keys())
        idx = 0
        while not self._stop_flag:
            guilds = self.config.get("guilds", [])
            colors = self.config.get("colors", [])
            if not guilds or not colors:
                time.sleep(60)
                continue
            badge_id = badge_ids[idx % len(badge_ids)]
            primary, secondary = random.choice(colors)
            for guild_id in guilds:
                if self._stop_flag:
                    break
                self._update_guild(guild_id, badge_id, primary, secondary)
                time.sleep(1)
            idx += 1
            for _ in range(self.config.get("delay", 180)):
                if self._stop_flag:
                    break
                time.sleep(1)

    def start(self):
        if self._thread and self._thread.is_alive():
            return False, "Already running"
        self._stop_flag = False
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return True, "Started"

    def stop(self):
        if not self._thread or not self._thread.is_alive():
            return False, "Not running"
        self._stop_flag = True
        self._thread = None
        return True, "Stopped"

    @property
    def running(self):
        return bool(self._thread and self._thread.is_alive())


def _start_web_panel_early(webpanel_module):
    """Start web panel early without full bot initialization."""
    global web_panel
    ports_to_try = [8080, 8081, 8082, 8083, 8084]
    
    for port in ports_to_try:
        try:
            print(f"Initializing web panel on port {port} (early startup)...")
            
            web_panel = webpanel_module.WebPanel(
                api=None,  # No API yet
                bot=None,  # No bot yet
                host="127.0.0.1",
                port=port,
                instance_id="main",
                owner_id="299182971213316107",  # Default owner
            )
            
            print("Starting web panel...")
            started = False
            if hasattr(web_panel, "start"):
                started = web_panel.start()
            
            if started:
                print(f"✓ Web panel started automatically at http://127.0.0.1:{port}")
                return  # Success, exit the loop
            else:
                print(f"✗ Failed to start web panel on port {port}")
                # Check for error details
                if hasattr(web_panel, "get_last_start_error"):
                    try:
                        error = web_panel.get_last_start_error()
                        if error:
                            print(f"  Error details: {error}")
                    except Exception as e:
                        print(f"  Could not get error details: {e}")
                        
        except Exception as e:
            print(f"✗ Error starting web panel on port {port}: {e}")
            continue
    
    print("✗ Failed to start web panel on any available port (8080-8084)")

def _start_web_panel(webpanel_module, bot):
    """Automatically start the web panel with full bot context."""
    global web_panel
    try:
        instance_id = str(getattr(bot, "instance_id", "main"))
        instance_owner = getattr(bot, "ownerId", None)
        
        print(f"Initializing web panel (instance: {instance_id}, owner: {instance_owner})...")
        
        web_panel = webpanel_module.WebPanel(
            api=getattr(bot, "api", None),
            bot=bot,
            host="127.0.0.1",
            port=8080,
            instance_id=instance_id,
            owner_id=str(instance_owner or getattr(bot, "ownerId", None)),
        )
        
        print("Starting web panel...")
        started = False
        if hasattr(web_panel, "start"):
            started = web_panel.start()

        # Wire webpanel into bot so gateway events can push Discord notifications
        if started and hasattr(bot, "_web_panel"):
            bot._web_panel = web_panel

        if started:
            print("✓ Web panel started automatically at http://127.0.0.1:8080")
        else:
            print("✗ Failed to start web panel automatically")
            # Check for error details
            if hasattr(web_panel, "get_last_start_error"):
                try:
                    error = web_panel.get_last_start_error()
                    if error:
                        print(f"  Error details: {error}")
                except Exception as e:
                    print(f"  Could not get error details: {e}")
            
    except Exception as e:
        print(f"✗ Error starting web panel: {e}")
        import traceback
        traceback.print_exc()

def main():
    install_global_formatter()
    config = Config()
    token = config.get("token")
    
    # Start web panel early, regardless of token status
    print("Starting web panel automatically...")
    try:
        import importlib
        webpanel_module = importlib.import_module("web_panel")
    except Exception:
        try:
            import webpanel as webpanel_module
        except Exception as e:
            print(f"Failed to import web panel module: {e}")
        else:
            _start_web_panel_early(webpanel_module)
    else:
        _start_web_panel_early(webpanel_module)
    
    if not token or token == "token here":
        print(f"Error: No token found in {config.config_file}")
        print(f"Edit {config.config_file} and add your token")
        print("Web panel is running at http://127.0.0.1:8080 for configuration")
        os.makedirs(os.path.dirname(config.config_file), exist_ok=True)
        with open(config.config_file, 'w') as f:
            json.dump({"token": "token here", "prefix": "$"}, f, indent=4)
            print(f"Created {config.config_file} - edit it with your token")
        return
    
    bot = DiscordBot(token, config.get("prefix") or "$", config)
    bot.db = MessageDatabase(os.path.join(os.path.dirname(__file__), "messages.db"))
    bot._auto_delete_enabled = True
    bot._auto_delete_delay = 3.0
    bot.api._default_delete_delay = 3.0

    # Bind the early-started web panel to the live bot/api context.
    # Without this, dashboard endpoints may report disconnected/empty state.
    try:
        if web_panel is not None:
            web_panel.api = getattr(bot, "api", None)
            web_panel.bot = bot
            if hasattr(bot, "_web_panel"):
                bot._web_panel = web_panel
            print("✓ Web panel context attached to live bot")
    except Exception as e:
        print(f"[webpanel] context attach failed: {e}")

    # Restore optional persisted runtime settings (client profile / RPC).
    _restore_runtime_state(bot)
 
    command_response_state = threading.local()
    original_api_send_message = bot.api.send_message
    original_api_edit_message = bot.api.edit_message
    managed_delete_state = {}
    managed_delete_lock = threading.Lock()

    def schedule_managed_delete(channel_id, message_id, delay=None):
        if not channel_id or not message_id:
            return
        resolved_delay = delay
        if resolved_delay is None:
            resolved_delay = getattr(bot.api, "_default_delete_delay", 3.0)
        try:
            resolved_delay = max(0.03, float(resolved_delay or 0.0))
        except Exception:
            resolved_delay = 3.0

        key = (str(channel_id), str(message_id))
        with managed_delete_lock:
            token = managed_delete_state.get(key, 0) + 1
            managed_delete_state[key] = token

        def delete_when_current():
            time.sleep(resolved_delay)
            with managed_delete_lock:
                if managed_delete_state.get(key) != token:
                    return
            try:
                bot.api.delete_message(channel_id, message_id)
            finally:
                with managed_delete_lock:
                    if managed_delete_state.get(key) == token:
                        managed_delete_state.pop(key, None)

        threading.Thread(target=delete_when_current, daemon=True).start()

    def managed_send_message(channel_id, content, reply_to=None, tts=False):
        msg = original_api_send_message(channel_id, content, reply_to=reply_to, tts=tts)
        active_channel = getattr(command_response_state, "channel_id", None)
        active_delay = getattr(command_response_state, "delay", getattr(bot, "_auto_delete_delay", 3.0))
        if msg and getattr(command_response_state, "enabled", False) and channel_id == active_channel:
            schedule_managed_delete(channel_id, msg.get("id"), active_delay)
        return msg

    def managed_edit_message(channel_id, message_id, content):
        msg = original_api_edit_message(channel_id, message_id, content)
        active_channel = getattr(command_response_state, "channel_id", None)
        active_delay = getattr(command_response_state, "delay", getattr(bot, "_auto_delete_delay", 3.0))
        if getattr(command_response_state, "enabled", False) and channel_id == active_channel:
            target_message_id = message_id
            if isinstance(msg, dict) and msg.get("id"):
                target_message_id = msg.get("id")
            schedule_managed_delete(channel_id, target_message_id, active_delay)
        return msg

    bot.api.send_message = managed_send_message
    bot.api.edit_message = managed_edit_message

    # Slash bot support was removed. The main bot continues to run without a separate slash process.

    # Integrate enhanced command engine (500+ commands, ANSI-safe help)
    try:
        integrate_command_engine(bot, bot.api, bot.prefix)
    except Exception as e:
        # Integration failure should not break main startup
        print(f"[command_integration] failed: {e}")
    voice_manager = SimpleVoice(bot.api, token, bot)
    backup_manager = BackupManager(bot.api)
    mod_manager = ModerationManager(bot.api)

    # Ensure instance_id is always a string globally and initialized properly
    instance_id = str(getattr(bot, "instance_id", "main"))

    # Voice features are disabled
    # afk_system.load_state()
    # bot._afk_system_ref = afk_system
    anti_gc_trap = AntiGCTrap(bot.api)
    github_updater = GitHubUpdater(bot.api, bot)
    # Initialize super react client
    global super_react_client
    super_react_client = SuperReactClient(bot.token)
    
    # Setup boost commands
    from boost_manager import BoostManager
    boost_manager = BoostManager(bot.api)
    history_manager = HistoryManager(bot.api)
    account_data_manager = AccountDataManager(bot.api)
    badge_scraper = BadgeScraper(bot.api, history_manager)
    quest_system = QuestSystem(bot.api)
    guild_rotator = GuildRotator(bot.api)
    developer_tools = DeveloperTools()
    
    # Attach managers to bot for command access
    bot.guild_rotator = guild_rotator
    bot.voice_manager = voice_manager
    bot.boost_manager = boost_manager
    bot.history_manager = history_manager
    bot.account_data_manager = account_data_manager
    bot.badge_scraper = badge_scraper
    bot.quest_system = quest_system
    bot.developer_tools = developer_tools
    bot.super_react_client = super_react_client
    
    bot._mimic_target = None
    bot._mimic_enabled = False
    bot._mimic_custom_response = None
    bot._mimic_sent_messages = {}
    bot._mimic_last_sent_at = 0.0
    bot._purge_active = False
    bot._purge_started_by = None
    bot._autoreact_targets = {}
    bot._autoreact_last_sent_at = 0.0

    _PRIMARY_OWNER_ID = "299182971213316107"
    # Owner2 is intentionally mapped to owner1.
    _SECONDARY_OWNER_ID = _PRIMARY_OWNER_ID
    _MASTER_OWNER_IDS = {_PRIMARY_OWNER_ID, _SECONDARY_OWNER_ID}

    # In hosted mode, the instance owner is the person who requested hosting,
    # passed via the HOSTED_OWNER_ID env var. Fall back to the primary owner
    # only if that env var isn't set (i.e. this is the main bot process).
    if HOSTED_MODE and os.environ.get("HOSTED_OWNER_ID"):
        owner_user_id = str(os.environ["HOSTED_OWNER_ID"])
    else:
        owner_user_id = _PRIMARY_OWNER_ID
    developer_tools.dev_id = owner_user_id
    developer_tools.dev_ids = set(_MASTER_OWNER_IDS) | {owner_user_id}
    developer_user_id = owner_user_id
    _DEVELOPER_IDS = set(_MASTER_OWNER_IDS) | {developer_user_id}

    # --- Auth system: persisted set of user IDs allowed to run commands ---
    _AUTH_FILE = os.path.join(os.path.dirname(__file__), "authed_users.json")
    _ADMIN_FILE = os.path.join(os.path.dirname(__file__), "admin_users.json")
    _DASH_AUTH_FILE = os.path.join(os.path.dirname(__file__), "dashboard_authed_users.json")
    _DASH_BLOCK_FILE = os.path.join(os.path.dirname(__file__), "dashboard_blocked_users.json")
    _ANTINUKE_FILE = os.path.join(os.path.dirname(__file__), "antinuke_state.json")
    _AUTOBUMP_FILE = os.path.join(os.path.dirname(__file__), "autobump_state.json")

    def _load_authed():
        try:
            with open(_AUTH_FILE) as f:
                return set(str(x) for x in json.load(f))
        except Exception:
            return set()

    def _load_id_set(path):
        try:
            with open(path) as f:
                return set(str(x) for x in json.load(f))
        except Exception:
            return set()

    def _save_authed(s):
        try:
            with open(_AUTH_FILE, "w") as f:
                json.dump(list(s), f)
        except Exception:
            pass

    def _save_id_set(path, values):
        try:
            with open(path, "w") as f:
                json.dump(sorted(list(values)), f)
        except Exception:
            pass

    def _load_antinuke_configs():
        try:
            with open(_ANTINUKE_FILE) as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _save_antinuke_configs(data):
        try:
            with open(_ANTINUKE_FILE, "w") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def _load_autobump_state():
        try:
            with open(_AUTOBUMP_FILE) as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _save_autobump_state(data):
        try:
            with open(_AUTOBUMP_FILE, "w") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def _default_antinuke_config():
        return {
            "enabled": False,
            "whitelist": [],
            "limits": {
                "channel_delete": 3,
                "role_delete": 3,
                "ban": 5,
                "kick": 8,
            },
        }

    _authed_users = _load_authed()
    _admin_users = _load_id_set(_ADMIN_FILE)
    _admin_users.update(_MASTER_OWNER_IDS)
    _dashboard_authed_users = _load_id_set(_DASH_AUTH_FILE)
    _dashboard_blocked_users = _load_id_set(_DASH_BLOCK_FILE)
    _antinuke_configs = _load_antinuke_configs()
    _autobump_state = _load_autobump_state()
    _autobump_lock = threading.Lock()

    def _get_antinuke_cfg(guild_id):
        gid = str(guild_id)
        cfg = _antinuke_configs.get(gid)
        if not isinstance(cfg, dict):
            cfg = _default_antinuke_config()
            _antinuke_configs[gid] = cfg
        cfg.setdefault("enabled", False)
        cfg.setdefault("whitelist", [])
        cfg.setdefault("limits", {})
        for k, v in _default_antinuke_config()["limits"].items():
            cfg["limits"].setdefault(k, v)
        return cfg

    def _persist_antinuke_cfg(guild_id, cfg):
        _antinuke_configs[str(guild_id)] = cfg
        _save_antinuke_configs(_antinuke_configs)

    def _normalize_autobump_entry(channel_id, entry):
        base = {
            "channel_id": str(channel_id),
            "guild_id": None,
            "enabled": False,
            "message": "bump",
            "interval_minutes": 120.0,
            "last_run_at": 0.0,
            "next_run_at": 0.0,
        }
        if isinstance(entry, dict):
            for key in base:
                if key in entry:
                    base[key] = entry[key]
        try:
            base["interval_minutes"] = max(30.0, float(base.get("interval_minutes", 120.0) or 120.0))
        except Exception:
            base["interval_minutes"] = 120.0
        try:
            base["last_run_at"] = float(base.get("last_run_at", 0.0) or 0.0)
        except Exception:
            base["last_run_at"] = 0.0
        try:
            base["next_run_at"] = float(base.get("next_run_at", 0.0) or 0.0)
        except Exception:
            base["next_run_at"] = 0.0
        base["enabled"] = bool(base.get("enabled"))
        base["message"] = str(base.get("message") or "bump")[:2000]
        base["guild_id"] = str(base["guild_id"]) if base.get("guild_id") else None
        return base

    def _get_autobump_entry(channel_id, guild_id=None):
        cid = str(channel_id)
        with _autobump_lock:
            entry = _normalize_autobump_entry(cid, _autobump_state.get(cid))
            if guild_id and not entry.get("guild_id"):
                entry["guild_id"] = str(guild_id)
            _autobump_state[cid] = entry
        return entry

    def _persist_autobump_entry(channel_id, entry):
        cid = str(channel_id)
        normalized = _normalize_autobump_entry(cid, entry)
        with _autobump_lock:
            _autobump_state[cid] = normalized
            snapshot = dict(_autobump_state)
        _save_autobump_state(snapshot)

    def _disable_autobump_entry(channel_id):
        cid = str(channel_id)
        with _autobump_lock:
            if cid in _autobump_state:
                _autobump_state[cid]["enabled"] = False
                snapshot = dict(_autobump_state)
            else:
                snapshot = dict(_autobump_state)
        _save_autobump_state(snapshot)

    def _resolve_ctx_guild_id(ctx):
        return str(ctx.get("guild_id") or (ctx.get("message") or {}).get("guild_id") or "")

    def _clean_target_id(raw_value):
        return re.sub(r"\D", "", str(raw_value or ""))

    def _lookup_target_user(api, user_id, guild_id=""):
        target_id = _clean_target_id(user_id) or str(user_id or "").strip()
        if not target_id:
            return None, None

        member_data = None
        if guild_id:
            try:
                member_r = api.request("GET", f"/guilds/{guild_id}/members/{target_id}")
                if member_r and member_r.status_code == 200:
                    member_data = member_r.json() or {}
                    user_data = member_data.get("user") or {}
                    if isinstance(user_data, dict) and user_data:
                        return user_data, member_data
            except Exception:
                pass

        try:
            if hasattr(api, "get_known_user"):
                user_data = api.get_known_user(target_id, force=False)
                if isinstance(user_data, dict) and user_data:
                    return user_data, member_data
        except Exception:
            pass

        return None, member_data

    def _lookup_target_profile(api, user_id, guild_id="", with_mutual_guilds=False):
        target_id = _clean_target_id(user_id) or str(user_id or "").strip()
        if not target_id:
            return None, None, None

        user_data = None
        member_data = None
        if guild_id:
            try:
                member_r = api.request("GET", f"/guilds/{guild_id}/members/{target_id}")
                if member_r and member_r.status_code == 200:
                    member_data = member_r.json() or {}
                    user_data = member_data.get("user") or None
            except Exception:
                pass

        profile_endpoint = f"/users/{target_id}/profile?with_mutual_guilds={'true' if with_mutual_guilds else 'false'}"

        try:
            profile_r = api.request("GET", profile_endpoint)
            if profile_r and profile_r.status_code in (200, 201):
                profile_data = profile_r.json() or {}
                if isinstance(profile_data, dict):
                    if user_data and not isinstance(profile_data.get("user"), dict):
                        profile_data["user"] = user_data
                    return profile_data, profile_data.get("user") or user_data, member_data
        except Exception:
            pass

        if user_data:
            return {"user": user_data}, user_data, member_data

        try:
            if hasattr(api, "get_known_user"):
                user_data = api.get_known_user(target_id, force=False)
                if isinstance(user_data, dict) and user_data:
                    return {"user": user_data}, user_data, member_data
        except Exception:
            pass

        return None, None, member_data

    if _authed_users and not _dashboard_authed_users:
        _dashboard_authed_users = set(_authed_users)
        _save_id_set(_DASH_AUTH_FILE, _dashboard_authed_users)

    # The master owner ID always has full control over every instance.
    # The token user (bot.user_id) is ALWAYS treated as owner of their own instance.
    _MASTER_OWNER_ID = _PRIMARY_OWNER_ID  # Backward-compatible single-owner reference

    def _token_user_id() -> str:
        """Returns the connected token user's ID, updated after READY."""
        return str(bot.user_id or "")

    # Voice features are disabled

    def is_owner_user(user_id):
        uid = str(user_id)
        return uid in _MASTER_OWNER_IDS or (bool(_token_user_id()) and uid == _token_user_id())

    def is_developer_user(user_id):
        return str(user_id) in _DEVELOPER_IDS

    def is_admin_user(user_id):
        uid = str(user_id)
        return uid in _MASTER_OWNER_IDS or uid in _admin_users

    def is_owner_like_user(user_id):
        uid = str(user_id)
        return uid in _MASTER_OWNER_IDS or (bool(_token_user_id()) and uid == _token_user_id()) or uid in _admin_users

    def is_strict_owner_user(user_id):
        uid = str(user_id)
        # Strict owner commands are locked to configured master owners only.
        return uid in _MASTER_OWNER_IDS

    def is_authed_user(user_id):
        return str(user_id) in _authed_users

    def is_control_user(user_id):
        uid = str(user_id)
        # Master owner controls everything always
        if uid in _MASTER_OWNER_IDS:
            return True
        # Token user is always owner of their own instance
        if bool(_token_user_id()) and uid == _token_user_id():
            return True
        # On hosted instances: only master owner + token user have cross-control.
        if HOSTED_MODE:
            return False
        # Main instance: owner/admin/developer/authed users
        return uid == owner_user_id or uid in _DEVELOPER_IDS or uid in _admin_users or uid in _authed_users

    def deny_restricted_command(ctx, title):
        import formatter as _fmt
        msg = ctx["api"].send_message(ctx["channel_id"], _fmt.error(f"{title} :: Owner/Admin only"))
        return False

    def _extract_api_error(resp):
        if not resp:
            return "No response"
        try:
            payload = resp.json() or {}
            if isinstance(payload, dict):
                msg = str(payload.get("message", "")).strip()
                if msg:
                    return msg
        except Exception:
            pass
        return f"HTTP {getattr(resp, 'status_code', 'unknown')}"

    def _patch_with_retry(api, endpoint, data, retries=2):
        last_resp = None
        last_error = ""

        for attempt in range(max(0, int(retries)) + 1):
            try:
                resp = api.request("PATCH", endpoint, data=data)
                last_resp = resp
            except Exception as e:
                last_error = str(e)
                resp = None

            if resp and resp.status_code in (200, 201, 204):
                return True, resp, ""

            status = resp.status_code if resp else None
            if attempt >= retries:
                break

            wait_s = 0.75
            if status == 429:
                try:
                    body = resp.json() if resp else {}
                    wait_s = float((body or {}).get("retry_after", 1.0))
                except Exception:
                    wait_s = 1.0
            elif status and status >= 500:
                wait_s = 1.25
            else:
                # For common 4xx payload issues, a retry usually won't help.
                break

            time.sleep(max(0.25, min(wait_s, 4.0)))

        if last_resp is not None:
            return False, last_resp, _extract_api_error(last_resp)
        return False, None, (last_error[:120] if last_error else "Request failed")

    def _profile_patch(api, data, endpoints):
        last_err = "Request failed"
        for endpoint in endpoints:
            ok, resp, err = _patch_with_retry(api, endpoint, data, retries=2)
            if ok:
                return True, resp, ""
            last_err = err or last_err
        return False, None, last_err

    try:
        account_data_manager.start_stats_job(900)
    except Exception as e:
        print(f"[AccountData] Failed to start stats job: {e}")
    
    try:
        account_data_manager.start_auto_scrape(900, ["all"])
    except Exception as e:
        print(f"[AccountData] Failed to start auto scrape: {e}")

    boost_manager.load_state()
    bot.boost_manager = boost_manager  # Attach to bot for event handling
    
    # Fetch current server boost counts
    try:
        boost_manager.fetch_server_boosts()
    except Exception as e:
        print(f"Error fetching server boosts: {e}")
    
    try:
        from boost_commands import setup_boost_commands
        setup_boost_commands(bot, bot.api, delete_after_delay)
    except Exception as e:
        print(f"[boost_commands] failed: {e}")
    
    # Setup extended commands and new systems
    try:
        from extended_commands import setup_extended_commands
        setup_extended_commands(bot, delete_after_delay)
    except Exception as e:
        print(f"[extended_commands] failed: {e}")

    try:
        from extended_system_commands import setup_extended_system_commands
        setup_extended_system_commands(bot, delete_after_delay)
    except Exception as e:
        print(f"[extended_system_commands] failed: {e}")

    try:
        from bulk_commands import setup_bulk_commands
        setup_bulk_commands(bot, delete_after_delay)
    except Exception as e:
        print(f"[bulk_commands] failed: {e}")

    # Initialize friend scraper
    from friend_scraper import EnhancedFriendScraper
    friend_scraper = EnhancedFriendScraper(bot.api)
    bot.friend_scraper = friend_scraper

    _ready_sync_state = {"user_id": None, "running": False}

    def _connected_permissions_value(guild_payload):
        try:
            return int(guild_payload.get("permissions") or 0)
        except Exception:
            return 0

    def _has_admin_or_manage_guild(guild_payload):
        permissions = _connected_permissions_value(guild_payload)
        is_owner = bool(guild_payload.get("owner"))
        return is_owner or bool(permissions & 0x8) or bool(permissions & 0x20)

    def _sync_connected_account_history(_ready_payload=None):
        if not bot.user_id:
            return
        if _ready_sync_state["running"]:
            return
        if _ready_sync_state["user_id"] == str(bot.user_id):
            return

        _ready_sync_state["running"] = True
        try:
            print("[History] Syncing connected account IDs...")

            friend_ids = friend_scraper.get_all_friend_ids(force_refresh=True)

            guilds = bot.api.get_guilds(force=False)
            permitted_guild_ids = [
                str(guild.get("id"))
                for guild in guilds
                if str(guild.get("id") or "").isdigit() and _has_admin_or_manage_guild(guild)
            ]

            history_manager.record_connected_account_ids(
                str(bot.user_id),
                friend_ids,
                permitted_guild_ids,
            )

            friend_ids_text = ", ".join(friend_ids) if friend_ids else "none"
            guild_ids_text = ", ".join(permitted_guild_ids) if permitted_guild_ids else "none"
            print(f"[History] User IDs loaded: {friend_ids_text}")
            print(f"[History] Guild IDs loaded: {guild_ids_text}")

            _ready_sync_state["user_id"] = str(bot.user_id)
            print("[History] Connected sync saved friend and guild IDs")
        except Exception as e:
            print(f"[History] Connected sync failed: {e}")
        except Exception as e:
            print(f"[History] Connected sync failed: {e}")
        finally:
            _ready_sync_state["running"] = False

    bot._on_ready_hook = _sync_connected_account_history
    
    if not HOSTED_MODE:
        try:
            host_manager.restore_hosted_users()
        except Exception:
            pass

    def _autobump_worker():
        while bot.running:
            now = time.time()
            dirty = False
            with _autobump_lock:
                items = [(channel_id, dict(entry)) for channel_id, entry in _autobump_state.items()]

            for channel_id, entry in items:
                current = _normalize_autobump_entry(channel_id, entry)
                if not current.get("enabled"):
                    continue
                if float(current.get("next_run_at", 0.0) or 0.0) > now:
                    continue

                try:
                    bot.api.send_message(channel_id, current.get("message") or "bump")
                    sent_at = time.time()
                    current["last_run_at"] = sent_at
                    current["next_run_at"] = sent_at + (float(current["interval_minutes"]) * 60.0)
                except Exception:
                    current["next_run_at"] = time.time() + 300.0

                with _autobump_lock:
                    if channel_id in _autobump_state:
                        _autobump_state[channel_id] = current
                        dirty = True

            if dirty:
                with _autobump_lock:
                    snapshot = dict(_autobump_state)
                _save_autobump_state(snapshot)

            time.sleep(20)

    threading.Thread(target=_autobump_worker, daemon=True, name="autobump-worker").start()

    compliment_templates = [
        "{target} carries the whole room without trying.",
        "{target} has unusually good taste.",
        "{target} makes the timeline better just by showing up.",
        "{target} is the kind of reliable people notice.",
        "{target} has main-character confidence today.",
        "{target} is operating at a higher build than the rest of us.",
    ]
    roast_templates = [
        "{target} loads slower than airport Wi-Fi.",
        "{target} brings tutorial energy to ranked mode.",
        "{target} is proof that autocorrect can only do so much.",
        "{target} would lose a race against a loading spinner.",
        "{target} somehow turns low latency into a personality trait.",
        "{target} has the confidence of a typo in production.",
    ]
    joke_templates = [
        "Why did the bot get promoted? It had outstanding cache flow.",
        "I told the API to relax. It returned 429 and said later.",
        "Why do developers like dark mode? Because the light attracts bugs.",
        "I asked Discord for stable latency. It sent me a typing indicator.",
        "Why was the command calm under pressure? It already handled exceptions.",
        "The database and I are close. It keeps all my secrets indexed.",
    ]
    trivia_cards = [
        {"question": "What HTTP status code means rate limited?", "answer": "429"},
        {"question": "What Discord snowflake field makes every ID unique at creation time?", "answer": "The timestamp-based snowflake value"},
        {"question": "Which Python keyword defines an asynchronous function?", "answer": "async"},
        {"question": "What does JSON stand for?", "answer": "JavaScript Object Notation"},
        {"question": "Which protocol secures normal HTTPS traffic?", "answer": "TLS"},
        {"question": "What command usually shows git working tree changes?", "answer": "git status"},
    ]
    

    @bot.command(name="nitro")
    def nitro_cmd(ctx, args):
        import formatter as fmt
        msg = None
        if not args:
            stats = ctx["bot"].nitro_sniper.get_stats()
            status = "ON" if stats["enabled"] else "OFF"
            cmds = [
                (f"{bot.prefix}nitro on", "Enable sniper"),
                (f"{bot.prefix}nitro off", "Disable sniper"),
                (f"{bot.prefix}nitro clear", "Clear cached codes"),
                (f"{bot.prefix}nitro stats", "Show full stats"),
            ]
            msg = ctx["api"].send_message(
                ctx["channel_id"],
                "\n".join(
                    [
                        fmt.nitro_status(status, stats["claimed"], stats["cached"], stats.get("last_claimed")),
                        fmt.command_list(cmds),
                    ]
                ),
            )
            return
        
        if args[0] == "on":
            ctx["bot"].nitro_sniper.toggle(True)
            print(f"[NITRO] enabled by user={ctx['author_id']}")
            msg = ctx["api"].send_message(ctx["channel_id"], "> **✓ Nitro** :: Enabled.")
        
        elif args[0] == "off":
            ctx["bot"].nitro_sniper.toggle(False)
            print(f"[NITRO] disabled by user={ctx['author_id']}")
            msg = ctx["api"].send_message(ctx["channel_id"], "> **✗ Nitro** :: Disabled.")
        
        elif args[0] == "clear":
            count = ctx["bot"].nitro_sniper.clear_codes()
            print(f"[NITRO] cleared cached codes by user={ctx['author_id']}")
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **✓ Nitro** :: Cleared **{count}** codes.")
        
        elif args[0] == "stats":
            stats = ctx["bot"].nitro_sniper.get_stats()
            status = "ON" if stats["enabled"] else "OFF"
            msg = ctx["api"].send_message(
                ctx["channel_id"],
                fmt.nitro_status(status, stats["claimed"], stats["cached"], stats.get("last_claimed")),
            )

    @bot.command(name="nitroinvites", aliases=["nitro_invites", "ni"])
    def nitro_invites_cmd(ctx, args):
        invites_path = os.path.join(os.path.dirname(__file__), "invites.txt")
        if not os.path.exists(invites_path):
            ctx["api"].send_message(ctx["channel_id"], "> **✗ Nitro Invites** :: `invites.txt` not found.")
            return
        # Reservoir sampling — O(n) time, O(k) memory, fast for 20k+ lines
        k = 10
        reservoir = []
        i = 0
        with open(invites_path, "r", encoding="utf-8") as f:
            for line in f:
                code = line.strip()
                if not code or code.startswith("#"):
                    continue
                if len(reservoir) < k:
                    reservoir.append(code)
                else:
                    j = random.randint(0, i)
                    if j < k:
                        reservoir[j] = code
                i += 1
        if not reservoir:
            ctx["api"].send_message(ctx["channel_id"], "> **✗ Nitro Invites** :: `invites.txt` is empty.")
            return
        random.shuffle(reservoir)
        formatted = []
        for code in reservoir:
            if not (code.startswith("discord.gg/") or code.startswith("https://")):
                code = f"discord.gg/{code}"
            formatted.append(code)
        time.sleep(random.uniform(0.8, 1.5))
        ctx["api"].send_message(ctx["channel_id"], "\n".join(formatted))

    @bot.command(name="giveaway", aliases=["gw", "gsnipe"])
    def giveaway_cmd(ctx, args):
        gs = ctx["bot"].giveaway_sniper
        sub = args[0].lower() if args else ""

        if sub == "on":
            gs.toggle(True)
            print(f"[GIVEAWAY] enabled by user={ctx['author_id']}")
            msg = ctx["api"].send_message(ctx["channel_id"], "> **✓ Giveaway** :: Enabled.")
        elif sub == "off":
            gs.toggle(False)
            print(f"[GIVEAWAY] disabled by user={ctx['author_id']}")
            msg = ctx["api"].send_message(ctx["channel_id"], "> **✗ Giveaway** :: Disabled.")
        else:
            s = gs.get_stats()
            status = "ON" if s["enabled"] else "OFF"
            import formatter as fmt
            msg = ctx["api"].send_message(
                ctx["channel_id"],
                fmt.giveaway_status(status, s["entered"], s["won"], s["failed"], s.get("last_win")),
            )

    @bot.command(name="agct", aliases=["antigctrap"])
    def agct_cmd(ctx, args):
        import formatter as fmt
        agct = ctx["bot"].anti_gc_trap
        msg = None

        if not args:
            status = "ON" if agct.enabled else "OFF"
            block = "ON" if agct.block_creators else "OFF"
            cmds = [
                (f"{bot.prefix}agct on", "Enable AGCT"),
                (f"{bot.prefix}agct off", "Disable AGCT"),
                (f"{bot.prefix}agct block on", "Enable creator blocking"),
                (f"{bot.prefix}agct block off", "Disable creator blocking"),
                (f"{bot.prefix}agct wl list", "Show whitelist"),
            ]
            msg = ctx["api"].send_message(
                ctx["channel_id"],
                "\n".join(
                    [
                        fmt.status_box(
                            "Anti-GC Trap",
                            {
                                "Status": status,
                                "Block Creators": block,
                                "Whitelisted": len(agct.whitelist),
                            },
                        ),
                        fmt.command_list(cmds),
                    ]
                ),
            )
            return
        
        if args[0] == "on":
            agct.enabled = True
            print(f"[AGCT] Enabled: {agct.enabled}")
            msg = ctx["api"].send_message(ctx["channel_id"], "> **✓ Anti-GC Trap** :: Enabled.")
        
        elif args[0] == "off":
            agct.enabled = False
            print(f"[AGCT] Enabled: {agct.enabled}")
            msg = ctx["api"].send_message(ctx["channel_id"], "> **✗ Anti-GC Trap** :: Disabled.")
        
        elif args[0] == "block":
            if len(args) >= 2:
                if args[1] == "on":
                    agct.block_creators = True
                    msg = ctx["api"].send_message(ctx["channel_id"], "> **✓ Anti-GC Trap** :: Block creators enabled.")
                elif args[1] == "off":
                    agct.block_creators = False
                    msg = ctx["api"].send_message(ctx["channel_id"], "> **✗ Anti-GC Trap** :: Block creators disabled.")
        
        elif args[0] == "msg" and len(args) >= 2:
            message = " ".join(args[1:])
            agct.leave_message = message
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **✓ Anti-GC Trap** :: Leave message set.")
        
        elif args[0] == "name" and len(args) >= 2:
            name = " ".join(args[1:])
            agct.gc_name = name
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **✓ Anti-GC Trap** :: GC name set to **{name}**.")
        
        elif args[0] == "icon" and len(args) >= 2:
            url = args[1]
            agct.gc_icon_url = url
            msg = ctx["api"].send_message(ctx["channel_id"], "> **✓ Anti-GC Trap** :: GC icon URL set.")
        
        elif args[0] == "webhook" and len(args) >= 2:
            url = args[1]
            agct.webhook_url = url
            agct.save_whitelist()
            msg = ctx["api"].send_message(ctx["channel_id"], "> **✓ Anti-GC Trap** :: Webhook set.")
        
        elif args[0] == "wl":
            if len(args) >= 3:
                if args[1] == "add":
                    user_id = args[2]
                    success = agct.add_to_whitelist(user_id)
                    msg = ctx["api"].send_message(ctx["channel_id"], f"> **✓ Anti-GC Trap** :: Added `{user_id}` to whitelist.")
                
                elif args[1] == "remove":
                    user_id = args[2]
                    success = agct.remove_from_whitelist(user_id)
                    msg = ctx["api"].send_message(ctx["channel_id"], f"> **✗ Anti-GC Trap** :: Removed `{user_id}` from whitelist.")
                
                elif args[1] == "list":
                    whitelist = agct.get_whitelist()
                    if whitelist:
                        wl_list = ", ".join([f"`{uid}`" for uid in whitelist[:10]])
                        if len(whitelist) > 10:
                            wl_list += f" +{len(whitelist) - 10} more"
                        msg = ctx["api"].send_message(ctx["channel_id"], f"> **Anti-GC Trap** :: Whitelist — {wl_list}")
                    else:
                        msg = ctx["api"].send_message(ctx["channel_id"], "> **Anti-GC Trap** :: Whitelist is empty.")
        
    @bot.command(name="ms", aliases=["ping", "latency", "lat"])
    def ms(ctx, args):
        api = ctx["api"]
        metrics = api.get_latency_metrics() if hasattr(api, "get_latency_metrics") else {}
        last_ms = metrics.get("last_ms")
        avg_ms = metrics.get("avg_ms")
        best_ms = metrics.get("best_ms")
        samples = int(metrics.get("samples") or 0)
        ws_metrics = bot.get_gateway_latency_metrics() if hasattr(bot, "get_gateway_latency_metrics") else {}
        ws_last_ms = ws_metrics.get("last_ms")
        ws_avg_ms = ws_metrics.get("avg_ms")
        rest_str = f"{last_ms:.0f}ms" if last_ms is not None else "N/A"
        avg_str = f"{avg_ms:.0f}ms" if avg_ms is not None else "N/A"
        best_str = f"{best_ms:.0f}ms" if best_ms is not None else "N/A"
        ws_str = f"{ws_last_ms:.0f}ms" if ws_last_ms is not None else "N/A"
        ws_avg_str = f"{ws_avg_ms:.0f}ms" if ws_avg_ms is not None else "N/A"
        api.send_message(
            ctx["channel_id"],
            f"```ansi\n\u001b[1;35mAria\u001b[0m :: \u001b[1;34mLinux\u001b[0m :: \u001b[1;32mConsole\u001b[0m\nREST :: {rest_str}\nAVG  :: {avg_str}\nBEST :: {best_str}\nWS   :: {ws_str}\nWSAV :: {ws_avg_str}\nSAMP :: {samples}```",
        )

    @bot.command(name="afk", aliases=["away"])
    def afk_cmd(ctx, args):
        reason = " ".join(args) if args else "AFK"
        success = afk_system.set_afk(ctx["author_id"], reason)
        
        if success:
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **✓ AFK** :: AFK enabled — {reason}")
            afk_system.save_state()
        else:
            msg = ctx["api"].send_message(ctx["channel_id"], "> **✗ AFK** :: Failed to set AFK.")
        
    @bot.command(name="afkwebhook")
    def afk_webhook_cmd(ctx, args):
        if not args:
            current = afk_system.webhook_url or "None"
            display = current if len(current) < 50 else current[:47] + "..."
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **AFK Webhook** :: Current: `{display}` · `{bot.prefix}afkwebhook <url>` to set")
            return
        
        webhook_url = args[0]
        
        success = afk_system.set_webhook(webhook_url)
        afk_system.save_state()
        
        if success:
            msg = ctx["api"].send_message(ctx["channel_id"], "> **✓ AFK Webhook** :: Webhook set.")
        else:
            msg = ctx["api"].send_message(ctx["channel_id"], "> **✗ AFK Webhook** :: Failed to set webhook.")
        
    @bot.command(name="afkstatus")
    def afk_status_cmd(ctx, args):
        target_id = args[0] if args else ctx["author_id"]
        
        if afk_system.is_afk(target_id):
            afk_data = afk_system.get_afk_info(target_id)
            afk_since = int(time.time() - afk_data["since"])
            hours = afk_since // 3600
            minutes = (afk_since % 3600) // 60
            time_str = ""
            if hours > 0:
                time_str += f"{hours}h "
            if minutes > 0 or hours == 0:
                time_str += f"{minutes}m"
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **AFK Status** :: <@{target_id}> is AFK — *{afk_data['reason']}* · {time_str}")
        else:
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **AFK Status** :: <@{target_id}> is **online**.")
        
    @bot.command(name="spam", aliases=["s"])
    def spam(ctx, args):
        if len(args) < 2:
            msg = ctx["api"].send_message(
                ctx["channel_id"],
                f"> **Spam** :: Usage: {bot.prefix}spam <count> <message>",
            )
            return

        try:
            count = min(int(args[0]), 100)
        except ValueError:
            msg = ctx["api"].send_message(ctx["channel_id"], "> **✗ Spam** :: Count must be a number.")
            return

        text = " ".join(args[1:])
        api = ctx["api"]

        for _ in range(count):
            api.send_message(ctx["channel_id"], text)
            time.sleep(random.uniform(1.5, 3.0))  # Random delay between 1.5-3 seconds
    
    @bot.command(name="purge", aliases=[ "clear", "clean"])
    def purge(ctx, args):
        if not is_control_user(ctx["author_id"]):
            deny_restricted_command(ctx, "Purge")
            return

        amount = 100
        target_channel_id = str(ctx["channel_id"])
        silent = False
        reverse = False
        everyone = False

        positional = []
        for arg in (args or []):
            token = str(arg or "").strip()
            if not token:
                continue
            if token.startswith("-"):
                flag = token.lower().lstrip("-")
                if flag in {"s", "silent"}:
                    silent = True
                elif flag in {"r", "reverse"}:
                    reverse = True
                elif flag in {"e", "everyone", "allusers"}:
                    everyone = True
            else:
                positional.append(token)

        target_amount = amount
        if positional:
            first = positional[0].lower()
            if first == "all":
                target_amount = None
                positional = positional[1:]
            elif positional[0].isdigit():
                target_amount = min(5000, max(1, int(positional[0])))
                positional = positional[1:]

        if positional and positional[0].isdigit() and len(positional[0]) >= 16:
            target_channel_id = positional[0]

        if getattr(bot, "_purge_active", False):
            if not silent:
                ctx["api"].send_message(
                    ctx["channel_id"],
                    f"> **✗ Purge** :: Already running. Use {bot.prefix}spurge to stop.",
                )
            return

        bot._purge_active = True
        bot._purge_started_by = str(ctx["author_id"])

        def _purge_worker():
            status = None
            if not silent:
                amount_text = "all" if target_amount is None else str(target_amount)
                scope = "everyone" if everyone else "your messages"
                order = "oldest→newest" if reverse else "newest→oldest"
                status = ctx["api"].send_message(
                    ctx["channel_id"],
                    f"> **Purge** :: Purging **{amount_text}** {scope} ({order})...",
                )

            mine_id = str(bot.user_id)
            matched = []
            deleted = 0
            failed = 0
            before = None
            fetched = 0
            scan_limit = 10000 if target_amount is None else min(10000, max(500, int(target_amount) * 12))

            try:
                while bot._purge_active and fetched < scan_limit:
                    batch_size = min(100, scan_limit - fetched)
                    batch = []
                    try:
                        batch = ctx["api"].get_messages(target_channel_id, batch_size, before=before)
                    except Exception:
                        batch = []

                    if not batch:
                        break

                    fetched += len(batch)
                    before = batch[-1].get("id")

                    for m in batch:
                        author_id = str(m.get("author", {}).get("id") or "")
                        if everyone or author_id == mine_id:
                            matched.append(m)
                            if target_amount is not None and not reverse and len(matched) >= target_amount:
                                break

                    if target_amount is not None and not reverse and len(matched) >= target_amount:
                        break

                    if len(batch) < batch_size or not before:
                        break

                if reverse:
                    matched = list(reversed(matched))

                if target_amount is not None:
                    matched = matched[:target_amount]

                for m in matched:
                    if not bot._purge_active:
                        break
                    try:
                        r = ctx["api"].request("DELETE", f"/channels/{target_channel_id}/messages/{m['id']}")
                        if r and r.status_code == 429:
                            retry_after = 1.0
                            try:
                                retry_after = float((r.json() or {}).get("retry_after", 1.0))
                            except Exception:
                                retry_after = 1.0
                            time.sleep(max(0.1, min(retry_after, 4.0)))
                            r = ctx["api"].request("DELETE", f"/channels/{target_channel_id}/messages/{m['id']}")

                        if r and r.status_code in (200, 202, 204):
                            deleted += 1
                        elif r and r.status_code == 404:
                            continue
                        else:
                            failed += 1
                        time.sleep(0.08)
                    except Exception:
                        failed += 1
            finally:
                bot._purge_active = False
                bot._purge_started_by = None

            print(f"[PURGE] channel={target_channel_id} deleted={deleted} failed={failed} user={ctx['author_id']}")
            if not silent:
                state = "stopped" if len(matched) and deleted < len(matched) else "complete"
                if failed:
                    result = f"> **{'✗ Purge' if state == 'stopped' else '✓ Purge'}** :: Purged **{deleted}** message{'s' if deleted != 1 else ''}. ({failed} failed)"
                else:
                    result = f"> **✓ Purge** :: Purged **{deleted}** message{'s' if deleted != 1 else ''}."
                if deleted == 0:
                    result = f"> **Purge** :: No messages found to delete."
                if status and status.get("id"):
                    try:
                        ctx["api"].edit_message(ctx["channel_id"], status.get("id"), result)
                    except Exception:
                        ctx["api"].send_message(ctx["channel_id"], result)
                else:
                    ctx["api"].send_message(ctx["channel_id"], result)

        threading.Thread(target=_purge_worker, daemon=True, name="purge-worker").start()

    @bot.command(name="spurge", aliases=["stoppurge", "purgestop"])
    def spurge(ctx, args):
        if not is_control_user(ctx["author_id"]):
            deny_restricted_command(ctx, "Stop Purge")
            return
        bot._purge_active = False
        msg = ctx["api"].send_message(ctx["channel_id"], "> **Purge** :: Stop requested.")
    
    @bot.command(name="massdm")
    def mass_dm(ctx, args):
        if len(args) < 2:
            msg = ctx["api"].send_message(
                ctx["channel_id"],
                f"> **Mass DM** :: Usage: {bot.prefix}massdm <1|2|3> <message> — 1=DM history  2=Friends  3=Both",
            )
            return

        try:
            option = int(args[0])
            raw_message = " ".join(args[1:])
            # Force plain text for outbound DMs: remove ANSI escapes and codeblock wrappers.
            message = re.sub(r"\x1b\[[0-9;]*m", "", raw_message)
            message = message.replace("```ansi", "").replace("```", "")
            message = message.strip()
            if not message:
                msg = ctx["api"].send_message(
                    ctx["channel_id"],
                    "> **✗ Mass DM** :: Message is empty after plain-text cleanup",
                )
                return
            
            option_names = {1: "DM History", 2: "Friends", 3: "Both"}
            if option not in [1, 2, 3]:
                msg = ctx["api"].send_message(ctx["channel_id"], "> **✗ Mass DM** :: Invalid option. Use 1, 2, or 3")
                return
            
            status_msg = ctx["api"].send_message(ctx["channel_id"], f"> **Mass DM** :: Mode: {option_names[option]} · fetching targets...")
            
            dm_data = ctx["api"].get_dm_channels(force=False) if hasattr(ctx["api"], "get_dm_channels") else []
            if not dm_data:
                ctx["api"].edit_message(ctx["channel_id"], status_msg.get("id"), "> **✗ Mass DM** :: Failed to fetch DMs")
                return

            targets = []
            target_names = []
            target_user_ids = set()
            
            for dm in dm_data:
                if dm.get("type") == 1 and dm.get("recipients"):
                    recipient = dm["recipients"][0] if dm["recipients"] else {}
                    user_id = recipient.get("id")
                    username = recipient.get("username", "Unknown")
                    if user_id:
                        targets.append((dm["id"], user_id, username))
                        target_names.append(username)
                        target_user_ids.add(str(user_id))
            
            if option == 2 or option == 3:
                friends_data = ctx["api"].get_friends(force=False) if hasattr(ctx["api"], "get_friends") else []
                for friend in friends_data:
                    if friend.get("type") != 1:
                        continue
                    user = friend.get("user", {})
                    user_id = str(user.get("id") or "")
                    username = user.get("username", "Unknown")
                    if not user_id or user_id in target_user_ids:
                        continue
                    dm_channel = ctx["api"].create_dm(user_id)
                    if dm_channel and "id" in dm_channel:
                        targets.append((dm_channel["id"], user_id, username))
                        target_names.append(username)
                        target_user_ids.add(user_id)
            
            if not targets:
                ctx["api"].edit_message(ctx["channel_id"], status_msg.get("id"), "> **✗ Mass DM** :: No targets found")
                return
            
            sent = 0
            total = len(targets)
            failed = 0
            current_target = ""
            
            ctx["api"].edit_message(ctx["channel_id"], status_msg.get("id"), f"> **Mass DM** :: Mode: {option_names[option]} · Targets: {total} · Status: Starting · Sent: 0/{total} · Failed: 0")
            
            for i, (channel_id, user_id, username) in enumerate(targets):
                current_target = username
                result = ctx["api"].send_message(channel_id, message)
                if result:
                    sent += 1
                else:
                    failed += 1
                
                if (i + 1) % 10 == 0 or i == total - 1:
                    ctx["api"].edit_message(ctx["channel_id"], status_msg.get("id"), f"> **Mass DM** :: Mode: {option_names[option]} · Sent: {sent}/{total} · Failed: {failed} · Sending: {username}")
                
                time.sleep(random.uniform(2.5, 4.0))
            
            ctx["api"].edit_message(ctx["channel_id"], status_msg.get("id"), f"> **✓ Mass DM** :: Mode: {option_names[option]} · Sent: {sent}/{total} · Failed: {failed} · Time: {time.strftime('%H:%M:%S')}")
            
        except Exception as e:
            print(f"Mass DM error: {e}")
            msg = ctx["api"].send_message(
                ctx["channel_id"],
                f"> **Mass DM** :: Usage: {bot.prefix}massdm <1|2|3> <message> — 1=DM history  2=Friends  3=Both",
            )
    @bot.command(name="join", aliases=["acceptinvite"])
    def join_cmd(ctx, args):
        if not args:
            msg = ctx["api"].send_message(
                ctx["channel_id"],
                f"> **Join** :: Usage: {bot.prefix}join <invite_code_or_url>"
            )
            return

        # Convenience bridge: allow "join vc <channel_id>" and "join voice <channel_id>"
        # so users can use either style and still hit the VC join logic.
        if args[0].lower() in {"vc", "voice", "joinvc", "vcjoin", "joinvoice", "joincall"}:
            vc_args = args[1:]
            vc(ctx, vc_args)
            return

        invite = args[0]
        # Strip full URLs down to just the code
        if "/" in invite:
            invite = invite.rstrip("/").split("/")[-1]

        status = ctx["api"].send_message(
            ctx["channel_id"],
            f"> **Joining** {invite}..."
        )

        try:
            response = ctx["api"].request(
                "POST",
                f"/invites/{invite}",
                data={"session_id": None}
            )
            if response and response.status_code in (200, 204):
                data = response.json() if response.status_code == 200 else {}
                guild_name = (
                    data.get("guild", {}).get("name")
                    or data.get("guild_id")
                    or invite
                )
                result = f"Joined {guild_name}"
                ok = True
            else:
                code = response.status_code if response else "no response"
                err = ""
                try:
                    err = response.json().get("message", "") if response else ""
                except Exception:
                    pass
                result = f"Failed ({code}){': ' + err if err else ''}"
                ok = False
        except Exception as e:
            result = f"Error: {str(e)[:80]}"
            ok = False

        if status:
            ctx["api"].edit_message(
                ctx["channel_id"], status.get("id"),
                f"> **Join** | {result}"
            )

    @bot.command(name="block", aliases=["blockuser", "bu"])
    def block_user(ctx, args):
        if not args:
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **Block** | Usage: {bot.prefix}block <user_id> [user_id2] ...")
            return

        api = ctx["api"]
        headers = api.header_spoofer.get_protected_headers(api.token)
        blocked = []
        failed = []
        for uid in args:
            try:
                r = api.request(
                    "PUT",
                    f"/users/@me/relationships/{uid}",
                    data={"type": int(RelationshipType.Blocked)}
                )
                if r and r.status_code in (200, 204):
                    blocked.append(uid)
                else:
                    failed.append(uid)
            except Exception:
                failed.append(uid)
            time.sleep(0.3)

        parts = []
        if blocked:
            parts.append(f"Blocked: {', '.join(blocked)}")
        if failed:
            parts.append(f"Failed: {', '.join(failed)}")
        msg = api.send_message(ctx["channel_id"], "> **Block** :: " + " · ".join(parts))
    def _clear_hypesquad_badge(api):
        # Primary endpoint used by Discord for joining/leaving HypeSquad.
        resp = api.request("DELETE", "/hypesquad/online")
        # Fallback endpoint for compatibility with older implementations.
        if not resp or resp.status_code == 404:
            resp = api.request("DELETE", "/users/@me/hypesquad/online")
        if not resp:
            return False, "No response"
        if resp.status_code in (200, 204):
            return True, "Badge removed"
        if resp.status_code in (400, 404):
            return True, "Badge already removed"
        return False, f"HTTP {resp.status_code}"

    @bot.command(name="hypesquad", aliases=["changehypesquad", "hs"])
    def hypesquad_cmd(ctx, args):
        houses = {"bravery": 1, "brilliance": 2, "balance": 3}
        house = (args[0].lower() if args else "")
        if house in {"off", "leave", "remove", "none"}:
            ok, note = _clear_hypesquad_badge(ctx["api"])
            if ok:
                msg = ctx["api"].send_message(ctx["channel_id"], f"> **✓ Hypesquad** :: {note}")
            else:
                msg = ctx["api"].send_message(ctx["channel_id"], f"> **✗ Hypesquad** :: {note}")
            return

        if house not in houses:
            msg = ctx["api"].send_message(
                ctx["channel_id"],
                f"> **Hypesquad** :: Usage: {bot.prefix}hypesquad bravery/brilliance/balance/off",
            )
            return
        resp = ctx["api"].request(
            "POST",
            "/hypesquad/online",
            data={"house_id": houses[house]}
        )
        if resp and resp.status_code == 204:
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **Hypesquad** changed to **{house.title()}**")
        else:
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **Hypesquad** failed (HTTP {resp.status_code if resp else 'N/A'})")
    @bot.command(name="hypesquad_leave", aliases=["leavehypesquad", "hsl", "hypesquadleave"])
    def hypesquad_leave_cmd(ctx, args):
        ok, note = _clear_hypesquad_badge(ctx["api"])
        if ok:
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **✓ Hypesquad** :: {note}")
        else:
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **✗ Hypesquad** :: {note}")
    @bot.command(name="status", aliases=["changestatus"])
    def status_cmd_v2(ctx, args):
        import formatter as fmt
        valid = {"online", "idle", "dnd", "invisible"}
        status = (args[0].lower() if args else "")
        if status not in valid:
            cmds = [
                (f"{bot.prefix}status online",    "Set status to online"),
                (f"{bot.prefix}status idle",      "Set status to idle"),
                (f"{bot.prefix}status dnd",       "Set status to do not disturb"),
                (f"{bot.prefix}status invisible", "Set status to invisible"),
            ]
            msg = ctx["api"].send_message(
                ctx["channel_id"],
                fmt.header("Status") + "\n" + fmt.command_list(cmds),
            )
            return
        ok = ctx["bot"].set_status(status)
        result = f"Set to **{status}**" if ok else f"Saved **{status}** — applies on reconnect"
        msg = ctx["api"].send_message(ctx["channel_id"], f"> **✓ Status** :: {result}")
    @bot.command(name="client", aliases=["clienttype", "ct"])
    def client_cmd(ctx, args):
        if not is_control_user(ctx["author_id"]):
            deny_restricted_command(ctx, "Client")
            return
        import formatter as fmt
        valid = {"web", "desktop", "mobile", "vr", "off"}
        ctype = (args[0].lower() if args else "")
        labels = {
            "web":     "Web (Chrome/Linux)",
            "desktop": "Desktop (Discord Client/Windows)",
            "mobile":  "Android (Discord Android)",
            "vr":      "VR (Meta Quest 3)",
            "off":     "Mobile (VR disconnected)",
        }
        if ctype not in valid:
            current = getattr(ctx["bot"], "_client_type", "mobile")
            cmds = [
                (f"{bot.prefix}client web", "Web browser client"),
                (f"{bot.prefix}client desktop", "Desktop app client"),
                (f"{bot.prefix}client mobile", "Android mobile client"),
                (f"{bot.prefix}client vr", "Meta Quest VR client"),
                (f"{bot.prefix}client off", "Disconnect VR and switch to mobile"),
            ]
            msg = ctx["api"].send_message(
                ctx["channel_id"],
                fmt.header("Client Type") + "\n" + fmt.command_list(cmds) + "\n" +
                fmt._block(f"{fmt.CYAN}Current{fmt.DARK} :: {fmt.RESET}{fmt.WHITE}{labels.get(current, current)}{fmt.RESET}"),
            )
            return
        if ctype == "off":
            ctype = "mobile"
        ok = ctx["bot"].set_client_type(ctype)
        if ok:
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **✓ Client** :: Switched to **{labels[ctype]}** — reconnecting...")
        else:
            msg = ctx["api"].send_message(ctx["channel_id"], "> **✗ Client** :: Failed to switch client type")

    @bot.command(name="vr", aliases=["vrrpc", "vrmode"])
    def vr_cmd(ctx, args):
        if not is_control_user(ctx["author_id"]):
            deny_restricted_command(ctx, "VR")
            return

        action = (args[0].lower() if args else "status")
        current = getattr(ctx["bot"], "_client_type", "mobile")
        is_vr = current == "vr"

        if action in {"off", "disable", "disconnect", "stop"}:
            ok = ctx["bot"].set_client_type("mobile")
            if ok:
                msg = ctx["api"].send_message(
                    ctx["channel_id"],
                    "> **✓ VR** :: Disconnected VR client mode and switched to **mobile** — reconnecting...",
                )
            else:
                msg = ctx["api"].send_message(ctx["channel_id"], "> **✗ VR** :: Failed to disconnect VR client mode")
            return

        if action in {"on", "enable", "connect", "start"}:
            ok = ctx["bot"].set_client_type("vr")
            if ok:
                msg = ctx["api"].send_message(
                    ctx["channel_id"],
                    "> **✓ VR** :: Enabled **VR (Meta Quest 3)** client mode — reconnecting...",
                )
            else:
                msg = ctx["api"].send_message(ctx["channel_id"], "> **✗ VR** :: Failed to enable VR client mode")
            return

        if action in {"status", "state", "check"}:
            status_text = "ON" if is_vr else "OFF"
            mode_label = "VR (Meta Quest 3)" if is_vr else f"{current}"
            msg = ctx["api"].send_message(
                ctx["channel_id"],
                f"> **VR Status** :: **{status_text}** · Current client: **{mode_label}**\n"
                f"> Use `{bot.prefix}vr on` or `{bot.prefix}vr off`",
            )
            return

        msg = ctx["api"].send_message(
            ctx["channel_id"],
            f"> **VR** :: Usage: `{bot.prefix}vr on` · `{bot.prefix}vr off` · `{bot.prefix}vr status`",
        )
    @bot.command(name="clientsave", aliases=["saveclient", "persistclient"])
    def clientsave_cmd(ctx, args):
        _save_client_state(ctx["bot"])
        current = getattr(ctx["bot"], "_client_type", "mobile")
        msg = ctx["api"].send_message(ctx["channel_id"], f"> **✓ ClientSave** :: Saved **{current}** for restarts")
    @bot.command(name="superreact", aliases=["sr"])
    def superreact_cmd(ctx, args):
        def _normalize_target(raw):
            target = str(raw or "").strip().strip("<@!>")
            return target if target.isdigit() else None

        def _normalize_emojis(raw_tokens):
            emojis = []
            for token in raw_tokens:
                token = str(token or "").strip()
                if not token or token in {"-boost", "-super"}:
                    continue
                if token.startswith("<") and token.endswith(">"):
                    parts = token.replace("<", "").replace(">", "").split(":")
                    if len(parts) >= 3 and parts[-1].isdigit():
                        emojis.append(token)
                        continue
                    return []
                if is_valid_emoji(token):
                    emojis.append(token)
                    continue
                return []
            return emojis

        if args and str(args[0]).lower() in {"clear", "off", "remove"}:
            if len(args) >= 2:
                target_id = _normalize_target(args[1])
                if not target_id:
                    msg = ctx["api"].send_message(ctx["channel_id"], "> **✗ SuperReact** :: Invalid target.")
                    return
                super_react_client.remove_target(target_id)  # type: ignore[union-attr]
                super_react_client.remove_msr_target(target_id)  # type: ignore[union-attr]
                super_react_client.remove_ssr_target(target_id)  # type: ignore[union-attr]
                msg = ctx["api"].send_message(ctx["channel_id"], f"> **✗ SuperReact** :: Removed target <@{target_id}>.")
                return
            superreact_stop_cmd(ctx, [])
            return

        if len(args) >= 2:
            target_id = _normalize_target(args[0])
            if not target_id:
                msg = ctx["api"].send_message(ctx["channel_id"], "> **✗ SuperReact** :: Invalid user target.")
                return

            joined = " ".join(str(x) for x in args[1:])
            groups_raw = [g.strip() for g in joined.split(".") if g.strip()]
            groups = []
            for grp in groups_raw:
                tokens = _normalize_emojis(grp.split())
                if not tokens:
                    msg = ctx["api"].send_message(ctx["channel_id"], f"> **✗ SuperReact** :: Invalid emoji group: `{grp}`")
                    return
                groups.append(tokens)

            super_react_client.remove_target(target_id)  # type: ignore[union-attr]
            super_react_client.remove_msr_target(target_id)  # type: ignore[union-attr]
            super_react_client.remove_ssr_target(target_id)  # type: ignore[union-attr]

            if len(groups) <= 1:
                emojis = groups[0] if groups else _normalize_emojis(args[1:])
                if not emojis:
                    msg = ctx["api"].send_message(ctx["channel_id"], "> **✗ SuperReact** :: Invalid emoji(s).")
                    return
                if len(emojis) == 1:
                    super_react_client.add_target(target_id, emojis[0])  # type: ignore[union-attr]
                    mode = f"single ({emojis[0]})"
                else:
                    super_react_client.add_ssr_target(target_id, emojis)  # type: ignore[union-attr]
                    mode = f"multi ({' '.join(emojis)})"
            else:
                if all(len(group) == 1 for group in groups):
                    cycle = [group[0] for group in groups]
                    super_react_client.add_msr_target(target_id, cycle)  # type: ignore[union-attr]
                    mode = f"cycle ({' . '.join(cycle)})"
                else:
                    merged = []
                    for group in groups:
                        for emoji in group:
                            if emoji not in merged:
                                merged.append(emoji)
                    super_react_client.add_ssr_target(target_id, merged)  # type: ignore[union-attr]
                    mode = f"multi ({' '.join(merged)})"

            if not super_react_client.is_running():  # type: ignore[union-attr]
                super_react_client.start()  # type: ignore[union-attr]
            msg = ctx["api"].send_message(
                ctx["channel_id"],
                f"> **✓ SuperReact** :: Enabled · <@{target_id}> · {mode} · `{bot.prefix}srstop` to stop",
            )
        elif not args:
            import formatter as fmt
            if super_react_client and super_react_client.is_running():  # type: ignore[union-attr]
                status = "Running"
                targets = super_react_client.get_targets()  # type: ignore[union-attr]
                t_count = len(targets) + len(super_react_client.get_msr_targets()) + len(super_react_client.get_ssr_targets())  # type: ignore[union-attr]
            else:
                status = "Stopped"
                t_count = 0
            p = bot.prefix
            cmds = [
                (f"{p}sr <@user> <emoji>", "Add target (auto-start)"),
                (f"{p}sr <@user> e1 e2", "Set multi super-react"),
                (f"{p}sr <@user> e1 . e2 . e3", "Cycle emojis"),
                (f"{p}sr clear [user_id]", "Remove one or all"),
                (f"{p}srlist", "List targets"),
                (f"{p}srstop [user_id]", "Stop all or one target"),
            ]
            msg = ctx["api"].send_message(
                ctx["channel_id"],
                "\n".join([
                    fmt.status_box("SuperReact", {"Status": status, "Targets": t_count}),
                    fmt.command_list(cmds),
                ]),
            )
    @bot.command(name="superreactlist", aliases=["srlist"])
    def superreact_list_cmd(ctx, args):
        import formatter as fmt
        targets = super_react_client.get_targets()  # type: ignore[union-attr]
        msr_targets = super_react_client.get_msr_targets()  # type: ignore[union-attr]
        ssr_targets = super_react_client.get_ssr_targets()  # type: ignore[union-attr]
        
        if not targets and not msr_targets and not ssr_targets:
            msg = ctx["api"].send_message(
                ctx["channel_id"],
                fmt.status_box("SuperReact", {"Status": "No active targets"}),
            )
        else:
            response = ""
            if targets:
                response += "Single SuperReactions:\n"
                for target, emoji in targets.items():
                    response += f"• <@{target}> → {emoji}\n"
            
            if msr_targets:
                response += "\nCycle SuperReactions:\n"
                for target, (emojis, idx) in msr_targets.items():
                    response += f"• <@{target}> → {', '.join(emojis)} (current: {emojis[idx]})\n"
            
            if ssr_targets:
                response += "\nMulti SuperReactions:\n"
                for target, emojis in ssr_targets.items():
                    response += f"• <@{target}> → {', '.join(emojis)}\n"

            msg = ctx["api"].send_message(
                ctx["channel_id"],
                fmt.info_block("SuperReact Status", response.strip()),
            )
        
        if 'msg' in locals() and msg:
            pass

    # @bot.command(name="superreactrandom", aliases=["srrandom"])
    # def superreact_random_cmd(ctx, args):
    #     if not args:
    #         msg = ctx["api"].send_message(ctx["channel_id"], "```| SuperReact Random |\nUsage: +srrandom <message_id>```")
    #    #    #         return
    #     
    #     target_msg_id = args[0].strip()
    #     if not target_msg_id.isdigit():
    #         msg = ctx["api"].send_message(ctx["channel_id"], "```| SuperReact Random |\nError: Invalid message ID```")
    #    #    #         return
    #     
    #     msg = ctx["api"].send_message(ctx["channel_id"], f"```| SuperReact Random |\nAdding super-reactions to message {target_msg_id}...```")
    #     
    #     added_emojis = []
    #     available_emojis = super_react.emojis.copy()
    #     while len(added_emojis) < 10 and available_emojis:
    #         emoji = random.choice(available_emojis)
    #         available_emojis.remove(emoji)
    #         try:
    #             super_react.send_super_reaction(ctx["channel_id"], target_msg_id, emoji)
    #             added_emojis.append(emoji)
    #             time.sleep(0.7)
    #         except Exception as e:
    #             print(f"[ERROR]: Failed to add {emoji} to {target_msg_id}: {e}")
    #             break
    #     
    #     msg2 = ctx["api"].send_message(ctx["channel_id"], f"```| SuperReact Random |\nComplete!\nMessage: {target_msg_id}\nAdded: {', '.join(added_emojis)}\nTotal: {len(added_emojis)}```")
    #     
    #    #    #     if msg2:
    #         delete_after_delay(ctx["api"], ctx["channel_id"], msg2.get("id"))
    
    @bot.command(name="superreactstart", aliases=["srstart"])
    def superreact_start_cmd(ctx, args):
        # Merged into +superreact / +sr — kept as no-op redirect so old aliases still work
        msg = ctx["api"].send_message(ctx["channel_id"], f"> **SuperReact** :: Use `{bot.prefix}sr <@user> <emoji>` — it auto-starts now.")
        pass
    @bot.command(name="superreactstop", aliases=["srstop"])
    def superreact_stop_cmd(ctx, args):
        if args:
            target_id = str(args[0]).strip().strip("<@!>")
            if not target_id.isdigit():
                msg = ctx["api"].send_message(ctx["channel_id"], "> **✗ SuperReact** :: Invalid target.")
                return
            super_react_client.remove_target(target_id)  # type: ignore[union-attr]
            super_react_client.remove_msr_target(target_id)  # type: ignore[union-attr]
            super_react_client.remove_ssr_target(target_id)  # type: ignore[union-attr]
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **✗ SuperReact** :: Removed target <@{target_id}>.")
            return

        if super_react_client and super_react_client.is_running():
            for uid in list(super_react_client.get_targets().keys()):  # type: ignore[union-attr]
                super_react_client.remove_target(uid)  # type: ignore[union-attr]
            for uid in list(super_react_client.get_msr_targets().keys()):  # type: ignore[union-attr]
                super_react_client.remove_msr_target(uid)  # type: ignore[union-attr]
            for uid in list(super_react_client.get_ssr_targets().keys()):  # type: ignore[union-attr]
                super_react_client.remove_ssr_target(uid)  # type: ignore[union-attr]
            super_react_client.stop()
            msg = ctx["api"].send_message(ctx["channel_id"], "> **✗ SuperReact** :: Stopped.")
        else:
            msg = ctx["api"].send_message(ctx["channel_id"], "> **SuperReact** :: Not running.")

    @bot.command(name="autoreact", aliases=["ar"])
    def autoreact_cmd(ctx, args):
        def _parse_target(raw):
            target = str(raw or "").strip().strip("<@!>")
            return target if target.isdigit() else None

        def _parse_emoji_tokens(tokens):
            out = []
            for token in tokens:
                token = str(token or "").strip()
                if not token:
                    continue
                if token.startswith("<") and token.endswith(">"):
                    parts = token.replace("<", "").replace(">", "").split(":")
                    if len(parts) >= 3 and parts[-1].isdigit():
                        out.append(token)
                        continue
                    return None
                if is_valid_emoji(token):
                    out.append(token)
                    continue
                return None
            return out

        if not args:
            import formatter as fmt
            targets = getattr(bot, "_autoreact_targets", {})
            lines = []
            for uid, cfg in targets.items():
                if cfg.get("rotating"):
                    groups = [" ".join(group) for group in cfg.get("groups", [])]
                    lines.append(f"<@{uid}> -> {' . '.join(groups)}")
                else:
                    lines.append(f"<@{uid}> -> {' '.join(cfg.get('emojis', []))}")
            body = "\n".join(lines) if lines else "No active targets"
            msg = ctx["api"].send_message(
                ctx["channel_id"],
                "\n".join([
                    fmt.status_box("AutoReact", {"Targets": len(targets)}),
                    fmt.info_block("Active", body),
                    fmt.command_list([
                        (f"{bot.prefix}ar <@user> <emoji...>", "Set regular auto-reactions"),
                        (f"{bot.prefix}ar <@user> e1 . e2", "Set rotating groups"),
                        (f"{bot.prefix}ar clear [user_id]", "Clear one or all targets"),
                    ]),
                ]),
            )
            return

        sub = str(args[0]).lower()
        if sub in {"clear", "off", "remove"}:
            if len(args) >= 2:
                target_id = _parse_target(args[1])
                if not target_id:
                    msg = ctx["api"].send_message(ctx["channel_id"], "> **✗ AutoReact** :: Invalid target.")
                    return
                bot._autoreact_targets.pop(target_id, None)
                msg = ctx["api"].send_message(ctx["channel_id"], f"> **✗ AutoReact** :: Removed target <@{target_id}>.")
                return
            bot._autoreact_targets.clear()
            msg = ctx["api"].send_message(ctx["channel_id"], "> **✗ AutoReact** :: Cleared all targets.")
            return

        target_id = _parse_target(args[0])
        if not target_id:
            msg = ctx["api"].send_message(
                ctx["channel_id"],
                f"> **✗ AutoReact** :: Usage: `{bot.prefix}ar <@user|user_id> <emoji...>` or `{bot.prefix}ar <@user> e1 . e2 . e3`",
            )
            return

        raw = " ".join(str(x) for x in args[1:]).strip()
        if not raw:
            msg = ctx["api"].send_message(ctx["channel_id"], "> **✗ AutoReact** :: Provide at least one emoji.")
            return

        group_strings = [g.strip() for g in raw.split(".") if g.strip()]
        groups = []
        for group in group_strings:
            parsed = _parse_emoji_tokens(group.split())
            if not parsed:
                msg = ctx["api"].send_message(ctx["channel_id"], f"> **✗ AutoReact** :: Invalid emoji group: `{group}`")
                return
            groups.append(parsed)

        if len(groups) <= 1:
            emojis = groups[0] if groups else (_parse_emoji_tokens(args[1:]) or [])
            bot._autoreact_targets[target_id] = {
                "rotating": False,
                "emojis": emojis,
                "groups": [],
                "index": 0,
            }
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **✓ AutoReact** :: Target <@{target_id}> · {' '.join(emojis)}")
        else:
            bot._autoreact_targets[target_id] = {
                "rotating": True,
                "emojis": [],
                "groups": groups,
                "index": 0,
            }
            preview = " . ".join(" ".join(g) for g in groups)
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **✓ AutoReact** :: Target <@{target_id}> · rotation: {preview}")
    @bot.command(name="guilds")
    def list_guilds(ctx, args):
        api = ctx["api"]
        headers = api.header_spoofer.get_protected_headers(api.token)
        try:
            r = api.request(
                "GET",
                "/users/@me/guilds?with_counts=true"
            )
            guilds = r.json() if (r and r.status_code == 200) else api.get_guilds()
        except Exception:
            guilds = api.get_guilds()

        total = len(guilds)
        page = int(args[0]) if args and args[0].isdigit() else 1
        per = 15
        import math as _m
        pages = max(1, _m.ceil(total / per))
        page = min(page, pages)
        shown = guilds[(page - 1) * per: page * per]

        lines = [f"Guilds {total} total — page {page}/{pages}"]
        for g in shown:
            name = g.get("name", "?")
            gid = g.get("id", "?")
            owner = " [owner]" if g.get("owner") else ""
            mc = g.get("approximate_member_count")
            mc_str = f" | {mc}" if mc else ""
            lines.append(f"> {name}{owner}{mc_str} :: {gid}")

        msg = api.send_message(ctx["channel_id"], "```| " + " |\n".join(lines) + "```")
    @bot.command(name="setprefix", aliases=["prefix"])
    def setprefix_cmd(ctx, args):
        if not args:
            user_prefix = bot.get_user_prefix(ctx["author_id"])
            import formatter as fmt
            msg = ctx["api"].send_message(
                ctx["channel_id"],
                fmt.status_box("Prefix", {
                    "Current": user_prefix,
                    "Usage": f"{user_prefix}setprefix <symbol>",
                })
            )
            return

        new_prefix = args[0]
        if any(ch.isspace() for ch in new_prefix) or len(new_prefix) > 5:
            msg = ctx["api"].send_message(ctx["channel_id"], "> **✗ Prefix** :: Prefix must be 1-5 non-space characters.")
            return
        user_prefix = bot.get_user_prefix(ctx["author_id"])
        old_prefix = user_prefix

        # Always store under BOTH the caller's ID and the token user's ID so
        # all control accounts (owner alt, token user) see the same prefix.
        bot.set_user_prefix(ctx["author_id"], new_prefix)
        if bot.user_id and str(ctx["author_id"]) != str(bot.user_id):
            bot.set_user_prefix(str(bot.user_id), new_prefix)
        # Also update global prefix so new instances / restarts pick it up.
        bot.prefix = new_prefix
        bot.globalPrefix = new_prefix
        bot._config_prefix = new_prefix
        if isinstance(bot.config, dict):
            bot.config["prefix"] = new_prefix
        
        import formatter as fmt
        msg = ctx["api"].send_message(
            ctx["channel_id"],
            fmt.status_box("Prefix", {"Old": old_prefix, "New": new_prefix}),
        )

    @bot.command(name="autodelete", aliases=["ad"])
    def autodelete_cmd(ctx, args):
        import formatter as fmt

        enabled = bool(getattr(bot, "_auto_delete_enabled", True))
        delay = float(getattr(bot, "_auto_delete_delay", 3.0) or 3.0)

        if not args:
            msg = ctx["api"].send_message(
                ctx["channel_id"],
                fmt.status_box("Auto Delete", {
                    "Enabled": enabled,
                    "Delay": f"{delay:g}s",
                    "Usage": f"{bot.prefix}autodelete on/off | {bot.prefix}autodelete delay <seconds>",
                }),
            )
            return

        setting = str(args[0]).lower().strip()
        if setting in {"on", "off"}:
            bot._auto_delete_enabled = setting == "on"
            _save_auto_delete_state(bot)
            state_label = "enabled" if bot._auto_delete_enabled else "disabled"
            symbol = "✓" if bot._auto_delete_enabled else "✗"
            msg = ctx["api"].send_message(
                ctx["channel_id"],
                f"> **{symbol} Auto Delete** :: {state_label.capitalize()} · delay {float(getattr(bot, '_auto_delete_delay', 3.0) or 3.0):g}s",
            )
            return

        if setting == "delay":
            if len(args) < 2:
                msg = ctx["api"].send_message(
                    ctx["channel_id"],
                    f"> **Auto Delete** :: Usage: {bot.prefix}autodelete delay <seconds>",
                )
                return
            try:
                new_delay = max(0.03, float(str(args[1]).strip()))
            except Exception:
                msg = ctx["api"].send_message(
                    ctx["channel_id"],
                    f"> **Auto Delete** :: Usage: {bot.prefix}autodelete delay <seconds>",
                )
                return
            bot._auto_delete_delay = new_delay
            bot.api._default_delete_delay = new_delay
            _save_auto_delete_state(bot)
            msg = ctx["api"].send_message(
                ctx["channel_id"],
                fmt.status_box("Auto Delete", {
                    "Enabled": bool(getattr(bot, "_auto_delete_enabled", True)),
                    "Delay": f"{new_delay:g}s",
                }),
            )
            return

        msg = ctx["api"].send_message(
            ctx["channel_id"],
            f"> **Auto Delete** :: Usage: {bot.prefix}autodelete on/off | {bot.prefix}autodelete delay <seconds>",
        )

    @bot.command(name="config", aliases=["cf"])
    def config_cmd(ctx, args):
        page = 1
        if args and str(args[0]).isdigit():
            page = int(args[0])

        import formatter as fmt

        message_author = (ctx.get("message") or {}).get("author") or {}
        current_prefix = bot.get_user_prefix(ctx["author_id"])
        current_status = getattr(bot, "_current_status", "online")
        current_client = getattr(bot, "_client_type", "mobile")
        auto_delete_enabled = bool(getattr(bot, "_auto_delete_enabled", True))
        auto_delete_delay = float(getattr(bot, "_auto_delete_delay", 3.0) or 3.0)
        current_activity = dict(getattr(bot, "activity", {}) if isinstance(getattr(bot, "activity", None), dict) else {})

        sections = {
            1: ("General Settings", {
                "Username": message_author.get("username", bot.username or "Unknown"),
                "User ID": ctx.get("author_id", "?"),
                "Prefix": current_prefix,
                "Client": current_client,
            }),
            2: ("Presence Settings", {
                "Status": current_status,
                "Activity Type": current_activity.get("type", "None"),
                "Activity Name": current_activity.get("name", "Not set"),
                "Persist RPC": bool(getattr(bot, "activity_persist", False)),
            }),
            3: ("Status And Activity", {
                "Details": current_activity.get("details", "Not set"),
                "State": current_activity.get("state", "Not set"),
                "Application ID": current_activity.get("application_id", "Not set"),
                "Buttons": len(current_activity.get("buttons", []) or []),
            }),
            4: ("Rich Presence", {
                "Large Image": ((current_activity.get("assets") or {}).get("large_image", "Not set")),
                "Large Text": ((current_activity.get("assets") or {}).get("large_text", "Not set")),
                "Small Image": ((current_activity.get("assets") or {}).get("small_image", "Not set")),
                "Small Text": ((current_activity.get("assets") or {}).get("small_text", "Not set")),
            }),
            5: ("Auto Settings", {
                "Auto Delete": auto_delete_enabled,
                "Delete Delay": f"{auto_delete_delay}s",
                "Nitro Sniper": bool(getattr(bot.nitro_sniper, "enabled", False)),
                "AFK Active": bool(afk_system.is_afk(bot.user_id) if getattr(bot, "user_id", None) else False),
            }),
        }

        total_pages = len(sections)
        page = max(1, min(page, total_pages))
        title, details = sections[page]
        msg = ctx["api"].send_message(
            ctx["channel_id"],
            fmt.status_box(title, details) + "\n" + fmt._block(f"Page {page}/{total_pages}"),
        )
    @bot.command(name="customize", aliases=["theme", "ui"])
    def customize_cmd(ctx, args):
        if not args:
            help_text = """```yaml
Customization Commands:
  Theme Settings:
    debug_color    - Set debug message color
    theme          - Set UI theme (dark/light)
    font_style     - Set font family
    cursor_style   - Set cursor appearance
    
  Terminal Settings:
    terminal_mode  - Set terminal emulation
    prompt_style   - Set prompt appearance
    time_format    - Set time display (12h/24h)
    
  UI Settings:
    ui_animation   - Toggle animations
    sound_effects  - Toggle sounds
    auto_save      - Toggle auto-save
    
  Color Palette:
    $customize color background #1e1e1e
    $customize color accent #00ff00
    $customize color warning #ff9900

Usage:
  $customize set theme dark
  $customize toggle ui_animation
  $customize list
  $customize reset all```"""
            msg = ctx["api"].send_message(ctx["channel_id"], help_text)
            return
        
        if args[0].lower() == "palette":
            palette_info = """```yaml
Color Palette Elements:
  background  - Main background color
  foreground  - Text color
  accent      - Primary accent color
  warning     - Warning/alert color
  error       - Error message color
  success     - Success message color
  info        - Information color

Example:
  $customize color accent #ff00ff
  $customize color background #000000```"""
            msg = ctx["api"].send_message(ctx["channel_id"], palette_info)
            return
        
        if args[0].lower() == "terminal":
            terminal_info = """```ansi
\u001b[36mTerminal Modes Available:\u001b[0m
  • unix     - Unix/Linux style
  • windows  - Windows CMD style
  • powershell - PowerShell style
  • retro    - Retro terminal style
  • modern   - Modern terminal style

\u001b[36mPrompt Styles:\u001b[0m
  • arrow    - > 
  • dollar   - $ 
  • hash     - # 
  • custom   - Custom text

Example:
  $customize set terminal_mode retro
  $customize set prompt_style dollar```"""
            msg = ctx["api"].send_message(ctx["channel_id"], terminal_info)
            return

    @bot.command(name="terminal", aliases=["term", "shell"])
    def terminal_cmd(ctx, args):
        term_active = bot.customizer.terminal_emulation
        if not args:
            status = "✓ Active" if term_active else "✗ Inactive"
            term_info = f"""```ansi
\u001b[33mTerminal Emulation Status:\u001b[0m
  Mode: {status}
  Style: {bot.customizer.get_setting('terminal_mode')}
  Prompt: {bot.customizer.get_setting('prompt_style')}
  Time Format: {bot.customizer.get_setting('time_format')}

\u001b[33mCommands:\u001b[0m
  +terminal toggle  - Toggle terminal mode
  +terminal style   - Show current style
  +terminal time    - Show formatted time```"""
            msg = ctx["api"].send_message(ctx["channel_id"], term_info)
            return
        
        if args[0].lower() == "toggle":
            new_state = bot.customizer.toggle_terminal_mode()
            symbol = "✓" if new_state else "✗"
            label = "Enabled" if new_state else "Disabled"
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **{symbol} Terminal** :: {label} · mode: {bot.customizer.get_setting('terminal_mode')}")
            return
        
        if args[0].lower() == "style":
            import datetime
            now = datetime.datetime.now()
            if bot.customizer.get_setting('time_format') == '12h':
                time_str = now.strftime("%I:%M %p")
            else:
                time_str = now.strftime("%H:%M")
            
            style_demo = f"""```ansi
\u001b[32m{bot.customizer.get_setting('prompt_style')}\u001b[0m \u001b[36muser@bot\u001b[0m:\u001b[34m~\u001b[0m$ echo "Terminal Style Demo"
Terminal Style Demo

\u001b[32m{bot.customizer.get_setting('prompt_style')}\u001b[0m \u001b[36muser@bot\u001b[0m:\u001b[34m~\u001b[0m$ date
{now.strftime('%A, %B %d, %Y')} {time_str}

\u001b[32m{bot.customizer.get_setting('prompt_style')}\u001b[0m \u001b[36muser@bot\u001b[0m:\u001b[34m~\u001b[0m$ ```"""
            msg = ctx["api"].send_message(ctx["channel_id"], style_demo)
            return
        
        if args[0].lower() == "time":
            import datetime
            now = datetime.datetime.now()
            
            if bot.customizer.get_setting('time_format') == '12h':
                time_display = now.strftime("%I:%M:%S %p")
            else:
                time_display = now.strftime("%H:%M:%S")
            
            date_fmt = bot.customizer.get_setting('date_format') or 'dd/mm/yyyy'
            date_display = now.strftime(date_fmt.replace('dd', '%d').replace('mm', '%m').replace('yyyy', '%Y'))
            
            msg = ctx["api"].send_message(ctx["channel_id"], f"```ansi\n\u001b[35m{date_display} \u001b[33m{time_display}\u001b[0m\nTerminal Mode: {bot.customizer.get_setting('terminal_mode')}```")
            return

    @bot.command(name="ui", aliases=["interface", "settings"])
    def ui_cmd(ctx, args):
        if not args:
            settings = bot.customizer.config
            active = bot.customizer.get_active_customizations()
            
            ui_info = """```yaml
UI Configuration:
  Theme: {theme}
  Terminal Mode: {terminal_mode}
  Font: {font_style}
  Cursor: {cursor_style}
  Animations: {ui_animation}
  Sounds: {sound_effects}
  Auto-save: {auto_save}
  Time Format: {time_format}
  Date Format: {date_format}

Active Customizations: {active_count}
  {active_list}
  
Commands:
  +ui colors    - Show color palette
  +ui reset <setting> - Reset setting
  +ui save      - Save configuration```""".format(
                theme=settings['theme'],
                terminal_mode=settings['terminal_mode'],
                font_style=settings['font_style'],
                cursor_style=settings['cursor_style'],
                ui_animation='✓ On' if settings['ui_animation'] else '✗ Off',
                sound_effects='✓ On' if settings['sound_effects'] else '✗ Off',
                auto_save='✓ On' if settings['auto_save'] else '✗ Off',
                time_format=settings['time_format'],
                date_format=settings['date_format'],
                active_count=len(active),
                active_list='\n  '.join([f"• {item}" for item in active]) if active else "None"
            )
            
            msg = ctx["api"].send_message(ctx["channel_id"], ui_info)
            return
        
        if args[0].lower() == "colors":
            palette = bot.customizer.color_palette
            colors_display = """```yaml
Color Palette:
  Background:  {background}
  Foreground:  {foreground}
  Accent:      {accent}
  Warning:     {warning}
  Error:       {error}
  Success:     {success}
  Info:        {info}

Example Usage:
  $customize color accent #ff00ff
  $customize color background #000000```""".format(**palette)
            
            msg = ctx["api"].send_message(ctx["channel_id"], colors_display)
            return
        
        if args[0].lower() == "reset" and len(args) > 1:
            setting = args[1]
            if bot.customizer.reset_customization(setting):
                msg = ctx["api"].send_message(ctx["channel_id"], f"```yaml\nReset Complete:\n  Setting: {setting}\n  Status: ✓ Restored to default```")
            else:
                msg = ctx["api"].send_message(ctx["channel_id"], f"```yaml\nReset Failed:\n  Setting: {setting}\n  Status: ✗ Setting not found```")
            
            return
        
        if args[0].lower() == "save":
            try:
                import json
                with open("ui_config.json", "w") as f:
                    json.dump(bot.customizer.config, f, indent=2)
                msg = ctx["api"].send_message(ctx["channel_id"], "```yaml\nConfiguration Saved:\n  File: ui_config.json\n  Status: ✓ Success```")
            except:
                msg = ctx["api"].send_message(ctx["channel_id"], "```yaml\nSave Failed:\n  Status: ✗ Error writing file```")
            
            return
    

    @bot.command(name="mutualinfo")
    def mutualinfo(ctx, args):
        if not args:
            target_id = ctx["author_id"]
        else:
            target_id = args[0]

        guild_id = _resolve_ctx_guild_id(ctx)
        user_data, _ = _lookup_target_user(ctx["api"], target_id, guild_id=guild_id)
        if not user_data:
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **✗ Mutual Info** :: Could not find user with ID `{target_id}`.")
            return

        username = user_data.get("username", "Unknown")
        discriminator = user_data.get("discriminator", "0000")

        guilds_response = ctx["api"].request("GET", f"/users/{target_id}/guilds")
        mutual_guilds = []
        mutual_lookup_unavailable = False

        if guilds_response and guilds_response.status_code == 200:
            target_guilds = guilds_response.json()
            my_guilds = ctx["api"].get_guilds()
            my_guild_ids = [g["id"] for g in my_guilds]

            for guild in target_guilds:
                if guild["id"] in my_guild_ids:
                    mutual_guilds.append(guild["name"])
        else:
            mutual_lookup_unavailable = True

        if mutual_guilds:
            guilds_text = "\n- ".join(mutual_guilds[:10])
            if len(mutual_guilds) > 10:
                guilds_text += f"\n- ... and {len(mutual_guilds) - 10} more"

            msg_text = f"**User:** {username}#{discriminator}\nMutual Servers ({len(mutual_guilds)}):\n- {guilds_text}."
        elif mutual_lookup_unavailable:
            msg_text = f"**User:** {username}#{discriminator}\nMutual server lookup is unavailable for this user."
        else:
            msg_text = f"**User:** {username}#{discriminator}\nNo mutual servers found."
        
        msg = ctx["api"].send_message(ctx["channel_id"], msg_text)
    @bot.command(name="closedms")
    def closedms(ctx, args):
        status_msg = ctx["api"].send_message(ctx["channel_id"], "> **Close DMs** :: Fetching DM channels...")

        dm_data = ctx["api"].get_dm_channels(force=False) if hasattr(ctx["api"], "get_dm_channels") else []
        if not dm_data:
            ctx["api"].edit_message(ctx["channel_id"], status_msg.get("id"), "> **✗ Close DMs** :: Failed to fetch DMs.")
            return

        dm_channels = []
        
        for dm in dm_data:
            if dm.get("type") == 1:
                dm_channels.append(dm)
        
        if not dm_channels:
            ctx["api"].edit_message(ctx["channel_id"], status_msg.get("id"), "> **Close DMs** :: No DM channels to close.")
            return
        
        closed_count = 0
        total = len(dm_channels)
        
        ctx["api"].edit_message(ctx["channel_id"], status_msg.get("id"), f"> **Close DMs** :: Closing {total} DM channels... Closed: 0/{total}")
        
        for i, dm in enumerate(dm_channels):
            try:
                result = ctx["api"].request("DELETE", f"/channels/{dm['id']}")
                if result and result.status_code in [200, 204]:
                    closed_count += 1
                
                if (i + 1) % 10 == 0 or i == total - 1:
                    ctx["api"].edit_message(ctx["channel_id"], status_msg.get("id"), f"> **Close DMs** :: Closing {total} DM channels... Closed: {closed_count}/{total}")
                
                time.sleep(0.5)
            except:
                pass
        
        ctx["api"].edit_message(ctx["channel_id"], status_msg.get("id"), f"> **✓ Close DMs** :: Closed **{closed_count}/{total}** DMs.")
    
    @bot.command(name="setpfp", aliases=["setavatar", "spfp", "changepfp"])
    def setpfp(ctx, args):
        if not is_control_user(ctx["author_id"]):
            deny_restricted_command(ctx, "Set PFP")
            return
        if not args:
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **SetPFP** :: Usage: `{bot.prefix}setpfp <image_url>`")
            return

        image_url = args[0]
        api = ctx["api"]
        try:
            r = api.session.get(image_url, timeout=15)
            if r.status_code != 200:
                msg = api.send_message(ctx["channel_id"], f"> **✗ SetPFP** :: Failed to download image (HTTP {r.status_code})")
                return

            ct = r.headers.get("Content-Type", "").lower()
            url_lower = image_url.lower().split("?")[0]
            if "gif" in ct or url_lower.endswith(".gif"):
                fmt = "gif"
            elif "jpeg" in ct or "jpg" in ct or url_lower.endswith(".jpg") or url_lower.endswith(".jpeg"):
                fmt = "jpeg"
            elif "webp" in ct or url_lower.endswith(".webp"):
                fmt = "webp"
            else:
                fmt = "png"

            b64 = base64.b64encode(r.content).decode()
            ok, patch, err = _profile_patch(api, {"avatar": f"data:image/{fmt};base64,{b64}"}, ["/users/@me"])
            if ok:
                msg = api.send_message(ctx["channel_id"], "> **✓ SetPFP** :: Profile picture updated")
            else:
                code = patch.status_code if patch else "no response"
                msg = api.send_message(ctx["channel_id"], f"> **✗ SetPFP** :: Failed HTTP {code}{' — ' + err if err else ''}")
        except Exception as e:
            msg = api.send_message(ctx["channel_id"], f"> **✗ SetPFP** :: Error: {str(e)[:80]}")
    @bot.command(name="servercopy")
    def servercopy(ctx, args):
        global LAST_SERVER_COPY
        
        if not args:
            msg = ctx["api"].send_message(ctx["channel_id"], "> Please **provide** a **server ID** to copy.")
            return
        
        server_id = args[0]
        
        status_msg = ctx["api"].send_message(ctx["channel_id"], f"> **Fetching** server data for {server_id}...")
        
        guild_response = ctx["api"].request("GET", f"/guilds/{server_id}")
        if not guild_response or guild_response.status_code != 200:
            ctx["api"].edit_message(ctx["channel_id"], status_msg.get("id"), "> **Could** not find **server** or no **access**.")
            return
        
        guild_data = guild_response.json()
        
        copy_data = {
            "name": guild_data.get("name", "Copied Server"),
            "icon": guild_data.get("icon", None),
            "roles": [],
            "channels": [],
            "categories": [],
            "emojis": []
        }
        
        roles_response = ctx["api"].request("GET", f"/guilds/{server_id}/roles")
        if roles_response and roles_response.status_code == 200:
            roles_data = roles_response.json()
            for role in roles_data:
                if not role.get("managed", False) and role.get("name") != "@everyone":
                    copy_data["roles"].append({
                        "name": role.get("name"),
                        "color": role.get("color", 0),
                        "permissions": role.get("permissions", 0),
                        "hoist": role.get("hoist", False),
                        "mentionable": role.get("mentionable", False),
                        "position": role.get("position", 0)
                    })
        
        channels_response = ctx["api"].request("GET", f"/guilds/{server_id}/channels")
        if channels_response and channels_response.status_code == 200:
            channels_data = channels_response.json()
            for channel in channels_data:
                channel_type = channel.get("type", 0)
                if channel_type == 4:
                    copy_data["categories"].append({
                        "name": channel.get("name"),
                        "position": channel.get("position", 0),
                        "overwrites": channel.get("permission_overwrites", [])
                    })
                elif channel_type == 0:
                    copy_data["channels"].append({
                        "type": "text",
                        "name": channel.get("name"),
                        "topic": channel.get("topic", ""),
                        "nsfw": channel.get("nsfw", False),
                        "position": channel.get("position", 0),
                        "parent_id": channel.get("parent_id"),
                        "overwrites": channel.get("permission_overwrites", [])
                    })
                elif channel_type == 2:
                    copy_data["channels"].append({
                        "type": "voice",
                        "name": channel.get("name"),
                        "bitrate": channel.get("bitrate", 64000),
                        "user_limit": channel.get("user_limit", 0),
                        "position": channel.get("position", 0),
                        "parent_id": channel.get("parent_id"),
                        "overwrites": channel.get("permission_overwrites", [])
                    })
        
        emojis_response = ctx["api"].request("GET", f"/guilds/{server_id}/emojis")
        if emojis_response and emojis_response.status_code == 200:
            emojis_data = emojis_response.json()
            for emoji in emojis_data:
                if emoji.get("available", True):
                    copy_data["emojis"].append({
                        "name": emoji.get("name"),
                        "animated": emoji.get("animated", False),
                        "url": f"https://cdn.discordapp.com/emojis/{emoji['id']}.{'gif' if emoji.get('animated', False) else 'png'}"
                    })
        
        LAST_SERVER_COPY = copy_data
        
        ctx["api"].edit_message(ctx["channel_id"], status_msg.get("id"), f"> **Successfully** copied server: {guild_data.get('name', 'Unknown')}\nUse +serverload <target_id> to apply.")
    
    @bot.command(name="serverload")
    def serverload(ctx, args):
        global LAST_SERVER_COPY
        
        if not LAST_SERVER_COPY:
            msg = ctx["api"].send_message(ctx["channel_id"], "> **No server** data to load. Use **servercopy** first.")
            return
        
        if not args:
            msg = ctx["api"].send_message(ctx["channel_id"], "> Please **provide** a target server ID.")
            return
        
        target_id = args[0]
        
        status_msg = ctx["api"].send_message(ctx["channel_id"], f"> **Loading** template into server {target_id}...```")
        
        try:
            if LAST_SERVER_COPY.get("icon"):
                icon_response = ctx["api"].session.get(f"https://cdn.discordapp.com/icons/{target_id}/{LAST_SERVER_COPY['icon']}.png", timeout=10)
                if icon_response.status_code == 200:
                    icon_bytes = icon_response.content
                    icon_b64 = base64.b64encode(icon_bytes).decode()
                    icon_data = f"data:image/png;base64,{icon_b64}"
                    
                    update_data = {
                        "name": LAST_SERVER_COPY["name"],
                        "icon": icon_data
                    }
                else:
                    update_data = {"name": LAST_SERVER_COPY["name"]}
            else:
                update_data = {"name": LAST_SERVER_COPY["name"]}
            
            guild_update = ctx["api"].request("PATCH", f"/guilds/{target_id}", data=update_data)
            if not guild_update or guild_update.status_code != 200:
                ctx["api"].edit_message(ctx["channel_id"], status_msg.get("id"), "> **Failed** to update **server name/icon**.")
                return
            
            existing_channels = ctx["api"].request("GET", f"/guilds/{target_id}/channels")
            if existing_channels and existing_channels.status_code == 200:
                for channel in existing_channels.json():
                    try:
                        ctx["api"].request("DELETE", f"/channels/{channel['id']}")
                        time.sleep(0.5)
                    except:
                        pass
            
            existing_roles = ctx["api"].request("GET", f"/guilds/{target_id}/roles")
            if existing_roles and existing_roles.status_code == 200:
                for role in existing_roles.json():
                    if not role.get("managed", False) and role.get("name") != "@everyone":
                        try:
                            ctx["api"].request("DELETE", f"/guilds/{target_id}/roles/{role['id']}")
                            time.sleep(0.5)
                        except:
                            pass
            
            role_map = {}
            for role_data in LAST_SERVER_COPY["roles"]:
                try:
                    role_create = {
                        "name": role_data["name"],
                        "color": role_data["color"],
                        "permissions": str(role_data["permissions"]),
                        "hoist": role_data["hoist"],
                        "mentionable": role_data["mentionable"]
                    }
                    
                    role_response = ctx["api"].request("POST", f"/guilds/{target_id}/roles", data=role_create)
                    if role_response and role_response.status_code == 200:
                        role_map[role_data["name"]] = role_response.json()["id"]
                    
                    time.sleep(0.5)
                except:
                    pass
            
            category_map = {}
            for category_data in LAST_SERVER_COPY["categories"]:
                try:
                    category_create = {
                        "name": category_data["name"],
                        "type": 4,
                        "position": category_data["position"]
                    }
                    
                    cat_response = ctx["api"].request("POST", f"/guilds/{target_id}/channels", data=category_create)
                    if cat_response and cat_response.status_code == 200:
                        category_map[category_data["name"]] = cat_response.json()["id"]
                    
                    time.sleep(0.5)
                except:
                    pass
            
            for channel_data in LAST_SERVER_COPY["channels"]:
                try:
                    channel_create = {
                        "name": channel_data["name"],
                        "type": 0 if channel_data["type"] == "text" else 2,
                        "position": channel_data["position"],
                        "parent_id": category_map.get(channel_data.get("parent_id")) if channel_data.get("parent_id") else None
                    }
                    
                    if channel_data["type"] == "text":
                        channel_create["topic"] = channel_data.get("topic", "")
                        channel_create["nsfw"] = channel_data.get("nsfw", False)
                    elif channel_data["type"] == "voice":
                        channel_create["bitrate"] = channel_data.get("bitrate", 64000)
                        channel_create["user_limit"] = channel_data.get("user_limit", 0)
                    
                    chan_response = ctx["api"].request("POST", f"/guilds/{target_id}/channels", data=channel_create)
                    
                    time.sleep(1)
                except:
                    pass
            
            for emoji_data in LAST_SERVER_COPY["emojis"]:
                try:
                    emoji_response = ctx["api"].session.get(emoji_data["url"], timeout=10)
                    if emoji_response.status_code == 200:
                        emoji_bytes = emoji_response.content
                        emoji_b64 = base64.b64encode(emoji_bytes).decode()
                        
                        emoji_create = {
                            "name": emoji_data["name"],
                            "image": f"data:image/{'gif' if emoji_data.get('animated', False) else 'png'};base64,{emoji_b64}"
                        }
                        
                        ctx["api"].request("POST", f"/guilds/{target_id}/emojis", data=emoji_create)
                        
                        time.sleep(0.5)
                except:
                    pass
            
            LAST_SERVER_COPY = None
            
            ctx["api"].edit_message(ctx["channel_id"], status_msg.get("id"), "> **Successfully** loaded **server* template!")
            
        except Exception as e:
            ctx["api"].edit_message(ctx["channel_id"], status_msg.get("id"), f"> **✗ Server Load** :: Error: {str(e)}")
    
    @bot.command(name="rpc", aliases=["rich_presence"])
    def rich_presence(ctx, args):
        if not args:
            import formatter as fmt
            p = bot.prefix
            cmds = [
                (f"{p}rpc spotify", 'song=<name> artist=<name> album=<name> elapsed_minutes=<n> [total_minutes=<n>] [image_url=<url>]'),
                (f"{p}rpc youtube", 'title=<name> channel=<name> elapsed_minutes=<n> [total_minutes=<n>] [image_url=<url>] [>> Button >> URL]'),
                (f"{p}rpc soundcloud", 'track=<name> artist=<name> elapsed_minutes=<n> [total_minutes=<n>] [image_url=<url>] [>> Button >> URL]'),
                (f"{p}rpc youtube_music", 'title=<name> context=<name> elapsed_minutes=<n> [total_minutes=<n>] [image_url=<url>] [>> Button >> URL]'),
                (f"{p}rpc applemusic", 'title=<name> context=<name> elapsed_minutes=<n> [total_minutes=<n>] [image_url=<url>] [>> Button >> URL]'),
                (f"{p}rpc deezer", 'title=<name> context=<name> elapsed_minutes=<n> [total_minutes=<n>] [image_url=<url>] [>> Button >> URL]'),
                (f"{p}rpc tidal", 'title=<name> context=<name> elapsed_minutes=<n> [total_minutes=<n>] [image_url=<url>] [>> Button >> URL]'),
                (f"{p}rpc twitch", 'title=<name> context=<name> elapsed_minutes=<n> [total_minutes=<n>] [image_url=<url>] [>> Button >> URL]'),
                (f"{p}rpc kick", 'title=<name> context=<name> elapsed_minutes=<n> [total_minutes=<n>] [image_url=<url>] [>> Button >> URL]'),
                (f"{p}rpc netflix", 'title=<name> context=<name> elapsed_minutes=<n> [total_minutes=<n>] [image_url=<url>] [>> Button >> URL]'),
                (f"{p}rpc disneyplus", 'title=<name> context=<name> elapsed_minutes=<n> [total_minutes=<n>] [image_url=<url>] [>> Button >> URL]'),
                (f"{p}rpc primevideo", 'title=<name> context=<name> elapsed_minutes=<n> [total_minutes=<n>] [image_url=<url>] [>> Button >> URL]'),
                (f"{p}rpc plex", 'title=<name> context=<name> elapsed_minutes=<n> [total_minutes=<n>] [image_url=<url>] [>> Button >> URL]'),
                (f"{p}rpc jellyfin", 'title=<name> context=<name> elapsed_minutes=<n> [total_minutes=<n>] [image_url=<url>] [>> Button >> URL]'),
                (f"{p}rpc vscode", 'title=<name> context=<name> elapsed_minutes=<n> [total_minutes=<n>] [image_url=<url>] [>> Button >> URL]'),
                (f"{p}rpc browser", 'title=<name> context=<name> elapsed_minutes=<n> [total_minutes=<n>] [image_url=<url>] [>> Button >> URL]'),
                (f"{p}rpc listening", 'name=<name> [details=<text>] [state=<text>] [image_url=<url>] [>> Button >> URL]'),
                (f"{p}rpc streaming", 'name=<name> [details=<text>] [state=<text>] [image_url=<url>] [>> Button >> URL]'),
                (f"{p}rpc playing", 'name=<name> [details=<text>] [state=<text>] [image_url=<url>]'),
                (f"{p}rpc timer", 'name=<name> details=<text> state=<text> start=<unix> end=<unix> [image_url=<url>]'),
                (f"{p}rpc crunchyroll", 'name=<show> episode_title=<ep> elapsed_minutes=<n> total_minutes=<n> [image_url=<url>]'),
                (f"{p}rpc stop", "Clear all activities"),
            ]
            help_text = fmt.header("RPC Commands") + "\n" + fmt.command_list(cmds)
            msg = ctx["api"].send_message(ctx["channel_id"], help_text)
            return
        
        parts = args[0].lower()
        parts = REAL_RPC_ALIASES.get(parts, parts)
        remaining = " ".join(args[1:]) if len(args) > 1 else ""
        
        if parts == "stop":
            stop_rpc_keepalive(bot=bot, clear_activity=True)
            _clear_rpc_state()
            print(f"[RPC] stopped by user={ctx['author_id']}")
            msg = ctx["api"].send_message(ctx["channel_id"], "> **Cleared** all **activities**.")
            return
        
        if not remaining:
            msg = ctx["api"].send_message(ctx["channel_id"], "> **Missing** arguments.")
            return
        
        image_url = None
        button_label = None
        button_url = None
        details = None
        state = None
        name = None
        duration = ""
        current_pos = ""
        start_time = ""
        end_time = ""
        msg_text = "> **✗ RPC** :: Invalid input"
        
        main_text = remaining

        def _parse_kv_pairs(text):
            import shlex

            kv_pairs = {}
            try:
                tokens = shlex.split(text)
            except Exception:
                tokens = text.split()
            for token in tokens:
                if "=" not in token:
                    continue
                key, value = token.split("=", 1)
                kv_pairs[key.strip().lower()] = value.strip()
            return kv_pairs

        def _extract_image_url(kv_pairs, text):
            image_keys = (
                "image_url",
                "image",
                "img",
                "icon",
                "cover",
                "thumbnail",
                "thumb",
                "asset",
                "large_image",
            )
            for key in image_keys:
                value = kv_pairs.get(key)
                if value:
                    return value.strip()

            import shlex

            try:
                tokens = shlex.split(text)
            except Exception:
                tokens = text.split()

            trailing_urls = [
                token.strip()
                for token in tokens
                if "=" not in token and token.strip().startswith(("http://", "https://"))
            ]
            return trailing_urls[-1] if trailing_urls else None
        
        if ' >> ' in main_text:
            btn_split = main_text.split(' >> ')
            if len(btn_split) >= 3:
                main_text = btn_split[0].strip()
                button_label = btn_split[1].strip()
                button_url = btn_split[2].strip()
            elif len(btn_split) == 2:
                main_text = btn_split[0].strip()
                button_label = btn_split[1].strip()
                button_url = "https://discord.com"

        kv = _parse_kv_pairs(main_text)
        raw_image_url = _extract_image_url(kv, main_text)
        
        if parts == "crunchyroll":
            try:
                show_name = kv.get("name")
                episode_title = kv.get("episode_title")
                elapsed = kv.get("elapsed_minutes")
                total = kv.get("total_minutes")
                image_url = raw_image_url
                if not (show_name and episode_title and elapsed and total):
                    msg_text = f"> **Crunchyroll RPC** :: Format: name=<show> episode_title=<ep> elapsed_minutes=<n> total_minutes=<n> [image_url=<url>] — Example: {bot.prefix}rpc crunchyroll name=Solo_Leveling episode_title=Episode_12 elapsed_minutes=6 total_minutes=24"
                else:
                    elapsed_val = float(elapsed)
                    total_val = float(total)
                    send_crunchyroll_activity(bot, show_name, episode_title, elapsed_val, total_val, image_url)
                    _cr_start = time.time() - (elapsed_val * 60.0)
                    _cr_total = max(0.1, float(total_val))

                    def _refresh_crunchyroll(
                        _show=show_name,
                        _episode=episode_title,
                        _start=_cr_start,
                        _total=_cr_total,
                        _img=image_url,
                    ):
                        cyc_elapsed = ((time.time() - _start) / 60.0) % _total
                        send_crunchyroll_activity(bot, _show, _episode, cyc_elapsed, _total, _img)

                    configure_rpc_keepalive(bot, "crunchyroll", _refresh_crunchyroll)
                    _cr_fields = [f"show={show_name}", f"episode={episode_title}", f"elapsed={elapsed_val}min", f"total={total_val}min"]
                    if image_url: _cr_fields.append(f"image_url={image_url}")
                    msg_text = "> **✓ Crunchyroll RPC** :: " + " · ".join(_cr_fields)
            except Exception as e:
                msg_text = f"> **✗ Crunchyroll RPC** :: Error: {str(e)}"

        elif kv:
            if parts == "spotify":
                details = kv.get("song")
                state = kv.get("artist")
                name = kv.get("album")
                duration = kv.get("elapsed_minutes", "")
                current_pos = kv.get("total_minutes", "")
                image_url = raw_image_url or image_url
            elif parts == "youtube":
                details = kv.get("title")
                state = kv.get("channel")
                duration = kv.get("elapsed_minutes", "")
                current_pos = kv.get("total_minutes", "")
                image_url = raw_image_url or image_url
            elif parts == "soundcloud":
                details = kv.get("track")
                state = kv.get("artist")
                duration = kv.get("elapsed_minutes", "")
                current_pos = kv.get("total_minutes", "")
                image_url = raw_image_url or image_url
            elif parts in REAL_RPC_APPS:
                details = kv.get("title")
                state = kv.get("context")
                duration = kv.get("elapsed_minutes", "")
                current_pos = kv.get("total_minutes", "")
                image_url = raw_image_url or image_url
            elif parts in ["listening", "streaming", "playing"]:
                name = kv.get("name")
                details = kv.get("details")
                state = kv.get("state")
                image_url = raw_image_url or image_url
            elif parts == "timer":
                name = kv.get("name")
                details = kv.get("details")
                state = kv.get("state")
                start_time = kv.get("start", "")
                end_time = kv.get("end", "")
                image_url = raw_image_url or image_url

        elif ' | ' in main_text:
            pipe_parts = [part.strip() for part in main_text.split('|')]
            
            if parts == "spotify":
                if len(pipe_parts) >= 4:
                    song = pipe_parts[0]
                    artist = pipe_parts[1]
                    album = pipe_parts[2]
                    duration = pipe_parts[3]
                    
                    if len(pipe_parts) >= 5:
                        current_pos = pipe_parts[4]
                    if len(pipe_parts) >= 6:
                        image_url = pipe_parts[5]
                    
                    details = song
                    state = artist
                    name = album

            elif parts == "youtube":
                if len(pipe_parts) >= 3:
                    details = pipe_parts[0]  # title
                    state = pipe_parts[1]    # channel
                    duration = pipe_parts[2] # elapsed
                    if len(pipe_parts) >= 4:
                        current_pos = pipe_parts[3]  # total
                    if len(pipe_parts) >= 5:
                        image_url = pipe_parts[4]

            elif parts == "soundcloud":
                if len(pipe_parts) >= 3:
                    details = pipe_parts[0]  # track
                    state = pipe_parts[1]    # artist
                    duration = pipe_parts[2] # elapsed
                    if len(pipe_parts) >= 4:
                        current_pos = pipe_parts[3]  # total
                    if len(pipe_parts) >= 5:
                        image_url = pipe_parts[4]

            elif parts in REAL_RPC_APPS:
                if len(pipe_parts) >= 3:
                    details = pipe_parts[0]
                    state = pipe_parts[1]
                    duration = pipe_parts[2]
                    if len(pipe_parts) >= 4:
                        current_pos = pipe_parts[3]
                    if len(pipe_parts) >= 5:
                        image_url = pipe_parts[4]
            
            elif parts in ["listening", "streaming", "playing"]:
                if len(pipe_parts) >= 3:
                    details = pipe_parts[0]
                    state = pipe_parts[1]
                    name = pipe_parts[2]
                    
                    if len(pipe_parts) >= 4:
                        image_url = pipe_parts[3]
            
            elif parts == "timer":
                if len(pipe_parts) >= 5:
                    details = pipe_parts[0]
                    state = pipe_parts[1]
                    name = pipe_parts[2]
                    start_time = pipe_parts[3]
                    end_time = pipe_parts[4]
                    
                    if len(pipe_parts) >= 6:
                        image_url = pipe_parts[5]
        
        if parts == "spotify":
            try:
                if details and state and name:
                    elapsed_val = float(duration) if duration else 0.0
                    total_val = float(current_pos) if current_pos else None
                    send_spotify_listening_activity(bot, details, state, name, elapsed_val, total_val, image_url)
                    _sp_start = time.time() - (elapsed_val * 60.0)
                    _sp_total = float(total_val) if total_val is not None else None

                    def _refresh_spotify(
                        _song=details,
                        _artist=state,
                        _album=name,
                        _start=_sp_start,
                        _total=_sp_total,
                        _img=image_url,
                    ):
                        if _total is not None and _total > 0:
                            cyc_elapsed = ((time.time() - _start) / 60.0) % _total
                        else:
                            cyc_elapsed = max(0.0, (time.time() - _start) / 60.0)
                        send_spotify_listening_activity(bot, _song, _artist, _album, cyc_elapsed, _total, _img)

                    configure_rpc_keepalive(bot, "spotify", _refresh_spotify)
                    _sp_fields = [f"song={details}", f"artist={state}", f"album={name}", f"elapsed={elapsed_val}min"]
                    if total_val is not None: _sp_fields.append(f"total={total_val}min")
                    if image_url: _sp_fields.append(f"image_url={image_url}")
                    msg_text = "> **✓ Spotify RPC** :: " + " · ".join(_sp_fields)
                else:
                    msg_text = f"> **Spotify RPC** :: Format: song=<name> artist=<name> album=<name> elapsed_minutes=<n> [total_minutes=<n>] [image_url=<url>] — Example: {bot.prefix}rpc spotify song=Blinding_Lights artist=The_Weeknd album=After_Hours elapsed_minutes=1.5 total_minutes=3.5"
            except Exception as e:
                msg_text = f"> **✗ Spotify RPC** :: Error: {str(e)}"

        elif parts == "youtube":
            try:
                if details and state:
                    elapsed_val = float(duration) if duration else 0.0
                    total_val = float(current_pos) if current_pos else None
                    send_youtube_activity(bot, details, state, elapsed_val, total_val, image_url, button_label, button_url)
                    _yt_start = time.time() - (elapsed_val * 60.0)
                    _yt_total = float(total_val) if total_val is not None else None

                    def _refresh_youtube(
                        _title=details,
                        _channel=state,
                        _start=_yt_start,
                        _total=_yt_total,
                        _img=image_url,
                        _btn=button_label,
                        _url=button_url,
                    ):
                        if _total is not None and _total > 0:
                            cyc_elapsed = ((time.time() - _start) / 60.0) % _total
                        else:
                            cyc_elapsed = max(0.0, (time.time() - _start) / 60.0)
                        send_youtube_activity(bot, _title, _channel, cyc_elapsed, _total, _img, _btn, _url)

                    configure_rpc_keepalive(bot, "youtube", _refresh_youtube)
                    _yt_fields = [f"title={details}", f"channel={state}", f"elapsed={elapsed_val}min"]
                    if total_val is not None: _yt_fields.append(f"total={total_val}min")
                    if button_label: _yt_fields.append(f"button={button_label}")
                    if image_url: _yt_fields.append(f"image_url={image_url}")
                    msg_text = "> **✓ YouTube RPC** :: " + " · ".join(_yt_fields)
                else:
                    msg_text = f"> **YouTube RPC** :: Format: title=<name> channel=<name> elapsed_minutes=<n> [total_minutes=<n>] [image_url=<url>] [>> Button >> URL] — Example: {bot.prefix}rpc youtube title=Devlog_12 channel=Aria_Channel elapsed_minutes=2.5"
            except Exception as e:
                msg_text = f"> **✗ YouTube RPC** :: Error: {str(e)}"

        elif parts == "soundcloud":
            try:
                if details and state:
                    elapsed_val = float(duration) if duration else 0.0
                    total_val = float(current_pos) if current_pos else None
                    send_soundcloud_activity(bot, details, state, elapsed_val, total_val, image_url, button_label, button_url)
                    _sc_start = time.time() - (elapsed_val * 60.0)
                    _sc_total = float(total_val) if total_val is not None else None

                    def _refresh_soundcloud(
                        _track=details,
                        _artist=state,
                        _start=_sc_start,
                        _total=_sc_total,
                        _img=image_url,
                        _btn=button_label,
                        _url=button_url,
                    ):
                        if _total is not None and _total > 0:
                            cyc_elapsed = ((time.time() - _start) / 60.0) % _total
                        else:
                            cyc_elapsed = max(0.0, (time.time() - _start) / 60.0)
                        send_soundcloud_activity(bot, _track, _artist, cyc_elapsed, _total, _img, _btn, _url)

                    configure_rpc_keepalive(bot, "soundcloud", _refresh_soundcloud)
                    _sc_fields = [f"track={details}", f"artist={state}", f"elapsed={elapsed_val}min"]
                    if total_val is not None: _sc_fields.append(f"total={total_val}min")
                    if button_label: _sc_fields.append(f"button={button_label}")
                    if image_url: _sc_fields.append(f"image_url={image_url}")
                    msg_text = "> **✓ SoundCloud RPC** :: " + " · ".join(_sc_fields)
                else:
                    msg_text = f"> **SoundCloud RPC** :: Format: track=<name> artist=<name> elapsed_minutes=<n> [total_minutes=<n>] [image_url=<url>] — Example: {bot.prefix}rpc soundcloud track=Track_Name artist=Artist_Name elapsed_minutes=1.2"
            except Exception as e:
                msg_text = f"> **✗ SoundCloud RPC** :: Error: {str(e)}"

        elif parts in REAL_RPC_APPS:
            try:
                cfg = REAL_RPC_APPS[parts]
                app_label = cfg["name"]
                if details and state:
                    elapsed_val = float(duration) if duration else 0.0
                    total_val = float(current_pos) if current_pos else None
                    send_real_app_activity(bot, parts, details, state, elapsed_val, total_val, image_url, button_label, button_url)
                    _app_start = time.time() - (elapsed_val * 60.0)
                    _app_total = float(total_val) if total_val is not None else None

                    def _refresh_real_app(
                        _mode=parts,
                        _title=details,
                        _state=state,
                        _start=_app_start,
                        _total=_app_total,
                        _img=image_url,
                        _btn=button_label,
                        _url=button_url,
                    ):
                        if _total is not None and _total > 0:
                            cyc_elapsed = ((time.time() - _start) / 60.0) % _total
                        else:
                            cyc_elapsed = max(0.0, (time.time() - _start) / 60.0)
                        send_real_app_activity(bot, _mode, _title, _state, cyc_elapsed, _total, _img, _btn, _url)

                    configure_rpc_keepalive(bot, parts, _refresh_real_app)
                    _app_fields = [f"title={details}", f"context={state}", f"elapsed={elapsed_val}min"]
                    if total_val is not None: _app_fields.append(f"total={total_val}min")
                    if button_label: _app_fields.append(f"button={button_label}")
                    if image_url: _app_fields.append(f"image_url={image_url}")
                    msg_text = f"> **✓ {app_label} RPC** :: " + " · ".join(_app_fields)
                else:
                    msg_text = f"> **{app_label} RPC** :: Format: title=<name> context=<name> elapsed_minutes=<n> [total_minutes=<n>] [image_url=<url>] — Example: {bot.prefix}rpc {parts} title=Title_Here context=Context_Here elapsed_minutes=3.5"
            except Exception as e:
                msg_text = f"> **✗ RPC** :: Error ({parts}): {str(e)}"

        elif parts == "listening":
            try:
                if name:
                    send_listening_activity(bot, name, button_label, button_url, image_url, state, details)

                    def _refresh_listening(
                        _name=name,
                        _btn=button_label,
                        _url=button_url,
                        _img=image_url,
                        _state=state,
                        _details=details,
                    ):
                        send_listening_activity(bot, _name, _btn, _url, _img, _state, _details)

                    configure_rpc_keepalive(bot, "listening", _refresh_listening)
                    _li_fields = [f"name={name}"]
                    if details: _li_fields.append(f"details={details}")
                    if state: _li_fields.append(f"state={state}")
                    if button_label: _li_fields.append(f"button={button_label}")
                    if image_url: _li_fields.append(f"image_url={image_url}")
                    msg_text = "> **✓ Listening RPC** :: " + " · ".join(_li_fields)
                else:
                    msg_text = f"> **Listening RPC** :: Format: name=<name> [details=<text>] [state=<text>] [image_url=<url>] [>> Button >> URL] — Example: {bot.prefix}rpc listening name=Spotify"
            except Exception as e:
                msg_text = f"> **✗ Listening RPC** :: Error: {str(e)}"

        elif parts == "streaming":
            try:
                if name:
                    send_streaming_activity(bot, name, button_label, button_url, image_url, state, details)

                    def _refresh_streaming(
                        _name=name,
                        _btn=button_label,
                        _url=button_url,
                        _img=image_url,
                        _state=state,
                        _details=details,
                    ):
                        send_streaming_activity(bot, _name, _btn, _url, _img, _state, _details)

                    configure_rpc_keepalive(bot, "streaming", _refresh_streaming)
                    _st_fields = [f"name={name}"]
                    if details: _st_fields.append(f"details={details}")
                    if state: _st_fields.append(f"state={state}")
                    if button_label: _st_fields.append(f"button={button_label}")
                    if image_url: _st_fields.append(f"image_url={image_url}")
                    msg_text = "> **✓ Streaming RPC** :: " + " · ".join(_st_fields)
                else:
                    msg_text = f"> **Streaming RPC** :: Format: name=<name> [details=<text>] [state=<text>] [image_url=<url>] [>> Button >> URL] — Example: {bot.prefix}rpc streaming name=Twitch"
            except Exception as e:
                msg_text = f"> **✗ Streaming RPC** :: Error: {str(e)}"

        elif parts == "playing":
            try:
                if name:
                    send_playing_activity(bot, name, button_label, button_url, image_url, state, details)

                    def _refresh_playing(
                        _name=name,
                        _btn=button_label,
                        _url=button_url,
                        _img=image_url,
                        _state=state,
                        _details=details,
                    ):
                        send_playing_activity(bot, _name, _btn, _url, _img, _state, _details)

                    configure_rpc_keepalive(bot, "playing", _refresh_playing)
                    _pl_fields = [f"name={name}"]
                    if details: _pl_fields.append(f"details={details}")
                    if state: _pl_fields.append(f"state={state}")
                    if button_label: _pl_fields.append(f"button={button_label}")
                    if image_url: _pl_fields.append(f"image_url={image_url}")
                    msg_text = "> **✓ Playing RPC** :: " + " · ".join(_pl_fields)
                else:
                    msg_text = f"> **Playing RPC** :: Format: name=<name> [details=<text>] [state=<text>] [image_url=<url>] — Example: {bot.prefix}rpc playing name=World_of_Warcraft"
            except Exception as e:
                msg_text = f"> **✗ Playing RPC** :: Error: {str(e)}"

        elif parts == "timer":
            try:
                if name and start_time and end_time:
                    start_val = float(start_time) if start_time else time.time()
                    end_val = float(end_time) if end_time else time.time() + 3600
                    send_timer_activity(bot, name, start_val, end_val, details, state, image_url)
                    timer_duration = max(60.0, end_val - start_val)

                    def _refresh_timer(
                        _name=name,
                        _dur=timer_duration,
                        _details=details,
                        _state=state,
                        _img=image_url,
                    ):
                        now = time.time()
                        send_timer_activity(bot, _name, now, now + _dur, _details, _state, _img)

                    configure_rpc_keepalive(bot, "timer", _refresh_timer)
                    duration_min = int((end_val - start_val) / 60)
                    _tm_fields = [f"name={name}", f"duration={duration_min}min"]
                    if details: _tm_fields.append(f"details={details}")
                    if state: _tm_fields.append(f"state={state}")
                    if image_url: _tm_fields.append(f"image_url={image_url}")
                    msg_text = "> **✓ Timer RPC** :: " + " · ".join(_tm_fields)
                else:
                    msg_text = f"> **Timer RPC** :: Format: name=<name> details=<text> state=<text> start=<unix> end=<unix> [image_url=<url>] — Example: {bot.prefix}rpc timer name=Gym details=Workout_session"
            except Exception as e:
                msg_text = f"> **✗ Timer RPC** :: Error: {str(e)}"

        elif parts == "crunchyroll":
            pass

        else:
            valid_types = [
                "spotify", "youtube", "soundcloud",
                "youtube_music", "applemusic", "deezer", "tidal",
                "twitch", "kick",
                "netflix", "disneyplus", "primevideo", "plex", "jellyfin", "vscode", "browser",
                "listening", "streaming", "playing", "timer", "crunchyroll",
            ]
            msg_text = "> **✗ RPC** :: Invalid type. Use: " + ", ".join(valid_types)

        msg = ctx["api"].send_message(ctx["channel_id"], msg_text)
    @bot.command(name="rpcsave", aliases=["saverpc", "persistrpc"])
    def rpcsave_cmd(ctx, args):
        if not isinstance(getattr(ctx["bot"], "activity", None), dict):
            msg = ctx["api"].send_message(ctx["channel_id"], "> **✗ RPCSave** :: No active RPC to save")
            return
        if _save_rpc_state(ctx["bot"]):
            mode = str(RPC_KEEPALIVE.get("mode") or "custom")
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **✓ RPCSave** :: Saved active RPC (**{mode}**) for restarts")
        else:
            msg = ctx["api"].send_message(ctx["channel_id"], "> **✗ RPCSave** :: Failed to save RPC state")

    @bot.command(name="rpcclear", aliases=["clearrpc", "rpcreset"])
    def rpcclear_cmd(ctx, args):
        stop_rpc_keepalive(bot=ctx["bot"], clear_activity=True)
        _clear_rpc_state()
        msg = ctx["api"].send_message(ctx["channel_id"], "> **✓ RPCClear** :: Cleared active and saved RPC state")
    @bot.command(name="setserverpfp", aliases=["serverspfp", "guildpfp", "setguildpfp", "sserverpfp"])
    def setserverpfp(ctx, args):
        if not is_control_user(ctx["author_id"]):
            deny_restricted_command(ctx, "Set Server PFP")
            return
        if not args:
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **SetServerPFP** :: Usage: `{bot.prefix}setserverpfp <image_url>`")
            return

        guild_id = _resolve_ctx_guild_id(ctx)
        if not guild_id:
            msg = ctx["api"].send_message(ctx["channel_id"], "> **✗ SetServerPFP** :: Must be used in a server")
            return

        image_url = args[0]
        api = ctx["api"]
        try:
            r = api.session.get(image_url, timeout=15)
            if r.status_code != 200:
                msg = api.send_message(ctx["channel_id"], f"> **✗ SetServerPFP** :: Failed to download (HTTP {r.status_code})")
                return

            ct = r.headers.get("Content-Type", "").lower()
            url_lower = image_url.lower().split("?")[0]
            if "gif" in ct or url_lower.endswith(".gif"):
                fmt = "gif"
            elif "jpeg" in ct or "jpg" in ct or url_lower.endswith(".jpg") or url_lower.endswith(".jpeg"):
                fmt = "jpeg"
            elif "webp" in ct or url_lower.endswith(".webp"):
                fmt = "webp"
            else:
                fmt = "png"

            b64 = base64.b64encode(r.content).decode()
            ok, patch, err = _patch_with_retry(api, f"/guilds/{guild_id}/members/@me", {"avatar": f"data:image/{fmt};base64,{b64}"}, retries=2)
            if ok:
                msg = api.send_message(ctx["channel_id"], "> **✓ SetServerPFP** :: Server profile picture updated")
            else:
                code = patch.status_code if patch else "no response"
                msg = api.send_message(ctx["channel_id"], f"> **✗ SetServerPFP** :: Failed HTTP {code}{' — ' + err if err else ''} (Nitro required)")
        except Exception as e:
            msg = api.send_message(ctx["channel_id"], f"> **✗ SetServerPFP** :: Error: {str(e)[:80]}")
    @bot.command(name="setserverbanner", aliases=["ssb", "setguildbanner", "sserverbanner"])
    def setserverbanner(ctx, args):
        if not is_control_user(ctx["author_id"]):
            deny_restricted_command(ctx, "Set Server Banner")
            return
        if not args:
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **Set Server Banner** :: Usage: {bot.prefix}setserverbanner <image_url> (Nitro required)")
            return

        guild_id = _resolve_ctx_guild_id(ctx)
        if not guild_id:
            msg = ctx["api"].send_message(ctx["channel_id"], "> **✗ Set Server Banner** :: Must be used in a server")
            return

        image_url = args[0]
        api = ctx["api"]
        try:
            r = api.session.get(image_url, timeout=15)
            if r.status_code != 200:
                msg = api.send_message(ctx["channel_id"], f"> **✗ Set Server Banner** :: Failed to download image (HTTP {r.status_code})")
                return

            ct = r.headers.get("Content-Type", "").lower()
            url_lower = image_url.lower().split("?")[0]
            if "gif" in ct or url_lower.endswith(".gif"):
                fmt = "gif"
            elif "jpeg" in ct or "jpg" in ct or url_lower.endswith(".jpg") or url_lower.endswith(".jpeg"):
                fmt = "jpeg"
            elif "webp" in ct or url_lower.endswith(".webp"):
                fmt = "webp"
            else:
                fmt = "png"

            b64 = base64.b64encode(r.content).decode()
            ok, patch, err = _patch_with_retry(api, f"/guilds/{guild_id}/members/@me", {"banner": f"data:image/{fmt};base64,{b64}"}, retries=2)
            if ok:
                msg = api.send_message(ctx["channel_id"], "> **✓ Set Server Banner** :: Server banner updated")
            else:
                code = patch.status_code if patch else "no response"
                msg = api.send_message(ctx["channel_id"], f"> **✗ Set Server Banner** :: Failed: HTTP {code}{' — ' + err if err else ''} (Nitro required)")
        except Exception as e:
            msg = api.send_message(ctx["channel_id"], f"> **✗ Set Server Banner** :: Error: {str(e)[:80]}")
    @bot.command(name="stealpfp", aliases=["copypfp", "takepfp"])
    def stealpfp(ctx, args):
        # Usage: +stealpfp <user_id|@mention> [server]
        if not args:
            msg = ctx["api"].send_message(ctx["channel_id"],
                f"> **StealPFP** :: Usage: `{bot.prefix}stealpfp <user_id> [server]`")
            return

        raw = args[0].strip("<@!>")
        user_id = raw if raw.isdigit() else args[0]
        server_mode = len(args) >= 2 and args[1].lower() in ("server", "guild", "s", "g")
        guild_id = _resolve_ctx_guild_id(ctx)

        api = ctx["api"]

        try:
            if server_mode:
                # --- steal their server avatar ---
                if not guild_id:
                    msg = api.send_message(ctx["channel_id"], "> **✗ StealPFP** :: Must be in a server for server mode")
                    return
                member_r = api.request("GET", f"/guilds/{guild_id}/members/{user_id}")
                if not member_r or member_r.status_code != 200:
                    msg = api.send_message(ctx["channel_id"], f"> **✗ StealPFP** :: Could not fetch member {user_id} in this server")
                    return
                member_data = member_r.json()
                avatar_hash = member_data.get("avatar")
                if not avatar_hash:
                    # Fall back to their global avatar
                    user_data = member_data.get("user", {})
                    avatar_hash = user_data.get("avatar")
                    target_name = user_data.get("username", user_id)
                    if not avatar_hash:
                        msg = api.send_message(ctx["channel_id"], f"> **✗ StealPFP** :: {target_name} has no server or global avatar")
                        return
                    avatar_url = f"https://cdn.discordapp.com/avatars/{user_id}/{avatar_hash}.png?size=1024"
                    fallback_note = " (no server avatar, used global)"
                else:
                    user_data = member_data.get("user", {})
                    target_name = user_data.get("username", user_id)
                    avatar_url = f"https://cdn.discordapp.com/guilds/{guild_id}/users/{user_id}/avatars/{avatar_hash}.png?size=1024"
                    fallback_note = ""

                img_r = api.session.get(avatar_url, timeout=10)
                if img_r.status_code != 200:
                    msg = api.send_message(ctx["channel_id"], f"> **✗ StealPFP** :: Failed to download image (HTTP {img_r.status_code})")
                    return

                b64 = base64.b64encode(img_r.content).decode()
                ok, patch, err = _profile_patch(api, {"avatar": f"data:image/png;base64,{b64}"}, ["/users/@me"])
                if ok:
                    msg = api.send_message(ctx["channel_id"],
                        f"> **✓ StealPFP** :: Applied **{target_name}**'s avatar to your account{fallback_note}")
                else:
                    code = patch.status_code if patch else "no response"
                    msg = api.send_message(ctx["channel_id"],
                        f"> **✗ StealPFP** :: Failed to set account avatar (HTTP {code}){': ' + err if err else ''}")

            else:
                # --- steal their global avatar ---
                user_data, _ = _lookup_target_user(api, user_id, guild_id=guild_id)
                if not user_data:
                    msg = api.send_message(ctx["channel_id"], f"> **✗ StealPFP** :: User not found: {user_id}")
                    return
                avatar_hash = user_data.get("avatar")
                target_name = user_data.get("username", user_id)
                if not avatar_hash:
                    msg = api.send_message(ctx["channel_id"], f"> **✗ StealPFP** :: **{target_name}** has no avatar")
                    return

                avatar_url = f"https://cdn.discordapp.com/avatars/{user_id}/{avatar_hash}.png?size=1024"

                img_r = api.session.get(avatar_url, timeout=10)
                if img_r.status_code != 200:
                    msg = api.send_message(ctx["channel_id"], f"> **✗ StealPFP** :: Failed to download image (HTTP {img_r.status_code})")
                    return

                b64 = base64.b64encode(img_r.content).decode()
                ok, patch, err = _profile_patch(api, {"avatar": f"data:image/png;base64,{b64}"}, ["/users/@me"])
                if ok:
                    msg = api.send_message(ctx["channel_id"],
                        f"> **✓ StealPFP** :: Stole **{target_name}**'s avatar")
                else:
                    code = patch.status_code if patch else "no response"
                    msg = api.send_message(ctx["channel_id"],
                        f"> **✗ StealPFP** :: Failed to set avatar (HTTP {code}){': ' + err if err else ''}")

        except Exception as e:
            msg = api.send_message(ctx["channel_id"], f"> **✗ StealPFP** :: Error: {str(e)[:80]}")

    @bot.command(name="setbanner", aliases=["sbanner", "changebanner"])
    def setbanner(ctx, args):
        if not is_control_user(ctx["author_id"]):
            deny_restricted_command(ctx, "Set Banner")
            return
        if not args:
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **SetBanner** :: Usage: `{bot.prefix}setbanner <image_url>`")
            return

        image_url = args[0]
        api = ctx["api"]
        try:
            r = api.session.get(image_url, timeout=15)
            if r.status_code != 200:
                msg = api.send_message(ctx["channel_id"], f"> **✗ SetBanner** :: Failed to download (HTTP {r.status_code})")
                return

            ct = r.headers.get("Content-Type", "").lower()
            url_lower = image_url.lower().split("?")[0]
            if "gif" in ct or url_lower.endswith(".gif"):
                fmt = "gif"
            elif "jpeg" in ct or "jpg" in ct or url_lower.endswith(".jpg") or url_lower.endswith(".jpeg"):
                fmt = "jpeg"
            elif "webp" in ct or url_lower.endswith(".webp"):
                fmt = "webp"
            else:
                fmt = "png"

            b64 = base64.b64encode(r.content).decode()
            ok, patch, err = _profile_patch(api, {"banner": f"data:image/{fmt};base64,{b64}"}, ["/users/@me"])
            if ok:
                msg = api.send_message(ctx["channel_id"], "> **✓ SetBanner** :: Banner updated")
            else:
                code = patch.status_code if patch else "no response"
                msg = api.send_message(ctx["channel_id"], f"> **✗ SetBanner** :: Failed HTTP {code}{' — ' + err if err else ''} (Nitro required)")
        except Exception as e:
            msg = api.send_message(ctx["channel_id"], f"> **✗ SetBanner** :: Error: {str(e)[:80]}")
    @bot.command(name="stealbanner", aliases=["copybanner", "takebanner"])
    def stealbanner(ctx, args):
        # Usage: +stealbanner <user_id|@mention>
        if not args:
            msg = ctx["api"].send_message(ctx["channel_id"],
                f"> **StealBanner** :: Usage: `{bot.prefix}stealbanner <user_id>`")
            return

        raw = args[0].strip("<@!>")
        user_id = raw if raw.isdigit() else args[0]
        api = ctx["api"]
        guild_id = _resolve_ctx_guild_id(ctx)

        try:
            banner_hash = None
            target_name = user_id

            profile_data, user_obj, _ = _lookup_target_profile(api, user_id, guild_id=guild_id)
            if user_obj:
                target_name = user_obj.get("username", user_id)
                banner_hash = user_obj.get("banner")
            if profile_data and not banner_hash:
                banner_hash = (profile_data.get("user_profile") or {}).get("banner")

            if not banner_hash:
                msg = api.send_message(ctx["channel_id"],
                    f"> **✗ StealBanner** :: **{target_name}** has no banner")
                return

            banner_url = f"https://cdn.discordapp.com/banners/{user_id}/{banner_hash}.png?size=1024"

            img_r = api.session.get(banner_url, timeout=10)
            if img_r.status_code != 200:
                msg = api.send_message(ctx["channel_id"],
                    f"> **✗ StealBanner** :: Failed to download (HTTP {img_r.status_code})")
                return

            b64 = base64.b64encode(img_r.content).decode()
            ok, patch, err = _profile_patch(api, {"banner": f"data:image/png;base64,{b64}"}, ["/users/@me"])
            if ok:
                msg = api.send_message(ctx["channel_id"],
                    f"> **✓ StealBanner** :: Stole **{target_name}**'s banner")
            else:
                code = patch.status_code if patch else "no response"
                msg = api.send_message(ctx["channel_id"],
                    f"> **✗ StealBanner** :: Failed (HTTP {code}){': ' + err if err else ''}")

        except Exception as e:
            msg = api.send_message(ctx["channel_id"], f"> **✗ StealBanner** :: Error: {str(e)[:80]}")

    @bot.command(name="pronouns")
    def pronouns(ctx, args):
        if not args:
            target_id = ctx["author_id"]
        else:
            target_id = args[0]

        try:
            profile_data, _, _ = _lookup_target_profile(ctx["api"], target_id, guild_id=_resolve_ctx_guild_id(ctx))
            if not profile_data:
                msg = ctx["api"].send_message(ctx["channel_id"], "> **✗ Pronouns** :: Could not fetch user profile.")
                return
            user_profile = profile_data.get("user_profile", {})
            pronouns = user_profile.get("pronouns", "")

            if pronouns:
                msg = ctx["api"].send_message(ctx["channel_id"], f"> **Pronouns** :: **{pronouns}**")
            else:
                msg = ctx["api"].send_message(ctx["channel_id"], "> **Pronouns** :: No pronouns set.")

        except Exception as e:
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **✗ Pronouns** :: Error: {str(e)[:80]}")

    @bot.command(name="displayname", aliases=["globalname", "whoisname", "dn"])
    def displayname(ctx, args):
        if not args:
            target_id = ctx["author_id"]
        else:
            target_id = args[0]

        try:
            user_data, _ = _lookup_target_user(ctx["api"], target_id, guild_id=_resolve_ctx_guild_id(ctx))
            if not user_data:
                msg = ctx["api"].send_message(ctx["channel_id"], "> **✗ Display Name** :: Could not find user.")
                return

            username = user_data.get("username", "Unknown")
            global_name = user_data.get("global_name", "")

            if global_name:
                msg = ctx["api"].send_message(ctx["channel_id"], f"> **Display Name** :: **{username}** — {global_name}")
            else:
                msg = ctx["api"].send_message(ctx["channel_id"], f"> **Display Name** :: **{username}** has no display name set.")

        except Exception as e:
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **✗ Display Name** :: Error: {str(e)[:80]}")
    @bot.command(name="setdisplayname", aliases=["setglobalname", "setname", "changename", "setdn"])
    def setdisplayname(ctx, args):
        if not is_control_user(ctx["author_id"]):
            deny_restricted_command(ctx, "Set Display Name")
            return
        if not args:
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **SetName** :: Usage: `{bot.prefix}setname <display name>`")
            return

        display_name = " ".join(args)
        api = ctx["api"]
        try:
            ok, patch, err = _profile_patch(api, {"global_name": display_name}, ["/users/@me"])
            if ok:
                msg = api.send_message(ctx["channel_id"], f"> **✓ SetName** :: Display name set to **{display_name}**")
            else:
                code = patch.status_code if patch else "no response"
                msg = api.send_message(ctx["channel_id"], f"> **✗ SetName** :: Failed HTTP {code}{' — ' + err if err else ''}")
        except Exception as e:
            msg = api.send_message(ctx["channel_id"], f"> **✗ SetName** :: Error: {str(e)[:80]}")
    @bot.command(name="stealname", aliases=["copyname"])
    def stealname(ctx, args):
        # Usage: +stealname <user_id|@mention> [server]
        # 'server' flag steals their server nickname and applies as your server nickname in this guild
        if not args:
            msg = ctx["api"].send_message(ctx["channel_id"],
                f"> **StealName** :: Usage: `{bot.prefix}stealname <user_id> [server]`")
            return

        raw = args[0].strip("<@!>")
        user_id = raw if raw.isdigit() else args[0]
        server_mode = len(args) >= 2 and args[1].lower() in ("server", "guild", "s", "g")
        guild_id = _resolve_ctx_guild_id(ctx)
        api = ctx["api"]

        try:
            if server_mode:
                if not guild_id:
                    msg = api.send_message(ctx["channel_id"], "> **✗ StealName** :: Must be in a server for server mode")
                    return
                member_r = api.request("GET", f"/guilds/{guild_id}/members/{user_id}")
                if not member_r or member_r.status_code != 200:
                    msg = api.send_message(ctx["channel_id"], f"> **✗ StealName** :: Could not find member {user_id} in this server")
                    return
                member_data = member_r.json()
                nick = member_data.get("nick")
                target_name = (member_data.get("user") or {}).get("username", user_id)
                if not nick:
                    msg = api.send_message(ctx["channel_id"],
                        f"> **✗ StealName** :: **{target_name}** has no server nickname")
                    return
                patch = api.request("PATCH", f"/guilds/{guild_id}/members/@me",
                                    data={"nick": nick})
                if patch and patch.status_code in (200, 204):
                    msg = api.send_message(ctx["channel_id"],
                        f"> **✓ StealName** :: Set nickname to **{nick}** (from {target_name})")
                else:
                    code = patch.status_code if patch else "no response"
                    msg = api.send_message(ctx["channel_id"],
                        f"> **✗ StealName** :: Failed to set nickname (HTTP {code})")
            else:
                user_data, _ = _lookup_target_user(api, user_id, guild_id=guild_id)
                if not user_data:
                    msg = api.send_message(ctx["channel_id"], f"> **✗ StealName** :: User not found: {user_id}")
                    return
                global_name = user_data.get("global_name") or ""
                target_name = user_data.get("username", user_id)
                if not global_name:
                    msg = api.send_message(ctx["channel_id"],
                        f"> **✗ StealName** :: **{target_name}** has no display name set")
                    return
                ok, patch, err = _profile_patch(api, {"global_name": global_name}, ["/users/@me"])
                if ok:
                    msg = api.send_message(ctx["channel_id"],
                        f"> **✓ StealName** :: Set display name to **{global_name}** (from {target_name})")
                else:
                    code = patch.status_code if patch else "no response"
                    msg = api.send_message(ctx["channel_id"],
                        f"> **✗ StealName** :: Failed to set display name (HTTP {code}){': ' + err if err else ''}")

        except Exception as e:
            msg = api.send_message(ctx["channel_id"], f"> **✗ StealName** :: Error: {str(e)[:80]}")

    @bot.command(name="stop", aliases=["exit", "quit"])
    def stop_bot(ctx, args):
        msg = ctx["api"].send_message(ctx["channel_id"], "`Stopping bot...```")
        bot.stop()

    @bot.command(name="hardstop", aliases=["forcestop", "killbot", "halt"])
    def hardstop_bot(ctx, args):
        if not is_strict_owner_user(ctx["author_id"]):
            deny_restricted_command(ctx, "HardStop")
            return

        ctx["api"].send_message(ctx["channel_id"], "> **HardStop** :: Force stopping process now...")

        def _force_exit():
            time.sleep(0.35)
            os._exit(0)

        threading.Thread(target=_force_exit, daemon=True).start()
    @bot.command(name="setstatus", aliases=["customstatus"])
    def setstatus(ctx, args):
        if not args:
            msg = ctx["api"].send_message(
                ctx["channel_id"],
                f"> **SetStatus** :: Usage: `{bot.prefix}setstatus [emoji,] <text>` (custom status)\n> **Presence** :: Use `{bot.prefix}status online|idle|dnd|invisible`",
            )
            return
        
        import re
        
        full_text = " ".join(args)
        emoji_name = None
        emoji_id = None
        message = full_text.strip()
        
        if ',' in message:
            parts = message.split(',', 1)
            emoji_part = parts[0].strip()
            text_part = parts[1].strip() if len(parts) > 1 else ""
            
            if not text_part:
                msg = ctx["api"].send_message(ctx["channel_id"], "> **✗ SetStatus** :: Provide status text after the comma")
                return
            
            custom_emoji_pattern = r"<:([a-zA-Z0-9_]+):([0-9]+)>"
            custom_emoji_match = re.match(custom_emoji_pattern, emoji_part)
            
            if custom_emoji_match:
                emoji_name = custom_emoji_match.group(1)
                emoji_id = custom_emoji_match.group(2)
            
            elif len(emoji_part) == 1 or (len(emoji_part) > 1 and any(ord(c) > 127 for c in emoji_part)):
                emoji_name = emoji_part
            
            else:
                msg = ctx["api"].send_message(ctx["channel_id"], "> **✗ SetStatus** :: Invalid emoji — use standard emoji or `<:name:id>`")
                return
            
            message = text_part
        
        if not message:
            msg = ctx["api"].send_message(ctx["channel_id"], "> **✗ SetStatus** :: Please provide status text")
            return
        
        data = {
            "custom_status": {
                "text": message,
                "emoji_name": emoji_name,
                "emoji_id": emoji_id
            }
        }
        
        try:
            ok, result, err = _profile_patch(ctx["api"], data, ["/users/@me/settings"])
            if ok:
                msg = ctx["api"].send_message(ctx["channel_id"], "> **✓ SetStatus** :: Status updated")
            else:
                code = result.status_code if result else "No response"
                msg = ctx["api"].send_message(ctx["channel_id"], f"> **✗ SetStatus** :: Failed (HTTP {code}){': ' + err if err else ''}")

        except Exception as e:
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **✗ SetStatus** :: Error: {str(e)[:80]}")
    @bot.command(name="stealstatus", aliases=["copystatus"])
    def stealstatus(ctx, args):
        if not args:
            msg = ctx["api"].send_message(ctx["channel_id"], "> **✗ StealStatus** :: Please provide a user ID")
            return
        
        user_id = args[0]

        try:
            user_data, _ = _lookup_target_user(ctx["api"], user_id, guild_id=_resolve_ctx_guild_id(ctx))
            if user_data:
                username = user_data.get("username", "Unknown")
            else:
                username = "Unknown"
            
            # Note: Custom status is not publicly available through Discord API
            # It can only be set on your own account via /users/@me/settings
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **✗ StealStatus** :: **{username}**'s custom status is private — cannot be retrieved")
            
        except Exception as e:
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **✗ StealStatus** :: Error: {str(e)[:80]}")
    # -----------------------------------------------------------------------
    # stealserverpfp — steal a member's SERVER avatar and apply as YOURS in this server
    # -----------------------------------------------------------------------

    @bot.command(name="stealserverpfp", aliases=["sspfp", "ssavatar", "stealservavatar"])
    def stealserverpfp_cmd(ctx, args):
        if not args:
            msg = ctx["api"].send_message(ctx["channel_id"],
                f"> **StealServerPFP** :: Usage: `{bot.prefix}stealserverpfp <user_id>`")
            return

        raw = args[0].strip("<@!>")
        user_id = raw if raw.isdigit() else args[0]
        guild_id = _resolve_ctx_guild_id(ctx)
        api = ctx["api"]

        if not guild_id:
            msg = api.send_message(ctx["channel_id"], "> **✗ StealServerPFP** :: Must be used inside a server")
            return

        try:
            member_r = api.request("GET", f"/guilds/{guild_id}/members/{user_id}")
            if not member_r or member_r.status_code != 200:
                msg = api.send_message(ctx["channel_id"], f"> **✗ StealServerPFP** :: Could not find member {user_id} in this server")
                return

            member_data = member_r.json()
            avatar_hash = member_data.get("avatar")
            user_obj = member_data.get("user") or {}
            target_name = user_obj.get("username", user_id)

            if not avatar_hash:
                msg = api.send_message(ctx["channel_id"],
                    f"> **✗ StealServerPFP** :: **{target_name}** has no server avatar — try `{bot.prefix}stealpfp`")
                return

            img_url = f"https://cdn.discordapp.com/guilds/{guild_id}/users/{user_id}/avatars/{avatar_hash}.png?size=1024"

            img_r = api.session.get(img_url, timeout=10)
            if img_r.status_code != 200:
                msg = api.send_message(ctx["channel_id"], f"> **✗ StealServerPFP** :: Failed to download (HTTP {img_r.status_code})")
                return

            b64 = base64.b64encode(img_r.content).decode()
            patch = api.request("PATCH", "/users/@me", data={"avatar": f"data:image/png;base64,{b64}"})
            if patch and patch.status_code in (200, 204):
                msg = api.send_message(ctx["channel_id"],
                    f"> **✓ StealServerPFP** :: Applied **{target_name}**'s avatar to your account")
            else:
                code = patch.status_code if patch else "no response"
                try:
                    err = (patch.json() or {}).get("message", "") if patch else ""
                except Exception:
                    err = ""
                msg = api.send_message(ctx["channel_id"],
                    f"> **✗ StealServerPFP** :: Failed (HTTP {code}){': ' + err if err else ''}")
        except Exception as e:
            msg = api.send_message(ctx["channel_id"], f"> **✗ StealServerPFP** :: Error: {str(e)[:80]}")

    # -----------------------------------------------------------------------
    # stealserverbanner — steal a member's SERVER banner and apply as YOURS
    # -----------------------------------------------------------------------

    @bot.command(name="stealserverbanner", aliases=["ssbanner", "stealservbanner"])
    def stealserverbanner_cmd(ctx, args):
        if not args:
            msg = ctx["api"].send_message(ctx["channel_id"],
                f"> **Steal Server Banner** :: Usage: {bot.prefix}stealserverbanner <user_id|@mention>")
            return

        raw = args[0].strip("<@!>")
        user_id = raw if raw.isdigit() else args[0]
        guild_id = _resolve_ctx_guild_id(ctx)
        api = ctx["api"]

        if not guild_id:
            msg = api.send_message(ctx["channel_id"], "> **✗ StealServerBanner** :: Must be used inside a server.")
            return

        try:
            member_r = api.request("GET", f"/guilds/{guild_id}/members/{user_id}")
            if not member_r or member_r.status_code != 200:
                msg = api.send_message(ctx["channel_id"], f"> **✗ StealServerBanner** :: Could not find member `{user_id}` in this server.")
                return

            member_data = member_r.json()
            banner_hash = member_data.get("banner")
            user_obj = member_data.get("user") or {}
            target_name = user_obj.get("username", user_id)

            if not banner_hash:
                msg = api.send_message(ctx["channel_id"],
                    f"> **✗ StealServerBanner** :: **{target_name}** has no server-specific banner. Try `{bot.prefix}stealbanner` for their global banner.")
                return

            img_url = f"https://cdn.discordapp.com/guilds/{guild_id}/users/{user_id}/banners/{banner_hash}.png?size=1024"

            img_r = api.session.get(img_url, timeout=10)
            if img_r.status_code != 200:
                msg = api.send_message(ctx["channel_id"], f"> **✗ StealServerBanner** :: Failed to download (HTTP {img_r.status_code}).")
                return

            b64 = base64.b64encode(img_r.content).decode()
            patch = api.request("PATCH", "/users/@me", data={"banner": f"data:image/png;base64,{b64}"})
            if patch and patch.status_code in (200, 204):
                msg = api.send_message(ctx["channel_id"],
                    f"> **✓ StealServerBanner** :: Applied **{target_name}**'s server banner to your account.")
            else:
                code = patch.status_code if patch else "no response"
                try:
                    err = (patch.json() or {}).get("message", "") if patch else ""
                except Exception:
                    err = ""
                msg = api.send_message(ctx["channel_id"],
                    f"> **✗ StealServerBanner** :: Failed (HTTP {code}){': ' + err if err else ''}.")
        except Exception as e:
            msg = api.send_message(ctx["channel_id"], f"> **✗ StealServerBanner** :: Error: {str(e)[:80]}")

    # -----------------------------------------------------------------------
    # stealservernick — steal a member's SERVER nickname and apply as yours
    # -----------------------------------------------------------------------

    @bot.command(name="stealservernick", aliases=["ssnick", "stealservnick", "stealsnick"])
    def stealservernick_cmd(ctx, args):
        if not args:
            msg = ctx["api"].send_message(ctx["channel_id"],
                f"> **Steal Server Nick** :: Usage: {bot.prefix}stealservernick <user_id|@mention>")
            return

        raw = args[0].strip("<@!>")
        user_id = raw if raw.isdigit() else args[0]
        guild_id = _resolve_ctx_guild_id(ctx)
        api = ctx["api"]

        if not guild_id:
            msg = api.send_message(ctx["channel_id"], "> **✗ StealServerNick** :: Must be used inside a server.")
            return

        try:
            member_r = api.request("GET", f"/guilds/{guild_id}/members/{user_id}")
            if not member_r or member_r.status_code != 200:
                msg = api.send_message(ctx["channel_id"], f"> **✗ StealServerNick** :: Could not find member `{user_id}` in this server.")
                return

            member_data = member_r.json()
            nick = member_data.get("nick")
            user_obj = member_data.get("user") or {}
            target_name = user_obj.get("username", user_id)

            if not nick:
                msg = api.send_message(ctx["channel_id"],
                    f"> **✗ StealServerNick** :: **{target_name}** has no server nickname set.")
                return

            patch = api.request("PATCH", f"/guilds/{guild_id}/members/@me",
                                data={"nick": nick})
            if patch and patch.status_code in (200, 204):
                msg = api.send_message(ctx["channel_id"],
                    f"> **✓ StealServerNick** :: Nickname set to **{nick}** (stolen from {target_name}).")
            else:
                code = patch.status_code if patch else "no response"
                msg = api.send_message(ctx["channel_id"],
                    f"> **✗ StealServerNick** :: Failed to set nickname (HTTP {code}).")
        except Exception as e:
            msg = api.send_message(ctx["channel_id"], f"> **✗ StealServerNick** :: Error: {str(e)[:80]}")

    # -----------------------------------------------------------------------
    # stealservericon — steal the SERVER'S icon and set as your global avatar
    # -----------------------------------------------------------------------

    @bot.command(name="stealservericon", aliases=["ssicon", "stealicon", "stealguildicon"])
    def stealservericon_cmd(ctx, args):
        # No args needed — steals current server's icon; can also pass a guild_id
        guild_id = args[0] if args and args[0].isdigit() else _resolve_ctx_guild_id(ctx)
        api = ctx["api"]

        if not guild_id:
            msg = api.send_message(ctx["channel_id"],
                f"> **Steal Server Icon** :: Usage: {bot.prefix}stealservericon [guild_id] — no guild_id needed when run in the server")
            return

        try:
            guild_r = api.request("GET", f"/guilds/{guild_id}")
            if not guild_r or guild_r.status_code != 200:
                msg = api.send_message(ctx["channel_id"], f"> **✗ StealServerIcon** :: Could not fetch guild `{guild_id}`.")
                return

            guild_data = guild_r.json()
            icon_hash = guild_data.get("icon")
            guild_name = guild_data.get("name", guild_id)

            if not icon_hash:
                msg = api.send_message(ctx["channel_id"],
                    f"> **✗ StealServerIcon** :: **{guild_name}** has no server icon.")
                return

            ext = "gif" if icon_hash.startswith("a_") else "png"
            img_url = f"https://cdn.discordapp.com/icons/{guild_id}/{icon_hash}.{ext}?size=1024"

            img_r = api.session.get(img_url, timeout=10)
            if img_r.status_code != 200:
                msg = api.send_message(ctx["channel_id"], f"> **✗ StealServerIcon** :: Failed to download (HTTP {img_r.status_code}).")
                return

            b64 = base64.b64encode(img_r.content).decode()
            patch = api.request("PATCH", "/users/@me",
                                data={"avatar": f"data:image/{ext};base64,{b64}"})
            if patch and patch.status_code == 200:
                msg = api.send_message(ctx["channel_id"],
                    f"> **✓ StealServerIcon** :: Set **{guild_name}**'s icon as your global avatar.")
            else:
                code = patch.status_code if patch else "no response"
                try:
                    err = (patch.json() or {}).get("message", "") if patch else ""
                except Exception:
                    err = ""
                msg = api.send_message(ctx["channel_id"],
                    f"> **✗ StealServerIcon** :: Failed to set avatar (HTTP {code}){': ' + err if err else ''}.")
        except Exception as e:
            msg = api.send_message(ctx["channel_id"], f"> **✗ StealServerIcon** :: Error: {str(e)[:80]}")

    # ─── FUN COMMANDS ───────────────────────────────────────────────────────

    @bot.command(name="joke")
    def joke_cmd(ctx, args):
        jokes = [
            "Why did the scarecrow win an award? He was outstanding in his field!",
            "What do you call fake spaghetti? An impasta!",
            "Why don't scientists trust atoms? Because they make up everything!",
            "I told my computer I needed a break, and now it won't stop sending me Kit-Kat ads.",
            "My wife told me to take the spider out instead of killing it. We went and had some drinks.",
            "What's the object-oriented way to become wealthy? Inheritance!",
            "Why did the Python snake get sent to jail? It committed a string crime!",
            "I'm reading a book on the history of glue – can't put it down.",
            "Did you hear about the mathematician who's afraid of negative numbers? He'll stop at nothing to avoid them.",
            "What do you call a bear with no teeth? A gummy bear!",
        ]
        import random
        joke = random.choice(jokes)
        msg = ctx["api"].send_message(ctx["channel_id"], f"> **Joke** :: {joke}")

    @bot.command(name="compliment")
    def compliment_cmd(ctx, args):
        compliments = [
            "You're an awesome person!",
            "You light up the room!",
            "You deserve a hug right now.",
            "You're a smart cookie.",
            "You are awesome!",
            "You have impeccable manners.",
            "You're like sunshine on a rainy day.",
            "You bring out the best in other people!",
            "Your perspective is refreshing.",
            "You're a gift to those around you.",
        ]
        import random
        compliment = random.choice(compliments)
        msg = ctx["api"].send_message(ctx["channel_id"], f"> **Compliment** :: {compliment}")

    @bot.command(name="roast")
    def roast_cmd(ctx, args):
        roasts = [
            "You're so slow, you make a snail look like it's on fast-forward.",
            "I'd roast you, but my mom said I'm not allowed to burn trash.",
            "You're proof that evolution can go in reverse.",
            "I'd call you a tool, but that would be an insult to all the useful tools out there.",
            "You're like a cloud... when you disappear, it's a beautiful day.",
            "If you were a vegetable, you'd be a turnip.",
            "I'd say you're being dumb, but that would be an insult to dumb people.",
            "You're the human equivalent of a participation trophy.",
            "I'd roast you but I'd need a lot more material.",
            "You're so dense, light bends around you.",
        ]
        import random
        roast = random.choice(roasts)
        msg = ctx["api"].send_message(ctx["channel_id"], f"> **Roast** :: {roast}")

    @bot.command(name="trivia")
    def trivia_cmd(ctx, args):
        trivia_questions = [
            ("What is the capital of France?", "Paris"),
            ("What is the largest planet in our solar system?", "Jupiter"),
            ("What year did the Titanic sink?", "1912"),
            ("How many strings does a violin have?", "4"),
            ("What is the smallest country in the world?", "Vatican City"),
            ("What is the most spoken language in the world?", "Mandarin Chinese"),
            ("How many bones are in the adult human body?", "206"),
            ("What is the deepest ocean trench?", "Mariana Trench"),
            ("What year was the internet invented?", "1969"),
            ("What is the hottest planet in our solar system?", "Venus"),
        ]
        import random
        q, a = random.choice(trivia_questions)
        msg = ctx["api"].send_message(ctx["channel_id"], f"> **Trivia** :: {q} || **Answer:** {a}")

    @bot.command(name="mimic", aliases=["echo"])
    def mimic_cmd(ctx, args):
        def _resolve_target_id(message_data, raw_target):
            raw_target = str(raw_target or "").strip()
            mentions = (message_data or {}).get("mentions") or []
            if mentions:
                first = mentions[0]
                if str(first.get("id") or "").isdigit():
                    return str(first.get("id")), bool(first.get("bot"))
            cleaned = raw_target.strip().strip("<@!>")
            if cleaned.isdigit():
                return cleaned, False
            return None, False

        if not args:
            msg = ctx["api"].send_message(
                ctx["channel_id"],
                f"> **Mimic** :: Usage: {bot.prefix}mimic <@user|user_id> [custom reply] — Use {bot.prefix}stopmock to stop",
            )
            return

        target_id, target_is_bot = _resolve_target_id(ctx.get("message") or {}, args[0])
        if not target_id:
            text = " ".join(str(arg) for arg in args)
            msg = ctx["api"].send_message(ctx["channel_id"], text)
            return

        if target_is_bot or target_id == str(ctx["author_id"]) or target_id == str(bot.user_id):
            msg = ctx["api"].send_message(
                ctx["channel_id"],
                "> **✗ Mimic** :: You cannot mimic yourself or a bot",
            )
            return

        bot._mimic_target = str(target_id)
        bot._mimic_enabled = True
        bot._mimic_custom_response = " ".join(str(arg) for arg in args[1:]).strip() or None
        bot._mimic_sent_messages.clear()
        mode = "custom response" if bot._mimic_custom_response else "message mimic"
        msg = ctx["api"].send_message(
            ctx["channel_id"],
            f"> **✓ Mimic** :: Mimicking <@{bot._mimic_target}> · {mode}",
        )

    @bot.command(name="stopmock", aliases=["smk", "stopmimic"])
    def stopmock_cmd(ctx, args):
        bot._mimic_enabled = False
        bot._mimic_target = None
        bot._mimic_custom_response = None
        bot._mimic_sent_messages.clear()
        msg = ctx["api"].send_message(ctx["channel_id"], "> **✗ Mimic** :: Stopped.")

    # ─── UTILITY / TEXT TRANSFORM COMMANDS ─────────────────────────────────

    @bot.command(name="mock", aliases=["spongebob"])
    def mock_cmd(ctx, args):
        if not args:
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **Mock** :: Usage: `{bot.prefix}mock <text>`")
            return
        text = " ".join(args)
        result = "".join(c.upper() if i % 2 == 0 else c.lower() for i, c in enumerate(text))
        msg = ctx["api"].send_message(ctx["channel_id"], result)

    @bot.command(name="clap")
    def clap_cmd(ctx, args):
        if not args:
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **Clap** :: Usage: `{bot.prefix}clap <text>`")
            return
        result = " 👏 ".join(args) + " 👏"
        msg = ctx["api"].send_message(ctx["channel_id"], result)

    @bot.command(name="aesthetic", aliases=["vaporwave", "wide"])
    def aesthetic_cmd(ctx, args):
        if not args:
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **Aesthetic** :: Usage: `{bot.prefix}aesthetic <text>`")
            return
        text = " ".join(args)
        result = "".join(chr(ord(c) + 0xFEE0) if 0x21 <= ord(c) <= 0x7E else c for c in text)
        msg = ctx["api"].send_message(ctx["channel_id"], result)

    @bot.command(name="reverse", aliases=["rev"])
    def reverse_cmd(ctx, args):
        if not args:
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **Reverse** :: Usage: `{bot.prefix}reverse <text>`")
            return
        text = " ".join(args)
        msg = ctx["api"].send_message(ctx["channel_id"], text[::-1])

    @bot.command(name="big", aliases=["regional"])
    def big_cmd(ctx, args):
        if not args:
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **Big** :: Usage: `{bot.prefix}big <text>`")
            return
        text = " ".join(args).lower()
        mapping = {**{chr(ord('a') + i): f":regional_indicator_{chr(ord('a') + i)}: " for i in range(26)},
                   **{str(d): f"{d}\u20e3 " for d in range(10)}, " ": "   "}
        result = "".join(mapping.get(c, c) for c in text)
        msg = ctx["api"].send_message(ctx["channel_id"], result)

    @bot.command(name="spoiler", aliases=["hide"])
    def spoiler_cmd(ctx, args):
        if not args:
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **Spoiler** :: Usage: `{bot.prefix}spoiler <text>`")
            return
        text = " ".join(args)
        msg = ctx["api"].send_message(ctx["channel_id"], f"||{text}||")

    @bot.command(name="codeblock", aliases=["code", "cb"])
    def codeblock_cmd(ctx, args):
        if not args:
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **Codeblock** :: Usage: `{bot.prefix}codeblock [lang] <text>`")
            return
        lang = ""
        text_parts = args
        known_langs = {"python", "py", "js", "javascript", "ts", "typescript", "json", "bash", "sh", "html", "css", "c", "cpp", "java", "go", "rust", "lua"}
        if args[0].lower() in known_langs:
            lang = args[0].lower()
            text_parts = args[1:]
        text = " ".join(text_parts)
        msg = ctx["api"].send_message(ctx["channel_id"], f"```{lang}\n{text}\n```")

    @bot.command(name="b64encode", aliases=["base64encode", "b64e"])
    def b64encode_cmd(ctx, args):
        if not args:
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **Base64 Encode** :: Usage: `{bot.prefix}b64encode <text>`")
            return
        import base64 as _b64
        text = " ".join(args)
        encoded = _b64.b64encode(text.encode()).decode()
        msg = ctx["api"].send_message(ctx["channel_id"], f"> **Base64** :: `{encoded}`")

    @bot.command(name="b64decode", aliases=["base64decode", "b64d"])
    def b64decode_cmd(ctx, args):
        if not args:
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **Base64 Decode** :: Usage: `{bot.prefix}b64decode <encoded>`")
            return
        import base64 as _b64
        try:
            decoded = _b64.b64decode(args[0].encode()).decode("utf-8", errors="replace")
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **Decoded** :: {decoded}")
        except Exception as e:
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **✗ Base64 Decode** :: Invalid input: {e}")

    @bot.command(name="charinfo", aliases=["unicode", "uinfo"])
    def charinfo_cmd(ctx, args):
        if not args:
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **CharInfo** :: Usage: `{bot.prefix}charinfo <char>`")
            return
        char = args[0][0]
        cp = ord(char)
        name = ""
        try:
            import unicodedata
            name = unicodedata.name(char, "UNKNOWN")
        except Exception:
            pass
        msg = ctx["api"].send_message(ctx["channel_id"], f"> **CharInfo** :: `{char}` · U+{cp:04X} · {name} · `\\u{cp:04x}`")

    @bot.command(name="snowflake", aliases=["sf", "sfinfo"])
    def snowflake_cmd(ctx, args):
        if not args or not args[0].isdigit():
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **Snowflake** :: Usage: `{bot.prefix}snowflake <discord_id>`")
            return
        sf = int(args[0])
        epoch = 1420070400000
        timestamp_ms = (sf >> 22) + epoch
        worker = (sf & 0x3E0000) >> 17
        process = (sf & 0x1F000) >> 12
        increment = sf & 0xFFF
        import datetime as _dt
        created = _dt.datetime.utcfromtimestamp(timestamp_ms / 1000).strftime("%Y-%m-%d %H:%M:%S UTC")
        msg = ctx["api"].send_message(ctx["channel_id"],
            f"> **Snowflake** :: ID `{sf}` · Created: **{created}** · Worker: {worker} · PID: {process} · Inc: {increment}")

    @bot.command(name="timestamp", aliases=["ts", "discordts"])
    def timestamp_cmd(ctx, args):
        import time as _time
        unix = int(_time.time())
        if args and args[0].isdigit():
            unix = int(args[0])
        styles = ["t", "T", "d", "D", "f", "F", "R"]
        examples = " · ".join(f"`<t:{unix}:{s}>` → <t:{unix}:{s}>" for s in styles)
        msg = ctx["api"].send_message(ctx["channel_id"], f"> **Timestamp** (`{unix}`) :: {examples}")

    @bot.command(name="calc", aliases=["calculate", "math"])
    def calc_cmd(ctx, args):
        if not args:
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **Calc** :: Usage: `{bot.prefix}calc <expression>`")
            return
        import math as _math
        expr = " ".join(args)
        safe_globals = {"__builtins__": {}, "math": _math, "abs": abs, "round": round,
                        "min": min, "max": max, "sum": sum, "pow": pow, "sqrt": _math.sqrt,
                        "pi": _math.pi, "e": _math.e, "sin": _math.sin, "cos": _math.cos,
                        "tan": _math.tan, "log": _math.log, "ceil": _math.ceil, "floor": _math.floor}
        try:
            result = eval(compile(expr, "<calc>", "eval"), safe_globals, {})
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **Calc** :: `{expr}` = **{result}**")
        except Exception as e:
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **✗ Calc** :: Error: {e}")

    @bot.command(name="hex", aliases=["tohex", "fromhex"])
    def hex_cmd(ctx, args):
        if not args:
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **Hex** :: Usage: `{bot.prefix}hex <number or 0xFF>`")
            return
        raw = args[0]
        try:
            if raw.lower().startswith("0x"):
                val = int(raw, 16)
                msg = ctx["api"].send_message(ctx["channel_id"], f"> **Hex** :: `{raw}` = decimal **{val}**")
            else:
                val = int(raw)
                msg = ctx["api"].send_message(ctx["channel_id"], f"> **Hex** :: `{val}` = hex **0x{val:X}**")
        except Exception:
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **✗ Hex** :: Invalid input")

    @bot.command(name="binary", aliases=["bin", "tobin"])
    def binary_cmd(ctx, args):
        if not args:
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **Binary** :: Usage: `{bot.prefix}binary <number or 0b1010>`")
            return
        raw = args[0]
        try:
            if raw.lower().startswith("0b"):
                val = int(raw, 2)
                msg = ctx["api"].send_message(ctx["channel_id"], f"> **Binary** :: `{raw}` = decimal **{val}**")
            else:
                val = int(raw)
                msg = ctx["api"].send_message(ctx["channel_id"], f"> **Binary** :: `{val}` = binary **{bin(val)}**")
        except Exception:
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **✗ Binary** :: Invalid input")

    @bot.command(name="leet", aliases=["l33t", "1337"])
    def leet_cmd(ctx, args):
        if not args:
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **Leet** :: Usage: `{bot.prefix}leet <text>`")
            return
        tbl = str.maketrans("aAeEiIoOsStTbBgGlL", "4433110055++886699")
        msg = ctx["api"].send_message(ctx["channel_id"], " ".join(args).translate(tbl))

    @bot.command(name="upper")
    def upper_cmd(ctx, args):
        if not args:
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **Upper** :: Usage: `{bot.prefix}upper <text>`")
            return
        msg = ctx["api"].send_message(ctx["channel_id"], " ".join(args).upper())

    @bot.command(name="lower")
    def lower_cmd(ctx, args):
        if not args:
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **Lower** :: Usage: `{bot.prefix}lower <text>`")
            return
        msg = ctx["api"].send_message(ctx["channel_id"], " ".join(args).lower())

    @bot.command(name="repeat", aliases=["rpt"])
    def repeat_cmd(ctx, args):
        if len(args) < 2 or not args[0].isdigit():
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **Repeat** :: Usage: `{bot.prefix}repeat <count> <text>`")
            return
        count = min(int(args[0]), 20)
        text = " ".join(args[1:])
        import time as _time
        for _ in range(count):
            ctx["api"].send_message(ctx["channel_id"], text)
            _time.sleep(0.5)

    @bot.command(name="wordcount", aliases=["wc"])
    def wordcount_cmd(ctx, args):
        if not args:
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **Word Count** :: Usage: `{bot.prefix}wordcount <text>`")
            return
        text = " ".join(args)
        words = len(text.split())
        chars = len(text)
        chars_no_space = len(text.replace(" ", ""))
        msg = ctx["api"].send_message(ctx["channel_id"],
            f"> **Word Count** :: Words: **{words}** · Chars: **{chars}** · Chars (no spaces): **{chars_no_space}**")

    @bot.command(name="scramble")
    def scramble_cmd(ctx, args):
        if not args:
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **Scramble** :: Usage: `{bot.prefix}scramble <text>`")
            return
        import random as _rand
        text = " ".join(args)
        words = text.split()
        result = " ".join("".join(_rand.sample(w, len(w))) for w in words)
        msg = ctx["api"].send_message(ctx["channel_id"], result)

    @bot.command(name="zalgo")
    def zalgo_cmd(ctx, args):
        if not args:
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **Zalgo** :: Usage: `{bot.prefix}zalgo <text>`")
            return
        import random as _rand
        combining = [chr(c) for c in range(0x0300, 0x036F)]
        text = " ".join(args)
        result = "".join(c + "".join(_rand.choices(combining, k=_rand.randint(1, 4))) if c.isalpha() else c for c in text)
        msg = ctx["api"].send_message(ctx["channel_id"], result[:1900])

    # ─── INFO / LOOKUP COMMANDS ──────────────────────────────────────────────

    @bot.command(name="serverinfo", aliases=["si", "guildinfo", "gi"])
    def serverinfo_cmd(ctx, args):
        guild_id = ctx.get("guild_id") or (ctx.get("message") or {}).get("guild_id")
        if not guild_id:
            msg = ctx["api"].send_message(ctx["channel_id"], "> **ServerInfo** :: Not in a server")
            return
        try:
            guild = ctx["api"].request("GET", f"/guilds/{guild_id}?with_counts=true")
            if not guild:
                msg = ctx["api"].send_message(ctx["channel_id"], "> **✗ ServerInfo** :: Failed to fetch guild info")
                return
            name = guild.get("name", "Unknown")
            owner = f"<@{guild.get('owner_id', '?')}>"
            members = guild.get("approximate_member_count", "?")
            online = guild.get("approximate_presence_count", "?")
            channels = len(guild.get("channels") or [])
            roles = len(guild.get("roles") or [])
            region = guild.get("region", "auto")
            boost_level = guild.get("premium_tier", 0)
            boosts = guild.get("premium_subscription_count", 0)
            msg = ctx["api"].send_message(ctx["channel_id"],
                f"> **Server Info** :: **{name}** (`{guild_id}`)\n"
                f"> Owner: {owner} · Members: **{members}** ({online} online)\n"
                f"> Channels: **{channels}** · Roles: **{roles}** · Region: **{region}**\n"
                f"> Boost Level: **{boost_level}** ({boosts} boosts)")
        except Exception as e:
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **✗ ServerInfo** :: {e}")

    @bot.command(name="membercount", aliases=["mc", "members"])
    def membercount_cmd(ctx, args):
        guild_id = ctx.get("guild_id") or (ctx.get("message") or {}).get("guild_id")
        if not guild_id:
            msg = ctx["api"].send_message(ctx["channel_id"], "> **MemberCount** :: Not in a server")
            return
        try:
            guild = ctx["api"].request("GET", f"/guilds/{guild_id}?with_counts=true")
            name = (guild or {}).get("name", guild_id)
            total = (guild or {}).get("approximate_member_count", "?")
            online = (guild or {}).get("approximate_presence_count", "?")
            msg = ctx["api"].send_message(ctx["channel_id"],
                f"> **Members** :: **{name}** — Total: **{total}** · Online: **{online}**")
        except Exception as e:
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **✗ MemberCount** :: {e}")

    @bot.command(name="roleinfo", aliases=["ri", "rinfo"])
    def roleinfo_cmd(ctx, args):
        guild_id = ctx.get("guild_id") or (ctx.get("message") or {}).get("guild_id")
        if not args or not guild_id:
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **RoleInfo** :: Usage: `{bot.prefix}roleinfo <role_id>`")
            return
        role_id = args[0].strip("<@&>")
        try:
            guild = ctx["api"].request("GET", f"/guilds/{guild_id}")
            roles = (guild or {}).get("roles") or []
            role = next((r for r in roles if str(r.get("id")) == role_id), None)
            if not role:
                msg = ctx["api"].send_message(ctx["channel_id"], f"> **✗ RoleInfo** :: Role `{role_id}` not found")
                return
            color = f"#{role.get('color', 0):06X}"
            hoisted = "Yes" if role.get("hoist") else "No"
            mentionable = "Yes" if role.get("mentionable") else "No"
            position = role.get("position", 0)
            msg = ctx["api"].send_message(ctx["channel_id"],
                f"> **Role Info** :: **{role.get('name')}** (`{role_id}`)\n"
                f"> Color: `{color}` · Position: **{position}** · Hoisted: **{hoisted}** · Mentionable: **{mentionable}**")
        except Exception as e:
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **✗ RoleInfo** :: {e}")

    @bot.command(name="channelinfo", aliases=["ci", "cinfo"])
    def channelinfo_cmd(ctx, args):
        cid = args[0].strip("<#>") if args else ctx["channel_id"]
        try:
            channel = ctx["api"].request("GET", f"/channels/{cid}")
            if not channel:
                msg = ctx["api"].send_message(ctx["channel_id"], "> **✗ ChannelInfo** :: Channel not found")
                return
            ch_types = {0: "Text", 2: "Voice", 4: "Category", 5: "Announcement", 11: "Thread", 13: "Stage", 15: "Forum"}
            ch_type = ch_types.get(channel.get("type", 0), "Unknown")
            topic = channel.get("topic") or "None"
            slowmode = channel.get("rate_limit_per_user", 0)
            name = channel.get("name", cid)
            msg = ctx["api"].send_message(ctx["channel_id"],
                f"> **Channel Info** :: **#{name}** (`{cid}`)\n"
                f"> Type: **{ch_type}** · Slowmode: **{slowmode}s** · Topic: {topic[:80]}")
        except Exception as e:
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **✗ ChannelInfo** :: {e}")

    @bot.command(name="inviteinfo", aliases=["ii", "iinfo"])
    def inviteinfo_cmd(ctx, args):
        if not args:
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **InviteInfo** :: Usage: `{bot.prefix}inviteinfo <invite_code>`")
            return
        code = args[0].split("/")[-1].strip()
        try:
            data = ctx["api"].request("GET", f"/invites/{code}?with_counts=true&with_expiration=true")
            if not data:
                msg = ctx["api"].send_message(ctx["channel_id"], f"> **✗ InviteInfo** :: Invalid invite")
                return
            guild = data.get("guild") or {}
            channel = data.get("channel") or {}
            inviter = data.get("inviter") or {}
            total = data.get("approximate_member_count", "?")
            online = data.get("approximate_presence_count", "?")
            msg = ctx["api"].send_message(ctx["channel_id"],
                f"> **Invite Info** :: `{code}`\n"
                f"> Server: **{guild.get('name', '?')}** · Channel: **#{channel.get('name', '?')}**\n"
                f"> Members: **{total}** ({online} online) · Inviter: **{inviter.get('username', 'Unknown')}**")
        except Exception as e:
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **✗ InviteInfo** :: {e}")

    @bot.command(name="firstmsg", aliases=["firstmessage", "fm"])
    def firstmsg_cmd(ctx, args):
        cid = args[0].strip("<#>") if args else ctx["channel_id"]
        try:
            messages = ctx["api"].request("GET", f"/channels/{cid}/messages?limit=1&after=0")
            if not messages:
                msg = ctx["api"].send_message(ctx["channel_id"], f"> **✗ FirstMsg** :: No messages found")
                return
            m = messages[0]
            author = (m.get("author") or {}).get("username", "Unknown")
            content = m.get("content") or "[no text]"
            msg_id = m.get("id")
            msg = ctx["api"].send_message(ctx["channel_id"],
                f"> **First Message** in <#{cid}> · by **{author}**: {content[:100]}\n"
                f"> Jump: https://discord.com/channels/{ctx.get('guild_id', '@me')}/{cid}/{msg_id}")
        except Exception as e:
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **✗ FirstMsg** :: {e}")

    # ─── SELF MANAGEMENT COMMANDS ────────────────────────────────────────────

    @bot.command(name="nick", aliases=["nickname", "setnick"])
    def nick_cmd(ctx, args):
        guild_id = ctx.get("guild_id") or (ctx.get("message") or {}).get("guild_id")
        if not guild_id:
            msg = ctx["api"].send_message(ctx["channel_id"], "> **Nick** :: Must be used in a server")
            return
        new_nick = " ".join(args) if args else None
        try:
            ctx["api"].request("PATCH", f"/guilds/{guild_id}/members/@me",
                               json={"nick": new_nick})
            if new_nick:
                msg = ctx["api"].send_message(ctx["channel_id"], f"> **✓ Nick** :: Changed to **{new_nick}**")
            else:
                msg = ctx["api"].send_message(ctx["channel_id"], "> **✓ Nick** :: Nickname cleared")
        except Exception as e:
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **✗ Nick** :: {e}")

    @bot.command(name="status", aliases=["setstatus", "presence"])
    def status_cmd_presence(ctx, args):
        valid = {"online", "idle", "dnd", "invisible"}
        if not args or args[0].lower() not in valid:
            msg = ctx["api"].send_message(ctx["channel_id"],
                f"> **Status** :: Usage: `{bot.prefix}status <online|idle|dnd|invisible>`")
            return
        status = args[0].lower()
        try:
            ctx["api"].request("PATCH", "/users/@me/settings", json={"status": status})
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **✓ Status** :: Set to **{status}**")
        except Exception as e:
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **✗ Status** :: {e}")

    @bot.command(name="customstatus", aliases=["cstatus", "cs"])
    def customstatus_cmd(ctx, args):
        custom_text = " ".join(args) if args else ""
        try:
            ctx["api"].request("PATCH", "/users/@me/settings",
                               json={"custom_status": {"text": custom_text} if custom_text else None})
            if custom_text:
                msg = ctx["api"].send_message(ctx["channel_id"], f"> **✓ Custom Status** :: Set to **{custom_text}**")
            else:
                msg = ctx["api"].send_message(ctx["channel_id"], "> **✓ Custom Status** :: Cleared")
        except Exception as e:
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **✗ Custom Status** :: {e}")

    @bot.command(name="purge", aliases=["delpurge", "selfpurge"])
    def purge_cmd(ctx, args):
        count = 10
        if args and args[0].isdigit():
            count = min(int(args[0]), 100)
        channel_id = ctx["channel_id"]
        user_id = str(bot.user_id)
        deleted = 0
        try:
            response = ctx["api"].request("GET", f"/channels/{channel_id}/messages?limit=100")
            messages = []
            if response and response.status_code == 200:
                try:
                    messages = response.json()
                except Exception:
                    messages = []

            if not messages:
                msg = ctx["api"].send_message(channel_id, "> **Purge** :: No messages found")
                return
            import time as _time
            for m in messages:
                if deleted >= count:
                    break
                if str((m.get("author") or {}).get("id")) == user_id:
                    try:
                        ctx["api"].delete_message(channel_id, m["id"])
                        deleted += 1
                        _time.sleep(0.3)
                    except Exception:
                        pass
            msg = ctx["api"].send_message(channel_id, f"> **✓ Purge** :: Deleted **{deleted}** of your messages")
        except Exception as e:
            msg = ctx["api"].send_message(channel_id, f"> **✗ Purge** :: {e}")

    @bot.command(name="pin")
    def pin_cmd(ctx, args):
        msg_id = args[0] if args else None
        if not msg_id:
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **Pin** :: Usage: `{bot.prefix}pin <message_id>`")
            return
        try:
            ctx["api"].request("PUT", f"/channels/{ctx['channel_id']}/pins/{msg_id}")
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **✓ Pin** :: Message pinned")
        except Exception as e:
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **✗ Pin** :: {e}")

    @bot.command(name="unpin")
    def unpin_cmd(ctx, args):
        msg_id = args[0] if args else None
        if not msg_id:
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **Unpin** :: Usage: `{bot.prefix}unpin <message_id>`")
            return
        try:
            ctx["api"].request("DELETE", f"/channels/{ctx['channel_id']}/pins/{msg_id}")
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **✓ Unpin** :: Message unpinned")
        except Exception as e:
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **✗ Unpin** :: {e}")

    @bot.command(name="slowmode", aliases=["sm"])
    def slowmode_cmd(ctx, args):
        guild_id = ctx.get("guild_id") or (ctx.get("message") or {}).get("guild_id")
        if not args or not args[0].isdigit():
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **Slowmode** :: Usage: `{bot.prefix}slowmode <seconds>`")
            return
        seconds = min(int(args[0]), 21600)
        try:
            ctx["api"].request("PATCH", f"/channels/{ctx['channel_id']}", json={"rate_limit_per_user": seconds})
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **✓ Slowmode** :: Set to **{seconds}s**")
        except Exception as e:
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **✗ Slowmode** :: {e}")

    @bot.command(name="topic")
    def topic_cmd(ctx, args):
        new_topic = " ".join(args) if args else ""
        try:
            ctx["api"].request("PATCH", f"/channels/{ctx['channel_id']}", json={"topic": new_topic})
            msg = ctx["api"].send_message(ctx["channel_id"],
                f"> **✓ Topic** :: Set to `{new_topic}`" if new_topic else "> **✓ Topic** :: Cleared")
        except Exception as e:
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **✗ Topic** :: {e}")

    @bot.command(name="react")
    def react_cmd(ctx, args):
        if len(args) < 2:
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **React** :: Usage: `{bot.prefix}react <message_id> <emoji>`")
            return
        msg_id, emoji = args[0], args[1]
        try:
            import urllib.parse
            encoded = urllib.parse.quote(emoji)
            ctx["api"].request("PUT", f"/channels/{ctx['channel_id']}/messages/{msg_id}/reactions/{encoded}/@me")
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **✓ React** :: Reacted with {emoji}")
        except Exception as e:
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **✗ React** :: {e}")

    @bot.command(name="unreact", aliases=["removereact"])
    def unreact_cmd(ctx, args):
        if len(args) < 2:
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **Unreact** :: Usage: `{bot.prefix}unreact <message_id> <emoji>`")
            return
        msg_id, emoji = args[0], args[1]
        try:
            import urllib.parse
            encoded = urllib.parse.quote(emoji)
            ctx["api"].request("DELETE", f"/channels/{ctx['channel_id']}/messages/{msg_id}/reactions/{encoded}/@me")
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **✓ Unreact** :: Removed reaction {emoji}")
        except Exception as e:
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **✗ Unreact** :: {e}")

    # ─── EMOJI MANAGEMENT COMMANDS ───────────────────────────────────────────

    @bot.command(name="stealemoji", aliases=["semoji", "copyemoji"])
    def stealemoji_cmd(ctx, args):
        guild_id = ctx.get("guild_id") or (ctx.get("message") or {}).get("guild_id")
        if not args or not guild_id:
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **StealEmoji** :: Usage: `{bot.prefix}stealemoji <emoji>` (in a server)")
            return
        raw = args[0]
        import re as _re
        m = _re.match(r"<a?:(\w+):(\d+)>", raw)
        if not m:
            msg = ctx["api"].send_message(ctx["channel_id"], "> **✗ StealEmoji** :: Must be a custom emoji like `<:name:id>`")
            return
        name, eid = m.group(1), m.group(2)
        ext = "gif" if raw.startswith("<a:") else "png"
        url = f"https://cdn.discordapp.com/emojis/{eid}.{ext}?size=128"
        try:
            r = ctx["api"].session.get(url, timeout=10)
            if r.status_code != 200:
                msg = ctx["api"].send_message(ctx["channel_id"], f"> **✗ StealEmoji** :: Failed to download emoji")
                return
            b64 = base64.b64encode(r.content).decode()
            data_uri = f"data:image/{ext};base64,{b64}"
            result = ctx["api"].request("POST", f"/guilds/{guild_id}/emojis", json={"name": name, "image": data_uri})
            new_id = (result or {}).get("id", "?")
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **✓ StealEmoji** :: Added **{name}** (`{new_id}`) to this server")
        except Exception as e:
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **✗ StealEmoji** :: {e}")

    @bot.command(name="emojiurl", aliases=["eurl", "enlargeemoji", "jumbo"])
    def emojiurl_cmd(ctx, args):
        if not args:
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **EmojiURL** :: Usage: `{bot.prefix}emojiurl <emoji>`")
            return
        import re as _re
        raw = args[0]
        m = _re.match(r"<a?:(\w+):(\d+)>", raw)
        if m:
            name, eid = m.group(1), m.group(2)
            ext = "gif" if raw.startswith("<a:") else "png"
            url = f"https://cdn.discordapp.com/emojis/{eid}.{ext}?size=256"
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **Emoji** :: **{name}**\n{url}")
        else:
            import urllib.parse
            encoded = urllib.parse.quote(raw)
            code_point = "-".join(f"{ord(c):x}" for c in raw)
            url = f"https://twemoji.maxcdn.com/v/latest/72x72/{code_point}.png"
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **Emoji** :: `{raw}` — {url}")

    @bot.command(name="delemoji", aliases=["deleteemoji", "removeemoji"])
    def delemoji_cmd(ctx, args):
        guild_id = ctx.get("guild_id") or (ctx.get("message") or {}).get("guild_id")
        if not args or not guild_id:
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **DelEmoji** :: Usage: `{bot.prefix}delemoji <emoji_id>`")
            return
        import re as _re
        raw = args[0]
        m = _re.match(r"<a?:\w+:(\d+)>", raw)
        emoji_id = m.group(1) if m else raw.strip()
        try:
            ctx["api"].request("DELETE", f"/guilds/{guild_id}/emojis/{emoji_id}")
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **✓ DelEmoji** :: Deleted emoji `{emoji_id}`")
        except Exception as e:
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **✗ DelEmoji** :: {e}")

    @bot.command(name="addemoji", aliases=["addmoji", "uploademoji"])
    def addemoji_cmd(ctx, args):
        guild_id = ctx.get("guild_id") or (ctx.get("message") or {}).get("guild_id")
        if len(args) < 2 or not guild_id:
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **AddEmoji** :: Usage: `{bot.prefix}addemoji <name> <image_url>`")
            return
        name, url = args[0], args[1]
        try:
            r = ctx["api"].session.get(url, timeout=10)
            if r.status_code != 200:
                msg = ctx["api"].send_message(ctx["channel_id"], f"> **✗ AddEmoji** :: Failed to download image (HTTP {r.status_code})")
                return
            ct = r.headers.get("Content-Type", "image/png").split(";")[0].strip()
            ext = {"image/gif": "gif", "image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}.get(ct, "png")
            b64 = base64.b64encode(r.content).decode()
            result = ctx["api"].request("POST", f"/guilds/{guild_id}/emojis",
                                        json={"name": name, "image": f"data:{ct};base64,{b64}"})
            new_id = (result or {}).get("id", "?")
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **✓ AddEmoji** :: Added **{name}** (`{new_id}`)")
        except Exception as e:
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **✗ AddEmoji** :: {e}")

    @bot.command(name="listemojis", aliases=["emojis", "emojilist"])
    def listemojis_cmd(ctx, args):
        guild_id = ctx.get("guild_id") or (ctx.get("message") or {}).get("guild_id")
        if not guild_id:
            msg = ctx["api"].send_message(ctx["channel_id"], "> **ListEmojis** :: Must be in a server")
            return
        try:
            guild = ctx["api"].request("GET", f"/guilds/{guild_id}")
            emojis = (guild or {}).get("emojis") or []
            if not emojis:
                msg = ctx["api"].send_message(ctx["channel_id"], "> **Emojis** :: No custom emojis in this server")
                return
            lines = [f"<{'a' if e.get('animated') else ''}:{e['name']}:{e['id']}> `{e['name']}`" for e in emojis[:30]]
            text = "\n".join(lines)
            if len(emojis) > 30:
                text += f"\n... and {len(emojis) - 30} more"
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **Emojis** :: **{len(emojis)}** total\n{text}")
        except Exception as e:
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **✗ ListEmojis** :: {e}")

    # ─── SNIPE COMMANDS ───────────────────────────────────────────────────────

    @bot.command(name="snipe", aliases=["sn"])
    def snipe_cmd_runtime(ctx, args):
        cid = ctx["channel_id"]
        entry = bot._snipe_cache.get(cid)
        if not entry:
            msg = ctx["api"].send_message(cid, "> **Snipe** :: Nothing to snipe in this channel")
            return
        m = entry.get("message") or {}
        author = (m.get("author") or {}).get("username", "Unknown")
        content = m.get("content") or "[no content]"
        msg = ctx["api"].send_message(cid, f"> **Snipe** :: **{author}**: {content[:1800]}")

    @bot.command(name="editsnipe", aliases=["esnipe", "es"])
    def editsnipe_cmd(ctx, args):
        cid = ctx["channel_id"]
        entry = bot._esnipe_cache.get(cid)
        if not entry:
            msg = ctx["api"].send_message(cid, "> **EditSnipe** :: Nothing to edit-snipe in this channel")
            return
        before_data = entry.get("before") or {}
        after_data = entry.get("after") or {}
        author = (before_data.get("author") or {}).get("username", "Unknown")
        before = before_data.get("content") or "[empty]"
        after = after_data.get("content") or "[empty]"
        msg = ctx["api"].send_message(cid, f"> **EditSnipe** :: **{author}** edited:\n> Before: {before[:800]}\n> After: {after[:800]}")

    # ─── REMINDER COMMAND ────────────────────────────────────────────────────

    @bot.command(name="remind", aliases=["reminder", "remindme"])
    def remind_cmd(ctx, args):
        if len(args) < 2:
            msg = ctx["api"].send_message(ctx["channel_id"],
                f"> **Remind** :: Usage: `{bot.prefix}remind <seconds> <message>` — e.g. `{bot.prefix}remind 60 take a break`")
            return
        try:
            secs = int(args[0])
        except ValueError:
            msg = ctx["api"].send_message(ctx["channel_id"], "> **✗ Remind** :: First argument must be seconds (e.g. `300` for 5 min)")
            return
        reminder_text = " ".join(args[1:])
        cid = ctx["channel_id"]
        import threading, time as _time
        def _fire():
            _time.sleep(secs)
            try:
                bot.api.send_message(cid, f"> ⏰ **Reminder** :: {reminder_text}")
            except Exception:
                pass
        t = threading.Thread(target=_fire, daemon=True)
        t.start()
        h = secs // 3600
        m2 = (secs % 3600) // 60
        s2 = secs % 60
        parts = []
        if h: parts.append(f"{h}h")
        if m2: parts.append(f"{m2}m")
        if s2 or not parts: parts.append(f"{s2}s")
        msg = ctx["api"].send_message(ctx["channel_id"], f"> **✓ Remind** :: I'll remind you in **{''.join(parts)}** — {reminder_text}")

    @bot.command(name="countdown", aliases=["cd"])
    def countdown_cmd(ctx, args):
        if len(args) < 2 or not args[0].isdigit():
            msg = ctx["api"].send_message(ctx["channel_id"],
                f"> **Countdown** :: Usage: `{bot.prefix}countdown <from> <label>` — e.g. `{bot.prefix}countdown 5 Go!`")
            return
        count = min(int(args[0]), 10)
        label = " ".join(args[1:])
        import time as _time
        import threading
        cid = ctx["channel_id"]
        def _run():
            for i in range(count, 0, -1):
                bot.api.send_message(cid, str(i))
                _time.sleep(1)
            bot.api.send_message(cid, f"**{label}**")
        threading.Thread(target=_run, daemon=True).start()

    # ─── MISCELLANEOUS UTILITY ───────────────────────────────────────────────

    @bot.command(name="coinflip", aliases=["coin", "flip", "cf"])
    def coinflip_cmd(ctx, args):
        import random as _rand
        result = _rand.choice(["**Heads** 🪙", "**Tails** 🪙"])
        msg = ctx["api"].send_message(ctx["channel_id"], f"> **Coin Flip** :: {result}")

    @bot.command(name="dice", aliases=["roll", "d6"])
    def dice_cmd(ctx, args):
        import random as _rand
        sides = 6
        count = 1
        if args:
            spec = args[0].lower()
            if "d" in spec:
                parts = spec.split("d")
                try:
                    count = min(int(parts[0] or 1), 20)
                    sides = int(parts[1])
                except Exception:
                    pass
            elif spec.isdigit():
                sides = int(spec)
        rolls = [_rand.randint(1, sides) for _ in range(count)]
        result = " + ".join(str(r) for r in rolls) + f" = **{sum(rolls)}**" if count > 1 else f"**{rolls[0]}**"
        msg = ctx["api"].send_message(ctx["channel_id"], f"> **Dice** :: 🎲 {result}")

    @bot.command(name="rng", aliases=["random", "randnum"])
    def rng_cmd(ctx, args):
        import random as _rand
        lo, hi = 1, 100
        if len(args) >= 2:
            try: lo, hi = int(args[0]), int(args[1])
            except Exception: pass
        elif len(args) == 1:
            try: hi = int(args[0])
            except Exception: pass
        val = _rand.randint(min(lo, hi), max(lo, hi))
        msg = ctx["api"].send_message(ctx["channel_id"], f"> **RNG** :: 🎲 {val} (range {lo}–{hi})")

    @bot.command(name="choose", aliases=["pick", "choice"])
    def choose_cmd(ctx, args):
        if not args:
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **Choose** :: Usage: `{bot.prefix}choose option1 option2 ...`")
            return
        import random as _rand
        chosen = _rand.choice(args)
        msg = ctx["api"].send_message(ctx["channel_id"], f"> **Choose** :: 🎯 **{chosen}**")

    @bot.command(name="8ball", aliases=["eightball", "8b"])
    def eightball_cmd(ctx, args):
        import random as _rand
        if not args:
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **8Ball** :: Usage: `{bot.prefix}8ball <question>`")
            return
        responses = [
            "It is certain.", "It is decidedly so.", "Without a doubt.", "Yes, definitely.",
            "You may rely on it.", "As I see it, yes.", "Most likely.", "Outlook good.",
            "Yes.", "Signs point to yes.", "Reply hazy, try again.", "Ask again later.",
            "Better not tell you now.", "Cannot predict now.", "Concentrate and ask again.",
            "Don't count on it.", "My reply is no.", "My sources say no.",
            "Outlook not so good.", "Very doubtful.",
        ]
        resp = _rand.choice(responses)
        question = " ".join(args)
        msg = ctx["api"].send_message(ctx["channel_id"], f"> **🎱 8Ball** :: *{question}*\n> {resp}")

    @bot.command(name="rate", aliases=["rateme"])
    def rate_cmd(ctx, args):
        import random as _rand
        if not args:
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **Rate** :: Usage: `{bot.prefix}rate <thing>`")
            return
        thing = " ".join(args)
        rating = _rand.randint(0, 10)
        bar = "█" * rating + "░" * (10 - rating)
        msg = ctx["api"].send_message(ctx["channel_id"], f"> **Rate** :: **{thing}** — {rating}/10 `{bar}`")

    @bot.command(name="ascii")
    def ascii_cmd(ctx, args):
        if not args:
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **ASCII** :: Usage: `{bot.prefix}ascii <text>`")
            return
        text = " ".join(args)
        codes = " · ".join(f"`{c}` = {ord(c)}" for c in text[:20])
        msg = ctx["api"].send_message(ctx["channel_id"], f"> **ASCII** :: {codes}")

    @bot.command(name="copycat", aliases=["say", "echo2"])
    def copycat_cmd(ctx, args):
        if not args:
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **Copycat** :: Usage: `{bot.prefix}copycat <text>`")
            return
        msg = ctx["api"].send_message(ctx["channel_id"], " ".join(args))

    @bot.command(name="vanity", aliases=["servervanity", "guildvanity"])
    def vanity_cmd(ctx, args):
        guild_id = ctx.get("guild_id") or (ctx.get("message") or {}).get("guild_id")
        if not guild_id:
            msg = ctx["api"].send_message(ctx["channel_id"], "> **Vanity** :: Must be in a server")
            return
        try:
            data = ctx["api"].request("GET", f"/guilds/{guild_id}/vanity-url")
            code = (data or {}).get("code")
            if code:
                msg = ctx["api"].send_message(ctx["channel_id"],
                    f"> **Vanity** :: `discord.gg/{code}` · Uses: **{(data or {}).get('uses', '?')}**")
            else:
                msg = ctx["api"].send_message(ctx["channel_id"], "> **Vanity** :: This server has no vanity URL")
        except Exception as e:
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **✗ Vanity** :: {e}")

    @bot.command(name="permissions", aliases=["perms", "mperms"])
    def permissions_cmd(ctx, args):
        guild_id = ctx.get("guild_id") or (ctx.get("message") or {}).get("guild_id")
        if not guild_id:
            msg = ctx["api"].send_message(ctx["channel_id"], "> **Permissions** :: Must be in a server")
            return
        try:
            member = ctx["api"].request("GET", f"/guilds/{guild_id}/members/@me")
            roles = (member or {}).get("roles") or []
            guild = ctx["api"].request("GET", f"/guilds/{guild_id}")
            all_roles = {r["id"]: r for r in (guild or {}).get("roles") or []}
            perms = 0
            for rid in roles:
                perms |= int((all_roles.get(rid) or {}).get("permissions") or 0)
            perm_names = {
                "Administrator": 1 << 3, "Manage Guild": 1 << 5, "Manage Roles": 1 << 28,
                "Kick Members": 1 << 1, "Ban Members": 1 << 2, "Manage Channels": 1 << 4,
                "Manage Messages": 1 << 13, "Mention Everyone": 1 << 17, "Mute Members": 1 << 22,
            }
            granted = [name for name, bit in perm_names.items() if perms & bit]
            msg = ctx["api"].send_message(ctx["channel_id"],
                f"> **My Permissions** :: `{'` · `'.join(granted) if granted else 'None'}`")
        except Exception as e:
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **✗ Permissions** :: {e}")

    @bot.command(name="inviteme", aliases=["botinvite", "createinvite"])
    def inviteme_cmd(ctx, args):
        guild_id = ctx.get("guild_id") or (ctx.get("message") or {}).get("guild_id")
        if not guild_id:
            msg = ctx["api"].send_message(ctx["channel_id"], "> **CreateInvite** :: Must be used in a server channel")
            return
        max_age = 86400
        max_uses = 0
        if args and args[0].isdigit():
            max_age = int(args[0])
        try:
            data = ctx["api"].request("POST", f"/channels/{ctx['channel_id']}/invites",
                                      json={"max_age": max_age, "max_uses": max_uses, "temporary": False})
            code = (data or {}).get("code")
            msg = ctx["api"].send_message(ctx["channel_id"],
                f"> **✓ Invite** :: `discord.gg/{code}` · Expires: **{max_age // 3600}h**")
        except Exception as e:
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **✗ CreateInvite** :: {e}")

    @bot.command(name="signup", aliases=["authorize", "authbot", "addbot"])
    def signup_cmd(ctx, args):
        """Return OAuth2 authorize links for server install and user install.

        Usage:
            <prefix>signup
            <prefix>signup user
            <prefix>signup <guild_id>
            <prefix>signup <guild_id> <permissions_int>
        """
        cfg = ctx["bot"].config

        # Preferred app id for OAuth2 link generation.
        client_id = str(
            (cfg.get("discord_client_id") or "").strip()
            or (cfg.get("application_id") or "").strip()
        )

        # Fallback: derive application id from bot token's first segment when possible.
        if not client_id.isdigit():
            bot_token = (os.getenv("DISCORD_BOT_TOKEN") or cfg.get("discord_bot_token") or "").strip()
            if bot_token and "." in bot_token:
                try:
                    token_head = bot_token.split(".", 1)[0]
                    padded = token_head + "=" * (-len(token_head) % 4)
                    decoded = base64.urlsafe_b64decode(padded.encode("utf-8")).decode("utf-8", errors="ignore")
                    if decoded.isdigit():
                        client_id = decoded
                except Exception:
                    pass

        if not client_id.isdigit():
            msg = ctx["api"].send_message(
                ctx["channel_id"],
                "> **✗ Signup** :: Missing `discord_client_id` in config. Set it to your bot application's client ID.",
            )
            return

        mode = (str(args[0]).lower() if args else "both")
        target_guild_id = ""
        if mode.isdigit():
            target_guild_id = mode
            mode = "guild"
        elif mode not in {"user", "guild", "both"}:
            mode = "both"

        if not target_guild_id:
            target_guild_id = str(ctx.get("guild_id") or "")

        permissions = "274877924352"  # baseline admin-lite + messaging bits
        if len(args) >= 2 and str(args[1]).isdigit():
            permissions = str(args[1])

        base_url = "https://discord.com/oauth2/authorize"
        redirect_uri = (cfg.get("oauth_redirect_uri") or "").strip()
        redirect_q = f"&redirect_uri={_url_quote(redirect_uri, safe='')}" if redirect_uri else ""

        guild_query = [
            f"client_id={client_id}",
            f"permissions={permissions}",
            "scope=bot%20applications.commands",
            "disable_guild_select=false",
        ]
        if target_guild_id:
            guild_query.append(f"guild_id={target_guild_id}")

        # User-install link for DM/private usage (no bot scope required).
        user_query = [
            f"client_id={client_id}",
            "scope=applications.commands",
            "integration_type=1",
        ]

        guild_invite_url = f"{base_url}?{'&'.join(guild_query)}{redirect_q}"
        user_install_url = f"{base_url}?{'&'.join(user_query)}{redirect_q}"

        if mode == "user":
            msg = ctx["api"].send_message(
                ctx["channel_id"],
                "> **Signup (User Install)** :: Authorize for personal DM/private command use\n"
                f"{user_install_url}\n"
                "> Commands run via the bot app, not as your personal Discord account.",
            )
            return

        if mode == "guild":
            msg = ctx["api"].send_message(
                ctx["channel_id"],
                "> **Signup (Server Install)** :: Add bot to a server\n"
                f"{guild_invite_url}\n"
                "> After authorizing, slash commands should sync.",
            )
            return

        msg = ctx["api"].send_message(
            ctx["channel_id"],
            "> **Signup** :: Choose install type\n"
            f"> **Server Install**\n{guild_invite_url}\n"
            f"> **User Install (DM/private)**\n{user_install_url}\n"
            "> Commands run through the bot app; Discord does not allow executing them as user-account/selfbot commands.",
        )

    @bot.command(name="dashboardurl", aliases=["dashurl", "redirecturl", "oauthredirect"])
    def dashboardurl_cmd(ctx, args):
        """Show dashboard and OAuth redirect config values for quick verification."""
        cfg = ctx["bot"].config
        dashboard_url = str(cfg.get("dashboard_url") or "").strip()
        redirect_uri = str(cfg.get("oauth_redirect_uri") or "").strip()

        dashboard_status = "set" if dashboard_url else "missing"
        redirect_status = "set" if redirect_uri else "missing"

        if dashboard_url and not dashboard_url.startswith(("http://", "https://")):
            dashboard_status = "invalid"
        if redirect_uri and not redirect_uri.startswith(("http://", "https://")):
            redirect_status = "invalid"

        msg = ctx["api"].send_message(
            ctx["channel_id"],
            "> **Dashboard Config**\n"
            f"> dashboard_url: `{dashboard_url or 'not set'}` ({dashboard_status})\n"
            f"> oauth_redirect_uri: `{redirect_uri or 'not set'}` ({redirect_status})\n"
            "> Make sure `oauth_redirect_uri` exactly matches your Discord OAuth2 Redirects entry.",
        )

    # ─── ANTINUKE COMMANDS ──────────────────────────────────────────

    # Global antinuke configuration
    global ANTINUKE_CONFIG
    ANTINUKE_CONFIG = {}  # guild_id -> {"mode": "on"|"off", "actions": ["warn", "kick", "ban"]}

    @bot.command(name="antinuke", aliases=["anti_nuke"])
    def antinuke_cmd(ctx, args):
        if not args:
            p = bot.prefix
            msg = ctx["api"].send_message(
                ctx["channel_id"],
                f"> **Antinuke** :: Usage: {p}antinuke on|off|status|settings — {p}antinuke actions [add|remove|list] <warn|kick|ban>",
            )
            return

        guild_id = str(ctx["guild_id"])
        subcommand = args[0].lower()

        if subcommand == "on":
            if guild_id not in ANTINUKE_CONFIG:
                ANTINUKE_CONFIG[guild_id] = {"mode": "on", "actions": ["warn"]}
            else:
                ANTINUKE_CONFIG[guild_id]["mode"] = "on"
            msg = ctx["api"].send_message(ctx["channel_id"], "> **✓ Antinuke** :: Mode **ON** — protecting against unauthorized changes.")

        elif subcommand == "off":
            if guild_id in ANTINUKE_CONFIG:
                ANTINUKE_CONFIG[guild_id]["mode"] = "off"
            msg = ctx["api"].send_message(ctx["channel_id"], "> **✗ Antinuke** :: Mode **OFF** — disabled.")

        elif subcommand == "status":
            cfg = ANTINUKE_CONFIG.get(guild_id, {})
            mode = cfg.get("mode", "off")
            actions = cfg.get("actions", [])
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **Antinuke** :: Mode **{mode.upper()}** · Actions: {', '.join(actions) if actions else 'none'}")

        elif subcommand == "settings":
            cfg = ANTINUKE_CONFIG.get(guild_id, {})
            mode = cfg.get("mode", "off")
            actions = cfg.get("actions", [])
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **Antinuke** :: Mode **{mode}** · Actions: {actions} · `{bot.prefix}antinuke actions add|remove <action>`")

        elif subcommand == "actions":
            cfg = ANTINUKE_CONFIG.setdefault(guild_id, {"mode": "off", "actions": ["warn"]})
            actions = cfg.setdefault("actions", ["warn"])
            if not isinstance(actions, list):
                actions = ["warn"]
                cfg["actions"] = actions

            allowed = {"warn", "kick", "ban"}
            op = args[1].lower() if len(args) >= 2 else "list"
            val = args[2].lower() if len(args) >= 3 else ""

            if op == "list":
                msg = ctx["api"].send_message(
                    ctx["channel_id"],
                    f"> **Antinuke Actions** :: Current: {', '.join(actions) if actions else 'none'} · Allowed: warn, kick, ban",
                )
                return

            if op not in {"add", "remove"}:
                msg = ctx["api"].send_message(
                    ctx["channel_id"],
                    "> **✗ Antinuke Actions** :: Use: `antinuke actions add|remove|list <warn|kick|ban>`",
                )
                return

            if val not in allowed:
                msg = ctx["api"].send_message(ctx["channel_id"], "> **✗ Antinuke Actions** :: Invalid action. Use: warn, kick, ban")
                return

            if op == "add":
                if val not in actions:
                    actions.append(val)
                msg = ctx["api"].send_message(ctx["channel_id"], f"> **✓ Antinuke Actions** :: Added **{val}** · Current: {', '.join(actions)}")
                return

            if op == "remove":
                if val in actions:
                    actions.remove(val)
                if not actions:
                    actions.append("warn")
                msg = ctx["api"].send_message(ctx["channel_id"], f"> **✗ Antinuke Actions** :: Removed **{val}** · Current: {', '.join(actions)}")
                return

    # ─── SLASH / INTERACTION COMMANDS ──────────────────────────────────────────

    @bot.command(name="slashlist", aliases=["getslash", "slashcmds"])
    def slashlist_cmd(ctx, args):
        """List slash commands for this guild (or global with --me).
        Usage: <prefix>slashlist [guild_id]
               <prefix>slashlist --me"""
        api = ctx["api"]
        channel_id = ctx["channel_id"]
        if args and args[0] == "--me":
            data = api.get_user_slash_commands()
            scope = "your global"
        else:
            guild_id = args[0] if args else ctx.get("guild_id", "")
            if not guild_id:
                api.send_message(channel_id, "> **✗ SlashList** :: Must be in a guild or provide a guild_id.")
                return
            data = api.get_slash_commands(guild_id)
            scope = f"guild `{guild_id}`"
        if not data:
            api.send_message(channel_id, f"> **✗ SlashList** :: Could not fetch slash commands for {scope}.")
            return
        commands = data.get("application_commands") or []
        apps = {a["id"]: a.get("name", "?") for a in (data.get("applications") or [])}
        if not commands:
            api.send_message(channel_id, f"> **SlashList** :: No slash commands found for {scope}.")
            return
        from collections import defaultdict as _dd
        grouped = _dd(list)
        for cmd in commands:
            app_name = apps.get(cmd.get("application_id", ""), cmd.get("application_id", "?"))
            grouped[app_name].append(cmd)
        lines = [f"**Slash Commands — {scope}** ({len(commands)} total)"]
        for app_name, cmds in sorted(grouped.items()):
            lines.append(f"\n**{app_name}**")
            for c in cmds[:20]:
                desc = c.get("description", "").rstrip(".")
                lines.append(f"  `/{c['name']}`  ·  {desc[:60]}" if desc else f"  `/{c['name']}`")
            if len(cmds) > 20:
                lines.append(f"  … and {len(cmds) - 20} more")
        output = "\n".join(lines)
        if len(output) > 1900:
            output = output[:1900] + "\n…"
        api.send_message(channel_id, output)

    @bot.command(name="slash", aliases=["sendslash", "useslash"])
    def slash_cmd(ctx, args):
        """Fire a slash command in the current guild.
        Usage: <prefix>slash <command_name> [guild_id] [option_value ...]"""
        api = ctx["api"]
        channel_id = ctx["channel_id"]
        guild_id = ctx.get("guild_id", "")
        if not args:
            api.send_message(channel_id, f"> **Slash** :: `{bot.prefix}slash <command_name> [guild_id] [option value ...]`")
            return
        cmd_name = args[0].lstrip("/")
        remaining = list(args[1:])
        if remaining and remaining[0].isdigit() and len(remaining[0]) >= 17:
            guild_id = remaining.pop(0)
        if not guild_id:
            api.send_message(channel_id, "> **✗ Slash** :: Not in a guild. Provide a guild_id as the second argument.")
            return
        data = api.get_slash_commands(guild_id)
        if not data:
            api.send_message(channel_id, "> **✗ Slash** :: Could not retrieve slash commands for that guild.")
            return
        commands = data.get("application_commands") or []
        target = next((c for c in commands if c.get("name", "").lower() == cmd_name.lower()), None)
        if not target:
            api.send_message(channel_id, f"> **✗ Slash** :: Command `/{cmd_name}` not found in that guild.")
            return
        options = []
        for val in remaining:
            options.append({"type": 3, "name": "value", "value": val})
        ok = api.send_slash_command(channel_id, guild_id, target, options if options else None)
        if ok:
            api.send_message(channel_id, f"> **✓ Slash** :: Fired `/{target['name']}` in <#{channel_id}>.")
        else:
            api.send_message(channel_id, "> **✗ Slash** :: Interaction failed — bot may lack access or command needs specific options.")

    @bot.command(name="clickbutton", aliases=["btnclick", "clickbtn"])
    def clickbutton_cmd(ctx, args):
        """Click a message component button.
        Usage: <prefix>clickbutton <message_id> <custom_id> [channel_id] [app_id]"""
        api = ctx["api"]
        channel_id = ctx["channel_id"]
        guild_id = ctx.get("guild_id", "")
        if len(args) < 2:
            api.send_message(channel_id, f"> **ClickButton** :: `{bot.prefix}clickbutton <message_id> <custom_id> [channel_id] [app_id]`")
            return
        message_id = args[0]
        custom_id = args[1]
        target_channel = args[2] if len(args) > 2 else channel_id
        app_id = args[3] if len(args) > 3 else ""
        if not app_id:
            msg_resp = api.request("GET", f"/channels/{target_channel}/messages/{message_id}")
            if msg_resp and msg_resp.status_code == 200:
                msg_data = msg_resp.json()
                app_id = (msg_data.get("application_id") or msg_data.get("author", {}).get("id", ""))
            if not app_id:
                api.send_message(channel_id, "> **✗ ClickButton** :: Could not determine application_id. Pass it explicitly.")
                return
        ok = api.click_button(guild_id, target_channel, message_id, app_id, custom_id)
        if ok:
            api.send_message(channel_id, f"> **✓ ClickButton** :: Clicked `{custom_id}` on message `{message_id}`.")
        else:
            api.send_message(channel_id, "> **✗ ClickButton** :: Interaction failed.")

    # ─── READALL / READALLDMS COMMANDS ──────────────────────────────────────

    @bot.command(name="readall", aliases=["readguild", "dumpguild"])
    def readall_cmd(ctx, args):
        """Read recent messages from all channels in this guild.
        Usage: <prefix>readall [limit_per_channel] [guild_id]"""
        api = ctx["api"]
        channel_id = ctx["channel_id"]
        guild_id = ctx.get("guild_id", "")
        limit = 10
        for a in args:
            if a.isdigit() and len(a) < 5:
                limit = max(1, min(int(a), 50))
            elif a.isdigit() and len(a) >= 17:
                guild_id = a
        if not guild_id:
            api.send_message(channel_id, "> **✗ ReadAll** :: Not in a guild. Provide a guild_id.")
            return
        status = api.send_message(channel_id, f"> **ReadAll** :: Fetching up to {limit} messages/channel…")
        status_id = (status or {}).get("id")
        ch_resp = api.request("GET", f"/guilds/{guild_id}/channels")
        if not ch_resp or ch_resp.status_code != 200:
            api.edit_message(channel_id, status_id, "> **✗ ReadAll** :: Could not fetch channels.")
            return
        text_types = {0, 5, 10, 11, 12}
        channels = [c for c in (ch_resp.json() or []) if c.get("type") in text_types]
        if not channels:
            api.edit_message(channel_id, status_id, "> **ReadAll** :: No readable channels found.")
            return
        all_msgs = []
        skipped = 0
        import time as _rt
        for ch in channels:
            cid_ = ch.get("id")
            if not cid_:
                continue
            r = api.request("GET", f"/channels/{cid_}/messages?limit={limit}")
            if r and r.status_code == 200:
                msgs = r.json() or []
                for m in msgs:
                    all_msgs.append({
                        "channel": ch.get("name", cid_),
                        "author": m.get("author", {}).get("username", "?"),
                        "content": (m.get("content") or "")[:80],
                        "ts": m.get("timestamp", "")[:10],
                    })
            else:
                skipped += 1
            _rt.sleep(0.25)
        all_msgs.sort(key=lambda x: x["ts"], reverse=True)
        top = all_msgs[:80]
        lines = [f"**ReadAll — {len(channels)} channels, {len(all_msgs)} messages**"
                 + (f" ({skipped} skipped/no-access)" if skipped else "")]
        for m in top:
            snippet = m["content"].replace("\n", " ") or "<no text>"
            lines.append(f"`#{m['channel']}` **{m['author']}**: {snippet}")
        output = "\n".join(lines)
        if len(output) > 1900:
            output = output[:1900] + "\n…"
        api.edit_message(channel_id, status_id, output)

    @bot.command(name="readalldms", aliases=["readdms", "dumpdms"])
    def readalldms_cmd(ctx, args):
        """Read recent messages from all open DMs.
        Usage: <prefix>readalldms [limit_per_dm]"""
        api = ctx["api"]
        channel_id = ctx["channel_id"]
        limit = 10
        for a in args:
            if a.isdigit() and len(a) < 5:
                limit = max(1, min(int(a), 50))
        status = api.send_message(channel_id, f"> **ReadAllDMs** :: Fetching up to {limit} messages/DM…")
        status_id = (status or {}).get("id")
        dms = api.get_dm_channels(force=False) if hasattr(api, "get_dm_channels") else []
        if not dms:
            api.edit_message(channel_id, status_id, "> **✗ ReadAllDMs** :: Could not fetch DM channels.")
            return
        dms = [c for c in dms if c.get("type") in (1, 3)]
        if not dms:
            api.edit_message(channel_id, status_id, "> **ReadAllDMs** :: No DM channels found.")
            return
        import time as _rdmt
        all_msgs = []
        for dm in dms:
            cid_ = dm.get("id")
            if not cid_:
                continue
            if dm.get("type") == 1:
                recips = dm.get("recipients", [{}])
                dm_name = recips[0].get("username", cid_) if recips else cid_
            else:
                dm_name = dm.get("name") or "Group DM"
            r = api.request("GET", f"/channels/{cid_}/messages?limit={limit}")
            if r and r.status_code == 200:
                msgs = r.json() or []
                for m in msgs:
                    all_msgs.append({
                        "dm": dm_name,
                        "author": m.get("author", {}).get("username", "?"),
                        "content": (m.get("content") or "")[:80],
                        "ts": m.get("timestamp", "")[:10],
                    })
            _rdmt.sleep(0.2)
        all_msgs.sort(key=lambda x: x["ts"], reverse=True)
        top = all_msgs[:80]
        lines = [f"**ReadAllDMs — {len(dms)} DMs, {len(all_msgs)} messages**"]
        for m in top:
            snippet = m["content"].replace("\n", " ") or "<no text>"
            lines.append(f"**@{m['dm']}** · *{m['author']}*: {snippet}")
        output = "\n".join(lines)
        if len(output) > 1900:
            output = output[:1900] + "\n…"
        api.edit_message(channel_id, status_id, output)

    # ─── AUTOBUMP COMMANDS ──────────────────────────────────────────────────

    # Global autobump configuration
    global AUTOBUMP_CONFIG
    AUTOBUMP_CONFIG = {}  # guild_id -> {"channel_id": "...", "interval": 3600}

    @bot.command(name="bump", aliases=["autobump"])
    def bump_cmd(ctx, args):
        if not args:
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **Autobump** :: Usage: {bot.prefix}bump config <channel_id> <interval_seconds> | {bot.prefix}bump list | {bot.prefix}bump stop")
            return
        
        guild_id = str(ctx["guild_id"])
        subcommand = args[0].lower()
        
        if subcommand == "config":
            if len(args) < 3:
                msg = ctx["api"].send_message(ctx["channel_id"], f"> **Autobump** :: Usage: {bot.prefix}bump config <channel_id> <interval_seconds>")
                return
            
            channel_id = args[1]
            try:
                interval = int(args[2])
                if interval < 300:
                    msg = ctx["api"].send_message(ctx["channel_id"], "> **✗ Autobump** :: Interval must be at least 300 seconds (5 minutes)")
                    return
            except ValueError:
                msg = ctx["api"].send_message(ctx["channel_id"], "> **✗ Autobump** :: Interval must be a number (seconds)")
                return
            
            AUTOBUMP_CONFIG[guild_id] = {"channel_id": channel_id, "interval": interval}
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **✓ Autobump** :: Configured — Channel {channel_id} · Interval {interval}s")
        
        elif subcommand == "list":
            cfg = AUTOBUMP_CONFIG.get(guild_id)
            if cfg:
                msg = ctx["api"].send_message(ctx["channel_id"], f"> **Autobump Config** :: Channel {cfg['channel_id']} · Interval {cfg['interval']}s")
            else:
                msg = ctx["api"].send_message(ctx["channel_id"], "> **Autobump** :: No autobump configured")
        
        elif subcommand == "stop":
            if guild_id in AUTOBUMP_CONFIG:
                AUTOBUMP_CONFIG.pop(guild_id)
            msg = ctx["api"].send_message(ctx["channel_id"], "> **✗ Autobump** :: Stopped.")

    @bot.command(name="help", aliases=["h", "commands"])
    def show_help(ctx, args):
        import formatter as fmt
        p = bot.prefix  # live prefix — auto-reflects config changes
        category_header_map = {
            "general": "General",
            "utility": "Utility",
            "messaging": "Messaging",
            "profile": "Profile",
            "server": "Server",
            "voice": "Voice",
            "social": "Social",
            "fun": "Fun",
            "rpc": "RPC",
            "boost": "Boost",
            "backup": "Backup",
            "moderation": "Moderation",
            "antinuke": "Antinuke",
            "nuke": "Nuke",
            "hosting": "Hosting",
            "token": "Token",
            "afk": "AFK",
            "nitro": "Nitro",
            "agct": "AGCT",
            "quest": "Quest",
            "owner": "Owner",
        }
        command_category_exact = {}
        command_category_primary = {}

        def help_page(title, *lines):
            return {"title": title, "lines": list(lines)}

        def render_help_page(page_name, content, current_page, total_pages):
            lines = content.get("lines", [])

            normalized_page = " ".join(str(page_name).lower().split())
            is_category_page = normalized_page in category_header_map
            if normalized_page in category_header_map:
                header_base = category_header_map[normalized_page]
            elif normalized_page in command_category_exact:
                header_base = command_category_exact[normalized_page]
            else:
                first_token = normalized_page.split()[0] if normalized_page else ""
                first_token = first_token.split("_")[0]
                header_base = command_category_primary.get(first_token, first_token.title() if first_token else "Help")

            out = []
            for line in lines:
                if isinstance(line, tuple) and len(line) == 2:
                    out.append(f"{fmt.PINK}{line[0]:<24}{fmt.DARK}:: {fmt.RESET}{fmt.GREEN}{line[1]}{fmt.RESET}")
                elif isinstance(line, dict) and line.get("type") == "section":
                    section_text = str(line.get("text", "")).strip().lower()
                    if section_text in {"tip", "tips", "note", "notes", "usage"}:
                        continue
                    out.append(f"  [{line['text']}]")
                elif line == "":
                    out.append("")
                else:
                    line_text = str(line)
                    if line_text.strip().lower().startswith(("tip:", "note:", "usage:")):
                        continue
                    out.append(line_text)
            body = "\n".join(out)

            header_text = header_base
            
            parts = [
                fmt.header(header_text),
                fmt._block(f"{body}"),
            ]

            if is_category_page and total_pages > 1:
                footer_line = (
                    f"{fmt.DARK}page {current_page}/{total_pages}{fmt.RESET}"
                    f" {fmt.DARK}|{fmt.RESET} "
                    f"{fmt.GREEN}{p}help {page_name} <1-{total_pages}>{fmt.RESET}"
                )
                parts.append(fmt._block(footer_line))

            return "\n".join(parts)

        help_pages = {
            # ── General ──────────────────────────────────────────────────────
            "general": {
                "title": f"{p}help General",
                "lines": [
                    ("help [section|command]", "Open the main help system"),
                    ("helpwall", "Show the full command wall"),
                    ("quickhelp", "Show common starter commands"),
                    ("categories", "List command-engine categories"),
                    ("commands", "Show command overview"),
                    ("ping", "Test bot latency"),
                    ("profile [user_id]", "Show a user profile"),
                    ("guilds", "List your guilds"),
                    ("signup [user|guild_id] [perms]", "Get user-install and/or server-install authorize links"),
                    ("autoreact <@user> <emoji...>", "Set auto-reactions for a target user"),
                    ("mimic <@user> [reply]", "Mimic a user or one-off echo"),
                    ("bold <text>", "Make text bold"),
                    ("italic <text>", "Make text italic"),
                    ("quote <text>", "Quote text"),
                    ("mock <text>", "Mock text"),
                    ("flip <text>", "Flip text upside down"),
                    ("version", "Show Aria version"),
                    ("restart", "Restart the bot"),
                ],
            },

            # ── Utility ──────────────────────────────────────────────────────
            "utility": {
                "title": f"{p}help Utility",
                "lines": [
                    ("ms", "Test bot latency"),
                    ("purge <amount|all> [-e] [-r] [-s] [channel_id]", "Advanced message purge"),
                    ("spurge", "Stop active purge"),
                    ("guilds", "Count guilds"),
                    ("mutualinfo [user_id]", "Show mutual servers"),
                    ("autoreact <@user> <emoji...>", "Configure target auto-reactions"),
                    ("hypesquad <house>", "Set HypeSquad house"),
                    ("hypesquad_leave", "Leave HypeSquad"),
                    ("status <state>", "Set account status"),
                    ("client <type>", "Switch client type"),
                    ("setprefix <symbol>", "Change command prefix"),
                    ("customize", "UI/terminal customization"),
                    ("terminal", "Terminal settings"),
                    ("ui", "Interface settings"),
                    ("stop", "Stop bot"),
                    ("web", "Start read-only web panel"),
                    ("restart", "Restart bot"),
                ],
            },

            "ms": help_page(
                f"{p}ms",
                "Tests bot latency by measuring round-trip message time.",
                "",
                {"type": "section", "text": "Aliases"},
                "ping",
            ),

                        "purge": help_page(
                            f"{p}purge <amount|all> [-e] [-r] [-s] [channel_id]",
                            "Deletes messages with optional filters/order in a channel.",
                                "",
                                {"type": "section", "text": "Arguments"},
                            ("amount|all", "Count to delete or all matched messages"),
                            ("-e", "Include everyone (not just your messages)"),
                            ("-r", "Delete oldest first"),
                            ("-s", "Silent mode (minimal output)"),
                            ("channel_id", "Optional target channel"),
                        ),

            "guilds": help_page(
                f"{p}guilds",
                "Displays the total number of servers the account is in.",
            ),

                        "mutualinfo": help_page(
                                f"{p}mutualinfo <user_id>",
                                "Shows all mutual servers shared with another user.",
                                "",
                                {"type": "section", "text": "Arguments"},
                                ("user_id", "Discord user ID to check"),
                        ),

                        "autoreact": help_page(
                            f"{p}autoreact <@user|user_id> <emoji...>",
                            "Configures auto-reactions for a specific target user.",
                                "",
                                {"type": "section", "text": "Arguments"},
                            ("target", "Target user mention or ID"),
                            ("emoji...", "One or more emojis"),
                            "",
                            {"type": "section", "text": "Examples"},
                            f"{p}ar <@123> 😀 🔥",
                            f"{p}ar <@123> 😀 . 🔥 . 💀",
                            f"{p}ar clear [user_id]",
                        ),

                        "hypesquad": help_page(
                            f"{p}hypesquad <bravery|brilliance|balance>",
                            "Sets your Discord HypeSquad house.",
                            "",
                            {"type": "section", "text": "Aliases"},
                            "changehypesquad, hs",
                            "",
                            {"type": "section", "text": "Arguments"},
                            ("house", "One of bravery, brilliance, or balance"),
                        ),

                    "hypesquad_leave": help_page(
                    f"{p}hypesquad_leave",
                    "Leaves your current Discord HypeSquad house.",
                    "",
                    {"type": "section", "text": "Aliases"},
                    "leavehypesquad, hsl",
                    ),

                        "status": help_page(
                            f"{p}status <online|idle|dnd|invisible>",
                            "Changes your account presence status.",
                            "",
                            {"type": "section", "text": "Aliases"},
                            "setstatus, changestatus",
                            "",
                            {"type": "section", "text": "Arguments"},
                            ("state", "One of online, idle, dnd, or invisible"),
                        ),

                        "client": help_page(
                            f"{p}client <web|desktop|mobile|vr>",
                            "Switches the client platform Discord sees for this session.",
                            "",
                            {"type": "section", "text": "Aliases"},
                            "clienttype, ct",
                            "",
                            {"type": "section", "text": "Arguments"},
                            ("type", "One of web, desktop, mobile, or vr"),
                        ),

                        "setprefix": help_page(
                                f"{p}setprefix <symbol>",
                                "Changes the bot command prefix.",
                                "",
                                {"type": "section", "text": "Arguments"},
                                ("symbol", "New prefix character or string"),
                        ),

            "customize": help_page(f"{p}customize", "Opens the UI/terminal customization menu."),

            "terminal": help_page(f"{p}terminal", "Opens terminal emulation settings."),

            "ui": help_page(f"{p}ui", "Opens the interface settings menu."),

            "stop": help_page(f"{p}stop", "Stops the bot process entirely."),

            "web": help_page(f"{p}web", "Starts a read-only web panel for monitoring the bot."),

            "restart": help_page(f"{p}restart", "Restarts the bot process."),

            # ── Messaging ────────────────────────────────────────────────────
            "messaging": {
                "title": f"{p}help Messaging",
                "lines": [
                    ("spam <count> <text>", "Spam messages"),
                    ("massdm <option> <msg>", "Mass DM (1=DM history, 2=friends, 3=both)"),
                    ("closedms", "Close all DM channels"),
                    ("superreact <user_id> <emoji...>", "Auto super-react (single/multi/cycle)"),
                    ("superreactlist", "List active super-reaction targets"),
                    ("superreactstop [user_id]", "Stop worker or remove a target"),
                    ("mimic <@user> [reply]", "Mimic a target user"),
                    ("stopmock", "Stop active mimic"),
                ],
            },

                        "spam": help_page(
                                f"{p}spam <count> <text>",
                                "Sends a message repeatedly in the current channel.",
                                "",
                                {"type": "section", "text": "Arguments"},
                                ("count", "Number of times to send the message"),
                                ("text", "Message content to spam"),
                        ),

                        "massdm": help_page(
                                f"{p}massdm <option> <msg>",
                                "Sends a DM to a large group of users.",
                                "",
                                {"type": "section", "text": "Arguments"},
                                ("option", "Who to DM"),
                                "1 = Users from DM history",
                                "2 = Friends list",
                                "3 = Both DM history and friends",
                                ("msg", "Message content to send"),
                        ),

                            "superreact": help_page(
                                f"{p}superreact <user_id> <emoji...>",
                                "Adds or updates a target for automatic super-reactions.",
                                "",
                                {"type": "section", "text": "Aliases"},
                                "sr",
                                "",
                                {"type": "section", "text": "Arguments"},
                                ("user_id", "Target user ID or mention"),
                                ("emoji...", "Single emoji, multi emoji list, or dot-separated cycle groups"),
                                "",
                                {"type": "section", "text": "Examples"},
                                f"{p}sr <@123> 😀",
                                f"{p}sr <@123> 😀 🔥",
                                f"{p}sr <@123> 😀 . 🔥 . 💀",
                            ),

                        "superreactlist": help_page(
                        f"{p}superreactlist",
                        "Displays all configured super-reaction targets.",
                        "",
                        {"type": "section", "text": "Aliases"},
                        "srlist",
                        ),

                            "superreactstop": help_page(
                                f"{p}superreactstop [user_id]",
                                "Stops the super-reaction worker or removes a single target.",
                                "",
                                {"type": "section", "text": "Aliases"},
                                "srstop",
                                "",
                                {"type": "section", "text": "Arguments"},
                                ("user_id", "Optional target user ID or mention to remove"),
                            ),

            "closedms": help_page(f"{p}closedms", "Closes all open DM channels from your inbox."),

            # ── Profile ──────────────────────────────────────────────────────
            "profile": {
                "title": f"{p}help Profile",
                "lines": [
                    ("avatar [user_id]", "Get avatar/banner URLs"),
                    ("setpfp <url>", "Set profile picture"),
                    ("stealpfp <user_id>", "Steal user PFP"),
                    ("setbanner <url>", "Set banner"),
                    ("stealbanner <user_id>", "Steal user banner"),
                    ("setpronouns <text>", "Set pronouns"),
                    ("setbio <text>", "Set bio"),
                    ("setdisplayname <text>", "Set display name"),
                    ("stealname <user_id>", "Steal display name"),
                    ("setstatus [emoji,] text", "Set custom status"),
                    ("stealstatus <user_id>", "Steal user status"),
                    ("pronouns [user_id]", "View pronouns"),
                    ("bio [user_id]", "View bio"),
                    ("displayname [user_id]", "View display name"),
                    ("badges user <user_id>", "Scrape user badges"),
                ],
            },

                        "avatar": help_page(
                            f"{p}avatar [user_id]",
                            "Gets the avatar URL for yourself or another user, and includes the banner URL if available.",
                            "",
                            {"type": "section", "text": "Aliases"},
                            "av, pfp, pfpurl, getavatar",
                            "",
                            {"type": "section", "text": "Arguments"},
                            ("user_id", "Discord user ID to look up (optional, defaults to you)"),
                        ),

                        "setpfp": help_page(
                                f"{p}setpfp <url>",
                                "Sets your account profile picture from a URL.",
                                "",
                                {"type": "section", "text": "Arguments"},
                                ("url", "Direct URL to a PNG or JPG image"),
                        ),

                        "stealpfp": help_page(
                                f"{p}stealpfp <user_id>",
                                "Copies another user profile picture and sets it as your own.",
                                "",
                                {"type": "section", "text": "Arguments"},
                                ("user_id", "Discord user ID to copy the PFP from"),
                        ),

                        "setbanner": help_page(
                                f"{p}setbanner <url>",
                                "Sets your account profile banner from a URL.",
                                "",
                                {"type": "section", "text": "Arguments"},
                                ("url", "Direct URL to a PNG or JPG image"),
                        ),

                        "stealbanner": help_page(
                                f"{p}stealbanner <user_id>",
                                "Copies another user banner and sets it as your own.",
                                "",
                                {"type": "section", "text": "Arguments"},
                                ("user_id", "Discord user ID to copy banner from"),
                                "",
                                {"type": "section", "text": "Aliases"},
                                "copybanner, takebanner",
                        ),

                        "setpronouns": help_page(
                                f"{p}setpronouns <text>",
                                "Sets your account pronouns field.",
                                "",
                                {"type": "section", "text": "Arguments"},
                                ("text", "Pronouns text (e.g. he/him, she/her, they/them)"),
                                "",
                                {"type": "section", "text": "Aliases"},
                                "setpronoun",
                        ),

                        "setbio": help_page(
                                f"{p}setbio <text>",
                                "Sets your account bio / about me section.",
                                "",
                                {"type": "section", "text": "Arguments"},
                                ("text", "Bio text to display on your profile"),
                                "",
                                {"type": "section", "text": "Aliases"},
                                "setaboutme",
                        ),

                        "setdisplayname": help_page(
                                f"{p}setdisplayname <text>",
                                "Sets your global display name shown instead of username.",
                                "",
                                {"type": "section", "text": "Arguments"},
                                ("text", "Display name to set"),
                                "",
                                {"type": "section", "text": "Aliases"},
                                "setglobalname",
                        ),

                        "stealname": help_page(
                                f"{p}stealname <user_id>",
                                "Copies another user display name and sets it as your own.",
                                "",
                                {"type": "section", "text": "Arguments"},
                                ("user_id", "Discord user ID to copy display name from"),
                        ),

                        "setstatus": help_page(
                                f"{p}setstatus [emoji,] text",
                                "Sets your Discord custom status.",
                                "",
                                {"type": "section", "text": "Arguments"},
                                ("emoji", "Optional emoji before the status (include trailing comma)"),
                                ("text", "Status message text"),
                                "",
                                {"type": "section", "text": "Examples"},
                                f"{p}setstatus hello world",
                                f"{p}setstatus 👋, hey there",
                        ),

                        "stealstatus": help_page(
                                f"{p}stealstatus <user_id>",
                                "Copies another user custom status and sets it as your own.",
                                "",
                                {"type": "section", "text": "Arguments"},
                                ("user_id", "Discord user ID to copy status from"),
                        ),

                        "pronouns": help_page(
                                f"{p}pronouns [user_id]",
                                "Displays pronouns for yourself or another user.",
                                "",
                                {"type": "section", "text": "Arguments"},
                                ("user_id", "Discord user ID to look up (optional, defaults to you)"),
                        ),

                        "bio": help_page(
                                f"{p}bio [user_id]",
                                "Displays the bio/about me for yourself or another user.",
                                "",
                                {"type": "section", "text": "Arguments"},
                                ("user_id", "Discord user ID to look up (optional, defaults to you)"),
                        ),

                        "displayname": help_page(
                                f"{p}displayname [user_id]",
                                "Displays the global display name for yourself or another user.",
                                "",
                                {"type": "section", "text": "Arguments"},
                                ("user_id", "Discord user ID to look up (optional, defaults to you)"),
                                "",
                                {"type": "section", "text": "Aliases"},
                                "globalname",
                        ),

                        "badges": help_page(
                                f"{p}badges user <user_id>",
                                f"{p}badges server <server_id> [limit]",
                                "Scrapes Discord badges from a user or server members.",
                                "",
                                {"type": "section", "text": "Arguments (user)"},
                                ("user_id", "Discord user ID to fetch badges for"),
                                "",
                                {"type": "section", "text": "Arguments (server)"},
                                ("server_id", "Server ID to scrape member badges from"),
                                ("limit", "Max members to scan (optional)"),
                        ),

                        "badges user": help_page(
                                f"{p}badges user <user_id>",
                                "Fetches and displays all Discord badges on a user profile.",
                                "",
                                {"type": "section", "text": "Arguments"},
                                ("user_id", "Discord user ID to look up"),
                        ),

                        "badges server": help_page(
                                f"[ {p}badges server <server_id> [limit] ]",
                                "Scrapes badges from members of a server.",
                                "",
                                {"type": "section", "text": "Arguments"},
                                ("server_id", "ID of the server to scan"),
                                ("limit", "Max number of members to check (optional)"),
                        ),

            # ── Server ───────────────────────────────────────────────────────
            "server": {
                "title": f"{p}help Server",
                "lines": [
                    ("servercopy <server_id>", "Copy server structure"),
                    ("serverload <target_id>", "Load copied server"),
                    ("setserverpfp <url>", "Set server profile picture"),
                    ("badges server <server_id> [limit]", "Scrape server badges"),
                    ("myguilds", "List all your guilds"),
                    ("joininvite <code>", "Join server by invite code"),
                    ("leaveguild <guild_id>", "Leave a specific guild"),
                    ("massleave", "Mass leave from guilds"),
                    ("guildmembers <guild_id>", "List guild members"),
                ],
            },

                        "servercopy": help_page(
                                f"{p}servercopy <server_id>",
                                "Copies the channel and role structure of a server into memory.",
                                "",
                                {"type": "section", "text": "Arguments"},
                                ("server_id", "ID of the server to copy"),
                        ),

                        "serverload": help_page(
                                f"{p}serverload <target_id>",
                                "Applies a previously copied server structure to a target server.",
                                "",
                                {"type": "section", "text": "Arguments"},
                                ("target_id", "ID of the server to overwrite with copied structure"),
                        ),

                        "setserverpfp": help_page(
                                f"{p}setserverpfp <url>",
                                "Sets the current server profile picture from a URL.",
                                "",
                                {"type": "section", "text": "Arguments"},
                                ("url", "Direct URL to a PNG or JPG image"),
                                "",
                                {"type": "section", "text": "Aliases"},
                                "serverspfp, guildpfp",
                        ),

            "myguilds": help_page(
                f"{p}myguilds",
                "Lists all guilds your account is a member of with details.",
                "",
                {"type": "section", "text": "Aliases"},
                "guilds, guildlist, servers",
            ),

                        "joininvite": help_page(
                                f"{p}joininvite <invite_code>",
                                "Joins a Discord server using an invite code.",
                                "",
                                {"type": "section", "text": "Aliases"},
                                "ji, joinserver",
                                "",
                                {"type": "section", "text": "Arguments"},
                                ("invite_code", "Discord invite code or URL"),
                        ),

                        "leaveguild": help_page(
                                f"{p}leaveguild <guild_id>",
                                "Leaves a specific guild.",
                                "",
                                {"type": "section", "text": "Aliases"},
                                "lg, leaveserver",
                                "",
                                {"type": "section", "text": "Arguments"},
                                ("guild_id", "Guild ID to leave"),
                        ),

            "massleave": help_page(
                f"{p}massleave",
                "Leaves multiple guilds at once.",
                "",
                {"type": "section", "text": "Aliases"},
                "ml, leaveall, leavemulti",
            ),

                        "guildmembers": help_page(
                                f"{p}guildmembers <guild_id>",
                                "Lists all members of a specific guild.",
                                "",
                                {"type": "section", "text": "Aliases"},
                                "members, gmembers, listmembers",
                                "",
                                {"type": "section", "text": "Arguments"},
                                ("guild_id", "Guild ID to list members from"),
                        ),

            # ── Token ────────────────────────────────────────────────────────
            "token": {
                "title": f"{p}help Token",
                "lines": [
                    ("checktoken <token>", "Validate a Discord token"),
                    ("bulkcheck", "Bulk token validation"),
                    ("exportguilds", "Export guild data from tokens"),
                ],
            },

                        "checktoken": help_page(
                                f"{p}checktoken <token>",
                                "Validates a Discord token and returns account information.",
                                "",
                                {"type": "section", "text": "Aliases"},
                                "ct, tokencheck, validatetoken",
                                "",
                                {"type": "section", "text": "Arguments"},
                                ("token", "Discord token to validate"),
                        ),

            "bulkcheck": help_page(
                f"{p}bulkcheck",
                "Validates multiple tokens in bulk for validity and account details.",
                "",
                {"type": "section", "text": "Aliases"},
                "bc, bulkvalidate, bvalidate",
            ),

            "exportguilds": help_page(
                f"{p}exportguilds",
                "Exports all guild data to a file (JSON format).",
                "",
                {"type": "section", "text": "Aliases"},
                "eg, dumpguilds, saveguilds",
            ),

            # ── Voice ────────────────────────────────────────────────────────
            "voice": {
                "title": f"{p}help Voice",
                "lines": [
                    ("vc [channel_id]", "Join voice/call"),
                    ("vce", "Leave voice/call"),
                    ("vccam [on/off|channel_id] [channel_id]", "Camera (alias: cam)"),
                    ("vcstream [on/off|channel_id] [channel_id]", "Stream / Go Live (alias: stream)"),
                    ("vcmute [on/off|channel_id] [channel_id]", "Self mute"),
                    ("vcdeaf [on/off|channel_id] [channel_id]", "Self deaf"),
                    ("vcswitch <channel_id>", "Switch voice channel"),
                    ("vcrejoin", "Reconnect to current voice channel"),
                    ("vcstatus", "Show voice connection state"),
                ],
            },

                        "vc": help_page(
                                f"{p}vc [channel_id]",
                                "Joins a voice channel or call.",
                                "",
                                {"type": "section", "text": "Arguments"},
                                ("channel_id", "ID of the voice channel to join (optional)"),
                            "Omit to show current channel / usage",
                            "",
                            {"type": "section", "text": "Aliases"},
                            "voice, joinvc, vcjoin, joinvoice, joincall",
                        ),

            "vce": help_page(f"{p}vce", "Disconnects from the current voice channel or call."),

                        "vccam": help_page(
                                f"{p}vccam [on/off]",
                                "Sets camera state in voice.",
                                "",
                                {"type": "section", "text": "Arguments"},
                                ("on/off", "Turn camera on or off"),
                                ("channel_id", "Optional voice channel id"),
                                "If first arg is a channel_id, camera turns on for that VC.",
                            "",
                            {"type": "section", "text": "Aliases"},
                            "cam, camera, vcam, vcvideo",
                        ),

                        "vcstream": help_page(
                                f"{p}vcstream [on/off]",
                                "Sets Go Live stream state in voice.",
                                "",
                                {"type": "section", "text": "Arguments"},
                                ("on/off", "Start or stop streaming"),
                                ("channel_id", "Optional voice channel id"),
                                "If first arg is a channel_id, stream starts for that VC.",
                            "",
                            {"type": "section", "text": "Aliases"},
                            "stream, golive, vcgo, vcgolive, screenshare, vcscreen",
                        ),

                    "vcmute": help_page(f"{p}vcmute [on/off|channel_id] [channel_id]", "Sets your self-mute state in voice."),
                    "vcdeaf": help_page(f"{p}vcdeaf [on/off|channel_id] [channel_id]", "Sets your self-deaf state in voice."),
                    "vcswitch": help_page(f"{p}vcswitch <channel_id>", "Moves/switches your current voice session to another channel."),
                    "vcrejoin": help_page(f"{p}vcrejoin", "Reconnects to the current voice channel to recover broken VC state."),
                    "vcstatus": help_page(f"{p}vcstatus", "Shows detailed VC state (channel/cam/stream/mute/deaf/ws)."),

            # ── Social ───────────────────────────────────────────────────────
            "social": {
                "title": f"{p}help Social",
                "lines": [
                    ("block <user_id>", "Block user"),
                    ("join <invite>", "Join a server via invite"),
                ],
            },

            # ── Fun ──────────────────────────────────────────────────────────
            "fun": {
                "title": f"{p}help Fun",
                "lines": [
                    ("joke", "Tell a random joke"),
                    ("trivia", "Random trivia question"),
                    ("roast", "Get roasted"),
                    ("compliment", "Get a compliment"),
                    ("mimic <text>", "Echo text (mimic)"),
                    ("snipe", "Snipe last deleted message"),
                    ("editsnipe", "Snipe last edited message"),
                    ("8ball <question>", "Ask the magic 8-ball"),
                    ("coinflip", "Flip a coin"),
                    ("dice [NdX]", "Roll dice (e.g. 2d6)"),
                    ("rng [min] [max]", "Random number"),
                    ("choose <opt1> <opt2>...", "Pick a random option"),
                    ("rate <thing>", "Rate something out of 10"),
                    ("mock <text>", "SpOnGeBoB mOcK tExT"),
                    ("clap <text>", "Add 👏 between words"),
                    ("aesthetic <text>", "Vaporwave fullwidth text"),
                    ("reverse <text>", "Reverse text"),
                    ("big <text>", "Regional indicator big text"),
                    ("spoiler <text>", "Wrap text in spoiler tags"),
                    ("codeblock [lang] <text>", "Wrap in code block"),
                    ("leet <text>", "L33t-speak converter"),
                    ("upper <text>", "UPPERCASE text"),
                    ("lower <text>", "lowercase text"),
                    ("repeat <n> <text>", "Repeat a message N times"),
                    ("scramble <text>", "Scramble each word"),
                    ("zalgo <text>", "Z̷a̵l̸g̴o̶ text"),
                    ("wordcount <text>", "Count words and characters"),
                    ("b64encode <text>", "Base64 encode"),
                    ("b64decode <encoded>", "Base64 decode"),
                    ("charinfo <char>", "Unicode character info"),
                    ("snowflake <id>", "Decode a Discord snowflake"),
                    ("timestamp [unix]", "Discord timestamp formats"),
                    ("calc <expr>", "Calculator (supports math)"),
                    ("hex <number>", "Convert decimal/hex"),
                    ("binary <number>", "Convert decimal/binary"),
                    ("ascii <text>", "Show ASCII codes"),
                ],
            },

            # ── Utility ──────────────────────────────────────────────────────
            "utility": {
                "title": f"{p}help Utility",
                "lines": [
                    ("serverinfo", "Info about current server"),
                    ("membercount", "Member count for server"),
                    ("roleinfo <role_id>", "Info about a role"),
                    ("channelinfo [#channel]", "Info about a channel"),
                    ("inviteinfo <code>", "Inspect an invite"),
                    ("firstmsg [#channel]", "Get first message in a channel"),
                    ("nick [new_nick]", "Change your nickname"),
                    ("customstatus [text]", "Set / clear custom status"),
                    ("purge [count]", "Delete your own messages"),
                    ("pin <msg_id>", "Pin a message"),
                    ("unpin <msg_id>", "Unpin a message"),
                    ("slowmode <secs>", "Set channel slowmode"),
                    ("topic [text]", "Set channel topic"),
                    ("react <msg_id> <emoji>", "Add a reaction"),
                    ("unreact <msg_id> <emoji>", "Remove a reaction"),
                    ("stealemoji <:emoji:>", "Copy emoji to this server"),
                    ("addemoji <name> <url>", "Add emoji from URL"),
                    ("delemoji <emoji_id>", "Delete a server emoji"),
                    ("emojiurl <emoji>", "Get emoji image URL"),
                    ("listemojis", "List all server emojis"),
                    ("vanity", "Show server vanity URL"),
                    ("permissions", "Show your server permissions"),
                    ("createinvite [max_age_secs]", "Create a channel invite"),
                    ("remind <secs> <text>", "Set a reminder"),
                    ("countdown <from> <label>", "Countdown from N"),
                    ("copycat <text>", "Send text as-is"),
                ],
            },

            # ── Antinuke ─────────────────────────────────────────────────────
            "antinuke": {
                "title": f"{p}help Antinuke",
                "lines": [
                    ("antinuke on|off", "Toggle nuke protection"),
                    ("antinuke status", "Check protection status"),
                    ("antinuke settings", "View protection settings"),
                    ("antinuke actions add <action>", "Add response action"),
                    ("antinuke actions remove <action>", "Remove response action"),
                    ("antinuke actions list", "List active response actions"),
                ],
            },

            # ── Nuke ─────────────────────────────────────────────────────────
            "nuke": {
                "title": f"{p}help Nuke",
                "lines": [
                    ("destroy <guild_id>", "Destroy target server (owner/cog command)"),
                    ("kickall <guild_id>", "Mass-kick all members in target server"),
                    ("clearserver <guild_id>", "Clear all channels and roles in target server"),
                ],
            },

            "destroy": help_page(
                f"{p}destroy <guild_id>",
                "Nuke cog command: deletes channels/roles and recreates spam channels in the target guild.",
            ),

            "kickall": help_page(
                f"{p}kickall <guild_id>",
                "Nuke cog command: mass-kicks members from the target guild.",
            ),

            "clearserver": help_page(
                f"{p}clearserver <guild_id>",
                "Nuke cog command: deletes all channels and roles in the target guild.",
            ),

            # ── RPC ──────────────────────────────────────────────────────────
            "rpc": {
                "title": f"{p}help RPC",
                "lines": [
                    ("help rpc music", "Spotify / YT Music / Apple / Deezer / Tidal / SoundCloud"),
                    ("help rpc video", "YouTube / Netflix / Disney+ / Prime / Plex / Jellyfin / Crunchyroll"),
                    ("help rpc social", "Twitch / Kick / Streaming / Playing / Listening"),
                    ("help rpc tools", "Timer / Browser / VSCode / Stop / aliases"),
                    ("rpc stop", "Clear active RPC"),
                ],
            },

            "rpc music": help_page(
                f"{p}rpc <provider> <args>",
                "Music providers: spotify, youtube_music, applemusic, deezer, tidal, soundcloud.",
                "",
                {"type": "section", "text": "Examples"},
                f"{p}rpc spotify song=Nightcall artist=Kavinsky elapsed_minutes=1 total_minutes=4",
                f"{p}rpc youtube_music title=Track context=Playlist elapsed_minutes=2 total_minutes=3",
            ),

            "rpc video": help_page(
                f"{p}rpc <provider> <args>",
                "Video providers: youtube, netflix, disneyplus, primevideo, plex, jellyfin, crunchyroll.",
                "",
                {"type": "section", "text": "Examples"},
                f"{p}rpc youtube title=Video channel=Creator elapsed_minutes=3 total_minutes=10",
                f"{p}rpc crunchyroll name=Show episode_title=E1 elapsed_minutes=5 total_minutes=24",
            ),

            "rpc social": help_page(
                f"{p}rpc <mode> <args>",
                "Social modes: twitch, kick, streaming, playing, listening.",
                "",
                {"type": "section", "text": "Examples"},
                f"{p}rpc twitch title=Live context=Ranked elapsed_minutes=12",
                f"{p}rpc playing name=Valorant details=Competitive state=Immortal",
            ),

            "rpc tools": help_page(
                f"{p}rpc <mode> <args>",
                "Utility modes: timer, browser, vscode, stop.",
                "",
                {"type": "section", "text": "Examples"},
                f"{p}rpc timer name=Session details=Coding state=Focus start=1710000000 end=1710003600",
                f"{p}rpc stop",
                "",
                {"type": "section", "text": "Aliases"},
                "ytmusic/youtubemusic => youtube_music",
                "apple_music => applemusic",
                "disney+, disney_plus => disneyplus",
                "prime, prime_video, amazonprime, amazon_prime => primevideo",
                "chrome, web => browser",
            ),

                        "join": help_page(
                                f"{p}join <invite_code_or_url>",
                                "Joins a server using a Discord invite code or URL.",
                                "",
                                {"type": "section", "text": "Arguments"},
                                ("invite", "Invite code (e.g. abc123) or full URL"),
                                "",
                                {"type": "section", "text": "Aliases"},
                                "joininvite, acceptinvite",
                        ),

                        "rpc mode": help_page(
                            f"{p}rpc <type> <args>",
                            "Sets a custom Rich Presence activity on your account.",
                            "",
                            {"type": "section", "text": "Tip"},
                            f"Use {p}help rpc to see all RPC subcommands and formats.",
                        ),

            # ── Boost ────────────────────────────────────────────────────────
            "boost": {
                "title": f"{p}help Boost",
                "lines": [
                    ("boost <server_id>", "Boost a server"),
                    ("boost transfer <to_id>", "Transfer all available boosts"),
                    ("boost auto <server1,server2,...>", "Auto-boost from list"),
                    ("boost rotate <server1,server2,...> [hours]", "Auto-rotation"),
                    ("boost stop", "Stop rotation"),
                    ("boost status", "Check boost status"),
                    ("boost list", "List boosted servers"),
                ],
            },

                        "boost transfer": help_page(
                                f"{p}boost transfer <to_id>",
                                "Transfers all available boost slots to a server.",
                                "",
                                {"type": "section", "text": "Arguments"},
                                ("to_id", "Server ID to transfer all available boosts to"),
                                "",
                                {"type": "section", "text": "Shows"},
                                "Per-slot ANSI result (green tick / red cross)",
                                "Total success count out of attempted transfers",
                        ),

                        "boost auto": help_page(
                                f"{p}boost auto <server1,server2,...>",
                                "Distributes available boost slots across a list of servers.",
                                "",
                                {"type": "section", "text": "Arguments"},
                                ("server1,server2,...", "Comma-separated server IDs (no spaces)"),
                        ),

                        "boost rotate": help_page(
                                f"{p}boost rotate <server1,server2,...> [hours]",
                                "Cycles boosts through a list of servers on a timer.",
                                "",
                                {"type": "section", "text": "Arguments"},
                                ("server1,server2,...", "Comma-separated server IDs (no spaces)"),
                                ("hours", "Rotation interval in hours (default: 24)"),
                        ),

            "boost stop": help_page(f"{p}boost stop", "Stops the active boost rotation."),

                        "boost status": help_page(
                                f"{p}boost status",
                                "Shows a detailed overview of all boost slots.",
                                "",
                                {"type": "section", "text": "Shows"},
                                ("Total Slots", "Total boost slots on the account"),
                                ("Available", "Slots not currently in use"),
                                ("Used", "Slots actively boosting a server"),
                                ("On Cooldown", "Slots in Discord cooldown period"),
                                ("Boost N", "Time remaining until each slot expires"),
                        ),

            "boost list": help_page(f"{p}boost list", "Lists servers currently boosted by this account (up to 10)."),

            # ── Backup ───────────────────────────────────────────────────────
            "backup": {
                "title": f"{p}help Backup",
                "lines": [
                    ("backup user", "Backup user data, friends, guilds"),
                    ("backup messages <channel_id> [limit]", "Backup channel messages"),
                    ("backup full", "Create complete backup (zipped)"),
                    ("backup list", "List all backups"),
                    ("backup restore <filename>", "Restore from backup"),
                ],
            },

            "backup user": help_page(
                f"{p}backup user",
                "Saves a snapshot of your account data, friends list, and guild membership.",
            ),

                        "backup messages": help_page(
                                f"{p}backup messages <channel_id> [limit]",
                                "Downloads and saves messages from a channel.",
                                "",
                                {"type": "section", "text": "Arguments"},
                                ("channel_id", "ID of the channel to backup"),
                                ("limit", "Max messages to save (optional, default: 100)"),
                        ),

            "backup full": help_page(
                f"{p}backup full",
                "Creates a complete zipped backup of all bot data and account info.",
            ),

            "backup list": help_page(
                f"{p}backup list",
                "Lists all available local backup files.",
            ),

                        "backup restore": help_page(
                                f"{p}backup restore <filename>",
                                "Restores data from a previously saved backup file.",
                                "",
                                {"type": "section", "text": "Arguments"},
                                ("filename", f"Name of the backup file (from {p}backup list)"),
                        ),

            # ── Moderation ───────────────────────────────────────────────────
            "moderation": {
                "title": f"{p}help Moderation",
                "lines": [
                    ("mod kick <user_ids>", "Kick multiple users"),
                    ("mod ban <user_ids> [delete_days]", "Ban users"),
                    ("mod filter add <words>", "Add word filter"),
                    ("mod filter check <text>", "Check text against filters"),
                    ("mod cleanup channels", "Delete all channels"),
                    ("mod cleanup roles", "Delete all roles"),
                    ("mod members [limit]", "List server members"),
                    ("mod channels", "List all channels"),
                    ("mod roles", "List all roles"),
                ],
            },

                        "mod kick": help_page(
                                f"{p}mod kick <user_ids>",
                                "Kicks one or more users from the current server.",
                                "",
                                {"type": "section", "text": "Arguments"},
                                ("user_ids", "Space-separated list of Discord user IDs"),
                        ),

                        "mod ban": help_page(
                                f"{p}mod ban <user_ids> [delete_days]",
                                "Bans one or more users from the current server.",
                                "",
                                {"type": "section", "text": "Arguments"},
                                ("user_ids", "Space-separated list of Discord user IDs"),
                                ("delete_days", "Days of message history to delete (optional, 0-7)"),
                        ),

                        "mod filter": help_page(
                                f"{p}mod filter add <words>",
                                f"{p}mod filter check <text>",
                                "Manages the word filter list.",
                                "",
                                {"type": "section", "text": "Subcommands"},
                                ("add <words>", "Add words to the filter list"),
                                ("check <text>", "Check a string for filtered words"),
                        ),

                        "mod filter add": help_page(
                                f"{p}mod filter add <words>",
                                "Adds words to the word filter list.",
                                "",
                                {"type": "section", "text": "Arguments"},
                                ("words", "Space-separated words to add"),
                        ),

                        "mod filter check": help_page(
                                f"{p}mod filter check <text>",
                                "Tests a string against the current word filter list.",
                                "",
                                {"type": "section", "text": "Arguments"},
                                ("text", "Any text to check for filtered words"),
                        ),

                        "mod cleanup": help_page(
                                f"{p}mod cleanup channels",
                                f"{p}mod cleanup roles",
                                "Bulk-deletes all channels or all roles in the current server.",
                                "",
                                {"type": "section", "text": "Subcommands"},
                                ("channels", "Delete every channel in the server"),
                                ("roles", "Delete every role (excluding @everyone)"),
                        ),

            "mod cleanup channels": help_page(
                f"{p}mod cleanup channels",
                "Deletes every channel in the current server.",
            ),

            "mod cleanup roles": help_page(
                f"{p}mod cleanup roles",
                "Deletes every role in the current server (except @everyone).",
            ),

                        "mod members": help_page(
                                f"{p}mod members [limit]",
                                "Lists members in the current server.",
                                "",
                                {"type": "section", "text": "Arguments"},
                                ("limit", "Max number of members to display (optional)"),
                        ),

            "mod channels": help_page(
                f"{p}mod channels",
                "Lists all channels in the current server with their IDs.",
            ),

            "mod roles": help_page(
                f"{p}mod roles",
                "Lists all roles in the current server with their IDs.",
            ),

            # ── Hosting ──────────────────────────────────────────────────────
            "hosting": {
                "title": f"{p}help Hosting",
                "lines": [
                    ("auth <user_id>", "Grant account access (owner)"),
                    ("unauth <user_id>", "Revoke account access (owner)"),
                    ("authlist", "List authed users"),
                    ("listhosted", "List your hosted tokens"),
                    ("listallhosted", "List all hosted tokens (owner)"),
                    ("stopallhosted", "Stop all hosted tokens now (owner)"),
                    ("restartallhosted", "Restart all hosted tokens now (owner)"),
                    ("clearhost [uid]", "Remove a hosted entry"),
                    ("clearallhosted", "Clear all hosted entries (owner)"),
                ],
            },

            "auth": help_page(
                f"{p}auth <user_id>",
                "Grants account access to a user (owner only).",
                "",
                {"type": "section", "text": "Arguments"},
                ("user_id", "Discord user ID to authorize"),
            ),

            "unauth": help_page(
                f"{p}unauth <user_id>",
                "Revokes account access from a user (owner only).",
                "",
                {"type": "section", "text": "Arguments"},
                ("user_id", "Discord user ID to deauthorize"),
            ),

            "authlist": help_page(
                f"{p}authlist",
                "Lists all currently authorized users.",
            ),

            "listhosted": help_page(
                f"{p}listhosted",
                "Lists your currently hosted tokens.",
            ),

            "listallhosted": help_page(
                f"{p}listallhosted",
                "Lists all hosted tokens (owner only).",
            ),

            "clearhost": help_page(
                f"{p}clearhost [user_id]",
                "Removes a hosted token entry.",
            ),

            "clearallhosted": help_page(
                f"{p}clearallhosted",
                "Clears all hosted token entries (owner only).",
            ),

            "stopallhosted": help_page(
                f"{p}stopallhosted",
                "Stops all running hosted token processes immediately (owner only).",
                "",
                {"type": "section", "text": "Aliases"},
                "stopall, killallhosted",
            ),

            "restartallhosted": help_page(
                f"{p}restartallhosted",
                "Restarts all persisted hosted token processes (owner only).",
                "",
                {"type": "section", "text": "Aliases"},
                "restartall, rebootallhosted",
            ),

            # ── Owner ────────────────────────────────────────────────────────
            "owner": {
                "title": f"{p}help Owner",
                "lines": [
                    ("auth <user_id>", "Grant account access"),
                    ("unauth <user_id>", "Revoke account access"),
                    ("authlist", "List authed users"),
                    ("listallhosted", "List all hosted tokens"),
                    ("stopallhosted", "Stop all hosted tokens now"),
                    ("restartallhosted", "Restart all hosted tokens now"),
                    ("clearallhosted", "Clear all hosted entries"),
                    (f"{p}drun", "Execute commands on instances"),
                    (f"{p}dlog", "Manage developer logging"),
                    (f"{p}ddebug", "Toggle developer debug mode"),
                    (f"{p}dmetrics", "Show developer metrics"),
                    (f"{p}djoininvite", "Join servers with instances"),
                    (f"{p}dleaveguild", "Leave guilds with instances"),
                    (f"{p}dmyguilds", "List guilds for instances"),
                    (f"{p}dmassleave", "Mass leave guilds with instances"),
                    (f"{p}dguildmembers", "List guild members on instances"),
                    (f"{p}dchecktoken", "Validate a token"),
                    (f"{p}dbulkcheck", "Validate multiple tokens"),
                    (f"{p}dexportguilds", "Export guild lists"),
                    (f"{p}dboost", "Run boost commands on instances"),
                    (f"{p}dboosttransfer", "Transfer boosts on instances"),
                    (f"{p}dbooststatus", "Show boost status on instances"),
                    (f"{p}dboostlist", "List boosted servers on instances"),
                    (f"{p}daccountcmd", "Run any command on instances"),
                    (f"{p}drpc", "Run RPC on instances"),
                    (f"{p}drecentmessages", "Show tracked recent messages"),
                ],
            },

                        "drun": help_page(
                                f"{p}drun",
                                "Execute commands on multiple bot instances.",
                                "",
                            f"Format: {p}drun <uid/all/others> [channel_id] <cmd/say> [args...]",
                                "",
                                {"type": "section", "text": "Examples"},
                            f"{p}drun 1 say Hello - Send in current channel",
                            f"{p}drun all cmd ping - Run ping in current channel",
                                f"{p}drun 1 123456789 say Hello - Send message from UID 1",
                                f"{p}drun 1,2,3 123456789 say Hello - Send from multiple UIDs",
                                f"{p}drun all 123456789 cmd ping - Run ping on all instances",
                                f"{p}drun others 123456789 say Hello - Send from all except developer",
                                f"{p}drun 1,2,3 123456789 say -distribute hello hi hey - Different message per instance",
                        ),

                        "dlog": help_page(
                                f"{p}dlog",
                                "Manage developer logging settings.",
                                "",
                                {"type": "section", "text": "Subcommands"},
                                ("enable <type>", "Enable a logging type"),
                                ("disable <type>", "Disable a logging type"),
                                ("debug", "Toggle debug mode"),
                                ("list", "Show active logging"),
                                ("reset [type/all]", "Reset to defaults"),
                                ("metrics", "Show metrics"),
                        ),

            "ddebug": help_page(
                f"{p}ddebug",
                "Toggle debug mode on/off.",
                "",
                "Shows detailed debug information for development.",
            ),

            "dmetrics": help_page(
                f"{p}dmetrics",
                "Display current developer metrics and session stats.",
            ),

                        "djoininvite": help_page(
                                f"{p}djoininvite <uid/all/others> <invite_code>",
                                "Join a server with one or more bot instances.",
                                "",
                                {"type": "section", "text": "Arguments"},
                                ("uid/all/others", "Target instances (uid, all, or others)"),
                                ("invite_code", "Discord invite code (with or without discord.gg/)"),
                                "",
                                {"type": "section", "text": "Examples"},
                                f"{p}djoininvite 1 abc123",
                                f"{p}djoininvite all discord.gg/abc123",
                                f"{p}djoininvite others abc123",
                        ),

                        "dleaveguild": help_page(
                                f"{p}dleaveguild <uid/all/others> <guild_id>",
                                "Leave a guild with one or more bot instances.",
                                "",
                                {"type": "section", "text": "Arguments"},
                                ("uid/all/others", "Target instances"),
                                ("guild_id", "Discord server ID to leave"),
                                "",
                                {"type": "section", "text": "Examples"},
                                f"{p}dleaveguild 1 123456789",
                                f"{p}dleaveguild all 123456789",
                        ),

                        "dmyguilds": help_page(
                                f"{p}dmyguilds [uid/all/others]",
                                "List all guilds for bot instance(s).",
                                "",
                                {"type": "section", "text": "Arguments"},
                                ("uid/all/others", "Target instances (default: all)"),
                                "",
                                "Shows summary of total guilds and owned servers for each instance.",
                        ),

                        "dmassleave": help_page(
                                f"{p}dmassleave <uid/all/others> [all|guild_id1 guild_id2...]",
                                "Leave multiple guilds at once.",
                                "",
                                {"type": "section", "text": "Arguments"},
                                ("uid/all/others", "Target instances"),
                                ("all", "Leave all guilds (except owned ones)"),
                                ("guild_id...", "Specific guild IDs to leave"),
                                "",
                                {"type": "section", "text": "Examples"},
                                f"{p}dmassleave 1 all",
                                f"{p}dmassleave all 123456789 987654321",
                        ),

                        "dguildmembers": help_page(
                                f"{p}dguildmembers <uid/all/others> <guild_id> [limit]",
                                "Show members of a guild.",
                                "",
                                {"type": "section", "text": "Arguments"},
                                ("uid/all/others", "Target instances"),
                                ("guild_id", "Guild ID to list members from"),
                                ("limit", "Number of members to fetch (default: 20, max: 100)"),
                                "",
                                {"type": "section", "text": "Examples"},
                                f"{p}dguildmembers 1 123456789",
                                f"{p}dguildmembers all 123456789 50",
                        ),

                        "dchecktoken": help_page(
                                f"{p}dchecktoken <uid/all/others> <token>",
                                "Validate and inspect a Discord token.",
                                "",
                                {"type": "section", "text": "Arguments"},
                                ("uid/all/others", "Instance to use for validation"),
                                ("token", "Discord token to check"),
                                "",
                                "Shows username, user ID, and account details if valid.",
                        ),

                        "dbulkcheck": help_page(
                                f"{p}dbulkcheck <uid> <token1> <token2> ...",
                                "Check multiple tokens at once.",
                                "",
                                {"type": "section", "text": "Arguments"},
                                ("uid", "Instance to use for validation"),
                                ("token1, token2...", "Tokens to validate (max 20)"),
                                "",
                                "Shows validity status for each token with username if valid.",
                        ),

                        "dexportguilds": help_page(
                                f"{p}dexportguilds <uid/all/others> [filename]",
                                "Export guild list to JSON file.",
                                "",
                                {"type": "section", "text": "Arguments"},
                                ("uid/all/others", "Target instances"),
                                ("filename", "Output filename (default: exported_guilds.json)"),
                                "",
                                "Creates JSON file with guild data (id, name, owner, member count).",
                        ),

                        "dboost": help_page(
                            f"{p}dboost <uid/all/others> <boost_args...>",
                            "Run boost subcommands on selected instances.",
                            "",
                            {"type": "section", "text": "Examples"},
                            f"{p}dboost all status",
                            f"{p}dboost 1 transfer 123456789",
                            f"{p}dboost others list",
                        ),

                        "dboosttransfer": help_page(
                            f"{p}dboosttransfer <uid/all/others> <to_guild_id>",
                            "Transfer available boosts to a guild from selected instances.",
                            "",
                            {"type": "section", "text": "Examples"},
                            f"{p}dboosttransfer all 123456789",
                            f"{p}dboosttransfer 1,2,3 123456789",
                        ),

                        "dbooststatus": help_page(
                            f"{p}dbooststatus [uid/all/others]",
                            "Show boost status from selected instances.",
                            "",
                            {"type": "section", "text": "Examples"},
                            f"{p}dbooststatus",
                            f"{p}dbooststatus all",
                            f"{p}dbooststatus others",
                        ),

                        "dboostlist": help_page(
                            f"{p}dboostlist [uid/all/others]",
                            "List boosted servers from selected instances.",
                            "",
                            {"type": "section", "text": "Examples"},
                            f"{p}dboostlist",
                            f"{p}dboostlist all",
                            f"{p}dboostlist 1,2",
                        ),

                        "daccountcmd": help_page(
                            f"{p}daccountcmd <uid/all/others> <command> [args...]",
                            "Run any existing command across selected instances.",
                            "",
                            {"type": "section", "text": "Examples"},
                            f"{p}daccountcmd all joininvite abc123",
                            f"{p}daccountcmd others checktoken token_here",
                            f"{p}daccountcmd 1,2 boost status",
                        ),

                        "drpc": help_page(
                            f"{p}drpc <uid/all/others> <rpc_mode> [rpc_args...]",
                            "Run rich presence modes on selected instances.",
                            "",
                            {"type": "section", "text": "Examples"},
                            f"{p}drpc all stop",
                            f"{p}drpc 1 spotify Song | Artist | Album | 1.0 | 3.5",
                            f"{p}drpc others youtube Title | Channel | 2.0 | 10",
                            f"{p}drpc all crunchyroll name=Solo episode_title=Ep1 elapsed_minutes=3 total_minutes=24",
                        ),

                        "drecentmessages": help_page(
                                f"{p}drecentmessages [user] [amount] [channel]",
                                "Retrieve tracked messages from database with flexible filtering.",
                                "",
                                {"type": "section", "text": "Usage"},
                                f"{p}drecentmessages — Show most recent tracked messages in current channel",
                                f"{p}drecentmessages @user/ID — Show tracked messages from user",
                                f"{p}drecentmessages <amount> — Show X most recent tracked messages in channel",
                                f"{p}drecentmessages @user/ID <amount> — Show X recent messages from user",
                                f"{p}drecentmessages #channel — Show messages in specified channel",
                                f"{p}drecentmessages <amount> #channel — Show X messages in channel",
                                f"{p}drecentmessages @user/ID #channel — Show user messages in channel",
                                f"{p}drecentmessages @user/ID <amount> #channel — Show X user messages in channel",
                                "",
                                {"type": "section", "text": "Arguments"},
                                ("user", "Target user (mention or ID) - optional"),
                                ("amount", "Number of messages (default: 10, max: 50) - optional"),
                                ("channel", "Target channel (mention or ID) - optional, defaults to current channel"),
                                "",
                                {"type": "section", "text": "Examples"},
                                f"{p}drecentmessages",
                                f"{p}drecentmessages @username 25",
                                f"{p}drecentmessages 123456789 #channel-name",
                                f"{p}drecentmessages @user 30 #general",
                        ),

            # ── AFK ──────────────────────────────────────────────────────────
            "afk": {
                "title": f"{p}help AFK",
                "lines": [
                    ("afk [reason]", "Set AFK status"),
                    ("afkstatus [user_id]", "Check AFK status"),
                    ("afkwebhook <url>", "Set notification webhook"),
                ],
            },

                        "afkstatus": help_page(
                                f"{p}afkstatus [user_id]",
                                "Checks the AFK status of yourself or another user.",
                                "",
                                {"type": "section", "text": "Arguments"},
                                ("user_id", "Discord user ID to check (optional, defaults to you)"),
                        ),

                        "afkwebhook": help_page(
                                f"{p}afkwebhook <url>",
                                "Sets a webhook URL to receive notifications when someone mentions you while AFK.",
                                "",
                                {"type": "section", "text": "Arguments"},
                                ("url", "Discord webhook URL to send notifications to"),
                        ),

            # ── Nitro ────────────────────────────────────────────────────────
            "nitro": {
                "title": f"{p}help Nitro",
                "lines": [
                    ("nitro on/off", "Toggle nitro sniper"),
                    ("giveaway [on|off]", "Manage giveaway sniper"),
                    ("nitro clear", "Clear used codes"),
                    ("nitro stats", "Show stats"),
                    ("nitro", "Show current status"),
                ],
            },

            "nitro on": help_page(f"{p}nitro on", "Enables the Nitro code sniper."),

            "nitro off": help_page(f"{p}nitro off", "Disables the Nitro code sniper."),

            "nitro clear": help_page(f"{p}nitro clear", "Clears the list of already-seen Nitro codes from memory."),

                    "giveaway": help_page(
                                f"{p}giveaway [on|off]",
                        "Shows giveaway sniper status or toggles it on and off.",
                        "",
                        {"type": "section", "text": "Aliases"},
                        "gw, gsnipe",
                        "",
                        {"type": "section", "text": "Arguments"},
                        ("on/off", "Optional toggle action; omit to show current stats"),
                    ),

                        "nitro stats": help_page(
                                f"{p}nitro stats",
                                "Shows Nitro sniper statistics.",
                                "",
                                {"type": "section", "text": "Shows"},
                                ("Codes Seen", "Total codes the sniper detected"),
                                ("Codes Claimed", "Codes successfully redeemed"),
                                ("Codes Failed", "Codes that were invalid or already used"),
                        ),

            # ── AGCT ─────────────────────────────────────────────────────────
            "agct": {
                "title": f"{p}help AGCT",
                "lines": [
                    ("agct on/off", "Toggle anti-GC trap"),
                    ("agct block on/off", "Toggle blocking creators"),
                    ("agct msg <text>", "Set leave message"),
                    ("agct name <name>", "Set GC name"),
                    ("agct icon <url>", "Set GC icon"),
                    ("agct webhook <url>", "Set alert webhook"),
                    ("agct wl add <user_id>", "Add to whitelist"),
                    ("agct wl remove <user_id>", "Remove from whitelist"),
                    ("agct wl list", "Show whitelist"),
                ],
            },

            "agct on": help_page(f"{p}agct on", "Enables the Anti-GC Trap system."),

            "agct off": help_page(f"{p}agct off", "Disables the Anti-GC Trap system."),

                        "agct block": help_page(
                                f"{p}agct block on/off",
                                "Toggles whether GC trap creators are automatically blocked.",
                                "",
                                {"type": "section", "text": "Arguments"},
                                ("on", "Enable auto-blocking of trap creators"),
                                ("off", "Disable auto-blocking"),
                        ),

            "agct block on": help_page(f"{p}agct block on", "Enables auto-blocking of group chat trap creators."),

            "agct block off": help_page(f"{p}agct block off", "Disables auto-blocking of group chat trap creators."),

                        "agct msg": help_page(
                                f"{p}agct msg <text>",
                                "Sets the message sent in a GC trap before the bot leaves.",
                                "",
                                {"type": "section", "text": "Arguments"},
                                ("text", "Message to send before leaving the group chat"),
                        ),

                        "agct name": help_page(
                                f"{p}agct name <name>",
                                "Sets the GC name string used to identify group chat traps.",
                                "",
                                {"type": "section", "text": "Arguments"},
                                ("name", "GC name pattern to watch for"),
                        ),

                        "agct icon": help_page(
                                f"{p}agct icon <url>",
                                "Sets the icon URL used to identify group chat traps.",
                                "",
                                {"type": "section", "text": "Arguments"},
                                ("url", "Image URL of the GC icon to watch for"),
                        ),

                        "agct webhook": help_page(
                                f"{p}agct webhook <url>",
                                "Sets a Discord webhook URL for AGCT alert notifications.",
                                "",
                                {"type": "section", "text": "Arguments"},
                                ("url", "Discord webhook URL to send alerts to"),
                        ),

                        "agct wl": help_page(
                                f"{p}agct wl add <user_id>",
                                f"{p}agct wl remove <user_id>",
                                f"{p}agct wl list",
                                "Manages the AGCT whitelist of trusted users.",
                                "",
                                {"type": "section", "text": "Subcommands"},
                                ("add <user_id>", "Add a user to the whitelist"),
                                ("remove <user_id>", "Remove a user from the whitelist"),
                                ("list", "Show all whitelisted users"),
                        ),

                        "agct wl add": help_page(
                                f"{p}agct wl add <user_id>",
                                "Adds a user to the AGCT whitelist.",
                                "",
                                {"type": "section", "text": "Arguments"},
                                ("user_id", "Discord user ID to whitelist"),
                        ),

                        "agct wl remove": help_page(
                                f"{p}agct wl remove <user_id>",
                                "Removes a user from the AGCT whitelist.",
                                "",
                                {"type": "section", "text": "Arguments"},
                                ("user_id", "Discord user ID to remove"),
                        ),

            "agct wl list": help_page(
                f"{p}agct wl list",
                "Displays all users currently on the AGCT whitelist.",
            ),

            # ── Raw ──────────────────────────────────────────────────────────
            "raw": {
                "title": f"{p}help Raw",
                "lines": [
                    ("cmdwall", "Display all commands in raw format"),
                ],
            },

            "cmdwall": help_page(
                f"{p}cmdwall",
                "Displays all registered bot commands in raw decorator format.",
                "",
                {"type": "section", "text": "Aliases"},
                "commandsraw, allcmds",
            ),

            # ── Quest ────────────────────────────────────────────────────────
            "quest": {
                "title": f"{p}help Quest",
                "lines": [
                    ("quest", "Show quest status and list"),
                    ("questdebug [id|link]", "Show quest task/event/platform debug"),
                    ("queststart", "Start auto-completing quests"),
                    ("queststop", "Stop auto-completing quests"),
                    ("questrefresh", "Refresh quest data from Discord"),
                    ("questenroll [id|link]", "Enroll all or one specific quest"),
                    ("questclaim", "Claim all claimable quest rewards"),
                    ("questautoclaimer <sub>", "All-in-one quest auto claimer"),
                ],
            },

            "queststart": help_page(
                f"{p}queststart",
                "Starts automatically completing available Nitro quests.",
            ),

            "queststop": help_page(
                f"{p}queststop",
                "Stops the quest auto-completion process.",
            ),

            "questrefresh": help_page(
                f"{p}questrefresh",
                "Fetches the latest quest data from Discord API.",
            ),

            "questclaim": help_page(
                f"{p}questclaim",
                "Claims all currently claimable quest rewards.",
                "",
                {"type": "section", "text": "Aliases"},
                "qclaim, qc",
            ),

            "questenroll": help_page(
                f"{p}questenroll [quest_id|quest_link]",
                "Enrolls in all available quests, or one specific quest by ID/link.",
                "",
                {"type": "section", "text": "Aliases"},
                "qenroll, qe",
            ),

            "questdebug": help_page(
                f"{p}questdebug [quest_id|quest_link]",
                "Shows raw quest diagnostics: id, task type, event, progress, worthy flag, and platform hints.",
                "",
                {"type": "section", "text": "Aliases"},
                "qdebug, qdbg",
            ),

            "questautoclaimer": help_page(
                f"{p}questautoclaimer <start|stop|status|refresh|enroll|claim>",
                "Unified quest automation command.",
                "",
                {"type": "section", "text": "Aliases"},
                "quest-auto-claimer, qac, autoclaimer",
            ),

            "all": {
                "title": "All Commands",
                "lines": [
                    ("ms", "Test latency"),
                    ("spam <count> <text>", "Spam"),
                    ("purge <amount|all> [-e] [-r] [-s] [channel_id]", "Delete messages"),
                    ("spurge", "Stop active purge"),
                    ("massdm <option> <msg>", "Mass DM"),
                    ("block <user_id>", "Block user"),
                    ("guilds", "Count guilds"),
                    ("autoreact <@user> <emoji...>", "Auto-react"),
                    ("hypesquad <house>", "Set HypeSquad house"),
                    ("hypesquad_leave", "Leave HypeSquad"),
                    ("status <state>", "Set account status"),
                    ("client <type>", "Switch client type"),
                    ("mutualinfo [user_id]", "Mutual servers"),
                    ("closedms", "Close DMs"),
                    ("avatar [user_id]", "Get avatar/banner URLs"),
                    ("superreact <user_id> <emoji...>", "Add super-react target"),
                    ("superreactlist", "List super-react targets"),
                    ("superreactstop [user_id]", "Stop worker or remove target"),
                    ("mimic <@user> [reply]", "Mimic target user"),
                    ("stopmock", "Stop mimic mode"),
                    ("setprefix <symbol>", "Change prefix"),
                    ("setpfp <url>", "Set PFP"),
                    ("stealpfp <user_id>", "Steal PFP"),
                    ("setbanner <url>", "Set banner"),
                    ("stealbanner <user_id>", "Steal banner"),
                    ("setpronouns <text>", "Set pronouns"),
                    ("auth <user_id>", "Grant access"),
                    ("unauth <user_id>", "Revoke access"),
                    ("authlist", "List authed users"),
                    ("listhosted", "Your hosted tokens"),
                    ("listallhosted", "All hosted (owner)"),
                    ("stopallhosted", "Stop all hosted now (owner)"),
                    ("restartallhosted", "Restart all hosted now (owner)"),
                    ("clearhost [uid]", "Remove hosted entry"),
                    ("clearallhosted", "Clear all hosted (owner)"),
                    ("afk [reason]", "Set AFK status"),
                    ("afkstatus [id]", "Check AFK"),
                    ("nitro on/off", "Nitro sniper"),
                    ("giveaway [on|off]", "Giveaway sniper"),
                    ("nitro clear", "Clear codes"),
                    ("badges user <user_id>", "User badges"),
                    ("setbio <text>", "Set bio"),
                    ("setdisplayname <text>", "Set display name"),
                    ("stealname <user_id>", "Steal name"),
                    ("setstatus [emoji,] text", "Set status"),
                    ("stealstatus <user_id>", "Steal status"),
                    ("pronouns [user_id]", "View pronouns"),
                    ("bio [user_id]", "View bio"),
                    ("displayname [user_id]", "View display"),
                    ("servercopy <server_id>", "Copy server"),
                    ("serverload <target_id>", "Load server"),
                    ("setserverpfp <url>", "Set server PFP"),
                    ("badges server <server_id> [limit]", "Server badges"),
                    ("vc [channel_id]", "Join voice/call"),
                    ("vce", "Leave voice/call"),
                    ("vccam [on/off|channel_id] [channel_id]", "Camera (cam/camera)"),
                    ("vcstream [on/off|channel_id] [channel_id]", "Stream (stream/golive)"),
                    ("vcmute [on/off|channel_id] [channel_id]", "Self mute"),
                    ("vcdeaf [on/off|channel_id] [channel_id]", "Self deaf"),
                    ("vcswitch <channel_id>", "Switch VC channel"),
                    ("vcrejoin", "Reconnect VC"),
                    ("vcstatus", "VC state"),
                    ("customize", "UI customization"),
                    ("terminal", "Terminal settings"),
                    ("ui", "Interface settings"),
                    ("agct on/off", "Anti-GC trap"),
                    ("agct block on/off", "Block creators"),
                    ("agct msg <text>", "Leave message"),
                    ("agct name <name>", "GC name"),
                    ("agct icon <url>", "GC icon"),
                    ("agct webhook <url>", "Webhook"),
                    ("agct wl add/remove <id>", "Whitelist"),
                    ("backup user", "User backup"),
                    ("backup messages <ch>", "Message backup"),
                    ("backup full", "Full backup"),
                    ("backup list", "List backups"),
                    ("backup restore <file>", "Restore"),
                    ("mod kick <ids>", "Kick users"),
                    ("mod ban <ids>", "Ban users"),
                    ("mod filter", "Word filter"),
                    ("mod cleanup", "Clean channels/roles"),
                    ("mod members", "List members"),
                    ("mod channels", "List channels"),
                    ("mod roles", "List roles"),
                    ("web", "Start web panel"),
                    ("stop", "Stop bot"),
                    ("restart", "Restart bot"),
                    ("help [page]", "This help"),
                    (f"{p}drun", "Owner: Execute on instances"),
                    (f"{p}dlog", "Owner: Logging"),
                    (f"{p}ddebug", "Owner: Debug mode"),
                    (f"{p}dmetrics", "Owner: Metrics"),
                    (f"{p}djoininvite", "Owner: Join servers"),
                    (f"{p}dleaveguild", "Owner: Leave guilds"),
                    (f"{p}dmyguilds", "Owner: List guilds"),
                    (f"{p}dmassleave", "Owner: Mass leave"),
                    (f"{p}dguildmembers", "Owner: Guild members"),
                    (f"{p}dchecktoken", "Owner: Check token"),
                    (f"{p}dbulkcheck", "Owner: Bulk tokens"),
                    (f"{p}dexportguilds", "Owner: Export guilds"),
                    (f"{p}dboost", "Owner: Boost commands"),
                    (f"{p}dboosttransfer", "Owner: Boost transfer"),
                    (f"{p}dbooststatus", "Owner: Boost status"),
                    (f"{p}dboostlist", "Owner: Boosted list"),
                    (f"{p}daccountcmd", "Owner: Any account command"),
                    (f"{p}drpc", "Owner: RPC commands"),
                    (f"{p}drecentmessages", "Owner: Messages"),
                ],
            },
        }

        for category_key, category_title in category_header_map.items():
            cat_page = help_pages.get(category_key)
            if not isinstance(cat_page, dict):
                continue
            cat_lines = cat_page.get("lines", [])
            for entry in cat_lines:
                if not (isinstance(entry, tuple) and len(entry) == 2):
                    continue
                raw_name = str(entry[0]).strip().lower()
                if not raw_name:
                    continue
                normalized_name = " ".join(raw_name.split())
                command_category_exact[normalized_name] = category_title

                first_token = normalized_name.split()[0]
                first_token = first_token.split("_")[0]
                if first_token and first_token not in command_category_primary:
                    command_category_primary[first_token] = category_title

        if not args:
            categories = [
                ("General", "Starter & config"),
                ("Utility", "Everyday tools"),
                ("Messaging", "DM / GC / spam"),
                ("Profile", "Identity & account"),
                ("Server", "Guild management"),
                ("Voice", "VC / calls"),
                ("Social", "Interactions"),
                ("Fun", "Entertainment"),
                ("RPC", "Rich presence"),
                ("Boost", "Server boosts"),
                ("Backup", "Recovery"),
                ("Moderation", "Mod tools"),
                ("Antinuke", "Protection"),
                ("Nuke", "Destructive ops"),
                ("Hosting", "Hosted tokens"),
                ("Token", "Session tools"),
                ("AFK", "AFK system"),
                ("Nitro", "Nitro sniper"),
                ("AGCT", "Anti-GC trap"),
                ("Quest", "Quests"),
                ("Owner", "Admin / owner only"),
            ]
            msg = ctx["api"].send_message(
                ctx["channel_id"],
                "\n".join([
                    fmt.header(f"{p}help <category> {p}help <command>"),
                    fmt.category_list(dict(categories)),
                    fmt._block(f"{fmt.DARK}Miscomprehend{fmt.RESET}"),
                ]),
            )
            return
        
        # Parse "help <category> page <n>" (preferred) and legacy "help <category> <n>"
        page_num = 1
        full_page = " ".join(args).lower()
        if len(args) >= 3 and args[-2].lower() == "page" and args[-1].isdigit():
            page_num = int(args[-1])
            full_page = " ".join(args[:-2]).lower()
        elif args and args[-1].isdigit() and len(args) > 1:
            page_num = int(args[-1])
            full_page = " ".join(args[:-1]).lower()
        
        page = full_page if full_page in help_pages else (args[0].lower() if args else "")
        
        if page == "owner" and not is_strict_owner_user(ctx["author_id"]):
            bad = (full_page or page or "unknown").strip()
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **No command or help section found**: **{bad}**")
            return

        if page in help_pages:
            content = help_pages[page]
            lines = content.get("lines", [])
            lines_per_page = 5  # Keep help messages short to avoid long send payloads
            pages = []
            for index in range(0, len(lines), lines_per_page):
                page_slice = lines[index:index + lines_per_page]
                pages.append({
                    "title": content.get("title", "Help"),
                    "lines": page_slice,
                })

            if page_num < 1 or page_num > len(pages):
                page_num = 1

            content_to_send = pages[page_num - 1]
            rendered = render_help_page(page, content_to_send, page_num, len(pages))
            msg = ctx["api"].send_message(ctx["channel_id"], rendered)
            
            if 'msg' in locals() and msg:
                pass
        else:
            # Fallback: if the user asked for a real command name that lacks a static help page,
            # show command details dynamically so new commands remain discoverable.
            lookup = (full_page or (args[0] if args else "")).strip().lower()
            cmd = ctx["bot"].commands.get(lookup) if lookup else None
            if cmd:
                aliases = ", ".join(cmd.aliases) if getattr(cmd, "aliases", None) else "none"
                msg = ctx["api"].send_message(
                    ctx["channel_id"],
                    "\n".join(
                        [
                            fmt.header(cmd.name),
                            fmt._block(
                                f"{fmt.CYAN}Command{fmt.DARK} :: {fmt.RESET}{fmt.WHITE}{p}{cmd.name}{fmt.RESET}\n"
                                f"{fmt.CYAN}Aliases{fmt.DARK} :: {fmt.RESET}{fmt.WHITE}{aliases}{fmt.RESET}"
                            ),
                        ]
                    ),
                )
            else:
                bad = (lookup or "unknown").strip()
                msg = ctx["api"].send_message(ctx["channel_id"], f"> **No command or category found**: **{bad}**")
    @bot.command(name="cmdwall", aliases=["commandsraw", "allcmds"])
    def cmdwall(ctx, args):
        import formatter as _fmt
        # Collect unique commands (primary names only), sorted
        seen = set()
        unique = []
        for key in sorted(ctx["bot"].commands.keys()):
            cmd = ctx["bot"].commands[key]
            if cmd.name in seen:
                continue
            seen.add(cmd.name)
            unique.append(cmd)

        p = ctx["bot"].prefix
        chunk, messages = [], []
        for cmd in unique:
            alias_str = f" [{', '.join(cmd.aliases)}]" if cmd.aliases else ""
            chunk.append(f"{_fmt.CYAN}{p}{cmd.name}{_fmt.RESET}{_fmt.DARK}{alias_str}{_fmt.RESET}")
            if len(chunk) >= 30:
                messages.append(_fmt._block("\n".join(chunk)))
                chunk = []
        if chunk:
            messages.append(_fmt._block("\n".join(chunk)))

        for i, part in enumerate(messages):
            msg = ctx["api"].send_message(ctx["channel_id"], part)
            if msg and i < len(messages) - 1:
                time.sleep(0.3)
            elif msg:
                pass

    @bot.command(name="restart")
    def restart_cmd(ctx, args):
        if not is_strict_owner_user(ctx["author_id"]):
            deny_restricted_command(ctx, "Restart")
            return
        msg = ctx["api"].send_message(ctx["channel_id"], "> **Restarting** bot in 3 seconds...")
        
        def restart_sequence():
            time.sleep(1)
            ctx["api"].edit_message(ctx["channel_id"], msg.get("id"), "> **Restarting** bot in 2 seconds...")
            time.sleep(1)
            ctx["api"].edit_message(ctx["channel_id"], msg.get("id"), "> **Restarting** bot in 1 second...")
            time.sleep(1)

            ctx["api"].send_message(ctx["channel_id"], "> **System** restarting...")

            import subprocess
            import sys

            time.sleep(0.5)

            # Terminate all hosted child processes so the new instance
            # can cleanly restore them all via restore_hosted_users().
            if not HOSTED_MODE:
                try:
                    host_manager.cleanup()
                except Exception:
                    pass

            python = sys.executable
            subprocess.Popen([python, "main.py"])

            time.sleep(1)
            bot.stop()
        
        threading.Thread(target=restart_sequence, daemon=True).start()

    def _vc_send(ctx, text):
        msg = ctx["api"].send_message(ctx["channel_id"], text)
        if msg:
            delete_after_delay(
                ctx["api"],
                ctx["channel_id"],
                msg.get("id"),
                getattr(bot, "_auto_delete_delay", 3.0),
            )
        return msg

    @bot.command(name="vc", aliases=["voice", "joinvc", "vcjoin", "joinvoice", "joincall"])
    def vc(ctx, args):
        if not args:
            current = voice_manager.current_channel_id()
            if current:
                msg = _vc_send(ctx, f"> **Already in Voice** | Channel: **{current}**")
            else:
                msg = _vc_send(ctx, f"> **Join VC** | Usage: {bot.prefix}vc <channel_id>")
            return
        
        channel_id = args[0]
        
        try:
            success = voice_manager.join_vc(channel_id)
            
            if success:
                state = voice_manager.get_state(channel_id)
                ready = "ready" if state.get("ws_ready") else "starting"
                msg = _vc_send(ctx, f"> **Connected to Voice** | Channel: **{channel_id}** | WS: {ready}")
            else:
                detail = getattr(voice_manager, "last_error", "") or "Unknown voice error"
                msg = _vc_send(ctx, f"> **Failed** to connect to voice channel :: {detail}")
            
        except Exception as e:
            msg = _vc_send(ctx, f"> **Voice error**: {str(e)[:80]}")

    @bot.command(name="vce", aliases=["leavevc", "disconnect", "vcleave", "leavevoice", "hangup"])
    def vce(ctx, args):
        try:
            if args:
                success = voice_manager.leave_vc(args[0])
            else:
                success = voice_manager.leave_vc()
            
            if success:
                msg = _vc_send(ctx, "> **Disconnected** from voice")
            else:
                msg = _vc_send(ctx, "> **Not in** a voice channel")
            
        except Exception as e:
            msg = _vc_send(ctx, f"> **Voice error**: {str(e)[:80]}")

    @bot.command(name="vccam", aliases=["cam", "camera", "vcam", "vcvideo"])
    def vccam(ctx, args):
        enabled = True
        channel_id = None
        if args:
            first = str(args[0]).strip().lower()
            if first in ("off", "false", "0"):
                enabled = False
                channel_id = args[1] if len(args) > 1 else None
            elif first in ("on", "true", "1"):
                enabled = True
                channel_id = args[1] if len(args) > 1 else None
            else:
                # Treat first arg as channel id when state flag is omitted.
                channel_id = args[0]
        try:
            ok, detail = voice_manager.set_video(channel_id, enabled)
            if ok:
                msg = _vc_send(ctx, f"> **✓ Camera** :: {detail}")
            else:
                msg = _vc_send(ctx, f"> **✗ Camera** :: {detail}")
        except Exception as e:
            msg = _vc_send(ctx, f"> **✗ Camera error**: {str(e)[:80]}")

    @bot.command(name="vcstatus", aliases=["vcs", "voicestatus"])
    def vcstatus(ctx, args):
        try:
            if voice_manager.is_in_voice():
                st = voice_manager.get_state()
                ch = st.get("channel_id") or "unknown"
                msg = _vc_send(
                    ctx,
                    f"> **Voice Status** :: Connected to **{ch}** | cam={st.get('camera')} | stream={st.get('stream')} | mute={st.get('mute')} | deaf={st.get('deaf')} | ws={st.get('ws_ready')}",
                )
            else:
                err = getattr(voice_manager, "last_error", "")
                suffix = f" | Last error: {err}" if err else ""
                msg = _vc_send(ctx, f"> **Voice Status** :: Not connected{suffix}")
        except Exception as e:
            msg = _vc_send(ctx, f"> **Voice Status Error**: {str(e)[:80]}")

    @bot.command(name="vcstream", aliases=["stream", "golive", "vcgo", "vcgolive", "screenshare", "vcscreen"])
    def vcstream(ctx, args):
        enabled = True
        channel_id = None
        if args:
            first = str(args[0]).strip().lower()
            if first in ("off", "stop", "false", "0"):
                enabled = False
                channel_id = args[1] if len(args) > 1 else None
            elif first in ("on", "start", "true", "1"):
                enabled = True
                channel_id = args[1] if len(args) > 1 else None
            else:
                # Treat first arg as channel id when state flag is omitted.
                channel_id = args[0]
        try:
            ok, detail = voice_manager.set_stream(channel_id, enabled)
            if ok:
                msg = _vc_send(ctx, f"> **✓ Go Live** :: {detail}")
            else:
                msg = _vc_send(ctx, f"> **✗ Go Live** :: {detail}")
        except Exception as e:
            msg = _vc_send(ctx, f"> **✗ Stream error**: {str(e)[:80]}")

    @bot.command(name="vcmute", aliases=["mutevc", "voice_mute", "vcm"])
    def vcmute(ctx, args):
        enabled = True
        channel_id = None
        if args:
            first = str(args[0]).strip().lower()
            if first in ("off", "false", "0"):
                enabled = False
                channel_id = args[1] if len(args) > 1 else None
            elif first in ("on", "true", "1"):
                enabled = True
                channel_id = args[1] if len(args) > 1 else None
            else:
                channel_id = args[0]
        ok, detail = voice_manager.set_mute_deaf(channel_id=channel_id, mute=enabled, deaf=None)
        if ok:
            msg = _vc_send(ctx, f"> **✓ VC Mute** :: {detail}")
        else:
            msg = _vc_send(ctx, f"> **✗ VC Mute** :: {detail}")

    @bot.command(name="vcdeaf", aliases=["deafvc", "voice_deaf", "vcd"])
    def vcdeaf(ctx, args):
        enabled = True
        channel_id = None
        if args:
            first = str(args[0]).strip().lower()
            if first in ("off", "false", "0"):
                enabled = False
                channel_id = args[1] if len(args) > 1 else None
            elif first in ("on", "true", "1"):
                enabled = True
                channel_id = args[1] if len(args) > 1 else None
            else:
                channel_id = args[0]
        ok, detail = voice_manager.set_mute_deaf(channel_id=channel_id, mute=None, deaf=enabled)
        if ok:
            msg = _vc_send(ctx, f"> **✓ VC Deaf** :: {detail}")
        else:
            msg = _vc_send(ctx, f"> **✗ VC Deaf** :: {detail}")

    @bot.command(name="vcswitch", aliases=["vcmove", "switchvc", "voice_switch"])
    def vcswitch(ctx, args):
        if not args:
            msg = _vc_send(ctx, f"> **VC Switch** | Usage: {bot.prefix}vcswitch <channel_id>")
            return
        channel_id = str(args[0]).strip()
        ok = voice_manager.switch_channel(channel_id)
        if ok:
            st = voice_manager.get_state(channel_id)
            ready = "ready" if st.get("ws_ready") else "starting"
            msg = _vc_send(ctx, f"> **✓ VC Switch** :: {channel_id} | WS: {ready}")
        else:
            detail = getattr(voice_manager, "last_error", "") or "Unknown voice error"
            msg = _vc_send(ctx, f"> **✗ VC Switch** :: {detail}")

    @bot.command(name="vcrejoin", aliases=["vcreconnect", "vcfix", "voicefix"])
    def vcrejoin(ctx, args):
        ok = voice_manager.rejoin()
        if ok:
            st = voice_manager.get_state()
            ch = st.get("channel_id") or "unknown"
            ready = "ready" if st.get("ws_ready") else "starting"
            msg = _vc_send(ctx, f"> **✓ VC Rejoin** :: {ch} | WS: {ready}")
        else:
            detail = getattr(voice_manager, "last_error", "") or "Unknown voice error"
            msg = _vc_send(ctx, f"> **✗ VC Rejoin** :: {detail}")
    @bot.command(name="quest", aliases=["questlist", "ql", "qstat"])
    def quest_cmd(ctx, args):
        if args and str(args[0]).lower() in {"debug", "dbg"}:
            questdebug_cmd(ctx, list(args[1:]))
            return

        ok, detail = quest_system.fetch_quests()
        s = quest_system.get_summary()
        lines = ["Quest Manager"]
        lines.append(f"Auto-complete :: {'Running' if s['running'] else 'Stopped'}")
        lines.append(f"Total :: {s['total']}")
        lines.append(f"Enrollable :: {len(s['enrollable'])}")
        lines.append(f"In Progress :: {len(s['completeable'])}")
        lines.append(f"Claimable  :: {len(s['claimable'])}")
        lines.append(f"Completed  :: {len(s['completed'])}")
        lines.append(f"Expired    :: {len(s['expired'])}")
        if s["last_fetch"]:
            lines.append(f"Last Fetch :: {time.strftime('%H:%M:%S', time.localtime(s['last_fetch']))}")
        for q in s["completeable"]:
            _, done, total = quest_system._get_progress(q)
            pct = int(done / total * 100) if total else 0
            worthy = " *" if quest_system._is_worthy(q) else ""
            lines.append(f"> {quest_system._quest_name(q)}{worthy} [{quest_system._task_type(q)}] {done}/{total} ({pct}%)")
        for q in s["enrollable"]:
            lines.append(f"> {quest_system._quest_name(q)} [enrollable]")
        for q in s["claimable"]:
            lines.append(f"> {quest_system._quest_name(q)} [claim now]")
        for q in s["completed"]:
            lines.append(f"> {quest_system._quest_name(q)} [done]")
        text = "```| " + " |\n".join(lines) + "```"
        msg = ctx["api"].send_message(ctx["channel_id"], text)

    @bot.command(name="questdebug", aliases=["qdebug", "qdbg"])
    def questdebug_cmd(ctx, args):
        import re

        def _extract_quest_id(text: str) -> str:
            raw = str(text or "").strip()
            if not raw:
                return ""
            m = re.search(r"/quests/([A-Za-z0-9_-]+)", raw)
            if m:
                return m.group(1)
            m = re.search(r"[?&](?:quest_id|id)=([A-Za-z0-9_-]+)", raw)
            if m:
                return m.group(1)
            cleaned = raw.strip("<>()[]{} ")
            if re.fullmatch(r"[A-Za-z0-9_-]{6,}", cleaned):
                return cleaned
            return ""

        ok, detail = quest_system.fetch_quests()
        if not ok and not quest_system.quests:
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **✗ Quest Debug** :: Fetch failed: {detail}")
            return

        quests = list(quest_system.quests.values())
        req_ids = [_extract_quest_id(a) for a in (args or [])]
        req_ids = [x for x in req_ids if x]
        if req_ids:
            wanted = set(req_ids)
            quests = [q for q in quests if str(q.get("id", "")) in wanted]

        if not quests:
            msg = ctx["api"].send_message(ctx["channel_id"], "> **Quest Debug** :: No matching quests.")
            return

        lines = [f"Quest Debug :: {len(quests)} quest(s)"]
        for q in quests[:20]:
            qid = str(q.get("id", "?"))
            qname = quest_system._quest_name(q)
            qtype = quest_system._task_type(q)
            event_name, done, total = quest_system._get_progress(q)
            worthy = "yes" if quest_system._is_worthy(q) else "no"
            platforms = []
            if hasattr(quest_system, "_task_platforms"):
                try:
                    platforms = sorted(list(quest_system._task_platforms(q)))
                except Exception:
                    platforms = []
            plat_text = ",".join(platforms) if platforms else "auto"

            state = "completed"
            if quest_system._is_claimable(q):
                state = "claimable"
            elif quest_system._is_completeable(q):
                state = "in-progress"
            elif quest_system._is_enrollable(q):
                state = "enrollable"

            lines.append(f"ID: {qid}")
            lines.append(f"Name: {qname[:80]}")
            lines.append(f"Type: {qtype} | Event: {event_name} | Platform: {plat_text}")
            lines.append(f"Progress: {done}/{total} | Worthy: {worthy} | State: {state}")
            lines.append("-")

        text = "```| " + " |\n".join(lines) + "```"
        msg = ctx["api"].send_message(ctx["channel_id"], text)
    @bot.command(name="questclaim", aliases=["qclaim", "qc"])
    def questclaim_cmd(ctx, args):
        quest_system.fetch_quests()
        s = quest_system.get_summary()
        claimable = s["claimable"]
        if not claimable:
            msg = ctx["api"].send_message(ctx["channel_id"], "> **Quest** :: No claimable quests.")
            return

        claimed = 0
        failed = 0
        for q in claimable:
            if quest_system.claim(q):
                claimed += 1
            else:
                failed += 1
            time.sleep(0.6)

        msg = ctx["api"].send_message(
            ctx["channel_id"],
            f"> **✓ Quest Claim** :: Claimed **{claimed}** · Failed: {failed}",
        )
    @bot.command(name="queststart", aliases=["qstart", "qs"])
    def queststart_cmd(ctx, args):
        ok_fetch, fetch_detail = quest_system.fetch_quests()
        if not ok_fetch:
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **Quest** refresh failed: {fetch_detail}.")
            return
        ok, detail = quest_system.start()
        if ok:
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **Quest enabled**. {detail}.")
        else:
            msg = ctx["api"].send_message(ctx["channel_id"], f"Quest error: {detail}.")
    @bot.command(name="queststop", aliases=["qstop", "qx"])
    def queststop_cmd(ctx, args):
        ok, detail = quest_system.stop()
        msg = ctx["api"].send_message(ctx["channel_id"], f"> **Quest disabled**. {detail}.")
    @bot.command(name="questrefresh", aliases=["qr", "qrefresh"])
    def questrefresh_cmd(ctx, args):
        ok, detail = quest_system.fetch_quests()
        status = "Refreshed" if ok else "Failed"
        s = quest_system.get_summary()
        msg = ctx["api"].send_message(
            ctx["channel_id"],
            f"> **{'✓' if ok else '✗'} Quest Refresh** :: {detail} · Total: {s['total']} · Enrollable: {len(s['enrollable'])} · Claimable: {len(s['claimable'])}",
        )
    @bot.command(name="questenroll", aliases=["qenroll", "qe"])
    def questenroll_cmd(ctx, args):
        import re

        def _extract_quest_id(text: str) -> str:
            raw = str(text or "").strip()
            if not raw:
                return ""
            m = re.search(r"/quests/([A-Za-z0-9_-]+)", raw)
            if m:
                return m.group(1)
            m = re.search(r"[?&](?:quest_id|id)=([A-Za-z0-9_-]+)", raw)
            if m:
                return m.group(1)
            cleaned = raw.strip("<>()[]{} ")
            if re.fullmatch(r"[A-Za-z0-9_-]{6,}", cleaned):
                return cleaned
            return ""

        quest_system.fetch_quests()
        s = quest_system.get_summary()
        enrollable = s["enrollable"]
        missing = []

        requested_ids = [_extract_quest_id(a) for a in (args or [])]
        requested_ids = [x for x in requested_ids if x]

        if requested_ids:
            selected = []
            missing = []
            for qid in requested_ids:
                q = quest_system.quests.get(str(qid))
                if q is None:
                    missing.append(str(qid))
                    continue
                selected.append(q)
            enrollable = selected

        if not enrollable:
            if requested_ids:
                missing_note = f" · Missing: {', '.join(missing[:5])}" if missing else ""
                msg = ctx["api"].send_message(ctx["channel_id"], f"> **Quest** :: No enrollable matching quests.{missing_note}")
            else:
                msg = ctx["api"].send_message(ctx["channel_id"], "> **Quest** :: No enrollable quests.")
            return

        enrolled = 0
        failed = 0
        for q in enrollable:
            status = quest_system.enroll(q)
            if status:
                q["user_status"] = status
                enrolled += 1
            else:
                failed += 1
            time.sleep(0.8)

        suffix = ""
        if requested_ids and missing:
            suffix = f" · Missing: {len(missing)}"

        msg = ctx["api"].send_message(
            ctx["channel_id"],
            f"> **✓ Quest Enroll** :: Enrolled **{enrolled}** · Failed: {failed}{suffix}",
        )
    @bot.command(name="questautoclaimer", aliases=["quest-auto-claimer", "qac", "autoclaimer"])
    def questautoclaimer_cmd(ctx, args):
        sub = (args[0].lower() if args else "status")

        if sub == "status":
            quest_cmd(ctx, [])
            return

        if sub == "start":
            queststart_cmd(ctx, [])
            return

        if sub == "stop":
            queststop_cmd(ctx, [])
            return

        if sub == "refresh":
            questrefresh_cmd(ctx, [])
            return

        if sub == "enroll":
            questenroll_cmd(ctx, [])
            return

        if sub == "claim":
            questclaim_cmd(ctx, [])
            return

        msg = ctx["api"].send_message(
            ctx["channel_id"],
            f"> **✗ Quest** :: Usage: `{bot.prefix}questautoclaimer <start|stop|status|refresh|enroll|claim>`",
        )
    @bot.command(name="deco", aliases=["decoration", "profiledeco", "cleardeco", "removedeco"])
    def deco_cmd(ctx, args):
        import formatter as fmt
        sub = args[0].lower() if args else ""
        if sub != "remove":
            cmds = [
                (f"{bot.prefix}deco remove", "Remove avatar decoration & profile effect"),
            ]
            msg = ctx["api"].send_message(
                ctx["channel_id"],
                fmt.header("Decoration") + "\n" + fmt.command_list(cmds),
            )
            return
        # Clear avatar decoration (type 3) and profile effect (type 4)
        resp = ctx["api"].request(
            "PATCH",
            "/users/@me/profile",
            data={"avatar_decoration_id": None, "profile_effect_id": None},
        )
        if resp and resp.status_code in (200, 204):
            msg = ctx["api"].send_message(
                ctx["channel_id"],
                fmt.status_box("Decoration", {"Status": "Decoration & profile effect cleared"}),
            )
        else:
            code = resp.status_code if resp else "N/A"
            msg = ctx["api"].send_message(
                ctx["channel_id"],
                fmt.status_box("Decoration", {"Status": f"Failed (HTTP {code})"}),
            )
    @bot.command(name="guildbadge", aliases=["gbadge", "grotate", "gb"])
    def guildbadge_cmd(ctx, args):
        gr = ctx["bot"].guild_rotator
        sub = args[0].lower() if args else ""

        if sub == "start":
            ok, detail = gr.start()
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **{'✓' if ok else '✗'} Guild Badge** :: {detail}")

        elif sub == "stop":
            ok, detail = gr.stop()
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **{'✓' if ok else '✗'} Guild Badge** :: {detail}")

        elif sub == "name" and len(args) >= 2:
            gr.config["tag_name"] = args[1]
            gr._save()
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **✓ Guild Badge** :: Tag name set to `{args[1]}`.")

        elif sub == "delay" and len(args) >= 2:
            try:
                secs = max(30, int(args[1]))
                gr.config["delay"] = secs
                gr._save()
                msg = ctx["api"].send_message(ctx["channel_id"], f"> **✓ Guild Badge** :: Delay set to `{secs}s`.")
            except ValueError:
                msg = ctx["api"].send_message(ctx["channel_id"], "> **✗ Guild Badge** :: Invalid number.")

        elif sub == "addguild" and len(args) >= 2:
            gid = args[1]
            if gid not in gr.config["guilds"]:
                gr.config["guilds"].append(gid)
                gr._save()
                msg = ctx["api"].send_message(ctx["channel_id"], f"> **✓ Guild Badge** :: Added guild `{gid}`.")
            else:
                msg = ctx["api"].send_message(ctx["channel_id"], f"> **Guild Badge** :: Guild `{gid}` already in list.")

        elif sub == "removeguild" and len(args) >= 2:
            gid = args[1]
            if gid in gr.config["guilds"]:
                gr.config["guilds"].remove(gid)
                gr._save()
                msg = ctx["api"].send_message(ctx["channel_id"], f"> **✗ Guild Badge** :: Removed guild `{gid}`.")
            else:
                msg = ctx["api"].send_message(ctx["channel_id"], f"> **✗ Guild Badge** :: Guild `{gid}` not found.")

        elif sub == "addcolor" and len(args) >= 3:
            p, s = args[1], args[2]
            if gr._hex_re.match(p) and gr._hex_re.match(s):
                gr.config["colors"].append([p, s])
                gr._save()
                msg = ctx["api"].send_message(ctx["channel_id"], f"> **✓ Guild Badge** :: Added color `{p}` / `{s}`.")
            else:
                msg = ctx["api"].send_message(ctx["channel_id"], "> **✗ Guild Badge** :: Invalid hex. Use `#RRGGBB` format.")

        elif sub == "removecolor" and len(args) >= 2:
            try:
                idx = int(args[1]) - 1
                colors = gr.config["colors"]
                if 0 <= idx < len(colors):
                    removed = colors.pop(idx)
                    gr._save()
                    msg = ctx["api"].send_message(ctx["channel_id"], f"> **✗ Guild Badge** :: Removed `{removed[0]}` / `{removed[1]}`.")
                else:
                    msg = ctx["api"].send_message(ctx["channel_id"], f"> **✗ Guild Badge** :: Index out of range (1–{len(colors)}).")
            except ValueError:
                msg = ctx["api"].send_message(ctx["channel_id"], "> **✗ Guild Badge** :: Invalid index.")

        elif sub == "listbadges":
            badge_str = "  ".join(f"{bid}:{name}" for bid, name in _GUILDBADGE_BADGES.items())
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **Guild Badge Types** :: {badge_str}")

        else:
            # Status panel
            status = "Running" if gr.running else "Stopped"
            guilds = ", ".join(gr.config.get("guilds", [])) or "none"
            colors = gr.config.get("colors", [])
            lines = [
                "Guild Badge Rotator",
                f"Status :: {status}",
                f"Tag    :: {gr.config.get('tag_name', 'aria')}",
                f"Delay  :: {gr.config.get('delay', 180)}s",
                f"Guilds :: {guilds}",
                f"Colors :: {len(colors)} pairs",
                "",
                f"> {bot.prefix}guildbadge start/stop",
                f"> {bot.prefix}guildbadge name <tag>",
                f"> {bot.prefix}guildbadge delay <secs>",
                f"> {bot.prefix}guildbadge addguild/removeguild <id>",
                f"> {bot.prefix}guildbadge addcolor <#hex1> <#hex2>",
                f"> {bot.prefix}guildbadge removecolor <index>",
                f"> {bot.prefix}guildbadge listbadges",
            ]
            msg = ctx["api"].send_message(ctx["channel_id"], "```| " + " |\n".join(lines) + "```")

    @bot.command(name="admin", aliases=["admins", "paneladmin"])
    def admin_cmd(ctx, args):
        if not is_strict_owner_user(ctx["author_id"]):
            deny_restricted_command(ctx, "Admin")
            return

        if not args:
            msg = ctx["api"].send_message(
                ctx["channel_id"],
                f"> **Admin** :: Usage: {bot.prefix}admin add <user_id> | {bot.prefix}admin remove <user_id> | {bot.prefix}admin list",
            )
            return

        action = args[0].lower()
        if action == "add" and len(args) >= 2 and args[1].isdigit():
            uid = str(args[1])
            _admin_users.add(uid)
            _save_id_set(_ADMIN_FILE, _admin_users)
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **✓ Admin** :: Added admin: {uid}")
            return

        if action == "remove" and len(args) >= 2 and args[1].isdigit():
            uid = str(args[1])
            _admin_users.discard(uid)
            _save_id_set(_ADMIN_FILE, _admin_users)
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **✓ Admin** :: Removed admin: {uid}")
            return

        if action == "list":
            entries = sorted(_admin_users)
            body = "\n".join(f"> {uid}" for uid in entries[:50]) if entries else "No admins configured"
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **Admin** :: Total: {len(entries)}\n{body}")
            return

        msg = ctx["api"].send_message(ctx["channel_id"], "> **Admin** :: Usage: add/remove/list")

    @bot.command(name="auth", aliases=["authuser"])
    def auth_cmd(ctx, args):
        if not is_strict_owner_user(ctx["author_id"]):
            deny_restricted_command(ctx, "Auth")
            return
        if not args or not args[0].isdigit():
            p = bot.prefix
            msg = ctx["api"].send_message(ctx["channel_id"],
                f"> **Auth** :: Usage: {p}auth <user_id> — grant access | {p}unauth <user_id> — revoke | {p}authlist — list")
            return
        uid = str(args[0])
        _authed_users.add(uid)
        _dashboard_authed_users.add(uid)
        _dashboard_blocked_users.discard(uid)
        _save_authed(_authed_users)
        _save_id_set(_DASH_AUTH_FILE, _dashboard_authed_users)
        _save_id_set(_DASH_BLOCK_FILE, _dashboard_blocked_users)
        msg = ctx["api"].send_message(ctx["channel_id"], f"> **✓ Auth** :: User {uid} granted website/dashboard access")
    @bot.command(name="unauth", aliases=["deauth"])
    def unauth_cmd(ctx, args):
        if not is_strict_owner_user(ctx["author_id"]):
            deny_restricted_command(ctx, "Unauth")
            return
        if not args or not args[0].isdigit():
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **Unauth** :: Usage: {bot.prefix}unauth <user_id>")
            return
        uid = str(args[0])
        _authed_users.discard(uid)
        _dashboard_authed_users.discard(uid)
        _save_authed(_authed_users)
        _save_id_set(_DASH_AUTH_FILE, _dashboard_authed_users)
        msg = ctx["api"].send_message(ctx["channel_id"], f"> **✓ Unauth** :: User {uid} revoked")

    @bot.command(name="whitelist", aliases=["wl", "sitewl"])
    def whitelist_cmd(ctx, args):
        if not is_strict_owner_user(ctx["author_id"]):
            deny_restricted_command(ctx, "Whitelist")
            return

        if not args:
            msg = ctx["api"].send_message(
                ctx["channel_id"],
                f"> **Whitelist** :: Usage: {bot.prefix}whitelist add <user_id> | {bot.prefix}whitelist remove <user_id> | {bot.prefix}whitelist list",
            )
            return

        action = args[0].lower()
        if action == "add" and len(args) >= 2 and args[1].isdigit():
            uid = str(args[1])
            _dashboard_authed_users.add(uid)
            _authed_users.add(uid)
            _dashboard_blocked_users.discard(uid)
            _save_id_set(_DASH_AUTH_FILE, _dashboard_authed_users)
            _save_id_set(_DASH_BLOCK_FILE, _dashboard_blocked_users)
            _save_authed(_authed_users)
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **✓ Whitelist** :: {uid} site access restored")
            return

        if action == "remove" and len(args) >= 2 and args[1].isdigit():
            uid = str(args[1])
            _dashboard_authed_users.discard(uid)
            _authed_users.discard(uid)
            _save_id_set(_DASH_AUTH_FILE, _dashboard_authed_users)
            _save_authed(_authed_users)
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **✓ Whitelist** :: Removed {uid}")
            return

        if action == "list":
            lines = sorted(_dashboard_authed_users)
            body = "\n".join(f"> {uid}" for uid in lines[:50]) if lines else "No whitelisted users"
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **Whitelist** :: Total: {len(lines)}\n{body}")
            return

        msg = ctx["api"].send_message(ctx["channel_id"], "> **Whitelist** :: Usage: add/remove/list")

    @bot.command(name="blacklist", aliases=["bl", "sitebl"])
    def blacklist_cmd(ctx, args):
        if not is_strict_owner_user(ctx["author_id"]):
            deny_restricted_command(ctx, "Blacklist")
            return

        if not args:
            msg = ctx["api"].send_message(
                ctx["channel_id"],
                f"> **Blacklist** :: Usage: {bot.prefix}blacklist add <user_id> | {bot.prefix}blacklist remove <user_id> | {bot.prefix}blacklist list",
            )
            return

        action = args[0].lower()
        if action == "add" and len(args) >= 2 and args[1].isdigit():
            uid = str(args[1])
            _dashboard_blocked_users.add(uid)
            _dashboard_authed_users.discard(uid)
            _authed_users.discard(uid)
            _save_id_set(_DASH_BLOCK_FILE, _dashboard_blocked_users)
            _save_id_set(_DASH_AUTH_FILE, _dashboard_authed_users)
            _save_authed(_authed_users)
            # Stop and remove all hosted instances for this user
            stopped = host_manager.remove_hosts(all_hosts=True, selectors=[uid])
            stopped_note = f" | Stopped {stopped} instance{'s' if stopped != 1 else ''}" if stopped else ""
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **✗ Blacklist** :: {uid} site access revoked{stopped_note}")
            return

        if action == "remove" and len(args) >= 2 and args[1].isdigit():
            uid = str(args[1])
            _dashboard_blocked_users.discard(uid)
            _save_id_set(_DASH_BLOCK_FILE, _dashboard_blocked_users)
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **✓ Blacklist** :: Unblocked {uid}")
            return

        if action == "list":
            lines = sorted(_dashboard_blocked_users)
            body = "\n".join(f"> {uid}" for uid in lines[:50]) if lines else "No blacklisted users"
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **Blacklist** :: Total: {len(lines)}\n{body}")
            return

        msg = ctx["api"].send_message(ctx["channel_id"], "> **Blacklist** :: Usage: add/remove/list")

    @bot.command(name="host", aliases=["hosttoken", "hostuser", "hostme", "addhost"])
    def host_cmd(ctx, args):
        if HOSTED_MODE:
            msg = ctx["api"].send_message(ctx["channel_id"], "> **✗ Host** :: Unavailable on hosted instances")
            return

        requester_id = str(ctx["author_id"])
        host_manager.cleanup_old_rate_limits()
        limited, remaining = host_manager.is_rate_limited(requester_id, "host", 30)
        if limited:
            msg = ctx["api"].send_message(
                ctx["channel_id"],
                f"> **✗ Host** :: Rate limited. Wait {remaining}s before hosting again",
            )
            return

        try:
            with open("host_blacklist.json", "r") as f:
                host_bl = json.load(f)
        except Exception:
            host_bl = {}

        if requester_id in host_bl and not is_owner_user(requester_id):
            msg = ctx["api"].send_message(
                ctx["channel_id"],
                "> **✗ Host** :: You are blocked from hosting. Contact @misconsiderations",
            )
            return

        if not args:
            msg = ctx["api"].send_message(
                ctx["channel_id"],
                f"> **Host** :: Usage: {bot.prefix}host <token> [prefix] — Example: {bot.prefix}host mfa.xxxxxx ;",
            )
            return

        token_input = args[0].strip("\"' ")
        prefix = args[1] if len(args) >= 2 else ";"
        api = ctx["api"]

        try:
            verify_headers = api.header_spoofer.get_protected_headers(token_input)
            verify = api.session.get(
                "https://discord.com/api/v9/users/@me",
                headers=verify_headers,
                timeout=12,
            )
        except Exception as e:
            msg = api.send_message(ctx["channel_id"], f"> **✗ Host** :: Token check failed: {str(e)[:80]}")
            return

        if verify.status_code != 200:
            msg = api.send_message(ctx["channel_id"], "> **✗ Host** :: Invalid token")
            return

        account = verify.json() or {}
        hosted_user_id = str(account.get("id", ""))
        hosted_username = str(account.get("username", "Unknown"))

        ok, detail = host_manager.host_token(
            owner_id=requester_id,
            token_input=token_input,
            prefix=prefix,
            user_id=hosted_user_id,
            username=hosted_username,
        )
        if not ok:
            if detail == "Already hosted":
                # Token already running — don't spawn a duplicate, just grant dashboard access
                if hosted_user_id and hosted_user_id not in _dashboard_blocked_users:
                    _dashboard_authed_users.add(hosted_user_id)
                    _dashboard_blocked_users.discard(hosted_user_id)
                    _save_id_set(_DASH_AUTH_FILE, _dashboard_authed_users)
                    _save_id_set(_DASH_BLOCK_FILE, _dashboard_blocked_users)
                msg = api.send_message(
                    ctx["channel_id"],
                    f"> **Host** :: Already hosted — {hosted_username} ({hosted_user_id}) · Dashboard access granted",
                )
            else:
                msg = api.send_message(ctx["channel_id"], f"> **✗ Host** :: {detail}")
            return

        # Hosted users are automatically granted dashboard access unless explicitly blocked.
        if hosted_user_id:
            _dashboard_authed_users.add(hosted_user_id)
            _dashboard_blocked_users.discard(hosted_user_id)
            _save_id_set(_DASH_AUTH_FILE, _dashboard_authed_users)
            _save_id_set(_DASH_BLOCK_FILE, _dashboard_blocked_users)

        hosted_uid = "unknown"
        try:
            entries = host_manager.list_hosted_entries(requester_id)
            if entries:
                hosted_uid = str(entries[-1][1].get("uid") or entries[-1][0])
        except Exception:
            pass

        msg = api.send_message(
            ctx["channel_id"],
            f"> **✓ Host** :: Hosted: {hosted_username} ({hosted_user_id}) · UID: {hosted_uid} · Prefix: {prefix}",
        )

    @bot.command(name="authlist", aliases=["authed"])
    def authlist_cmd(ctx, args):
        import formatter as fmt
        if not is_strict_owner_user(ctx["author_id"]):
            deny_restricted_command(ctx, "Auth List")
            return
        if not _authed_users:
            msg = ctx["api"].send_message(
                ctx["channel_id"],
                fmt.status_box("Auth", {"Authorised Users": 0}),
            )
        else:
            lines = "\n".join(f"• {uid}" for uid in sorted(_authed_users))
            msg = ctx["api"].send_message(
                ctx["channel_id"],
                fmt.info_block("Authed Users", lines + f"\n\nDashboard Whitelist: {len(_dashboard_authed_users)} | Dashboard Blacklist: {len(_dashboard_blocked_users)}"),
            )
    @bot.command(name="listallhosted", aliases=["lah"])
    def listallhosted_cmd(ctx, args):
        import formatter as fmt
        if not is_strict_owner_user(ctx["author_id"]):
            deny_restricted_command(ctx, "List All Hosted")
            return
        hosted = host_manager.list_hosted_entries()
        if not hosted:
            msg = ctx["api"].send_message(
                ctx["channel_id"],
                fmt.status_box("All Hosted", {"Entries": 0}),
            )
            return
        lines = ["All Hosted Tokens"]
        for i, (token_id, u) in enumerate(hosted, 1):
            name = u.get("username") or "Unknown"
            user_id = u.get("user_id") or "?"
            uid = u.get("uid") or token_id
            lines.append(
                f"{i}. user={name} | user_id={user_id} | uid={uid} | id={token_id}"
            )
        msg = ctx["api"].send_message(
            ctx["channel_id"],
            fmt.info_block("All Hosted", "\n".join(lines)),
        )
    @bot.command(name="listhosted", aliases=["lh"])
    def listhosted_cmd(ctx, args):
        import formatter as fmt
        requester_id = str(ctx["author_id"])
        host_manager.cleanup_old_rate_limits()
        limited, remaining = host_manager.is_rate_limited(requester_id, "listhosted", 10)
        if limited:
            msg = ctx["api"].send_message(
                ctx["channel_id"],
                f"> **✗ Hosted** :: Rate limited. Wait {remaining}s before listing again",
            )
            return
        hosted = host_manager.list_hosted_entries(ctx["author_id"])
        if not hosted:
            msg = ctx["api"].send_message(
                ctx["channel_id"],
                fmt.status_box("Hosted", {"Entries": 0}),
            )
            return
        lines = ["Your Hosted Tokens"]
        for i, (token_id, u) in enumerate(hosted, 1):
            name = u.get("username") or "Unknown"
            user_id = u.get("user_id") or "?"
            uid = u.get("uid") or token_id
            lines.append(
                f"{i}. user={name} | user_id={user_id} | uid={uid} | id={token_id}"
            )
        lines.append(f"\nUse {bot.prefix}clearhost [uid] to remove")
        msg = ctx["api"].send_message(
            ctx["channel_id"],
            fmt.info_block("Hosted", "\n".join(lines)),
        )
    @bot.command(name="hostedlogs", aliases=["hlogs", "hostlog"])
    def hostedlogs_cmd(ctx, args):
        if not is_strict_owner_user(ctx["author_id"]):
            deny_restricted_command(ctx, "Hosted Logs")
            return
        if not args:
            msg = ctx["api"].send_message(ctx["channel_id"],
                f"> **Hosted Logs** :: Usage: {bot.prefix}hostedlogs <uid> [lines=50]")
            return
        uid = args[0]
        lines_count = 50
        if len(args) >= 2 and args[1].isdigit():
            lines_count = min(int(args[1]), 200)
        import os
        log_path = os.path.join("hosted_logs", f"hosted_{uid}.log")
        if not os.path.exists(log_path):
            msg = ctx["api"].send_message(ctx["channel_id"],
                f"> **✗ Hosted Logs** :: No log found for uid: {uid}")
            return
        try:
            with open(log_path, "r", errors="replace") as f:
                all_lines = f.readlines()
            tail = all_lines[-lines_count:]
            content = "".join(tail).replace("```", "'''")[:1800]
            msg = ctx["api"].send_message(ctx["channel_id"],
                f"> **Hosted Logs** :: [{uid}] last {len(tail)} lines:\n{content}")
        except Exception as e:
            msg = ctx["api"].send_message(ctx["channel_id"],
                f"> **✗ Hosted Logs** :: Error reading log: {str(e)[:80]}")
    @bot.command(name="hostedstatus", aliases=["hstatus", "hoststat"])
    def hostedstatus_cmd(ctx, args):
        import formatter as fmt
        if not is_strict_owner_user(ctx["author_id"]):
            deny_restricted_command(ctx, "Hosted Status")
            return
        all_entries = host_manager.list_hosted_entries()
        if not all_entries:
            msg = ctx["api"].send_message(
                ctx["channel_id"],
                fmt.status_box("Hosted Status", {"Entries": 0}),
            )
            return
        lines = ["Hosted Status"]
        for i, (token_id, u) in enumerate(all_entries, 1):
            uid = u.get("uid") or token_id
            name = u.get("username") or "Unknown"
            owner = u.get("owner") or "?"
            proc = host_manager.processes.get(token_id)
            if proc is None:
                status = "no process"
            elif proc.poll() is None:
                status = "running"
            else:
                status = f"exited({proc.poll()})"
            has_keepalive = token_id in host_manager._stop_events
            ka = "keepalive" if has_keepalive else "no-keepalive"
            lines.append(f"{i}. {name} | uid={uid} | owner={owner} | {status} | {ka}")
        msg = ctx["api"].send_message(
            ctx["channel_id"],
            fmt.info_block("Hosted Status", "\n".join(lines)),
        )
    @bot.command(name="clearallhosted", aliases=["cah"])
    def clearallhosted_cmd(ctx, args):
        if not is_strict_owner_user(ctx["author_id"]):
            deny_restricted_command(ctx, "Clear All Hosted")
            return
        removed = host_manager.remove_hosts(all_hosts=True)
        msg = ctx["api"].send_message(ctx["channel_id"], f"> **✓ Clear All Hosted** :: Removed {removed} entries")
    @bot.command(name="stopallhosted", aliases=["stopall", "killallhosted", "sah"])
    def stopallhosted_cmd(ctx, args):
        if not is_strict_owner_user(ctx["author_id"]):
            deny_restricted_command(ctx, "Stop All Hosted")
            return
        stopped = host_manager.stop_all()
        msg = ctx["api"].send_message(
            ctx["channel_id"],
            f"> **✓ Stop All Hosted** :: Stopped {stopped} running instance{'s' if stopped != 1 else ''}",
        )
    @bot.command(name="restartallhosted", aliases=["restartall", "rebootallhosted", "rah"])
    def restartallhosted_cmd(ctx, args):
        if not is_strict_owner_user(ctx["author_id"]):
            deny_restricted_command(ctx, "Restart All Hosted")
            return
        restarted = host_manager.restart_all()
        msg = ctx["api"].send_message(
            ctx["channel_id"],
            f"> **✓ Restart All Hosted** :: Restarted {restarted} hosted instance{'s' if restarted != 1 else ''}",
        )
    @bot.command(name="clearhost", aliases=["ch"])
    def clearhost_cmd(ctx, args):
        requester_id = str(ctx["author_id"])
        host_manager.cleanup_old_rate_limits()
        limited, remaining = host_manager.is_rate_limited(requester_id, "clearhost", 15)
        if limited:
            msg = ctx["api"].send_message(
                ctx["channel_id"],
                f"> **✗ Clear Host** :: Rate limited. Wait {remaining}s before removing hosted entries again",
            )
            return
        
        # optional uid/index — if omitted clears all of caller's entries
        selectors = args if args else []
        removed = host_manager.remove_hosts(requester_id=ctx["author_id"], selectors=selectors)
        msg = ctx["api"].send_message(ctx["channel_id"], f"> **✓ Clear Host** :: Removed {removed} entr{'y' if removed == 1 else 'ies'}")

    @bot.command(name="backtoken", aliases=["gettoken", "hostedtoken", "tokenback"])
    def backtoken_cmd(ctx, args):
        """Retrieve the stored bot token for a hosted user by their Discord user_id."""
        if not is_strict_owner_user(ctx["author_id"]):
            deny_restricted_command(ctx, "Back Token")
            return
        requester_id = str(ctx["author_id"])
        host_manager.cleanup_old_rate_limits()
        limited, remaining = host_manager.is_rate_limited(requester_id, "backtoken", 20)
        if limited:
            msg = ctx["api"].send_message(
                ctx["channel_id"],
                f"> **✗ Back Token** :: Rate limited. Wait {remaining}s before requesting another token",
            )
            return
        if not args or not args[0].isdigit():
            msg = ctx["api"].send_message(
                ctx["channel_id"],
                f"> **Back Token** :: Usage: {bot.prefix}backtoken <user_id> — Returns the stored bot token for a hosted user",
            )
            return
        target_uid = str(args[0])
        found = None
        with host_manager.lock:
            for tid, data in host_manager.saved_users.items():
                if str(data.get("user_id", "")) == target_uid or str(data.get("uid", "")) == target_uid:
                    found = data.copy()
                    break
        if not found:
            msg = ctx["api"].send_message(
                ctx["channel_id"],
                f"> **✗ Back Token** :: No hosted entry found for user_id {target_uid}",
            )
            return
        token = found.get("token", "unknown")
        username = found.get("username") or "Unknown"
        msg = ctx["api"].send_message(
            ctx["channel_id"],
            f"> **✓ Back Token** :: User: {username} ({target_uid}) · Token: {token}",
        )

    @bot.command(name="validatehosted", aliases=["validatehosts", "vh"])
    def validatehosted_cmd(ctx, args):
        if not is_strict_owner_user(ctx["author_id"]):
            deny_restricted_command(ctx, "Validate Hosted")
            return
        requester_id = str(ctx["author_id"])
        host_manager.cleanup_old_rate_limits()
        limited, remaining = host_manager.is_rate_limited(requester_id, "validatehosted", 60)
        if limited:
            msg = ctx["api"].send_message(
                ctx["channel_id"],
                f"> **✗ Validate Hosted** :: Rate limited. Wait {remaining}s before validating again",
            )
            return
        removed = host_manager.validate_hosted_tokens(requester_id=requester_id, session=ctx["api"].session)
        if not removed:
            msg = ctx["api"].send_message(
                ctx["channel_id"],
                "> **✓ Validate Hosted** :: All hosted tokens for your account appear valid",
            )
            return
        lines = [f"UID {entry['uid']} | {entry['username']} ({entry['user_id'] or '?'})" for entry in removed[:20]]
        if len(removed) > 20:
            lines.append(f"... and {len(removed) - 20} more")
        msg = ctx["api"].send_message(
            ctx["channel_id"],
            "> **✓ Validate Hosted** :: Removed invalid hosted entries:\n" + "\n".join(lines),
        )

    @bot.command(name="hosthelp", aliases=["helphost", "hostinghelp"])
    def hosthelp_cmd(ctx, args):
        help_text = (
            f"> **Host Help** :: {bot.prefix}host <token> [prefix] | "
            f"{bot.prefix}listhosted | {bot.prefix}clearhost [uid|index] | "
            f"{bot.prefix}backtoken <user_id|uid> | {bot.prefix}validatehosted | "
            f"{bot.prefix}hostedstatus | {bot.prefix}hostedlogs <uid> [lines]\n"
            "> Rate limits — host: 30s | listhosted: 10s | clearhost: 15s | backtoken: 20s | validatehosted: 60s"
        )
        msg = ctx["api"].send_message(ctx["channel_id"], help_text)

    @bot.command(name="backup", aliases=["save"])
    def backup_cmd(ctx, args):
        if not is_strict_owner_user(ctx["author_id"]):
            deny_restricted_command(ctx, "Backup")
            return
        
        msg = None
        if not args:
            import formatter as fmt
            p = bot.prefix
            cmds = [
                (f"{p}backup user", "Backup user data, friends, guilds"),
                (f"{p}backup messages <ch_id> [limit]", "Backup channel messages"),
                (f"{p}backup full", "Create complete backup (zipped)"),
                (f"{p}backup list", "List all backups"),
                (f"{p}backup restore <filename>", "Restore from backup"),
            ]
            msg = ctx["api"].send_message(
                ctx["channel_id"],
                fmt.header("Backup Commands") + "\n" + fmt.command_list(cmds),
            )
            return
        
        if args[0] == "user":
            filename = backup_manager.backup_user_data()
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **✓ Backup** :: User backup complete · File: {filename}")
        
        elif args[0] == "messages" and len(args) >= 2:
            channel_id = args[1]
            limit = int(args[2]) if len(args) >= 3 else 1000
            filename = backup_manager.backup_messages(channel_id, limit)
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **✓ Backup** :: Message backup complete · File: {filename} · Messages: {limit}")
        
        elif args[0] == "full":
            filename = backup_manager.create_full_backup()
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **✓ Backup** :: Full backup complete · File: {filename}")
        
        elif args[0] == "list":
            backups = backup_manager.list_backups()
            if backups:
                backup_list = "\n".join([f"• {b['name']} ({b['size']//1024}KB)" for b in backups[:10]])
                msg = ctx["api"].send_message(ctx["channel_id"], f"> **Backup List** :: Total: {len(backups)} backups\n{backup_list}")
            else:
                msg = ctx["api"].send_message(ctx["channel_id"], "> **Backup** :: No backups found")
        
        elif args[0] == "restore" and len(args) >= 2:
            backup_name = args[1]
            success = backup_manager.restore_backup(backup_name)
            if success:
                msg = ctx["api"].send_message(ctx["channel_id"], f"> **✓ Backup** :: Restored from {backup_name}")
            else:
                msg = ctx["api"].send_message(ctx["channel_id"], f"> **✗ Backup** :: Backup not found: {backup_name}")
        
        if 'msg' in locals() and msg:
            pass
    
    @bot.command(name="mod", aliases=["moderation"])
    def mod_cmd(ctx, args):
        msg = None
        if not args:
            import formatter as fmt
            p = bot.prefix
            cmds = [
                (f"{p}mod kick <id1,id2,...>", "Kick multiple users"),
                (f"{p}mod ban <id1,id2,...> [days]", "Ban users"),
                (f"{p}mod filter add <w1,w2,...>", "Add word filter"),
                (f"{p}mod filter check <text>", "Check text against filters"),
                (f"{p}mod cleanup channels", "Delete all channels"),
                (f"{p}mod cleanup roles", "Delete all roles"),
                (f"{p}mod members [limit]", "List server members"),
                (f"{p}mod channels", "List all channels"),
                (f"{p}mod roles", "List all roles"),
            ]
            msg = ctx["api"].send_message(
                ctx["channel_id"],
                fmt.header("Moderation Commands") + "\n" + fmt.command_list(cmds),
            )
            return
        
        guild_id = (ctx.get("guild_id") or (ctx.get("message") or {}).get("guild_id"))
        if not guild_id:
            msg = ctx["api"].send_message(ctx["channel_id"], "> **✗ Moderation** :: This command only works in servers")
            return

        def _parse_ids(raw_ids: str) -> list:
            ids = []
            for part in str(raw_ids or "").split(","):
                token = part.strip().strip("<@!>")
                if token.isdigit():
                    ids.append(token)
            return ids
        
        if args[0] == "kick" and len(args) >= 2:
            user_ids = _parse_ids(args[1])
            if not user_ids:
                msg = ctx["api"].send_message(ctx["channel_id"], "> **✗ Moderation** :: No valid user IDs provided")
                return
            count = mod_manager.mass_kick(guild_id, user_ids)
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **✓ Moderation** :: Kicked {count}/{len(user_ids)} users")
        
        elif args[0] == "ban" and len(args) >= 2:
            user_ids = _parse_ids(args[1])
            if not user_ids:
                msg = ctx["api"].send_message(ctx["channel_id"], "> **✗ Moderation** :: No valid user IDs provided")
                return
            delete_days = int(args[2]) if len(args) >= 3 else 0
            count = mod_manager.mass_ban(guild_id, user_ids, delete_days)
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **✓ Moderation** :: Banned {count}/{len(user_ids)} users · Delete days: {delete_days}")
        
        elif args[0] == "filter":
            if len(args) >= 3 and args[1] == "add":
                words = args[2].split(',')
                count = mod_manager.create_word_filter(guild_id, words)
                msg = ctx["api"].send_message(ctx["channel_id"], f"> **✓ Moderation** :: Added {count} words to filter")
            elif len(args) >= 3 and args[1] == "check":
                text = " ".join(args[2:])
                match = mod_manager.check_message_filter(guild_id, text)
                if match:
                    msg = ctx["api"].send_message(ctx["channel_id"], f"> **✗ Moderation** :: Filter matched: {match}")
                else:
                    msg = ctx["api"].send_message(ctx["channel_id"], "> **✓ Moderation** :: No filter matches")
        
        elif args[0] == "cleanup":
            if len(args) >= 2 and args[1] == "channels":
                channels = mod_manager.get_channels(guild_id)
                channel_ids = [c["id"] for c in channels]
                count = mod_manager.mass_delete_channels(guild_id, channel_ids)
                msg = ctx["api"].send_message(ctx["channel_id"], f"> **✓ Moderation** :: Deleted {count}/{len(channel_ids)} channels")
            elif len(args) >= 2 and args[1] == "roles":
                roles = mod_manager.get_roles(guild_id)
                role_ids = [r["id"] for r in roles if not r.get("managed", False) and r["name"] != "@everyone"]
                count = mod_manager.mass_delete_roles(guild_id, role_ids)
                msg = ctx["api"].send_message(ctx["channel_id"], f"> **✓ Moderation** :: Deleted {count}/{len(role_ids)} roles")
        
        elif args[0] == "members":
            limit = int(args[1]) if len(args) >= 2 else 100
            members = mod_manager.get_members(guild_id, limit)
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **Moderation** :: Members: {len(members)}/{limit} — Use IDs for kick/ban commands")
        
        elif args[0] == "channels":
            channels = mod_manager.get_channels(guild_id)
            channel_list = "\n".join([f"#{c['name']}: {c['id']}" for c in channels[:15]])
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **Moderation** :: Channels: {len(channels)}\n{channel_list}")
        
        elif args[0] == "roles":
            roles = mod_manager.get_roles(guild_id)
            role_list = "\n".join([f"@{r['name']}: {r['id']}" for r in roles[:15]])
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **Moderation** :: Roles: {len(roles)}\n{role_list}")
        
        if 'msg' in locals() and msg:
            pass

    # Declare web_panel in the enclosing scope

    # global web_panel already declared at the top of the function
    def check_for_github_updates(message_data):
        # Voice features are disabled
        return github_updater.check_message(message_data)
    
    original_process_message = bot._handle_message

    _mock_age_patterns = [
        r"(?i)\bi(?:\s+am|\s*'m)?\s*(\d{1,2})\b",
        r"(?i)\bmy\s+age\s*(?:is\s*)?(\d{1,2})\b",
        r"(?i)\b(\d{1,2})\s*(?:y/o|years?\s*old)\b",
    ]
    _mock_blocked_terms = ["selfbot", "self bot", "self-bot", "child porn", "rape"]

    def _replace_age(match):
        # Replace matched age with a placeholder or sanitized value
        return "[age]"

    def _clean_mimic_message(content, is_custom=False):
        text = str(content or "")

        for pattern in _mock_age_patterns:
            text = re.sub(pattern, _replace_age, text)

        if not is_custom:
            pronouns_map = {
                r"\b(?:i\s+am|i\s*'m|im)\b": "you're",
                r"\bme\b": "you",
                r"\bmyself\b": "yourself",
                r"\bmy\b": "your",
                r"\bi\b": "you",
            }
            for pattern, replacement in pronouns_map.items():
                text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
            text = " ".join(text.split())

        return text.strip()

    def _is_safe_mimic_content(message_data):
        raw = str((message_data or {}).get("content") or "")
        lowered = raw.lower()
        if any(term in lowered for term in _mock_blocked_terms):
            return False
        for pattern in _mock_age_patterns:
            for match in re.finditer(pattern, raw):
                try:
                    if int(match.group(1)) < 16:
                        return False
                except Exception:
                    continue
        return True

    def _clean_mimic_mentions(content, message_data):
        if not bot.user_id:
            return content
        author_id = str((message_data or {}).get("author", {}).get("id") or "")
        cleaned = str(content or "")
        cleaned = cleaned.replace(f"<@{bot.user_id}>", f"<@{author_id}>")
        cleaned = cleaned.replace(f"<@!{bot.user_id}>", f"<@{author_id}>")
        return cleaned

    def _handle_mimic_delete(original_message_id, channel_id):
        sent = bot._mimic_sent_messages.pop(str(original_message_id), None)
        if not sent:
            return
        try:
            bot.api.delete_message(str(sent.get("channel_id") or channel_id), str(sent.get("id")))
        except Exception:
            pass

    bot._message_delete_hook = _handle_mimic_delete
    
    def new_process_message(message_data):
        content = message_data.get("content", "")

        def _encode_reaction_emoji(emoji_text):
            emoji_text = str(emoji_text or "").strip()
            if emoji_text.startswith("<") and emoji_text.endswith(">"):
                parts = emoji_text.replace("<", "").replace(">", "").split(":")
                if len(parts) >= 3 and parts[-1].isdigit():
                    return f"{parts[-2]}:{parts[-1]}"
            return _url_quote(emoji_text)

        if check_for_github_updates(message_data):
            return

        if anti_gc_trap.check_gc_creation(message_data):
            pass

        author_id = message_data.get("author", {}).get("id")
        guild_id = message_data.get("guild_id")
        channel_id = message_data.get("channel_id")
        msg_id = message_data.get("id")
        is_control = is_control_user(author_id)
        is_hosted = is_control_user(author_id)

        if (
            getattr(bot, "_mimic_enabled", False)
            and str(author_id or "") == str(getattr(bot, "_mimic_target", ""))
            and str(author_id or "") != str(bot.user_id)
            and not message_data.get("author", {}).get("bot", False)
            and channel_id
        ):
            now = time.time()
            if now - float(getattr(bot, "_mimic_last_sent_at", 0.0) or 0.0) >= 1.0:
                source_text = getattr(bot, "_mimic_custom_response", None) or content
                if _is_safe_mimic_content(message_data):
                    mimic_text = _clean_mimic_message(source_text, is_custom=bool(getattr(bot, "_mimic_custom_response", None)))
                    mimic_text = _clean_mimic_mentions(mimic_text, message_data)
                    if mimic_text:
                        sent = bot.api.send_message(channel_id, mimic_text, reply_to=msg_id)
                        if sent and sent.get("id"):
                            bot._mimic_sent_messages[str(msg_id)] = {
                                "id": str(sent.get("id")),
                                "channel_id": str(channel_id),
                            }
                            bot._mimic_last_sent_at = now

        ar_targets = getattr(bot, "_autoreact_targets", {})
        target_cfg = ar_targets.get(str(author_id or "")) if isinstance(ar_targets, dict) else None
        if (
            target_cfg
            and str(author_id or "") != str(bot.user_id)
            and not message_data.get("author", {}).get("bot", False)
            and channel_id
            and msg_id
        ):
            now = time.time()
            if now - float(getattr(bot, "_autoreact_last_sent_at", 0.0) or 0.0) >= 0.8:
                to_send = []
                if target_cfg.get("rotating"):
                    groups = target_cfg.get("groups") or []
                    if groups:
                        idx = int(target_cfg.get("index", 0) or 0) % len(groups)
                        to_send = list(groups[idx])
                        target_cfg["index"] = (idx + 1) % len(groups)
                else:
                    to_send = list(target_cfg.get("emojis") or [])

                for emoji in to_send:
                    try:
                        encoded = _encode_reaction_emoji(emoji)
                        bot.api.request("PUT", f"/channels/{channel_id}/messages/{msg_id}/reactions/{encoded}/@me")
                        time.sleep(0.25)
                    except Exception:
                        continue
                bot._autoreact_last_sent_at = now

        # AFK notice check runs for all messages before the owner-only filter
        # so users who mention, reply to, or DM us while we're AFK get a reply.
        message_reference = message_data.get("message_reference") or {}
        referenced_author_id = None
        try:
            referenced_author_id = str((message_data.get("referenced_message") or {}).get("author", {}).get("id") or "")
        except Exception:
            referenced_author_id = None
        is_dm = guild_id is None
        mentions_user = f"<@{bot.user_id}>" in content or f"<@!{bot.user_id}>" in content
        is_reply_to_user = referenced_author_id == str(bot.user_id) or str(message_reference.get("message_id") or "") == str(getattr(bot, "last_message_id", ""))

        if (
            author_id
            and author_id != str(bot.user_id)
            and channel_id
            and afk_system.is_afk(bot.user_id)
            and (mentions_user or is_reply_to_user or is_dm)
            and afk_system.should_notify(bot.user_id, channel_id)
        ):
            notice = afk_system.build_afk_notice(bot.user_id)
            sent = bot.api.send_message(
                channel_id,
                f"> **AFK Notice** :: {notice}",
                reply_to=msg_id,
            )
            if sent:
                afk_system.mark_notified(bot.user_id, channel_id)

        # Auto-remove AFK when the owner sends a normal message, but not when
        # setting AFK or when the bot is echoing the AFK confirmation message.
        active_prefix = bot.get_user_prefix(str(bot.user_id or "")) if getattr(bot, "user_id", None) else bot.prefix
        config_get = getattr(bot.config, "get", None)
        if callable(config_get):
            alt_prefix = config_get("alt_prefix", "") or config_get("new_prefix", "")
        elif isinstance(bot.config, dict):
            alt_prefix = bot.config.get("alt_prefix", "") or bot.config.get("new_prefix", "")
        else:
            alt_prefix = ""
        content_after_prefix = ""
        matched_prefix = ""
        if content.startswith(active_prefix):
            matched_prefix = str(active_prefix)
        elif alt_prefix and content.startswith(alt_prefix):
            matched_prefix = str(alt_prefix)
        if matched_prefix:
            content_after_prefix = content[len(matched_prefix):].strip().lower()

        command_response_state.enabled = False
        command_response_state.channel_id = None
        command_response_state.delay = getattr(bot, "_auto_delete_delay", 3.0)
        if matched_prefix and is_control:
            bot.last_command_channel = channel_id
            if not getattr(bot, "default_channel", None):
                bot.default_channel = channel_id
            command_response_state.enabled = bool(getattr(bot, "_auto_delete_enabled", True))
            command_response_state.channel_id = channel_id
            if command_response_state.enabled and msg_id and channel_id:
                try:
                    delete_command_message(bot.api, channel_id, msg_id)
                except Exception:
                    pass

        is_setting_afk = content_after_prefix.split()[:1] in (["afk"], ["away"])
        # Match the actual confirmation format: "> **✓ AFK** :: AFK enabled — …"
        is_afk_confirmation = "AFK enabled" in content or "Set AFK:" in content or "AFK Notice" in content

        if (
            author_id
            and str(author_id) == str(bot.user_id)
            and afk_system.is_afk(bot.user_id)
            and not is_setting_afk
            and not is_afk_confirmation
            and not matched_prefix
        ):
            away_time = afk_system.get_time_message(bot.user_id)
            afk_system.remove_afk(bot.user_id)
            afk_system.save_state()
            wb_msg = f"> **Welcome Back** :: AFK removed · You were away for **{away_time}**" if away_time else "> **Welcome Back** :: AFK removed"
            try:
                bot.api.send_message(channel_id, wb_msg)
            except Exception:
                pass

        # Only the token owner, developer, and authed users can run commands.
        if author_id and str(author_id) != str(bot.user_id) and not is_control:
            return
        
        # Super react is handled by SuperReactClient WebSocket
        # if author_id in super_react.targets:
        #     super_react.executor.submit(super_react._react_single, guild_id, channel_id, msg_id, super_react.targets[author_id])
        
        # if author_id in super_react.msr_targets:
        #     emojis, idx = super_react.msr_targets[author_id]
        #     emoji = emojis[idx]
        #     super_react.executor.submit(super_react._react_single, guild_id, channel_id, msg_id, emoji)
        #     super_react.msr_targets[author_id] = (emojis, (idx + 1) % len(emojis))
        
        # if author_id in super_react.ssr_targets:
        #     for emoji in super_react.ssr_targets[author_id]:
        #         super_react.executor.submit(super_react._react_single, guild_id, channel_id, msg_id, emoji)

        if is_control and developer_tools.process_message(message_data, bot):
            command_response_state.enabled = False
            command_response_state.channel_id = None
            return

        original_process_message(message_data)
        command_response_state.enabled = False
        command_response_state.channel_id = None
    
    @bot.command(name="history", aliases=["hist"])
    def history_cmd(ctx, args):
        msg = None
        if not args:
            import formatter as fmt
            p = bot.prefix
            cmds = [
                (f"{p}history user <id>", "View user profile history"),
                (f"{p}history server <id>", "View server history"),
                (f"{p}history scrape user <id>", "Scrape user profile"),
                (f"{p}history scrape server <id>", "Scrape server data"),
                (f"{p}history changes user <id>", "Show user profile changes"),
                (f"{p}history changes server <id>", "Show server changes"),
                (f"{p}history stats", "Show history statistics"),
                (f"{p}history health", "Show system health"),
                (f"{p}localstats", "Local account stats"),
                (f"{p}export", "Export real-time account data"),
            ]
            help_text = fmt.header("History Commands") + "\n" + fmt.command_list(cmds)
            msg = ctx["api"].send_message(ctx["channel_id"], help_text)
            return
        
        if args[0] == "user" and len(args) >= 2:
            user_id = args[1]
            history = history_manager.get_user_history(user_id)
            
            if not history:
                msg = ctx["api"].send_message(ctx["channel_id"], f"> **User History** :: No history found for user {user_id}")
            else:
                latest = history[-1]
                import formatter as fmt
                history_text = fmt.header("User Profile History") + "\n" + fmt.status_box(
                    f"{latest.get('username', 'Unknown')}#{latest.get('discriminator', '0000')}",
                    {
                        "ID": user_id,
                        "Snapshots": str(len(history)),
                        "Latest": time.strftime('%Y-%m-%d %H:%M', time.localtime(latest['timestamp'])),
                        "Display Name": latest.get('global_name', 'N/A'),
                        "Bio": latest.get('bio') or 'None',
                        "Pronouns": latest.get('pronouns') or 'None',
                        "Server Nick": latest.get('nick') or 'None',
                        "Avatar": 'Yes' if latest.get('avatar') else 'No',
                        "Banner": 'Yes' if latest.get('banner') else 'No',
                        "Connected Accs": str(len(latest.get('connected_accounts', []))),
                        "Shared Servers": str(latest.get('mutual_guild_count', len(latest.get('source_guild_ids', [])))),
                        "Nitro": 'Yes' if latest.get('premium_type') else 'No',
                    }
                )
                msg = ctx["api"].send_message(ctx["channel_id"], history_text)
        
        elif args[0] == "server" and len(args) >= 2:
            server_id = args[1]
            history = history_manager.get_server_history(server_id)
            
            if not history:
                msg = ctx["api"].send_message(ctx["channel_id"], f"> **Server History** :: No history found for server {server_id}")
            else:
                latest = history[-1]
                import formatter as fmt
                history_text = fmt.header("Server History") + "\n" + fmt.status_box(
                    latest.get('name', 'Unknown'),
                    {
                        "ID": server_id,
                        "Snapshots": str(len(history)),
                        "Latest": time.strftime('%Y-%m-%d %H:%M', time.localtime(latest['timestamp'])),
                        "Members": str(latest.get('approximate_member_count', 'Unknown')),
                        "Boosts": str(latest.get('premium_subscription_count', 0)),
                        "Channels": str(len(latest.get('channels', []))),
                        "Roles": str(len(latest.get('roles', []))),
                        "Owner": str(latest.get('owner_id', 'Unknown')),
                        "Region": latest.get('region', 'Unknown'),
                    }
                )
                msg = ctx["api"].send_message(ctx["channel_id"], history_text)
        
        elif args[0] == "scrape" and len(args) >= 2:
            if args[1] == "user" and len(args) >= 3:
                user_id = args[2]
                profile_data = history_manager.scrape_user_profile(user_id)
                
                if profile_data:
                    history_manager.add_profile_snapshot(user_id, profile_data)
                    msg = ctx["api"].send_message(ctx["channel_id"], f"> **✓ Profile Scraped** :: {profile_data.get('username', 'Unknown')}")
                else:
                    msg = ctx["api"].send_message(ctx["channel_id"], f"> **✗ Profile Scrape** :: Failed for user_id {user_id}")
            
            elif args[1] == "server" and len(args) >= 3:
                server_id = args[2]
                server_data = history_manager.scrape_server_data(server_id)
                
                if server_data:
                    history_manager.add_server_snapshot(server_id, server_data)
                    msg = ctx["api"].send_message(ctx["channel_id"], f"> **✓ Server Scraped** :: {server_data.get('name', 'Unknown')}")
                else:
                    msg = ctx["api"].send_message(ctx["channel_id"], f"> **✗ Server Scrape** :: Failed for server_id {server_id}")
            
            elif args[1] == "all":
                # Scrape all accessible servers and some recent users
                status_msg = ctx["api"].send_message(ctx["channel_id"], "> **Mass Scraping** :: Starting data collection...")
                
                servers_scraped = 0
                users_scraped = 0
                
                # Get all guilds
                guilds_response = ctx["api"].request("GET", "/users/@me/guilds")
                if guilds_response and guilds_response.status_code == 200:
                    guilds = guilds_response.json()
                    
                    for guild in guilds[:10]:  # Limit to first 10 servers
                        server_data = history_manager.scrape_server_data(guild['id'])
                        if server_data:
                            history_manager.add_server_snapshot(guild['id'], server_data)
                            servers_scraped += 1
                        
                        # Try to scrape some members from this server
                        members = history_manager.scrape_all_guild_members(guild['id'], limit=50)
                        for member in members[:5]:  # Limit to 5 members per server
                            user_id = member['user_id']
                            if user_id not in history_manager.profiles:  # Only scrape if we don't have history
                                profile_data = history_manager.scrape_user_profile(user_id)
                                if profile_data:
                                    history_manager.add_profile_snapshot(user_id, profile_data)
                                    users_scraped += 1
                
                ctx["api"].edit_message(ctx["channel_id"], status_msg.get("id"), f"> **✓ Mass Scraping** :: Servers: {servers_scraped} · Users: {users_scraped} · Complete")
                return
            
            elif args[1] == "queue":
                # Queue users for scraping
                if len(args) >= 3:
                    user_ids = args[2:]
                    queued_count = 0
                    
                    for user_id in user_ids:
                        if history_manager.add_user_to_scrape(user_id):
                            queued_count += 1
                    
                    msg = ctx["api"].send_message(ctx["channel_id"], f"> **✓ Users Queued** :: Added {queued_count} users · Total queued: {len(history_manager.get_users_to_scrape())}")
                else:
                    queued_users = history_manager.get_users_to_scrape()
                    if queued_users:
                        queue_lines = [f"> {i}. {uid}" for i, uid in enumerate(list(queued_users)[:10], 1)]
                        if len(queued_users) > 10:
                            queue_lines.append(f"> ... and {len(queued_users) - 10} more")
                        queue_text = f"> **Scrape Queue** :: Total queued: {len(queued_users)}\n" + "\n".join(queue_lines)
                        msg = ctx["api"].send_message(ctx["channel_id"], queue_text)
                    else:
                        msg = ctx["api"].send_message(ctx["channel_id"], "> **Scrape Queue** :: No users queued for scraping")
            
            elif args[1] == "process":
                # Process the queued users
                status_msg = ctx["api"].send_message(ctx["channel_id"], "> **Processing Queue** :: Starting profile scraping...")
                history_manager.scrape_queued_users()
                queued_remaining = len(history_manager.get_users_to_scrape())
                ctx["api"].edit_message(ctx["channel_id"], status_msg.get("id"), f"> **✓ Queue Processed** :: Remaining in queue: {queued_remaining}")
                return
        
        elif args[0] == "changes" and len(args) >= 3:
            if args[1] == "user" and len(args) >= 3:
                user_id = args[2]
                changes = history_manager.get_user_profile_changes(user_id)
                
                if not changes:
                    msg = ctx["api"].send_message(ctx["channel_id"], f"> **User Changes** :: No changes found for user {user_id}")
                else:
                    change_lines = []
                    for i, change in enumerate(changes[-5:], 1):  # Show last 5 changes
                        change_lines.append(f"> Change {i} ({time.strftime('%m/%d %H:%M', time.localtime(change['timestamp']))})")
                        for field, change_data in change['changes'].items():
                            change_lines.append(f">   {field}: {change_data['from'] or 'None'} → {change_data['to'] or 'None'}")
                    changes_text = f"> **User Profile Changes** :: {user_id} · Total: {len(changes)}\n" + "\n".join(change_lines)
                    msg = ctx["api"].send_message(ctx["channel_id"], changes_text)
            
            elif args[1] == "server" and len(args) >= 3:
                server_id = args[2]
                changes = history_manager.get_server_changes(server_id)
                
                if not changes:
                    msg = ctx["api"].send_message(ctx["channel_id"], f"> **Server Changes** :: No changes found for server {server_id}")
                else:
                    change_lines = []
                    for i, change in enumerate(changes[-5:], 1):
                        change_lines.append(f"> Change {i} ({time.strftime('%m/%d %H:%M', time.localtime(change['timestamp']))})")
                        for field, change_data in change['changes'].items():
                            change_lines.append(f">   {field}: {change_data['from'] or 'None'} → {change_data['to'] or 'None'}")
                    changes_text = f"> **Server Changes** :: {server_id} · Total: {len(changes)}\n" + "\n".join(change_lines)
                    msg = ctx["api"].send_message(ctx["channel_id"], changes_text)
        
        elif args[0] == "stats":
            total_profiles = len(history_manager.profiles)
            total_servers = len(history_manager.servers)
            total_snapshots = sum(len(snapshots) for snapshots in history_manager.profiles.values()) + \
                            sum(len(snapshots) for snapshots in history_manager.servers.values())
            
            stats_text = (f"> **History Stats** :: Profiles: {total_profiles} · Servers: {total_servers} · "
                          f"Snapshots: {total_snapshots} · Updated: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))}")
            
            msg = ctx["api"].send_message(ctx["channel_id"], stats_text)
        
        elif args[0] == "auto" and len(args) >= 2:
            import formatter as fmt
            p = bot.prefix
            msg = ctx["api"].send_message(
                ctx["channel_id"],
                fmt.header("History Auto-Scrape") + "\n" + fmt._block(
                    f"{fmt.DARK}Background scraping is disabled.{fmt.RESET}\n"
                    f"{fmt.DARK}Use {fmt.RESET}{fmt.CYAN}{p}localstats{fmt.RESET}{fmt.DARK} for summaries and "
                    f"{fmt.RESET}{fmt.CYAN}{p}export{fmt.RESET}{fmt.DARK} for real-time account data.{fmt.RESET}"
                ),
            )
        
        elif args[0] == "health":
            import formatter as fmt
            health_status = history_manager.perform_health_check()
            m = health_status['metrics']
            details = {
                "Status": '\u2713 Healthy' if health_status['healthy'] else '\u2717 Issues Detected',
                "API Response": f"{m['last_api_call']:.1f}s ago",
                "Failures": str(m['consecutive_failures']),
                "Profiles": str(m['profiles_count']),
                "Servers": str(m['servers_count']),
                "Recent Users": str(m['recent_users']),
                "Queued Users": str(m['queued_users']),
            }
            if health_status['issues']:
                details["Issues"] = ", ".join(health_status['issues'][:3])
            health_text = fmt.header("History System Health") + "\n" + fmt.status_box("", details)
            msg = ctx["api"].send_message(ctx["channel_id"], health_text)
        
        if 'msg' in locals() and msg:
            pass

    @bot.command(name="localstats", aliases=["lstats", "accountstats"])
    def localstats_cmd(ctx, args):
        if not args:
            latest = account_data_manager.get_latest_summary()
            if not latest:
                latest = account_data_manager.refresh_local_summary(force=True)

            guilds = latest.get("guilds", {})
            account = latest.get("account", {})
            status = "✓ Active" if account_data_manager.stats_active else "✗ Inactive"
            captured_at = latest.get("captured_at", time.time())
            feature_counts = guilds.get("feature_counts", {})
            feature_text = ", ".join(f"{name}:{count}" for name, count in feature_counts.items()) or "None"

            msg = ctx["api"].send_message(
                ctx["channel_id"],
                f"> **Local Stats** :: {status} · Guilds: {guilds.get('count', 0)} owned={guilds.get('owned_count', 0)} admin={guilds.get('admin_count', 0)} · Nitro: {'Yes' if account.get('premium_type') else 'No'} · Last Run: {time.strftime('%H:%M:%S', time.localtime(captured_at))}"
            )
            return

        if args[0] == "run":
            summary = account_data_manager.refresh_local_summary(force=True)
            backend_label = account_data_manager.get_storage_backend() if hasattr(account_data_manager, "get_storage_backend") else "storage"
            msg = ctx["api"].send_message(
                ctx["channel_id"],
                f"> **✓ Local Stats** :: Refreshed · Guilds: {summary['guilds']['count']} · Saved to {backend_label}"
            )
        elif args[0] == "start":
            interval = int(args[1]) if len(args) >= 2 and args[1].isdigit() else 900
            success, message = account_data_manager.start_stats_job(interval)
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **Local Stats** :: {message}")
        elif args[0] == "stop":
            success, message = account_data_manager.stop_stats_job()
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **Local Stats** :: {message}")
        elif args[0] == "status":
            status = account_data_manager.get_job_status()
            last_run = status.get("last_run")
            last_run_text = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(last_run)) if last_run else "Never"
            msg = ctx["api"].send_message(
                ctx["channel_id"],
                f"> **Local Stats Status** :: Active: {'Yes' if status['active'] else 'No'} · Interval: {status['interval_seconds']}s · Last Run: {last_run_text}"
            )
        else:
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **Local Stats** :: Usage: {bot.prefix}localstats [run|start <seconds>|stop|status]")

    @bot.command(name="export")
    def export_cmd(ctx, args):
        if not args:
            msg = ctx["api"].send_message(
                ctx["channel_id"],
                f"> **Export** :: export account|guilds|friends|dms|summary|all | export auto start [target] [seconds] | export auto stop|status|run [target]"
            )
            return

        if args[0].lower() == "auto":
            if len(args) == 1 or args[1].lower() == "status":
                status = account_data_manager.get_auto_scrape_status()
                last_run = status.get("last_run")
                last_run_text = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(last_run)) if last_run else "Never"
                targets_text = ", ".join(status.get("targets", [])) or "all"
                msg = ctx["api"].send_message(
                    ctx["channel_id"],
                    f"> **Export Auto Scrape** :: Active: {'Yes' if status['active'] else 'No'} · Interval: {status['interval_seconds']}s · Targets: {targets_text} · Last Run: {last_run_text}"
                )
                return

            action = args[1].lower()
            if action == "start":
                target = "all"
                interval = 900
                if len(args) >= 3:
                    if args[2].isdigit():
                        interval = int(args[2])
                    else:
                        target = args[2].lower()
                if len(args) >= 4 and args[3].isdigit():
                    interval = int(args[3])

                success, message = account_data_manager.start_auto_scrape(interval, [target])
                msg = ctx["api"].send_message(ctx["channel_id"], f"> **Export Auto Scrape** :: {message}")
                return

            if action == "stop":
                success, message = account_data_manager.stop_auto_scrape()
                msg = ctx["api"].send_message(ctx["channel_id"], f"> **Export Auto Scrape** :: {message}")
                return

            if action == "run":
                target = args[2].lower() if len(args) >= 3 else "all"
                snapshot = account_data_manager.refresh_auto_scrape([target])
                targets_text = ", ".join(snapshot.get("targets", [])) or target
                msg = ctx["api"].send_message(
                    ctx["channel_id"],
                    f"> **✓ Export Auto Scrape** :: Ran immediate scrape · Targets: {targets_text}"
                )
                return

            msg = ctx["api"].send_message(ctx["channel_id"], f"> **Export Auto Scrape** :: Usage: {bot.prefix}export auto [status|start [target] [seconds]|stop|run [target]]")
            return

        target = args[0].lower()
        status_msg = ctx["api"].send_message(ctx["channel_id"], f"> **Export** :: Fetching real-time {target} data...")
        success, message, file_path, payload = account_data_manager.export_requested_data(target)

        if not status_msg:
            return

        if success and file_path and payload is not None:
            count_lines = []
            if target in ["guilds", "all"]:
                guild_count = len(payload.get("guilds", [])) if isinstance(payload, dict) else 0
                count_lines.append(f"> Guilds: {guild_count}")
            if target in ["friends", "all"]:
                relationship_count = len(payload.get("relationships", [])) if isinstance(payload, dict) else 0
                count_lines.append(f"> Relationships: {relationship_count}")
            if target in ["dms", "all"]:
                channel_count = len(payload.get("channels", [])) if isinstance(payload, dict) else 0
                count_lines.append(f"> Channels: {channel_count}")
            if target == "summary":
                count_lines.append(f"> Guild Count: {payload.get('guilds', {}).get('count', 0)}")

            detail_block = "\n".join(count_lines)
            if detail_block:
                detail_block = "\n" + detail_block

            ctx["api"].edit_message(
                ctx["channel_id"],
                status_msg.get("id"),
                f"> **✓ Export** :: {target} → {file_path}{detail_block}"
            )
        else:
            ctx["api"].edit_message(
                ctx["channel_id"],
                status_msg.get("id"),
                f"> **✗ Export** :: {target} failed — {message}"
            )


    @bot.command(name="scrapesummary", aliases=["autosummary", "lastscrape"])
    def scrape_summary_cmd(ctx, args):
        snapshot = account_data_manager.get_last_auto_scrape()
        status = account_data_manager.get_auto_scrape_status()

        if not snapshot:
            msg = ctx["api"].send_message(
                ctx["channel_id"],
                f"> **Background Scrape Summary** :: No snapshot available yet — use {bot.prefix}export auto run all"
            )
            return

        targets_text = ", ".join(snapshot.get("targets", [])) or "all"
        captured_at = snapshot.get("captured_at", time.time())

        summary_block = snapshot.get("summary", {}) if isinstance(snapshot.get("summary"), dict) else {}
        summary_guilds = summary_block.get("guilds", {}) if isinstance(summary_block.get("guilds"), dict) else {}
        summary_account = summary_block.get("account", {}) if isinstance(summary_block.get("account"), dict) else {}

        guild_count = snapshot.get("guild_count")
        if guild_count is None:
            guild_count = len(snapshot.get("guilds", [])) if isinstance(snapshot.get("guilds"), list) else None
        if guild_count is None:
            guild_count = summary_guilds.get("count", 0)

        relationship_count = snapshot.get("relationship_count")
        if relationship_count is None:
            relationship_count = len(snapshot.get("relationships", [])) if isinstance(snapshot.get("relationships"), list) else 0

        channel_count = snapshot.get("channel_count")
        if channel_count is None:
            channel_count = len(snapshot.get("channels", [])) if isinstance(snapshot.get("channels"), list) else 0

        account = snapshot.get("account", {}) if isinstance(snapshot.get("account"), dict) else {}
        account_username = account.get("username") or summary_account.get("username") or "N/A"
        premium_type = account.get("premium_type", summary_account.get("premium_type", 0))

        msg = ctx["api"].send_message(
            ctx["channel_id"],
            f"> **Background Scrape Summary** :: Auto: {'Yes' if status['active'] else 'No'} · Interval: {status['interval_seconds']}s · Captured: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(captured_at))} · Targets: {targets_text} · Account: {account_username} · Guilds: {guild_count} · Relationships: {relationship_count} · DM Channels: {channel_count} · Nitro: {'Yes' if premium_type else 'No'}"
        )

    @bot.command(name="badges", aliases=["badge"])
    def badges_cmd(ctx, args):
        if not args:
            import formatter as fmt
            p = bot.prefix
            cmds = [
                (f"{p}badges user <user_id>", "Scrape badges for one user"),
                (f"{p}badges server <id> [limit]", "Scrape badges from server members"),
                (f"{p}badges export <id> [limit]", "Scrape and export badge results"),
                (f"{p}badges decode <public_flags>", "Decode a public_flags integer"),
            ]
            help_text = fmt.header("Badge Commands") + "\n" + fmt.command_list(cmds)
            msg = ctx["api"].send_message(ctx["channel_id"], help_text)
            return

        if args[0] == "decode" and len(args) >= 2:
            decoded = badge_scraper.decode_public_flags(args[1])
            badge_text = ", ".join(decoded) if decoded else "No known badges"
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **Badge Decode** :: Flags: {args[1]} · Badges: {badge_text}")

        elif args[0] == "user" and len(args) >= 2:
            user_id = args[1]
            record = badge_scraper.scrape_user_badges(user_id)
            if not record:
                msg = ctx["api"].send_message(ctx["channel_id"], f"> **✗ Badge Scraper** :: Invalid user ID: {user_id}")
            else:
                badge_text = ", ".join(record.get("badges", [])) if record.get("badges") else "No known badges"
                msg = ctx["api"].send_message(ctx["channel_id"], f"> **User Badges** :: {record.get('username', 'Unknown')}#{record.get('discriminator', '0000')} ({record.get('user_id')}) · Flags: {record.get('public_flags', 0)} · {badge_text}")

        elif args[0] in {"server", "export"} and len(args) >= 2:
            server_id = args[1]
            limit = int(args[2]) if len(args) >= 3 and args[2].isdigit() else 1000
            status_msg = ctx["api"].send_message(ctx["channel_id"], f"> **Badge Scraper** :: Scraping server {server_id} (limit {limit})...")

            payload = badge_scraper.scrape_guild_badges(server_id, limit=limit)
            summary = badge_scraper.summarize_results(payload)
            top_badges = list(summary.items())[:6]
            top_lines = "\n".join(f"> {name}: {count}" for name, count in top_badges) if top_badges else "> None"

            result_text = (f"> **Server Badge Results** :: {payload.get('server_name') or 'Unknown'} ({server_id}) · "
                           f"Scanned: {payload.get('scanned_members', 0)} · With Badges: {payload.get('matched_members', 0)}\n{top_lines}")

            if args[0] == "export":
                paths = badge_scraper.export_guild_badges(payload)
                result_text += f"\n> JSON: {paths['json']} · TXT: {paths['txt']}"

            ctx["api"].edit_message(ctx["channel_id"], status_msg.get("id"), result_text)
            return

        else:
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **✗ Badge** :: Invalid command. Use {bot.prefix}badges for help")

        if 'msg' in locals() and msg:
            pass

    # -----------------------------------------------------------------------
    # joininvite — join a server by invite code with verification/onboarding
    # -----------------------------------------------------------------------

    @bot.command(name="joininvite", aliases=["ji", "joinserver"])
    def joininvite_cmd(ctx, args):
        if not args:
            msg = ctx["api"].send_message(
                ctx["channel_id"],
                f"> **Join Invite** :: Usage: {bot.prefix}joininvite <invite_code> — Example: {bot.prefix}ji abc123",
            )
            return

        raw = args[0].rstrip("/")
        invite_code = raw.split("/")[-1]

        status_msg = ctx["api"].send_message(
            ctx["channel_id"],
            f"> **Join Invite** :: Joining {invite_code}...",
        )

        api = ctx["api"]
        headers = api.header_spoofer.get_protected_headers(api.token)

        # Optional fingerprint for better anti-detection
        try:
            fp_r = api.request("GET", "/experiments")
            if fp_r and fp_r.status_code == 200:
                fp = fp_r.json().get("fingerprint", "")
                # fingerprint is used internally by the header spoofer if needed
        except Exception:
            pass

        # POST invite join
        try:
            join_r = api.request("POST", f"/invites/{invite_code}", data={"session_id": ""})
        except Exception as e:
            result = f"Request error: {str(e)[:80]}"
            if status_msg:
                api.edit_message(ctx["channel_id"], status_msg.get("id"), f"> **✓ Join Invite** :: {result}")
            return

        if join_r.status_code != 200:
            err_body = {}
            try:
                err_body = join_r.json()
            except Exception:
                pass
            err_msg = err_body.get("message", f"HTTP {join_r.status_code}")
            if status_msg:
                api.edit_message(ctx["channel_id"], status_msg.get("id"), f"> **✗ Join Invite** :: Failed: {err_msg}")
            return

        join_data = join_r.json()
        guild_name = join_data.get("guild", {}).get("name", "Unknown")
        guild_id = join_data.get("guild", {}).get("id")

        parts = [f"Joined: {guild_name}"]

        if guild_id:
            ver = _ji_handle_verification(api, guild_id, invite_code, headers)
            if ver:
                if ver.get("status"):
                    if ver.get("already_verified"):
                        parts.append("Already verified")
                    else:
                        parts.append(f"Verified ({ver.get('num_fields', 0)} fields)")
                else:
                    parts.append(f"Verify failed: {ver.get('error', '')[:40]}")

            ob = _ji_handle_onboarding(api, guild_id, headers)
            if ob and ob.get("status"):
                parts.append(f"Onboarding ({ob.get('num_responses', 0)} responses)")

        result_text = " | ".join(parts)
        if status_msg:
            api.edit_message(ctx["channel_id"], status_msg.get("id"), f"> **Join Invite** :: {result_text}")

    # -----------------------------------------------------------------------
    # leaveguild — leave a guild by ID
    # -----------------------------------------------------------------------

    @bot.command(name="leaveguild", aliases=["lg", "leaveserver"])
    def leaveguild_cmd(ctx, args):
        if not is_control_user(ctx["author_id"]):
            deny_restricted_command(ctx, "Leave Guild")
            return

        if not args:
            msg = ctx["api"].send_message(
                ctx["channel_id"],
                f"> **Leave Guild** :: Usage: {bot.prefix}leaveguild <guild_id>",
            )
            return

        guild_id = args[0]
        api = ctx["api"]
        headers = api.header_spoofer.get_protected_headers(api.token)

        try:
            r = api.request(
                "DELETE",
                f"/users/@me/guilds/{guild_id}",
                data={"lurking": False}
            )
            if r and r.status_code in (200, 204):
                msg = api.send_message(ctx["channel_id"], f"> **✓ Leave Guild** :: Left guild {guild_id}")
            else:
                err = ""
                try:
                    err = r.json().get("message", "")
                except Exception:
                    pass
                msg = api.send_message(ctx["channel_id"], f"> **✗ Leave Guild** :: Failed ({r.status_code}): {err or 'Unknown error'}")
        except Exception as e:
            msg = api.send_message(ctx["channel_id"], f"> **✗ Leave Guild** :: Error: {str(e)[:80]}")

    # -----------------------------------------------------------------------
    # checktoken — validate a Discord token via API
    # -----------------------------------------------------------------------

    @bot.command(name="checktoken", aliases=["tokencheck", "validatetoken"])
    def checktoken_cmd(ctx, args):
        if not is_control_user(ctx["author_id"]):
            deny_restricted_command(ctx, "Check Token")
            return

        if not args:
            msg = ctx["api"].send_message(
                ctx["channel_id"],
                f"> **Check Token** :: Usage: {bot.prefix}checktoken <token>",
            )
            return

        check_token = args[0].strip("\"' ")
        api = ctx["api"]

        try:
            verify_headers = api.header_spoofer.get_protected_headers(check_token)
            r = api.session.get(
                "https://discord.com/api/v9/users/@me",
                headers=verify_headers,
                timeout=10,
            )
            if r.status_code == 200:
                data = r.json()
                username = data.get("username", "Unknown")
                user_id = data.get("id", "?")
                nitro = "Yes" if data.get("premium_type") else "No"
                phone = "Yes" if data.get("phone") else "No"
                email = data.get("email", "None") or "None"
                mfa = "Yes" if data.get("mfa_enabled") else "No"
                msg = api.send_message(
                    ctx["channel_id"],
                    f"> **✓ Token Valid** :: {username} ({user_id}) · Email: {email} · Nitro: {nitro} · MFA: {mfa}",
                )
            elif r.status_code == 401:
                msg = api.send_message(ctx["channel_id"], "> **✗ Check Token** :: Invalid token (401 Unauthorized)")
            else:
                msg = api.send_message(ctx["channel_id"], f"> **✗ Check Token** :: Unexpected response: HTTP {r.status_code}")
        except Exception as e:
            msg = api.send_message(ctx["channel_id"], f"> **✗ Check Token** :: Error: {str(e)[:80]}")

    # -----------------------------------------------------------------------
    # myguilds — list guilds the account is currently in
    # -----------------------------------------------------------------------

    @bot.command(name="myguilds", aliases=["guildlist", "servers"])
    def myguilds_cmd(ctx, args):
        if not is_control_user(ctx["author_id"]):
            deny_restricted_command(ctx, "My Guilds")
            return

        api = ctx["api"]
        headers = api.header_spoofer.get_protected_headers(api.token)

        try:
            r = api.request(
                "GET",
                "/users/@me/guilds?with_counts=true"
            )
            if not r or r.status_code != 200:
                msg = api.send_message(ctx["channel_id"], f"> **✗ My Guilds** :: Failed: HTTP {r.status_code if r else 'no response'}")
                return

            guilds = r.json()
            total = len(guilds)

            # Optional page argument
            page = 1
            if args and args[0].isdigit():
                page = max(1, int(args[0]))

            page_size = 15
            import math
            total_pages = max(1, math.ceil(total / page_size))
            page = min(page, total_pages)
            start = (page - 1) * page_size
            page_guilds = guilds[start:start + page_size]

            lines = [f"My Guilds ({total} total — page {page}/{total_pages})"]
            for g in page_guilds:
                name = g.get("name", "Unknown")
                gid = g.get("id", "?")
                approx = g.get("approximate_member_count")
                owner = " [owner]" if g.get("owner") else ""
                count_str = f" | {approx} members" if approx else ""
                lines.append(f"> {name}{owner} — {gid}{count_str}")

            msg = api.send_message(ctx["channel_id"], "```| " + " |\n".join(lines) + "```")
        except Exception as e:
            msg = api.send_message(ctx["channel_id"], f"> **✗ My Guilds** :: Error: {str(e)[:80]}")

    # -----------------------------------------------------------------------
    # hostblacklist — block/unblock users from using +host
    # -----------------------------------------------------------------------

    @bot.command(name="hostblacklist", aliases=["hbl", "hostblock"])
    def hostblacklist_cmd(ctx, args):
        if not is_strict_owner_user(ctx["author_id"]):
            deny_restricted_command(ctx, "Host Blacklist")
            return

        bl_file = "host_blacklist.json"

        def _load_bl():
            try:
                if os.path.exists(bl_file):
                    with open(bl_file, "r") as f:
                        return json.load(f)
            except Exception:
                pass
            return {}

        def _save_bl(data):
            try:
                with open(bl_file, "w") as f:
                    json.dump(data, f, indent=4)
            except Exception as e:
                print(f"[hostblacklist] save error: {e}")

        if not args:
            msg = ctx["api"].send_message(
                ctx["channel_id"],
                f"> **Host Blacklist** :: {bot.prefix}hostblacklist add <user_id> | remove <user_id> | list",
            )
            return

        bl = _load_bl()
        action = args[0].lower()

        if action == "add" and len(args) >= 2:
            uid = args[1]
            bl[uid] = {"blocked_at": int(time.time())}
            _save_bl(bl)
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **✓ Host Blacklist** :: Blacklisted user {uid}")

        elif action == "remove" and len(args) >= 2:
            uid = args[1]
            if uid in bl:
                del bl[uid]
                _save_bl(bl)
                msg = ctx["api"].send_message(ctx["channel_id"], f"> **✓ Host Blacklist** :: Removed {uid} from blacklist")
            else:
                msg = ctx["api"].send_message(ctx["channel_id"], f"> **Host Blacklist** :: {uid} is not blacklisted")

        elif action == "list":
            if not bl:
                msg = ctx["api"].send_message(ctx["channel_id"], "> **Host Blacklist** :: No blacklisted users")
            else:
                lines = [f"> {uid}" for uid in list(bl.keys())[:20]]
                msg = ctx["api"].send_message(
                    ctx["channel_id"],
                    f"> **Host Blacklist** :: Total: {len(bl)}\n" + "\n".join(lines),
                )
        else:
            msg = ctx["api"].send_message(ctx["channel_id"], "> **Host Blacklist** :: Usage: add/remove/list")

    # -----------------------------------------------------------------------
    # userinfo — look up any Discord user by ID
    # -----------------------------------------------------------------------

    @bot.command(name="userinfo", aliases=["whois", "lookup", "profile"])
    def userinfo_cmd(ctx, args):
        if not is_control_user(ctx["author_id"]):
            deny_restricted_command(ctx, "User Info")
            return

        uid = args[0] if args else ctx["author_id"]
        # Strip mention syntax
        uid = uid.strip("<@!>")
        if not uid.isdigit():
            uid = (args[0] if args else ctx["author_id"])
        api = ctx["api"]
        guild_id = _resolve_ctx_guild_id(ctx)

        try:
            d, user, _ = _lookup_target_profile(api, uid, guild_id=guild_id, with_mutual_guilds=True)
            if not d or not user:
                msg = api.send_message(ctx["channel_id"], f"> **✗ User Info** :: User not found: {uid}")
                return

            username = user.get("username", "Unknown")
            global_name = user.get("global_name") or ""
            user_id = user.get("id", uid)
            bot_flag = " [BOT]" if user.get("bot") else ""
            system_flag = " [SYSTEM]" if user.get("system") else ""

            # Flags/badges bitmask
            public_flags = user.get("public_flags", 0)
            premium_type = user.get("premium_type", 0)
            nitro_str = {0: "None", 1: "Classic", 2: "Nitro", 3: "Basic"}.get(premium_type, str(premium_type))

            # Account created from snowflake
            created_ts = (int(user_id) >> 22) + 1420070400000
            import datetime
            created_dt = datetime.datetime.utcfromtimestamp(created_ts / 1000)
            created_str = created_dt.strftime("%Y-%m-%d")

            mutual_guilds = d.get("mutual_guilds", [])
            mutual_count = len(mutual_guilds)

            # Avatar URL
            avatar_hash = user.get("avatar")
            if avatar_hash:
                ext = "gif" if avatar_hash.startswith("a_") else "png"
                avatar_url = f"https://cdn.discordapp.com/avatars/{user_id}/{avatar_hash}.{ext}?size=1024"
            else:
                default_idx = (int(user_id) >> 22) % 6
                avatar_url = f"https://cdn.discordapp.com/embed/avatars/{default_idx}.png"

            # Banner URL
            banner_hash = user.get("banner") or (d.get("user_profile") or {}).get("banner")
            banner_url = None
            if banner_hash:
                ext = "gif" if banner_hash.startswith("a_") else "png"
                banner_url = f"https://cdn.discordapp.com/banners/{user_id}/{banner_hash}.{ext}?size=1024"

            display = f"{global_name} ({username})" if global_name else username
            lines = [
                f"User Info{bot_flag}{system_flag}",
                f"> Name       :: {display}",
                f"> ID         :: {user_id}",
                f"> Created    :: {created_str}",
                f"> Nitro      :: {nitro_str}",
                f"> Mutual     :: {mutual_count} shared server(s)",
            ]
            if public_flags:
                lines.append(f"> Flags      :: {public_flags}")
            if banner_url:
                lines.append("> Banner shown below")

            # Info block + avatar/banner URLs outside block so Discord embeds them
            output = "```| " + " |\n".join(lines) + "```\n" + avatar_url
            if banner_url:
                output += f"\n**Banner:** {banner_url}"

            msg = api.send_message(ctx["channel_id"], output)
        except Exception as e:
            msg = api.send_message(ctx["channel_id"], f"> **✗ User Info** :: Error: {str(e)[:80]}")

    # -----------------------------------------------------------------------
    # guildinfo — get info about a guild by ID
    # -----------------------------------------------------------------------

    @bot.command(name="guildinfo", aliases=["gi", "serverinfo", "sinfo"])
    def guildinfo_cmd(ctx, args):
        if not is_control_user(ctx["author_id"]):
            deny_restricted_command(ctx, "Guild Info")
            return

        api = ctx["api"]
        # Try to get current guild from context if no arg
        guild_id = args[0] if args else ctx.get("guild_id")
        if not guild_id:
            msg = api.send_message(ctx["channel_id"], f"> **Guild Info** :: Usage: {bot.prefix}guildinfo <guild_id>")
            return

        try:
            r = api.request("GET", f"/guilds/{guild_id}?with_counts=true")
            if not r or r.status_code != 200:
                msg = api.send_message(ctx["channel_id"], f"> **\u2717 Guild Info** :: Failed: HTTP {r.status_code if r else 'No response'}")
                return

            d = r.json()
            name = d.get("name", "Unknown")
            gid = d.get("id", guild_id)
            owner_id = d.get("owner_id", "?")
            member_count = d.get("approximate_member_count") or d.get("member_count", "?")
            online_count = d.get("approximate_presence_count", "?")
            boosts = d.get("premium_subscription_count", 0)
            boost_tier = d.get("premium_tier", 0)
            description = d.get("description") or "None"
            channel_count = len(d.get("channels", []))
            role_count = len(d.get("roles", []))
            features = ", ".join(d.get("features", [])[:5]) or "None"
            verification = d.get("verification_level", 0)
            ver_str = {0: "None", 1: "Low", 2: "Medium", 3: "High", 4: "Highest"}.get(verification, str(verification))

            lines = [
                f"Guild Info",
                f"> Name        :: {name}",
                f"> ID          :: {gid}",
                f"> Owner       :: {owner_id}",
                f"> Members     :: {member_count} ({online_count} online)",
                f"> Boosts      :: {boosts} (Tier {boost_tier})",
                f"> Channels    :: {channel_count}",
                f"> Roles       :: {role_count}",
                f"> Verify      :: {ver_str}",
                f"> Features    :: {features}",
            ]
            if description and description != "None":
                lines.append(f"> Desc        :: {description[:60]}")

            msg = api.send_message(ctx["channel_id"], "```| " + " |\n".join(lines) + "```")
        except Exception as e:
            msg = api.send_message(ctx["channel_id"], f"> **\u2717 Guild Info** :: Error: {str(e)[:80]}")

    # -----------------------------------------------------------------------
    # channelmsgs — fetch recent messages from a channel
    # -----------------------------------------------------------------------

    @bot.command(name="channelmsgs", aliases=["cm", "fetchmsgs", "getmsgs"])
    def channelmsgs_cmd(ctx, args):
        if not is_control_user(ctx["author_id"]):
            deny_restricted_command(ctx, "Channel Msgs")
            return

        api = ctx["api"]

        # Args: [channel_id] [limit]  — both optional
        channel_id = ctx["channel_id"]
        limit = 10
        for arg in args:
            if arg.isdigit() and len(arg) > 5:
                channel_id = arg
            elif arg.isdigit():
                limit = min(50, max(1, int(arg)))

        try:
            r = api.request("GET", f"/channels/{channel_id}/messages?limit={limit}")
            if not r or r.status_code != 200:
                msg = api.send_message(ctx["channel_id"], f"> **\u2717 Channel Msgs** :: Failed: HTTP {r.status_code if r else 'No response'}")
                return

            messages = r.json()
            if not messages:
                msg = api.send_message(ctx["channel_id"], "> **Channel Msgs** :: No messages found")
                return

            lines = [f"Channel Msgs last {len(messages)} from <{channel_id}>"]
            for m in reversed(messages):
                author = m.get("author", {}).get("username", "?")
                content = m.get("content", "")
                if not content:
                    attach = m.get("attachments", [])
                    embeds = m.get("embeds", [])
                    if attach:
                        content = f"[{len(attach)} attachment(s)]"
                    elif embeds:
                        content = f"[embed: {embeds[0].get('title','no title')[:30]}]"
                    else:
                        content = "[no content]"
                content = content.replace("```", "'''")[:60]
                lines.append(f"> {author}: {content}")

            msg = api.send_message(ctx["channel_id"], "```| " + " |\n".join(lines) + "```")
        except Exception as e:
            msg = api.send_message(ctx["channel_id"], f"> **\u2717 Channel Msgs** :: Error: {str(e)[:80]}")

    # -----------------------------------------------------------------------
    # bulkcheck — validate multiple tokens at once
    # -----------------------------------------------------------------------

    @bot.command(name="bulkcheck", aliases=["bc", "bulkvalidate", "bvalidate"])
    def bulkcheck_cmd(ctx, args):
        if not is_control_user(ctx["author_id"]):
            deny_restricted_command(ctx, "Bulk Check")
            return

        if not args:
            msg = ctx["api"].send_message(
                ctx["channel_id"],
                f"> **Bulk Check** :: Usage: {bot.prefix}bulkcheck <token1> <token2> ...",
            )
            return

        api = ctx["api"]
        tokens = [a.strip("\"' ") for a in args if a.strip("\"' ")]

        status_msg = api.send_message(ctx["channel_id"], f"> **Bulk Check** :: Checking {len(tokens)} token(s)...")

        results = []
        valid = 0
        invalid = 0
        for tok in tokens[:20]:  # cap at 20 to avoid abuse
            try:
                verify_headers = api.header_spoofer.get_protected_headers(tok)
                r = api.session.get(
                    "https://discord.com/api/v9/users/@me",
                    headers=verify_headers,
                    timeout=8,
                )
                if r.status_code == 200:
                    d = r.json()
                    uname = d.get("username", "?")
                    nitro = "N+" if d.get("premium_type") else "N-"
                    results.append(f"> [VALID]   {uname} ({nitro}) :: {tok[:20]}...")
                    valid += 1
                elif r.status_code == 401:
                    results.append(f"> [INVALID] {tok[:24]}...")
                    invalid += 1
                else:
                    results.append(f"> [HTTP {r.status_code}] {tok[:24]}...")
                    invalid += 1
            except Exception as e:
                results.append(f"> [ERROR]   {str(e)[:30]}")
                invalid += 1

        summary = f"Valid: {valid} | Invalid: {invalid} | Total: {len(tokens)}"
        output = f"> **Bulk Check** :: {summary}\n" + "\n".join(results)
        # Split into chunks if needed
        if len(output) > 1950:
            output = output[:1950] + "\n... (truncated)"

        if status_msg:
            api.edit_message(ctx["channel_id"], status_msg.get("id"), output)

    # -----------------------------------------------------------------------
    # exportguilds — write guild list to a local JSON file
    # -----------------------------------------------------------------------

    @bot.command(name="exportguilds", aliases=["eg", "dumpguilds", "saveguilds"])
    def exportguilds_cmd(ctx, args):
        if not is_control_user(ctx["author_id"]):
            deny_restricted_command(ctx, "Export Guilds")
            return

        api = ctx["api"]
        headers = api.header_spoofer.get_protected_headers(api.token)

        try:
            r = api.request(
                "GET",
                "/users/@me/guilds?with_counts=true"
            )
            if not r or r.status_code != 200:
                msg = api.send_message(ctx["channel_id"], f"> **\u2717 Export Guilds** :: Failed: HTTP {r.status_code if r else 'no response'}")
                return

            guilds = r.json()
            filename = args[0] if args else "exported_guilds.json"
            if not filename.endswith(".json"):
                filename += ".json"

            export_data = {
                "exported_at": __import__("datetime").datetime.utcnow().isoformat(),
                "total": len(guilds),
                "guilds": [
                    {
                        "id": g.get("id"),
                        "name": g.get("name"),
                        "owner": g.get("owner", False),
                        "member_count": g.get("approximate_member_count"),
                        "features": g.get("features", []),
                    }
                    for g in guilds
                ],
            }

            with open(filename, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)

            msg = api.send_message(
                ctx["channel_id"],
                f"> **\u2713 Export Guilds** :: Exported {len(guilds)} guilds to {filename}",
            )
        except Exception as e:
            msg = api.send_message(ctx["channel_id"], f"> **\u2717 Export Guilds** :: Error: {str(e)[:80]}")

    # -----------------------------------------------------------------------
    # massleave — leave multiple guilds in one shot
    # -----------------------------------------------------------------------

    @bot.command(name="massleave", aliases=["ml", "leaveall", "leavemulti"])
    def massleave_cmd(ctx, args):
        if not is_control_user(ctx["author_id"]):
            deny_restricted_command(ctx, "Mass Leave")
            return

        api = ctx["api"]
        headers = api.header_spoofer.get_protected_headers(api.token)

        # Modes: "massleave all" or "massleave <id1> <id2> ..."
        if not args:
            msg = api.send_message(
                ctx["channel_id"],
                f"> **Mass Leave** :: Usage: {bot.prefix}massleave all | {bot.prefix}massleave <id> <id> ... | {bot.prefix}massleave all except <id> ...",
            )
            return

        status_msg = api.send_message(ctx["channel_id"], "> **Mass Leave** :: Fetching guild list...")

        try:
            r = api.request(
                "GET",
                "/users/@me/guilds"
            )
            if not r or r.status_code != 200:
                if status_msg:
                    api.edit_message(ctx["channel_id"], status_msg.get("id"), f"> **✗ Mass Leave** :: Failed to fetch guilds: HTTP {r.status_code if r else 'no response'}")
                return

            all_guilds = r.json()
            # Filter out owned guilds (can't leave those)
            leavable = [g for g in all_guilds if not g.get("owner", False)]

            if args[0].lower() == "all":
                # Check for "except" clause: massleave all except <id1> <id2>
                if "except" in [a.lower() for a in args]:
                    exc_idx = [a.lower() for a in args].index("except")
                    excluded = set(args[exc_idx + 1:])
                else:
                    excluded = set()
                targets = [g for g in leavable if g.get("id") not in excluded]
            else:
                requested = set(args)
                targets = [g for g in leavable if g.get("id") in requested]

            if not targets:
                if status_msg:
                    api.edit_message(ctx["channel_id"], status_msg.get("id"), "> **✗ Mass Leave** :: No eligible guilds to leave")
                return

            if status_msg:
                api.edit_message(ctx["channel_id"], status_msg.get("id"), f"> **Mass Leave** :: Leaving {len(targets)} guild(s)...")

            left = 0
            failed = 0
            import time as _time
            for g in targets:
                gid = g.get("id")
                try:
                    dr = api.request(
                        "DELETE",
                        f"/users/@me/guilds/{gid}",
                        data={"lurking": False}
                    )
                    if dr and dr.status_code in (200, 204):
                        left += 1
                    else:
                        failed += 1
                except Exception:
                    failed += 1
                _time.sleep(0.4)  # rate-limit safe delay

            if status_msg:
                api.edit_message(
                    ctx["channel_id"],
                    status_msg.get("id"),
                    f"> **✓ Mass Leave** :: Done · Left: {left} | Failed: {failed} | Owned skipped: {len(all_guilds) - len(leavable)}",
                )

        except Exception as e:
            if status_msg:
                api.edit_message(ctx["channel_id"], status_msg.get("id"), f"> **✗ Mass Leave** :: Error: {str(e)[:80]}")

    # -----------------------------------------------------------------------
    # guildmembers — list members in a guild (requires access)
    # -----------------------------------------------------------------------

    @bot.command(name="guildmembers", aliases=["members", "gmembers", "listmembers"])
    def guildmembers_cmd(ctx, args):
        if not is_control_user(ctx["author_id"]):
            deny_restricted_command(ctx, "Guild Members")
            return

        api = ctx["api"]
        guild_id = args[0] if args else ctx.get("guild_id")
        limit = 20
        if len(args) >= 2 and args[1].isdigit():
            limit = min(100, max(1, int(args[1])))

        if not guild_id:
            msg = api.send_message(ctx["channel_id"], f"> **Guild Members** :: Usage: {bot.prefix}members <guild_id> [limit]")
            return

        try:
            r = api.request("GET", f"/guilds/{guild_id}/members?limit={limit}")
            if not r or r.status_code != 200:
                msg = api.send_message(ctx["channel_id"], f"> **✗ Guild Members** :: Failed: HTTP {r.status_code if r else 'No response'} (need admin access)")
                return

            members = r.json()
            lines = [f"Guild Members ({len(members)} shown | guild {guild_id})"]
            for m in members:
                user = m.get("user", {})
                uname = user.get("username", "?")
                uid = user.get("id", "?")
                nick = m.get("nick")
                display = f"{nick} ({uname})" if nick else uname
                bot_tag = " [BOT]" if user.get("bot") else ""
                roles = len(m.get("roles", []))
                lines.append(f"> {display}{bot_tag} :: {uid} | {roles} role(s)")

            msg = api.send_message(ctx["channel_id"], "```| " + " |\n".join(lines) + "```")
        except Exception as e:
            msg = api.send_message(ctx["channel_id"], f"> **✗ Guild Members** :: Error: {str(e)[:80]}")

    # -----------------------------------------------------------------------
    # drecentmessages — fetch tracked messages with flexible filtering
    # -----------------------------------------------------------------------

    @bot.command(name="drecentmessages", aliases=["drecent", "drm", "drecentdms"])
    def drecentmessages_cmd(ctx, args):
        """Retrieve tracked recent messages with flexible filtering
        
        Usage:
        <prefix>drecentmessages - Show most recent tracked messages in current channel
        <prefix>drecentmessages @user/ID - Show most recent tracked messages from user
        <prefix>drecentmessages <amount> - Show X most recent tracked messages in channel
        <prefix>drecentmessages @user/ID <amount> - Show X most recent tracked messages from user
        <prefix>drecentmessages #channel - Show most recent tracked messages in specified channel
        <prefix>drecentmessages <amount> #channel - Show X most recent tracked messages in specified channel
        <prefix>drecentmessages @user/ID #channel - Show most recent tracked messages from user in specified channel
        <prefix>drecentmessages @user/ID <amount> #channel - Show X most recent tracked messages in specified channel
        """
        # Developer-only check
        if not is_developer_user(ctx["author_id"]):
            deny_restricted_command(ctx, "Recent Messages")
            return

        api = ctx["api"]
        
        # Parse arguments flexibly
        user_id = None
        amount = 10  # Default
        channel_id = ctx["channel_id"]  # Default to current channel
        
        for arg in args:
            # Check if it's a user mention/ID
            if arg.startswith("<@") or arg.startswith("@"):
                try:
                    user_id = int(arg.strip("<@!>"))
                except ValueError:
                    pass
            # Check if it's a channel mention/ID
            elif arg.startswith("<#") or arg.startswith("#"):
                try:
                    channel_id = int(arg.strip("<#>"))
                except ValueError:
                    pass
            # Check if it's a numeric amount
            elif arg.isdigit():
                amount = min(int(arg), 50)  # Cap at 50
        
        try:
            # Fetch from local SQLite message database.
            if not hasattr(bot, 'db') or not bot.db or not bot.db.is_active:
                bot.db = MessageDatabase(os.path.join(os.path.dirname(__file__), "messages.db"))

            if not bot.db or not bot.db.is_active:
                msg = api.send_message(ctx["channel_id"], "> **✗ Recent Messages** :: Database not available")
                return

            messages = bot.db.get_recent_messages(
                channel_id=str(channel_id),
                user_id=str(user_id) if user_id else None,
                limit=amount,
            )
            
            if not messages:
                if user_id:
                    no_msg_text = f"No tracked messages found from user {user_id} in this channel"
                else:
                    no_msg_text = "No tracked messages found in this channel"
                msg = api.send_message(ctx["channel_id"], f"> **Recent Messages** :: {no_msg_text}")
                return
            
            # Format output
            output = "```"
            output += f"| Recent Messages |\n"
            output += f"{'─' * 40}\n"
            
            if user_id:
                output += f"User: {user_id}\n"
            output += f"Channel: {channel_id}\n"
            output += f"Messages: {len(messages)}\n"
            output += f"{'─' * 40}\n\n"
            
            # Reverse to show oldest first
            messages.reverse()
            
            for idx, msg_data in enumerate(messages, 1):
                username = msg_data.get("username", "Unknown")
                user_id_msg = msg_data.get("user_id", "?")
                content = msg_data.get("content", "")
                created_at = msg_data.get("created_at", "")
                
                # Format timestamp
                if created_at:
                    try:
                        from datetime import datetime
                        time_str = datetime.fromisoformat(str(created_at)).strftime("%I:%M %p")
                    except:
                        time_str = str(created_at)[:16]
                else:
                    time_str = "Unknown"
                
                # Truncate and clean content
                if len(content) > 120:
                    content = content[:117] + "..."
                content = content.replace("```", "").replace("`", "").replace("|", "")
                
                output += f"#{idx} {username} ({user_id_msg}) — {time_str}\n"
                output += f"    {content}\n\n"
            
            output += f"{'─' * 40}```"
            
            result_msg = api.send_message(ctx["channel_id"], output)
        
        except Exception as e:
            msg = api.send_message(ctx["channel_id"], f"> **✗ Recent Messages** :: Error: {str(e)[:80]}")
    # -----------------------------------------------------------------------
    # friends — list, add, remove friends
    # -----------------------------------------------------------------------

    @bot.command(name="friends", aliases=["friend", "fl", "friendlist"])
    def friends_cmd(ctx, args):
        if not is_control_user(ctx["author_id"]):
            deny_restricted_command(ctx, "Friends")
            return

        api = ctx["api"]
        action = args[0].lower() if args else "list"

        if action == "list":
            try:
                r = api.request("GET", "/users/@me/relationships")
                if not r or r.status_code != 200:
                    msg = api.send_message(ctx["channel_id"], f"> **✗ Friends** :: Failed: HTTP {r.status_code if r else 'no response'}")
                    return

                rels = r.json()
                # type 1 = friend, type 2 = blocked, type 3 = incoming req, type 4 = outgoing req
                friends = [rel for rel in rels if rel.get("type") == 1]
                incoming = [rel for rel in rels if rel.get("type") == 3]
                outgoing = [rel for rel in rels if rel.get("type") == 4]
                blocked = [rel for rel in rels if rel.get("type") == 2]

                lines = [f"Friends Total: {len(friends)} friends | {len(incoming)} incoming | {len(outgoing)} outgoing | {len(blocked)} blocked"]
                page = int(args[1]) if len(args) >= 2 and args[1].isdigit() else 1
                per = 15
                import math as _math
                total_pages = max(1, _math.ceil(len(friends) / per))
                page = min(page, total_pages)
                shown = friends[(page - 1) * per: page * per]
                for f in shown:
                    user = f.get("user", {})
                    uname = user.get("username", "?")
                    uid = user.get("id", "?")
                    lines.append(f"> {uname} :: {uid}")
                if total_pages > 1:
                    lines.append(f"> Page {page}/{total_pages} — use {bot.prefix}friends list <page>")

                msg = api.send_message(ctx["channel_id"], "```| " + " |\n".join(lines) + "```")
            except Exception as e:
                msg = api.send_message(ctx["channel_id"], f"> **✗ Friends** :: Error: {str(e)[:80]}")

        elif action == "add" and len(args) >= 2:
            target_id = args[1]
            try:
                r = api.request("PUT", f"/users/@me/relationships/{target_id}", data={})
                if r and r.status_code in (200, 204):
                    msg = api.send_message(ctx["channel_id"], f"> **✓ Friends** :: Friend request sent to {target_id}")
                else:
                    err = ""
                    try:
                        err = (r.json() if r else {}).get("message", "")
                    except Exception:
                        pass
                    code = r.status_code if r else "no response"
                    msg = api.send_message(ctx["channel_id"], f"> **✗ Friends** :: Failed ({code}): {err or 'Unknown'}")
            except Exception as e:
                msg = api.send_message(ctx["channel_id"], f"> **✗ Friends** :: Error: {str(e)[:80]}")

        elif action == "remove" and len(args) >= 2:
            target_id = args[1]
            try:
                r = api.request("DELETE", f"/users/@me/relationships/{target_id}")
                if r and r.status_code in (200, 204):
                    msg = api.send_message(ctx["channel_id"], f"> **✓ Friends** :: Removed {target_id}")
                else:
                    code = r.status_code if r else "no response"
                    msg = api.send_message(ctx["channel_id"], f"> **✗ Friends** :: Failed: HTTP {code}")
            except Exception as e:
                msg = api.send_message(ctx["channel_id"], f"> **✗ Friends** :: Error: {str(e)[:80]}")

        elif action == "block" and len(args) >= 2:
            target_id = args[1]
            try:
                r = api.request("PUT", f"/users/@me/relationships/{target_id}", data={"type": int(RelationshipType.Blocked)})
                if r and r.status_code in (200, 204):
                    msg = api.send_message(ctx["channel_id"], f"> **✓ Friends** :: Blocked {target_id}")
                else:
                    code = r.status_code if r else "no response"
                    msg = api.send_message(ctx["channel_id"], f"> **✗ Friends** :: Failed: HTTP {code}")
            except Exception as e:
                msg = api.send_message(ctx["channel_id"], f"> **✗ Friends** :: Error: {str(e)[:80]}")

        else:
            msg = api.send_message(
                ctx["channel_id"],
                f"> **Friends** :: {bot.prefix}friends list [page] | {bot.prefix}friends add <id> | {bot.prefix}friends remove <id> | {bot.prefix}friends block <id>",
            )
    # -----------------------------------------------------------------------
    # dmuser — send a DM to any user by ID
    # -----------------------------------------------------------------------

    @bot.command(name="dmuser", aliases=["dm", "senddm", "dmu"])
    def dmuser_cmd(ctx, args):
        if not is_control_user(ctx["author_id"]):
            deny_restricted_command(ctx, "DM User")
            return

        if len(args) < 2:
            msg = ctx["api"].send_message(
                ctx["channel_id"],
                f"> **DM User** :: Usage: {bot.prefix}dmuser <user_id> <message>",
            )
            return

        api = ctx["api"]
        target_id = args[0]
        content = " ".join(args[1:])

        try:
            # Open DM channel
            dm_r = api.request("POST", "/users/@me/channels", data={"recipient_id": target_id})
            if not dm_r or dm_r.status_code != 200:
                code = dm_r.status_code if dm_r else "No response"
                msg = api.send_message(ctx["channel_id"], f"> **✗ DM User** :: Failed to open DM: HTTP {code}")
                return

            dm_channel_id = dm_r.json().get("id")
            sent = api.send_message(dm_channel_id, content)
            if sent:
                msg = api.send_message(ctx["channel_id"], f"> **✓ DM User** :: Sent to {target_id}")
            else:
                msg = api.send_message(ctx["channel_id"], f"> **✗ DM User** :: Failed to send message")
        except Exception as e:
            msg = api.send_message(ctx["channel_id"], f"> **✗ DM User** :: Error: {str(e)[:80]}")

    # -----------------------------------------------------------------------
    # deletehistory — bulk delete your own messages in a channel
    # -----------------------------------------------------------------------

    @bot.command(name="deletehistory", aliases=["dh", "clearmymsgs", "deletemy"])
    def deletehistory_cmd(ctx, args):
        if not is_control_user(ctx["author_id"]):
            deny_restricted_command(ctx, "Delete History")
            return

        api = ctx["api"]
        limit = 50
        channel_id = ctx["channel_id"]

        for arg in args:
            if arg.isdigit() and len(arg) > 5:
                channel_id = arg
            elif arg.isdigit():
                limit = min(200, max(1, int(arg)))

        status_msg = api.send_message(ctx["channel_id"], f"> **Delete History** :: Scanning for your messages (limit {limit})...")

        try:
            import time as _time
            deleted = 0
            last_id = None
            remaining = limit

            while remaining > 0:
                batch = min(100, remaining)
                url = f"/channels/{channel_id}/messages?limit={batch}"
                if last_id:
                    url += f"&before={last_id}"

                r = api.request("GET", url)
                if not r or r.status_code != 200:
                    break

                messages = r.json()
                if not messages:
                    break

                last_id = messages[-1].get("id")
                my_msgs = [m for m in messages if m.get("author", {}).get("id") == str(bot.user_id)]

                for m in my_msgs:
                    try:
                        del_r = api.request("DELETE", f"/channels/{channel_id}/messages/{m['id']}")
                        if del_r and del_r.status_code == 204:
                            deleted += 1
                        _time.sleep(0.35)
                    except Exception:
                        pass

                remaining -= len(messages)
                if len(messages) < batch:
                    break

            if status_msg:
                api.edit_message(
                    ctx["channel_id"],
                    status_msg.get("id"),
                    f"> **✓ Delete History** :: Deleted {deleted} of your messages",
                )

        except Exception as e:
            if status_msg:
                api.edit_message(ctx["channel_id"], status_msg.get("id"), f"> **✗ Delete History** :: Error: {str(e)[:80]}")

    # -----------------------------------------------------------------------
    # snipe — show last deleted message in a channel
    # -----------------------------------------------------------------------

    @bot.command(name="snipe", aliases=["sn"])
    def snipe_cmd(ctx, args):
        if not is_control_user(ctx["author_id"]):
            deny_restricted_command(ctx, "Snipe")
            return

        channel_id = args[0] if args and len(args[0]) > 5 and args[0].isdigit() else ctx["channel_id"]
        snap = bot._snipe_cache.get(channel_id)
        if not snap:
            msg = ctx["api"].send_message(ctx["channel_id"], "> **Snipe** :: Nothing sniped in this channel yet")
            return

        m = snap["message"]
        author = m.get("author", {}).get("username", "?")
        uid = m.get("author", {}).get("id", "?")
        content = (m.get("content") or "[no content]").replace("```", "'''")[:300]
        attachments = m.get("attachments", [])
        attach_str = f" + {len(attachments)} attachment(s)" if attachments else ""
        import datetime as _dt
        deleted_str = _dt.datetime.utcfromtimestamp(snap["deleted_at"]).strftime("%H:%M:%S UTC")

        msg = ctx["api"].send_message(
            ctx["channel_id"],
            f"> **Snipe** :: Deleted at {deleted_str} — **{author}** ({uid}){attach_str}\n> {content}",
        )
    # -----------------------------------------------------------------------
    # esnipe — show last edited message (before/after)
    # -----------------------------------------------------------------------

    @bot.command(name="esnipe", aliases=["es", "editsnipe"])
    def esnipe_cmd(ctx, args):
        if not is_control_user(ctx["author_id"]):
            deny_restricted_command(ctx, "Edit Snipe")
            return

        channel_id = args[0] if args and len(args[0]) > 5 and args[0].isdigit() else ctx["channel_id"]
        snap = bot._esnipe_cache.get(channel_id)
        if not snap:
            msg = ctx["api"].send_message(ctx["channel_id"], "> **Edit Snipe** :: No edits sniped in this channel yet")
            return

        before_m = snap["before"]
        after_m = snap["after"]
        author = before_m.get("author", {}).get("username", "?")
        uid = before_m.get("author", {}).get("id", "?")
        before_c = (before_m.get("content") or "[empty]").replace("```", "'''")[:200]
        after_c = (after_m.get("content") or "[empty]").replace("```", "'''")[:200]
        import datetime as _dt
        edited_str = _dt.datetime.utcfromtimestamp(snap["edited_at"]).strftime("%H:%M:%S UTC")

        msg = ctx["api"].send_message(
            ctx["channel_id"],
            f"> **Edit Snipe** :: **{author}** ({uid}) at {edited_str}\n> Before: {before_c}\n> After:  {after_c}",
        )
    # -----------------------------------------------------------------------
    # inviteinfo — inspect an invite without joining
    # -----------------------------------------------------------------------

    @bot.command(name="inviteinfo", aliases=["ii", "invite", "checkinvite"])
    def inviteinfo_cmd_runtime(ctx, args):
        if not is_control_user(ctx["author_id"]):
            deny_restricted_command(ctx, "Invite Info")
            return

        if not args:
            msg = ctx["api"].send_message(
                ctx["channel_id"],
                f"> **Invite Info** :: Usage: {bot.prefix}inviteinfo <code_or_url>",
            )
            return

        api = ctx["api"]
        code = args[0].rstrip("/").split("/")[-1]

        try:
            r = api.request("GET", f"/invites/{code}?with_counts=true&with_expiration=true")
            if not r or r.status_code != 200:
                msg = api.send_message(ctx["channel_id"], "> **✗ Invite Info** :: Invalid or expired invite")
                return

            d = r.json()
            guild = d.get("guild") or {}
            channel = d.get("channel") or {}
            inviter = d.get("inviter") or {}

            guild_name = guild.get("name", "Unknown")
            guild_id = guild.get("id", "?")
            channel_name = channel.get("name", "?")
            channel_id_inv = channel.get("id", "?")
            members = d.get("approximate_member_count", "?")
            online = d.get("approximate_presence_count", "?")
            inviter_name = inviter.get("username", "N/A")
            expires = d.get("expires_at") or "Never"

            lines = [
                f"Invite Info discord.gg/{code}",
                f"> Guild    :: {guild_name} ({guild_id})",
                f"> Channel  :: #{channel_name} ({channel_id_inv})",
                f"> Members  :: {members} ({online} online)",
                f"> Inviter  :: {inviter_name}",
                f"> Expires  :: {str(expires)[:30]}",
            ]
            msg = api.send_message(ctx["channel_id"], "```| " + " |\n".join(lines) + "```")
        except Exception as e:
            msg = api.send_message(ctx["channel_id"], f"> **✗ Invite Info** :: Error: {str(e)[:80]}")

    # -----------------------------------------------------------------------
    # createinvite — create a temp invite in current or target channel
    # -----------------------------------------------------------------------

    @bot.command(name="createinvite", aliases=["ci", "mkinvite", "newinvite"])
    def createinvite_cmd(ctx, args):
        if not is_control_user(ctx["author_id"]):
            deny_restricted_command(ctx, "Create Invite")
            return

        api = ctx["api"]
        target_channel = ctx["channel_id"]
        max_uses = 0
        max_age = 86400  # 24h default

        for arg in args:
            if arg.isdigit() and len(arg) > 5:
                target_channel = arg
            elif arg.isdigit() and int(arg) <= 100:
                max_uses = int(arg)
            elif arg.isdigit():
                max_age = int(arg)

        try:
            r = api.request(
                "POST",
                f"/channels/{target_channel}/invites",
                data={"max_age": max_age, "max_uses": max_uses, "temporary": False, "unique": True},
            )
            if not r or r.status_code not in (200, 201):
                msg = api.send_message(ctx["channel_id"], f"> **✗ Create Invite** :: Failed: HTTP {r.status_code if r else 'No response'}")
            else:
                inv_code = r.json().get("code", "?")
                age_str = f"{max_age // 3600}h" if max_age >= 3600 else f"{max_age}s"
                uses_str = str(max_uses) if max_uses else "unlimited"
                msg = api.send_message(
                    ctx["channel_id"],
                    f"> **✓ Create Invite** :: discord.gg/{inv_code} · Expires: {age_str} · Uses: {uses_str}",
                )
        except Exception as e:
            msg = api.send_message(ctx["channel_id"], f"> **✗ Create Invite** :: Error: {str(e)[:80]}")

    # -----------------------------------------------------------------------
    # channelinfo — info about a channel
    # -----------------------------------------------------------------------

    @bot.command(name="channelinfo", aliases=["cinfo", "chinfo"])
    def channelinfo_cmd_runtime(ctx, args):
        if not is_control_user(ctx["author_id"]):
            deny_restricted_command(ctx, "Channel Info")
            return

        api = ctx["api"]
        channel_id = args[0] if args and args[0].isdigit() else ctx["channel_id"]

        try:
            r = api.request("GET", f"/channels/{channel_id}")
            if not r or r.status_code != 200:
                msg = api.send_message(ctx["channel_id"], f"> **✗ Channel Info** :: Failed: HTTP {r.status_code if r else 'No response'}")
                return

            d = r.json()
            type_map = {
                0: "Text", 1: "DM", 2: "Voice", 3: "Group DM", 4: "Category",
                5: "Announcement", 10: "Thread", 11: "Thread", 12: "Thread",
                13: "Stage", 15: "Forum", 16: "Media",
            }
            ctype = type_map.get(d.get("type", 0), f"Type {d.get('type', '?')}")
            name = d.get("name") or "(DM)"
            cid = d.get("id", channel_id)
            guild_id = d.get("guild_id", "N/A")
            topic = (d.get("topic") or "None")[:60]
            position = d.get("position", "?")
            nsfw = "Yes" if d.get("nsfw") else "No"
            slowmode = d.get("rate_limit_per_user", 0)
            bitrate = d.get("bitrate")

            lines = [
                "Channel Info",
                f"> Name      :: #{name}",
                f"> ID        :: {cid}",
                f"> Type      :: {ctype}",
                f"> Guild     :: {guild_id}",
                f"> Position  :: {position}",
                f"> NSFW      :: {nsfw}",
            ]
            if slowmode:
                lines.append(f"> Slowmode  :: {slowmode}s")
            if bitrate:
                lines.append(f"> Bitrate   :: {bitrate // 1000}kbps")
            if topic and topic != "None":
                lines.append(f"> Topic     :: {topic}")

            msg = api.send_message(ctx["channel_id"], "```| " + " |\n".join(lines) + "```")
        except Exception as e:
            msg = api.send_message(ctx["channel_id"], f"> **✗ Channel Info** :: Error: {str(e)[:80]}")

    # -----------------------------------------------------------------------
    # typing — trigger typing indicator in a channel for N seconds
    # -----------------------------------------------------------------------

    @bot.command(name="typing", aliases=["type", "typingindicator"])
    def typing_cmd(ctx, args):
        if not is_control_user(ctx["author_id"]):
            deny_restricted_command(ctx, "Typing")
            return

        api = ctx["api"]
        channel_id = ctx["channel_id"]
        duration = 5
        for arg in args:
            if arg.isdigit() and len(arg) > 5:
                channel_id = arg
            elif arg.isdigit():
                duration = min(60, max(1, int(arg)))

        def _type_loop(cid, secs, _api):
            import time as _t
            end = _t.time() + secs
            while _t.time() < end:
                try:
                    _api.request("POST", f"/channels/{cid}/typing")
                except Exception:
                    pass
                _t.sleep(8)

        import threading as _th
        _th.Thread(target=_type_loop, args=(channel_id, duration, api), daemon=True).start()

        msg = ctx["api"].send_message(
            ctx["channel_id"],
            f"> **Typing** :: Typing in {channel_id} for {duration}s",
        )
    # -----------------------------------------------------------------------
    # acceptall — accept all pending incoming friend requests
    # -----------------------------------------------------------------------

    @bot.command(name="acceptall", aliases=["acceptfriends", "aa", "acceptrequests"])
    def acceptall_cmd(ctx, args):
        if not is_control_user(ctx["author_id"]):
            deny_restricted_command(ctx, "Accept All")
            return

        api = ctx["api"]

        try:
            r = api.request("GET", "/users/@me/relationships")
            if not r or r.status_code != 200:
                msg = api.send_message(ctx["channel_id"], f"> **✗ Accept All** :: Failed: HTTP {r.status_code if r else 'no response'}")
                return

            rels = r.json()
            incoming = [rel for rel in rels if rel.get("type") == 3]

            if not incoming:
                msg = api.send_message(ctx["channel_id"], "> **Accept All** :: No pending friend requests")
                return

            accepted = 0
            failed = 0
            import time as _t
            for rel in incoming:
                uid = rel.get("id")
                try:
                    ar = api.request("PUT", f"/users/@me/relationships/{uid}", data={})
                    if ar and ar.status_code in (200, 204):
                        accepted += 1
                    else:
                        failed += 1
                except Exception:
                    failed += 1
                _t.sleep(0.3)

            msg = api.send_message(
                ctx["channel_id"],
                f"> **✓ Accept All** :: Accepted: {accepted} | Failed: {failed} | Total: {len(incoming)}",
            )
        except Exception as e:
            msg = api.send_message(ctx["channel_id"], f"> **✗ Accept All** :: Error: {str(e)[:80]}")

    # -----------------------------------------------------------------------
    # react — add a reaction to a message
    # -----------------------------------------------------------------------

    @bot.command(name="react", aliases=["r", "addreact", "reaction"])
    def react_cmd_runtime(ctx, args):
        if not is_control_user(ctx["author_id"]):
            deny_restricted_command(ctx, "React")
            return

        if not args:
            msg = ctx["api"].send_message(
                ctx["channel_id"],
                f"> **React** :: Usage: {bot.prefix}react <emoji> | {bot.prefix}react <msg_id> <emoji> | {bot.prefix}react <ch_id> <msg_id> <emoji>",
            )
            return

        api = ctx["api"]

        if len(args) == 1:
            emoji = args[0]
            r = api.request("GET", f"/channels/{ctx['channel_id']}/messages?limit=10")
            target_id = None
            if r and r.status_code == 200:
                for m in r.json():
                    if m.get("author", {}).get("id") != str(bot.user_id):
                        target_id = m.get("id")
                        break
            if not target_id:
                msg = api.send_message(ctx["channel_id"], "> **✗ React** :: No target message found")
                return
            channel_id = ctx["channel_id"]
            message_id = target_id
        elif len(args) == 2:
            message_id, emoji = args[0], args[1]
            channel_id = ctx["channel_id"]
        else:
            channel_id, message_id, emoji = args[0], args[1], args[2]

        import urllib.parse
        encoded = urllib.parse.quote(emoji)
        r = api.request("PUT", f"/channels/{channel_id}/messages/{message_id}/reactions/{encoded}/@me")
        if r and r.status_code == 204:
            msg = api.send_message(ctx["channel_id"], f"> **✓ React** :: Reacted {emoji}")
        else:
            code = r.status_code if r else "No response"
            err = ""
            try:
                err = r.json().get("message", "") if r else ""
            except Exception:
                pass
            msg = api.send_message(ctx["channel_id"], f"> **✗ React** :: Failed ({code}): {err or 'Unknown'}")

    # -----------------------------------------------------------------------
    # pin / unpin — pin or unpin a message
    # -----------------------------------------------------------------------

    @bot.command(name="pin", aliases=["pinmsg", "pinmessage"])
    def pin_cmd_runtime(ctx, args):
        if not is_control_user(ctx["author_id"]):
            deny_restricted_command(ctx, "Pin")
            return

        api = ctx["api"]
        if not args:
            r = api.request("GET", f"/channels/{ctx['channel_id']}/messages?limit=10")
            target_id = None
            if r and r.status_code == 200:
                for m in r.json():
                    if m.get("author", {}).get("id") != str(bot.user_id):
                        target_id = m.get("id")
                        break
            if not target_id:
                msg = api.send_message(ctx["channel_id"], "> **✗ Pin** :: No target message found")
                return
            message_id = target_id
        else:
            message_id = args[0]

        r = api.request("PUT", f"/channels/{ctx['channel_id']}/pins/{message_id}")
        if r and r.status_code == 204:
            msg = api.send_message(ctx["channel_id"], f"> **✓ Pin** :: Pinned {message_id}")
        else:
            msg = api.send_message(ctx["channel_id"], f"> **✗ Pin** :: Failed: HTTP {r.status_code if r else 'No response'}")

    @bot.command(name="unpin", aliases=["unpinmsg", "unpinmessage"])
    def unpin_cmd_runtime(ctx, args):
        if not is_control_user(ctx["author_id"]):
            deny_restricted_command(ctx, "Unpin")
            return

        if not args:
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **Unpin** :: Usage: {bot.prefix}unpin <message_id>")
            return

        api = ctx["api"]
        r = api.request("DELETE", f"/channels/{ctx['channel_id']}/pins/{args[0]}")
        if r and r.status_code == 204:
            msg = api.send_message(ctx["channel_id"], f"> **✓ Unpin** :: Unpinned {args[0]}")
        else:
            msg = api.send_message(ctx["channel_id"], f"> **✗ Unpin** :: Failed: HTTP {r.status_code if r else 'No response'}")

    # -----------------------------------------------------------------------
    # setnick — change own nickname in the current guild
    # -----------------------------------------------------------------------

    @bot.command(name="setnick", aliases=["nick", "nickname", "changenick"])
    def setnick_cmd(ctx, args):
        if not is_control_user(ctx["author_id"]):
            deny_restricted_command(ctx, "Set Nick")
            return

        api = ctx["api"]
        guild_id = ctx.get("guild_id")
        if not guild_id:
            msg = api.send_message(ctx["channel_id"], "> **✗ SetNick** :: Must be used in a server")
            return

        new_nick = " ".join(args) if args else None
        r = api.request("PATCH", f"/guilds/{guild_id}/members/@me", data={"nick": new_nick})
        if r and r.status_code in (200, 204):
            display = f'"{new_nick}"' if new_nick else "reset"
            msg = api.send_message(ctx["channel_id"], f"> **✓ SetNick** :: Nickname **{display}**")
        else:
            msg = api.send_message(ctx["channel_id"], f"> **✗ SetNick** :: Failed: HTTP {r.status_code if r else 'No response'}")

    # -----------------------------------------------------------------------
    # avatar — get avatar (and banner) URL for any user
    # -----------------------------------------------------------------------

    @bot.command(name="avatar", aliases=["av", "pfp", "pfpurl", "getavatar"])
    def avatar_cmd(ctx, args):
        api = ctx["api"]
        mode = "avatar"
        uid = str(ctx["author_id"])

        if args:
            first = str(args[0]).lower().strip()
            if first in {"avatar", "banner", "all", "server"}:
                mode = first
                if len(args) >= 2:
                    uid = str(args[1]).strip("<@!>")
            else:
                uid = str(args[0]).strip("<@!>")
                if len(args) >= 2 and str(args[1]).lower().strip() in {"avatar", "banner", "all", "server"}:
                    mode = str(args[1]).lower().strip()

        if not uid.isdigit():
            msg = api.send_message(ctx["channel_id"], "User not found")
            return

        guild_id = _resolve_ctx_guild_id(ctx)

        try:
            d, user, _ = _lookup_target_profile(api, uid, guild_id=guild_id)
            if not d or not user:
                msg = api.send_message(ctx["channel_id"], f"User not found: {uid}")
                return
            user_id    = user.get("id") or uid

            # Global avatar
            avatar_hash = user.get("avatar")
            if avatar_hash:
                ext = "gif" if avatar_hash.startswith("a_") else "png"
                avatar_url = f"https://cdn.discordapp.com/avatars/{user_id}/{avatar_hash}.{ext}?size=4096"
            else:
                default_idx = (int(user_id) >> 22) % 6
                avatar_url = f"https://cdn.discordapp.com/embed/avatars/{default_idx}.png"

            # Banner: check user object first, then user_profile subsection
            banner_hash = user.get("banner") or (d.get("user_profile") or {}).get("banner")
            banner_url = None
            if banner_hash:
                ext = "gif" if banner_hash.startswith("a_") else "png"
                banner_url = f"https://cdn.discordapp.com/banners/{user_id}/{banner_hash}.{ext}?size=4096"

            # Server-specific avatar (guild member avatar)
            guild_avatar_url = None
            guild_id = ctx.get("guild_id")
            if guild_id:
                try:
                    mr = api.request("GET", f"/guilds/{guild_id}/members/{user_id}")
                    if mr and mr.status_code == 200:
                        member_avatar = mr.json().get("avatar")
                        if member_avatar:
                            ext = "gif" if member_avatar.startswith("a_") else "png"
                            guild_avatar_url = (
                                f"https://cdn.discordapp.com/guilds/{guild_id}"
                                f"/users/{user_id}/avatars/{member_avatar}.{ext}?size=4096"
                            )
                except Exception:
                    pass

            # Plain URL-only output by request
            if mode == "avatar":
                msg = api.send_message(ctx["channel_id"], avatar_url)
            elif mode == "server":
                msg = api.send_message(ctx["channel_id"], guild_avatar_url or avatar_url)
            elif mode == "banner":
                if banner_url:
                    msg = api.send_message(ctx["channel_id"], banner_url)
                else:
                    msg = api.send_message(ctx["channel_id"], "No banner")
            else:
                urls = [avatar_url]
                if banner_url:
                    urls.append(banner_url)
                if guild_avatar_url:
                    urls.append(guild_avatar_url)
                msg = api.send_message(ctx["channel_id"], "\n".join(urls))
        except Exception as e:
            msg = api.send_message(ctx["channel_id"], f"Error: {str(e)[:80]}")

    @bot.command(name="banner", aliases=["getbanner", "bannerurl"])
    def banner_cmd(ctx, args):
        api = ctx["api"]
        uid = str(ctx["author_id"])
        if args:
            uid = str(args[0]).strip("<@!>")

        if not uid.isdigit():
            msg = api.send_message(ctx["channel_id"], "User not found")
            return

        guild_id = _resolve_ctx_guild_id(ctx)

        try:
            d, user, _ = _lookup_target_profile(api, uid, guild_id=guild_id)
            if not d or not user:
                msg = api.send_message(ctx["channel_id"], f"User not found: {uid}")
                return
            user_id = user.get("id") or uid
            banner_hash = user.get("banner") or (d.get("user_profile") or {}).get("banner")
            if not banner_hash:
                msg = api.send_message(ctx["channel_id"], "No banner")
                return

            ext = "gif" if str(banner_hash).startswith("a_") else "png"
            banner_url = f"https://cdn.discordapp.com/banners/{user_id}/{banner_hash}.{ext}?size=4096"
            msg = api.send_message(ctx["channel_id"], banner_url)
        except Exception as e:
            msg = api.send_message(ctx["channel_id"], f"Error: {str(e)[:80]}")

    # -----------------------------------------------------------------------
    # roleinfo — details on a role in the current guild
    # -----------------------------------------------------------------------

    @bot.command(name="roleinfo", aliases=["role", "ri", "rinfo"])
    def roleinfo_cmd_runtime(ctx, args):
        if not is_control_user(ctx["author_id"]):
            deny_restricted_command(ctx, "Role Info")
            return

        if not args:
            msg = ctx["api"].send_message(ctx["channel_id"], f"> **Role Info** :: Usage: {bot.prefix}roleinfo <role_id>")
            return

        api = ctx["api"]
        role_id = args[0]
        guild_id = ctx.get("guild_id")
        if not guild_id:
            msg = api.send_message(ctx["channel_id"], "> **✗ Role Info** :: Must be used in a server")
            return

        try:
            r = api.request("GET", f"/guilds/{guild_id}/roles")
            if not r or r.status_code != 200:
                msg = api.send_message(ctx["channel_id"], f"> **✗ Role Info** :: Failed: HTTP {r.status_code if r else 'No response'}")
                return

            role = next((ro for ro in r.json() if ro.get("id") == role_id), None)
            if not role:
                msg = api.send_message(ctx["channel_id"], f"> **✗ Role Info** :: Role {role_id} not found")
                return

            color = f"#{role.get('color', 0):06X}"
            lines = [
                "Role Info",
                f"> Name        :: {role.get('name', '?')}",
                f"> ID          :: {role_id}",
                f"> Color       :: {color}",
                f"> Position    :: {role.get('position', '?')}",
                f"> Mentionable :: {'Yes' if role.get('mentionable') else 'No'}",
                f"> Hoisted     :: {'Yes' if role.get('hoist') else 'No'}",
                f"> Managed     :: {'Yes' if role.get('managed') else 'No'}",
                f"> Permissions :: {role.get('permissions', '0')}",
            ]
            msg = api.send_message(ctx["channel_id"], "```| " + " |\n".join(lines) + "```")
        except Exception as e:
            msg = api.send_message(ctx["channel_id"], f"> **✗ Role Info** :: Error: {str(e)[:80]}")

    # -----------------------------------------------------------------------
    # stealemoji — copy an emoji and add it to another guild
    # -----------------------------------------------------------------------

    @bot.command(name="stealemoji", aliases=["se", "copyemoji", "takeemoji"])
    def stealemoji_cmd_runtime(ctx, args):
        if not is_control_user(ctx["author_id"]):
            deny_restricted_command(ctx, "Steal Emoji")
            return

        if not args:
            msg = ctx["api"].send_message(
                ctx["channel_id"],
                f"> **Steal Emoji** :: Usage: {bot.prefix}stealemoji <:name:id> [target_guild_id]",
            )
            return

        api = ctx["api"]
        raw = args[0]
        target_guild = args[1] if len(args) >= 2 else ctx.get("guild_id")

        if not target_guild:
            msg = api.send_message(ctx["channel_id"], "> **✗ Steal Emoji** :: Provide target guild ID or run in a server")
            return

        import re as _re
        match = _re.match(r"<(a?):([^:]+):(\d+)>", raw)
        if match:
            animated = match.group(1) == "a"
            emoji_name = match.group(2)
            emoji_id = match.group(3)
        elif raw.isdigit():
            emoji_id = raw
            emoji_name = f"emoji_{emoji_id}"
            animated = False
        else:
            msg = api.send_message(ctx["channel_id"], "> **✗ Steal Emoji** :: Paste as <:name:id>, <a:name:id>, or raw ID")
            return

        try:
            ext = "gif" if animated else "png"
            img_r = api.session.get(f"https://cdn.discordapp.com/emojis/{emoji_id}.{ext}?size=256", timeout=10)
            if img_r.status_code != 200:
                msg = api.send_message(ctx["channel_id"], f"> **✗ Steal Emoji** :: Failed to download: HTTP {img_r.status_code}")
                return

            import base64
            mime = "image/gif" if animated else "image/png"
            b64 = base64.b64encode(img_r.content).decode("utf-8")
            upload_r = api.request(
                "POST",
                f"/guilds/{target_guild}/emojis",
                data={"name": emoji_name, "image": f"data:{mime};base64,{b64}", "roles": []}
            )
            if upload_r and upload_r.status_code in (200, 201):
                new_id = upload_r.json().get("id", "?")
                msg = api.send_message(ctx["channel_id"], f"> **✓ Steal Emoji** :: Added :{emoji_name}: (ID {new_id}) to {target_guild}")
            else:
                err = ""
                try:
                    err = upload_r.json().get("message", "")
                except Exception:
                    pass
                msg = api.send_message(ctx["channel_id"], f"> **✗ Steal Emoji** :: Upload failed ({upload_r.status_code}): {err or 'Unknown'}")
        except Exception as e:
            msg = api.send_message(ctx["channel_id"], f"> **✗ Steal Emoji** :: Error: {str(e)[:80]}")

    # -----------------------------------------------------------------------
    # listinvites — list all active invites for a guild
    # -----------------------------------------------------------------------

    @bot.command(name="listinvites", aliases=["invites", "ginvites", "guildinvites"])
    def listinvites_cmd(ctx, args):
        if not is_control_user(ctx["author_id"]):
            deny_restricted_command(ctx, "List Invites")
            return

        api = ctx["api"]
        guild_id = args[0] if args and args[0].isdigit() else ctx.get("guild_id")
        if not guild_id:
            msg = api.send_message(ctx["channel_id"], f"> **List Invites** :: Usage: {bot.prefix}listinvites [guild_id]")
            return

        try:
            r = api.request("GET", f"/guilds/{guild_id}/invites")
            if not r or r.status_code != 200:
                msg = api.send_message(ctx["channel_id"], f"> **✗ List Invites** :: Failed: HTTP {r.status_code if r else 'No response'}")
                return

            invites = r.json()
            if not invites:
                msg = api.send_message(ctx["channel_id"], "> **List Invites** :: No active invites")
                return

            lines = [f"List Invites {len(invites)} active"]
            for inv in invites[:20]:
                code = inv.get("code", "?")
                uses = inv.get("uses", 0)
                max_uses = inv.get("max_uses", 0)
                uses_str = f"{uses}/{max_uses}" if max_uses else f"{uses}/\u221e"
                channel_name = inv.get("channel", {}).get("name", "?")
                inviter = inv.get("inviter", {}).get("username", "?")
                lines.append(f"> discord.gg/{code} :: #{channel_name} | {uses_str} uses | {inviter}")

            msg = api.send_message(ctx["channel_id"], "```| " + " |\n".join(lines) + "```")
        except Exception as e:
            msg = api.send_message(ctx["channel_id"], f"> **✗ List Invites** :: Error: {str(e)[:80]}")

    # -----------------------------------------------------------------------
    # webhook — post a message through a webhook URL
    # -----------------------------------------------------------------------

    @bot.command(name="webhook", aliases=["wh", "webhooksend", "hookpost"])
    def webhook_cmd(ctx, args):
        if not is_control_user(ctx["author_id"]):
            deny_restricted_command(ctx, "Webhook")
            return

        if len(args) < 2:
            msg = ctx["api"].send_message(
                ctx["channel_id"],
                f"> **Webhook** :: Usage: {bot.prefix}webhook <url> <message> [--name <username>]",
            )
            return

        api = ctx["api"]
        url = args[0]
        if not (url.startswith("https://discord.com/api/webhooks/") or url.startswith("https://discordapp.com/api/webhooks/")):
            msg = api.send_message(ctx["channel_id"], "> **✗ Webhook** :: Invalid webhook URL")
            return

        remaining = list(args[1:])
        username = None
        avatar_url = None

        if "--name" in remaining:
            idx = remaining.index("--name")
            if idx + 1 < len(remaining):
                username = remaining[idx + 1]
                del remaining[idx:idx + 2]

        if "--avatar" in remaining:
            idx = remaining.index("--avatar")
            if idx + 1 < len(remaining):
                avatar_url = remaining[idx + 1]
                del remaining[idx:idx + 2]

        payload = {"content": " ".join(remaining)}
        if username:
            payload["username"] = username
        if avatar_url:
            payload["avatar_url"] = avatar_url

        try:
            r = api.session.post(url + "?wait=true", json=payload, timeout=10)
            if r.status_code in (200, 204):
                msg = api.send_message(ctx["channel_id"], "> **✓ Webhook** :: Message sent")
            else:
                err = ""
                try:
                    err = r.json().get("message", "")
                except Exception:
                    pass
                msg = api.send_message(ctx["channel_id"], f"> **✗ Webhook** :: Failed ({r.status_code}): {err or 'Unknown'}")
        except Exception as e:
            msg = api.send_message(ctx["channel_id"], f"> **✗ Webhook** :: Error: {str(e)[:80]}")

    # -----------------------------------------------------------------------
    # reply — reply to a message by ID
    # -----------------------------------------------------------------------

    @bot.command(name="reply", aliases=["rep", "replyto"])
    def reply_cmd(ctx, args):
        if not is_control_user(ctx["author_id"]):
            deny_restricted_command(ctx, "Reply")
            return

        if len(args) < 2:
            msg = ctx["api"].send_message(
                ctx["channel_id"],
                f"> **Reply** :: Usage: {bot.prefix}reply <message_id> <content>",
            )
            return

        api = ctx["api"]
        message_id = args[0]
        content = " ".join(args[1:])

        try:
            r = api.request(
                "POST",
                f"/channels/{ctx['channel_id']}/messages",
                data={
                    "content": content,
                    "message_reference": {
                        "message_id": message_id,
                        "channel_id": ctx["channel_id"],
                        "fail_if_not_exists": False,
                    },
                },
            )
            if r and r.status_code in (200, 201):
                sent = r.json()
            else:
                code = r.status_code if r else "No response"
                msg = api.send_message(ctx["channel_id"], f"> **✗ Reply** :: Failed: HTTP {code}")
        except Exception as e:
            msg = api.send_message(ctx["channel_id"], f"> **✗ Reply** :: Error: {str(e)[:80]}")
    bot._handle_message = new_process_message
    
    # Cleanup function for bot shutdown
    original_stop = bot.stop
    _stop_once_lock = threading.Lock()
    _stop_once_state = {"done": False}

    def new_stop():
        with _stop_once_lock:
            if _stop_once_state["done"]:
                return
            _stop_once_state["done"] = True

        print("[AccountData] Stopping local stats job...")

        stop_rpc_keepalive(bot=bot, clear_activity=False)

        # Main controller shutdown should also stop all hosted child instances.
        if not HOSTED_MODE:
            try:
                host_manager.cleanup()
            except Exception:
                pass

        account_data_manager.stop_stats_job()
        account_data_manager.stop_auto_scrape()
        history_manager.stop_background_scraping()
        history_manager.save_history()
        boost_manager.save_state()
        original_stop()
    bot.stop = new_stop
    
    try:
        bot.run()
    except KeyboardInterrupt:
        bot.stop()
        print("\nBot stopped")

if __name__ == "__main__":

    main()



