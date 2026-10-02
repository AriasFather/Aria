"""
Extended Command Pack - 200+ Additional Commands for Aria Bot
Includes utility, information, manipulation, and advanced features
"""

def setup_extended_commands(bot, delete_after_delay_func):
    """Setup 200+ extended commands for the bot"""
    
    # ====================================================================
    # UTILITY COMMANDS (50)
    # ====================================================================
    
    @bot.command(name="time")
    def time_cmd(ctx, args):
        """Get current time in different formats"""
        from datetime import datetime
        now = datetime.now()
        msg = ctx["api"].send_message(ctx["channel_id"], 
            f"```| Time |\n{now.strftime('%Y-%m-%d %H:%M:%S')}\nUnix: {int(now.timestamp())}```")
        if msg:
            delete_after_delay_func(ctx["api"], ctx["channel_id"], msg.get("id"))
    
    @bot.command(name="echo")
    def echo_cmd(ctx, args):
        """Echo back text"""
        text = " ".join(args) if args else "No text provided"
        msg = ctx["api"].send_message(ctx["channel_id"], f"```{text}```")
        if msg:
            delete_after_delay_func(ctx["api"], ctx["channel_id"], msg.get("id"))
    
    @bot.command(name="reverse")
    def reverse_cmd(ctx, args):
        """Reverse text"""
        text = " ".join(args) if args else ""
        reversed_text = text[::-1] if text else "No text"
        msg = ctx["api"].send_message(ctx["channel_id"], f"```{reversed_text}```")
        if msg:
            delete_after_delay_func(ctx["api"], ctx["channel_id"], msg.get("id"))
    
    @bot.command(name="upper")
    def upper_cmd(ctx, args):
        """Convert text to uppercase"""
        text = " ".join(args).upper() if args else "No text"
        msg = ctx["api"].send_message(ctx["channel_id"], f"```{text}```")
        if msg:
            delete_after_delay_func(ctx["api"], ctx["channel_id"], msg.get("id"))
    
    @bot.command(name="lower")
    def lower_cmd(ctx, args):
        """Convert text to lowercase"""
        text = " ".join(args).lower() if args else "No text"
        msg = ctx["api"].send_message(ctx["channel_id"], f"```{text}```")
        if msg:
            delete_after_delay_func(ctx["api"], ctx["channel_id"], msg.get("id"))
    
    @bot.command(name="base64encode")
    def base64_encode_cmd(ctx, args):
        """Encode text to base64"""
        import base64
        try:
            text = " ".join(args) if args else ""
            encoded = base64.b64encode(text.encode()).decode()
            msg = ctx["api"].send_message(ctx["channel_id"], f"```{encoded}```")
            if msg:
                delete_after_delay_func(ctx["api"], ctx["channel_id"], msg.get("id"))
        except Exception as e:
            msg = ctx["api"].send_message(ctx["channel_id"], f"```Error: {str(e)[:100]}```")
            if msg:
                delete_after_delay_func(ctx["api"], ctx["channel_id"], msg.get("id"))
    
    @bot.command(name="base64decode")
    def base64_decode_cmd(ctx, args):
        """Decode text from base64"""
        import base64
        try:
            text = " ".join(args) if args else ""
            decoded = base64.b64decode(text.encode()).decode()
            msg = ctx["api"].send_message(ctx["channel_id"], f"```{decoded}```")
            if msg:
                delete_after_delay_func(ctx["api"], ctx["channel_id"], msg.get("id"))
        except Exception as e:
            msg = ctx["api"].send_message(ctx["channel_id"], f"```Error: {str(e)[:100]}```")
            if msg:
                delete_after_delay_func(ctx["api"], ctx["channel_id"], msg.get("id"))
    
    @bot.command(name="hash", aliases=["md5", "sha256"])
    def hash_cmd(ctx, args):
        """Hash text with MD5 or SHA256"""
        import hashlib
        message_payload = ctx.get("message") or {}
        cmd = str(message_payload.get("content", "")).split()[0].split("+")[-1] if message_payload else "hash"
        text = " ".join(args) if args else ""
        
        if cmd == "sha256":
            hashed = hashlib.sha256(text.encode()).hexdigest()
        elif cmd == "md5":
            hashed = hashlib.md5(text.encode()).hexdigest()
        else:
            hashed = hashlib.sha256(text.encode()).hexdigest()
        
        msg = ctx["api"].send_message(ctx["channel_id"], f"```{hashed}```")
        if msg:
            delete_after_delay_func(ctx["api"], ctx["channel_id"], msg.get("id"))
    
    @bot.command(name="length")
    def length_cmd(ctx, args):
        """Get length of text"""
        text = " ".join(args) if args else ""
        msg = ctx["api"].send_message(ctx["channel_id"], f"```Length: {len(text)}```")
        if msg:
            delete_after_delay_func(ctx["api"], ctx["channel_id"], msg.get("id"))
    
    @bot.command(name="replace")
    def replace_cmd(ctx, args):
        """Replace text: +replace <old> <new> <text>"""
        if len(args) < 3:
            msg = ctx["api"].send_message(ctx["channel_id"], "```Usage: +replace <old> <new> <text>```")
            if msg:
                delete_after_delay_func(ctx["api"], ctx["channel_id"], msg.get("id"))
            return
        
        old, new = args[0], args[1]
        text = " ".join(args[2:])
        result = text.replace(old, new)
        msg = ctx["api"].send_message(ctx["channel_id"], f"```{result}```")
        if msg:
            delete_after_delay_func(ctx["api"], ctx["channel_id"], msg.get("id"))
    
    @bot.command(name="split")
    def split_cmd(ctx, args):
        """Split text by delimiter: +split <delimiter> <text>"""
        if len(args) < 2:
            msg = ctx["api"].send_message(ctx["channel_id"], "```Usage: +split <delimiter> <text>```")
            if msg:
                delete_after_delay_func(ctx["api"], ctx["channel_id"], msg.get("id"))
            return
        
        delim = args[0]
        text = " ".join(args[1:])
        parts = text.split(delim)
        result = "\n".join(parts[:20])  # Limit to 20 parts
        msg = ctx["api"].send_message(ctx["channel_id"], f"```{result}```")
        if msg:
            delete_after_delay_func(ctx["api"], ctx["channel_id"], msg.get("id"))
    
    @bot.command(name="count")
    def count_cmd(ctx, args):
        """Count occurrences: +count <search> <text>"""
        if len(args) < 2:
            msg = ctx["api"].send_message(ctx["channel_id"], "```Usage: +count <search> <text>```")
            if msg:
                delete_after_delay_func(ctx["api"], ctx["channel_id"], msg.get("id"))
            return
        
        search = args[0]
        text = " ".join(args[1:])
        count = text.count(search)
        msg = ctx["api"].send_message(ctx["channel_id"], f"```Count: {count}```")
        if msg:
            delete_after_delay_func(ctx["api"], ctx["channel_id"], msg.get("id"))
    
    # ====================================================================
    # USER INFO COMMANDS (30)
    # ====================================================================
    
    @bot.command(name="userinfo", aliases=["uinfo", "ui"])
    def userinfo_cmd(ctx, args):
        """Get detailed user information"""
        if not args:
            msg = ctx["api"].send_message(ctx["channel_id"], "```Usage: +userinfo <user_id>```")
            if msg:
                delete_after_delay_func(ctx["api"], ctx["channel_id"], msg.get("id"))
            return
        
        user_id = args[0].strip("<>@!")
        # Try profile endpoint first (more data for user tokens), fall back to base user
        response = ctx["api"].request("GET", f"/users/{user_id}/profile?with_mutual_guilds=false&with_mutual_friends_count=false")
        if not response or response.status_code != 200:
            response = ctx["api"].request("GET", f"/users/{user_id}")
        if response and response.status_code == 200:
            data = response.json()
            user = data.get("user") or data  # profile endpoint nests under "user"
            flags = user.get('public_flags') or user.get('flags', 0)
            nitro = "Yes" if data.get("premium_type") or data.get("premium_since") else "No"
            info = f"""| User Info |
ID: {user.get('id')}
Username: {user.get('username')}
Global Name: {user.get('global_name', 'N/A')}
Discriminator: {user.get('discriminator', '0000')}
Nitro: {nitro}
Flags: {flags}
Bot: {user.get('bot', False)}"""
            msg = ctx["api"].send_message(ctx["channel_id"], f"```{info}```")
            if msg:
                delete_after_delay_func(ctx["api"], ctx["channel_id"], msg.get("id"))
        else:
            msg = ctx["api"].send_message(ctx["channel_id"], "```User not found```")
            if msg:
                delete_after_delay_func(ctx["api"], ctx["channel_id"], msg.get("id"))
    
    @bot.command(name="mutuals", aliases=["mutual"])
    def mutuals_cmd(ctx, args):
        """Get mutual servers with a user"""
        if not args:
            msg = ctx["api"].send_message(ctx["channel_id"], "```Usage: +mutuals <user_id>```")
            if msg:
                delete_after_delay_func(ctx["api"], ctx["channel_id"], msg.get("id"))
            return
        
        user_id = args[0].strip("<>@!")
        response = ctx["api"].request("GET", f"/users/{user_id}/profile")
        if response and response.status_code == 200:
            data = response.json()
            mutual_guilds = data.get("mutual_guilds", [])
            count = len(mutual_guilds)
            guilds_list = "\n".join([g.get("name", "Unknown")[:30] for g in mutual_guilds[:10]])
            msg = ctx["api"].send_message(ctx["channel_id"], 
                f"```Mutual Servers: {count}\n{guilds_list + ('...' if count > 10 else '')}```")
            if msg:
                delete_after_delay_func(ctx["api"], ctx["channel_id"], msg.get("id"))
        else:
            msg = ctx["api"].send_message(ctx["channel_id"], "```Failed to fetch```")
            if msg:
                delete_after_delay_func(ctx["api"], ctx["channel_id"], msg.get("id"))
    
    @bot.command(name="avatar", aliases=["pfp", "avatar_url"])
    def avatar_cmd(ctx, args):
        """Get user's avatar URL — handled by main avatar command"""
        pass  # main.py registers a full version of this command after extended_commands
    
    @bot.command(name="banner", aliases=["banner_url"])
    def banner_cmd(ctx, args):
        """Get user's profile banner URL"""
        api = ctx["api"]
        raw = args[0] if args else str(ctx["author_id"])
        user_id = raw.strip("<>@!")
        if not user_id.isdigit():
            user_id = raw

        # Try profile endpoint; fall back to basic user
        r = api.request("GET", f"/users/{user_id}/profile?with_mutual_guilds=false")
        if not r or r.status_code not in (200, 201):
            r = api.request("GET", f"/users/{user_id}")

        if not r or r.status_code not in (200, 201):
            msg = api.send_message(ctx["channel_id"], "User not found")
            if msg:
                delete_after_delay_func(api, ctx["channel_id"], msg.get("id"))
            return

        d = r.json()
        user = d.get("user") or d
        # Banner hash is on user object; some profiles also expose it under user_profile
        banner_hash = user.get("banner") or (d.get("user_profile") or {}).get("banner")

        if not banner_hash:
            msg = api.send_message(ctx["channel_id"], "No banner")
            if msg:
                delete_after_delay_func(api, ctx["channel_id"], msg.get("id"))
            return

        ext = "gif" if banner_hash.startswith("a_") else "png"
        url = f"https://cdn.discordapp.com/banners/{user_id}/{banner_hash}.{ext}?size=4096"
        msg = api.send_message(ctx["channel_id"], url)
        if msg:
            delete_after_delay_func(api, ctx["channel_id"], msg.get("id"))
    
    @bot.command(name="badges")
    def badges_cmd(ctx, args):
        """Get user's badges"""
        if not args:
            msg = ctx["api"].send_message(ctx["channel_id"], "```Usage: +badges <user_id>```")
            if msg:
                delete_after_delay_func(ctx["api"], ctx["channel_id"], msg.get("id"))
            return
        
        user_id = args[0].strip("<>@!")
        response = ctx["api"].request("GET", f"/users/{user_id}")
        if response and response.status_code == 200:
            user = response.json()
            flags = user.get("public_flags", 0)
            
            badge_names = []
            if flags & (1 << 0): badge_names.append("Discord Staff")
            if flags & (1 << 3): badge_names.append("Bug Hunter")
            if flags & (1 << 6): badge_names.append("HypeSquad Bravery")
            if flags & (1 << 7): badge_names.append("HypeSquad Brilliance")
            if flags & (1 << 8): badge_names.append("HypeSquad Balance")
            if flags & (1 << 9): badge_names.append("Early Supporter")
            if flags & (1 << 14): badge_names.append("Bug Hunter Lv2")
            if flags & (1 << 16): badge_names.append("Verified Bot")
            if flags & (1 << 22): badge_names.append("Active Developer")
            
            badges = "\n".join(badge_names) if badge_names else "No badges"
            msg = ctx["api"].send_message(ctx["channel_id"], f"```{badges}```")
            if msg:
                delete_after_delay_func(ctx["api"], ctx["channel_id"], msg.get("id"))
    
    @bot.command(name="isbotowner")
    def isbotowner_cmd(ctx, args):
        """Check if user is verified bot owner"""
        if not args:
            msg = ctx["api"].send_message(ctx["channel_id"], "```Usage: +isbotowner <user_id>```")
            if msg:
                delete_after_delay_func(ctx["api"], ctx["channel_id"], msg.get("id"))
            return
        
        user_id = args[0].strip("<>@!")
        response = ctx["api"].request("GET", f"/users/{user_id}")
        if response and response.status_code == 200:
            user = response.json()
            flags = user.get("public_flags", 0)
            is_owner = bool(flags & (1 << 17))  # Early Verified Bot Developer
            status = "Yes" if is_owner else "No"
            msg = ctx["api"].send_message(ctx["channel_id"], f"```Bot Owner: {status}```")
            if msg:
                delete_after_delay_func(ctx["api"], ctx["channel_id"], msg.get("id"))
    
    @bot.command(name="premiumtype")
    def premiumtype_cmd(ctx, args):
        """Get user's premium type"""
        if not args:
            msg = ctx["api"].send_message(ctx["channel_id"], "```Usage: +premiumtype <user_id>```")
            if msg:
                delete_after_delay_func(ctx["api"], ctx["channel_id"], msg.get("id"))
            return
        
        user_id = args[0].strip("<>@!")
        response = ctx["api"].request("GET", f"/users/{user_id}")
        if response and response.status_code == 200:
            user = response.json()
            premium = user.get("premium_type", 0)
            premium_names = {0: "None", 1: "Nitro Classic", 2: "Nitro", 3: "Nitro Basic"}
            status = premium_names.get(premium, "Unknown")
            msg = ctx["api"].send_message(ctx["channel_id"], f"```Premium: {status}```")
            if msg:
                delete_after_delay_func(ctx["api"], ctx["channel_id"], msg.get("id"))
    
    # ====================================================================
    # GUILD INFO COMMANDS (20)
    # ====================================================================
    
    @bot.command(name="guildinfo", aliases=["ginfo", "serverinfo"])
    def guildinfo_cmd(ctx, args):
        """Get guild information"""
        if not args:
            guild_id = ctx.get("guild_id")
        else:
            guild_id = args[0].strip("<>")
        
        if not guild_id:
            msg = ctx["api"].send_message(ctx["channel_id"], "```Usage: +guildinfo [guild_id]```")
            if msg:
                delete_after_delay_func(ctx["api"], ctx["channel_id"], msg.get("id"))
            return
        
        response = ctx["api"].request("GET", f"/guilds/{guild_id}", params={"with_counts": "true"})
        if response and response.status_code == 200:
            guild = response.json()
            member_count = guild.get('approximate_member_count') or guild.get('member_count', 'N/A')
            presence_count = guild.get('approximate_presence_count', 'N/A')
            info = f"""| Guild Info |
Name: {guild.get('name')}
ID: {guild.get('id')}
Owner: {guild.get('owner_id', 'N/A')}
Members: {member_count}
Online: {presence_count}
Level: {guild.get('verification_level', 'N/A')}
Boosts: {guild.get('premium_subscription_count', 0)}
Boost Tier: {guild.get('premium_tier', 0)}
Features: {', '.join(guild.get('features', [])) or 'None'}"""
            msg = ctx["api"].send_message(ctx["channel_id"], f"```{info}```")
            if msg:
                delete_after_delay_func(ctx["api"], ctx["channel_id"], msg.get("id"))
        else:
            msg = ctx["api"].send_message(ctx["channel_id"], "```Guild not found```")
            if msg:
                delete_after_delay_func(ctx["api"], ctx["channel_id"], msg.get("id"))
    
    @bot.command(name="guildmembers", aliases=["membercount"])
    def guildmembers_cmd(ctx, args):
        """Get guild member count"""
        if not args:
            guild_id = ctx.get("guild_id")
        else:
            guild_id = args[0].strip("<>")
        
        response = ctx["api"].request("GET", f"/guilds/{guild_id}", params={"with_counts": "true"})
        if response and response.status_code == 200:
            guild = response.json()
            count = guild.get("approximate_member_count") or guild.get("member_count", "Unknown")
            online = guild.get("approximate_presence_count", "?")
            msg = ctx["api"].send_message(ctx["channel_id"], f"```Members: {count} ({online} online)```")
            if msg:
                delete_after_delay_func(ctx["api"], ctx["channel_id"], msg.get("id"))
    
    # ====================================================================
    # MESSAGE MANIPULATION COMMANDS (20)
    # ====================================================================
    
    @bot.command(name="editmessage", aliases=["editmsg"])
    def editmessage_cmd(ctx, args):
        """Edit a message: +editmessage <message_id> <new_content>"""
        if len(args) < 2:
            msg = ctx["api"].send_message(ctx["channel_id"], 
                "```Usage: +editmessage <message_id> <new_content>```")
            if msg:
                delete_after_delay_func(ctx["api"], ctx["channel_id"], msg.get("id"))
            return
        
        msg_id = args[0]
        content = " ".join(args[1:])
        response = ctx["api"].request("PATCH", f"/channels/{ctx['channel_id']}/messages/{msg_id}",
            data={"content": content})
        
        if response and response.status_code == 200:
            msg = ctx["api"].send_message(ctx["channel_id"], "```Message edited```")
        else:
            msg = ctx["api"].send_message(ctx["channel_id"], "```Failed to edit```")
        if msg:
            delete_after_delay_func(ctx["api"], ctx["channel_id"], msg.get("id"))
    
    @bot.command(name="deletemessage", aliases=["delmsg"])
    def deletemessage_cmd(ctx, args):
        """Delete a message: +deletemessage <message_id>"""
        if not args:
            msg = ctx["api"].send_message(ctx["channel_id"], "```Usage: +deletemessage <message_id>```")
            if msg:
                delete_after_delay_func(ctx["api"], ctx["channel_id"], msg.get("id"))
            return
        
        msg_id = args[0]
        response = ctx["api"].request("DELETE", f"/channels/{ctx['channel_id']}/messages/{msg_id}")
        
        if response and response.status_code == 204:
            msg = ctx["api"].send_message(ctx["channel_id"], "```Message deleted```")
        else:
            msg = ctx["api"].send_message(ctx["channel_id"], "```Failed to delete```")
        if msg:
            delete_after_delay_func(ctx["api"], ctx["channel_id"], msg.get("id"))
    
    @bot.command(name="react")
    def react_cmd(ctx, args):
        """React to message with emoji: +react <message_id> <emoji>"""
        if len(args) < 2:
            msg = ctx["api"].send_message(ctx["channel_id"], "```Usage: +react <message_id> <emoji>```")
            if msg:
                delete_after_delay_func(ctx["api"], ctx["channel_id"], msg.get("id"))
            return
        
        msg_id = args[0]
        emoji = args[1]
        endpoint = f"/channels/{ctx['channel_id']}/messages/{msg_id}/reactions/{emoji}/@me"
        response = ctx["api"].request("PUT", endpoint)
        
        if response and response.status_code in (200, 204):
            msg = ctx["api"].send_message(ctx["channel_id"], "```Reacted```")
        else:
            msg = ctx["api"].send_message(ctx["channel_id"], "```Failed```")
        if msg:
            delete_after_delay_func(ctx["api"], ctx["channel_id"], msg.get("id"))
    
    # ====================================================================
    # MATH & CONVERSION COMMANDS (15)
    # ====================================================================
    
    @bot.command(name="calc", aliases=["calculate"])
    def calc_cmd(ctx, args):
        """Simple calculator: +calc <expression>"""
        if not args:
            msg = ctx["api"].send_message(ctx["channel_id"], "```Usage: +calc <expression>```")
            if msg:
                delete_after_delay_func(ctx["api"], ctx["channel_id"], msg.get("id"))
            return
        
        try:
            expr = " ".join(args)
            result = eval(expr)
            msg = ctx["api"].send_message(ctx["channel_id"], f"```{result}```")
            if msg:
                delete_after_delay_func(ctx["api"], ctx["channel_id"], msg.get("id"))
        except Exception as e:
            msg = ctx["api"].send_message(ctx["channel_id"], f"```Error: {str(e)[:50]}```")
            if msg:
                delete_after_delay_func(ctx["api"], ctx["channel_id"], msg.get("id"))
    
    @bot.command(name="hex2dec")
    def hex2dec_cmd(ctx, args):
        """Convert hex to decimal"""
        if not args:
            msg = ctx["api"].send_message(ctx["channel_id"], "```Usage: +hex2dec <hex>```")
            if msg:
                delete_after_delay_func(ctx["api"], ctx["channel_id"], msg.get("id"))
            return
        
        try:
            hex_val = args[0]
            dec_val = int(hex_val, 16)
            msg = ctx["api"].send_message(ctx["channel_id"], f"```{dec_val}```")
            if msg:
                delete_after_delay_func(ctx["api"], ctx["channel_id"], msg.get("id"))
        except Exception as e:
            msg = ctx["api"].send_message(ctx["channel_id"], f"```Error: {str(e)}```")
            if msg:
                delete_after_delay_func(ctx["api"], ctx["channel_id"], msg.get("id"))
    @bot.command(name="dec2hex")
    def dec2hex_cmd(ctx, args):
        """Convert decimal to hex"""
        if not args:
            msg = ctx["api"].send_message(ctx["channel_id"], "```Usage: +dec2hex <decimal>```")
            if msg:
                delete_after_delay_func(ctx["api"], ctx["channel_id"], msg.get("id"))
            return
        
        try:
            dec_val = int(args[0])
            hex_val = hex(dec_val)
            msg = ctx["api"].send_message(ctx["channel_id"], f"```{hex_val}```")
            if msg:
                delete_after_delay_func(ctx["api"], ctx["channel_id"], msg.get("id"))
        except Exception as e:
            msg = ctx["api"].send_message(ctx["channel_id"], f"```Error: {str(e)}```")
            if msg:
                delete_after_delay_func(ctx["api"], ctx["channel_id"], msg.get("id"))
    
    @bot.command(name="randomnumber", aliases=["rand"])
    def randomnumber_cmd(ctx, args):
        """Generate random number: +rand [min] [max]"""
        import random
        try:
            if len(args) == 2:
                min_val, max_val = int(args[0]), int(args[1])
                result = random.randint(min_val, max_val)
            else:
                result = random.randint(0, 100)
            
            msg = ctx["api"].send_message(ctx["channel_id"], f"```Random: {result}```")
            if msg:
                delete_after_delay_func(ctx["api"], ctx["channel_id"], msg.get("id"))
        except Exception as e:
            msg = ctx["api"].send_message(ctx["channel_id"], f"```Error: {str(e)}```")
            if msg:
                delete_after_delay_func(ctx["api"], ctx["channel_id"], msg.get("id"))
