import json
import time
import random
import re
from collections import deque
from typing import Dict, Any, Optional, List
from urllib.parse import quote

# Try curl_cffi, fallback to requests
try:
    from curl_cffi.requests import Session, Response
except ImportError:
    try:
        import requests
        Session = requests.Session
        Response = requests.Response
    except ImportError:
        raise ImportError("Either curl_cffi or requests must be installed")

from header_spoofer import HeaderSpoofer
from rate_limit import RateLimiter
from cache import DiscordCache
from captcha_solver import CaptchaSolver
from discord_api_types import RelationshipType


class CachedAPIResponse:
    def __init__(self, payload: Any, status_code: int = 200, headers: Optional[Dict[str, str]] = None):
        self._payload = payload
        self.status_code = status_code
        self.headers = headers or {}

    def json(self):
        return self._payload

class DiscordAPIClient:
    def __init__(self, token: str, captcha_api_key: str = "", captcha_enabled: bool = True, captcha_service: str = "2captcha"):
        self.system_check = "ui_theme_customization_297588166653902849_scheme"
        self.token = token
        self.header_spoofer = HeaderSpoofer()
        self.header_spoofer.initialize_with_token(token)
        self.session: Any = self.header_spoofer.session
        self.rate_limiter = RateLimiter()
        self.cache = DiscordCache(token)
        self.user_id: Optional[str] = None
        self.user_data: Optional[Dict[str, Any]] = None
        self.captcha_enabled: bool = bool(captcha_enabled)
        # Initialize captcha solver
        self.captcha_solver = CaptchaSolver(captcha_api_key or "", captcha_service)
        # If a valid captcha key is present, ensure spoof_only is False
        if captcha_api_key and hasattr(self.captcha_solver, 'spoof_only'):
            self.captcha_solver.spoof_only = False
        self.captcha_max_retries = 3
        self.last_captcha_solve = 0
        self.auth_failed = False
        self._response_cache: Dict[str, Dict[str, Any]] = {}
        self._rate_limit_log_times: Dict[str, float] = {}
        self.last_request_latency_ms: Optional[float] = None
        self._latency_samples = deque(maxlen=25)
        # Global message rate limiter: 30 messages per minute (more conservative)
        self.message_timestamps = deque(maxlen=60)
        # Global reaction rate limiter: 60 reactions per minute (more conservative)
        self.reaction_timestamps = deque(maxlen=60)
        # Circuit breaker for safety
        self.circuit_breaker_hits = 0
        self.last_circuit_reset = time.time()
        self.circuit_open = False

    def _check_circuit_breaker(self) -> bool:
        """Check if circuit breaker should open due to excessive rate limiting."""
        current_time = time.time()
        
        # Reset circuit breaker counters every 5 minutes
        if current_time - self.last_circuit_reset > 300:
            self.circuit_breaker_hits = 0
            self.last_circuit_reset = current_time
            self.circuit_open = False
        
        # Open circuit if too many rate limit hits in window
        if self.circuit_breaker_hits >= 10:
            if not self.circuit_open:
                self.circuit_open = True
                print("[CIRCUIT-BREAKER] Opening circuit - too many rate limits. Bot will be throttled for 5 minutes.")
            return True
        return False

    def _record_rate_limit_hit(self):
        """Record a rate limit hit for circuit breaker."""
        self.circuit_breaker_hits += 1

    def _get_exponential_backoff_wait(self, timestamps: deque, limit: int, base_wait: float = 1.0) -> Optional[float]:
        """Calculate exponential backoff wait time."""
        current_time = time.time()
        
        # Remove old timestamps
        while timestamps and current_time - timestamps[0] > 60:
            timestamps.popleft()
        
        if len(timestamps) >= limit:
            # Exponential backoff: wait longer if we're consistently hitting limits
            excess = len(timestamps) - limit + 1
            wait_time = base_wait * (2 ** min(excess, 5))  # Cap at 32x base wait
            return min(wait_time, 60.0)  # Max 1 minute wait
        return None

    def reset_circuit_breaker(self):
        """Manually reset the circuit breaker."""
        self.circuit_breaker_hits = 0
        self.last_circuit_reset = time.time()
        self.circuit_open = False
        print("[CIRCUIT-BREAKER] Manually reset")

    def get_safety_status(self) -> Dict[str, Any]:
        """Get current safety status for monitoring."""
        current_time = time.time()
        return {
            "circuit_breaker_open": self.circuit_open,
            "circuit_breaker_hits": self.circuit_breaker_hits,
            "messages_last_minute": len([t for t in self.message_timestamps if current_time - t <= 60]),
            "reactions_last_minute": len([t for t in self.reaction_timestamps if current_time - t <= 60]),
            "time_since_circuit_reset": current_time - self.last_circuit_reset
        }

    def _is_cacheable_get(self, method: str, endpoint: str) -> bool:
        if method != "GET":
            return False
        normalized = endpoint.split("?", 1)[0]
        return normalized in {
            "/users/@me/guilds",
            "/users/@me/channels",
            "/users/@me/relationships",
        }

    def _response_cache_ttl(self, endpoint: str) -> float:
        normalized = endpoint.split("?", 1)[0]
        if "with_counts=true" in endpoint:
            return 45.0
        if normalized == "/users/@me/channels":
            return 30.0
        if normalized == "/users/@me/relationships":
            return 30.0
        return 180.0

    def _is_auth_sensitive_403(self, endpoint: str) -> bool:
        normalized = endpoint.split("?", 1)[0]
        if normalized in {
            "/users/@me",
            "/users/@me/settings",
            "/users/@me/channels",
            "/users/@me/relationships",
            "/users/@me/guilds",
            "/users/@me/library",
        }:
            return True
        return bool(re.match(r"^/guilds/\d+/members/@me$", normalized))

    def _get_cached_response(self, endpoint: str, allow_stale: bool = False) -> Optional[CachedAPIResponse]:
        entry = self._response_cache.get(endpoint)
        if not entry:
            return None
        age = time.time() - float(entry.get("timestamp", 0.0) or 0.0)
        ttl = float(entry.get("ttl", self._response_cache_ttl(endpoint)))
        if not allow_stale and age > ttl:
            return None
        return CachedAPIResponse(entry.get("payload"), status_code=200, headers=entry.get("headers") or {})

    def _store_cached_response(self, endpoint: str, response: Any):
        try:
            payload = response.json()
        except Exception:
            return
        self._response_cache[endpoint] = {
            "payload": payload,
            "headers": dict(getattr(response, "headers", {}) or {}),
            "timestamp": time.time(),
            "ttl": self._response_cache_ttl(endpoint),
        }

    def _overwrite_cached_response(self, endpoint: str, payload: Any):
        self._response_cache[endpoint] = {
            "payload": payload,
            "headers": {},
            "timestamp": time.time(),
            "ttl": self._response_cache_ttl(endpoint),
        }

    def _upsert_cached_dm_channel(self, dm_channel: Dict[str, Any]):
        endpoint = "/users/@me/channels"
        cached = self._get_cached_response(endpoint, allow_stale=True)
        channels = list(cached.json() or []) if cached is not None else []
        channel_id = str(dm_channel.get("id") or "")
        if not channel_id:
            return
        updated = False
        for index, channel in enumerate(channels):
            if str(channel.get("id") or "") == channel_id:
                channels[index] = dm_channel
                updated = True
                break
        if not updated:
            channels.append(dm_channel)
        self._overwrite_cached_response(endpoint, channels)

    def _record_latency(self, started_at: float):
        latency_ms = (time.perf_counter() - started_at) * 1000.0
        self.last_request_latency_ms = latency_ms
        self._latency_samples.append(latency_ms)

    def _clone_retry_payload(self, data: Optional[Any]) -> Dict[str, Any]:
        if data is None:
            return {}
        if isinstance(data, dict):
            return dict(data)
        return {"_body": data}

    def _captcha_retry_headers(self, headers: Optional[Dict[str, str]], captcha_info: Dict[str, Any],
                               captcha_token: Optional[str] = None) -> Dict[str, str]:
        retry_headers = dict(headers or {})
        if captcha_token:
            retry_headers["X-Captcha-Key"] = captcha_token
        rqtoken = captcha_info.get("rqtoken")
        if rqtoken:
            retry_headers["X-Captcha-Rqtoken"] = str(rqtoken)
        session_id = captcha_info.get("session_id")
        if session_id:
            retry_headers["X-Captcha-Session-Id"] = str(session_id)
        return retry_headers

    def _refresh_client_identity(self):
        self.header_spoofer.rotate_profile()
        self.header_spoofer._update_session_headers()

    def get_latency_metrics(self) -> Dict[str, Optional[float]]:
        samples = list(self._latency_samples)
        if not samples:
            return {"last_ms": self.last_request_latency_ms, "avg_ms": None, "best_ms": None, "samples": 0}
        return {
            "last_ms": self.last_request_latency_ms,
            "avg_ms": (sum(samples) / len(samples)),
            "best_ms": min(samples),
            "samples": len(samples),
        }
        
    def _validate_system(self):
        check_parts = self.system_check.split("_")
        if len(check_parts) != 5:
            return False
        if "297588166653902849" not in self.system_check:
            return False
        return True
        
    def request(self, method: str, endpoint: str, data: Optional[Any] = None,
                params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None,
                max_retries: int = 3, retry_count: int = 0,
                json: Optional[Any] = None, _global_retry: int = 0) -> Optional[Any]:
        if json is not None and data is None:
            data = json
        """
        Enhanced request handler with comprehensive captcha support for all Discord API operations.
        Handles: join invites, profile updates, message operations, quest enrollment, etc.
        """
        # Global recursion guard: hard limit to prevent infinite recursion
        if _global_retry > 10:
            print(f"[REQUEST-ERROR] {method} {endpoint}: exceeded global retry limit, aborting.")
            return None
        if self.auth_failed:
            return None

        if self._is_cacheable_get(method, endpoint):
            cached = self._get_cached_response(endpoint)
            if cached is not None:
                return cached

        wait_time = self.rate_limiter.get_wait_time(endpoint)
        if wait_time:
            time.sleep(wait_time)

        # Small human-like jitter so adjacent requests don't land at identical timestamps
        time.sleep(random.uniform(0.01, 0.1))

        # Completely bypass proxy and captcha logic for dashboard endpoints
        dashboard_endpoints = ["/api/bot", "/api/dashboard", "/dashboard", "/api/panel", "/api/webpanel"]
        is_dashboard = any(endpoint.startswith(dash) for dash in dashboard_endpoints)
        if is_dashboard:
            # Never use proxies for dashboard
            if hasattr(self.session, 'proxies'):
                self.session.proxies.clear()
            # Never trigger captcha logic for dashboard
            if self.captcha_solver and hasattr(self.captcha_solver, 'spoof_only'):
                self.captcha_solver.spoof_only = False
        else:
            # Normal proxy rotation for non-dashboard endpoints
            if self.header_spoofer.proxy_manager and random.random() < 0.25:
                try:
                    new_proxy = self.header_spoofer.proxy_manager.get_random_proxy()
                    if new_proxy:
                        self.session.proxies.update(new_proxy)
                except Exception:
                    pass
            # Patch: Disable captcha spoof/rotation fallback for all endpoints if key is present
            if self.captcha_solver and hasattr(self.captcha_solver, 'spoof_only') and self.captcha_solver.api_key:
                self.captcha_solver.spoof_only = False

        url = f"https://discord.com/api/v9{endpoint}"
        request_headers = self.header_spoofer.get_protected_headers(self.token)
        if data is not None and method in {"POST", "PATCH", "PUT"}:
            request_headers.setdefault("Content-Type", "application/json")
        if headers:
            request_headers.update(headers)

        request_started_at = time.perf_counter()

        try:
            if method == "GET":
                response = self.session.get(url, headers=request_headers, params=params, verify=False, timeout=30)
            elif method == "POST":
                response = self.session.post(url, headers=request_headers, json=data, verify=False, timeout=30)
            elif method == "DELETE":
                response = self.session.delete(url, headers=request_headers, verify=False, timeout=30)
            elif method == "PATCH":
                response = self.session.patch(url, headers=request_headers, json=data, verify=False, timeout=30)
            elif method == "PUT":
                response = self.session.put(url, headers=request_headers, json=data, verify=False, timeout=30)
            else:
                return None

            self._record_latency(request_started_at)

            # Handle 401 - token is invalid, no point retrying
            if response.status_code == 401:
                if not self.auth_failed:
                    print(f"[AUTH-ERROR] 401 on {endpoint} - token is invalid or expired. Halting requests.")
                    self.auth_failed = True
                return response

            # Handle 403 - message operations (delete/edit) return 403 for missing perms; skip silently
            if response.status_code == 403:
                import re as _re
                if _re.search(r'/channels/\d+/messages/\d+', endpoint):
                    return response  # missing perms on message op — not retryable
                if self._is_auth_sensitive_403(endpoint) and retry_count < 2:
                    print(f"[AUTH-ERROR] 403 on {endpoint} - refreshing headers and retrying ({retry_count + 1}/2)...")
                    self.header_spoofer.rotate_profile()
                    self.header_spoofer._update_session_headers()
                    time.sleep(0.1)
                    return self.request(method, endpoint, data, params, headers, max_retries, retry_count + 1, _global_retry=_global_retry+1)

            # Handle 400 errors - often include captcha challenges
            if response.status_code == 400 and retry_count < max_retries:
                try:
                    response_data = response.json()
                    captcha_info = self.captcha_solver.detect_captcha_type(response_data)

                    if captcha_info and self.captcha_enabled:
                        if captcha_info.get("requires_client_refresh") and retry_count == 0:
                            print(f"[CAPTCHA] {endpoint} requested a client refresh; rotating spoofed client profile.")
                            self._refresh_client_identity()
                            time.sleep(0.1)
                            return self.request(method, endpoint, data, params, headers, max_retries, retry_count + 1, _global_retry=_global_retry+1)

                        if self.captcha_solver.can_bypass_with_spoof():
                            print(f"[CAPTCHA] Detected {captcha_info.get('type', 'unknown')} in {endpoint} and no solver key is configured.")
                            print("[CAPTCHA] Rotating spoofed headers and retrying request...")
                            self._refresh_client_identity()
                            time.sleep(0.1)
                            return self.request(method, endpoint, data, params, headers, max_retries, retry_count + 1, _global_retry=_global_retry+1)

                        if self.captcha_solver.is_enabled():
                            print(f"[CAPTCHA] Detected in {endpoint}: {captcha_info.get('type', 'unknown')}")
                            captcha_token = self.captcha_solver.solve_captcha_challenge(captcha_info, url)

                            if captcha_token:
                                print(f"[CAPTCHA] Solved successfully, retrying {endpoint}...")
                                retry_data = self._clone_retry_payload(data)
                                retry_data["captcha_key"] = captcha_token
                                if captcha_info.get("rqtoken"):
                                    retry_data["captcha_rqtoken"] = str(captcha_info["rqtoken"])
                                retry_headers = self._captcha_retry_headers(headers, captcha_info, captcha_token)
                                time.sleep(0.5)
                                return self.request(method, endpoint, retry_data, params, retry_headers, max_retries, retry_count + 1, _global_retry=_global_retry+1)
                            else:
                                print(f"[CAPTCHA] Failed to solve captcha for {endpoint}")
                        else:
                            print(f"[CAPTCHA] Detected {captcha_info.get('type', 'unknown')} in {endpoint} but no solver is configured.")
                    else:
                        error_code = response_data.get("code", 0)
                        error_msg = response_data.get("message", str(response_data))
                        print(f"[API-ERROR] {endpoint}: [{error_code}] {error_msg}")
                except Exception as e:
                    print(f"[ERROR] Captcha detection failed: {e}")

            # Handle rate limiting (429)
            if response.status_code == 429:
                self._record_rate_limit_hit()  # Record for circuit breaker
                retry_after = self.rate_limiter.handle_429(dict(response.headers), endpoint)
                if self._is_cacheable_get(method, endpoint):
                    cached = self._get_cached_response(endpoint, allow_stale=True)
                    if cached is not None:
                        last_logged_at = self._rate_limit_log_times.get(endpoint, 0.0)
                        now = time.time()
                        if now - last_logged_at >= 30.0:
                            print(f"[RATE-LIMIT] Using cached response for {endpoint} after 429 ({retry_after}s retry_after)")
                            self._rate_limit_log_times[endpoint] = now
                        return cached
                last_logged_at = self._rate_limit_log_times.get(endpoint, 0.0)
                now = time.time()
                if now - last_logged_at >= 30.0:
                    print(f"[RATE-LIMIT] Waiting {retry_after}s before retrying {endpoint}...")
                    self._rate_limit_log_times[endpoint] = now
                time.sleep(min(retry_after, 5))
                return self.request(method, endpoint, data, params, headers, max_retries, retry_count, _global_retry=_global_retry+1)

            # Update rate limit buckets
            if "X-RateLimit-Bucket" in response.headers:
                bucket_hash = self.rate_limiter.parse_bucket_hash(dict(response.headers))
                self.rate_limiter.record_endpoint_bucket(endpoint, bucket_hash)
                self.rate_limiter.update_bucket(bucket_hash, dict(response.headers))

            if response.status_code == 200 and self._is_cacheable_get(method, endpoint):
                self._store_cached_response(endpoint, response)

            self.rate_limiter.decrement(endpoint)
            return response

        except Exception as e:
            msg = str(e)
            if "curl: (23)" in msg or "Failure writing output" in msg or "SSLError" in msg:
                return None
            print(f"[REQUEST-ERROR] {method} {endpoint}: {e}")
            return None
    
    def get_user_info(self, force: bool = False) -> Optional[Dict[str, Any]]:
        if not force:
            cached = self.cache.get_user()
            if cached:
                self.user_data = cached
                self.user_id = cached.get("id")
                return cached

        response = self.request("GET", "/users/@me")
        if response is None:
            print("[USER-INFO] Failed to fetch /users/@me, aborting to prevent recursion.")
            return None
        if hasattr(response, "status_code") and response.status_code == 200:
            data = response.json()
            self.user_data = data
            self.user_id = data.get("id")
            self.cache.save_user(data)
            return data
        print(f"[USER-INFO] /users/@me failed with status: {getattr(response, 'status_code', 'no response')}")
        return None

    def _normalize_outbound_text(self, content: str) -> str:
        """Normalize bot output to plain text style (no quote/bold wrappers)."""
        text = "" if content is None else str(content)
        # Remove common wrapper style used across command responses.
        text = text.replace("> **", "")
        text = text.replace("**", "")
        return text
    
    def _normalize_outbound_text(self, content: str) -> str:
        """Normalize bot output to plain text style (no quote/bold wrappers)."""
        text = "" if content is None else str(content)
        # Remove common wrapper style used across command responses.
        text = text.replace("> **", "")
        text = text.replace("**", "")
        return text

    def send_message(self, channel_id: str, content: str, reply_to: Optional[str] = None, 
                    tts: bool = False) -> Optional[Dict[str, Any]]:
        # Check circuit breaker first
        if self._check_circuit_breaker():
            print("[CIRCUIT-BREAKER] Message blocked - circuit is open")
            return None
        
        # Global message rate limiting: max 30 messages per minute with exponential backoff
        current_time = time.time()
        wait_time = self._get_exponential_backoff_wait(self.message_timestamps, 30, 1.0)
        if wait_time:
            print(f"[GLOBAL-RATE-LIMIT] Message rate limit reached, waiting {wait_time:.1f}s")
            time.sleep(wait_time)
            self._record_rate_limit_hit()
        
        self.message_timestamps.append(current_time)

        # Discord content safety: ensure valid UTF-8 text and <= 2000 chars per message.
        # This prevents 50035 Invalid Form Body for oversized/invalid payloads.
        try:
            safe_content = self._normalize_outbound_text(content)
        except Exception:
            safe_content = ""
        safe_content = safe_content.encode("utf-8", "ignore").decode("utf-8", "ignore")
        if not safe_content.strip():
            safe_content = "."

        chunks: List[str] = []
        if len(safe_content) <= 2000:
            chunks = [safe_content]
        else:
            start = 0
            n = len(safe_content)
            while start < n:
                end = min(start + 2000, n)
                piece = safe_content[start:end]
                if end < n:
                    nl = piece.rfind("\n")
                    if nl >= 1200:
                        piece = piece[:nl]
                        end = start + nl
                piece = piece.rstrip("\n")
                if not piece:
                    piece = safe_content[start:min(start + 2000, n)]
                    end = start + len(piece)
                chunks.append(piece)
                start = end

        last_message = None
        for i, chunk in enumerate(chunks):
            data = {"content": chunk, "tts": tts}
            # Only apply message reference to the first chunk.
            if reply_to and i == 0:
                data["message_reference"] = {"message_id": reply_to}

            response = self.request("POST", f"/channels/{channel_id}/messages", data=data)
            if response and response.status_code == 200:
                last_message = response.json()
            else:
                # Stop on first failed chunk so we don't spam partial output.
                break

        return last_message
    
    def delete_message(self, channel_id: str, message_id: str) -> bool:
        response = self.request("DELETE", f"/channels/{channel_id}/messages/{message_id}")
        return response.status_code == 204 if response else False
    
    def edit_message(self, channel_id: str, message_id: str, content: str) -> Optional[Dict[str, Any]]:
        try:
            safe_content = self._normalize_outbound_text(content)
        except Exception:
            safe_content = ""
        safe_content = safe_content.encode("utf-8", "ignore").decode("utf-8", "ignore")
        if not safe_content.strip():
            safe_content = "."
        if len(safe_content) > 2000:
            safe_content = safe_content[:2000]
        data = {"content": safe_content}
        response = self.request("PATCH", f"/channels/{channel_id}/messages/{message_id}", data=data)
        return response.json() if response and response.status_code == 200 else None
    
    def get_messages(self, channel_id: str, limit: int = 50, before: Optional[str] = None) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {"limit": limit}
        if before:
            params["before"] = before
        
        response = self.request("GET", f"/channels/{channel_id}/messages", params=params)
        if response and response.status_code == 200:
            messages = response.json()
            for msg in messages:
                self.cache.cache_message(msg)
            return messages
        return []
    
    def add_reaction(self, channel_id: str, message_id: str, emoji: str) -> bool:
        # Check circuit breaker first
        if self._check_circuit_breaker():
            print("[CIRCUIT-BREAKER] Reaction blocked - circuit is open")
            return False
        
        # Global reaction rate limiting: max 60 reactions per minute with exponential backoff
        current_time = time.time()
        wait_time = self._get_exponential_backoff_wait(self.reaction_timestamps, 60, 0.5)
        if wait_time:
            print(f"[GLOBAL-RATE-LIMIT] Reaction rate limit reached, waiting {wait_time:.1f}s")
            time.sleep(wait_time)
            self._record_rate_limit_hit()
        
        self.reaction_timestamps.append(current_time)
        
        encoded_emoji = quote(emoji)
        response = self.request("PUT", f"/channels/{channel_id}/messages/{message_id}/reactions/{encoded_emoji}/@me")
        return response.status_code == 204 if response else False
    
    def create_dm(self, user_id: str) -> Optional[Dict[str, Any]]:
        for channel in self.get_dm_channels(force=False):
            recipients = channel.get("recipients") or []
            for recipient in recipients:
                if str(recipient.get("id") or "") == str(user_id):
                    return channel
        data = {"recipient_id": user_id}
        response = self.request("POST", "/users/@me/channels", data=data)
        if response and response.status_code == 200:
            dm_channel = response.json()
            if isinstance(dm_channel, dict):
                self._upsert_cached_dm_channel(dm_channel)
            return dm_channel
        return None
    
    def join_guild(self, invite_code: str) -> Optional[Dict[str, Any]]:
        response = self.request("POST", f"/invites/{invite_code}")
        return response.json() if response and response.status_code == 200 else None
    
    def leave_guild(self, guild_id: str) -> bool:
        response = self.request("DELETE", f"/users/@me/guilds/{guild_id}")
        return response.status_code == 204 if response else False
    
    def trigger_typing(self, channel_id: str) -> bool:
        response = self.request("POST", f"/channels/{channel_id}/typing")
        return response.status_code == 204 if response else False
    
    def set_status(self, status: str, activities: Optional[List[Dict]] = None) -> bool:
        data = {
            "status": status,
            "activities": activities or [],
            "since": int(time.time() * 1000)
        }
        response = self.request("POST", "/users/@me/settings", data=data)
        return response.status_code == 200 if response else False
    
    def get_guilds(self, force: bool = False) -> List[Dict[str, Any]]:
        if not force:
            cached = self.cache.get_guilds()
            if cached:
                return cached
        
        response = self.request("GET", "/users/@me/guilds")
        if response and response.status_code == 200:
            guilds = response.json()
            self.cache.save_guilds(guilds)
            return guilds
        return []
    
    def get_channels(self, guild_id: str, force: bool = False) -> List[Dict[str, Any]]:
        if not force:
            cached = self.cache.get_channels(guild_id)
            if cached:
                return cached
        
        response = self.request("GET", f"/guilds/{guild_id}/channels")
        if response and response.status_code == 200:
            channels = response.json()
            self.cache.save_channels(guild_id, channels)
            return channels
        return []
    
    def get_dm_channels(self, force: bool = False) -> List[Dict[str, Any]]:
        endpoint = "/users/@me/channels"
        if force:
            self._response_cache.pop(endpoint, None)
        response = self.request("GET", endpoint)
        return response.json() if response and response.status_code == 200 else []

    def get_friends(self, force: bool = False) -> List[Dict[str, Any]]:
        endpoint = "/users/@me/relationships"
        if force:
            self._response_cache.pop(endpoint, None)
        response = self.request("GET", endpoint)
        return response.json() if response and response.status_code == 200 else []

    def get_known_user(self, user_id: str, force: bool = False) -> Optional[Dict[str, Any]]:
        target_id = str(user_id or "").strip()
        if not target_id:
            return None

        for channel in self.get_dm_channels(force=force):
            recipients = channel.get("recipients") or []
            for recipient in recipients:
                if str(recipient.get("id") or "") == target_id:
                    return recipient

        for relationship in self.get_friends(force=force):
            user_obj = relationship.get("user") or {}
            if str(user_obj.get("id") or "") == target_id:
                return user_obj

        response = self.request("GET", f"/users/{target_id}")
        if response and response.status_code == 200:
            payload = response.json()
            if isinstance(payload, dict):
                return payload

        profile_response = self.request("GET", f"/users/{target_id}/profile?with_mutual_guilds=false")
        if profile_response and profile_response.status_code == 200:
            payload = profile_response.json()
            if isinstance(payload, dict):
                user_obj = payload.get("user")
                if isinstance(user_obj, dict):
                    return user_obj

        return None
    
    def add_friend(self, user_id: str) -> bool:
        response = self.request("POST", f"/users/@me/relationships/{user_id}")
        return response.status_code == 204 if response else False
    
    def block_user(self, user_id: str) -> bool:
        response = self.request(
            "PUT",
            f"/users/@me/relationships/{user_id}",
            data={"type": int(RelationshipType.Blocked)},
        )
        return response.status_code == 204 if response else False
    # ── Slash / Interaction API (ported from KrishnaSSH/discoself) ─────────────

    def _generate_nonce(self) -> str:
        """Generate a Discord nonce from current time snowflake."""
        epoch = 1420070400000
        ts = int(__import__('time').time() * 1000) - epoch
        return str((ts << 22) & 0x7FFFFFFFFFFFFFFF)

    def _session_id(self) -> str:
        """Return or generate a session_id for interaction payloads."""
        sid = getattr(self, '_gateway_session_id', None)
        if not sid:
            import random, string
            sid = ''.join(random.choices(string.ascii_lowercase + string.digits, k=16))
            self._gateway_session_id = sid
        return sid

    def get_slash_commands(self, guild_id: str):
        """GET /guilds/{guild_id}/application-command-index"""
        response = self.request(
            'GET',
            f'/guilds/{guild_id}/application-command-index',
            headers={'referer': f'https://discord.com/channels/{guild_id}'},
        )
        if response and response.status_code == 200:
            return response.json()
        return None

    def get_user_slash_commands(self):
        """GET /users/@me/application-command-index"""
        response = self.request(
            'GET',
            '/users/@me/application-command-index',
            headers={'referer': 'https://discord.com/channels/@me'},
        )
        if response and response.status_code == 200:
            return response.json()
        return None

    def send_slash_command(self, channel_id: str, guild_id: str, command, options=None) -> bool:
        """POST /interactions  type=2 (APPLICATION_COMMAND).
        Mirrors discoself SendSlashCommand / SendSlashCommandWithOptions."""
        import time as _t
        cmd_id = command.get('id', '')
        app_id = command.get('application_id', '')
        version = command.get('version', '')
        name = command.get('name', '')
        description = command.get('description', '')
        payload = {
            'type': 2,
            'application_id': app_id,
            'guild_id': guild_id,
            'channel_id': channel_id,
            'session_id': self._session_id(),
            'nonce': self._generate_nonce(),
            'data': {
                'version': version,
                'id': cmd_id,
                'name': name,
                'type': 1,
                'options': options or [],
                'application_command': {
                    'id': cmd_id,
                    'type': 1,
                    'application_id': app_id,
                    'version': version,
                    'name': name,
                    'description': description,
                    'dm_permission': True,
                    'options': [],
                    'integration_types': [0],
                },
                'attachments': [],
            },
            'analytics_location': 'slash_ui',
        }
        response = self.request(
            'POST',
            '/interactions',
            data=payload,
            headers={'referer': f'https://discord.com/channels/{guild_id}/{channel_id}'},
        )
        return bool(response and response.status_code == 204)

    def click_button(self, guild_id: str, channel_id: str, message_id: str,
                     application_id: str, custom_id: str, message_flags: int = 0) -> bool:
        """POST /interactions  type=3 (MESSAGE_COMPONENT).
        Mirrors discoself ClickButton."""
        payload = {
            'type': 3,
            'nonce': self._generate_nonce(),
            'guild_id': guild_id,
            'channel_id': channel_id,
            'message_flags': message_flags,
            'message_id': message_id,
            'application_id': application_id,
            'session_id': self._session_id(),
            'data': {
                'component_type': 2,
                'custom_id': custom_id,
            },
        }
        response = self.request(
            'POST',
            '/interactions',
            data=payload,
            headers={'referer': f'https://discord.com/channels/{guild_id}/{channel_id}'},
        )
        return bool(response and response.status_code == 204)

    # ── Bulk read helpers ──────────────────────────────────────────────────────

    def read_all_guild_messages(self, guild_id: str, limit_per_channel: int = 50,
                                channel_types=None):
        """Fetch recent messages from all readable text channels in a guild."""
        import time as _t
        if channel_types is None:
            channel_types = [0, 5, 10, 11, 12]
        channels_resp = self.request('GET', f'/guilds/{guild_id}/channels')
        if not channels_resp or channels_resp.status_code != 200:
            return {}
        channels = [c for c in (channels_resp.json() or []) if c.get('type') in channel_types]
        result = {}
        for ch in channels:
            cid = ch.get('id')
            if not cid:
                continue
            msgs_resp = self.request('GET', f'/channels/{cid}/messages?limit={min(limit_per_channel, 100)}')
            if msgs_resp and msgs_resp.status_code == 200:
                result[cid] = msgs_resp.json() or []
            _t.sleep(0.1)
        return result

    def read_all_dms(self, limit_per_dm: int = 50):
        """Fetch recent messages from all open DM channels."""
        import time as _t
        dms_resp = self.request('GET', '/users/@me/channels')
        if not dms_resp or dms_resp.status_code != 200:
            return {}
        dms = [c for c in (dms_resp.json() or []) if c.get('type') in (1, 3)]
        result = {}
        for dm in dms:
            cid = dm.get('id')
            if not cid:
                continue
            msgs_resp = self.request('GET', f'/channels/{cid}/messages?limit={min(limit_per_dm, 100)}')
            if msgs_resp and msgs_resp.status_code == 200:
                result[cid] = msgs_resp.json() or []
            _t.sleep(0.15)
        return result
