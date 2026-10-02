"""
NEW COMMANDS FOR EXTENDED SYSTEM
Adds commands for friend scraper and self-hosting management
"""

def setup_extended_system_commands(bot, deleteAfterDelayFunc):
    setupExtendedSystemCommands(bot, deleteAfterDelayFunc)

def setupExtendedSystemCommands(bot, deleteAfterDelayFunc):
    def _prefix(ctx):
        return getattr(ctx["bot"], "prefix", ";")

    def _friend_scraper(ctx):
        return getattr(ctx["bot"], "friend_scraper", None)

    def _reply(ctx, text):
        msg = ctx["api"].send_message(ctx["channel_id"], f"```{text}```")
        if msg:
            deleteAfterDelayFunc(ctx["api"], ctx["channel_id"], msg.get("id"))
        return msg

    @bot.command(name="friends")
    def friendsCmd(ctx, args):
        scraper = _friend_scraper(ctx)
        if not scraper:
            _reply(ctx, "Friend scraper not initialized")
            return

        friendIds = scraper.get_all_friend_ids()
        if not friendIds:
            _reply(ctx, "No friends")
            return

        friendList = []
        for fid in friendIds[:20]:
            details = scraper.get_friend_details(fid) or {}
            friendList.append(f"{details.get('username', 'Unknown')} ({fid})")

        result = f"| Friends ({len(friendIds)}) |\n" + "\n".join(friendList)
        if len(friendIds) > 20:
            result += f"\n... and {len(friendIds) - 20} more"

        _reply(ctx, result)
    @bot.command(name="friendcount")
    def friendcountCmd(ctx, args):
        scraper = _friend_scraper(ctx)
        if not scraper:
            _reply(ctx, "Friend scraper not initialized")
            return

        friendIds = scraper.get_all_friend_ids()
        _reply(ctx, f"Friends: {len(friendIds)}")

    @bot.command(name="mutualfriends")
    def mutualfriendsCmd(ctx, args):
        if not args:
            _reply(ctx, f"Usage: {_prefix(ctx)}mutualfriends <user_id>")
            return

        try:
            scraper = _friend_scraper(ctx)
            if not scraper:
                _reply(ctx, "Friend scraper not initialized")
                return

            user_id = args[0].strip("<>@!")
            mutuals = scraper.get_mutual_friends_with(user_id)

            _reply(ctx, f"Mutual Friends: {len(mutuals)}\n{chr(10).join(mutuals[:10])}")
        except Exception as e:
            _reply(ctx, f"Error: {str(e)[:100]}")

    @bot.command(name="registerself", aliases=["registerhost"])
    def registerselfCmd(ctx, args):
        """Register as self-hosted: +registerself <token> [prefix]
        Owner only command
        """
        manager = getattr(ctx["bot"], "self_hosting_manager", None)
        if not manager:
            _reply(ctx, "Self-hosting not available")
            return

        if not bot.is_owner(ctx["author_id"]) and not manager.can_register(ctx["author_id"]):
            _reply(ctx, "Unauthorized: self-host registration is disabled for this user")
            return

        if len(args) < 1:
            _reply(ctx, f"Usage: {_prefix(ctx)}registerself <token> [prefix]")
            return

        token = args[0].strip('"\' ')
        prefix = args[1] if len(args) > 1 else ";"
        user_id = ctx["author_id"]

        success, message = manager.register_user(
            user_id, token, ctx["author_id"], prefix
        )
        _reply(ctx, message)

    @bot.command(name="selfhoststatus", aliases=["hostingstatus"])
    def selfhoststatusCmd(ctx, args):
        """Check self-hosting status"""
        if not hasattr(ctx["bot"], "self_hosting_manager"):
            _reply(ctx, "Self-hosting not available")
            return

        accounts = ctx["bot"].self_hosting_manager.list_hosted_accounts(ctx["author_id"])

        if not accounts:
            _reply(ctx, "No self-hosted accounts")
            return

        result = f"| Self-Hosted Accounts ({len(accounts)}) |\n"
        for acc in accounts:
            status = "enabled" if acc.get("enabled") else "disabled"
            result += f"{status} {acc['user_id']} | prefix: {acc['prefix']}\n"

        _reply(ctx, result)

    @bot.command(name="unregisterself", aliases=["unregisterhost"])
    def unregisterselfCmd(ctx, args):
        """Unregister self-hosted account: +unregisterself <user_id>"""
        if not hasattr(ctx["bot"], "self_hosting_manager"):
            _reply(ctx, "Self-hosting not available")
            return

        if not args:
            _reply(ctx, f"Usage: {_prefix(ctx)}unregisterself <user_id>")
            return

        user_id = args[0]
        success, message = ctx["bot"].self_hosting_manager.unregister_user(user_id, ctx["author_id"])

        _reply(ctx, message)

    @bot.command(name="disableselfhost")
    def disableselfhostCmd(ctx, args):
        """Disable a self-hosted account: +disableselfhost <user_id>"""
        if not hasattr(ctx["bot"], "self_hosting_manager"):
            return

        if not args:
            _reply(ctx, f"Usage: {_prefix(ctx)}disableselfhost <user_id>")
            return

        user_id = args[0]
        requester_id = None if bot.is_owner(ctx["author_id"]) else ctx["author_id"]
        success, message = ctx["bot"].self_hosting_manager.disable_account(user_id, requester_id=requester_id)
        _reply(ctx, message)

    @bot.command(name="enableselfhost")
    def enableselfhostCmd(ctx, args):
        """Enable a self-hosted account: +enableselfhost <user_id>"""
        if not hasattr(ctx["bot"], "self_hosting_manager"):
            return

        if not args:
            _reply(ctx, f"Usage: {_prefix(ctx)}enableselfhost <user_id>")
            return

        user_id = args[0]
        requester_id = None if bot.is_owner(ctx["author_id"]) else ctx["author_id"]
        success, message = ctx["bot"].self_hosting_manager.enable_account(user_id, requester_id=requester_id)
        _reply(ctx, message)

    @bot.command(name="selfhostauth")
    def selfhostauthCmd(ctx, args):
        if not bot.is_owner(ctx["author_id"]):
            _reply(ctx, "Unauthorized: owner only command")
            return

        manager = getattr(ctx["bot"], "self_hosting_manager", None)
        if not manager:
            _reply(ctx, "Self-hosting not available")
            return

        if not args:
            status = "enabled" if manager.registration_enabled else "disabled"
            users = ", ".join(manager.list_authorized_users()) or "none"
            _reply(ctx, f"Self-host auth\nRegistration: {status}\nAuthorized users: {users}")
            return

        action = args[0].lower()
        if action == "on":
            _, message = manager.set_registration_enabled(True)
        elif action == "off":
            _, message = manager.set_registration_enabled(False)
        elif action == "allow" and len(args) >= 2:
            _, message = manager.authorize_user(args[1])
        elif action in {"deny", "remove", "unauth"} and len(args) >= 2:
            _, message = manager.unauthorize_user(args[1])
        elif action == "list":
            users = ", ".join(manager.list_authorized_users()) or "none"
            message = f"Authorized users: {users}"
        else:
            message = f"Usage: {_prefix(ctx)}selfhostauth <on|off|allow <user_id>|deny <user_id>|list>"

        _reply(ctx, message)

    @bot.command(name="listallhosted")
    def listallhostedCmd(ctx, args):
        """List all hosted accounts (Owner only)"""
        if not bot.is_owner(ctx["author_id"]):
            _reply(ctx, "Unauthorized: owner only command")
            return

        if not hasattr(ctx["bot"], "self_hosting_manager"):
            _reply(ctx, "Self-hosting not available")
            return

        accounts = ctx["bot"].self_hosting_manager.list_all_accounts()

        if not accounts:
            _reply(ctx, "No hosted accounts")
            return

        result = f"| Hosted Accounts ({len(accounts)}) |\n"
        for acc in accounts:
            status = "enabled" if acc.get("enabled") else "disabled"
            result += f"{status} {acc['user_id']} | prefix: {acc['prefix']}\n"

        _reply(ctx, result)
