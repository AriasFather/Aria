"""Opt-in local feed for matching messages, edits, and deletions."""

import json
import os
import tempfile
import threading
import time
from collections import deque
from typing import Any, Dict, Optional


DEFAULT_CONFIG = {
    "enabled": False,
    "keywords": [],
    "mentions": True,
    "edits": True,
    "deletes": True,
    "ignore_self": True,
    "scope": {"mode": "all", "id": ""},
}
VALID_SCOPES = {"all", "dms", "guilds", "guild", "channel"}
MAX_KEYWORDS = 100
MAX_KEYWORD_LENGTH = 80
MAX_CONTENT_LENGTH = 2000
MAX_FEED_EVENTS = 400


class MessageLogger:
    def __init__(self, path: str, feed_limit: int = MAX_FEED_EVENTS):
        self.path = os.path.abspath(path)
        self.feed_limit = max(1, min(int(feed_limit), MAX_FEED_EVENTS))
        self._lock = threading.RLock()
        self._feed = deque(maxlen=self.feed_limit)
        self.config = self._load_config()

    def _load_config(self) -> dict:
        try:
            with open(self.path, "r", encoding="utf-8") as config_file:
                data = json.load(config_file)
        except (OSError, json.JSONDecodeError):
            data = {}
        if not isinstance(data, dict):
            data = {}
        config = dict(DEFAULT_CONFIG)
        config.update({key: data[key] for key in DEFAULT_CONFIG if key in data})
        config["keywords"] = self._normalize_keywords(config.get("keywords"))
        scope = config.get("scope")
        if not isinstance(scope, dict):
            scope = {}
        mode = str(scope.get("mode", "all")).lower()
        config["scope"] = {
            "mode": mode if mode in VALID_SCOPES else "all",
            "id": str(scope.get("id") or "").strip(),
        }
        for key in ("enabled", "mentions", "edits", "deletes", "ignore_self"):
            config[key] = bool(config[key])
        return config

    @staticmethod
    def _normalize_keywords(values) -> list:
        if not isinstance(values, list):
            return []
        result = []
        seen = set()
        for value in values:
            word = str(value or "").strip()[:MAX_KEYWORD_LENGTH]
            folded = word.casefold()
            if word and folded not in seen and len(result) < MAX_KEYWORDS:
                seen.add(folded)
                result.append(word)
        return result

    def _save(self) -> None:
        directory = os.path.dirname(self.path)
        os.makedirs(directory, exist_ok=True)
        descriptor, temp_path = tempfile.mkstemp(prefix=".message-logger-", dir=directory)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as config_file:
                json.dump(self.config, config_file, indent=2, ensure_ascii=True)
                config_file.flush()
                os.fsync(config_file.fileno())
            os.replace(temp_path, self.path)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def update_config(self, patch: dict) -> dict:
        if not isinstance(patch, dict):
            raise ValueError("Logger configuration must be an object")
        with self._lock:
            for key in ("enabled", "mentions", "edits", "deletes", "ignore_self"):
                if key in patch:
                    self.config[key] = bool(patch[key])
            if "keywords" in patch:
                self.config["keywords"] = self._normalize_keywords(patch["keywords"])
            if "scope" in patch:
                scope = patch["scope"]
                if not isinstance(scope, dict):
                    raise ValueError("Logger scope must be an object")
                mode = str(scope.get("mode", self.config["scope"]["mode"])).lower()
                scope_id = str(scope.get("id", self.config["scope"]["id"]) or "").strip()
                if mode not in VALID_SCOPES:
                    raise ValueError(f"Scope must be one of: {', '.join(sorted(VALID_SCOPES))}")
                if mode in {"guild", "channel"} and not scope_id:
                    raise ValueError(f"A {mode} ID is required for this scope")
                self.config["scope"] = {"mode": mode, "id": scope_id}
            self._save()
            return self.state()

    def state(self) -> dict:
        with self._lock:
            return {"config": json.loads(json.dumps(self.config)), "feed": list(reversed(self._feed))}

    def clear_feed(self) -> None:
        with self._lock:
            self._feed.clear()

    def _in_scope(self, guild_id: str, channel_id: str) -> bool:
        scope = self.config["scope"]
        mode = scope["mode"]
        if mode == "all":
            return True
        if mode == "dms":
            return not guild_id
        if mode == "guilds":
            return bool(guild_id)
        if mode == "guild":
            return guild_id == scope["id"]
        if mode == "channel":
            return channel_id == scope["id"]
        return False

    @staticmethod
    def _message_data(payload: dict) -> dict:
        author = payload.get("author") or {}
        message_id = str(payload.get("id") or "")
        channel_id = str(payload.get("channel_id") or "")
        guild_id = str(payload.get("guild_id") or "")
        attachments = payload.get("attachments") or []
        return {
            "id": message_id,
            "channel_id": channel_id,
            "guild_id": guild_id,
            "author_id": str(author.get("id") or ""),
            "author": str(author.get("global_name") or author.get("username") or "Unknown"),
            "content": str(payload.get("content") or "")[:MAX_CONTENT_LENGTH],
            "attachments": [str(item.get("url")) for item in attachments[:10] if isinstance(item, dict) and item.get("url")],
            "jump": f"https://discord.com/channels/{guild_id or '@me'}/{channel_id}/{message_id}",
            "ts": int(time.time()),
        }

    def _record(self, entry: dict, kind: str, owner_id: Optional[str], **extra) -> None:
        if not self.config["enabled"]:
            return
        if self.config["ignore_self"] and owner_id and entry["author_id"] == str(owner_id):
            return
        if not self._in_scope(entry["guild_id"], entry["channel_id"]):
            return
        event = {**entry, "kind": kind, **extra}
        with self._lock:
            self._feed.append(event)

    def on_message_create(self, payload: dict, owner_id: Optional[str] = None) -> None:
        if not self.config["enabled"] or not isinstance(payload, dict):
            return
        entry = self._message_data(payload)
        if self.config["ignore_self"] and owner_id and entry["author_id"] == str(owner_id):
            return
        if not self._in_scope(entry["guild_id"], entry["channel_id"]):
            return
        mentions = payload.get("mentions") or []
        if self.config["mentions"] and owner_id and any(str(item.get("id") or "") == str(owner_id) for item in mentions if isinstance(item, dict)):
            self._record(entry, "mention", owner_id)
            return
        content = entry["content"].casefold()
        matched = next((word for word in self.config["keywords"] if word.casefold() in content), None)
        if matched:
            self._record(entry, "keyword", owner_id, matched=matched)

    def on_message_update(self, payload: dict, before: Optional[dict], owner_id: Optional[str] = None) -> None:
        if not self.config["enabled"] or not self.config["edits"] or not isinstance(payload, dict):
            return
        merged = dict(before or {})
        merged.update(payload)
        entry = self._message_data(merged)
        old_content = str((before or {}).get("content") or "")[:MAX_CONTENT_LENGTH]
        if not entry["content"] or entry["content"] == old_content:
            return
        self._record(entry, "edit", owner_id, before=old_content, after=entry["content"])

    def on_message_delete(self, payload: dict, cached: Optional[dict], owner_id: Optional[str] = None) -> None:
        if not self.config["enabled"] or not self.config["deletes"] or not isinstance(payload, dict):
            return
        merged = dict(cached or {})
        merged.update(payload)
        entry = self._message_data(merged)
        self._record(entry, "delete", owner_id)