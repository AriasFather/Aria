"""Clan-tag controls and rotation for Aria's synchronous account client."""

from __future__ import annotations

import threading
from typing import Any, Optional


class GuildTools:
    def __init__(self, api: Any):
        self.api = api
        self._rotation_lock = threading.Lock()
        self._rotation_stop: Optional[threading.Event] = None
        self._rotation_thread: Optional[threading.Thread] = None

    def _guilds(self) -> list[dict[str, Any]]:
        try:
            return self.api.get_guilds(force=True) or []
        except Exception:
            try:
                response = self.api.request("GET", "/users/@me/guilds")
                if response and response.status_code == 200:
                    return response.json() or []
            except Exception:
                pass
        return []

    def _set_clan(self, guild_id: Optional[str], enabled: bool) -> tuple[bool, str]:
        try:
            response = self.api.request(
                "PUT",
                "/users/@me/clan",
                json={"identity_guild_id": guild_id, "identity_enabled": enabled},
            )
        except Exception as exc:
            return False, f"Clan tag request failed: {exc}"
        if response is None or getattr(response, "status_code", 0) not in (200, 204):
            status = getattr(response, "status_code", "no response")
            return False, f"Clan tag request failed (HTTP {status})."
        return True, ""

    def set_clan(self, value: str) -> str:
        guild_id = str(value or "").strip()
        if not guild_id.isdigit():
            return "Usage: setclan <guild_id>"
        if not any(str(guild.get("id")) == guild_id for guild in self._guilds()):
            return "That guild is not in your account's guild list."
        ok, error = self._set_clan(guild_id, True)
        return f"Clan tag set for guild {guild_id}." if ok else error

    def clear_clan(self) -> str:
        ok, error = self._set_clan(None, False)
        return "Clan tag cleared." if ok else error

    @property
    def rotation_running(self) -> bool:
        with self._rotation_lock:
            return bool(self._rotation_thread and self._rotation_thread.is_alive())

    @staticmethod
    def _parse_rotation(value: str) -> tuple[list[int], float]:
        parts = (value or "").split()
        delay_minutes = 10.0
        if parts and parts[-1].lower().endswith("m"):
            try:
                delay_minutes = float(parts.pop()[:-1])
            except ValueError:
                return [], 0
            if not 1 <= delay_minutes <= 1440:
                return [], 0
        if not parts or any(not part.isdigit() or int(part) < 1 for part in parts):
            return [], 0
        return list(dict.fromkeys(int(part) for part in parts)), delay_minutes

    def start_rotation(self, value: str) -> str:
        indexes, delay_minutes = self._parse_rotation(value)
        if not indexes:
            return "Usage: rotatetags <1 2 3...> [Nm] (delay: 1-1440 minutes)"
        self.stop_rotation()
        stop_event = threading.Event()
        worker = threading.Thread(
            target=self._rotate_loop,
            args=(indexes, delay_minutes, stop_event),
            name="AriaClanTagRotation",
            daemon=True,
        )
        with self._rotation_lock:
            self._rotation_stop = stop_event
            self._rotation_thread = worker
        worker.start()
        return f"Rotating {len(indexes)} clan tag(s) every {delay_minutes:g} minute(s)."

    def _rotate_loop(self, indexes: list[int], delay_minutes: float, stop_event: threading.Event) -> None:
        index = 0
        while not stop_event.is_set():
            try:
                guilds = self._guilds()
                selected_index = indexes[index % len(indexes)]
                if selected_index <= len(guilds):
                    self._set_clan(str(guilds[selected_index - 1].get("id") or ""), True)
                index += 1
            except Exception as exc:
                print(f"[guild-tools] Clan-tag rotation error: {exc}")
            if stop_event.wait(max(60.0, delay_minutes * 60.0)):
                break

    def stop_rotation(self) -> bool:
        with self._rotation_lock:
            stop_event = self._rotation_stop
            worker = self._rotation_thread
        if stop_event is None or worker is None or not worker.is_alive():
            return False
        stop_event.set()
        if worker is not threading.current_thread():
            worker.join(timeout=1.0)
        with self._rotation_lock:
            if self._rotation_thread is worker and not worker.is_alive():
                self._rotation_stop = None
                self._rotation_thread = None
        return True


def setup_guild_commands(bot: Any, delete_after_delay=None) -> GuildTools:
    tools = GuildTools(bot.api)
    bot.guild_tools = tools

    def send(ctx: dict[str, Any], text: str) -> None:
        api = ctx["api"]
        message = api.send_message(ctx["channel_id"], f"> **Guild** :: {text}")
        if message and callable(delete_after_delay):
            delete_after_delay(api, ctx["channel_id"], message.get("id"))

    @bot.command(name="setclan", aliases=["clanset", "settag"])
    def setclan_cmd(ctx, args):
        send(ctx, tools.set_clan(args[0] if args else ""))

    @bot.command(name="clearclan", aliases=["removeclan", "cleartag"])
    def clearclan_cmd(ctx, args):
        send(ctx, tools.clear_clan())

    @bot.command(name="rotatetags")
    def rotatetags_cmd(ctx, args):
        send(ctx, tools.start_rotation(" ".join(args)))

    @bot.command(name="stoprotatetags")
    def stoprotatetags_cmd(ctx, args):
        send(ctx, "Clan-tag rotation stopped." if tools.stop_rotation() else "No clan-tag rotation is active.")

    return tools