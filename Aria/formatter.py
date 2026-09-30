RESET = "\u001b[0m"
BOLD = "\u001b[1m"
UNDERLINE = "\u001b[4m"

DARK = "\u001b[30m"
WHITE = "\u001b[0;37m"
CYAN = "\u001b[0;36m"
PURPLE = "\u001b[0;35m"
BLUE = "\u001b[0;34m"
GREEN = "\u001b[0;32m"
RED = "\u001b[0;31m"
YELLOW = "\u001b[0;33m"
PINK = "\u001b[1;35m"

NAME = "Aria"
VERSION = "v2.0.0"
AUTHOR = "Misconsideration"

def quote_block(text: str) -> str:
    """Wrap text in quote blocks for Discord display."""
    return '\n'.join(f'> {line}' for line in text.split('\n'))

def format_message(title: str, content: str = "", status: str = None) -> str:
    """Format a message with title and optional content."""
    if status == "error":
        symbol = f"{RED}✗{RESET}"
    elif status == "success":
        symbol = f"{GREEN}✓{RESET}"
    elif status == "info":
        symbol = f"{CYAN}ℹ{RESET}"
    else:
        symbol = f"{PURPLE}•{RESET}"
    
    result = f"{symbol} {BOLD}{title}{RESET}"
    if content:
        result += f"\n{content}"
    return result

def _block(content: str) -> str:
    """Wrap content in ANSI code block."""
    lines = content.split("\n")
    result = ["```ansi"]
    result.extend(lines)
    result.append("```")
    return quote_block("\n".join(result))

def header(subtitle: str) -> str:
    """Create formatted header text (raw line, no code block)."""
    return f"{PINK}{BOLD}{UNDERLINE}{NAME}{RESET}{DARK} :: {RESET}{GREEN}{VERSION}{DARK} :: {RESET}{PINK}{subtitle}{RESET}"

def _raw_header(subtitle: str) -> str:
    """Header line without block wrapper."""
    return f"{PINK}{BOLD}{UNDERLINE}{NAME}{RESET}{DARK} :: {RESET}{GREEN}{VERSION}{DARK} :: {RESET}{PINK}{subtitle}{RESET}"

def category_list(categories: dict) -> str:
    """Format category listing as raw ANSI lines."""
    lines = []
    for name, desc in categories.items():
        lines.append(f"{PURPLE}{name:<10}{DARK}:: {RESET}{WHITE}{desc}{RESET}")
    return "\n".join(lines)

def command_list(cmds: list) -> str:
    """Format command listing as raw ANSI lines."""
    lines = []
    for name, desc in cmds:
        lines.append(f"{CYAN}{name:<13}{DARK}:: {RESET}{WHITE}{desc}{RESET}")
    return "\n".join(lines)

def status_bar(label: str, value: str, max_width: int = 40) -> str:
    """Format a status bar item."""
    value_str = str(value)[:max_width]
    return f"{CYAN}{label:<15}{DARK}:: {RESET}{WHITE}{value_str}{RESET}"

def success(msg: str) -> str:
    """Format a success message."""
    return f"{GREEN}✓ {msg}{RESET}"

def error(msg: str) -> str:
    """Format an error message."""
    return f"{RED}✗ {msg}{RESET}"

def warning(msg: str) -> str:
    """Format a warning message."""
    return f"{YELLOW}⚠ {msg}{RESET}"

    def nitro_status(status: str, claimed: int, cached: int, last_claimed=None) -> str:
        """Format Nitro sniper status output."""
        details = {
            "Status": str(status),
            "Claimed": str(claimed),
            "Cached": str(cached),
            "Last Claimed": str(last_claimed or "never"),
        }
        return status_box("Nitro", details)

    def giveaway_status(status: str, entered: int, won: int, failed: int, last_win=None) -> str:
        """Format giveaway sniper status output."""
        details = {
            "Status": str(status),
            "Entered": str(entered),
            "Won": str(won),
            "Failed": str(failed),
            "Last Win": str(last_win or "never"),
        }
        return status_box("Giveaway", details)
def nitro_status(status: str, claimed: int, cached: int, last_claimed=None) -> str:
    """Format Nitro sniper status output."""
    details = {
        "Status": str(status),
        "Claimed": str(claimed),
        "Cached": str(cached),
        "Last Claimed": str(last_claimed or "never"),
    }
    return status_box("Nitro", details)

def giveaway_status(status: str, entered: int, won: int, failed: int, last_win=None) -> str:
    """Format giveaway sniper status output."""
    details = {
        "Status": str(status),
        "Entered": str(entered),
        "Won": str(won),
        "Failed": str(failed),
        "Last Win": str(last_win or "never"),
    }
    return status_box("Giveaway", details)

def _compose(*sections) -> str:
    """Compose multiple sections into a single code block."""
    combined = "\n".join(str(s) for s in sections if s)
    return _block(combined)

def status_box(title: str, details: dict) -> str:
    """Format a status/configuration box."""
    lines = [_raw_header(str(title))]
    lines.append("")
    for key, value in details.items():
        lines.append(f"{CYAN}{key:<15}{DARK}:: {RESET}{WHITE}{str(value)}{RESET}")
    return _block("\n".join(lines))

def info_block(title: str, body: str) -> str:
    """Format a titled informational ANSI block."""
    return _block(f"{_raw_header(str(title))}\n\n{WHITE}{body}{RESET}")

def command_page(title: str, lines: list, footer: str = "") -> str:
    """Format a command page with title, command list, and optional footer."""
    result_lines = [_raw_header(title), ""]
    for name, desc in lines:
        result_lines.append(f"{CYAN}{name:<13}{DARK}:: {RESET}{WHITE}{desc}{RESET}")
    if footer:
        result_lines.append("")
        result_lines.append(f"{DARK}{footer}{RESET}")
    return _block("\n".join(result_lines))

def footer_page(prefix: str, category: str, page: int, total_pages: int) -> str:
    """Format pagination footer for command pages."""
    if total_pages <= 1:
        return f"{prefix}help {category.lower()} | page 1/1"
    return f"{prefix}help {category.lower()} | page {page}/{total_pages}"

def layout(header_text: str, body_text: str, footer_text: str) -> str:
    """Return legacy 3-block layout."""
    return "\n".join([
        _block(_raw_header(header_text)),
        _block(body_text),
        _block(f"{DARK}{footer_text}{RESET}"),
    ])

def sections(header_text: str, body_text: str, footer_text: str = "") -> str:
    """Return separated header/body/footer blocks, omitting the footer when empty."""
    parts = [
        _block(_raw_header(header_text)),
        _block(body_text),
    ]
    if str(footer_text or "").strip():
        parts.append(_block(str(footer_text)))
    return "\n".join(parts)

def panel(header_text: str, body_text: str = "", footer_text: str = "") -> str:
    """Return a single ANSI block with header, body, and optional footer."""
    parts = [_raw_header(header_text)]
    if str(body_text or "").strip():
        parts.extend(["", str(body_text)])
    if str(footer_text or "").strip():
        parts.extend(["", str(footer_text)])
    return _block("\n".join(parts))

def paginate(content: list, page: int, per_page: int = 10):
    """Paginate list content, returning (items_for_page, total_pages)."""
    total_pages = (len(content) + per_page - 1) // per_page if content else 1
    page = max(1, min(page, total_pages))
    start = (page - 1) * per_page
    end = start + per_page
    return content[start:end], total_pages

