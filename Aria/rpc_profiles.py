"""Persistent RPC presets and rotation settings for Aria."""

import json
import os
import tempfile
import threading
from typing import Any, Dict, List, Optional

_STORE_LOCKS = {}
_STORE_LOCKS_LOCK = threading.Lock()


class RPCProfileStore:
    MAX_PRESETS = 50
    MAX_NAME_LENGTH = 48
    MIN_ROTATION_INTERVAL = 15
    MAX_ROTATION_INTERVAL = 3600

    def __init__(self, path: str):
        self.path = os.path.abspath(path)
        with _STORE_LOCKS_LOCK:
            self._lock = _STORE_LOCKS.setdefault(self.path, threading.RLock())

    def _read(self) -> dict:
        try:
            with open(self.path, "r", encoding="utf-8") as state_file:
                state = json.load(state_file)
        except (OSError, json.JSONDecodeError):
            return {"presets": {}, "rotation": None, "stack": []}
        if not isinstance(state, dict):
            return {"presets": {}, "rotation": None, "stack": []}
        presets = state.get("presets")
        state["presets"] = presets if isinstance(presets, dict) else {}
        stack = state.get("stack")
        state["stack"] = stack if isinstance(stack, list) else []
        return state

    def _write(self, state: dict) -> None:
        directory = os.path.dirname(os.path.abspath(self.path))
        os.makedirs(directory, exist_ok=True)
        descriptor, temp_path = tempfile.mkstemp(prefix=".rpc-profiles-", dir=directory)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as state_file:
                json.dump(state, state_file, indent=2, ensure_ascii=True)
                state_file.flush()
                os.fsync(state_file.fileno())
            os.replace(temp_path, self.path)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    @staticmethod
    def _normalize_name(name: str) -> str:
        normalized = str(name or "").strip()
        if not normalized or len(normalized) > RPCProfileStore.MAX_NAME_LENGTH:
            raise ValueError("Preset names must be 1 to 48 characters")
        if any(ord(char) < 32 for char in normalized):
            raise ValueError("Preset names cannot contain control characters")
        return normalized

    @staticmethod
    def _normalize_activity(activity):
        if isinstance(activity, list):
            if not activity or len(activity) > 5 or any(not isinstance(item, dict) or not item for item in activity):
                raise ValueError("RPC activity bundles must contain one to five activity objects")
        elif not isinstance(activity, dict) or not activity:
            raise ValueError("An RPC activity dictionary or activity bundle is required")
        try:
            serialized = json.dumps(activity, ensure_ascii=True, allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise ValueError("RPC activity must contain JSON-compatible values") from exc
        if len(serialized.encode("utf-8")) > 65536:
            raise ValueError("RPC activity is too large to save")
        return json.loads(serialized)

    def list_presets(self) -> Dict[str, dict]:
        with self._lock:
            presets = self._read()["presets"]
            return {
                name: dict(activity)
                for name, activity in presets.items()
                if isinstance(name, str) and isinstance(activity, (dict, list))
            }

    def get_preset(self, name: str) -> Optional[dict]:
        normalized = self._normalize_name(name)
        with self._lock:
            activity = self._read()["presets"].get(normalized)
            if isinstance(activity, dict):
                return dict(activity)
            if isinstance(activity, list):
                return [dict(item) for item in activity if isinstance(item, dict)]
            return None

    def get_stack(self) -> List[dict]:
        with self._lock:
            return [dict(item) for item in self._read()["stack"] if isinstance(item, dict)]

    def save_stack(self, activities: List[dict]) -> List[dict]:
        normalized = self._normalize_activity(activities)
        if not isinstance(normalized, list):
            raise ValueError("RPC stack must be a list of activities")
        with self._lock:
            state = self._read()
            state["stack"] = normalized
            self._write(state)
        return [dict(item) for item in normalized]

    def clear_stack(self) -> None:
        with self._lock:
            state = self._read()
            state["stack"] = []
            self._write(state)

    def save_preset(self, name: str, activity: dict) -> None:
        normalized = self._normalize_name(name)
        normalized_activity = self._normalize_activity(activity)
        with self._lock:
            state = self._read()
            presets = state["presets"]
            if normalized not in presets and len(presets) >= self.MAX_PRESETS:
                raise ValueError(f"A maximum of {self.MAX_PRESETS} RPC presets is allowed")
            presets[normalized] = normalized_activity
            self._write(state)

    def delete_preset(self, name: str) -> bool:
        normalized = self._normalize_name(name)
        with self._lock:
            state = self._read()
            if normalized not in state["presets"]:
                return False
            del state["presets"][normalized]
            rotation = state.get("rotation")
            if isinstance(rotation, dict):
                rotation["presets"] = [item for item in rotation.get("presets", []) if item != normalized]
                if len(rotation["presets"]) < 2:
                    state["rotation"] = None
            self._write(state)
            return True

    def set_rotation(self, names: List[str], interval: int) -> dict:
        if not isinstance(names, list):
            raise ValueError("Rotation presets must be a list")
        normalized_names = [self._normalize_name(name) for name in names]
        if len(normalized_names) < 2 or len(set(normalized_names)) != len(normalized_names):
            raise ValueError("Rotation needs at least two unique presets")
        try:
            interval = int(interval)
        except (TypeError, ValueError) as exc:
            raise ValueError("Rotation interval must be a whole number of seconds") from exc
        if not self.MIN_ROTATION_INTERVAL <= interval <= self.MAX_ROTATION_INTERVAL:
            raise ValueError(
                f"Rotation interval must be {self.MIN_ROTATION_INTERVAL} to {self.MAX_ROTATION_INTERVAL} seconds"
            )
        with self._lock:
            state = self._read()
            missing = [name for name in normalized_names if name not in state["presets"]]
            if missing:
                raise ValueError(f"Unknown RPC preset: {', '.join(missing)}")
            state["rotation"] = {"presets": normalized_names, "interval": interval}
            self._write(state)
            return dict(state["rotation"])

    def get_rotation(self) -> Optional[dict]:
        with self._lock:
            rotation = self._read().get("rotation")
            if not isinstance(rotation, dict):
                return None
            names = rotation.get("presets")
            interval = rotation.get("interval")
            if not isinstance(names, list) or len(names) < 2 or not isinstance(interval, int):
                return None
            return {"presets": list(names), "interval": interval}

    def clear_rotation(self) -> None:
        with self._lock:
            state = self._read()
            state["rotation"] = None
            self._write(state)