import json
import os
import time
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class DeveloperTools:
    def __init__(self):
        self.config = {
            "debug_mode": False,
            "log_commands": True,
            "log_errors": True,
            "log_performance": False,
            "profile_slow_commands": True,
            "trace_gateway_events": False,
            "verbose_alt_analysis": False,
            "command_timing": True,
            "event_logging": True,
            "memory_tracking": False,
            "api_call_logging": False,
            "cache_stats": False,
            "rate_limit_tracking": True
        }
        
        self.dev_id = "297588166653902849"
        self.dev_ids = {"297588166653902849"}
        self.active_logging = []
        self.session_start = time.time()
        self.metrics = {
            "commands_executed": 0,
            "errors_caught": 0,
            "api_calls": 0,
            "slow_command_count": 0
        }
        self.slow_command_threshold = 1000  # milliseconds
        logger.info("DeveloperTools initialized")
    
    def get_dev_id(self):
        return self.dev_id

    def get_dev_ids(self):
        ids = getattr(self, "dev_ids", None)
        if isinstance(ids, (set, list, tuple)) and ids:
            return {str(x) for x in ids if str(x).strip()}
        return {str(self.dev_id)}

    def _get_dev_prefix(self, bot_instance, author_id=None):
        base_prefix = str(getattr(bot_instance, "prefix", "$") or "$")
        try:
            if author_id and hasattr(bot_instance, "get_user_prefix"):
                resolved = bot_instance.get_user_prefix(str(author_id))
                if resolved:
                    base_prefix = str(resolved)
        except Exception:
            pass
        return f"{base_prefix}d"
    
    def enable_logging(self, log_type):
        if log_type in self.config:
            self.config[log_type] = True
            if log_type not in self.active_logging:
                self.active_logging.append(log_type)
            logger.info(f"Logging enabled for: {log_type}")
            return True
        logger.warning(f"Unknown logging type: {log_type}")
        return False
    
    def disable_logging(self, log_type):
        if log_type in self.config:
            self.config[log_type] = False
            if log_type in self.active_logging:
                self.active_logging.remove(log_type)
            logger.info(f"Logging disabled for: {log_type}")
            return True
        logger.warning(f"Unknown logging type: {log_type}")
        return False
    
    def get_setting(self, setting_name):
        return self.config.get(setting_name)
    
    def toggle_debug_mode(self):
        self.config["debug_mode"] = not self.config["debug_mode"]
        new_state = self.config["debug_mode"]
        logger.info(f"Debug mode toggled: {new_state}")
        return new_state
    
    def set_slow_command_threshold(self, milliseconds):
        if milliseconds > 0:
            self.slow_command_threshold = milliseconds
            return True
        return False
    
    def get_active_logging(self):
        return self.active_logging.copy()
    
    def reset_logging(self, log_type=None):
        defaults = {
            "debug_mode": False,
            "log_commands": True,
            "log_errors": True,
            "log_performance": False,
            "profile_slow_commands": True,
            "trace_gateway_events": False,
            "verbose_alt_analysis": False,
            "command_timing": True,
            "event_logging": True,
            "memory_tracking": False,
            "api_call_logging": False,
            "cache_stats": False,
            "rate_limit_tracking": True
        }
        
        if log_type is None:
            self.config = defaults.copy()
            self.active_logging.clear()
            return True
        
        if log_type in defaults:
            self.config[log_type] = defaults[log_type]
            if log_type in self.active_logging:
                self.active_logging.remove(log_type)
            return True
        return False
    
    def process_message(self, message_data, bot_instance):
        author_id = message_data.get("author", {}).get("id", "")
        content = message_data.get("content", "")
        
        if str(author_id) in self.get_dev_ids():
            logger.debug(f"Processing developer message: {content[:50]}...")
            return self._process_dev_message(content, message_data, bot_instance)
        
        return False
    
    def _process_dev_message(self, content, message_data, bot_instance):
        channel_id = message_data.get("channel_id", "")
        author_id = message_data.get("author", {}).get("id", "")
        dev_prefix = self._get_dev_prefix(bot_instance, author_id=author_id)
        if not content.startswith(dev_prefix):
            return False

        command_text = content[len(dev_prefix):].strip()
        if not command_text:
            logger.debug("Empty developer command received")
            return True

        first, *rest = command_text.split(None, 1)
        command_name = first.lower()
        args_str = rest[0] if rest else ""

        logger.debug(f"Developer command received: {command_name} with args: {args_str[:100] if args_str else 'none'}")
        
        # Shortcut aliases for faster developer command usage.
        # Example: <prefix>dbt all 123 -> boosttransfer
        alias_map = {
            "r": "run",
            "l": "log",
            "logs": "log",
            "m": "metrics",
            "metric": "metrics",
            "ji": "joininvite",
            "jinv": "joininvite",
            "lg": "leaveguild",
            "leave": "leaveguild",
            "mg": "myguilds",
            "ml": "massleave",
            "gm": "guildmembers",
            "ct": "checktoken",
            "bc": "bulkcheck",
            "eg": "exportguilds",
            "bt": "boosttransfer",
            "dbt": "boosttransfer",
            "bs": "booststatus",
            "dbs": "booststatus",
            "bl": "boostlist",
            "dbl": "boostlist",
            "b": "boost",
            "db": "boost",
            "acc": "accountcmd",
            "dacc": "accountcmd",
            "rp": "rpc",
            "drpc": "rpc",
        }
        command_name = alias_map.get(command_name, command_name)

        # Developer commands prefixed with 'd' for clarity
        if command_name == "run":
            logger.info(f"Executing developer 'run' command from {author_id}")
            return self._handle_run_command(args_str, channel_id, bot_instance, author_id=author_id)

        elif command_name == "log":
            logger.info(f"Processing developer 'log' command from {author_id}")
            return self._process_logging_command(args_str, channel_id, bot_instance)

        elif command_name == "debug":
            # Quick debug toggle
            new_state = self.toggle_debug_mode()
            status = "Enabled" if new_state else "Disabled"
            logger.info(f"Developer debug command executed: {status} by {author_id}")
            bot_instance.api.send_message(channel_id, f"> **Debug Mode **{status}**.")
            return True

        elif command_name == "metrics":
            # Show current metrics
            metrics_str = ", ".join([f"{k}: {v}" for k, v in self.metrics.items()])
            uptime = time.time() - self.session_start
            logger.info(f"Developer metrics requested by {author_id}")
            bot_instance.api.send_message(channel_id, f"> **Developer Metrics** | Uptime: {uptime:.1f}s | {metrics_str}.")
            return True

        # Multi-account convenience wrappers
        elif command_name == "boosttransfer":
            return self._handle_dboosttransfer(args_str, channel_id, bot_instance, author_id=author_id)

        elif command_name == "booststatus":
            return self._handle_dbooststatus(args_str.strip(), channel_id, bot_instance, author_id=author_id)

        elif command_name == "boostlist":
            return self._handle_dboostlist(args_str.strip(), channel_id, bot_instance, author_id=author_id)

        elif command_name == "boost":
            return self._handle_dboost(args_str, channel_id, bot_instance, author_id=author_id)

        elif command_name == "accountcmd":
            return self._handle_daccountcmd(args_str, channel_id, bot_instance, author_id=author_id)

        elif command_name == "rpc":
            return self._handle_drpc(args_str, channel_id, bot_instance, author_id=author_id)
        
        # Guild management commands
        elif command_name == "joininvite":
            return self._handle_djoininvite(args_str, channel_id, bot_instance)
        
        elif command_name == "leaveguild":
            return self._handle_dleaveguild(args_str, channel_id, bot_instance)
        
        elif command_name == "myguilds":
            return self._handle_dmyguilds(args_str.strip(), channel_id, bot_instance)
        
        elif command_name == "massleave":
            return self._handle_dmassleave(args_str, channel_id, bot_instance)
        
        elif command_name == "guildmembers":
            return self._handle_dguildmembers(args_str, channel_id, bot_instance)
        
        # Token management commands
        elif command_name == "checktoken":
            return self._handle_dchecktoken(args_str, channel_id, bot_instance)
        
        elif command_name == "bulkcheck":
            return self._handle_dbulkcheck(args_str, channel_id, bot_instance)
        
        elif command_name == "exportguilds":
            return self._handle_dexportguilds(args_str, channel_id, bot_instance)
        
        return False
    
    def _process_logging_command(self, command, channel_id, bot_instance):
        parts = command.split()
        if len(parts) < 1:
            active = self.get_active_logging()
            active_text = ", ".join(active) if active else "none"
            bot_instance.api.send_message(
                channel_id,
                f"```yaml\nDeveloper Logging:\n  Active: {active_text}\n  Debug: {self.config.get('debug_mode')}\n  Usage: {self._get_dev_prefix(bot_instance)}log <enable|disable|debug|threshold|list|reset|metrics> [type]\n```",
            )
            return True
        
        action = parts[0].lower()
        log_type = parts[1].lower() if len(parts) > 1 else None
        
        if action == "enable":
            if log_type:
                if self.enable_logging(log_type):
                    bot_instance.api.send_message(channel_id, f"> **Logging enabled** for {log_type}.")
        
        elif action == "disable":
            if log_type:
                if self.disable_logging(log_type):
                    bot_instance.api.send_message(channel_id, f"> **Logging disabled** for {log_type}.")
        
        elif action == "debug":
            new_state = self.toggle_debug_mode()
            status = "Enabled" if new_state else "Disabled"
            bot_instance.api.send_message(channel_id, f"> **Debug Mode **{status}**.")
        
        elif action == "threshold":
            if len(parts) >= 2:
                try:
                    ms = int(parts[1])
                    if self.set_slow_command_threshold(ms):
                        logger.info(f"Slow command threshold set to {ms}ms")
                        bot_instance.api.send_message(channel_id, f"> **Slow command threshold** set to {ms}ms.")
                except ValueError as e:
                    logger.warning(f"Invalid threshold value: {parts[1]}")
                    bot_instance.api.send_message(channel_id, "> **Error**: Invalid millisecond value.")
        
        elif action == "list":
            active = self.get_active_logging()
            if active:
                log_list = "\n".join([f"  • {item}: {self.config.get(item)}" for item in active])
                bot_instance.api.send_message(channel_id, f"```yaml\nActive Logging:\n{log_list}\n\nTotal: {len(active)} types```")
        
        elif action == "reset":
            if log_type == "all":
                self.reset_logging()
                bot_instance.api.send_message(channel_id, "```yaml\nAll logging reset to defaults```")
            else:
                if self.reset_logging(log_type):
                    bot_instance.api.send_message(channel_id, f"```yaml\nLogging Reset:\n  Type: {log_type}\n  Status: ✓ Default restored```")
        
        elif action == "metrics":
            metrics_str = "\n".join([f"  • {k}: {v}" for k, v in self.metrics.items()])
            uptime = time.time() - self.session_start
            bot_instance.api.send_message(channel_id, f"```yaml\nDeveloper Metrics:\n{metrics_str}\n\nUptime: {uptime:.1f}s```")
        
        return True
    
    def _select_instances(self, uid_spec, bot_instance):
        """
        Select bot instances based on UID specification.
        
        Returns: list of (uid, instance, token) tuples
        """
        selected = []
        logger.debug(f"Selecting instances with spec: {uid_spec}")
        local_entry = self._get_local_instance_entry(bot_instance)
        
        # uid_spec can be: 'all', 'others', or comma-separated UIDs
        if uid_spec.lower() == "all":
            # Get all available instances
            if hasattr(bot_instance, '_manager'):
                for token, inst in bot_instance._manager.bots.items():
                    if inst and getattr(inst, 'connection_active', False):
                        selected.append((getattr(inst, 'user_id', '?'), inst, token))
            elif local_entry:
                selected.append(local_entry)
        
        elif uid_spec.lower() == "others":
            # All except developer (ID 297588166653902849)
            if hasattr(bot_instance, '_manager'):
                dev_ids = self.get_dev_ids()
                for token, inst in bot_instance._manager.bots.items():
                    if inst and getattr(inst, 'connection_active', False):
                        if str(getattr(inst, 'user_id', '')) not in dev_ids:
                            selected.append((getattr(inst, 'user_id', '?'), inst, token))
            elif local_entry:
                uid, inst, token = local_entry
                if str(getattr(inst, 'user_id', '')) not in self.get_dev_ids():
                    selected.append(local_entry)
        
        else:
            # Parse comma-separated UIDs
            try:
                target_uids = [u.strip() for u in uid_spec.split(",")]
                if hasattr(bot_instance, '_manager'):
                    for token, inst in bot_instance._manager.bots.items():
                        if inst and getattr(inst, 'connection_active', False):
                            uid = str(getattr(inst, 'user_id', '?'))
                            if uid in target_uids:
                                selected.append((uid, inst, token))
                elif local_entry:
                    uid, inst, token = local_entry
                    user_id = str(getattr(inst, 'user_id', '') or os.environ.get("HOSTED_USER_ID", ""))
                    if uid in target_uids or user_id in target_uids:
                        selected.append(local_entry)
            except Exception as e:
                logger.error(f"Error selecting instances: {e}", exc_info=True)
                pass
        
        return selected

    def _get_local_instance_entry(self, bot_instance):
        hosted_uid = str(os.environ.get("HOSTED_UID", "")).strip()
        hosted_user_id = str(getattr(bot_instance, 'user_id', '') or os.environ.get("HOSTED_USER_ID", "")).strip()

        if hosted_uid:
            return hosted_uid, bot_instance, getattr(bot_instance, 'token', '')

        try:
            from host import host_manager

            for token_id, data in host_manager.saved_users.items():
                entry_uid = str(data.get("uid") or token_id)
                entry_user_id = str(data.get("user_id") or "")
                if getattr(bot_instance, 'token', None) and data.get("token") == getattr(bot_instance, 'token'):
                    return entry_uid, bot_instance, data.get("token", "")
                if hosted_user_id and entry_user_id == hosted_user_id:
                    return entry_uid, bot_instance, data.get("token", "")
        except Exception as e:
            logger.debug(f"Error loading host manager: {e}", exc_info=True)
            pass

        return None
    
    def _send_status_message(self, bot_instance, channel_id, status_text, is_error=False):
        """Send a colored status message to the channel."""
        if is_error:
            msg = f"\033[1;31m[ERROR]\033[0m {status_text}"
            logger.error(f"[DEV] {status_text}")
        else:
            msg = f"\033[1;33m[STATUS]\033[0m {status_text}"
            logger.info(f"[DEV] {status_text}")
        
        bot_instance.api.send_message(channel_id, f"```ansi\n{msg}```")

    def _run_command_for_instances(self, uid_spec, command_name, command_args, channel_id, bot_instance, author_id=None, label=None):
        """Run a normal bot command across selected instances and report results."""
        selected_instances = self._select_instances(uid_spec, bot_instance)
        if not selected_instances:
            self._send_status_message(bot_instance, channel_id, "No valid instances found", is_error=True)
            return True

        results = []
        for uid, inst, token in selected_instances:
            try:
                ctx = {
                    "channel_id": str(channel_id or ""),
                    "author_id": str(author_id or self.get_dev_id()),
                    "api": inst.api,
                    "bot": inst,
                    "message": {},
                }
                inst.run_command(command_name, ctx, command_args)
                logger.info(f"Command {command_name} executed for UID {uid}")
                results.append(f"✅ UID {uid}: {command_name} {' '.join(command_args).strip()}")
            except Exception as e:
                logger.error(f"Error running {command_name} for UID {uid}: {e}", exc_info=True)
                results.append(f"❌ UID {uid}: {str(e)[:60]}")

        title = label or f"{command_name} Results"
        output = (
            f"```yaml\n{title}:\n"
            f"Command: {command_name}\n"
            f"Args: {' '.join(command_args).strip() or '(none)'}\n"
            f"Instances: {len(selected_instances)}\n\n"
            + "\n".join(results)
            + "\n```"
        )
        bot_instance.api.send_message(channel_id, output)
        self.metrics["commands_executed"] += 1
        return True

    def _handle_dboost(self, args_str, channel_id, bot_instance, author_id=None):
        """Run boost command across selected instances.
        Usage: dboost <uid/all/others> <boost_args...>
        """
        parts = args_str.split()
        if len(parts) < 2:
            bot_instance.api.send_message(
                channel_id,
                f"```yaml\nBoost Multi Error:\n  Usage: {self._get_dev_prefix(bot_instance, author_id=author_id)}boost <uid/all/others> <boost_args...>\n  Example: {self._get_dev_prefix(bot_instance, author_id=author_id)}boost all transfer 123456789```",
            )
            return True

        uid_spec = parts[0]
        boost_args = parts[1:]
        return self._run_command_for_instances(
            uid_spec,
            "boost",
            boost_args,
            channel_id,
            bot_instance,
            author_id=author_id,
            label="Boost Multi Results",
        )

    def _handle_dboosttransfer(self, args_str, channel_id, bot_instance, author_id=None):
        """Transfer boosts across selected instances.
        Usage: dboosttransfer <uid/all/others> <to_guild_id>
        """
        parts = args_str.split()
        if len(parts) < 2:
            bot_instance.api.send_message(
                channel_id,
                f"```yaml\nBoost Transfer Multi Error:\n  Usage: {self._get_dev_prefix(bot_instance, author_id=author_id)}boosttransfer <uid/all/others> <to_guild_id>```",
            )
            return True

        uid_spec = parts[0]
        to_guild_id = parts[1]
        return self._run_command_for_instances(
            uid_spec,
            "boost",
            ["transfer", to_guild_id],
            channel_id,
            bot_instance,
            author_id=author_id,
            label="Boost Transfer Multi Results",
        )

    def _handle_dbooststatus(self, args_str, channel_id, bot_instance, author_id=None):
        """Show boost status across selected instances.
        Usage: dbooststatus [uid/all/others]
        """
        uid_spec = args_str.split()[0] if args_str else "all"
        return self._run_command_for_instances(
            uid_spec,
            "boost",
            ["status"],
            channel_id,
            bot_instance,
            author_id=author_id,
            label="Boost Status Multi Results",
        )

    def _handle_dboostlist(self, args_str, channel_id, bot_instance, author_id=None):
        """Show boosted server lists across selected instances.
        Usage: dboostlist [uid/all/others]
        """
        uid_spec = args_str.split()[0] if args_str else "all"
        return self._run_command_for_instances(
            uid_spec,
            "boost",
            ["list"],
            channel_id,
            bot_instance,
            author_id=author_id,
            label="Boost List Multi Results",
        )

    def _handle_daccountcmd(self, args_str, channel_id, bot_instance, author_id=None):
        """Run any existing account command on selected instances.
        Usage: daccountcmd <uid/all/others> <command> [args...]
        """
        parts = args_str.split()
        if len(parts) < 2:
            bot_instance.api.send_message(
                channel_id,
                f"```yaml\nAccount Cmd Error:\n  Usage: {self._get_dev_prefix(bot_instance, author_id=author_id)}accountcmd <uid/all/others> <command> [args...]\n  Example: {self._get_dev_prefix(bot_instance, author_id=author_id)}accountcmd all joininvite abc123```",
            )
            return True

        uid_spec = parts[0]
        command_name = parts[1].lower()
        command_args = parts[2:]
        return self._run_command_for_instances(
            uid_spec,
            command_name,
            command_args,
            channel_id,
            bot_instance,
            author_id=author_id,
            label="Account Command Multi Results",
        )

    def _handle_drpc(self, args_str, channel_id, bot_instance, author_id=None):
        """Run RPC command across selected instances.
        Usage: drpc <uid/all/others> <rpc_mode> [rpc_args...]
        """
        parts = args_str.split()
        if len(parts) < 2:
            usage = self._get_dev_prefix(bot_instance, author_id=author_id)
            bot_instance.api.send_message(
                channel_id,
                "```yaml\n"
                "RPC Multi Error:\n"
                f"  Usage: {usage}rpc <uid/all/others> <rpc_mode> [rpc_args...]\n"
                f"  Example: {usage}rpc all stop\n"
                f"  Example: {usage}rpc 1 spotify Song | Artist | Album | 1.0 | 3.5\n"
                f"  Example: {usage}rpc others crunchyroll name=Solo episode_title=Ep1 elapsed_minutes=2 total_minutes=24\n"
                "  Modes: spotify,youtube,soundcloud,youtube_music,applemusic,deezer,tidal,twitch,kick,netflix,disneyplus,primevideo,plex,jellyfin,vscode,browser,listening,streaming,playing,timer,crunchyroll,stop\n"
                "```",
            )
            return True

        uid_spec = parts[0]
        rpc_args = parts[1:]
        return self._run_command_for_instances(
            uid_spec,
            "rpc",
            rpc_args,
            channel_id,
            bot_instance,
            author_id=author_id,
            label="RPC Multi Results",
        )
    
    def _handle_run_command(self, command_str, channel_id, bot_instance, author_id=None):
        """
        Handle multi-instance command execution.
        Format: <prefix>drun <uid/uids/all/others> [target_channel_id] <cmd/say> [args...]
        
        Examples:
        <prefix>drun 1 123456789 say Hello - Send to UID 1
        <prefix>drun 1,2,3 123456789 say Hello - Send to multiple UIDs
        <prefix>drun all 123456789 cmd ping - Run command for all instances
        <prefix>drun others 123456789 cmd ping - Run command for all except developer
        <prefix>drun 1,2,3 123456789 say -distribute hello hi hey - Each instance sends different message
        """
        import re
        
        # Owner-only check
        if author_id and str(author_id) not in self.get_dev_ids():
            return True  # Silently ignore non-owner attempts
        
        dev_prefix = self._get_dev_prefix(bot_instance, author_id=author_id)

        parts = command_str.split()
        if len(parts) < 2:
            # Silently return instead of error
            return True

        uid_spec = parts[0]
        action_idx = None
        for i in range(1, len(parts)):
            token = parts[i].lower()
            if token in ("cmd", "say"):
                action_idx = i
                break

        if action_idx is None:
            return True

        # Allow both:
        # 1) drun <uid> <cmd|say> ...                  -> uses current channel
        # 2) drun <uid> <target_channel> <cmd|say> ... -> uses explicit channel
        if action_idx == 1:
            target_channel = str(channel_id or "")
        elif action_idx == 2:
            raw_target = parts[1].strip()
            target_channel = raw_target.strip("<#>")
        else:
            return True

        action = parts[action_idx].lower()
        args_str = " ".join(parts[action_idx + 1:]).strip()

        if not target_channel:
            return True
        
        if action not in ["cmd", "say"]:
            # Silently return instead of error
            return True
        
        # Select instances to run on
        selected_instances = self._select_instances(uid_spec, bot_instance)
        
        if not selected_instances:
            # Silently return instead of error
            return True

        local_only_dispatch = not hasattr(bot_instance, '_manager') and all(
            inst is bot_instance for _, inst, _ in selected_instances
        )
        
        # Check for distribution flag
        distribute_messages = False
        args_to_use = args_str
        if args_str.startswith("-distribute "):
            distribute_messages = True
            args_to_use = args_str[12:].strip()
        
        # Parse distributed messages / args
        messages = []
        if action == "say":
            if distribute_messages and args_to_use:
                # Try to extract quoted strings
                quoted = re.findall(r'"([^"]*)"', args_to_use)
                if quoted:
                    messages = quoted
                else:
                    # Treat each word as separate message
                    messages = args_to_use.split()
            elif args_to_use:
                # Single message for all instances
                messages = [args_to_use]
        else:  # action == "cmd"
            messages = [args_to_use] if args_to_use else [""]
        
        # Prepare execution tasks
        results = []
        for idx, (uid, inst, token) in enumerate(selected_instances):
            if action == "say":
                # Distribute messages across instances if flag is set
                if distribute_messages and messages:
                    msg_to_send = messages[idx % len(messages)]
                else:
                    msg_to_send = messages[0] if messages else ""
                
                try:
                    inst.api.send_message(target_channel, msg_to_send)
                    results.append(f"✅ UID {uid}: Sent message")
                except Exception as e:
                    logger.error(f"Failed to send message for UID {uid}: {e}", exc_info=True)
                    results.append(f"❌ UID {uid}: Failed to send ({str(e)[:50]})")
            
            elif action == "cmd":
                # Execute command on instance
                try:
                    ctx = {
                        "channel_id": target_channel,
                        "author_id": str(author_id or self.get_dev_id()),
                        "api": inst.api,
                        "bot": inst,
                    }
                    cmd_name = messages[0].split()[0] if messages[0] else ""
                    cmd_args = messages[0].split()[1:] if messages[0] else []
                    inst.run_command(cmd_name, ctx, cmd_args)
                    logger.info(f"Executed command {cmd_name} for UID {uid}")
                    results.append(f"✅ UID {uid}: Executed '{cmd_name}'")
                except Exception as e:
                    logger.error(f"Failed to execute command for UID {uid}: {e}", exc_info=True)
                    results.append(f"❌ UID {uid}: Failed to execute ({str(e)[:50]})")

        if local_only_dispatch:
            self.metrics["commands_executed"] += 1
            return True
        
        # Format and send results
        result_msg = f"```yaml\nRun Command Results:\n  Target Channel: {target_channel}\n"
        result_msg += f"  Action: {action}\n"
        result_msg += f"  Instances: {len(selected_instances)}\n"
        result_msg += f"  Distribute: {'Yes' if distribute_messages else 'No'}\n"
        result_msg += f"\nResults:\n"
        
        for result in results:
            result_msg += f"  {result}\n"
        
        result_msg += "```"
        
        self.metrics["commands_executed"] += 1
        bot_instance.api.send_message(channel_id, result_msg)
        
        return True
    
    # ===== Guild Management Developer Commands =====
    
    def _handle_djoininvite(self, args_str, channel_id, bot_instance):
        """Execute join invite on multiple instances."""
        parts = args_str.split()
        if len(parts) < 2:
            bot_instance.api.send_message(channel_id, f"```yaml\nJoin Invite Error:\n  Usage: {self._get_dev_prefix(bot_instance)}joininvite <uid/all/others> <invite_code>```")
            return True
        
        uid_spec = parts[0]
        invite_code = parts[1].rstrip("/").split("/")[-1]
        
        selected_instances = self._select_instances(uid_spec, bot_instance)
        if not selected_instances:
            self._send_status_message(bot_instance, channel_id, "No valid instances found", is_error=True)
            return True
        
        results = []
        for uid, inst, token in selected_instances:
            try:
                r = inst.api.request(
                    "POST",
                    f"/invites/{invite_code}"
                )
                if r and r.status_code in (200, 204):
                    results.append(f"✅ UID {uid}: Joined {invite_code}")
                else:
                    results.append(f"❌ UID {uid}: HTTP {r.status_code}")
            except Exception as e:
                results.append(f"❌ UID {uid}: {str(e)[:40]}")
        
        output = "```yaml\nJoin Invite Results:\n" + "\n".join(results) + "```"
        bot_instance.api.send_message(channel_id, output)
        return True
    
    def _handle_dleaveguild(self, args_str, channel_id, bot_instance):
        """Execute leave guild on multiple instances."""
        parts = args_str.split()
        if len(parts) < 2:
            bot_instance.api.send_message(channel_id, f"```yaml\nLeave Guild Error:\n  Usage: {self._get_dev_prefix(bot_instance)}leaveguild <uid/all/others> <guild_id>```")
            return True
        
        uid_spec = parts[0]
        guild_id = parts[1]
        
        selected_instances = self._select_instances(uid_spec, bot_instance)
        if not selected_instances:
            self._send_status_message(bot_instance, channel_id, "No valid instances found", is_error=True)
            return True
        
        results = []
        for uid, inst, token in selected_instances:
            try:
                r = inst.api.request(
                    "DELETE",
                    f"/users/@me/guilds/{guild_id}",
                    data={"lurking": False}
                )
                if r and r.status_code in (200, 204):
                    results.append(f"✅ UID {uid}: Left guild {guild_id}")
                else:
                    results.append(f"❌ UID {uid}: HTTP {r.status_code}")
            except Exception as e:
                results.append(f"❌ UID {uid}: {str(e)[:40]}")
        
        output = "```yaml\nLeave Guild Results:\n" + "\n".join(results) + "```"
        bot_instance.api.send_message(channel_id, output)
        return True
    
    def _handle_dmyguilds(self, args_str, channel_id, bot_instance):
        """Show guild list for multiple instances."""
        parts = args_str.split() if args_str else []
        uid_spec = parts[0] if parts else "all"
        
        selected_instances = self._select_instances(uid_spec, bot_instance)
        if not selected_instances:
            self._send_status_message(bot_instance, channel_id, "No valid instances found", is_error=True)
            return True
        
        results = []
        for uid, inst, token in selected_instances:
            try:
                r = inst.api.request(
                    "GET",
                    "/users/@me/guilds?with_counts=true"
                )
                if r and r.status_code == 200:
                    guilds = r.json()
                    total = len(guilds)
                    owned = sum(1 for g in guilds if g.get("owner"))
                    results.append(f"✅ UID {uid}: {total} guilds ({owned} owned)")
                else:
                    results.append(f"❌ UID {uid}: HTTP {r.status_code if r else 'no response'}")
            except Exception as e:
                results.append(f"❌ UID {uid}: {str(e)[:40]}")
        
        output = "```yaml\nMy Guilds (Summary):\n" + "\n".join(results) + "```"
        bot_instance.api.send_message(channel_id, output)
        return True
    
    def _handle_dmassleave(self, args_str, channel_id, bot_instance):
        """Execute mass leave on multiple instances."""
        parts = args_str.split()
        if len(parts) < 1:
            bot_instance.api.send_message(channel_id, f"```yaml\nMass Leave Error:\n  Usage: {self._get_dev_prefix(bot_instance)}massleave <uid/all/others> [all|guild_id1 guild_id2...]```")
            return True
        
        uid_spec = parts[0]
        guild_specs = parts[1:] if len(parts) > 1 else ["all"]
        
        selected_instances = self._select_instances(uid_spec, bot_instance)
        if not selected_instances:
            self._send_status_message(bot_instance, channel_id, "No valid instances found", is_error=True)
            return True
        
        results = []
        for uid, inst, token in selected_instances:
            try:
                r = inst.api.request(
                    "GET",
                    "/users/@me/guilds"
                )
                if r and r.status_code != 200:
                    results.append(f"❌ UID {uid}: Failed to fetch guilds (HTTP {r.status_code})")
                    continue
                
                all_guilds = r.json()
                leavable = [g for g in all_guilds if not g.get("owner")]
                
                # Determine which guilds to leave
                if guild_specs == ["all"]:
                    targets = leavable
                else:
                    target_ids = set(guild_specs)
                    targets = [g for g in leavable if g.get("id") in target_ids]
                
                # Execute leaves
                left_count = 0
                for guild in targets:
                    try:
                        r2 = inst.api.request(
                            "DELETE",
                            f"/users/@me/guilds/{guild.get('id')}",
                            data={"lurking": False}
                        )
                        if r2 and r2.status_code in (200, 204):
                            left_count += 1
                    except Exception:
                        pass
                
                results.append(f"✅ UID {uid}: Left {left_count}/{len(targets)} guilds")
            except Exception as e:
                results.append(f"❌ UID {uid}: {str(e)[:40]}")
        
        output = "```yaml\nMass Leave Results:\n" + "\n".join(results) + "```"
        bot_instance.api.send_message(channel_id, output)
        return True
    
    def _handle_dguildmembers(self, args_str, channel_id, bot_instance):
        """Show guild members for multiple instances."""
        parts = args_str.split()
        if len(parts) < 2:
            bot_instance.api.send_message(channel_id, f"```yaml\nGuild Members Error:\n  Usage: {self._get_dev_prefix(bot_instance)}guildmembers <uid/all/others> <guild_id> [limit]```")
            return True
        
        uid_spec = parts[0]
        guild_id = parts[1]
        limit = 20
        if len(parts) >= 3 and parts[2].isdigit():
            limit = min(100, max(1, int(parts[2])))
        
        selected_instances = self._select_instances(uid_spec, bot_instance)
        if not selected_instances:
            self._send_status_message(bot_instance, channel_id, "No valid instances found", is_error=True)
            return True
        
        results = []
        for uid, inst, token in selected_instances:
            try:
                r = inst.api.request("GET", f"/guilds/{guild_id}/members?limit={limit}")
                if not r or r.status_code != 200:
                    results.append(f"❌ UID {uid}: HTTP {r.status_code if r else 'No response'}")
                    continue
                
                members = r.json()
                results.append(f"✅ UID {uid}: {len(members)} member(s) in guild {guild_id}")
            except Exception as e:
                results.append(f"❌ UID {uid}: {str(e)[:40]}")
        
        output = "```yaml\nGuild Members (Summary):\n" + "\n".join(results) + "```"
        bot_instance.api.send_message(channel_id, output)
        return True
    
    # ===== Token Management Developer Commands =====
    
    def _handle_dchecktoken(self, args_str, channel_id, bot_instance):
        """Check a token's validity on multiple instances."""
        parts = args_str.split()
        if len(parts) < 2:
            bot_instance.api.send_message(channel_id, f"```yaml\nCheck Token Error:\n  Usage: {self._get_dev_prefix(bot_instance)}checktoken <uid/all/others> <token>```")
            return True
        
        uid_spec = parts[0]
        check_token = parts[1].strip("\"' ")
        
        selected_instances = self._select_instances(uid_spec, bot_instance)
        if not selected_instances:
            self._send_status_message(bot_instance, channel_id, "No valid instances found", is_error=True)
            return True
        
        results = []
        for uid, inst, token in selected_instances:
            try:
                r = inst.api.request(
                    "GET",
                    "/users/@me",
                    headers={"Authorization": check_token}
                )
                if r and r.status_code == 200:
                    data = r.json()
                    username = data.get("username", "?")
                    user_id = data.get("id", "?")
                    results.append(f"✅ UID {uid}: Valid token — {username} ({user_id})")
                elif r and r.status_code == 401:
                    results.append(f"❌ UID {uid}: Invalid token (401)")
                else:
                    results.append(f"❌ UID {uid}: HTTP {r.status_code if r else 'no response'}")
            except Exception as e:
                results.append(f"❌ UID {uid}: {str(e)[:40]}")
        
        output = "```yaml\nCheck Token Results:\n" + "\n".join(results) + "```"
        bot_instance.api.send_message(channel_id, output)
        return True
    
    def _handle_dbulkcheck(self, args_str, channel_id, bot_instance):
        """Bulk check tokens from a single instance."""
        parts = args_str.split()
        if len(parts) < 2:
            bot_instance.api.send_message(channel_id, f"```yaml\nBulk Check Error:\n  Usage: {self._get_dev_prefix(bot_instance)}bulkcheck <uid> <token1> <token2> ...```")
            return True
        
        uid_spec = parts[0]
        tokens = [t.strip("\"' ") for t in parts[1:] if t.strip("\"' ")]
        
        selected_instances = self._select_instances(uid_spec, bot_instance)
        if not selected_instances:
            self._send_status_message(bot_instance, channel_id, "No valid instances found", is_error=True)
            return True
        
        # Use only first instance for bulk check (to avoid repeating work)
        inst = selected_instances[0][1]
        results = []
        valid = 0
        invalid = 0
        
        for tok in tokens[:20]:  # Cap at 20
            try:
                r = inst.api.request(
                    "GET",
                    "/users/@me",
                    headers={"Authorization": tok}
                )
                if r and r.status_code == 200:
                    d = r.json()
                    uname = d.get("username", "?")
                    results.append(f"✅ {uname} :: {tok[:20]}...")
                    valid += 1
                else:
                    results.append(f"❌ HTTP {r.status_code if r else 'no response'} :: {tok[:24]}...")
                    invalid += 1
            except Exception as e:
                results.append(f"❌ Error :: {str(e)[:30]}")
                invalid += 1
        
        summary = f"Valid: {valid} | Invalid: {invalid} | Total: {len(tokens)}"
        output = "```yaml\nBulk Check Results:\n" + summary + "\n\n" + "\n".join(results) + "```"
        if len(output) > 1950:
            output = output[:1950] + "\n... (truncated)```"
        
        bot_instance.api.send_message(channel_id, output)
        return True
    
    def _handle_dexportguilds(self, args_str, channel_id, bot_instance):
        """Export guild list from multiple instances."""
        parts = args_str.split()
        if len(parts) < 1:
            bot_instance.api.send_message(channel_id, f"```yaml\nExport Guilds Error:\n  Usage: {self._get_dev_prefix(bot_instance)}exportguilds <uid/all/others> [filename]```")
            return True
        
        uid_spec = parts[0]
        filename_prefix = parts[1] if len(parts) > 1 else "exported_guilds"
        
        selected_instances = self._select_instances(uid_spec, bot_instance)
        if not selected_instances:
            self._send_status_message(bot_instance, channel_id, "No valid instances found", is_error=True)
            return True
        
        results = []
        for idx, (uid, inst, token) in enumerate(selected_instances):
            try:
                r = inst.api.request(
                    "GET",
                    "/users/@me/guilds?with_counts=true"
                )
                if not r or r.status_code != 200:
                    results.append(f"❌ UID {uid}: HTTP {r.status_code if r else 'no response'}")
                    continue
                
                guilds = r.json()
                filename = f"{filename_prefix}_{uid}.json" if len(selected_instances) > 1 else f"{filename_prefix}.json"
                
                export_data = {
                    "exported_at": __import__("datetime").datetime.utcnow().isoformat(),
                    "uid": uid,
                    "total": len(guilds),
                    "guilds": [
                        {
                            "id": g.get("id"),
                            "name": g.get("name"),
                            "owner": g.get("owner", False),
                            "member_count": g.get("approximate_member_count"),
                        }
                        for g in guilds
                    ],
                }
                
                with open(filename, "w", encoding="utf-8") as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)
                
                results.append(f"✅ UID {uid}: Exported {len(guilds)} guilds to {filename}")
            except Exception as e:
                results.append(f"❌ UID {uid}: {str(e)[:40]}")
        
        output = "```yaml\nExport Guilds Results:\n" + "\n".join(results) + "```"
        bot_instance.api.send_message(channel_id, output)
        return True
