import json
import os
from typing import Any


def build_command_registry(bot: Any) -> dict[str, Any]:
    commands: dict[str, dict[str, Any]] = {}

    def value_for(command: Any, name: str, default: Any = None) -> Any:
        if isinstance(command, dict):
            return command.get(name, default)
        return getattr(command, name, default)

    def add_command(key: Any, command: Any) -> None:
        name = str(value_for(command, "name", "") or key or "").strip().lower()
        if not name:
            return
        row = commands.setdefault(name, {"name": name, "aliases": [], "description": "", "recent_usage": 0})
        description = str(value_for(command, "description", "") or "").strip()
        if description and not row["description"]:
            row["description"] = description
        aliases = value_for(command, "aliases", []) or []
        if isinstance(aliases, str):
            aliases = [aliases]
        known_aliases = set(row["aliases"])
        for alias in aliases:
            normalized = str(alias or "").strip().lower()
            if normalized and normalized != name and normalized not in known_aliases:
                row["aliases"].append(normalized)
                known_aliases.add(normalized)

    bot_commands = getattr(bot, "commands", {}) or {}
    for command_key, command in bot_commands.items():
        add_command(command_key, command)

    engine = getattr(bot, "command_engine", None)
    engine_commands = getattr(engine, "all_commands", {}) if engine is not None else {}
    for command_key, command in (engine_commands or {}).items():
        add_command(command_key, command)

    rows = sorted(commands.values(), key=lambda command: command["name"])
    for row in rows:
        row["aliases"].sort()

    prefix = str(getattr(bot, "prefix", "$") or "$")
    return {"version": 1, "prefix": prefix, "commands": rows, "total": len(rows)}


def write_command_registry(bot: Any, path: str) -> dict[str, Any]:
    registry = build_command_registry(bot)
    target = os.path.abspath(path)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    temporary = f"{target}.{os.getpid()}.tmp"
    with open(temporary, "w", encoding="utf-8") as file_handle:
        json.dump(registry, file_handle, ensure_ascii=True)
    os.replace(temporary, target)
    return registry


def load_command_registry(path: str) -> dict[str, Any] | None:
    try:
        with open(path, "r", encoding="utf-8") as file_handle:
            payload = json.load(file_handle)
    except (OSError, json.JSONDecodeError):
        return None

    if not isinstance(payload, dict) or payload.get("version") != 1:
        return None
    rows = payload.get("commands")
    if not isinstance(rows, list):
        return None

    commands = []
    for item in rows:
        if not isinstance(item, dict) or not str(item.get("name") or "").strip():
            continue
        aliases = item.get("aliases") if isinstance(item.get("aliases"), list) else []
        commands.append({
            "name": str(item["name"]),
            "aliases": [str(alias) for alias in aliases],
            "description": str(item.get("description") or ""),
            "recent_usage": 0,
        })

    commands.sort(key=lambda command: command["name"])
    return {"prefix": str(payload.get("prefix") or "$"), "commands": commands, "total": len(commands)}