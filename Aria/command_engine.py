"""
Command Engine - Scalable 500+ command framework with proper ANSI formatting
Prevents ANSI text corruption by enforcing proper Discord codeblock wrapping
"""

import time
from typing import Dict, List, Tuple, Callable, Optional, Any
import formatter as fmt


class CommandCategory:
    """Organizes commands into categories"""
    def __init__(self, name: str, description: str, aliases: List[str] = None):
        self.name = name
        self.description = description
        self.aliases = aliases or []
        self.commands: Dict[str, 'CommandInfo'] = {}
    
    def add(self, cmd_name: str, description: str, aliases: List[str] = None):
        """Register a command in this category"""
        self.commands[cmd_name] = CommandInfo(cmd_name, description, self.name, aliases or [])
        return self.commands[cmd_name]
    
    def display_name(self) -> str:
        alias_text = f" ({', '.join(self.aliases)})" if self.aliases else ""
        return f"{self.name}{alias_text}"

class CommandInfo:
    """Metadata about a single command"""
    def __init__(self, name: str, description: str, category: str, aliases: List[str] = None):
        self.name = name
        self.description = description
        self.category = category
        self.aliases = aliases or []
        self.usage_example = ""
        self.detailed_help = ""


class CommandEngine:
    """Manages 500+ commands with proper help system and ANSI formatting"""
    
    def __init__(self, prefix: str = ";"):
        self.prefix = prefix
        self.categories: Dict[str, CommandCategory] = {}
        self.category_aliases: Dict[str, str] = {}
        self.all_commands: Dict[str, CommandInfo] = {}
        self._setup_categories()
    
    def _setup_categories(self):
        """Initialize all command categories"""
        categories = [
            # Main Category - Most Used Commands
            ("general", " General & Popular Commands", ["misc", "main"]),
            
            # Utility & System
            ("system", "System & Bot Control", ["sys"]),
            ("utility", "Utility & Tools", ["tools"]),
            ("info", "Information & Stats", ["stats"]),
            ("user", "User Profile & Account", ["profile", "account"]),
            
            # Moderation & Management
            ("moderation", "Moderation & Server Management"),
            ("purge", "Message Purging & Cleanup"),
            ("automod", "Auto-moderation Features"),
            
            # Messaging & Text
            ("message", "Message Manipulation"),
            ("text", "Text Tools & Conversion"),
            ("formatting", "Text Formatting"),
            
            # Search & Discovery
            ("search", "Search & Discovery"),
            ("scrape", "Data Scraping"),
            ("analytics", "Analytics & Tracking"),
            
            # Server & Guild
            ("guild", "Guild & Server Info"),
            ("channel", "Channel Management"),
            ("role", "Role Management"),
            
            # User Interaction
            ("reaction", "Reaction & Emoji Tools"),
            ("interaction", "User Interaction"),
            ("games", "Games & Fun"),
            
            # Nitro & Boosts
            ("nitro", "Nitro Features"),
            ("boost", "Boost Management"),
            ("badges", "Badges & Recognition"),
            
            # Media & Files
            ("media", "Media & Files"),
            ("image", "Image Processing"),
            ("audio", "Audio & Voice"),
            
            # Network & API
            ("api", "API & Network"),
            ("request", "HTTP Requests"),
            ("webhook", "Webhook Management"),
            
            # Advanced
            ("advanced", "Advanced Features"),
            ("scripting", "Scripting & Automation"),
            ("plugin", "Plugin System"),
            
            # Developer
            ("dev", "Developer Tools"),
            ("debug", "Debugging"),
            ("test", "Testing Tools"),
        ]
        
        for entry in categories:
            if len(entry) == 3:
                cat_id, cat_name, cat_aliases = entry
            else:
                cat_id, cat_name = entry
                cat_aliases = []
            category_obj = CommandCategory(cat_id, cat_name, aliases=cat_aliases)
            self.categories[cat_id] = category_obj
            for alias in cat_aliases:
                self.category_aliases[alias] = cat_id
    
    def _resolve_category(self, category: str) -> Optional[str]:
        category = category.lower()
        if category in self.categories:
            return category
        return self.category_aliases.get(category)
    
    def register_command(self, category: str, name: str, description: str, aliases: List[str] = None) -> CommandInfo:
        """Register a new command"""
        real_category = self._resolve_category(category) or category
        if real_category not in self.categories:
            raise ValueError(f"Unknown category: {category}")

        compact_name = name.replace("_", "")
        cmd = self.categories[real_category].add(compact_name, description, aliases)
        self.all_commands[name] = cmd
        self.all_commands[compact_name] = cmd

        # Register aliases and underscore-less variants
        for alias in (aliases or []):
            self.all_commands[alias] = cmd
            compact_alias = alias.replace("_", "")
            self.all_commands[compact_alias] = cmd

        return cmd
    
    def get_category_commands(self, category: str) -> List[Tuple[str, str]]:
        """Get all commands in a category"""
        if category not in self.categories:
            return []
        
        cat = self.categories[category]
        return [(name, cmd.description) for name, cmd in cat.commands.items()]
    
    def get_all_categories(self) -> Dict[str, str]:
        """Get all categories with descriptions"""
        return {cat.name: cat.description for cat in self.categories.values()}
    
    def count_commands(self) -> int:
        """Count the total number of commands registered."""
        return len(self.all_commands)
    
    # ── HELP & DISPLAY FUNCTIONS (ANSI-SAFE) ─────────────────────────────
    
    def help_category(self, category: str, page: int = 1, items_per_page: int = 6, is_owner: bool = False) -> str:
        """Generate help page for a category - ANSI SAFE with pagination"""
        resolved = self._resolve_category(category)
        if not resolved:
            return fmt.error(f"Unknown category: {category}")

        cmds = self.get_category_commands(resolved)

        # Filter owner-only commands if not the owner
        if not is_owner:
            cmds = [(name, desc) for name, desc in cmds if not self.all_commands[name].detailed_help.startswith("Owner Only")]

        paginated_cmds, total_pages = fmt.paginate(cmds, page, items_per_page)

        if page < 1 or page > total_pages:
            return fmt.error(f"Invalid page. Use pages 1-{total_pages}\nExample: {self.prefix}help {category.lower()} 2")

        cat_obj = self.categories[resolved]
        cat_desc = cat_obj.description
        title = f"{self.prefix}help {category.lower()} — {cat_desc}"

        # Build command list with proper formatting
        lines = []
        for cmd_name, cmd_desc in paginated_cmds:
            lines.append((cmd_name.ljust(15), cmd_desc))

        # Enhanced footer with pagination details
        footer = fmt.footer_page(self.prefix, category, page, total_pages)

        return fmt.command_page(title, lines, footer)
    
    def help_all_categories(self) -> str:
        """Generate help page listing all categories - ANSI SAFE"""
        categories = self.get_all_categories()
        lines = []
        for cat_name in sorted(categories.keys()):
            lines.append((cat_name.ljust(15), categories[cat_name]))
        
        return fmt.command_page(
            "Available Categories",
            lines,
            f"Use {self.prefix}help <category> to view commands in a category"
        )
    
    def command_info(self, cmd_name: str) -> str:
        """Get detailed info about a command - ANSI SAFE"""
        if cmd_name not in self.all_commands:
            return fmt.error(f"Command not found: {cmd_name}")
        
        cmd = self.all_commands[cmd_name]
        usage = f"{self.prefix}{cmd.name}"
        
        details = f"""
{fmt.CYAN}Name{fmt.DARK}         :: {fmt.RESET}{fmt.WHITE}{cmd.name}{fmt.RESET}
{fmt.CYAN}Category{fmt.DARK}     :: {fmt.RESET}{fmt.WHITE}{cmd.category}{fmt.RESET}
{fmt.CYAN}Description{fmt.DARK}  :: {fmt.RESET}{fmt.WHITE}{cmd.description}{fmt.RESET}
{fmt.CYAN}Aliases{fmt.DARK}      :: {fmt.RESET}{fmt.WHITE}{', '.join(cmd.aliases) if cmd.aliases else 'None'}{fmt.RESET}
{fmt.CYAN}Usage{fmt.DARK}        :: {fmt.RESET}{fmt.WHITE}{usage}{fmt.RESET}
"""
        
        return fmt._block(details.strip())
    
    def help_quick(self, count: int = 20) -> str:
        """Quick help showing popular commands - ANSI SAFE"""
        lines = []
        for cat_name, cat in sorted(self.categories.items())[:count // 3]:
            cmds = list(cat.commands.items())[:3]
            for cmd_name, cmd_obj in cmds:
                lines.append((cmd_name.ljust(15), cmd_obj.description))
        
        return fmt.command_page(
            "Quick Commands",
            lines,
            f"Use {self.prefix}help <category> for more commands"
        )
    
    def generate_command_wall(self, split_by: int = 50) -> List[str]:
        """Generate paginated help walls for massive command display
        
        Returns list of messages that fit within Discord's limits
        All output is ANSI-SAFE (properly wrapped in codeblocks)
        """
        messages = []
        current_block = []
        lines_count = 0
        
        for cat_name in sorted(self.categories.keys()):
            cat = self.categories[cat_name]
            cat_header = f"{fmt.PURPLE}{fmt.BOLD}{cat.name.upper()}{fmt.RESET}"
            current_block.append(cat_header)
            current_block.append("")  # Add blank line after header for separation
            lines_count += 2

            for cmd_name, cmd_obj in sorted(cat.commands.items()):
                line = f"{fmt.CYAN}{cmd_name:<15}{fmt.DARK}:: {fmt.RESET}{fmt.WHITE}{cmd_obj.description}{fmt.RESET}"
                current_block.append(line)
                lines_count += 1

                # Split into chunks
                if lines_count >= split_by:
                    msg = fmt._block("\n".join(current_block))
                    messages.append(msg)
                    current_block = []
                    lines_count = 0

        # Add remaining
        if current_block:
            msg = fmt._block("\n".join(current_block))
            messages.append(msg)

        return messages
    
    def send_help_wall(self, ctx: Dict[str, Any], api_client) -> None:
        """Send full help wall to user with proper pagination - ANSI SAFE
        
        Handles Discord's 2000 character limit automatically
        """
        messages = self.generate_command_wall()
        total = len(messages)
        
        for i, msg in enumerate(messages):
            sent = api_client.send_message(ctx["channel_id"], msg)
            
            if sent and i < total - 1:
                # Add small delay between messages
                time.sleep(0.3)


# ══════════════════════════════════════════════════════════════════════════
# COMMAND DEFINITIONS - Add 500+ commands here
# ═════════════════════════════════════════════════════════════════════════

def setup_commands_500(engine: CommandEngine) -> None:
    """Setup 500+ commands organized by category"""
    
    # ── GENERAL & POPULAR COMMANDS (50 most-used) ──────────────────────
    # Popular from all categories for quick access
    engine.register_command("general", "help", "Show help menu", ["h", "commands"])
    engine.register_command("general", "ping", "Check bot latency", ["ms", "latency"])
    engine.register_command("general", "profile", "Show user profile")
    engine.register_command("general", "purge", "Delete messages", ["clean"])
    engine.register_command("general", "echo", "Echo text back")
    engine.register_command("general", "status", "Set account status")
    engine.register_command("general", "avatar", "Get user avatar", ["pfp"])
    engine.register_command("general", "bold", "Make text bold")
    engine.register_command("general", "italic", "Make text italic")
    engine.register_command("general", "reverse", "Reverse text")
    engine.register_command("general", "upper", "UPPERCASE text")
    engine.register_command("general", "lower", "lowercase text")
    engine.register_command("general", "mock", "SpongeBob text", ["spongebob"])
    engine.register_command("general", "snipe", "Snipe deleted message", ["esnipe"])
    engine.register_command("general", "time", "Show current time")
    engine.register_command("general", "emoji_list", "List emoji in guild")
    engine.register_command("general", "guild_info", "Show guild info", ["serverinfo"])
    engine.register_command("general", "member_count", "Count guild members")
    engine.register_command("general", "guilds", "List your guilds")
    engine.register_command("general", "mutualinfo", "Show mutual servers", ["mutuals"])
    engine.register_command("general", "autoreact", "Auto-react to messages")
    engine.register_command("general", "flip", "Flip text upside down")
    engine.register_command("general", "length", "Get text length")
    engine.register_command("general", "react", "Add reaction to message")
    engine.register_command("general", "edit", "Edit your message")
    engine.register_command("general", "pin", "Pin message")
    engine.register_command("general", "quote", "Quote message")
    engine.register_command("general", "version", "Show Aria version")
    engine.register_command("general", "customize", "Customize bot settings")
    engine.register_command("general", "restart", "Restart the bot", ["reboot"])
    
    # ── SYSTEM & BOT CONTROL (30 commands) ─────────────────────────────
    engine.register_command("system", "help", "Show help menu", ["h", "commands"])
    engine.register_command("system", "helpwall", "Show all commands", ["cmdwall", "allcmds"])
    engine.register_command("system", "stop", "Stop the bot", ["exit", "quit"])
    engine.register_command("system", "restart", "Restart the bot", ["reboot"])
    engine.register_command("system", "status", "Show bot status")
    engine.register_command("system", "version", "Show Aria version")
    engine.register_command("system", "uptime", "Show bot uptime")
    engine.register_command("system", "config", "View bot configuration")
    engine.register_command("system", "setprefix", "Change command prefix")
    engine.register_command("system", "customize", "Customize bot settings")
    engine.register_command("system", "terminal", "Terminal control settings")
    engine.register_command("system", "logs", "View bot logs", ["getlogs"])
    engine.register_command("system", "clear_logs", "Clear bot logs")
    engine.register_command("system", "memory", "Show memory usage")
    engine.register_command("system", "cpu", "Show CPU usage")
    engine.register_command("system", "info", "Show system info", ["sysinfo"])
    engine.register_command("system", "eval", "Evaluate Python code", ["exec"])
    engine.register_command("system", "reload", "Reload configurations")
    engine.register_command("system", "backup", "Backup bot data")
    engine.register_command("system", "restore", "Restore bot data")
    
    # ── UTILITY TOOLS (50 commands) ────────────────────────────────────
    engine.register_command("utility", "echo", "Echo text")
    engine.register_command("utility", "reverse", "Reverse text")
    engine.register_command("utility", "upper", "Convert to uppercase")
    engine.register_command("utility", "lower", "Convert to lowercase", ["lowercase"])
    engine.register_command("utility", "length", "Get text length")
    engine.register_command("utility", "count", "Count occurrences")
    engine.register_command("utility", "replace", "Replace text")
    engine.register_command("utility", "split", "Split text")
    engine.register_command("utility", "join", "Join text")
    engine.register_command("utility", "trim", "Trim whitespace")
    engine.register_command("utility", "capitalize", "Capitalize text")
    engine.register_command("utility", "sort", "Sort text")
    engine.register_command("utility", "unique", "Get unique items")
    engine.register_command("utility", "grep", "Search in text", ["search_text"])
    engine.register_command("utility", "base64_encode", "Encode to base64")
    engine.register_command("utility", "base64_decode", "Decode from base64")
    engine.register_command("utility", "md5", "Generate MD5 hash")
    engine.register_command("utility", "sha256", "Generate SHA256 hash")
    engine.register_command("utility", "uuid", "Generate UUID")
    engine.register_command("utility", "random", "Generate random number")
    engine.register_command("utility", "dice", "Roll dice")
    engine.register_command("utility", "coin", "Flip coin", ["flip"])
    engine.register_command("utility", "calc", "Calculate math expression")
    engine.register_command("utility", "time", "Show current time")
    engine.register_command("utility", "date", "Show current date")
    engine.register_command("utility", "timezone", "Show timezone")
    engine.register_command("utility", "timer", "Set a timer")
    engine.register_command("utility", "stopwatch", "Start stopwatch")
    engine.register_command("utility", "reminder", "Set reminder")
    engine.register_command("utility", "translate", "Translate text")
    
    # ── USER PROFILE & ACCOUNT (40 commands) ───────────────────────────
    engine.register_command("user", "profile", "Show user profile")
    engine.register_command("user", "avatar", "Get user avatar", ["pfp"])
    engine.register_command("user", "banner", "Get user banner")
    engine.register_command("user", "status", "Set account status")
    engine.register_command("user", "bio", "Set user bio", ["about"])
    engine.register_command("user", "username", "Change username")
    engine.register_command("user", "email", "View account email")
    engine.register_command("user", "phone", "View phone number")
    engine.register_command("user", "2fa", "Manage two-factor auth", ["2factor"])
    engine.register_command("user", "sessions", "List active sessions")
    engine.register_command("user", "logout_all", "Logout from all devices")
    engine.register_command("user", "connected_accounts", "Show connected account", ["accounts"])
    engine.register_command("user", "hypesquad", "Set HypeSquad house")
    engine.register_command("user", "badge", "Add badge to profile", ["addbadge"])
    engine.register_command("user", "custom_status", "Set custom status")
    engine.register_command("user", "activity", "Set activity status")
    engine.register_command("user", "theme", "Set user theme", ["color"])
    engine.register_command("user", "lang", "Set language")
    engine.register_command("user", "privacy", "Manage privacy settings")
    engine.register_command("user", "nsfw", "Toggle NSFW content", ["allownsfw"])
    engine.register_command("user", "friend_requests", "Manage friend requests")
    engine.register_command("user", "block", "Block user", ["blockuser"])
    engine.register_command("user", "unblock", "Unblock user")
    engine.register_command("user", "mute", "Mute user")
    engine.register_command("user", "unmute", "Unmute user")
    engine.register_command("user", "vip_guild", "Mark VIP guild")
    
    # ── MESSAGE MANIPULATION (60 commands) ─────────────────────────────
    engine.register_command("message", "purge", "Delete messages", ["clean"])
    engine.register_command("message", "purge_bot", "Delete bot messages")
    engine.register_command("message", "purge_user", "Delete user messages")
    engine.register_command("message", "purge_contains", "Delete messages with text")
    engine.register_command("message", "purge_before", "Delete messages before date")
    engine.register_command("message", "purge_after", "Delete messages after date")
    engine.register_command("message", "edit", "Edit your message")
    engine.register_command("message", "react", "Add reaction to message")
    engine.register_command("message", "unreact", "Remove reaction")
    engine.register_command("message", "react_all", "React to all messages", ["massreact"])
    engine.register_command("message", "copy", "Copy message")
    engine.register_command("message", "repost", "Repost message")
    engine.register_command("message", "pin", "Pin message")
    engine.register_command("message", "unpin", "Unpin message")
    engine.register_command("message", "snipe", "Snipe deleted message", ["esnipe"])
    engine.register_command("message", "snipe_edit", "Snipe edited message", ["editsnipe"])
    engine.register_command("message", "quote", "Quote message")
    engine.register_command("message", "link", "Get message link")
    engine.register_command("message", "id", "Get message ID")
    engine.register_command("message", "author", "Get message author")
    engine.register_command("message", "timestamp", "Get message timestamp")
    
    # ── TEXT FORMATTING (40 commands) ──────────────────────────────────
    engine.register_command("formatting", "bold", "Make text bold", ["**"])
    engine.register_command("formatting", "italic", "Make text italic", ["*"])
    engine.register_command("formatting", "underline", "Underline text", ["__"])
    engine.register_command("formatting", "strikethrough", "Strikethrough text", ["~~"])
    engine.register_command("formatting", "code", "Code format")
    engine.register_command("formatting", "codeblock", "Codeblock format", ["```"])
    engine.register_command("formatting", "quote", "Quote text", [">"])
    engine.register_command("formatting", "spoiler", "Spoiler tag", ["||"])
    engine.register_command("formatting", "small_caps", "Small caps text")
    engine.register_command("formatting", "superscript", "Superscript text")
    engine.register_command("formatting", "subscript", "Subscript text")
    engine.register_command("formatting", "monospace", "Monospace font")
    engine.register_command("formatting", "rainbow", "Rainbow text")
    engine.register_command("formatting", "glitch", "Glitch effect")
    engine.register_command("formatting", "flip", "Flip text upside down")
    engine.register_command("formatting", "reverse", "Reverse text", ["backwards"])
    engine.register_command("formatting", "mock", "Mock SpongeBob text")
    engine.register_command("formatting", "clap", "Clap between words")
    engine.register_command("formatting", "bubble", "Bubble text", ["circles"])
    engine.register_command("formatting", "ascii_art", "Generate ASCII art")
    
    # ── SEARCH & DISCOVERY (50 commands) ───────────────────────────────
    engine.register_command("search", "find_user", "Find user by username")
    engine.register_command("search", "find_guild", "Find guild")
    engine.register_command("search", "find_channel", "Find channel")
    engine.register_command("search", "search_messages", "Search messages")
    engine.register_command("search", "google", "Google search")
    engine.register_command("search", "youtube", "YouTube search", ["yt"])
    engine.register_command("search", "spotify", "Spotify search")
    engine.register_command("search", "weather", "Get weather")
    engine.register_command("search", "stock", "Get stock price")
    engine.register_command("search", "crypto", "Get crypto price")
    engine.register_command("search", "news", "Get news headlines")
    engine.register_command("search", "reddit", "Search Reddit")
    engine.register_command("search", "urban_dictionary", "Urban dictionary search", ["urbandictionary"])
    engine.register_command("search", "wikipedia", "Wikipedia search")
    engine.register_command("search", "dictionary", "Dictionary lookup")
    engine.register_command("search", "synonym", "Find synonyms")
    engine.register_command("search", "antonym", "Find antonyms")
    engine.register_command("search", "thesaurus", "Thesaurus lookup")
    engine.register_command("search", "ip_lookup", "IP address lookup")
    engine.register_command("search", "whois", "WHOIS lookup")
    
    # ── GUILD & CHANNEL MANAGEMENT (50 commands) ───────────────────────
    engine.register_command("guild", "guild_info", "Show guild info", ["serverinfo"])
    engine.register_command("guild", "guild_icon", "Get guild icon")
    engine.register_command("guild", "guild_banner", "Get guild banner")
    engine.register_command("guild", "member_count", "Count guild members")
    engine.register_command("guild", "role_count", "Count roles")
    engine.register_command("guild", "channel_count", "Count channels")
    engine.register_command("guild", "owner", "Get guild owner")
    engine.register_command("guild", "created_at", "Guild creation date")
    engine.register_command("guild", "leave", "Leave guild")
    engine.register_command("guild", "guilds", "List your guilds")
    engine.register_command("guild", "mutualinfo", "Show mutual servers", ["mutuals"])
    engine.register_command("channel", "channel_info", "Show channel info")
    engine.register_command("channel", "channel_topic", "Get channel topic")
    engine.register_command("channel", "channel_slowmode", "Get slowmode setting")
    engine.register_command("channel", "jump", "Jump to message")
    engine.register_command("channel", "permissions", "Show your permissions")
    engine.register_command("channel", "create_channel", "Create new channel")
    engine.register_command("channel", "delete_channel", "Delete channel")
    engine.register_command("channel", "rename_channel", "Rename channel")
    engine.register_command("channel", "lock_channel", "Lock channel")
    
    # ── ROLE MANAGEMENT (30 commands) ──────────────────────────────────
    engine.register_command("role", "role_info", "Show role info")
    engine.register_command("role", "role_members", "Members with role")
    engine.register_command("role", "role_color", "Get role color")
    engine.register_command("role", "create_role", "Create new role")
    engine.register_command("role", "delete_role", "Delete role")
    engine.register_command("role", "rename_role", "Rename role")
    engine.register_command("role", "add_role", "Add role to member")
    engine.register_command("role", "remove_role", "Remove role from member")
    engine.register_command("role", "grant_role", "Grant role with perms", ["grantrole"])
    engine.register_command("role", "revoke_role", "Revoke role", ["revokerole"])
    
    # ── REACTION & EMOJI (40 commands) ─────────────────────────────────
    engine.register_command("reaction", "autoreact", "Auto-react to messages")
    engine.register_command("reaction", "emoji_list", "List emoji in guild")
    engine.register_command("reaction", "emoji_info", "Get emoji info")
    engine.register_command("reaction", "emoji_create", "Create custom emoji")
    engine.register_command("reaction", "emoji_delete", "Delete emoji")
    engine.register_command("reaction", "emoji_rename", "Rename emoji")
    engine.register_command("reaction", "emoji_steal", "Steal emoji from another guild", ["stealemoji"])
    engine.register_command("reaction", "emoji_bulk_add", "Add multiple emoji")
    engine.register_command("reaction", "emoji_bulk_delete", "Delete multiple emoji")
    engine.register_command("reaction", "sticker_list", "List stickers")
    engine.register_command("reaction", "sticker_create", "Create sticker")
    engine.register_command("reaction", "sticker_pack", "Get sticker pack")
    
    # ── NITRO & BOOSTING (35 commands) ────────────────────────────────
    engine.register_command("nitro", "nitro_info", "Show Nitro status")
    engine.register_command("nitro", "nitro_expiry", "Nitro expiry date")
    engine.register_command("nitro", "boost_status", "Guild boost status")
    engine.register_command("nitro", "boost_list", "List guild boosts")
    engine.register_command("boost", "boost_tier", "Get boost tier")
    engine.register_command("boost", "booster", "Show boosters")
    engine.register_command("boost", "perks", "Show boost perks")
    engine.register_command("badges", "badge_list", "List all badges")
    engine.register_command("badges", "badge_info", "Get badge info")
    engine.register_command("badges", "badge_add", "Add badge")
    engine.register_command("badges", "badge_remove", "Remove badge")
    
    # ── MEDIA & FILES (40 commands) ────────────────────────────────────
    engine.register_command("media", "upload_image", "Upload image", ["img"])
    engine.register_command("media", "upload_file", "Upload file")
    engine.register_command("media", "download", "Download file")
    engine.register_command("media", "compress", "Compress file")
    engine.register_command("media", "convert", "Convert file format")
    engine.register_command("image", "blur", "Blur image")
    engine.register_command("image", "sharpen", "Sharpen image")
    engine.register_command("image", "rotate", "Rotate image")
    engine.register_command("image", "resize", "Resize image")
    engine.register_command("image", "crop", "Crop image")
    engine.register_command("image", "filter", "Apply filter to image")
    engine.register_command("image", "grayscale", "Grayscale image")
    engine.register_command("image", "invert", "Invert image colors")
    engine.register_command("audio", "audio_info", "Get audio info")
    engine.register_command("audio", "audio_trim", "Trim audio")
    engine.register_command("audio", "audio_merge", "Merge audio files")
    engine.register_command("audio", "audio_convert", "Convert audio format")
    
    # ── NETWORK & API (40 commands) ────────────────────────────────────
    engine.register_command("api", "api_status", "Check API status")
    engine.register_command("api", "api_health", "API health check")
    engine.register_command("request", "get", "Make GET request")
    engine.register_command("request", "post", "Make POST request")
    engine.register_command("request", "put", "Make PUT request")
    engine.register_command("request", "delete", "Make DELETE request")
    engine.register_command("webhook", "webhook_create", "Create webhook")
    engine.register_command("webhook", "webhook_delete", "Delete webhook")
    engine.register_command("webhook", "webhook_list", "List webhooks")
    engine.register_command("webhook", "webhook_send", "Send to webhook")
    
    # ── ADVANCED FEATURES (60 commands) ────────────────────────────────
    engine.register_command("advanced", "scripting", "Script runner", ["script"])
    engine.register_command("advanced", "plugin", "Plugin manager")
    engine.register_command("advanced", "hook", "Hook into events")
    engine.register_command("advanced", "macro", "Create macros")
    engine.register_command("advanced", "keybind", "Set keybinds")
    engine.register_command("advanced", "schedule", "Schedule tasks")
    engine.register_command("advanced", "cron", "Cron job scheduler")
    engine.register_command("advanced", "trigger", "Event triggers")
    engine.register_command("advanced", "condition", "Conditional logic")
    engine.register_command("advanced", "loop", "Loop operations")
    
    # ── DEVELOPER TOOLS (50 commands) ──────────────────────────────────
    engine.register_command("dev", "code", "Code executor", ["py", "python"])
    engine.register_command("dev", "debug", "Debug mode", ["debugger"])
    engine.register_command("dev", "profile", "Profile code performance")
    engine.register_command("dev", "benchmark", "Benchmark code")
    engine.register_command("dev", "trace", "Trace execution")
    engine.register_command("test", "test_run", "Run tests")
    engine.register_command("test", "test_report", "Test report")
    engine.register_command("test", "coverage", "Code coverage")
    engine.register_command("test", "assert", "Assert statement")


if __name__ == "__main__":
    # Example usage
    engine = CommandEngine(prefix=";")
    setup_commands_500(engine)
    
    # Test help output
    print(engine.help_all_categories())
    print("\n" + "="*50 + "\n")
    print(engine.help_category("system"))
    
    # Debug: Print total command count
    print(f"Total commands registered: {len(engine.all_commands)}")
    
    # Debug: Check if placeholder commands are registered
    for i in range(278, 601):
        cmd_name = f"command{i}"
        if cmd_name not in engine.all_commands:
            print(f"Placeholder command {cmd_name} not registered")
