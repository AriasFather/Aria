import json
import os
import tempfile
import threading
import time
from typing import Any


def _write_json_atomic(path: str, payload: dict[str, Any]) -> None:
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".hosted-rpc-", dir=directory)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as file_handle:
            json.dump(payload, file_handle, ensure_ascii=True, allow_nan=False)
            file_handle.flush()
            os.fsync(file_handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _rotation_running(bot: Any) -> bool:
    state = getattr(bot, "_rpc_rotation_state", {})
    return bool(state.get("running")) if isinstance(state, dict) else False


def _spotify_lyrics_status(bot: Any) -> dict[str, Any]:
    manager = getattr(bot, "spotify_lyrics_sync", None)
    get_status = getattr(manager, "status", None)
    if callable(get_status):
        try:
            state = get_status()
            return state if isinstance(state, dict) else {}
        except Exception:
            pass
    return {"available": False, "enabled": False, "running": False, "phase": "unavailable"}


def _write_status(bot: Any, control_dir: str) -> dict[str, Any]:
    activity = getattr(bot, "activity", None)
    activities = getattr(bot, "activities", None)
    if not isinstance(activities, list):
        activities = [activity] if isinstance(activity, dict) else []
    identified = bool(getattr(bot, "identified", False))
    connection_active = bool(getattr(bot, "connection_active", False))
    diagnostics = {}
    try:
        get_diagnostics = getattr(bot, "get_connection_diagnostics", None)
        diagnostics = get_diagnostics() if callable(get_diagnostics) else {}
    except Exception:
        diagnostics = {}
    status = {
        "active": bool(activities),
        "activity": activity if isinstance(activity, dict) else None,
        "activities": activities,
        "connected": bool(connection_active and identified),
        "identified": identified,
        "username": str(getattr(bot, "username", "") or ""),
        "user_id": str(getattr(bot, "user_id", "") or ""),
        "client_type": str(getattr(bot, "_client_type", "hosted") or "hosted"),
        "gateway_latency_ms": diagnostics.get("gateway_latency_ms", getattr(bot, "gateway_latency_ms", None)),
        "reconnect_attempts": int(diagnostics.get("consecutive_failures", getattr(bot, "_consecutive_failures", 0)) or 0),
        "connection_error": str(getattr(bot, "last_connection_error", "") or "")[:240],
        "rotation_running": _rotation_running(bot),
        "spotify_lyrics": _spotify_lyrics_status(bot),
        "updated_at": int(time.time()),
    }
    _write_json_atomic(os.path.join(control_dir, "rpc_status.json"), status)
    return status


def _apply_request(bot: Any, request: dict[str, Any]) -> dict[str, Any]:
    action = str(request.get("action") or "")
    try:
        if action in {"set", "stop"}:
            activity = request.get("activity") if action == "set" else None
            if action == "set" and not (
                isinstance(activity, dict)
                or isinstance(activity, list) and 1 <= len(activity) <= 5 and all(isinstance(item, dict) for item in activity)
            ):
                return {"ok": False, "error": "activity must be an object or a list of up to five activities"}
            apply_activity = getattr(bot, "_rpc_apply_activity", None)
            if callable(apply_activity):
                result = apply_activity(bot, activity)
            else:
                result = bot.set_activity(activity)
        elif action == "rotation_start":
            start_rotation = getattr(bot, "_rpc_start_rotation", None)
            if not callable(start_rotation):
                return {"ok": False, "error": "RPC rotation controls are unavailable"}
            result = start_rotation(bot)
        elif action == "rotation_stop":
            stop_rotation = getattr(bot, "_rpc_stop_rotation", None)
            if not callable(stop_rotation):
                return {"ok": False, "error": "RPC rotation controls are unavailable"}
            result = stop_rotation(bot, resume_keepalive=True)
            message = str(result[1]) if isinstance(result, tuple) and len(result) > 1 else "Rotation stopped"
            return {"ok": True, "message": message}
        elif action in {"spotify_start", "spotify_stop"}:
            lyrics = getattr(bot, "spotify_lyrics_sync", None)
            if lyrics is None:
                return {"ok": False, "error": "Spotify lyrics controls are unavailable"}
            if action == "spotify_start":
                lyrics.start()
            else:
                lyrics.stop()
            return {"ok": True, "spotify_lyrics": lyrics.status()}
        else:
            return {"ok": False, "error": "Unsupported hosted RPC action"}

        if isinstance(result, tuple):
            ok = bool(result[0])
            message = str(result[1]) if len(result) > 1 else ""
        else:
            ok = result is not False
            message = ""
        return {"ok": ok, "message": message}
    except Exception as error:
        return {"ok": False, "error": str(error)}


def start_hosted_rpc_worker(bot: Any, control_dir: str) -> threading.Event:
    request_dir = os.path.join(control_dir, "rpc_requests")
    response_dir = os.path.join(control_dir, "rpc_responses")
    os.makedirs(request_dir, exist_ok=True)
    os.makedirs(response_dir, exist_ok=True)
    stop_event = threading.Event()

    def run_worker() -> None:
        last_status = None
        last_status_at = 0.0
        while not stop_event.is_set():
            try:
                names = sorted(name for name in os.listdir(request_dir) if name.endswith(".json"))
            except OSError:
                names = []

            for name in names:
                request_path = os.path.join(request_dir, name)
                try:
                    with open(request_path, "r", encoding="utf-8") as file_handle:
                        request = json.load(file_handle)
                    os.unlink(request_path)
                except (OSError, json.JSONDecodeError):
                    continue

                request_id = str(request.get("request_id") or "") if isinstance(request, dict) else ""
                if not request_id or not request_id.isalnum():
                    continue
                if int(time.time()) - int(request.get("created_at", 0) or 0) > 30:
                    response = {"ok": False, "error": "Hosted RPC request expired"}
                else:
                    response = _apply_request(bot, request)
                status = _write_status(bot, control_dir)
                response.update({
                    "activity": status["activity"],
                    "activities": status["activities"],
                    "rotation_running": status["rotation_running"],
                    "spotify_lyrics": status["spotify_lyrics"],
                })
                _write_json_atomic(os.path.join(response_dir, f"{request_id}.json"), response)

            status_key = (
                bool(getattr(bot, "connection_active", False)),
                bool(getattr(bot, "identified", False)),
                bool(isinstance(getattr(bot, "activity", None), dict)),
                _rotation_running(bot),
                tuple(sorted(_spotify_lyrics_status(bot).items())),
            )
            now = time.monotonic()
            if status_key != last_status or now - last_status_at >= 1:
                _write_status(bot, control_dir)
                last_status = status_key
                last_status_at = now
            stop_event.wait(0.15)

    threading.Thread(target=run_worker, name="hosted-rpc-control", daemon=True).start()
    return stop_event


def dispatch_hosted_rpc(control_dir: str, action: str, activity: dict[str, Any] | None = None, timeout: float = 5.0) -> dict[str, Any]:
    request_id = os.urandom(16).hex()
    request_dir = os.path.join(control_dir, "rpc_requests")
    response_dir = os.path.join(control_dir, "rpc_responses")
    request_path = os.path.join(request_dir, f"{request_id}.json")
    response_path = os.path.join(response_dir, f"{request_id}.json")
    payload = {"request_id": request_id, "action": action, "created_at": int(time.time())}
    if activity is not None:
        payload["activity"] = activity

    try:
        _write_json_atomic(request_path, payload)
    except (OSError, TypeError, ValueError) as error:
        return {"ok": False, "error": f"Could not queue hosted RPC request: {error}"}

    deadline = time.monotonic() + max(0.1, float(timeout))
    while time.monotonic() < deadline:
        try:
            with open(response_path, "r", encoding="utf-8") as file_handle:
                response = json.load(file_handle)
            os.unlink(response_path)
            return response if isinstance(response, dict) else {"ok": False, "error": "Invalid hosted RPC response"}
        except FileNotFoundError:
            threading.Event().wait(0.05)
        except (OSError, json.JSONDecodeError):
            threading.Event().wait(0.05)

    try:
        os.unlink(request_path)
    except OSError:
        pass
    return {"ok": False, "error": "Hosted client did not respond to the RPC request"}