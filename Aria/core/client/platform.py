import importlib.util
import json
import logging
import os
import uuid
from pathlib import Path
from typing import Any, Optional
from discord_api_types import DEFAULT_GATEWAY_INTENTS, GatewayOpcodes

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SHARED_CONFIG_PATH = PROJECT_ROOT / "core" / "shared" / "config.py"
RUNTIME_STATE_PATH = PROJECT_ROOT / "runtime_state.json"

_TOKEN_INSTANCE_FILE = {}

CLIENT_PROFILES = {
    "web": {
        "$os": "linux",
        "$browser": "Chrome",
        "$device": "",
        "browser_user_agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.6422.113 Safari/537.36",
        "browser_version": "125.0.6422.113",
        "os_version": "",
        "system_locale": "en-US",
        "release_channel": "stable",
        "client_build_number": 284054,
    },
    "desktop": {
        "$os": "Windows",
        "$browser": "Discord Client",
        "$device": "desktop",
        "browser_user_agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) discord/1.0.9167 Chrome/124.0.6367.207 Electron/30.2.0 Safari/537.36",
        "browser_version": "30.2.0",
        "os_version": "10.0.22631",
        "system_locale": "en-US",
        "release_channel": "stable",
        "client_build_number": 284054,
    },
    "mobile": {
        "$os": "Android",
        "$browser": "Discord Android",
        "$device": "android",
        "browser_user_agent": "com.discord",
        "browser_version": "",
        "os_version": "14",
        "system_locale": "en-US",
        "release_channel": "stable",
        "client_build_number": 284054,
    },
    "vr": {
        "$os": "Meta Quest",
        "$browser": "Discord VR",
        "$device": "Meta Quest 3",
        "browser_user_agent": "Mozilla/5.0 (Linux; Android 14; Meta Quest 3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
        "browser_version": "Discord VR",
        "os_version": "Meta Quest OS",
        "system_locale": "en-US",
        "release_channel": "stable",
        "client_build_number": 284054,
    },
}

_CLIENT_ALIASES = {
    "android": "mobile",
    "ios": "mobile",
    "phone": "mobile",
    "browser": "web",
    "client": "desktop",
    "windows": "desktop",
}

_STATUS_ALIASES = {
    "ready": "online",
    "busy": "dnd",
    "offline": "invisible",
}


class SessionConfig:
    def __init__(self, device: str, enabled: bool = True):
        self.device = device
        self.enabled = enabled


def register_instance_token(token: str, instance_file: str):
    if not token or not instance_file:
        return
    _TOKEN_INSTANCE_FILE[str(token)] = str(instance_file)


def unregister_instance_token(token: str):
    if not token:
        return
    _TOKEN_INSTANCE_FILE.pop(str(token), None)


def _runtime_state() -> dict:
    try:
        with open(RUNTIME_STATE_PATH, "r", encoding="utf-8") as file_obj:
            data = json.load(file_obj)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _load_module_from_path(file_path: str) -> Optional[Any]:
    if not file_path or not os.path.exists(file_path):
        return None
    try:
        module_name = f"aria_platform_{abs(hash(file_path))}"
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except Exception as exc:
        logger.debug("Failed to load config module %s: %s", file_path, exc)
        return None


def _coerce_session(value: Any, default: str) -> SessionConfig:
    if hasattr(value, "device"):
        enabled = bool(getattr(value, "enabled", True))
        return SessionConfig(str(getattr(value, "device", default) or default), enabled)
    if isinstance(value, str) and value.strip():
        return SessionConfig(value.strip(), True)
    return SessionConfig(default, True)


def normalize_client_type(value: Optional[str]) -> str:
    raw = str(value or "mobile").strip().lower()
    raw = _CLIENT_ALIASES.get(raw, raw)
    return raw if raw in CLIENT_PROFILES else "web"


def normalize_status(value: Optional[str]) -> str:
    raw = str(value or "online").strip().lower()
    raw = _STATUS_ALIASES.get(raw, raw)
    return raw if raw in {"online", "idle", "dnd", "invisible"} else "online"


def resolve_instance_file(token: Optional[str] = None, explicit_instance_file: Optional[str] = None) -> Optional[str]:
    if explicit_instance_file and os.path.exists(explicit_instance_file):
        return explicit_instance_file
    mapped = _TOKEN_INSTANCE_FILE.get(str(token or ""))
    if mapped and os.path.exists(mapped):
        return mapped
    return None


def load_instance_session(instance_file: str):
    module = _load_module_from_path(instance_file)
    if module is None:
        return None
    session = getattr(module, "session", None)
    if session is not None:
        return session
    container = getattr(module, "container", None)
    if container is not None:
        return getattr(container, "client", None)
    return None


def configtarget(uid: int = 0, username: str = "", instance_file: str = "", token: str = "") -> str:
    resolved = resolve_instance_file(token=token, explicit_instance_file=instance_file)
    if resolved:
        return resolved
    return str(SHARED_CONFIG_PATH)


def get_config_source(instance_file: str = "", token: str = "") -> str:
    resolved = resolve_instance_file(token=token, explicit_instance_file=instance_file)
    return "instance" if resolved else "developer"


def container_client_loader(uid: int = 0, username: str = "", instance_file: str = "", token: str = ""):
    path = configtarget(uid=uid, username=username, instance_file=instance_file, token=token)
    module = _load_module_from_path(path)
    if module is not None:
        container = getattr(module, "container", None)
        if container is not None and getattr(container, "client", None):
            return _coerce_session(getattr(container, "client"), "mobile")
        session = getattr(module, "session", None)
        if session is not None:
            return _coerce_session(session, "mobile")

    try:
        from core.shared.config import container as fallback_container
    except ImportError:
        fallback_container = None  # Graceful fallback for unresolved import

    if fallback_container and getattr(fallback_container, "client", None):
        return _coerce_session(getattr(fallback_container, "client"), "mobile")
    return _coerce_session("web", "web")


def container_state_loader(uid: int = 0, username: str = "", instance_file: str = "", token: str = ""):
    path = configtarget(uid=uid, username=username, instance_file=instance_file, token=token)
    module = _load_module_from_path(path)
    if module is not None:
        container = getattr(module, "container", None)
        if container is not None and getattr(container, "state", None):
            return _coerce_session(getattr(container, "state"), "online")
        session = getattr(module, "session", None)
        if session is not None and getattr(session, "state", None):
            return _coerce_session(getattr(session, "state"), "online")


    try:
        from core.shared.config import container as fallback_container
    except ImportError:
        fallback_container = None  # Graceful fallback for unresolved import

    if fallback_container and getattr(fallback_container, "state", None):
        return _coerce_session(getattr(fallback_container, "state"), "online")
    return _coerce_session("online", "online")


def build_identify_payload(token: str, client_type: str, status: str = "online", activity: Any = None, intents: int = DEFAULT_GATEWAY_INTENTS, compress: bool = False) -> dict:
    resolved_client = normalize_client_type(client_type)
    resolved_status = normalize_status(status)
    properties = dict(CLIENT_PROFILES.get(resolved_client, CLIENT_PROFILES["web"]))
    if resolved_client == "mobile":
        properties["device_vendor_id"] = str(uuid.uuid4())
    if isinstance(activity, dict):
        activities = [activity]
    elif isinstance(activity, (list, tuple)):
        activities = [item for item in activity if isinstance(item, dict)][:5]
    else:
        activities = []

    return {
        "op": GatewayOpcodes.Identify,
        "d": {
            "token": token,
            "properties": properties,
            "presence": {
                "status": resolved_status,
                "since": 0,
                "activities": activities,
                "afk": False,
            },
            "compress": compress,
            "large_threshold": 250,
            "intents": intents,
        },
    }


def client_identify(instance_file: str = "", bot: Any = None, token: str = ""):
    client_session = container_client_loader(instance_file=instance_file, token=str(token or getattr(bot, "token", "default_token")))
    resolved = normalize_client_type(getattr(client_session, "device", "mobile"))
    if bot is not None and getattr(client_session, "enabled", True):
        bot._client_type = resolved
    logger.info("Platform client identify resolved: device=%s source=%s", resolved, get_config_source(instance_file, str(token or getattr(bot, "token", "default_token"))))
    return resolved


def state_identify(instance_file: str = "", bot: Any = None, token: str = ""):
    state_session = container_state_loader(instance_file=instance_file, token=str(token or getattr(bot, "token", "default_token")))
    resolved = normalize_status(getattr(state_session, "device", "online"))
    if bot is not None and getattr(state_session, "enabled", True):
        bot._current_status = resolved
    logger.info("Platform state identify resolved: status=%s source=%s", resolved, get_config_source(instance_file, str(token or getattr(bot, "token", "default_token"))))
    return resolved


def unclient_identify():
    return None


def unstate_identify():
    return None