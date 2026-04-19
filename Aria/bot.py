import json
import time
import threading
import ssl
import os
import re
from urllib.parse import urlparse
from typing import Dict, Any, Callable, List, Optional, Union
from api_client import DiscordAPIClient
from discord_api_types import ActivityType, DEFAULT_GATEWAY_INTENTS, GatewayOpcodes
from owner import BotCustomizer
from nitro import NitroSniper
from anti_gc_trap import AntiGCTrap
from giveaway import GiveawaySniper
from header_spoofer import HeaderSpoofer
from core.client.platform import CLIENT_PROFILES, normalize_client_type, normalize_status
import queue
import websocket
# Removed incorrect import
# from .utils import normalize_client_type, normalize_status

# Defining missing functions
from core.client.platform import client_identify, state_identify, build_identify_payload

class Command:
    def __init__(self, func: Callable, name: str, aliases: Optional[List[str]] = None):
        self.func = func
        self.name = name
        self.aliases = aliases or []

class DiscordBot:
    def __init__(self, token: str, prefix: str = "$", config: Union[Dict[str, Any], Any, None] = None):
        self.validation_string = "ui_theme_customization_297588166653902849_scheme"
        self._verify_system()

        self.token = token
        self.prefix = prefix
        self.globalPrefix = prefix  # keep for back-compat
        self._config_prefix = prefix  # immutable fallback — never mutated
        self.config = config or {}
        self.ownerId = "297588166653902849"
        self.instance_id = "default_instance"  # Initialize instance_id as a string

        # Initialize API client
        captcha_enabled = self.config.get("captcha_enabled", self.config.get("captchaEnabled", False))
        captcha_api_key = self.config.get("captcha_api_key", self.config.get("captchaApiKey", ""))
        captcha_service = self.config.get("captcha_service", self.config.get("captchaService", "2captcha"))
        print(f"[DEBUG] Loaded captcha_api_key: {captcha_api_key[:6]}...{captcha_api_key[-6:] if captcha_api_key else ''}")
        print(f"[DEBUG] Loaded captcha_service: {captcha_service}")
        self.api = DiscordAPIClient(token, captcha_api_key, captcha_enabled, captcha_service)

        self.customizer = BotCustomizer()
        self.nitro_sniper = NitroSniper(self.api)
        self.giveaway_sniper = GiveawaySniper(self.api)
        self.anti_gc_trap = AntiGCTrap(self.api)
        self.protection_coordinator = self.api.header_spoofer

        self.commands: Dict[str, Command] = {}
        self._snipe_cache: Dict[str, Any] = {}
        self._esnipe_cache: Dict[str, Any] = {}
        self._msg_cache: Dict[str, Any] = {}

        self.running = True
        self.ws: Any = None
        self.ws_thread = None
        self.sequence = None
        self.user_id = None
        self.username = None
        self.auto_react_emoji = None
        self.message_queue = queue.Queue()
        self.last_heartbeat = time.time()
        self.heartbeat_interval: Optional[float] = None
        self._heartbeat_sent_at: Optional[float] = None
        self._last_ack_at: Optional[float] = None
        self.gateway_latency_ms: Optional[float] = None
        self._gateway_latency_samples: List[float] = []
        self.heartbeat_thread = None
        self.identified = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 999999
        # Session resume state (RFC: op 6 RESUME)
        self.session_id: Optional[str] = None
        self.resume_gateway_url: Optional[str] = None
        self.can_resume: bool = False
        self.activity = None
        self.activity_persist = True
        self._last_activity_signature = None
        self.connection_active = False
        self.command_count = 0
        self._client_type = "web"
        self._client_type_forced = False
        self._current_status = "online"
        self._auto_delete_enabled: bool = True
        self._auto_delete_delay: float = 3.0
        self._mimic_target: Optional[str] = None
        self._mimic_enabled: bool = False
        self._mimic_custom_response: Optional[str] = None
        self._mimic_sent_messages: Dict[str, Dict[str, str]] = {}
        self._mimic_last_sent_at: float = 0.0
        self._purge_active: bool = False
        self._purge_started_by: Optional[str] = None
        self._autoreact_targets: Dict[str, Dict[str, Any]] = {}
        self._autoreact_last_sent_at: float = 0.0

        # Enhanced gateway connection management
        self._connection_lock = threading.Lock()
        self._connecting = False
        self._last_connection_attempt = 0.0
        self._consecutive_failures = 0
        self._max_consecutive_failures = 15  # Increased from 10
        self._heartbeat_missed_count = 0
        self._max_missed_heartbeats = 5  # Increased from 3
        self._last_successful_heartbeat = time.time()
        self._connection_quality_score = 100  # 0-100, decreases with issues
        self._connection_start_time = time.time()
        self._total_uptime = 0.0
        self._last_uptime_check = time.time()
        self._network_stability_score = 100  # Track network reliability
        self._message_delete_hook: Optional[Callable[[str, str], None]] = None
        self._on_ready_hook: Optional[Callable[[Dict[str, Any]], None]] = None
        self.boost_manager: Any = None
        self._afk_system_ref: Any = None
        self.friend_scraper: Any = None
        self.self_hosting_manager: Any = None
        self.db: Any = None
        self._web_panel: Any = None  # Set by main.py after webpanel starts

        # Gateway Bridge Support (for async gateway compatibility)
        self.use_async_gateway = self.config.get("use_async_gateway", False)
        self.gateway_bridge = None

        # Load persisted per-user prefixes
        self.user_prefixes_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "user_prefixes.json"
        )
        try:
            with open(self.user_prefixes_file, "r") as _f:
                self.user_prefixes: Dict[str, str] = json.load(_f)
        except Exception:
            self.user_prefixes: Dict[str, str] = {}
        # Persist on startup (creates file if absent)
        try:
            with open(self.user_prefixes_file, "w") as _f:
                json.dump(self.user_prefixes, _f, indent=2)
        except Exception as e:
            print(f"Failed to save user prefixes: {e}")

    def _normalize_activity_payload(self, activity):
        if not isinstance(activity, dict):
            return activity

        normalized = dict(activity)

        try:
            normalized_type = int(normalized.get("type"))
            normalized["type"] = normalized_type
        except Exception:
            pass

        app_id = normalized.get("application_id")
        if isinstance(app_id, str):
            app_id = app_id.strip()
            if app_id.isdigit():
                normalized["application_id"] = int(app_id)
            elif not app_id:
                normalized.pop("application_id", None)

        assets = normalized.get("assets")
        if isinstance(assets, dict):
            cleaned_assets = {}
            for key in ("large_image", "large_text", "small_image", "small_text"):
                value = assets.get(key)
                if value is None:
                    continue
                if isinstance(value, dict):
                    value = value.get("url") or value.get("name") or value.get("id")
                value = str(value).strip()
                if not value:
                    continue
                if key in {"large_image", "small_image"}:
                    if value.startswith("mp:mp:"):
                        value = value[3:]
                    if value.startswith("attachments/"):
                        value = f"mp:{value}"
                    if value.startswith("https://cdn.discordapp.com/attachments/") or value.startswith("https://media.discordapp.net/attachments/"):
                        match = re.search(r"https?://(?:cdn\.discordapp\.com|media\.discordapp\.net)/attachments/(\d+)/(\d+)/([^?#]+)", value)
                        if match:
                            channel_id, attachment_id, filename = match.groups()
                            value = f"mp:attachments/{channel_id}/{attachment_id}/{filename}"
                cleaned_assets[key] = value
            if cleaned_assets:
                normalized["assets"] = cleaned_assets
            else:
                normalized.pop("assets", None)

        metadata = normalized.get("metadata")
        buttons = normalized.get("buttons")
        if isinstance(buttons, list):
            cleaned_buttons = [str(button).strip() for button in buttons if str(button or "").strip()][:2]
            if cleaned_buttons:
                normalized["buttons"] = cleaned_buttons
            else:
                normalized.pop("buttons", None)
        elif buttons is not None:
            normalized.pop("buttons", None)

        if isinstance(metadata, dict):
            button_urls = metadata.get("button_urls")
            if isinstance(button_urls, list):
                cleaned_urls = [str(url).strip() for url in button_urls if str(url or "").strip()]
                if cleaned_urls:
                    metadata = dict(metadata)
                    metadata["button_urls"] = cleaned_urls[:2]
                    normalized["metadata"] = metadata
                else:
                    normalized.pop("metadata", None)
            elif not metadata:
                normalized.pop("metadata", None)
        elif metadata is not None:
            normalized.pop("metadata", None)

        return normalized

    def get_user_prefix(self, user_id: str) -> str:
        return self.user_prefixes.get(str(user_id), self._config_prefix)

    def set_user_prefix(self, user_id: str, new_prefix: str) -> None:
        uid = str(user_id)
        self.user_prefixes[uid] = new_prefix
        if uid == self._active_account_id():
            self.prefix = new_prefix
            self.globalPrefix = new_prefix
        self._save_user_prefixes()

    def clear_user_prefix(self, user_id: str) -> None:
        uid = str(user_id)
        if uid in self.user_prefixes:
            del self.user_prefixes[uid]
            self._save_user_prefixes()
        if uid == self._active_account_id():
            default_prefix = self.config.get("prefix", "$")
            self.prefix = default_prefix
            self.globalPrefix = default_prefix

    # ── command registration ─────────────────────────────────────────────
    def _normalize_command_key(self, key: str) -> str:
        """Normalize command keys so spaces/underscores/hyphens are equivalent."""
        k = str(key or "").strip().lower()
        if not k:
            return ""
        return re.sub(r"[\s_\-]+", "", k)

    def _register_command_key(self, key: str, cmd_obj: Command, is_alias: bool = False) -> None:
        k = str(key or "").strip().lower()
        if not k:
            return

        existing = self.commands.get(k)
        if existing is not None and existing is not cmd_obj:
            existing_name = str(existing.name or "").strip().lower()

            # Aliases should never steal an existing binding.
            if is_alias:
                return

            # Avoid shadowing an earlier canonical command with another canonical
            # from the same source file. This keeps the first real implementation.
            if existing_name == k:
                try:
                    existing_file = str(existing.func.__code__.co_filename or "")
                    new_file = str(cmd_obj.func.__code__.co_filename or "")
                except Exception:
                    existing_file = ""
                    new_file = ""
                if existing_file and new_file and existing_file == new_file:
                    print(f"[COMMAND-REGISTER] duplicate command skipped: {k} ({new_file})")
                    return

        self.commands[k] = cmd_obj
        # Allow joined command variants (space/underscore/hyphen all equivalent).
        compact = self._normalize_command_key(k)
        if compact and compact not in self.commands:
            self.commands[compact] = cmd_obj

    def _resolve_command(self, command_name: str) -> Optional[Command]:
        k = str(command_name or "").strip().lower()
        if not k:
            return None
        cmd = self.commands.get(k)
        if cmd is not None:
            return cmd
        compact = self._normalize_command_key(k)
        if compact:
            cmd = self.commands.get(compact)
            if cmd is not None:
                return cmd
        return None

    def _resolve_command_with_args(self, command_name: str, args: List[str]):
        """Resolve command name and optionally consume leading args for spaced commands.

        Examples supported:
        - questautoclaimer
        - quest_auto_claimer
        - quest auto claimer
        """
        cmd = self._resolve_command(command_name)
        if cmd is not None:
            return cmd, args

        tokens = [str(command_name or "").strip()] + [str(a or "").strip() for a in (args or [])]
        max_parts = min(4, len(tokens))

        for part_count in range(max_parts, 1, -1):
            chunk = [t for t in tokens[:part_count] if t]
            if len(chunk) < 2:
                continue
            candidates = [
                "".join(chunk),
                "_".join(chunk),
                "-".join(chunk),
                " ".join(chunk),
            ]
            for candidate in candidates:
                cmd = self._resolve_command(candidate)
                if cmd is not None:
                    # args excludes original command token, so drop consumed extras only.
                    remaining_args = args[part_count - 1:]
                    return cmd, remaining_args

        return None, args

    def command(self, name: Optional[str] = None, aliases: Optional[List[str]] = None):
        def decorator(func: Callable):
            cmd_name = name or func.__name__
            cmd_obj = Command(func, cmd_name, aliases)
            self._register_command_key(cmd_name, cmd_obj, is_alias=False)
            # Register aliases, but do not let them clobber other canonical commands.
            for alias in (aliases or []):
                self._register_command_key(alias, cmd_obj, is_alias=True)
            return func
        return decorator

    def execute_command(self, user_id: str, command_name: str, *args, **kwargs):
        command = self._resolve_command(command_name)
        if command is None:
            raise ValueError("Command not found.")
        return command.func(*args, **kwargs)

    def run_command(self, command_name: str, ctx: Dict[str, Any], args: List[str]) -> None:
        cmd, args = self._resolve_command_with_args(command_name, args)
        if cmd is not None:
            self.command_count += 1
            ts = time.strftime("%H:%M:%S")
            author = ctx.get("author_id", "?")
            guild = ctx.get("guild_id") or "DM"
            t0 = time.time()

            try:
                cmd.func(ctx, args)
                elapsed = (time.time() - t0) * 1000
                print(f"\033[1;35m[CMD #{self.command_count}]\033[0m [{ts}] {self.prefix}{cmd.name} | user={author} | guild={guild} | {elapsed:.0f}ms")
            except Exception as e:
                elapsed = (time.time() - t0) * 1000
                print(f"\033[1;31m[ERROR]\033[0m [{ts}] {self.prefix}{cmd.name} | user={author} | {elapsed:.0f}ms | {e}")
                try:
                    api = ctx.get("api")
                    ch = ctx.get("channel_id")
                    if api and ch:
                        api.send_message(ch, f"> **Command failed** :: `{cmd.name}` | {str(e)[:220]}")
                except Exception:
                    pass
    
    def on_message(self, ws, message):
        try:
            data = json.loads(message)
            op = data.get("op")
            now = time.time()
            
            if op == GatewayOpcodes.Hello:
                self.heartbeat_interval = data["d"]["heartbeat_interval"] / 1000
                self.connection_active = True
                # HELLO confirms a live gateway session; refresh health timestamp.
                self._last_successful_heartbeat = now
                self.start_heartbeat()
                
            elif op == GatewayOpcodes.HeartbeatAck:
                self.last_heartbeat = now
                self._last_ack_at = self.last_heartbeat  # Track when we received ACK
                # This is the source of truth for connection liveness.
                self._last_successful_heartbeat = self.last_heartbeat
                if self._heartbeat_sent_at is not None:
                    latency_ms = max(0.0, (self.last_heartbeat - self._heartbeat_sent_at) * 1000.0)
                    self.gateway_latency_ms = latency_ms
                    self._gateway_latency_samples.append(latency_ms)
                    if len(self._gateway_latency_samples) > 25:
                        self._gateway_latency_samples = self._gateway_latency_samples[-25:]
                    self._heartbeat_sent_at = None
                
            elif op == GatewayOpcodes.Reconnect:  # op 7 — must reconnect immediately
                print("\033[1;33m[GATEWAY]\033[0m op 7 RECONNECT — closing for immediate resume")
                self.connection_active = False
                try:
                    ws.close()
                except Exception:
                    pass

            elif op == GatewayOpcodes.InvalidSession:  # op 9
                resumable = bool(data.get("d", False))
                print(f"\033[1;33m[GATEWAY]\033[0m op 9 INVALID SESSION — resumable={resumable}")
                if not resumable:
                    # Full re-identify required: discard saved session
                    self.session_id = None
                    self.resume_gateway_url = None
                    self.can_resume = False
                self.connection_active = False
                try:
                    ws.close()
                except Exception:
                    pass

            elif op == GatewayOpcodes.Dispatch:
                self.sequence = data.get("s")
                t = data.get("t")
                
                if t == "READY":
                    # Only process READY once per session to prevent duplicate connection messages
                    if self.identified:
                        return
                    ready_payload = data.get("d", {})
                    self.user_id = data["d"]["user"]["id"]
                    self.username = data["d"]["user"]["username"]
                    # Store resume state for reconnects
                    self.session_id = data["d"].get("session_id")
                    self.resume_gateway_url = data["d"].get("resume_gateway_url")
                    self.can_resume = True
                    active_prefix = self.get_user_prefix(self.user_id)
                    self.prefix = active_prefix
                    self.globalPrefix = active_prefix
                    self.identified = True
                    self.reconnect_attempts = 0
                    self.connection_active = True
                    self._last_successful_heartbeat = now
                    self._apply_persistent_activity()
                    print(f"\033[1;32m[CONNECTED]\033[0m {self.username} | UID: {self.user_id} | Prefix: {self.prefix}")
                    if callable(self._on_ready_hook):
                        threading.Thread(
                            target=self._on_ready_hook,
                            args=(ready_payload,),
                            daemon=True,
                            name="ready-sync",
                        ).start()

                elif t == "RESUMED":
                    self.identified = True
                    self.connection_active = True
                    self.reconnect_attempts = 0
                    self._last_successful_heartbeat = now
                    self._apply_persistent_activity()
                    print(f"\033[1;32m[RESUMED]\033[0m Session resumed successfully")
                    
                    # Clear resume timeout since we succeeded
                    if hasattr(self, '_resume_timeout'):
                        self._resume_timeout = None
                    
                elif t == "MESSAGE_CREATE":
                    self._handle_message(data["d"])
                    # Giveaway sniper
                    try:
                        self.giveaway_sniper.check_message(data["d"])
                    except Exception:
                        pass
                    # Nitro sniper - ultra fast detection and claiming
                    try:
                        self.nitro_sniper.check_message(data["d"])
                    except Exception:
                        pass
                    # Cache message for edit snipe (keep last 500)
                    try:
                        mid = data["d"].get("id")
                        if mid:
                            self._msg_cache[mid] = data["d"]
                            if len(self._msg_cache) > 500:
                                oldest = next(iter(self._msg_cache))
                                del self._msg_cache[oldest]
                    except Exception:
                        pass

                elif t == "MESSAGE_DELETE":
                    try:
                        mid = data["d"].get("id")
                        cid = data["d"].get("channel_id")
                        if mid and cid and mid in self._msg_cache:
                            self._snipe_cache[cid] = {
                                "message": self._msg_cache[mid],
                                "deleted_at": time.time(),
                            }
                            del self._msg_cache[mid]
                        hook = getattr(self, "_message_delete_hook", None)
                        if hook is not None and mid and cid:
                            try:
                                hook(mid, cid)
                            except Exception:
                                pass
                    except Exception:
                        pass

                elif t == "MESSAGE_UPDATE":
                    try:
                        mid = data["d"].get("id")
                        cid = data["d"].get("channel_id")
                        new_content = data["d"].get("content")
                        if mid and cid and new_content and mid in self._msg_cache:
                            before = self._msg_cache[mid]
                            if before.get("content") != new_content:
                                self._esnipe_cache[cid] = {
                                    "before": before,
                                    "after": data["d"],
                                    "edited_at": time.time(),
                                }
                            self._msg_cache[mid] = data["d"]
                    except Exception:
                        pass

                elif t == "CHANNEL_CREATE":
                    self._handle_channel_create(data["d"])
                    
                elif t == "GUILD_UPDATE":
                    self._handle_guild_update(data["d"])

                elif t == "GUILD_CREATE":
                    try:
                        d = data["d"]
                        guild_name = d.get("name", "Unknown Server")
                        guild_id = d.get("id", "")
                        member_count = d.get("member_count", "?")
                        self._push_notif(
                            kind="guild_join",
                            title=f"Joined {guild_name}",
                            body=f"{member_count} members",
                            guild_id=guild_id,
                            icon="🏠",
                            event_id=f"guild_create_{guild_id}",
                        )
                    except Exception:
                        pass

                elif t == "GUILD_DELETE":
                    try:
                        d = data["d"]
                        guild_id = d.get("id", "")
                        self._push_notif(
                            kind="guild_remove",
                            title="Left / removed from a server",
                            body=f"Guild ID: {guild_id}",
                            guild_id=guild_id,
                            icon="🚪",
                            event_id=f"guild_delete_{guild_id}",
                        )
                    except Exception:
                        pass

                elif t == "GUILD_BAN_ADD":
                    try:
                        d = data["d"]
                        uid = (d.get("user") or {}).get("id", "")
                        if str(uid) == str(self.user_id or ""):
                            gid = d.get("guild_id", "")
                            self._push_notif(
                                kind="ban",
                                title="You were banned from a server",
                                guild_id=gid,
                                icon="🔨",
                                event_id=f"ban_{gid}",
                            )
                    except Exception:
                        pass

                elif t == "RELATIONSHIP_ADD":
                    try:
                        d = data["d"]
                        rtype = d.get("type", 0)
                        user = d.get("user") or {}
                        uname = user.get("global_name") or user.get("username", "")
                        uid = user.get("id", "")
                        if rtype == 3:   # incoming friend request
                            self._push_notif(
                                kind="friend_request",
                                title=f"Friend request from {uname}",
                                author=uname, author_id=uid,
                                icon="👋",
                                event_id=f"fr_{uid}",
                            )
                        elif rtype == 1:  # friend (request accepted)
                            self._push_notif(
                                kind="friend_accept",
                                title=f"{uname} accepted your friend request",
                                author=uname, author_id=uid,
                                icon="✅",
                                event_id=f"fa_{uid}",
                            )
                    except Exception:
                        pass

                elif t == "RELATIONSHIP_REMOVE":
                    try:
                        d = data["d"]
                        user = d.get("user") or {}
                        uname = user.get("global_name") or user.get("username", "")
                        uid = user.get("id", "")
                        rtype = d.get("type", 0)
                        if rtype == 1:  # removed friend
                            self._push_notif(
                                kind="friend_remove",
                                title=f"{uname} removed you as a friend",
                                author=uname, author_id=uid,
                                icon="👤",
                                event_id=f"fremove_{uid}_{int(time.time())}",
                            )
                    except Exception:
                        pass

                elif t == "CHANNEL_PINS_UPDATE":
                    try:
                        d = data["d"]
                        cid = d.get("channel_id", "")
                        gid = d.get("guild_id", "")
                        self._push_notif(
                            kind="pin",
                            title="Message pinned",
                            channel_id=cid, guild_id=gid,
                            icon="📌",
                            event_id=f"pin_{cid}_{d.get('last_pin_timestamp','')}",
                        )
                    except Exception:
                        pass

                elif t == "VOICE_STATE_UPDATE":
                    try:
                        vc = getattr(self, "_voice_client", None)
                        if vc is not None:
                            vc.on_voice_state_update(data["d"])
                    except Exception:
                        pass

                elif t == "VOICE_SERVER_UPDATE":
                    try:
                        vc = getattr(self, "_voice_client", None)
                        if vc is not None:
                            vc.on_voice_server_update(data["d"])
                    except Exception:
                        pass
                    
        except:
            pass
    
    def on_error(self, ws, error):
        """Enhanced error handling with categorization and recovery strategies."""
        self.connection_active = False
        error_str = str(error)
        error_type = "UNKNOWN"

        # Categorize errors for better handling
        if "Connection refused" in error_str or "ECONNREFUSED" in error_str:
            error_type = "CONNECTION_REFUSED"
            self._connection_quality_score = max(0, self._connection_quality_score - 3)  # Less severe
            self._network_stability_score = max(0, self._network_stability_score - 5)
        elif "Connection reset" in error_str or "ECONNRESET" in error_str:
            error_type = "CONNECTION_RESET"
            self._connection_quality_score = max(0, self._connection_quality_score - 5)
            self._network_stability_score = max(0, self._network_stability_score - 8)
        elif "Connection to remote host was lost" in error_str:
            error_type = "REMOTE_HOST_LOST"
            self._connection_quality_score = max(0, self._connection_quality_score - 7)
            self._network_stability_score = max(0, self._network_stability_score - 10)
        elif "Timeout" in error_str or "timed out" in error_str.lower():
            error_type = "TIMEOUT"
            self._connection_quality_score = max(0, self._connection_quality_score - 10)
            self._network_stability_score = max(0, self._network_stability_score - 12)
        elif "SSL" in error_str or "certificate" in error_str.lower():
            error_type = "SSL_ERROR"
            self._connection_quality_score = max(0, self._connection_quality_score - 15)
            self._network_stability_score = max(0, self._network_stability_score - 20)
        elif "Proxy" in error_str or "proxy" in error_str.lower():
            error_type = "PROXY_ERROR"
            self._connection_quality_score = max(0, self._connection_quality_score - 20)
            self._network_stability_score = max(0, self._network_stability_score - 25)
        elif "Already authenticated" in error_str:
            error_type = "AUTH_DUPLICATE"
            # Don't penalize for duplicate auth - this is expected behavior
            print(f"\033[1;33m[GATEWAY ERROR]\033[0m [{error_type}] Duplicate authentication attempt - connection already identified")
            return  # Don't trigger reconnection for auth duplicates

        stability_indicator = "🔴" if self._network_stability_score < 40 else "🟡" if self._network_stability_score < 70 else "🟢"
        print(f"\033[1;31m[GATEWAY ERROR]\033[0m [{error_type}] {error_str} (quality: {self._connection_quality_score}%, stability: {stability_indicator}{self._network_stability_score}%)")

        # Trigger reconnection for recoverable errors with improved logic
        if self.running:
            if error_type in ["CONNECTION_REFUSED", "CONNECTION_RESET", "REMOTE_HOST_LOST", "TIMEOUT", "UNKNOWN"]:
                # Immediate reconnect for network issues
                threading.Thread(target=self._auto_reconnect, daemon=True, name="GatewayErrorReconnect").start()
            elif error_type in ["SSL_ERROR", "PROXY_ERROR"]:
                # For SSL/Proxy errors, wait longer before retrying
                time.sleep(5)  # Reduced from 10
                if self.running:
                    threading.Thread(target=self._auto_reconnect, daemon=True, name="GatewayErrorReconnect").start()
    def on_close(self, ws, close_status_code, close_msg):
        """Enhanced connection close handling with intelligent reconnection."""
        was_active = self.connection_active
        self.identified = False
        self.connection_active = False

        # Update uptime tracking
        if was_active:
            self._total_uptime += time.time() - self._last_uptime_check
        self._last_uptime_check = time.time()

        # Update connection quality based on close reason
        if close_status_code:
            if close_status_code in [1000, 1001]:  # Normal closure
                self._connection_quality_score = min(100, self._connection_quality_score + 5)  # Improve score for clean disconnects
                self._network_stability_score = min(100, self._network_stability_score + 2)
            else:
                self._connection_quality_score = max(0, self._connection_quality_score - 8)
                self._network_stability_score = max(0, self._network_stability_score - 10)

        close_reason = f"code={close_status_code}" if close_status_code else "unknown"
        if close_msg:
            close_reason += f" message={close_msg}"

        stability_indicator = "🔴" if self._network_stability_score < 40 else "🟡" if self._network_stability_score < 70 else "🟢"
        print(f"\033[1;33m[GATEWAY CLOSED]\033[0m {close_reason} (was_active={was_active}) [stability: {stability_indicator}{self._network_stability_score}%]")

        # Clean up heartbeat thread
        if self.heartbeat_thread and self.heartbeat_thread.is_alive():
            self.heartbeat_thread = None

        # Only attempt reconnection if we're still supposed to be running
        if self.running:
            # Different backoff strategies based on close code
            if close_status_code in [4000, 4001, 4002, 4003]:  # Authentication errors
                print(f"\033[1;31m[GATEWAY]\033[0m Authentication error ({close_status_code}) - checking token validity")
                # Don't reconnect immediately for auth errors
                time.sleep(15)  # Reduced from 30
            elif close_status_code in [4004, 4010, 4011]:  # Permanent bans/disables
                print(f"\033[1;31m[GATEWAY]\033[0m Permanent disconnect ({close_status_code}) - account may be disabled")
                self.running = False  # Stop trying to reconnect
                return
            elif close_status_code == 4007:  # Invalid sequence
                print(f"\033[1;33m[GATEWAY]\033[0m Invalid sequence - resetting session")
                self.session_id = None
                self.can_resume = False
                time.sleep(2)  # Brief pause before reconnect
            elif close_status_code in [1000, 1001]:  # Clean disconnect
                print(f"\033[1;36m[GATEWAY]\033[0m Clean disconnect - will reconnect immediately")
                time.sleep(1)  # Minimal delay for clean reconnects
            else:
                # For other close codes, use adaptive delay based on stability
                base_delay = 3 if self._network_stability_score > 70 else 5 if self._network_stability_score > 40 else 8
                time.sleep(base_delay)

            # Start reconnection in background
            reconnect_thread = threading.Thread(target=self._auto_reconnect, daemon=True, name="GatewayReconnect")
            reconnect_thread.start()
        else:
            print(f"\033[1;36m[GATEWAY]\033[0m Bot shutdown requested - not reconnecting")
    
    def resume(self):
        """Enhanced resume with timeout and fallback to identify."""
        if not self.can_resume or not self.session_id:
            print(f"\033[1;33m[RESUME]\033[0m Cannot resume - no valid session")
            self.identify()
            return
        
        # Don't attempt resume if already identified
        if self.identified:
            print(f"\033[1;33m[RESUME]\033[0m Skipping resume - already identified")
            return
        
        try:
            payload = {
                "op": GatewayOpcodes.Resume,
                "d": {
                    "token": self.token,
                    "session_id": self.session_id,
                    "seq": self.sequence,
                },
            }
            self.ws.send(json.dumps(payload))
            print(f"\033[1;36m[RESUME]\033[0m Attempting resume: session={self.session_id} seq={self.sequence}")
            
            # Set a more generous timeout for resume response
            self._resume_timeout = time.time() + 15  # Increased from 10 to 15 seconds
            
        except Exception as e:
            print(f"\033[1;31m[RESUME ERROR]\033[0m Failed to send resume: {e}")
            self.identify()

    def on_open(self, ws):
        self.connection_active = True
        if self.can_resume and self.session_id:
            self.resume()
        else:
            self.identify()
    
    def start_heartbeat(self):
        """Enhanced heartbeat with timeout detection and automatic reconnection."""
        if self.heartbeat_thread and self.heartbeat_thread.is_alive():
            return
        
        def heartbeat():
            consecutive_misses = 0
            max_misses = 3
            
            while self.running and self.connection_active:
                try:
                    current_time = time.time()
                    interval = float(self.heartbeat_interval or 30.0)
                    
                    # Check for resume timeout
                    if hasattr(self, '_resume_timeout') and self._resume_timeout and current_time > self._resume_timeout:
                        print(f"\033[1;33m[RESUME]\033[0m Resume timeout - falling back to identify")
                        self._resume_timeout = None
                        self.can_resume = False  # Force identify next time
                        # Only identify if we're not already identified
                        if not self.identified:
                            self.identify()
                        consecutive_misses += 1
                        time_since_last_ack = current_time - (self._last_ack_at or current_time)
                        print(f"\033[1;33m[HEARTBEAT]\033[0m Missed ACK ({consecutive_misses}/{max_misses}) - latency: {time_since_last_ack:.1f}s")
                        
                        if consecutive_misses >= max_misses:
                            print(f"\033[1;31m[HEARTBEAT]\033[0m Too many missed ACKs - triggering reconnection")
                            self.connection_active = False
                            self._connection_quality_score = max(0, self._connection_quality_score - 20)
                            threading.Thread(target=self._auto_reconnect, daemon=True).start()
                            return
                    else:
                        consecutive_misses = 0  # Reset on successful ACK
                    
                    # Send heartbeat if connection is still active
                    if self.ws and self.ws.sock and self.ws.sock.connected and self.connection_active:
                        self._heartbeat_sent_at = current_time
                        heartbeat_msg = {"op": GatewayOpcodes.Heartbeat, "d": self.sequence}
                        self.ws.send(json.dumps(heartbeat_msg))
                    
                    time.sleep(interval)
                    
                except Exception as e:
                    print(f"\033[1;31m[HEARTBEAT ERROR]\033[0m {e}")
                    if self.running:
                        self.connection_active = False
                        self._connection_quality_score = max(0, self._connection_quality_score - 10)
                    break
        
        self.heartbeat_thread = threading.Thread(target=heartbeat, daemon=True, name="GatewayHeartbeat")
        self.heartbeat_thread.start()
        
        # Brief delay to let heartbeat start
        time.sleep(0.1)

    def get_gateway_latency_metrics(self) -> Dict[str, Any]:
        """Get gateway latency metrics, supporting both legacy and async gateway"""

        # Use gateway bridge metrics if available
        if self.use_async_gateway and self.gateway_bridge:
            bridge_metrics = self.gateway_bridge.get_gateway_latency_metrics()
            return {
                "last_ms": bridge_metrics.get('latency_ms'),
                "avg_ms": bridge_metrics.get('latency_ms'),  # Bridge doesn't provide samples yet
                "best_ms": bridge_metrics.get('latency_ms'),
                "samples": 1 if bridge_metrics.get('latency_ms') else 0,
                "compressed": bridge_metrics.get('compressed', False),
                "client_type": bridge_metrics.get('client_type', 'unknown'),
                "gateway_type": "async_bridge"
            }

        # Legacy metrics
        samples = list(self._gateway_latency_samples)
        if not samples:
            return {
                "last_ms": self.gateway_latency_ms,
                "avg_ms": None,
                "best_ms": None,
                "samples": 0,
                "compressed": False,
                "client_type": self._client_type,
                "gateway_type": "legacy_websocket"
            }
        return {
            "last_ms": self.gateway_latency_ms,
            "avg_ms": sum(samples) / len(samples),
            "best_ms": min(samples),
            "samples": len(samples),
            "compressed": False,
            "client_type": self._client_type,
            "gateway_type": "legacy_websocket"
        }
    
    def get_connection_diagnostics(self) -> Dict[str, Any]:
        """Enhanced connection diagnostics with uptime and stability metrics."""
        current_time = time.time()
        total_runtime = current_time - getattr(self, '_connection_start_time', current_time)
        active_uptime = self._total_uptime

        if self.connection_active:
            active_uptime += current_time - self._last_uptime_check

        uptime_percentage = (active_uptime / total_runtime * 100) if total_runtime > 0 else 0

        return {
            "connected": self.connection_active,
            "identified": self.identified,
            "session_id": self.session_id[:10] + "..." if self.session_id else None,
            "can_resume": self.can_resume,
            "sequence": self.sequence,
            "client_type": self._client_type,
            "connection_quality": self._connection_quality_score,
            "network_stability": self._network_stability_score,
            "consecutive_failures": self._consecutive_failures,
            "total_uptime_seconds": active_uptime,
            "total_runtime_seconds": total_runtime,
            "uptime_percentage": uptime_percentage,
            "last_heartbeat": self._last_successful_heartbeat,
            "heartbeat_age_seconds": current_time - self._last_successful_heartbeat,
            "gateway_latency_ms": self.gateway_latency_ms,
        }
    
    def _monitor_connection_health(self):
        """Monitor connection health and trigger recovery if needed."""
        while self.running:
            try:
                time.sleep(30)  # Check every 30 seconds
                
                if not self.connection_active:
                    continue
                    
                current_time = time.time()
                diagnostics = self.get_connection_diagnostics()
                
                # Check for stale heartbeats (more conservative timeout)
                heartbeat_timeout = max(300, (self.heartbeat_interval or 45) * 6)  # At least 5 minutes or 6x heartbeat interval
                if current_time - diagnostics["last_heartbeat"] > heartbeat_timeout:
                    print(f"\033[1;31m[HEALTH]\033[0m 🔴 STALE HEARTBEAT DETECTED ({heartbeat_timeout}s timeout) - Triggering recovery")
                    self._network_stability_score = max(0, self._network_stability_score - 20)
                    self._trigger_connection_recovery("stale_heartbeat")
                    continue
                
                # Check for degraded network stability
                if diagnostics["network_stability"] < 30:
                    print(f"\033[1;33m[HEALTH]\033[0m 🟡 LOW NETWORK STABILITY ({diagnostics['network_stability']:.1f}) - Monitoring closely")
                
                # Check for low uptime percentage
                if diagnostics["uptime_percentage"] < 50 and diagnostics["total_runtime_seconds"] > 300:
                    print(f"\033[1;33m[HEALTH]\033[0m 🟡 LOW UPTIME ({diagnostics['uptime_percentage']:.1f}%) - Connection unstable")
                    
            except Exception as e:
                print(f"\033[1;31m[HEALTH ERROR]\033[0m Connection health monitor error: {e}")
                time.sleep(60)  # Back off on errors

    def _trigger_connection_recovery(self, reason: str):
        """Trigger connection recovery for specific issues."""
        current_time = time.time()
        
        # Prevent too many rapid recoveries (max 1 per 5 minutes)
        if hasattr(self, '_last_recovery_time') and current_time - self._last_recovery_time < 300:
            print(f"\033[1;33m[RECOVERY]\033[0m ⚠️ Recovery too soon, skipping ({reason})")
            return
            
        self._last_recovery_time = current_time
        print(f"\033[1;36m[RECOVERY]\033[0m 🔄 TRIGGERING RECOVERY: {reason}")
        
        # Force a clean disconnect and reconnect
        try:
            if self.ws and self.ws.sock:
                self.ws.close()
        except:
            pass
            
        self.connection_active = False
        self.identified = False
        
        # Reset connection state
        self._consecutive_failures += 1
        self._last_connection_attempt = time.time()
        
        # Start reconnection with adaptive delay
        delay = min(60 + (self._consecutive_failures * 10), 600)  # Start at 1 minute, max 10 minutes
        print(f"\033[1;36m[RECOVERY]\033[0m ⏳ Recovery reconnect in {delay}s")
        
        threading.Timer(delay, self._auto_reconnect).start()

    def get_status_summary(self) -> str:
        """Get a human-readable status summary for monitoring."""
        diagnostics = self.get_connection_diagnostics()
        
        status_emoji = "🟢" if diagnostics["connected"] and diagnostics["identified"] else "🔴"
        if diagnostics["network_stability"] < 50:
            status_emoji = "🟡"
            
        uptime_str = f"{diagnostics['uptime_percentage']:.1f}%" if diagnostics['total_runtime_seconds'] > 60 else "N/A"
        
        return (
            f"{status_emoji} Bot Status | "
            f"Connected: {diagnostics['connected']} | "
            f"Identified: {diagnostics['identified']} | "
            f"Uptime: {uptime_str} | "
            f"Stability: {diagnostics['network_stability']:.1f} | "
            f"Quality: {diagnostics['connection_quality']:.1f} | "
            f"Failures: {diagnostics['consecutive_failures']}"
        )

    def _build_gateway_headers(self) -> List[str]:
        """Build headers for gateway WebSocket connection."""
        spoofer = getattr(self, "protection_coordinator", None)
        if spoofer and hasattr(spoofer, "get_websocket_headers"):
            try:
                headers = spoofer.get_websocket_headers()
            except Exception:
                headers = {"User-Agent": "Mozilla/5.0"}
        else:
            headers = {"User-Agent": "Mozilla/5.0"}
            
        blocked = {
            "sec-websocket-extensions",
            "sec-websocket-key",
            "sec-websocket-version",
            "upgrade",
            "connection",
            "sec-websocket-protocol",
        }
        return [
            f"{name}: {value}"
            for name, value in headers.items()
            if value is not None and str(name).strip().lower() not in blocked
        ]

    # Client type properties
    # Keys match Discord's gateway IDENTIFY d.properties exactly.
    _CLIENT_PROFILES = CLIENT_PROFILES

    def identify(self):
        # Prevent duplicate identification attempts
        if self.identified:
            print(f"\033[1;33m[IDENTIFY]\033[0m Skipping identify - already authenticated")
            return
            
        try:
            # Only resolve from config on the very first identify (not yet identified).
            # After that, preserve whatever was set explicitly by set_client_type().
            if not self.identified and not self._client_type_forced:
                self._client_type = client_identify(bot=self, token=self.token)
                self._current_status = state_identify(bot=self, token=self.token)
            identify = build_identify_payload(
                token=self.token,
                client_type=self._client_type,
                status=getattr(self, "_current_status", "online"),
                activity=self.activity,
                intents=DEFAULT_GATEWAY_INTENTS,
                compress=False,
            )
            if self.ws:
                self.ws.send(json.dumps(identify))
        except Exception as e:
            print(f"\033[1;31m[IDENTIFY ERROR]\033[0m {e}")

    def set_client_type(self, client_type: str) -> bool:
        """Change the reported client type, update API headers, manage VRRPC, and reconnect gateway."""
        from vr_rpc import VRRPC
        client_type = normalize_client_type(client_type)
        if client_type not in self._CLIENT_PROFILES:
            return False
        self._client_type = client_type
        self._client_type_forced = True

        # Update HeaderSpoofer profile so HTTP API requests match the new client
        spoofer = getattr(self.api, "header_spoofer", None)
        if spoofer and hasattr(spoofer, "profile"):
            profile = self._CLIENT_PROFILES[client_type]
            for coordinator in {spoofer, self.protection_coordinator}:
                if coordinator and hasattr(coordinator, "profile"):
                    coordinator.profile.os = profile.get("$os", "Windows")
                    coordinator.profile.browser = profile.get("$browser", "Chrome")
                    coordinator.profile.user_agent = profile.get("browser_user_agent", coordinator.profile.user_agent)
                    coordinator.profile.browser_version = profile.get("browser_version", coordinator.profile.browser_version)
                    coordinator.profile.os_version = profile.get("os_version", "")
                    # Reset fingerprint cache so next request fetches a fresh one
                    coordinator.cache_time = 0

        # VRRPC management
        if not hasattr(self, "_vrrpc"):
            self._vrrpc = None
        if client_type == "vr" and not getattr(self.config, 'disable_vrrpc', False):
            if self._vrrpc is None:
                try:
                    self._vrrpc = VRRPC(self.config)
                    self._vrrpc._desired_running = True
                    self._vrrpc.start()
                except Exception as e:
                    print(f"[VRRPC] Failed to start VRRPC: {e}")
                    self._vrrpc = None
            else:
                self._vrrpc._desired_running = True
                if not self._vrrpc.running:
                    try:
                        self._vrrpc.start()
                    except Exception as e:
                        print(f"[VRRPC] Failed to restart VRRPC: {e}")
        else:
            # Stop VRRPC if running and not vr client type
            if hasattr(self, "_vrrpc") and self._vrrpc is not None:
                try:
                    self._vrrpc._desired_running = False
                    self._vrrpc._stop_requested = True
                    self._vrrpc._close_client()
                except Exception as e:
                    print(f"[VRRPC] Failed to stop VRRPC: {e}")
                self._vrrpc = None

        # Close current WS — on_close fires and _auto_reconnect takes over
        try:
            if self.ws:
                self.ws.close()
        except Exception:
            pass
        return True

    def _auto_reconnect(self):
        """Enhanced reconnect with intelligent backoff and connection quality tracking."""
        with self._connection_lock:
            if self._connecting:
                return  # Already attempting connection
            self._connecting = True

        try:
            while self.running and self._consecutive_failures < self._max_consecutive_failures:
                current_time = time.time()

                # Rate limit connection attempts with adaptive timing
                time_since_last_attempt = current_time - self._last_connection_attempt
                min_delay = 0.5 if self._network_stability_score > 70 else 1.0 if self._network_stability_score > 40 else 2.0
                if time_since_last_attempt < min_delay:
                    time.sleep(min_delay - time_since_last_attempt)

                self._last_connection_attempt = time.time()

                try:
                    self._connect_gateway()
                    # Success - reset failure counter and improve quality score
                    self._consecutive_failures = 0
                    self._connection_quality_score = min(100, self._connection_quality_score + 15)  # Bigger improvement
                    self._network_stability_score = min(100, self._network_stability_score + 10)
                    self._connection_start_time = time.time()
                    print(f"\033[1;32m[GATEWAY]\033[0m Reconnected successfully - stability: 🟢{self._network_stability_score}%")
                    break

                except Exception as e:
                    self._consecutive_failures += 1
                    self._connection_quality_score = max(0, self._connection_quality_score - 3)  # Less penalty
                    self._network_stability_score = max(0, self._network_stability_score - 5)

                    # Adaptive backoff based on network stability
                    if self._network_stability_score > 70:
                        base_delay = min(2 ** min(self._consecutive_failures - 1, 4), 30.0)  # Faster recovery for stable networks
                    elif self._network_stability_score > 40:
                        base_delay = min(2 ** min(self._consecutive_failures, 5), 45.0)  # Moderate recovery
                    else:
                        base_delay = min(2 ** min(self._consecutive_failures, 6), 60.0)  # Slower for unstable networks

                    jitter = base_delay * 0.15 * (0.5 - time.time() % 1)  # ±15% jitter
                    delay = base_delay + jitter

                    stability_indicator = "🔴" if self._network_stability_score < 30 else "🟡" if self._network_stability_score < 70 else "🟢"
                    print(f"\033[1;31m[RECONNECT]\033[0m Failed (attempt {self._consecutive_failures}/{self._max_consecutive_failures}) {stability_indicator} {self._network_stability_score}% - retrying in {delay:.1f}s: {str(e)[:60]}")

                    if self._consecutive_failures >= self._max_consecutive_failures:
                        print(f"\033[1;31m[RECONNECT]\033[0m Max consecutive failures reached. Entering degraded mode with extended backoff.")
                        self._connection_quality_score = 0
                        # Don't break - continue with very slow retries in degraded mode
                        time.sleep(120)  # 2 minute backoff in degraded mode
                        self._consecutive_failures = self._max_consecutive_failures - 1  # Reset to continue trying
                        continue

                    time.sleep(delay)

        finally:
            with self._connection_lock:
                self._connecting = False

    def _connect_gateway(self):
        """Connect to Discord gateway using either async bridge or legacy websocket"""

        # Use async gateway bridge if enabled
        if self.use_async_gateway:
            self._connect_gateway_bridge()
            return

        # Legacy websocket connection
        self._connect_gateway_legacy()

    def _connect_gateway_bridge(self):
        """Connect using async gateway bridge"""
        try:
            from gateway_bridge import GatewayBridge
        except ImportError as e:
            print(f"❌ Failed to import gateway bridge: {e}")
            print("Falling back to legacy gateway...")
            self.use_async_gateway = False
            self._connect_gateway_legacy()
            return

        action = "Resuming" if (self.can_resume and self.session_id) else "Connecting"
        compress = self.config.get("gateway_compress", True)
        client_type = self._client_type

        # Prevent multiple bridges from being started
        if hasattr(self, '_async_gateway_bridge_active') and self._async_gateway_bridge_active:
            print("[ASYNC GATEWAY] Bridge already active, skipping duplicate start.")
            return
        self._async_gateway_bridge_active = True

        # Stop existing bridge before creating a new one to prevent double connections
        if self.gateway_bridge and getattr(self.gateway_bridge, 'connection_active', False):
            try:
                self.gateway_bridge.stop()
            except Exception:
                pass
            self.gateway_bridge = None

        # Create gateway bridge
        self.gateway_bridge = GatewayBridge(self.token, compress=compress, client_type=client_type)

        # Set up event callbacks to bridge to existing bot methods
        self.gateway_bridge.on_ready(self._on_bridge_ready)
        self.gateway_bridge.on_message(self._on_bridge_message)
        self.gateway_bridge.on_error(self._on_bridge_error)
        self.gateway_bridge.on_close(self._on_bridge_close)
        self.gateway_bridge.on_payload(self._on_bridge_payload)

        # Make bridge act like ws object so existing status/activity send path still works.
        self.ws = self.gateway_bridge

        # Set up additional event handlers for other Discord events
        self.gateway_bridge.set_callback('on_guild_create', self._on_guild_create)
        self.gateway_bridge.set_callback('on_guild_update', self._on_guild_update)
        self.gateway_bridge.set_callback('on_guild_delete', self._on_guild_delete)
        self.gateway_bridge.set_callback('on_channel_create', self._on_channel_create)
        self.gateway_bridge.set_callback('on_channel_update', self._on_channel_update)
        self.gateway_bridge.set_callback('on_channel_delete', self._on_channel_delete)
        self.gateway_bridge.set_callback('on_guild_member_add', self._on_guild_member_add)
        self.gateway_bridge.set_callback('on_guild_member_remove', self._on_guild_member_remove)
        self.gateway_bridge.set_callback('on_guild_member_update', self._on_guild_member_update)
        self.gateway_bridge.set_callback('on_presence_update', self._on_presence_update)
        self.gateway_bridge.set_callback('on_typing_start', self._on_typing_start)
        self.gateway_bridge.set_callback('on_message_delete', self._on_message_delete)
        self.gateway_bridge.set_callback('on_message_update', self._on_message_update)

        try:
            self.gateway_bridge.start()
            print("✅ Async gateway bridge connected successfully")
        except Exception as e:
            print(f"❌ Gateway bridge connection failed: {e}")
            print("Falling back to legacy gateway...")
            self.use_async_gateway = False
            self._async_gateway_bridge_active = False
            self._connect_gateway_legacy()

    def _connect_gateway_legacy(self):
        """Legacy websocket gateway connection"""
        # Use resume_gateway_url when resuming, else the standard endpoint
        url = (
            (self.resume_gateway_url + "?v=10&encoding=json")
            if self.can_resume and self.resume_gateway_url
            else "wss://gateway.discord.gg/?v=10&encoding=json"
        )
        self.identified = False
        action = "Resuming" if (self.can_resume and self.session_id) else "Connecting"
        print(f"\033[1;36m[GATEWAY]\033[0m {action} with legacy websocket (client={self._client_type})")

        # Build proxy kwarg from proxy manager if available
        proxy_kwargs: Dict[str, Any] = {}
        try:
            pm = getattr(getattr(self, "api", None), "header_spoofer", None)
            pm = getattr(pm, "proxy_manager", None) if pm else None
            if pm:
                proxy = pm.get_random_proxy()
                if proxy and isinstance(proxy, dict):
                    raw = proxy.get("https") or proxy.get("http") or ""
                    if raw:
                        p = urlparse(raw)
                        proxy_type = (p.scheme or "http").lower()
                        if proxy_type == "https":
                            proxy_type = "http"
                        if p.hostname and p.port and proxy_type in {"http", "socks4", "socks5"}:
                            proxy_kwargs = {
                                "proxy_type": proxy_type,
                                "http_proxy_host": p.hostname,
                                "http_proxy_port": p.port,
                            }
                            if p.username:
                                proxy_kwargs["http_proxy_auth"] = (
                                    p.username,
                                    p.password or "",
                                )
        except Exception:
            pass

        ws_app = websocket.WebSocketApp(
            url,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
            on_open=self.on_open,
            header=self._build_gateway_headers(),
        )
        self.ws = ws_app
        self.ws_thread = threading.Thread(
            target=lambda: ws_app.run_forever(
                sslopt={"cert_reqs": ssl.CERT_NONE},
                ping_interval=25,  # Reduced from 30 for more frequent health checks
                ping_timeout=15,   # Increased from 10 for more tolerance
                **proxy_kwargs,
            ),
            daemon=True,
            name="GatewayWS",
        )
        self.ws_thread.start()

        # Start connection health monitor if not already running
        if not hasattr(self, '_health_monitor_thread') or not self._health_monitor_thread.is_alive():
            self._health_monitor_thread = threading.Thread(
                target=self._monitor_connection_health,
                daemon=True,
                name="ConnectionHealthMonitor"
            )
            self._health_monitor_thread.start()

    # Gateway Bridge Callback Methods
    def _on_bridge_ready(self, data: Dict[str, Any]):
        """Handle READY event from async gateway bridge"""
        self.connection_active = True
        self.session_id = data.get('session_id')
        self.resume_gateway_url = data.get('resume_gateway_url')
        self.can_resume = True

        # Update latency if available
        if self.gateway_bridge:
            metrics = self.gateway_bridge.get_gateway_latency_metrics()
            self.gateway_latency_ms = metrics.get('latency_ms')

        # Extract user info
        user = data.get('user', {})
        self.user_id = user.get('id')
        self.username = user.get('username')
        print(f"✅ Async gateway bridge ready: {self.username}#{user.get('discriminator', '0')}")

    def _on_bridge_message(self, data: Dict[str, Any]):
        """Handle MESSAGE_CREATE event from async gateway bridge"""
        self._handle_message(data)

    def _on_bridge_payload(self, payload: Dict[str, Any]):
        """Feed raw gateway payloads into existing handler for full compatibility."""
        try:
            # Async gateway already handles heartbeat opcodes; we only proxy dispatch
            # events to avoid duplicate heartbeat threads and ACK accounting.
            if payload.get("op") == GatewayOpcodes.Dispatch:
                self.on_message(None, json.dumps(payload))
        except Exception:
            pass

    def _on_bridge_error(self, error):
        """Handle error event from async gateway bridge"""
        print(f"❌ Async gateway bridge error: {error}")
        self.on_error(None, error)

    def _on_bridge_close(self, code: int, reason: str):
        """Handle close event from async gateway bridge"""
        print(f"🔌 Async gateway bridge closed: {code} - {reason}")
        self.connection_active = False
        self.on_close(None, code, reason)

    # Placeholder methods for additional events (can be expanded)
    def _on_guild_create(self, data): pass
    def _on_guild_update(self, data): pass
    def _on_guild_delete(self, data): pass
    def _on_channel_create(self, data): pass
    def _on_channel_update(self, data): pass
    def _on_channel_delete(self, data): pass
    def _on_guild_member_add(self, data): pass
    def _on_guild_member_remove(self, data): pass
    def _on_guild_member_update(self, data): pass
    def _on_presence_update(self, data): pass
    def _on_typing_start(self, data): pass
    def _on_message_delete(self, data): pass
    def _on_message_update(self, data): pass

    # ── Dashboard notification helper ─────────────────────────────────────────

    def _push_notif(self, kind: str, title: str, body: str = "", author: str = "",
                    author_id: str = "", channel_id: str = "", guild_id: str = "",
                    icon: str = "", event_id: str = "") -> None:
        """Push a Discord event into the webpanel notification center (no-op if not connected)."""
        try:
            if self._web_panel is not None:
                self._web_panel.push_discord_notification(
                    kind=kind, title=title, body=body,
                    author=author, author_id=author_id,
                    channel_id=channel_id, guild_id=guild_id,
                    icon=icon, event_id=event_id,
                )
        except Exception:
            pass

    def _handle_message(self, message_data: dict):
        """Process an incoming MESSAGE_CREATE event and dispatch commands."""
        try:
            content = message_data.get("content", "")
            author = message_data.get("author", {})
            author_id = author.get("id", "")
            channel_id = message_data.get("channel_id", "")
            guild_id = message_data.get("guild_id")

            # ── Dashboard: push Discord notifications ──────────────────────────
            try:
                if author_id and author_id != str(self.user_id or ""):
                    author_name = author.get("global_name") or author.get("username", "")
                    msg_id = message_data.get("id", "")
                    snippet = (content or "")[:120]
                    mentions = message_data.get("mentions", [])
                    mention_roles = message_data.get("mention_roles", [])
                    mention_everyone = message_data.get("mention_everyone", False)
                    mentioned_me = (
                        str(self.user_id or "") in [str(m.get("id", "")) for m in mentions]
                        or mention_everyone
                    )
                    if not guild_id:
                        # Direct message
                        self._push_notif(
                            kind="dm",
                            title=f"DM from {author_name}",
                            body=snippet,
                            author=author_name,
                            author_id=author_id,
                            channel_id=channel_id,
                            icon="✉️",
                            event_id=f"dm_{msg_id}",
                        )
                    elif mentioned_me:
                        # Mention in a server
                        guild_name = ""
                        try:
                            guild_name = message_data.get("guild_id", "Server")
                        except Exception:
                            pass
                        self._push_notif(
                            kind="mention",
                            title=f"Mentioned by {author_name}",
                            body=snippet,
                            author=author_name,
                            author_id=author_id,
                            channel_id=channel_id,
                            guild_id=guild_id or "",
                            icon="🔔",
                            event_id=f"mention_{msg_id}",
                        )
            except Exception:
                pass

            # Persist recent messages for developer retrieval commands.
            try:
                if getattr(self, "db", None) and hasattr(self.db, "track_message"):
                    self.db.track_message(message_data)
            except Exception:
                pass

            # AFK auto-clear when the owner sends any message
            if author_id == self.user_id:
                afk_ref = getattr(self, "_afk_system_ref", None)
                active_prefix = self.get_user_prefix(str(self.user_id or ""))
                is_setting_afk = (
                    content.startswith(active_prefix)
                    and content[len(active_prefix):].strip().split()[:1] == ["afk"]
                )
                if not is_setting_afk and afk_ref and afk_ref.is_afk(self.user_id):
                    afk_ref.remove_afk(self.user_id)
                    msg = self.api.send_message(
                        channel_id,
                        "```| AFK |\nWelcome back! Your AFK has been removed```",
                    )

            # Auto-react to own messages
            if author_id == self.user_id and self.auto_react_emoji:
                msg_id = message_data.get("id")
                if msg_id:
                    emoji = str(self.auto_react_emoji)
                    import threading
                    threading.Thread(
                        target=lambda: self.api.add_reaction(channel_id, msg_id, emoji),
                        daemon=True,
                    ).start()

            # Command dispatch — determine which prefix to use for this user.
            # The "token-user prefix" is the bot's globally active prefix.
            # Control users (owner, alt accounts) always inherit it so that
            # changing prefix via setprefix works for ALL controller accounts.

            token_prefix = self.get_user_prefix(str(self.user_id or "")) if self.user_id else self.prefix
            user_prefix  = self.get_user_prefix(author_id) if author_id else self.prefix
            config_get = getattr(self.config, "get", None)
            if callable(config_get):
                alt_prefix = config_get("alt_prefix", "") or config_get("new_prefix", "")
                owner_prefix = config_get("owner_prefix", "!")
            elif isinstance(self.config, dict):
                alt_prefix = self.config.get("alt_prefix", "") or self.config.get("new_prefix", "")
                owner_prefix = self.config.get("owner_prefix", "!")
            else:
                alt_prefix = ""
                owner_prefix = "!"

            # Prefix matching order: user-specific, configured defaults, then active runtime prefix.
            candidate_prefixes = []
            user_prefix = self.get_user_prefix(author_id)
            if user_prefix:
                candidate_prefixes.append(user_prefix)
            if self.config.get("owner_prefix", "$"):
                candidate_prefixes.append(self.config.get("owner_prefix", "$"))
            if self.config.get("alt_prefix", ".."):
                candidate_prefixes.append(self.config.get("alt_prefix", ".."))
            if self.config.get("prefix", ";"):
                candidate_prefixes.append(self.config.get("prefix", ";"))
            if self.prefix:
                candidate_prefixes.append(self.prefix)

            # De-duplicate while preserving order and prefer longest first.
            deduped = []
            seen_prefixes = set()
            for p in candidate_prefixes:
                sp = str(p or "")
                if not sp or sp in seen_prefixes:
                    continue
                seen_prefixes.add(sp)
                deduped.append(sp)
            deduped.sort(key=len, reverse=True)

            matched_prefix = None
            for p in deduped:
                if content.startswith(p):
                    matched_prefix = p
                    break

            if not matched_prefix:
                return

            parts = content[len(matched_prefix):].strip().split()
            if not parts:
                return
            cmd_name = parts[0].lower()
            args = parts[1:]

            # Normalize common VC alias forms to canonical command keys so
            # VC routing still works even if alias keys are overridden later.
            cmd_name = {
                "joinvc": "vc",
                "vcjoin": "vc",
                "joinvoice": "vc",
                "joincall": "vc",
                "leavevc": "vce",
                "vcleave": "vce",
                "leavevoice": "vce",
            }.get(cmd_name, cmd_name)
            # Define ctx before usage, always include api and bot
            ctx = {
                "author_id": author_id,
                "guild_id": guild_id,
                "channel_id": channel_id,
                "api": self.api,
                "bot": self,
            }

            # Ensure cmd_name is always a string
            cmd_name = cmd_name or "default_command"
            if isinstance(cmd_name, str):
                resolved_command = self._resolve_command(cmd_name)
                if resolved_command is not None:
                    self.run_command(cmd_name, ctx, args)
        except Exception as e:
            print(f"\033[1;31m[MSG ERROR]\033[0m {e}")

    def _handle_channel_create(self, channel_data: dict):
        """Handle CHANNEL_CREATE — used for Anti-GC-trap detection."""
        try:
            trap_data = {
                "channel_id": channel_data.get("id"),
                "type": channel_data.get("type"),
                "name": channel_data.get("name", ""),
            }
            self.anti_gc_trap.check_gc_creation(trap_data)
        except Exception:
            pass

    def _handle_guild_update(self, guild_data: dict):
        """Handle GUILD_UPDATE — detect boost count changes."""
        try:
            if self.boost_manager is not None and hasattr(self.boost_manager, "handle_guild_update"):
                self.boost_manager.handle_guild_update(guild_data)
        except Exception:
            pass

    def _apply_persistent_activity(self):
        """Re-send the current activity over the gateway after (re)connect."""
        if self.activity and self.activity_persist:
            self.set_activity(self.activity)

    def _active_account_id(self) -> str:
        return str(self.user_id or "")

    def _save_user_prefixes(self):
        try:
            with open(self.user_prefixes_file, "w") as f:
                json.dump(self.user_prefixes, f, indent=2)
        except Exception as e:
            print(f"Failed to save user prefixes: {e}")

    def _verify_system(self):
        """Minimal integrity check — validates the stored token string."""
        v = getattr(self, "validation_string", "")
        parts = v.split("_") if v else []
        if len(parts) < 4:
            pass  # non-fatal; don't exit

    def set_status(self, status: str) -> bool:
        """Update presence status (online/idle/dnd/invisible) via gateway op 3."""
        status = normalize_status(status)
        valid = {"online", "idle", "dnd", "invisible"}
        if status not in valid:
            return False
        self._current_status = status
        if self.identified and self.connection_active and self.ws:
            try:
                since = int(time.time() * 1000) if status == "idle" else 0
                payload = {
                    "op": GatewayOpcodes.PresenceUpdate,
                    "d": {
                        "since": since,
                        "activities": [self.activity] if self.activity else [],
                        "status": status,
                        "afk": status == "idle",
                    },
                }
                self.ws.send(json.dumps(payload))
                return True
            except Exception:
                return False
        return False

    def set_activity(self, activity):
        """Set or clear the current presence activity."""
        activity = self._normalize_activity_payload(activity)
        self.activity = activity
        signature = None
        if isinstance(activity, dict):
            signature = (
                activity.get("type"),
                activity.get("name"),
                activity.get("details"),
                activity.get("state"),
                activity.get("application_id"),
            )
        if signature != self._last_activity_signature:
            if isinstance(activity, dict):
                activity_type = {
                    ActivityType.Playing: "playing",
                    ActivityType.Streaming: "streaming",
                    ActivityType.Listening: "listening",
                    ActivityType.Watching: "watching",
                    ActivityType.Competing: "competing",
                }.get(activity.get("type"), str(activity.get("type")))
                print(
                    f"\033[1;36m[RPC]\033[0m type={activity_type} "
                    f"name={activity.get('name') or ''} "
                    f"details={activity.get('details') or ''} "
                    f"state={activity.get('state') or ''}"
                )
            else:
                print("\033[1;36m[RPC]\033[0m cleared")
            self._last_activity_signature = signature
        if self.identified and self.connection_active and self.ws:
            try:
                status = getattr(self, "_current_status", "online")
                since = int(time.time() * 1000) if status == "idle" else 0
                payload = {
                    "op": GatewayOpcodes.PresenceUpdate,
                    "d": {
                        "since": since,
                        "activities": [activity] if activity else [],
                        "status": status,
                        "afk": status == "idle",
                    },
                }
                self.ws.send(json.dumps(payload))
            except Exception:
                pass

    def clear_activity(self):
        """Remove the current presence activity."""
        self.set_activity(None)

    def stop(self):
        """Gracefully stop the bot."""
        self.running = False
        self.connection_active = False

        # Stop gateway bridge if using async gateway
        if self.use_async_gateway and self.gateway_bridge:
            try:
                self.gateway_bridge.stop()
            except Exception as e:
                print(f"Error stopping gateway bridge: {e}")

        # Stop legacy websocket
        try:
            if self.ws:
                self.ws.close()
        except Exception:
            pass

    def run(self):
        """Connect to Discord gateway and block until stopped.

        A watchdog loop runs on the main thread: every 15 s it checks whether
        the gateway connection is still alive. If the connection has died, it triggers a
        reconnect so the bot wakes back up automatically.
        """
        self._connect_gateway()
        while self.running:
            try:
                time.sleep(15)
                # Watchdog: restart gateway if connection died silently
                connection_alive = False

                if self.use_async_gateway:
                    # Check async gateway bridge
                    connection_alive = (
                        self.gateway_bridge and
                        self.gateway_bridge.connection_active
                    )
                else:
                    # Check legacy websocket thread
                    connection_alive = (
                        self.ws_thread and
                        self.ws_thread.is_alive()
                    )

                if self.running and not connection_alive:
                    print("\033[1;33m[WATCHDOG]\033[0m Gateway connection dead — reconnecting…")
                    self.identified = False
                    self.connection_active = False
                    # Route through _auto_reconnect to avoid double connections
                    if not self._connecting:
                        threading.Thread(target=self._auto_reconnect, daemon=True, name="WatchdogReconnect").start()
            except KeyboardInterrupt:
                self.stop()
                break
