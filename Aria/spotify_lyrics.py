"""Spotify playback-to-custom-status lyrics sync for Aria."""

from __future__ import annotations

import json
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Optional


SPOTIFY_API = "https://api.spotify.com/v1"
LRCLIB_API = "https://lrclib.net/api/get"
TOKEN_TTL = 50 * 60
SYNC_INTERVAL = 30.0
_TIMESTAMP = re.compile(r"\[(?:(\d+):)?(\d+):(\d+(?:\.\d+)?)\]\s*(.*)")


def parse_synced_lyrics(raw: str) -> list[tuple[int, str]]:
    """Parse standard LRC timestamps into sorted millisecond/text pairs."""
    lines: list[tuple[int, str]] = []
    for line in raw.splitlines():
        match = _TIMESTAMP.match(line)
        if not match:
            continue
        hours, minutes, seconds, text = match.groups()
        milliseconds = (
            int(hours or 0) * 3_600_000
            + int(minutes) * 60_000
            + int(float(seconds) * 1_000)
        )
        lines.append((milliseconds, text.strip()))
    return sorted(lines, key=lambda item: item[0])


def _read_json(url: str, headers: dict[str, str], timeout: int) -> Any:
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        if response.status == 204:
            return None
        return json.loads(response.read())


def fetch_synced_lyrics(title: str, artist: str, album: str, duration_seconds: int) -> list[tuple[int, str]]:
    params = urllib.parse.urlencode({
        "track_name": title,
        "artist_name": artist,
        "album_name": album,
        "duration": duration_seconds,
    })
    try:
        data = _read_json(
            f"{LRCLIB_API}?{params}",
            {"User-Agent": "Aria/1.0"},
            timeout=8,
        )
        return parse_synced_lyrics((data or {}).get("syncedLyrics") or "")
    except Exception as exc:
        print(f"[spotify-lyrics] LRCLIB lookup failed: {exc}")
        return []


def current_lyric(lyrics: list[tuple[int, str]], position_ms: int) -> tuple[str, Optional[int]]:
    current = ""
    next_timestamp: Optional[int] = None
    for index, (timestamp, text) in enumerate(lyrics):
        if timestamp <= position_ms:
            current = text
            next_timestamp = lyrics[index + 1][0] if index + 1 < len(lyrics) else None
        else:
            if next_timestamp is None:
                next_timestamp = timestamp
            break
    return current, next_timestamp


class SpotifyLyricsSync:
    """Poll linked Spotify playback and mirror synced lyric lines to custom status."""

    def __init__(self, api: Any):
        self.api = api
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._token: Optional[str] = None
        self._token_time = 0.0
        self._last_status = ""
        self._state_lock = threading.Lock()
        self._state: dict[str, Any] = {
            "enabled": False,
            "playing": False,
            "phase": "idle",
            "title": "",
            "artist": "",
            "album": "",
            "cover": "",
            "duration_ms": 0,
            "anchor_pos_ms": 0,
            "anchor_wall_ms": 0,
            "has_lyrics": False,
            "lyric_count": 0,
            "current_line": "",
            "error": "",
        }

    @property
    def running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def status(self) -> dict[str, Any]:
        with self._state_lock:
            state = dict(self._state)
        state["running"] = self.running
        return state

    def _publish_state(self, **changes: Any) -> None:
        with self._state_lock:
            self._state.update(changes)

    def start(self) -> bool:
        if self.running:
            return False
        self._stop_event.clear()
        self._publish_state(enabled=True, phase="starting", error="")
        self._thread = threading.Thread(
            target=self._run,
            name="AriaSpotifyLyrics",
            daemon=True,
        )
        self._thread.start()
        return True

    def stop(self) -> bool:
        if not self.running:
            return False
        self._publish_state(enabled=False, phase="stopping")
        self._stop_event.set()
        return True

    def _response_json(self, response: Any) -> Any:
        if response is None:
            return None
        if isinstance(response, dict):
            return response
        if getattr(response, "status_code", 0) != 200:
            return None
        try:
            return response.json()
        except Exception:
            return None

    def _get_spotify_token(self) -> Optional[str]:
        try:
            response = self.api.request("GET", "/users/@me/connections")
        except Exception as exc:
            print(f"[spotify-lyrics] Could not load linked connections: {exc}")
            return None
        connections = self._response_json(response) or []
        connection = next(
            (item for item in connections if item.get("type") == "spotify"),
            None,
        )
        if not connection:
            self._publish_state(error="Link Spotify under Discord Settings > Connections first.")
            print("[spotify-lyrics] Link Spotify under Discord Settings > Connections first.")
            return None
        if connection.get("access_token"):
            return connection["access_token"]

        connection_id = connection.get("id")
        paths = []
        if connection_id:
            paths.extend((
                f"/connections/spotify/{connection_id}/access-token",
                f"/users/@me/connections/spotify/{connection_id}/access-token",
            ))
        paths.append("/users/@me/connections/spotify/access-token")
        for path in paths:
            try:
                response = self.api.request("GET", path)
            except Exception as exc:
                print(f"[spotify-lyrics] Token lookup failed for {path}: {exc}")
                continue
            data = self._response_json(response)
            if isinstance(data, dict) and data.get("access_token"):
                return data["access_token"]
        print("[spotify-lyrics] Could not obtain a Spotify playback token from the linked connection.")
        self._publish_state(error="Could not obtain a Spotify playback token from the linked connection.")
        return None

    def _get_playback(self, token: str) -> Any:
        return _read_json(
            f"{SPOTIFY_API}/me/player",
            {"Authorization": f"Bearer {token}"},
            timeout=8,
        )

    def _set_custom_status(self, text: str) -> bool:
        text = text[:128] if text else ""
        try:
            response = self.api.request(
                "PATCH",
                "/users/@me/settings",
                json={"custom_status": {"text": text} if text else None},
            )
        except Exception as exc:
            print(f"[spotify-lyrics] Custom status update failed: {exc}")
            return False
        if response is None:
            return False
        status_code = getattr(response, "status_code", 200)
        if status_code not in (200, 204):
            print(f"[spotify-lyrics] Custom status update failed (HTTP {status_code}).")
            return False
        self._last_status = text
        return True

    def _clear_status_if_unchanged(self) -> None:
        if not self._last_status:
            return
        try:
            settings = self._response_json(self.api.request("GET", "/users/@me/settings")) or {}
            current = (settings.get("custom_status") or {}).get("text")
            if current == self._last_status:
                self._set_custom_status("")
        except Exception as exc:
            print(f"[spotify-lyrics] Could not check custom status during cleanup: {exc}")

    def _run(self) -> None:
        lyrics: list[tuple[int, str]] = []
        track_id = ""
        last_line = ""
        next_sync = 0.0
        anchor_position = 0
        anchor_time = 0.0

        print("[spotify-lyrics] Sync started.")
        try:
            while not self._stop_event.is_set():
                now = time.time()
                if not self._token or now - self._token_time >= TOKEN_TTL:
                    self._token = self._get_spotify_token()
                    self._token_time = now
                    if not self._token:
                        self._publish_state(phase="waiting", enabled=True)
                        self._stop_event.wait(10)
                        continue

                if now >= next_sync:
                    try:
                        started = time.time()
                        playback = self._get_playback(self._token)
                        received = time.time()
                    except urllib.error.HTTPError as exc:
                        if exc.code == 401:
                            self._token = None
                            continue
                        if exc.code == 403:
                            print("[spotify-lyrics] Spotify playback API returned 403; Premium may be required.")
                        else:
                            print(f"[spotify-lyrics] Spotify API returned HTTP {exc.code}.")
                        self._stop_event.wait(5)
                        continue
                    except Exception as exc:
                        print(f"[spotify-lyrics] Playback lookup failed: {exc}")
                        self._stop_event.wait(5)
                        continue

                    if not playback or not playback.get("is_playing"):
                        self._publish_state(phase="waiting_for_playback", playing=False, current_line="", error="")
                        self._stop_event.wait(5)
                        continue

                    item = playback.get("item") or {}
                    current_track_id = item.get("id") or ""
                    anchor_position = int(playback.get("progress_ms") or 0) + int((received - started) * 500)
                    anchor_time = received
                    next_sync = received + SYNC_INTERVAL

                    if current_track_id != track_id:
                        track_id = current_track_id
                        last_line = ""
                        album_data = item.get("album") or {}
                        artists = item.get("artists") or []
                        title = item.get("name") or ""
                        artist = ", ".join(entry.get("name", "") for entry in artists)
                        album = album_data.get("name") or ""
                        duration = int(item.get("duration_ms") or 0)
                        lyrics = fetch_synced_lyrics(title, artist, album, duration // 1000)
                        images = album_data.get("images") or []
                        self._publish_state(
                            enabled=True,
                            phase="syncing" if lyrics else "no_lyrics",
                            playing=True,
                            title=title,
                            artist=artist,
                            album=album,
                            cover=images[0].get("url", "") if images else "",
                            duration_ms=duration,
                            anchor_pos_ms=anchor_position,
                            anchor_wall_ms=int(anchor_time * 1000),
                            has_lyrics=bool(lyrics),
                            lyric_count=len(lyrics),
                            current_line="",
                            error="" if lyrics else "No synced lyrics were found for this track.",
                        )
                        print(f"[spotify-lyrics] Loaded {len(lyrics)} synced lines for {title!r}.")
                        if not lyrics:
                            self._set_custom_status(f"♪ {title}" if title else "♪")

                    self._publish_state(
                        playing=True,
                        anchor_pos_ms=anchor_position,
                        anchor_wall_ms=int(anchor_time * 1000),
                    )

                if lyrics:
                    position = anchor_position + int((time.time() - anchor_time) * 1000)
                    line, next_timestamp = current_lyric(lyrics, position)
                    if line and line != last_line:
                        last_line = line
                        self._set_custom_status(line)
                        self._publish_state(current_line=line)
                        print(f"[spotify-lyrics] {line}")
                    wait_seconds = 1.0
                    if next_timestamp is not None:
                        wait_seconds = max(0.05, min(1.0, (next_timestamp - position) / 1000))
                    if next_sync > time.time():
                        wait_seconds = min(wait_seconds, max(0.05, next_sync - time.time()))
                else:
                    wait_seconds = max(0.1, min(1.0, next_sync - time.time())) if next_sync else 1.0
                self._stop_event.wait(wait_seconds)
        finally:
            self._clear_status_if_unchanged()
            self._publish_state(
                enabled=False,
                playing=False,
                phase="idle",
                current_line="",
            )
            print("[spotify-lyrics] Sync stopped.")