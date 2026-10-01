"""Explicit single/cycle/multi super-reaction commands for Aria."""

from __future__ import annotations

import unicodedata
from typing import Any


def _target_id(value: str) -> str | None:
    cleaned = str(value or "").strip().strip("<@!>").replace("&", "")
    return cleaned if cleaned.isdigit() else None


def _valid_unicode_emoji(value: str) -> bool:
    keycap = "\u20e3" in value
    has_emoji_base = False
    for character in value:
        codepoint = ord(character)
        category = unicodedata.category(character)
        if category in {"So", "Sk"} or 0x1F1E6 <= codepoint <= 0x1F1FF or 0x1F3FB <= codepoint <= 0x1F3FF:
            has_emoji_base = True
            continue
        if character in {"\ufe0e", "\ufe0f", "\u200d", "\u20e3"} or category.startswith("M"):
            continue
        if keycap and character in "#*0123456789":
            continue
        return False
    return has_emoji_base or keycap


def _emoji_list(tokens: list[str]) -> list[str]:
    emojis = []
    for raw in tokens:
        for token in str(raw or "").split(","):
            emoji = token.strip()
            if not emoji:
                continue
            if emoji.startswith(("<:", "<a:")) and emoji.endswith(">"):
                parts = emoji[1:-1].split(":")
                if len(parts) == 3 and parts[1] and parts[2].isdigit():
                    emojis.append(emoji)
                    continue
                return []
            if not _valid_unicode_emoji(emoji):
                return []
            emojis.append(emoji)
    return emojis


class SuperReactControls:
    """Shared reaction configuration API backed by Aria's existing client."""

    def __init__(self, client: Any):
        self.client = client

    def set_single(self, user_id: str, emoji: str) -> tuple[bool, str]:
        normalized_id = _target_id(user_id)
        emojis = _emoji_list([emoji])
        if not normalized_id or len(emojis) != 1:
            return False, "Invalid user or emoji."
        self.client.add_target(normalized_id, emojis[0])
        return True, f"Super-reacting to {normalized_id} with {emojis[0]}."

    def set_cycle(self, user_id: str, emojis: str | list[str]) -> tuple[bool, str]:
        normalized_id = _target_id(user_id)
        tokens = emojis.split() if isinstance(emojis, str) else emojis
        normalized_emojis = _emoji_list(tokens)
        if not normalized_id or not normalized_emojis:
            return False, "Invalid user or emoji list."
        self.client.add_msr_target(normalized_id, normalized_emojis)
        return True, f"Cycling {', '.join(normalized_emojis)} on {normalized_id}."

    def set_multi(self, user_id: str, emojis: str | list[str]) -> tuple[bool, str]:
        normalized_id = _target_id(user_id)
        tokens = emojis.split() if isinstance(emojis, str) else emojis
        normalized_emojis = _emoji_list(tokens)
        if not normalized_id or not normalized_emojis:
            return False, "Invalid user or emoji list."
        self.client.add_ssr_target(normalized_id, normalized_emojis)
        return True, f"Multi-reacting with {', '.join(normalized_emojis)} on {normalized_id}."

    def unset(self, mode: str, user_id: str) -> bool:
        normalized_id = _target_id(user_id)
        if not normalized_id:
            return False
        if mode == "single":
            targets = self.client.get_targets()
            if normalized_id not in targets:
                return False
            self.client.remove_target(normalized_id)
        elif mode == "cycle":
            targets = self.client.get_msr_targets()
            if normalized_id not in targets:
                return False
            self.client.remove_msr_target(normalized_id)
        elif mode == "multi":
            targets = self.client.get_ssr_targets()
            if normalized_id not in targets:
                return False
            self.client.remove_ssr_target(normalized_id)
        else:
            raise ValueError(f"Unknown super-reaction mode: {mode}")
        return True

    def clear_user(self, user_id: str) -> bool:
        normalized_id = _target_id(user_id)
        if not normalized_id:
            return False
        removed = False
        for mode in ("single", "cycle", "multi"):
            removed = self.unset(mode, normalized_id) or removed
        return removed


def setup_superreact_commands(bot: Any) -> None:
    controls = SuperReactControls(bot.super_react_client)
    bot.super_react_controls = controls

    def _send(ctx: dict[str, Any], text: str) -> None:
        ctx["api"].send_message(ctx["channel_id"], f"> **SuperReact** :: {text}")

    def _configure(ctx: dict[str, Any], args: list[str], mode: str) -> None:
        if len(args) < 2:
            usage = {
                "cycle": "Usage: cyclesuperreact <user> <emoji1,emoji2,...>",
                "multi": "Usage: multisuperreact <user> <emoji1,emoji2,...>",
            }[mode]
            _send(ctx, usage)
            return

        user_id = _target_id(args[0])
        ok, label = (
            controls.set_cycle(user_id or "", args[1:])
            if mode == "cycle"
            else controls.set_multi(user_id or "", args[1:])
        )
        if not ok:
            _send(ctx, label)
            return
        client = controls.client
        if not client.is_running():
            try:
                started = client.start()
            except Exception as exc:
                controls.unset(mode, user_id or "")
                _send(ctx, f"Could not start reaction engine: {str(exc)[:120]}")
                return
            if not started:
                controls.unset(mode, user_id or "")
                _send(ctx, "Reaction engine did not become ready; the target was not saved.")
                return
        _send(ctx, label)

    def _stop(ctx: dict[str, Any], args: list[str], mode: str) -> None:
        user_id = _target_id(args[0]) if args else None
        if not user_id:
            _send(ctx, "Usage: provide the user ID or mention to stop.")
            return
        if controls.client is None:
            _send(ctx, "Reaction engine is unavailable.")
            return
        if not controls.unset(mode, user_id):
            _send(ctx, f"No active {mode} reaction for {user_id}.")
            return
        _send(ctx, f"Stopped {mode} reactions for {user_id}.")

    @bot.command(name="cyclesuperreact", aliases=["csr"])
    def cyclesuperreact_cmd(ctx, args):
        _configure(ctx, args, "cycle")

    @bot.command(name="multisuperreact", aliases=["msr"])
    def multisuperreact_cmd(ctx, args):
        _configure(ctx, args, "multi")

    @bot.command(name="cyclesuperreactstop", aliases=["csrstop"])
    def cyclesuperreactstop_cmd(ctx, args):
        _stop(ctx, args, "cycle")

    @bot.command(name="multisuperreactstop", aliases=["msrstop"])
    def multisuperreactstop_cmd(ctx, args):
        _stop(ctx, args, "multi")