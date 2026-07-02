from typing import List, Optional, Tuple

import formatter as fmt
from api_client import DiscordAPIClient


def _extract_code_block(content: str) -> str:
    """Extract inner text from ```...``` blocks when present."""
    text = content.strip()
    if not (text.startswith("```") and text.endswith("```")):
        return content

    lines = text.splitlines()
    if len(lines) <= 2:
        return ""

    return "\n".join(lines[1:-1]).strip()


def _extract_title(line: str) -> Optional[str]:
    stripped = line.strip()
    if stripped.startswith("[") and stripped.endswith("]"):
        return stripped[1:-1].strip()
    return None


def _split_sections(body: str) -> List[Tuple[Optional[str], List[str]]]:
    sections: List[Tuple[Optional[str], List[str]]] = []
    current_title: Optional[str] = None
    current_lines: List[str] = []

    for raw_line in body.splitlines():
        title = _extract_title(raw_line)
        if title is not None:
            if current_title is not None or current_lines:
                sections.append((current_title, current_lines))
            current_title = title
            current_lines = []
            continue
        current_lines.append(raw_line.rstrip())

    if current_title is not None or current_lines:
        sections.append((current_title, current_lines))

    return sections


def _parse_command_lines(lines: List[str]) -> List[Tuple[str, str]]:
    commands: List[Tuple[str, str]] = []
    for line in lines:
        stripped = line.strip()
        if " :: " not in stripped:
            continue
        name, desc = stripped.split(" :: ", 1)
        commands.append((name.strip(), desc.strip()))
    return commands


def _parse_status_details(lines: List[str]) -> Tuple[dict, List[str]]:
    details = {}
    extras: List[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        if " :: " in stripped:
            continue

        if stripped.startswith(">"):
            stripped = stripped[1:].strip()

        if ": " in stripped:
            key, value = stripped.split(": ", 1)
            details[key.strip()] = value.strip()
        else:
            extras.append(stripped)

    return details, extras


def _render_section(title: Optional[str], lines: List[str]) -> str:
    cleaned = [line for line in lines if line.strip()]
    if not cleaned and title:
        return fmt._block(fmt._raw_header(title))

    commands = _parse_command_lines(cleaned)
    details, extras = _parse_status_details(cleaned)

    command_line_count = sum(1 for line in cleaned if " :: " in line)
    leftover_lines = [line for line in cleaned if " :: " not in line]

    if commands and command_line_count >= max(1, len(cleaned) - len(extras)):
        parts = []
        command_body = fmt.command_list(commands)
        if title:
            parts.append(fmt.sections(title, command_body))
        else:
            parts.append(fmt._block(command_body))
        if leftover_lines:
            extra = "\n".join(line.lstrip("> ").strip() for line in leftover_lines if line.strip())
            if extra:
                parts.append(fmt.info_block("Notes", extra))
        return "\n".join(parts)

    # Fallback
    parts = []
    if commands:
        command_body = fmt.command_list(commands)
        if title:
            parts.append(fmt.sections(title, command_body))
            title = None
        else:
            parts.append(fmt._block(command_body))
    if details:
        parts.append(fmt.status_box(title or "Details", details))
    non_command_lines = [line for line in cleaned if " :: " not in line and not line.strip().startswith(">")]
    merged_extras = extras + [line.strip() for line in non_command_lines if line.strip()]
    if merged_extras:
        parts.append(fmt.info_block(title or "Aria", "\n".join(merged_extras)))
    elif title and cleaned:
        parts.append(fmt.sections(title, "\n".join(cleaned)))
    if not parts:
        parts.append(fmt.info_block(title or "Aria", "\n".join(cleaned)))
    return "\n".join(parts)


def _format_structured_body(body: str) -> Optional[str]:
    sections = _split_sections(body)
    if not sections:
        return None

    has_titles = any(title for title, _ in sections)
    has_command_lines = any(any(" :: " in line for line in lines) for _, lines in sections)
    if not has_titles and not has_command_lines:
        return None

    section_count = len(sections)
    command_count = sum(
        1 for _, lines in sections for line in lines if " :: " in line
    )
    looks_like_static_page = (
        section_count > 1
        or command_count >= 4
        or (has_titles and len(body) >= 220)
        or (has_titles and has_command_lines)
    )
    if not looks_like_static_page:
        return None

    rendered_sections = [_render_section(title, lines) for title, lines in sections]
    body = "\n".join(section for section in rendered_sections if section)
    return body


def _merge_ansi_blocks(text: str) -> str:
    """Merge multiple > ```ansi ... > ``` blocks into one single block."""
    import re
    # Extract inner content from each ansi block
    pattern = re.compile(r'> ```ansi\n(.*?)> ```', re.DOTALL)
    matches = pattern.findall(text)
    if len(matches) <= 1:
        return text
    # Strip trailing newlines from each inner chunk, join with newline
    merged = "\n".join(chunk.rstrip("\n") for chunk in matches)
    return "> ```ansi\n" + merged + "\n> ```"


import re as _re
_SYMBOL_RE = _re.compile(r'(?<=\*\*)[✓✗⚠ℹ•·]\s*')
# Matches: > **Feature Name** :: description text
# Captures feature name and description so we can reassemble cleanly
_STATUS_RE = _re.compile(r'^(> )\*\*([^*]+)\*\*\s*::\s*(.*)$', _re.DOTALL)


def _clean_status_line(text: str) -> str:
    """Convert '> **Feature** :: description' to '> Feature description'."""
    # First strip symbols like ✓✗ from inside **...**
    text = _SYMBOL_RE.sub('', text)
    m = _STATUS_RE.match(text.rstrip())
    if m:
        prefix, feature, desc = m.group(1), m.group(2).strip(), m.group(3).strip()
        # lowercase first char of desc, bold both feature and description
        if desc:
            desc = desc[0].lower() + desc[1:]
            return f"{prefix}**{feature}** **{desc}**"
        return f"{prefix}**{feature}**"
    return text


def _format_outgoing(content: Optional[str]) -> Optional[str]:
    """Apply formatter style to outgoing command content."""
    if content is None:
        return None

    text = str(content)
    stripped = text.strip()

    if stripped.startswith("```ansi") or stripped.startswith("> ```ansi"):
        return text  # already ANSI formatted

    # Plain Discord markdown messages — clean status lines, pass everything else through
    if stripped.startswith("> ") or stripped.startswith("**"):
        # Multi-line messages: clean each line individually
        lines = text.split('\n')
        return '\n'.join(_clean_status_line(l) if l.strip().startswith('> **') else l for l in lines)

    # Preserve manual ANSI strings by wrapping once instead of reformatting structure.
    if "\u001b[" in text:
        return fmt._block(text)

    body = _extract_code_block(text)
    body = body.strip() if body else stripped

    if not body:
        return text

    structured = _format_structured_body(body)
    if structured:
        return structured

    return text


def install_global_formatter() -> None:
    """Patch API client methods so command outputs are formatted globally."""
    if getattr(DiscordAPIClient, "_aria_formatter_patched", False):
        return

    original_send = DiscordAPIClient.send_message
    original_edit = DiscordAPIClient.edit_message

    def send_message_patched(self, channel_id: str, content: str, reply_to=None, tts: bool = False):
        return original_send(self, channel_id, _format_outgoing(content), reply_to=reply_to, tts=tts)

    def edit_message_patched(self, channel_id: str, message_id: str, content: str):
        return original_edit(self, channel_id, message_id, _format_outgoing(content))

    DiscordAPIClient.send_message = send_message_patched
    DiscordAPIClient.edit_message = edit_message_patched
    DiscordAPIClient._aria_formatter_patched = True
