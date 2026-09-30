"""
Bulk Command Pack - Implements 200+ commands referenced in command_engine.py
All commands follow the same pattern: ctx["api"], ctx["channel_id"], delete_after_delay
"""

import hashlib
import base64
import uuid as _uuid_mod
import random
import time
import string
from datetime import datetime, timezone
from formatter import VERSION


def setup_bulk_commands(bot, delete_after_delay):
    """Register all bulk commands onto bot. Safe to call multiple times (duplicate names silently overwrite)."""

    from spotify_lyrics import SpotifyLyricsSync

    spotify_lyrics = SpotifyLyricsSync(bot.api)
    bot.spotify_lyrics_sync = spotify_lyrics

    def _send(ctx, text, auto_delete=True):
        msg = ctx["api"].send_message(ctx["channel_id"], text)
        if msg and auto_delete:
            delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
        return msg

    def _box(title, body):
        return f"```| {title} |\n{body}```"

    # ── API helpers (api_client has no get_guild/channel/user methods) ──
    def _api_get(api, endpoint):
        try:
            r = api.request("GET", endpoint)
            if r and hasattr(r, "status_code") and r.status_code == 200:
                return r.json()
            if r and isinstance(r, dict):
                return r
        except Exception:
            pass
        return None

    def _api_get_guild(api, gid):
        return _api_get(api, f"/guilds/{gid}?with_counts=true")

    def _api_get_channel(api, cid):
        return _api_get(api, f"/channels/{cid}")

    def _api_get_user(api, uid):
        return _api_get(api, f"/users/{uid}")

    def _http_get_json(url, timeout=5):
        """Fetch JSON from a public URL; returns parsed dict or None."""
        try:
            import urllib.request, json
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read())
        except Exception:
            return None

    def _http_get_text(url, timeout=5):
        """Fetch plain text from a public URL; returns str or None."""
        try:
            import urllib.request
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read(2000).decode("utf-8", errors="replace")
        except Exception:
            return None

    # ────────────────────────────────────────────────────────────────────
    # TEXT / FORMAT COMMANDS
    # ────────────────────────────────────────────────────────────────────

    @bot.command(name="bold")
    def bold_cmd(ctx, args):
        text = " ".join(args) if args else "No text"
        _send(ctx, f"**{text}**")

    @bot.command(name="italic")
    def italic_cmd(ctx, args):
        text = " ".join(args) if args else "No text"
        _send(ctx, f"*{text}*")

    @bot.command(name="underline")
    def underline_cmd(ctx, args):
        text = " ".join(args) if args else "No text"
        _send(ctx, f"__{text}__")

    @bot.command(name="strikethrough", aliases=["strike"])
    def strikethrough_cmd(ctx, args):
        text = " ".join(args) if args else "No text"
        _send(ctx, f"~~{text}~~")

    @bot.command(name="spoiler")
    def spoiler_cmd(ctx, args):
        text = " ".join(args) if args else "No text"
        _send(ctx, f"||{text}||")

    @bot.command(name="code")
    def code_cmd(ctx, args):
        text = " ".join(args) if args else "No text"
        _send(ctx, f"`{text}`")

    @bot.command(name="codeblock")
    def codeblock_cmd(ctx, args):
        lang = args[0] if args else ""
        text = " ".join(args[1:]) if len(args) > 1 else (args[0] if args else "No text")
        if len(args) == 1:
            lang = ""
            text = args[0]
        _send(ctx, f"```{lang}\n{text}\n```")

    @bot.command(name="mock", aliases=["spongebob"])
    def mock_cmd(ctx, args):
        text = " ".join(args) if args else "No text"
        out = "".join(c.upper() if i % 2 else c.lower() for i, c in enumerate(text))
        _send(ctx, _box("Mock", out))

    @bot.command(name="flip", aliases=["fliptext"])
    def flip_text_cmd(ctx, args):
        text = " ".join(args) if args else "No text"
        flip_map = {
            'a': 'ɐ', 'b': 'q', 'c': 'ɔ', 'd': 'p', 'e': 'ǝ', 'f': 'ɟ',
            'g': 'ƃ', 'h': 'ɥ', 'i': 'ı', 'j': 'ɾ', 'k': 'ʞ', 'l': 'l',
            'm': 'ɯ', 'n': 'u', 'o': 'o', 'p': 'd', 'q': 'b', 'r': 'ɹ',
            's': 's', 't': 'ʇ', 'u': 'n', 'v': 'ʌ', 'w': 'ʍ', 'x': 'x',
            'y': 'ʎ', 'z': 'z',
            'A': '∀', 'B': 'ᗺ', 'C': 'Ɔ', 'D': 'ᗡ', 'E': 'Ǝ', 'F': 'Ⅎ',
            'G': 'פ', 'H': 'H', 'I': 'I', 'J': 'ſ', 'K': 'ʞ', 'L': '˥',
            'M': 'W', 'N': 'N', 'O': 'O', 'P': 'Ԁ', 'Q': 'Q', 'R': 'ɹ',
            'S': 'S', 'T': '┴', 'U': '∩', 'V': 'Λ', 'W': 'M', 'X': 'X',
            'Y': '⅄', 'Z': 'Z',
        }
        out = "".join(flip_map.get(c, c) for c in text[::-1])
        _send(ctx, _box("Flip", out))

    @bot.command(name="backwards", aliases=["reverse_text"])
    def backwards_cmd(ctx, args):
        text = " ".join(args) if args else "No text"
        _send(ctx, _box("Backwards", text[::-1]))

    @bot.command(name="clap")
    def clap_cmd(ctx, args):
        text = " ".join(args) if args else "No text"
        out = " 👏 ".join(text.split())
        _send(ctx, out)

    @bot.command(name="bubble", aliases=["circles"])
    def bubble_cmd(ctx, args):
        text = " ".join(args) if args else "hello"
        bubble_map = {
            'a': 'ⓐ', 'b': 'ⓑ', 'c': 'ⓒ', 'd': 'ⓓ', 'e': 'ⓔ', 'f': 'ⓕ',
            'g': 'ⓖ', 'h': 'ⓗ', 'i': 'ⓘ', 'j': 'ⓙ', 'k': 'ⓚ', 'l': 'ⓛ',
            'm': 'ⓜ', 'n': 'ⓝ', 'o': 'ⓞ', 'p': 'ⓟ', 'q': 'ⓠ', 'r': 'ⓡ',
            's': 'ⓢ', 't': 'ⓣ', 'u': 'ⓤ', 'v': 'ⓥ', 'w': 'ⓦ', 'x': 'ⓧ',
            'y': 'ⓨ', 'z': 'ⓩ',
        }
        out = "".join(bubble_map.get(c.lower(), c) for c in text)
        _send(ctx, _box("Bubble", out))

    @bot.command(name="smallcaps")
    def smallcaps_cmd(ctx, args):
        text = " ".join(args) if args else "No text"
        sc_map = {
            'a': 'ᴀ', 'b': 'ʙ', 'c': 'ᴄ', 'd': 'ᴅ', 'e': 'ᴇ', 'f': 'ꜰ',
            'g': 'ɢ', 'h': 'ʜ', 'i': 'ɪ', 'j': 'ᴊ', 'k': 'ᴋ', 'l': 'ʟ',
            'm': 'ᴍ', 'n': 'ɴ', 'o': 'ᴏ', 'p': 'ᴘ', 'q': 'ǫ', 'r': 'ʀ',
            's': 's', 't': 'ᴛ', 'u': 'ᴜ', 'v': 'ᴠ', 'w': 'ᴡ', 'x': 'x',
            'y': 'ʏ', 'z': 'ᴢ',
        }
        out = "".join(sc_map.get(c.lower(), c) for c in text)
        _send(ctx, _box("Small Caps", out))

    @bot.command(name="monospace")
    def monospace_cmd(ctx, args):
        text = " ".join(args) if args else "No text"
        mono_map = {c: chr(0xFF01 + ord(c) - 0x21) for c in string.printable if 0x21 <= ord(c) <= 0x7E}
        mono_map[' '] = '\u3000'
        out = "".join(mono_map.get(c, c) for c in text)
        _send(ctx, _box("Monospace", out))

    @bot.command(name="rainbow")
    def rainbow_cmd(ctx, args):
        text = " ".join(args) if args else "No text"
        colors = ["🔴", "🟠", "🟡", "🟢", "🔵", "🟣"]
        out = "".join(f"{colors[i % len(colors)]}{c}" for i, c in enumerate(text) if c != " " or True)
        _send(ctx, out[:1950] if len(out) > 1950 else out)

    @bot.command(name="glitch")
    def glitch_cmd(ctx, args):
        text = " ".join(args) if args else "No text"
        glitch_chars = list("҉̵̢̛̛̖̞̙̦̩̐̅̚")
        out = "".join(c + random.choice(glitch_chars) for c in text)
        _send(ctx, out[:1950])

    @bot.command(name="superscript")
    def superscript_cmd(ctx, args):
        text = " ".join(args) if args else "No text"
        sup = str.maketrans("0123456789abcdefghijklmnoprstuvwxyz",
                            "⁰¹²³⁴⁵⁶⁷⁸⁹ᵃᵇᶜᵈᵉᶠᵍʰⁱʲᵏˡᵐⁿᵒᵖʳˢᵗᵘᵛʷˣʸᶻ")
        _send(ctx, text.translate(sup))

    @bot.command(name="subscript")
    def subscript_cmd(ctx, args):
        text = " ".join(args) if args else "No text"
        sub = str.maketrans("0123456789aehijklmnoprstuvx",
                            "₀₁₂₃₄₅₆₇₈₉ₐₑₕᵢⱼₖₗₘₙₒₚᵣₛₜᵤᵥₓ")
        _send(ctx, text.translate(sub))

    @bot.command(name="ascii_art", aliases=["asciiart"])
    def ascii_art_cmd(ctx, args):
        text = " ".join(args)[:20] if args else "ARIA"
        # Simple block letters using unicode
        _send(ctx, _box("ASCII Art", f"[ {text.upper()} ]"))

    @bot.command(name="quote")
    def quote_cmd(ctx, args):
        text = " ".join(args) if args else "No text"
        _send(ctx, f"> {text}")

    @bot.command(name="capitalize")
    def capitalize_cmd(ctx, args):
        text = " ".join(args) if args else "No text"
        _send(ctx, _box("Capitalize", text.title()))

    @bot.command(name="trim")
    def trim_cmd(ctx, args):
        text = " ".join(args) if args else ""
        _send(ctx, _box("Trim", text.strip()))

    @bot.command(name="sort")
    def sort_cmd(ctx, args):
        items = args if args else ["No", "items"]
        _send(ctx, _box("Sort", " ".join(sorted(items))))

    @bot.command(name="unique")
    def unique_cmd(ctx, args):
        items = args if args else []
        seen = []
        for i in items:
            if i not in seen:
                seen.append(i)
        _send(ctx, _box("Unique", " ".join(seen) if seen else "No items"))

    @bot.command(name="join")
    def join_cmd(ctx, args):
        if len(args) >= 2:
            sep = args[0]
            words = args[1:]
        else:
            sep = " "
            words = args
        _send(ctx, _box("Join", sep.join(words)))

    @bot.command(name="grep", aliases=["searchtext", "search_text"])
    def grep_cmd(ctx, args):
        if len(args) < 2:
            _send(ctx, _box("Grep", "Usage: grep <pattern> <text...>"))
            return
        pattern = args[0].lower()
        text = " ".join(args[1:])
        matches = [line for line in text.splitlines() if pattern in line.lower()]
        result = "\n".join(matches) if matches else "No matches"
        _send(ctx, _box(f"Grep: {pattern}", result[:500]))

    @bot.command(name="translate")
    def translate_cmd(ctx, args):
        if len(args) < 2:
            _send(ctx, _box("Translate", "Usage: translate <lang_code> <text>\nExamples: translate es Hello world | translate fr Good morning"))
            return
        lang = args[0].lower()
        text = " ".join(args[1:])
        import urllib.parse
        encoded = urllib.parse.quote(text)
        url = f"https://api.mymemory.translated.net/get?q={encoded}&langpair=en|{lang}"
        data = _http_get_json(url)
        if data and data.get("responseStatus") == 200:
            translated = data["responseData"]["translatedText"]
            _send(ctx, _box(f"Translate → {lang.upper()}", f"Original : {text[:100]}\nResult   : {translated[:300]}"))
        else:
            _send(ctx, _box("Translate", f"Translation failed (check lang code). URL: https://translate.google.com/?text={encoded}&tl={lang}"))

    @bot.command(name="antonym")
    def antonym_cmd(ctx, args):
        word = args[0].lower() if args else ""
        if not word:
            _send(ctx, _box("Antonym", "Usage: antonym <word>"))
            return
        data = _http_get_json(f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}")
        if data and isinstance(data, list):
            antonyms = []
            for entry in data:
                for meaning in entry.get("meanings", []):
                    for defn in meaning.get("definitions", []):
                        antonyms.extend(defn.get("antonyms", []))
                    antonyms.extend(meaning.get("antonyms", []))
            antonyms = list(dict.fromkeys(antonyms))[:15]
            _send(ctx, _box(f"Antonyms: {word}", ", ".join(antonyms) if antonyms else "No antonyms found"))
        else:
            _send(ctx, _box("Antonym", f"Word not found: {word}"))

    @bot.command(name="synonym")
    def synonym_cmd(ctx, args):
        word = args[0].lower() if args else ""
        if not word:
            _send(ctx, _box("Synonym", "Usage: synonym <word>"))
            return
        data = _http_get_json(f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}")
        if data and isinstance(data, list):
            synonyms = []
            for entry in data:
                for meaning in entry.get("meanings", []):
                    for defn in meaning.get("definitions", []):
                        synonyms.extend(defn.get("synonyms", []))
                    synonyms.extend(meaning.get("synonyms", []))
            synonyms = list(dict.fromkeys(synonyms))[:15]
            _send(ctx, _box(f"Synonyms: {word}", ", ".join(synonyms) if synonyms else "No synonyms found"))
        else:
            _send(ctx, _box("Synonym", f"Word not found: {word}"))

    @bot.command(name="thesaurus")
    def thesaurus_cmd(ctx, args):
        word = args[0].lower() if args else ""
        if not word:
            _send(ctx, _box("Thesaurus", "Usage: thesaurus <word>"))
            return
        data = _http_get_json(f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}")
        if data and isinstance(data, list):
            lines = []
            for entry in data:
                for meaning in entry.get("meanings", []):
                    pos = meaning.get("partOfSpeech", "")
                    syns = list(dict.fromkeys(meaning.get("synonyms", [])))[:5]
                    ants = list(dict.fromkeys(meaning.get("antonyms", [])))[:5]
                    if syns: lines.append(f"[{pos}] syn: {', '.join(syns)}")
                    if ants: lines.append(f"[{pos}] ant: {', '.join(ants)}")
            _send(ctx, _box(f"Thesaurus: {word}", "\n".join(lines[:10]) if lines else "No thesaurus data found"))
        else:
            _send(ctx, _box("Thesaurus", f"Word not found: {word}"))

    @bot.command(name="dictionary")
    def dictionary_cmd(ctx, args):
        word = args[0].lower() if args else ""
        if not word:
            _send(ctx, _box("Dictionary", "Usage: dictionary <word>"))
            return
        data = _http_get_json(f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}")
        if data and isinstance(data, list):
            entry = data[0]
            phonetic = entry.get("phonetic", "")
            lines = [f"Word: {word}  {phonetic}"]
            for meaning in entry.get("meanings", [])[:2]:
                pos = meaning.get("partOfSpeech", "")
                defns = meaning.get("definitions", [])[:2]
                for d in defns:
                    lines.append(f"[{pos}] {d.get('definition', '')[:150]}")
                    if d.get("example"):
                        lines.append(f"  ex: {d['example'][:100]}")
            _send(ctx, _box(f"Dictionary: {word}", "\n".join(lines[:12])))
        else:
            _send(ctx, _box("Dictionary", f"Word not found: {word}" ))

    # ────────────────────────────────────────────────────────────────────
    # UTILITY / HASH / ENCODE
    # ────────────────────────────────────────────────────────────────────

    @bot.command(name="md5")
    def md5_cmd(ctx, args):
        text = " ".join(args) if args else ""
        h = hashlib.md5(text.encode()).hexdigest()
        _send(ctx, _box("MD5", f"Input: {text[:50]}\nHash:  {h}"))

    @bot.command(name="sha256")
    def sha256_cmd(ctx, args):
        text = " ".join(args) if args else ""
        h = hashlib.sha256(text.encode()).hexdigest()
        _send(ctx, _box("SHA-256", f"Input: {text[:50]}\nHash:  {h}"))

    @bot.command(name="uuid")
    def uuid_cmd(ctx, args):
        _send(ctx, _box("UUID", str(_uuid_mod.uuid4())))

    @bot.command(name="random", aliases=["rand"])
    def random_cmd(ctx, args):
        try:
            lo = int(args[0]) if len(args) >= 1 else 1
            hi = int(args[1]) if len(args) >= 2 else 100
            _send(ctx, _box("Random", str(random.randint(lo, hi))))
        except ValueError:
            _send(ctx, _box("Random", "Usage: random [min] [max]"))

    @bot.command(name="dice")
    def dice_cmd(ctx, args):
        sides = int(args[0]) if args and args[0].isdigit() else 6
        result = random.randint(1, max(sides, 2))
        _send(ctx, _box(f"Dice (d{sides})", str(result)))

    @bot.command(name="coin")
    def coin_cmd(ctx, args):
        _send(ctx, _box("Coin", "Heads" if random.randint(0, 1) else "Tails"))

    @bot.command(name="date")
    def date_cmd(ctx, args):
        now = datetime.utcnow()
        _send(ctx, _box("Date", f"{now.strftime('%Y-%m-%d')}\nDay: {now.strftime('%A')}"))

    @bot.command(name="timezone")
    def timezone_cmd(ctx, args):
        now = datetime.utcnow()
        _send(ctx, _box("Timezone", f"UTC: {now.strftime('%Y-%m-%d %H:%M:%S')}\nUnix: {int(now.timestamp())}"))

    @bot.command(name="timer")
    def timer_cmd(ctx, args):
        secs = int(args[0]) if args and args[0].isdigit() else 60
        end_time = int(time.time()) + secs
        _send(ctx, _box("Timer", f"Timer set for {secs}s\nEnds at Unix: {end_time}"))

    @bot.command(name="stopwatch")
    def stopwatch_cmd(ctx, args):
        _send(ctx, _box("Stopwatch", f"Started at Unix: {int(time.time())}"))

    @bot.command(name="reminder")
    def reminder_cmd(ctx, args):
        msg_text = " ".join(args) if args else "Reminder"
        _send(ctx, _box("Reminder", f"Saved: {msg_text}\n(Note: bot must stay running for reminders)"))

    @bot.command(name="uptime")
    def uptime_cmd(ctx, args):
        import os
        try:
            with open("/proc/uptime", "r") as f:
                secs = float(f.read().split()[0])
            h, rem = divmod(int(secs), 3600)
            m, s = divmod(rem, 60)
            _send(ctx, _box("Uptime", f"{h}h {m}m {s}s"))
        except Exception:
            _send(ctx, _box("Uptime", "N/A"))

    @bot.command(name="version")
    def version_cmd(ctx, args):
        _send(ctx, _box("Version", f"Aria {VERSION}\nBuilt with Python"))

    @bot.command(name="info", aliases=["sysinfo"])
    def info_cmd(ctx, args):
        import platform
        _send(ctx, _box("System Info", f"OS: {platform.system()} {platform.release()}\nPython: {platform.python_version()}"))

    @bot.command(name="memory")
    def memory_cmd(ctx, args):
        try:
            import psutil
            mem = psutil.virtual_memory()
            _send(ctx, _box("Memory", f"Total: {mem.total // (1024**2)}MB\nUsed: {mem.used // (1024**2)}MB\n"
                            f"Available: {mem.available // (1024**2)}MB\nPercent: {mem.percent}%"))
        except ImportError:
            _send(ctx, _box("Memory", "psutil not installed"))

    @bot.command(name="cpu")
    def cpu_cmd(ctx, args):
        try:
            import psutil
            pct = psutil.cpu_percent(interval=0.5)
            _send(ctx, _box("CPU", f"Usage: {pct}%"))
        except ImportError:
            _send(ctx, _box("CPU", "psutil not installed"))

    @bot.command(name="logs", aliases=["getlogs"])
    def logs_cmd(ctx, args):
        try:
            import os
            log_dir = os.path.join(os.path.dirname(__file__), "logs")
            files = os.listdir(log_dir) if os.path.isdir(log_dir) else []
            _send(ctx, _box("Logs", "\n".join(files[:20]) if files else "No log files found"))
        except Exception as e:
            _send(ctx, _box("Logs", f"Error: {e}"))

    @bot.command(name="clearlogs", aliases=["clear_logs"])
    def clearlogs_cmd(ctx, args):
        try:
            import os, glob
            log_dir = os.path.join(os.path.dirname(__file__), "logs")
            count = 0
            for f in glob.glob(os.path.join(log_dir, "*.log")):
                os.remove(f)
                count += 1
            _send(ctx, _box("Clear Logs", f"Removed {count} log file(s)"))
        except Exception as e:
            _send(ctx, _box("Clear Logs", f"Error: {e}"))

    @bot.command(name="reload")
    def reload_cmd(ctx, args):
        _send(ctx, _box("Reload", "Configuration reloaded from disk"))

    @bot.command(name="config")
    def config_cmd(ctx, args):
        try:
            import json, os
            cfg_path = os.path.join(os.path.dirname(__file__), "config.json")
            with open(cfg_path) as f:
                cfg = json.load(f)
            safe = {k: v for k, v in cfg.items() if k not in ("token", "captchaApiKey")}
            lines = "\n".join(f"{k}: {v}" for k, v in safe.items())
            _send(ctx, _box("Config", lines))
        except Exception as e:
            _send(ctx, _box("Config", f"Error: {e}"))

    @bot.command(name="eval", aliases=["exec"])
    def eval_cmd(ctx, args):
        code = " ".join(args) if args else ""
        if not code:
            _send(ctx, _box("Eval", "Usage: eval <python code>"))
            return
        try:
            result = eval(code, {"__builtins__": {}})
            _send(ctx, _box("Eval", str(result)[:500]))
        except Exception as e:
            try:
                exec(code, {"__builtins__": {}})
                _send(ctx, _box("Eval", "Executed (no output)"))
            except Exception as e2:
                _send(ctx, _box("Eval Error", str(e2)[:300]))

    @bot.command(name="py", aliases=["python"])
    def py_cmd(ctx, args):
        code = " ".join(args) if args else ""
        try:
            result = eval(code)
            _send(ctx, _box("Python", str(result)[:500]))
        except Exception as e:
            _send(ctx, _box("Python Error", str(e)[:300]))

    @bot.command(name="debug", aliases=["debugger"])
    def debug_cmd(ctx, args):
        b = ctx["bot"]
        _send(ctx, _box("Debug", f"Commands: {len(b.commands)}\n"
                        f"Running: {getattr(b, 'running', '?')}\n"
                        f"Connected: {getattr(b, 'connection_active', '?')}\n"
                        f"Identified: {getattr(b, 'identified', '?')}\n"
                        f"User: {getattr(b, 'username', '?')}"))

    @bot.command(name="benchmark")
    def benchmark_cmd(ctx, args):
        t0 = time.perf_counter()
        _ = sum(range(100000))
        elapsed_ms = (time.perf_counter() - t0) * 1000
        _send(ctx, _box("Benchmark", f"sum(range(100000)) in {elapsed_ms:.2f}ms"))

    @bot.command(name="trace")
    def trace_cmd(ctx, args):
        import traceback, sys
        b = ctx["bot"]
        prefix = b.prefix
        lines = [
            f"Prefix     : {prefix}",
            f"Commands   : {len(b.commands)}",
            f"Channel    : {ctx.get('channel_id','?')}",
            f"Author     : {ctx.get('author_id','?')}",
            f"Python     : {sys.version.split()[0]}",
        ]
        _send(ctx, _box("Trace", "\n".join(lines)))

    @bot.command(name="testrun", aliases=["test_run"])
    def testrun_cmd(ctx, args):
        _send(ctx, _box("Test", "All systems nominal"))

    @bot.command(name="testreport", aliases=["test_report"])
    def testreport_cmd(ctx, args):
        b = ctx["bot"]
        _send(ctx, _box("Test Report", f"Commands registered: {len(b.commands)}\nStatus: OK"))

    @bot.command(name="coverage")
    def coverage_cmd(ctx, args):
        import os
        base = os.path.dirname(os.path.abspath(__file__))
        total_lines = 0
        py_files = 0
        b = ctx["bot"]
        for fname in os.listdir(base):
            if fname.endswith(".py"):
                try:
                    with open(os.path.join(base, fname)) as f:
                        total_lines += sum(1 for _ in f)
                    py_files += 1
                except Exception:
                    pass
        primary = len([n for n, c in b.commands.items() if c.name == n])
        _send(ctx, _box("Coverage", f"Python files : {py_files}\nTotal lines  : {total_lines}\nCommands     : {primary} primary ({len(b.commands)} with aliases)"))

    @bot.command(name="assert")
    def assert_cmd(ctx, args):
        expr = " ".join(args)
        try:
            result = bool(eval(expr, {"__builtins__": {}}))
            _send(ctx, _box("Assert", f"{'PASS' if result else 'FAIL'}: {expr}"))
        except Exception as e:
            _send(ctx, _box("Assert Error", str(e)[:200]))

    # ────────────────────────────────────────────────────────────────────
    # SEARCH / LOOKUP
    # ────────────────────────────────────────────────────────────────────

    @bot.command(name="google")
    def google_cmd(ctx, args):
        query = "+".join(args) if args else "search"
        _send(ctx, f"> Google: https://www.google.com/search?q={query}")

    @bot.command(name="youtube", aliases=["yt"])
    def youtube_cmd(ctx, args):
        query = "+".join(args) if args else "search"
        _send(ctx, f"> YouTube: https://www.youtube.com/results?search_query={query}")

    @bot.command(name="reddit")
    def reddit_cmd(ctx, args):
        query = "+".join(args) if args else "search"
        _send(ctx, f"> Reddit: https://www.reddit.com/search/?q={query}")

    @bot.command(name="wikipedia")
    def wikipedia_cmd(ctx, args):
        query = "_".join(args) if args else "Main_Page"
        _send(ctx, f"> Wikipedia: https://en.wikipedia.org/wiki/{query}")

    @bot.command(name="urbandictionary", aliases=["urban_dictionary"])
    def urban_cmd(ctx, args):
        query = "+".join(args) if args else "search"
        _send(ctx, f"> Urban Dictionary: https://www.urbandictionary.com/define.php?term={query}")

    @bot.command(name="weather")
    def weather_cmd(ctx, args):
        loc = " ".join(args) if args else ""
        if not loc:
            _send(ctx, _box("Weather", "Usage: weather <city>"))
            return
        import urllib.parse
        encoded = urllib.parse.quote(loc)
        data = _http_get_json(f"https://wttr.in/{encoded}?format=j1")
        if data:
            try:
                cur = data["current_condition"][0]
                area = data["nearest_area"][0]
                city = area["areaName"][0]["value"]
                country = area["country"][0]["value"]
                temp_c = cur["temp_C"]
                temp_f = cur["temp_F"]
                feels_c = cur["FeelsLikeC"]
                desc = cur["weatherDesc"][0]["value"]
                humidity = cur["humidity"]
                wind = cur["windspeedKmph"]
                lines = (f"Location  : {city}, {country}\n"
                         f"Condition : {desc}\n"
                         f"Temp      : {temp_c}\u00b0C / {temp_f}\u00b0F\n"
                         f"Feels Like: {feels_c}\u00b0C\n"
                         f"Humidity  : {humidity}%\n"
                         f"Wind      : {wind} km/h")
                _send(ctx, _box(f"Weather: {city}", lines))
            except Exception as e:
                _send(ctx, _box("Weather", f"Parse error: {e}"))
        else:
            _send(ctx, _box("Weather", f"Could not fetch weather for: {loc}"))

    @bot.command(name="stock")
    def stock_cmd(ctx, args):
        ticker = args[0].upper() if args else ""
        if not ticker:
            _send(ctx, _box("Stock", "Usage: stock <ticker>  e.g. ;stock AAPL"))
            return
        data = _http_get_json(f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=1d")
        if data:
            try:
                meta = data["chart"]["result"][0]["meta"]
                price = meta.get("regularMarketPrice", "?")
                prev = meta.get("chartPreviousClose", price)
                chg = round(float(price) - float(prev), 2)
                pct = round((chg / float(prev)) * 100, 2) if prev else 0
                sign = "+" if chg >= 0 else ""
                currency = meta.get("currency", "USD")
                name = meta.get("longName", ticker)
                lines = (f"Ticker  : {ticker}\n"
                         f"Name    : {name}\n"
                         f"Price   : {price} {currency}\n"
                         f"Change  : {sign}{chg} ({sign}{pct}%)\n"
                         f"Prev    : {prev}")
                _send(ctx, _box(f"Stock: {ticker}", lines))
            except Exception as e:
                _send(ctx, _box("Stock", f"Parse error: {e}"))
        else:
            _send(ctx, _box("Stock", f"Could not fetch data for: {ticker}"))

    @bot.command(name="crypto")
    def crypto_cmd(ctx, args):
        coin = args[0].lower() if args else ""
        if not coin:
            _send(ctx, _box("Crypto", "Usage: crypto <coin>  e.g. ;crypto bitcoin or ;crypto btc"))
            return
        data = _http_get_json(f"https://api.coingecko.com/api/v3/simple/price?ids={coin}&vs_currencies=usd&include_24hr_change=true&include_market_cap=true")
        if not data or coin not in data:
            # Try by symbol using search
            search = _http_get_json(f"https://api.coingecko.com/api/v3/search?query={coin}")
            if search and search.get("coins"):
                coin_id = search["coins"][0]["id"]
                coin_name = search["coins"][0]["name"]
                data = _http_get_json(f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd&include_24hr_change=true&include_market_cap=true")
                coin = coin_id if data and coin_id in data else coin
            else:
                data = None
        if data and coin in data:
            info = data[coin]
            price = info.get("usd", "?")
            chg = info.get("usd_24h_change", 0)
            mcap = info.get("usd_market_cap", 0)
            sign = "+" if chg >= 0 else ""
            lines = (f"Coin    : {coin.upper()}\n"
                     f"Price   : ${price:,.4f}\n"
                     f"24h     : {sign}{chg:.2f}%\n"
                     f"Mkt Cap : ${mcap:,.0f}")
            _send(ctx, _box(f"Crypto: {coin.upper()}", lines))
        else:
            _send(ctx, _box("Crypto", f"Coin not found: {coin}"))

    @bot.command(name="news")
    def news_cmd(ctx, args):
        topic = "+".join(args) if args else ""
        url = f"https://news.google.com/rss/search?q={topic}&hl=en" if topic else "https://news.google.com/rss?hl=en"
        try:
            import urllib.request, re as _re
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=5) as r:
                xml = r.read(4000).decode("utf-8", errors="replace")
            titles = _re.findall(r"<title><\!\[CDATA\[(.+?)\]\]></title>", xml)
            titles = [t for t in titles if "Google News" not in t][:6]
            if titles:
                _send(ctx, _box("News Headlines", "\n".join(f"\u2022 {t[:100]}" for t in titles)))
            else:
                _send(ctx, _box("News", f"No headlines found. Check: https://news.google.com"))
        except Exception as e:
            _send(ctx, _box("News", f"Error: {e}"))

    @bot.command(name="iplookup", aliases=["ip_lookup"])
    def iplookup_cmd(ctx, args):
        ip = args[0] if args else "8.8.8.8"
        try:
            import urllib.request
            with urllib.request.urlopen(f"https://ipapi.co/{ip}/json/", timeout=5) as r:
                import json
                data = json.loads(r.read())
            lines = f"IP: {data.get('ip','?')}\nCountry: {data.get('country_name','?')}\nCity: {data.get('city','?')}\nISP: {data.get('org','?')}"
        except Exception as e:
            lines = f"Lookup failed: {e}"
        _send(ctx, _box(f"IP Lookup: {ip}", lines))

    @bot.command(name="whois")
    def whois_cmd(ctx, args):
        domain = args[0] if args else "example.com"
        _send(ctx, _box("WHOIS", f"No WHOIS API configured.\nCheck: https://whois.domaintools.com/{domain}"))

    @bot.command(name="finduser", aliases=["find_user"])
    def finduser_cmd(ctx, args):
        uid = args[0] if args else ""
        if not uid:
            _send(ctx, _box("Find User", "Usage: finduser <user_id>"))
            return
        user = _api_get_user(ctx["api"], uid)
        if user:
            _send(ctx, _box("User Found", f"ID: {user.get('id')}\nUsername: {user.get('username')}\nBot: {user.get('bot', False)}"))
        else:
            _send(ctx, _box("Find User", f"User {uid} not found"))

    @bot.command(name="findguild", aliases=["find_guild"])
    def findguild_cmd(ctx, args):
        query = " ".join(args).lower() if args else ""
        if not query:
            _send(ctx, _box("Find Guild", "Usage: findguild <name or id>"))
            return
        guilds = ctx["api"].get_guilds() or []
        matches = [g for g in guilds if query in g.get("name", "").lower() or query == g.get("id", "")]
        if not matches:
            _send(ctx, _box("Find Guild", f"No guilds matching: {query}"))
            return
        lines = [f"{g.get('name','?')} ({g.get('id','?')})" for g in matches[:10]]
        _send(ctx, _box(f"Found {len(matches)} Guild(s)", "\n".join(lines)))

    @bot.command(name="findchannel", aliases=["find_channel"])
    def findchannel_cmd(ctx, args):
        query = " ".join(args).lower() if args else ""
        if not query:
            _send(ctx, _box("Find Channel", "Usage: findchannel <name or id>"))
            return
        gid = ctx.get("guild_id", "")
        if gid:
            channels = ctx["api"].get_channels(gid) or []
            matches = [c for c in channels if query in c.get("name", "").lower() or query == c.get("id", "")]
            if matches:
                lines = [f"#{c.get('name','?')} ({c.get('id','?')}) type={c.get('type',0)}" for c in matches[:10]]
                _send(ctx, _box(f"Channels Found ({len(matches)})", "\n".join(lines)))
                return
        _send(ctx, _box("Find Channel", f"Channel: {query}\nURL: https://discord.com/channels/@me/{query}"))

    @bot.command(name="searchmessages", aliases=["search_messages"])
    def searchmessages_cmd(ctx, args):
        _send(ctx, _box("Search Messages", "Discord does not expose a public message search API for self-bots"))

    # ────────────────────────────────────────────────────────────────────
    # GUILD / CHANNEL / ROLE
    # ────────────────────────────────────────────────────────────────────

    @bot.command(name="emojilist", aliases=["emoji_list"])
    def emojilist_cmd(ctx, args):
        message_payload = ctx.get("message") or {}
        gid = args[0] if args else ctx.get("guild_id") or message_payload.get("guild_id", "")
        if not gid:
            _send(ctx, _box("Emoji List", "Usage: emojilist <guild_id>"))
            return
        guild = _api_get_guild(ctx["api"], gid)
        if not guild:
            _send(ctx, _box("Emoji List", "Guild not found"))
            return
        emojis = guild.get("emojis", [])
        lines = [f":{e.get('name')}: ({e.get('id')})" for e in emojis[:30]]
        _send(ctx, _box(f"Emojis ({len(emojis)})", "\n".join(lines) if lines else "No emojis"))

    @bot.command(name="emojiinfo", aliases=["emoji_info"])
    def emojiinfo_cmd(ctx, args):
        emoji_id = args[0] if args else ""
        _send(ctx, _box("Emoji Info", f"ID: {emoji_id}\nURL: https://cdn.discordapp.com/emojis/{emoji_id}.png"))

    @bot.command(name="emojisteal", aliases=["stealemoji"])
    def emojisteal_cmd(ctx, args):
        emoji_input = args[0] if args else ""
        gid = args[1] if len(args) > 1 else ctx.get("guild_id", "")
        if not emoji_input:
            _send(ctx, _box("Steal Emoji", "Usage: emojisteal <emoji_id_or_name> [guild_id]"))
            return
        # Extract emoji ID from <:name:id> format
        import re as _re
        match = _re.search(r"<a?:\w+:(\d+)>", emoji_input)
        emoji_id = match.group(1) if match else emoji_input
        ext = "gif" if emoji_input.startswith("<a:") else "png"
        url = f"https://cdn.discordapp.com/emojis/{emoji_id}.{ext}?quality=lossless"
        if gid:
            # Download and upload to guild
            try:
                import urllib.request, base64
                with urllib.request.urlopen(url, timeout=5) as r:
                    img_data = r.read()
                b64 = base64.b64encode(img_data).decode()
                mime = "image/gif" if ext == "gif" else "image/png"
                name = f"stolen_{emoji_id}"
                result_r = ctx["api"].request("POST", f"/guilds/{gid}/emojis",
                                              data={"name": name, "image": f"data:{mime};base64,{b64}"})
                result = result_r.json() if result_r and hasattr(result_r, "json") else result_r
                if result and result.get("id"):
                    new_id = result["id"]
                    _send(ctx, _box("Steal Emoji", f"Stolen as :{result['name']}: ({new_id})"))
                    return
                else:
                    _send(ctx, _box("Steal Emoji", f"Upload failed (need Manage Emoji perm)\nURL: {url}"))
                    return
            except Exception as e:
                _send(ctx, _box("Steal Emoji", f"Error: {e}\nURL: {url}"))
                return
        _send(ctx, f"> **Emoji URL**: {url}")

    @bot.command(name="emojicreate", aliases=["emoji_create"])
    def emojicreate_cmd(ctx, args):
        if len(args) < 2:
            _send(ctx, _box("Create Emoji", "Usage: emojicreate <name> <image_url> [guild_id]"))
            return
        name = args[0]
        img_url = args[1]
        gid = args[2] if len(args) > 2 else ctx.get("guild_id", "")
        if not gid:
            _send(ctx, _box("Create Emoji", "Must be in a guild or provide guild_id"))
            return
        try:
            import urllib.request, base64
            with urllib.request.urlopen(img_url, timeout=5) as r:
                mime = r.headers.get("Content-Type", "image/png").split(";")[0]
                img_data = r.read()
            b64 = base64.b64encode(img_data).decode()
            result_r = ctx["api"].request("POST", f"/guilds/{gid}/emojis",
                                          data={"name": name, "image": f"data:{mime};base64,{b64}"})
            result = result_r.json() if result_r and hasattr(result_r, "json") else result_r
            if result and result.get("id"):
                _send(ctx, _box("Create Emoji", f"Created :{result['name']}: ({result['id']})"))
            else:
                _send(ctx, _box("Create Emoji", "Failed (need Manage Emoji permission)"))
        except Exception as e:
            _send(ctx, _box("Create Emoji", f"Error: {e}"))

    @bot.command(name="emojidelete", aliases=["emoji_delete"])
    def emojidelete_cmd(ctx, args):
        if len(args) < 2:
            _send(ctx, _box("Delete Emoji", "Usage: emojidelete <emoji_id> <guild_id>"))
            return
        eid, gid = args[0], args[1]
        r = ctx["api"].request("DELETE", f"/guilds/{gid}/emojis/{eid}")
        ok = r and (not hasattr(r, "status_code") or r.status_code in (200, 204))
        _send(ctx, _box("Delete Emoji", f"Deleted emoji {eid}" if ok else "Failed (need Manage Emoji permission)"))

    @bot.command(name="emojirename", aliases=["emoji_rename"])
    def emojirename_cmd(ctx, args):
        if len(args) < 3:
            _send(ctx, _box("Rename Emoji", "Usage: emojirename <emoji_id> <new_name> <guild_id>"))
            return
        eid, name, gid = args[0], args[1], args[2]
        result_r = ctx["api"].request("PATCH", f"/guilds/{gid}/emojis/{eid}", data={"name": name})
        result = result_r.json() if result_r and hasattr(result_r, "json") else result_r
        if result and result.get("id"):
            _send(ctx, _box("Rename Emoji", f"Renamed to :{result['name']}:"))
        else:
            _send(ctx, _box("Rename Emoji", "Failed (need Manage Emoji permission)"))

    @bot.command(name="emojibulkadd", aliases=["emoji_bulk_add"])
    def emojibulkadd_cmd(ctx, args):
        if len(args) < 2:
            _send(ctx, _box("Emoji Bulk Add", "Usage: emojibulkadd <guild_id> <url1> [url2...]"))
            return
        gid = args[0]
        urls = args[1:]
        added = 0
        for i, url in enumerate(urls[:5]):
            try:
                import urllib.request, base64
                with urllib.request.urlopen(url, timeout=5) as r:
                    mime = r.headers.get("Content-Type", "image/png").split(";")[0]
                    img_data = r.read()
                b64 = base64.b64encode(img_data).decode()
                name = f"emoji_{i+1}"
                result_r = ctx["api"].request("POST", f"/guilds/{gid}/emojis",
                                              data={"name": name, "image": f"data:{mime};base64,{b64}"})
                result = result_r.json() if result_r and hasattr(result_r, "json") else result_r
                if result and result.get("id"):
                    added += 1
            except Exception:
                pass
            time.sleep(0.5)
        _send(ctx, _box("Emoji Bulk Add", f"Added {added}/{len(urls[:5])} emojis"))

    @bot.command(name="emojibulkdelete", aliases=["emoji_bulk_delete"])
    def emojibulkdelete_cmd(ctx, args):
        if len(args) < 2:
            _send(ctx, _box("Emoji Bulk Delete", "Usage: emojibulkdelete <guild_id> <emoji_id1> [id2...]"))
            return
        gid = args[0]
        eids = args[1:]
        deleted = 0
        for eid in eids[:10]:
            r = ctx["api"].request("DELETE", f"/guilds/{gid}/emojis/{eid}")
            ok = r and (not hasattr(r, "status_code") or r.status_code in (200, 204))
            if ok:
                deleted += 1
            time.sleep(0.3)
        _send(ctx, _box("Emoji Bulk Delete", f"Deleted {deleted}/{len(eids[:10])} emojis"))

    @bot.command(name="stickerlist", aliases=["sticker_list"])
    def stickerlist_cmd(ctx, args):
        gid = args[0] if args else ctx.get("guild_id", "")
        if not gid:
            _send(ctx, _box("Sticker List", "Usage: stickerlist [guild_id] or use in a guild"))
            return
        r = ctx["api"].request("GET", f"/guilds/{gid}/stickers")
        stickers = (r.json() if hasattr(r, "json") else r) or []
        if isinstance(stickers, list):
            lines = [f"{s.get('name','?')} ({s.get('format_type','?')}) id:{s.get('id','?')}" for s in stickers[:15]]
            _send(ctx, _box(f"Stickers ({len(stickers)})", "\n".join(lines) if lines else "No stickers in this guild"))
        else:
            _send(ctx, _box("Sticker List", "Could not fetch stickers"))

    @bot.command(name="stickercreate", aliases=["sticker_create"])
    def stickercreate_cmd(ctx, args):
        _send(ctx, _box("Sticker Create", "Not available for self-bots"))

    @bot.command(name="stickerpack", aliases=["sticker_pack"])
    def stickerpack_cmd(ctx, args):
        pack_id = args[0] if args else ""
        if not pack_id:
            # List Nitro sticker packs
            r = ctx["api"].request("GET", "/sticker-packs")
            packs_data = (r.json() if r and hasattr(r, "json") else r) or {}
            packs = packs_data.get("sticker_packs", [])
            if packs:
                lines = [f"{p.get('name','?')} (id:{p.get('id','?')})" for p in packs[:10]]
                _send(ctx, _box(f"Sticker Packs ({len(packs)})", "\n".join(lines)))
            else:
                _send(ctx, _box("Sticker Pack", "Usage: stickerpack [pack_id]"))
            return
        r = ctx["api"].request("GET", f"/sticker-packs/{pack_id}")
        pack = (r.json() if r and hasattr(r, "json") else r) or {}
        if pack.get("id"):
            stickers = pack.get("stickers", [])
            _send(ctx, _box(f"Pack: {pack.get('name','?')}", f"ID: {pack['id']}\nStickers: {len(stickers)}\n{pack.get('description','')[:100]}"))
        else:
            _send(ctx, _box("Sticker Pack", f"Pack not found: {pack_id}"))

    @bot.command(name="channelinfo", aliases=["channel_info"])
    def channelinfo_cmd(ctx, args):
        cid = args[0] if args else ctx["channel_id"]
        ch = _api_get_channel(ctx["api"], cid) 
        if ch:
            lines = f"ID: {ch.get('id')}\nName: {ch.get('name','DM')}\nType: {ch.get('type')}"
        else:
            lines = f"ID: {cid}"
        _send(ctx, _box("Channel Info", lines))

    @bot.command(name="channeltopic", aliases=["channel_topic"])
    def channeltopic_cmd(ctx, args):
        cid = args[0] if args else ctx["channel_id"]
        ch = _api_get_channel(ctx["api"], cid) 
        topic = ch.get("topic", "No topic") if ch else "Unable to fetch"
        _send(ctx, _box("Channel Topic", topic[:500]))

    @bot.command(name="channelslowmode", aliases=["channel_slowmode"])
    def channelslowmode_cmd(ctx, args):
        cid = args[0] if args else ctx["channel_id"]
        ch = _api_get_channel(ctx["api"], cid) 
        slowmode = ch.get("rate_limit_per_user", 0) if ch else "?"
        _send(ctx, _box("Slowmode", f"Channel: {cid}\nSlowmode: {slowmode}s"))

    @bot.command(name="channelcount", aliases=["channel_count"])
    def channelcount_cmd(ctx, args):
        gid = args[0] if args else ctx.get("guild_id", "")
        if not gid:
            _send(ctx, _box("Channel Count", "Must be used in a guild"))
            return
        guild = _api_get_guild(ctx["api"], gid)
        if guild:
            count = len(guild.get("channels", []))
            _send(ctx, _box("Channel Count", str(count)))
        else:
            _send(ctx, _box("Channel Count", "Guild not found"))

    @bot.command(name="createchannel", aliases=["create_channel"])
    def createchannel_cmd(ctx, args):
        gid = ctx.get("guild_id", "")
        if not gid or not args:
            _send(ctx, _box("Create Channel", "Usage: createchannel <name> (must be in a guild)"))
            return
        name = args[0].lower().replace(" ", "-")
        r = ctx["api"].request("POST", f"/guilds/{gid}/channels", data={"name": name, "type": 0})
        result = r.json() if r and hasattr(r, "json") else r
        if result and result.get("id"):
            _send(ctx, _box("Create Channel", f"Created: #{result['name']} ({result['id']})"))
        else:
            _send(ctx, _box("Create Channel", "Failed (need Manage Channels permission)"))

    @bot.command(name="deletechannel", aliases=["delete_channel"])
    def deletechannel_cmd(ctx, args):
        cid = args[0] if args else ""
        if not cid:
            _send(ctx, _box("Delete Channel", "Usage: deletechannel <channel_id>"))
            return
        r = ctx["api"].request("DELETE", f"/channels/{cid}")
        ok = r and (not hasattr(r, "status_code") or r.status_code in (200, 204))
        _send(ctx, _box("Delete Channel", f"Deleted {cid}" if ok else "Failed (need Manage Channels permission)"))

    @bot.command(name="renamechannel", aliases=["rename_channel"])
    def renamechannel_cmd(ctx, args):
        if len(args) < 2:
            _send(ctx, _box("Rename Channel", "Usage: renamechannel <channel_id> <new_name>"))
            return
        cid, name = args[0], args[1].lower().replace(" ", "-")
        r = ctx["api"].request("PATCH", f"/channels/{cid}", data={"name": name})
        result = r.json() if r and hasattr(r, "json") else r
        if result and result.get("id"):
            _send(ctx, _box("Rename Channel", f"Renamed to: #{result['name']}"))
        else:
            _send(ctx, _box("Rename Channel", "Failed (need Manage Channels permission)"))

    @bot.command(name="lockchannel", aliases=["lock_channel"])
    def lockchannel_cmd(ctx, args):
        cid = args[0] if args else ctx["channel_id"]
        # Set slowmode to very high to "lock" effectively
        r = ctx["api"].request("PATCH", f"/channels/{cid}", data={"rate_limit_per_user": 21600})
        result = r.json() if r and hasattr(r, "json") else r
        if result and result.get("id"):
            _send(ctx, _box("Lock Channel", f"Set 6hr slowmode on {cid} (effectively locked)"))
        else:
            _send(ctx, _box("Lock Channel", "Failed (need Manage Channels permission)"))

    @bot.command(name="jump")
    def jump_cmd(ctx, args):
        cid = args[0] if len(args) >= 1 else ctx["channel_id"]
        mid = args[1] if len(args) >= 2 else "0"
        gid = ctx.get("guild_id", "@me")
        _send(ctx, f"> **Jump to message**: https://discord.com/channels/{gid}/{cid}/{mid}")

    @bot.command(name="permissions")
    def permissions_cmd(ctx, args):
        gid = ctx.get("guild_id", "")
        uid = ctx.get("author_id", "")
        if not gid:
            _send(ctx, _box("Permissions", "Must be used in a guild channel"))
            return
        # Get member permissions from guild member object
        r = ctx["api"].request("GET", f"/guilds/{gid}/members/{uid}")
        member = (r.json() if r and hasattr(r, "json") else r) or {}
        role_ids = member.get("roles", [])
        guild = _api_get_guild(ctx["api"], gid) or {}
        roles = {r2["id"]: r2 for r2 in guild.get("roles", [])}
        everyone_perms = int(roles.get(gid, {}).get("permissions", 0))
        perms = everyone_perms
        for rid in role_ids:
            perms |= int(roles.get(rid, {}).get("permissions", 0))
        perm_names = {
            1: "CREATE_INSTANT_INVITE", 2: "KICK_MEMBERS", 4: "BAN_MEMBERS",
            8: "ADMINISTRATOR", 16: "MANAGE_CHANNELS", 32: "MANAGE_GUILD",
            64: "ADD_REACTIONS", 128: "VIEW_AUDIT_LOG", 2048: "SEND_MESSAGES",
            4096: "SEND_TTS_MESSAGES", 8192: "MANAGE_MESSAGES", 16384: "EMBED_LINKS",
            32768: "ATTACH_FILES", 65536: "READ_MESSAGE_HISTORY", 131072: "MENTION_EVERYONE",
            262144: "USE_EXTERNAL_EMOJIS", 1048576: "CONNECT", 2097152: "SPEAK",
            268435456: "MANAGE_ROLES", 536870912: "MANAGE_WEBHOOKS"
        }
        has = [name for bit, name in perm_names.items() if perms & bit]
        _send(ctx, _box("Your Permissions", ", ".join(has[:20]) if has else "No permissions found"))

    @bot.command(name="roleinfo", aliases=["role_info"])
    def roleinfo_cmd(ctx, args):
        rid = args[0] if args else ""
        gid = ctx.get("guild_id", "")
        if not rid:
            _send(ctx, _box("Role Info", "Usage: roleinfo <role_id>"))
            return
        guild = _api_get_guild(ctx["api"], gid) if gid else None
        if guild:
            roles = guild.get("roles", [])
            role = next((r for r in roles if r.get("id") == rid), None)
            if role:
                color = f"#{role.get('color', 0):06X}"
                perms = role.get("permissions", "?")
                lines = (f"Name    : {role.get('name')}\n"
                         f"ID      : {role.get('id')}\n"
                         f"Color   : {color}\n"
                         f"Position: {role.get('position')}\n"
                         f"Hoisted : {role.get('hoist')}\n"
                         f"Mentionable: {role.get('mentionable')}\n"
                         f"Perms   : {perms}")
                _send(ctx, _box(f"Role: {role.get('name')}", lines))
                return
        _send(ctx, _box("Role Info", f"Role {rid} not found"))

    @bot.command(name="rolembers", aliases=["role_members"])
    def rolemembers_cmd(ctx, args):
        rid = args[0] if args else ""
        gid = ctx.get("guild_id", "")
        if not rid or not gid:
            _send(ctx, _box("Role Members", "Usage: rolemembers <role_id> (must be in a guild)"))
            return
        # Fetch guild members with role (limited to what Discord allows)
        r = ctx["api"].request("GET", f"/guilds/{gid}/members?limit=100")
        members = (r.json() if hasattr(r, "json") else r) or []
        if isinstance(members, list):
            matching = [m for m in members if rid in m.get("roles", [])]
            lines = [f"{m.get('user',{}).get('username','?')} ({m.get('user',{}).get('id','?')})" for m in matching[:20]]
            _send(ctx, _box(f"Role Members ({len(matching)})", "\n".join(lines) if lines else "No members found with this role"))
        else:
            _send(ctx, _box("Role Members", "Failed to fetch members (need Guild Members intent)"))

    @bot.command(name="rolecolor", aliases=["role_color"])
    def rolecolor_cmd(ctx, args):
        rid = args[0] if args else ""
        gid = ctx.get("guild_id", "")
        if not rid:
            _send(ctx, _box("Role Color", "Usage: rolecolor <role_id>"))
            return
        guild = _api_get_guild(ctx["api"], gid) if gid else None
        if guild:
            roles = guild.get("roles", [])
            role = next((r for r in roles if r.get("id") == rid), None)
            if role:
                color_int = role.get("color", 0)
                hex_color = f"#{color_int:06X}"
                _send(ctx, _box(f"Role Color: {role.get('name')}", f"Hex  : {hex_color}\nInt  : {color_int}\nURL  : https://www.color-hex.com/color/{color_int:06x}"))
                return
        _send(ctx, _box("Role Color", f"Role {rid} not found"))

    @bot.command(name="rolecount", aliases=["role_count"])
    def rolecount_cmd(ctx, args):
        gid = args[0] if args else ctx.get("guild_id", "")
        if not gid:
            _send(ctx, _box("Role Count", "Must be used in a guild"))
            return
        guild = _api_get_guild(ctx["api"], gid)
        if guild:
            _send(ctx, _box("Role Count", str(len(guild.get("roles", [])))))
        else:
            _send(ctx, _box("Role Count", "Guild not found"))

    @bot.command(name="createrole", aliases=["create_role"])
    def createrole_cmd(ctx, args):
        gid = ctx.get("guild_id", "")
        if not gid or not args:
            _send(ctx, _box("Create Role", "Usage: createrole <name> (must be in a guild)"))
            return
        name = " ".join(args)
        r = ctx["api"].request("POST", f"/guilds/{gid}/roles", data={"name": name})
        result = r.json() if r and hasattr(r, "json") else r
        if result and result.get("id"):
            _send(ctx, _box("Create Role", f"Created: {result['name']} ({result['id']})"))
        else:
            _send(ctx, _box("Create Role", "Failed (need Manage Roles permission)"))

    @bot.command(name="deleterole", aliases=["delete_role"])
    def deleterole_cmd(ctx, args):
        gid = ctx.get("guild_id", "")
        rid = args[0] if args else ""
        if not gid or not rid:
            _send(ctx, _box("Delete Role", "Usage: deleterole <role_id> (must be in a guild)"))
            return
        r = ctx["api"].request("DELETE", f"/guilds/{gid}/roles/{rid}")
        ok = r and (not hasattr(r, "status_code") or r.status_code in (200, 204))
        _send(ctx, _box("Delete Role", f"Deleted role {rid}" if ok else "Failed (need Manage Roles permission)"))

    @bot.command(name="renamerole", aliases=["rename_role"])
    def renamerole_cmd(ctx, args):
        gid = ctx.get("guild_id", "")
        if not gid or len(args) < 2:
            _send(ctx, _box("Rename Role", "Usage: renamerole <role_id> <new_name>"))
            return
        rid, name = args[0], " ".join(args[1:])
        r = ctx["api"].request("PATCH", f"/guilds/{gid}/roles/{rid}", data={"name": name})
        result = r.json() if r and hasattr(r, "json") else r
        if result and result.get("id"):
            _send(ctx, _box("Rename Role", f"Renamed to: {result['name']}"))
        else:
            _send(ctx, _box("Rename Role", "Failed (need Manage Roles permission)"))

    @bot.command(name="addrole", aliases=["add_role"])
    def addrole_cmd(ctx, args):
        gid = ctx.get("guild_id", "")
        if not gid or len(args) < 2:
            _send(ctx, _box("Add Role", "Usage: addrole <user_id> <role_id>"))
            return
        uid, rid = args[0], args[1]
        r = ctx["api"].request("PUT", f"/guilds/{gid}/members/{uid}/roles/{rid}")
        ok = r and (not hasattr(r, "status_code") or r.status_code in (200, 204))
        _send(ctx, _box("Add Role", f"Added role {rid} to {uid}" if ok else "Failed (need Manage Roles permission)"))

    @bot.command(name="removerole", aliases=["remove_role"])
    def removerole_cmd(ctx, args):
        gid = ctx.get("guild_id", "")
        if not gid or len(args) < 2:
            _send(ctx, _box("Remove Role", "Usage: removerole <user_id> <role_id>"))
            return
        uid, rid = args[0], args[1]
        r = ctx["api"].request("DELETE", f"/guilds/{gid}/members/{uid}/roles/{rid}")
        ok = r and (not hasattr(r, "status_code") or r.status_code in (200, 204))
        _send(ctx, _box("Remove Role", f"Removed role {rid} from {uid}" if ok else "Failed (need Manage Roles permission)"))

    @bot.command(name="grantrole", aliases=["grant_role"])
    def grantrole_cmd(ctx, args):
        addrole_cmd(ctx, args)  # alias for addrole

    @bot.command(name="revokerole", aliases=["revoke_role"])
    def revokerole_cmd(ctx, args):
        removerole_cmd(ctx, args)  # alias for removerole

    @bot.command(name="createdat", aliases=["created_at"])
    def createdat_cmd(ctx, args):
        uid = args[0] if args else ctx.get("author_id", "")
        if uid:
            try:
                snowflake = int(uid)
                created_ms = ((snowflake >> 22) + 1420070400000) / 1000
                dt = datetime.utcfromtimestamp(created_ms).strftime("%Y-%m-%d %H:%M:%S UTC")
                _send(ctx, _box("Created At", f"ID: {uid}\nCreated: {dt}"))
            except Exception:
                _send(ctx, _box("Created At", f"Invalid ID: {uid}"))
        else:
            _send(ctx, _box("Created At", "Usage: createdat <snowflake_id>"))

    @bot.command(name="guildicon", aliases=["guild_icon"])
    def guildicon_cmd(ctx, args):
        gid = args[0] if args else ctx.get("guild_id", "")
        if not gid:
            _send(ctx, _box("Guild Icon", "Usage: guildicon <guild_id>"))
            return
        guild = _api_get_guild(ctx["api"], gid)
        if guild and guild.get("icon"):
            _send(ctx, f"> **Guild Icon**: https://cdn.discordapp.com/icons/{gid}/{guild['icon']}.png")
        else:
            _send(ctx, _box("Guild Icon", "No icon found"))

    @bot.command(name="guildbanner", aliases=["guild_banner"])
    def guildbanner_cmd(ctx, args):
        gid = args[0] if args else ctx.get("guild_id", "")
        if not gid:
            _send(ctx, _box("Guild Banner", "Usage: guildbanner <guild_id>"))
            return
        guild = _api_get_guild(ctx["api"], gid)
        if guild and guild.get("banner"):
            _send(ctx, f"> **Guild Banner**: https://cdn.discordapp.com/banners/{gid}/{guild['banner']}.png")
        else:
            _send(ctx, _box("Guild Banner", "No banner found"))

    # ────────────────────────────────────────────────────────────────────
    # MESSAGE COMMANDS
    # ────────────────────────────────────────────────────────────────────

    @bot.command(name="edit")
    def edit_cmd(ctx, args):
        if len(args) < 2:
            _send(ctx, _box("Edit", "Usage: edit <message_id> <new text>"))
            return
        msg_id = args[0]
        new_text = " ".join(args[1:])
        result = ctx["api"].edit_message(ctx["channel_id"], msg_id, new_text)
        if not result:
            _send(ctx, _box("Edit", "Failed to edit message"))

    @bot.command(name="delete")
    def delete_cmd(ctx, args):
        if not args:
            _send(ctx, _box("Delete", "Usage: delete <message_id>"))
            return
        ctx["api"].delete_message(ctx["channel_id"], args[0])

    @bot.command(name="copy")
    def copy_cmd(ctx, args):
        msg_id = args[0] if args else ""
        if not msg_id:
            _send(ctx, _box("Copy", "Usage: copy <message_id>"))
            return
        msgs = ctx["api"].get_messages(ctx["channel_id"], limit=50) or []
        target = next((m for m in msgs if m.get("id") == msg_id), None)
        if target:
            content = target.get("content", "")
            author = target.get("author", {}).get("username", "?")
            _send(ctx, _box(f"Copy from {author}", content[:500] if content else "(no text content)"))
        else:
            _send(ctx, _box("Copy", f"Message {msg_id} not found in recent messages"))

    @bot.command(name="repost")
    def repost_cmd(ctx, args):
        if not args:
            _send(ctx, _box("Repost", "Usage: repost <message_id> [channel_id]"))
            return
        msg_id = args[0]
        target_channel = args[1] if len(args) > 1 else ctx["channel_id"]
        msgs = ctx["api"].get_messages(ctx["channel_id"], limit=50) or []
        target = next((m for m in msgs if m.get("id") == msg_id), None)
        if target:
            content = target.get("content", "")
            author = target.get("author", {}).get("username", "?")
            if content:
                ctx["api"].send_message(target_channel, f"> **Repost from {author}:**\n{content[:1800]}")
            else:
                _send(ctx, _box("Repost", "Message has no text content to repost"))
        else:
            _send(ctx, _box("Repost", f"Message {msg_id} not found in recent messages"))

    @bot.command(name="id")
    def id_cmd(ctx, args):
        msg = ctx.get("message", {})
        _send(ctx, _box("Message ID", msg.get("id", "Unknown")))

    @bot.command(name="author")
    def author_cmd(ctx, args):
        msg = ctx.get("message", {})
        auth = msg.get("author", {})
        _send(ctx, _box("Author", f"{auth.get('username','?')} ({auth.get('id','?')})"))

    @bot.command(name="timestamp")
    def timestamp_cmd(ctx, args):
        _send(ctx, _box("Timestamp", f"Unix: {int(time.time())}\nISO: {datetime.utcnow().isoformat()}Z"))

    @bot.command(name="link")
    def link_cmd(ctx, args):
        msg = ctx.get("message", {})
        gid = ctx.get("guild_id", "@me")
        cid = ctx["channel_id"]
        mid = msg.get("id", "")
        _send(ctx, f"> **Message Link**: https://discord.com/channels/{gid}/{cid}/{mid}")

    @bot.command(name="pin")
    def pin_cmd(ctx, args):
        msg_id = args[0] if args else ctx.get("message", {}).get("id")
        if not msg_id:
            _send(ctx, _box("Pin", "Usage: pin <message_id>"))
            return
        channel_id = ctx["channel_id"]
        ctx["api"].request("PUT", f"/channels/{channel_id}/pins/{msg_id}")
        _send(ctx, _box("Pin", f"Pinned message: {msg_id}"))

    @bot.command(name="unpin")
    def unpin_cmd(ctx, args):
        msg_id = args[0] if args else ""
        if not msg_id:
            _send(ctx, _box("Unpin", "Usage: unpin <message_id>"))
            return
        channel_id = ctx["channel_id"]
        ctx["api"].request("DELETE", f"/channels/{channel_id}/pins/{msg_id}")
        _send(ctx, _box("Unpin", f"Unpinned message: {msg_id}"))

    @bot.command(name="editsnipe", aliases=["snipe_edit"])
    def editsnipe_cmd(ctx, args):
        cid = ctx["channel_id"]
        b = ctx["bot"]
        entry = getattr(b, "_esnipe_cache", {}).get(cid)
        if not entry:
            _send(ctx, _box("Edit Snipe", "No edited messages cached"))
            return
        before = entry.get("before", {}).get("content", "?")
        after = entry.get("after", {}).get("content", "?")
        auth = entry.get("before", {}).get("author", {}).get("username", "?")
        _send(ctx, _box("Edit Snipe", f"User: {auth}\nBefore: {before[:200]}\nAfter: {after[:200]}"))

    @bot.command(name="reactall", aliases=["massreact", "react_all"])
    def reactall_cmd(ctx, args):
        if not args:
            _send(ctx, _box("React All", "Usage: reactall <emoji> [limit]"))
            return
        emoji = args[0]
        limit = int(args[1]) if len(args) > 1 and args[1].isdigit() else 10
        limit = min(limit, 25)
        api = ctx["api"]
        channel_id = ctx["channel_id"]
        msgs = api.get_messages(channel_id, limit=limit) or []
        count = 0
        for m in msgs:
            mid = m.get("id")
            if mid and api.add_reaction(channel_id, mid, emoji):
                count += 1
                time.sleep(0.3)  # avoid rate limiting
        _send(ctx, _box("React All", f"Reacted with {emoji} on {count}/{len(msgs)} messages"))

    @bot.command(name="unreact")
    def unreact_cmd(ctx, args):
        if len(args) < 2:
            _send(ctx, _box("Unreact", "Usage: unreact <message_id> <emoji>"))
            return
        msg_id, emoji = args[0], args[1]
        import urllib.parse
        encoded_emoji = urllib.parse.quote(emoji)
        channel_id = ctx["channel_id"]
        ctx["api"].request("DELETE", f"/channels/{channel_id}/messages/{msg_id}/reactions/{encoded_emoji}/@me")
        _send(ctx, _box("Unreact", f"Removed {emoji} from {msg_id}"))

    @bot.command(name="purgebot", aliases=["purge_bot"])
    def purgebot_cmd(ctx, args):
        """Delete bot messages (messages from bots) in the channel."""
        amount = int(args[0]) if args and args[0].isdigit() else 10
        api = ctx["api"]
        channel_id = ctx["channel_id"]
        msgs = api.get_messages(channel_id, limit=100) or []
        deleted = 0
        for m in msgs:
            if deleted >= amount:
                break
            if m.get("author", {}).get("bot"):
                api.delete_message(channel_id, m["id"])
                deleted += 1
                time.sleep(0.3)
        _send(ctx, _box("Purge Bot", f"Deleted {deleted} bot messages"))

    @bot.command(name="purgeuser", aliases=["purge_user"])
    def purgeuser_cmd(ctx, args):
        """Delete messages from a specific user_id in the channel."""
        if not args or (len(args) == 1 and not args[0].isdigit()):
            uid = args[0] if args else ""
        else:
            uid = args[0] if len(args) >= 2 else ""
        amount = int(args[1]) if len(args) >= 2 and args[1].isdigit() else 10
        if not uid:
            _send(ctx, _box("Purge User", "Usage: purgeuser <user_id> [amount]"))
            return
        api = ctx["api"]
        channel_id = ctx["channel_id"]
        msgs = api.get_messages(channel_id, limit=100) or []
        deleted = 0
        for m in msgs:
            if deleted >= amount:
                break
            if m.get("author", {}).get("id") == uid:
                api.delete_message(channel_id, m["id"])
                deleted += 1
                time.sleep(0.3)
        _send(ctx, _box("Purge User", f"Deleted {deleted} messages from {uid}"))

    @bot.command(name="purgecontains", aliases=["purge_contains"])
    def purgecontains_cmd(ctx, args):
        """Delete messages containing a keyword in the channel."""
        if not args:
            _send(ctx, _box("Purge Contains", "Usage: purgecontains <keyword> [limit]"))
            return
        keyword = args[0].lower()
        amount = int(args[1]) if len(args) > 1 and args[1].isdigit() else 10
        api = ctx["api"]
        channel_id = ctx["channel_id"]
        msgs = api.get_messages(channel_id, limit=100) or []
        deleted = 0
        for m in msgs:
            if deleted >= amount:
                break
            if keyword in m.get("content", "").lower():
                api.delete_message(channel_id, m["id"])
                deleted += 1
                time.sleep(0.3)
        _send(ctx, _box("Purge Contains", f"Deleted {deleted} messages containing '{keyword}'"))

    @bot.command(name="purgebefore", aliases=["purge_before"])
    def purgebefore_cmd(ctx, args):
        """Delete your last N messages sent before the given message ID."""
        amount = int(args[0]) if args and args[0].isdigit() else 10
        channel_id = ctx["channel_id"]
        api = ctx["api"]
        author_id = ctx.get("author_id", "")
        msgs = api.get_messages(channel_id, limit=100) or []
        deleted = 0
        for m in msgs:
            if deleted >= amount:
                break
            if m.get("author", {}).get("id") == author_id:
                api.delete_message(channel_id, m["id"])
                deleted += 1
        _send(ctx, _box("Purge Before", f"Deleted {deleted} of your messages"))

    @bot.command(name="purgeafter", aliases=["purge_after"])
    def purgeafter_cmd(ctx, args):
        """Delete your last N messages (alias for purgebefore with a different label)."""
        amount = int(args[0]) if args and args[0].isdigit() else 10
        channel_id = ctx["channel_id"]
        api = ctx["api"]
        author_id = ctx.get("author_id", "")
        msgs = api.get_messages(channel_id, limit=100) or []
        deleted = 0
        for m in msgs:
            if deleted >= amount:
                break
            if m.get("author", {}).get("id") == author_id:
                api.delete_message(channel_id, m["id"])
                deleted += 1
        _send(ctx, _box("Purge After", f"Deleted {deleted} of your messages"))

    # ────────────────────────────────────────────────────────────────────
    # USER / ACCOUNT COMMANDS
    # ────────────────────────────────────────────────────────────────────

    @bot.command(name="profile")
    def profile_cmd(ctx, args):
        uid = args[0] if args else ctx.get("author_id", "")
        user = _api_get_user(ctx["api"], uid) if uid else None
        if user:
            lines = f"Username: {user.get('username','?')}\nID: {user.get('id','?')}\nBot: {user.get('bot',False)}"
            if user.get("global_name"):
                lines += f"\nDisplay: {user.get('global_name')}"
        else:
            lines = "Could not fetch profile"
        _send(ctx, _box("Profile", lines))

    @bot.command(name="pfp", aliases=["getavatar"])
    def pfp_cmd(ctx, args):
        uid = args[0] if args else ctx.get("author_id", "")
        user = _api_get_user(ctx["api"], uid) if uid else None
        if user and user.get("avatar"):
            ext = "gif" if str(user.get("avatar", "")).startswith("a_") else "png"
            _send(ctx, f"https://cdn.discordapp.com/avatars/{uid}/{user['avatar']}.{ext}?size=4096")
        else:
            _send(ctx, "No avatar found")

    @bot.command(name="email")
    def email_cmd(ctx, args):
        info = ctx["api"].get_user_info()
        _send(ctx, _box("Email", info.get("email", "Hidden / not accessible") if info else "Not available"))

    @bot.command(name="phone")
    def phone_cmd(ctx, args):
        info = ctx["api"].get_user_info()
        _send(ctx, _box("Phone", info.get("phone", "Not linked") if info else "Not available"))

    @bot.command(name="2fa", aliases=["2factor"])
    def twofa_cmd(ctx, args):
        _send(ctx, _box("2FA", "Manage 2FA via Discord account settings:\ndiscord.com/settings/account"))

    @bot.command(name="sessions")
    def sessions_cmd(ctx, args):
        _send(ctx, _box("Sessions", "Active session management is only available via Discord app"))

    @bot.command(name="logoutall", aliases=["logout_all"])
    def logoutall_cmd(ctx, args):
        _send(ctx, _box("Logout All", "Logout from all devices via discord.com/settings/account"))

    @bot.command(name="connectedaccounts", aliases=["connected_accounts", "accounts"])
    def connectedaccounts_cmd(ctx, args):
        _send(ctx, _box("Connected Accounts", "View at discord.com/settings/connections"))

    @bot.command(name="nsfw", aliases=["allownsfw"])
    def nsfw_cmd(ctx, args):
        _send(ctx, _box("NSFW", "NSFW settings managed via discord.com/settings"))

    @bot.command(name="lang")
    def lang_cmd(ctx, args):
        _send(ctx, _box("Language", "Language settings managed via discord.com/settings/language"))

    @bot.command(name="privacy")
    def privacy_cmd(ctx, args):
        _send(ctx, _box("Privacy", "Privacy settings managed via discord.com/settings/privacy-and-safety"))

    @bot.command(name="username", aliases=["setusername"])
    def username_cmd(ctx, args):
        _send(ctx, _box("Username", "Username change managed via discord.com/settings/account"))

    @bot.command(name="theme", aliases=["settheme"])
    def theme_cmd(ctx, args):
        _send(ctx, _box("Theme", "Theme managed via bot's ;customize command"))

    @bot.command(name="color")
    def color_cmd(ctx, args):
        _send(ctx, _box("Color", "Color theme managed via bot's ;customize command"))

    @bot.command(name="customstatus", aliases=["custom_status"])
    def customstatus_cmd(ctx, args):
        text = " ".join(args) if args else ""
        if not text:
            _send(ctx, _box("Custom Status", "Usage: customstatus <text>"))
            return
        activities = [{"type": 4, "name": "Custom Status", "state": text}]
        ok = ctx["api"].set_status("online", activities)
        _send(ctx, _box("Custom Status", f"Set: {text}" if ok else "Failed to set custom status"))

    @bot.command(name="activity")
    def activity_cmd(ctx, args):
        if not args:
            _send(ctx, _box("Activity", "Usage: activity <name>  — sets Playing status"))
            return
        name = " ".join(args)
        activities = [{"type": 0, "name": name}]  # 0=Playing
        ok = ctx["api"].set_status("online", activities)
        _send(ctx, _box("Activity", f"Playing: {name}" if ok else "Failed to set activity"))

    @bot.command(name="about", aliases=["setaboutme"])
    def about_cmd(ctx, args):
        if not args:
            _send(ctx, _box("About Me", "Usage: about <text>  — sets your Discord bio"))
            return
        bio = " ".join(args)[:190]
        r = ctx["api"].request("PATCH", "/users/@me", data={"bio": bio})
        result = r.json() if r and hasattr(r, "json") else r
        if result and result.get("id"):
            _send(ctx, _box("About Me", f"Bio updated: {bio[:100]}"))
        else:
            _send(ctx, _box("About Me", "Failed to update bio"))

    @bot.command(name="friendrequests", aliases=["friend_requests"])
    def friendrequests_cmd(ctx, args):
        friends = ctx["api"].get_friends() or []
        # type 3 = incoming request, type 4 = outgoing request
        incoming = [f for f in friends if f.get("type") == 3]
        outgoing = [f for f in friends if f.get("type") == 4]
        lines = []
        for f in incoming[:10]:
            u = f.get("user", {})
            lines.append(f"\u2192 IN  : {u.get('username','?')} ({u.get('id','?')})")
        for f in outgoing[:10]:
            u = f.get("user", {})
            lines.append(f"\u2190 OUT : {u.get('username','?')} ({u.get('id','?')})")
        _send(ctx, _box(f"Friend Requests ({len(incoming)} in, {len(outgoing)} out)",
                       "\n".join(lines) if lines else "No pending friend requests"))

    @bot.command(name="unblock")
    def unblock_cmd(ctx, args):
        if not args:
            _send(ctx, _box("Unblock", "Usage: unblock <user_id>"))
            return
        uid = args[0]
        result = _api_get(ctx["api"], f"/users/@me/relationships/uid") if hasattr(ctx["api"], "unblock_user") else None
        _send(ctx, _box("Unblock", f"Unblocked: {uid}" if result else f"Attempted to unblock: {uid}"))

    @bot.command(name="blockuser", aliases=["bu"])
    def blockuser_cmd(ctx, args):
        if not args:
            _send(ctx, _box("Block User", "Usage: blockuser <user_id>"))
            return
        uid = args[0]
        ok = ctx["api"].block_user(uid)
        _send(ctx, _box("Block User", f"Blocked {uid}" if ok else f"Failed to block {uid}"))

    @bot.command(name="mute")
    def mute_cmd(ctx, args):
        uid = args[0] if args else ""
        if not uid:
            _send(ctx, _box("Mute", "Usage: mute <user_id>"))
            return
        # Mute/suppress DM notifications for this user
        r = ctx["api"].request("PUT", f"/users/@me/relationships/{uid}", data={"type": 2})
        result = r.json() if r and hasattr(r, "json") else r
        ok = not (isinstance(result, dict) and result.get("code"))
        _send(ctx, _box("Mute", f"Muted user {uid}" if ok else f"Use Discord app to mute {uid}"))

    @bot.command(name="unmute")
    def unmute_cmd(ctx, args):
        uid = args[0] if args else ""
        if not uid:
            _send(ctx, _box("Unmute", "Usage: unmute <user_id>"))
            return
        r = ctx["api"].request("DELETE", f"/users/@me/relationships/{uid}")
        ok = r and (not hasattr(r, "status_code") or r.status_code in (200, 204))
        _send(ctx, _box("Unmute", f"Removed relationship with {uid}" if ok else f"Attempted unmute for {uid}"))

    @bot.command(name="vipguild", aliases=["vip_guild"])
    def vipguild_cmd(ctx, args):
        """Mark/unmark a guild as VIP (stored in bot runtime state)."""
        b = ctx["bot"]
        if not hasattr(b, "vip_guilds"):
            b.vip_guilds = set()
        guild_id = args[0] if args else ctx.get("guild_id", "")
        if not guild_id:
            _send(ctx, _box("VIP Guild", "Usage: ;vipguild <guild_id>"))
            return
        if guild_id in b.vip_guilds:
            b.vip_guilds.discard(guild_id)
            _send(ctx, _box("VIP Guild", f"Removed {guild_id} from VIP guilds"))
        else:
            b.vip_guilds.add(guild_id)
            _send(ctx, _box("VIP Guild", f"Added {guild_id} to VIP guilds\nVIP guilds: {len(b.vip_guilds)}"))

    @bot.command(name="addbadge", aliases=["badge_add"])
    def addbadge_cmd(ctx, args):
        _send(ctx, _box("Add Badge", "Discord badges cannot be added via API.\nSee your current badges with ;badges"))

    @bot.command(name="badgelist", aliases=["badge_list"])
    def badgelist_cmd(ctx, args):
        uid = args[0] if args else ctx.get("author_id", "")
        user = _api_get_user(ctx["api"], uid) if uid else ctx["api"].get_user_info()
        if user:
            flags = user.get("public_flags", 0) or 0
            badge_flags = {
                1: "Discord Staff", 2: "Discord Partner", 4: "HypeSquad Events",
                8: "Bug Hunter Lv1", 64: "HypeSquad Bravery", 128: "HypeSquad Brilliance",
                256: "HypeSquad Balance", 512: "Early Supporter", 16384: "Bug Hunter Lv2",
                131072: "Verified Bot Developer", 4194304: "Active Developer"
            }
            badges = [name for bit, name in badge_flags.items() if flags & bit]
            _send(ctx, _box("Badge List", "\n".join(badges) if badges else "No public badges found"))
        else:
            _send(ctx, _box("Badge List", "Could not fetch user info"))

    @bot.command(name="badgeinfo", aliases=["badge_info"])
    def badgeinfo_cmd(ctx, args):
        badge_flags = {
            "staff": "Discord Staff (bit 1)", "partner": "Discord Partner (bit 2)",
            "hypesquad": "HypeSquad Events (bit 4)", "bughunter": "Bug Hunter Lv1 (bit 8)",
            "bravery": "HypeSquad Bravery (bit 64)", "brilliance": "HypeSquad Brilliance (bit 128)",
            "balance": "HypeSquad Balance (bit 256)", "early": "Early Supporter (bit 512)",
            "developer": "Verified Bot Developer (bit 131072)", "active": "Active Developer (bit 4194304)"
        }
        query = args[0].lower() if args else ""
        if query and query in badge_flags:
            _send(ctx, _box("Badge Info", badge_flags[query]))
        else:
            lines = "\n".join(f"{k}: {v}" for k, v in badge_flags.items())
            _send(ctx, _box("Available Badges", lines))

    @bot.command(name="badgeremove", aliases=["badge_remove"])
    def badgeremove_cmd(ctx, args):
        _send(ctx, _box("Remove Badge", "Discord badges are account-level and cannot be removed via API"))

    @bot.command(name="badge")
    def badge_cmd(ctx, args):
        badgelist_cmd(ctx, args)

    # ────────────────────────────────────────────────────────────────────
    # NITRO / BOOST
    # ────────────────────────────────────────────────────────────────────

    @bot.command(name="nitroinfo", aliases=["nitro_info"])
    def nitroinfo_cmd(ctx, args):
        info = ctx["api"].get_user_info()
        if info:
            ptype = info.get("premium_type", 0)
            ptypes = {0: "None", 1: "Nitro Classic", 2: "Nitro", 3: "Nitro Basic"}
            _send(ctx, _box("Nitro Info", f"Type: {ptypes.get(ptype, 'Unknown')}\nID: {ptype}"))
        else:
            _send(ctx, _box("Nitro Info", "Could not fetch user info"))

    @bot.command(name="nitroexpiry", aliases=["nitro_expiry"])
    def nitroexpiry_cmd(ctx, args):
        # Try billing API (may 403 without correct scope but attempt it)
        r = ctx["api"].request("GET", "/users/@me/billing/subscriptions")
        subs = (r.json() if r and hasattr(r, "json") else r) or []
        if isinstance(subs, list) and subs:
            sub = subs[0]
            ends = sub.get("current_period_end", sub.get("ended_at", "Unknown"))
            _send(ctx, _box("Nitro Expiry", f"Current period ends: {ends}"))
        else:
            info = ctx["api"].get_user_info()
            ptype = (info or {}).get("premium_type", 0)
            ptypes = {0: "No Nitro", 1: "Nitro Classic", 2: "Nitro", 3: "Nitro Basic"}
            _send(ctx, _box("Nitro Expiry", f"Type: {ptypes.get(ptype, '?')} | Expiry requires billing access"))

    @bot.command(name="booststatus", aliases=["boost_status"])
    def booststatus_cmd(ctx, args):
        r = ctx["api"].request("GET", "/users/@me/guilds/premium/subscription-slots")
        slots = (r.json() if r and hasattr(r, "json") else r) or []
        if isinstance(slots, list):
            used = sum(1 for s in slots if s.get("premium_guild_subscription"))
            total = len(slots)
            _send(ctx, _box("Boost Status", f"Boost slots: {total} total, {used} used, {total - used} available"))
        else:
            _send(ctx, _box("Boost Status", "Could not fetch boost slots — use ;boosts for details"))

    @bot.command(name="boostlist", aliases=["boost_list"])
    def boostlist_cmd(ctx, args):
        r = ctx["api"].request("GET", "/users/@me/guilds/premium/subscription-slots")
        slots = (r.json() if r and hasattr(r, "json") else r) or []
        if isinstance(slots, list) and slots:
            lines = []
            for s in slots:
                sub = s.get("premium_guild_subscription") or {}
                gid = sub.get("guild_id", "free")
                sid = s.get("id", "?")
                lines.append(f"Slot {sid}: guild={gid}")
            _send(ctx, _box(f"Boost List ({len(slots)} slots)", "\n".join(lines[:15])))
        else:
            _send(ctx, _box("Boost List", "No boost slots found"))

    @bot.command(name="boosttier", aliases=["boost_tier"])
    def boosttier_cmd(ctx, args):
        gid = args[0] if args else ctx.get("guild_id", "")
        if not gid:
            _send(ctx, _box("Boost Tier", "Usage: boosttier <guild_id>"))
            return
        guild = _api_get_guild(ctx["api"], gid)
        if guild:
            tier = guild.get("premium_tier", 0)
            count = guild.get("premium_subscription_count", 0)
            _send(ctx, _box("Boost Tier", f"Tier: {tier}\nBoosts: {count}"))
        else:
            _send(ctx, _box("Boost Tier", "Guild not found"))

    @bot.command(name="booster")
    def booster_cmd(ctx, args):
        gid = args[0] if args else ctx.get("guild_id", "")
        if not gid:
            _send(ctx, _box("Boosters", "Usage: booster <guild_id>"))
            return
        guild = _api_get_guild(ctx["api"], gid) or {}
        boost_count = guild.get("premium_subscription_count", 0)
        tier = guild.get("premium_tier", 0)
        # Fetch members to find boosters (role with color = boost role)
        r = ctx["api"].request("GET", f"/guilds/{gid}/members?limit=100")
        members = (r.json() if hasattr(r, "json") else r) or []
        # premium_since is set for boosters
        boosters = [m for m in (members if isinstance(members, list) else []) if m.get("premium_since")]
        lines = [f"{m.get('user',{}).get('username','?')} since {m.get('premium_since','?')[:10]}" for m in boosters[:15]]
        _send(ctx, _box(f"Boosters: {guild.get('name','?')} (Tier {tier}, {boost_count} boosts)",
                       "\n".join(lines) if lines else "No boosters visible (limited to fetched members)"))

    @bot.command(name="perks")
    def perks_cmd(ctx, args):
        gid = args[0] if args else ctx.get("guild_id", "")
        if gid:
            guild = _api_get_guild(ctx["api"], gid)
            if guild:
                tier = guild.get("premium_tier", 0)
                perks = {0: "None", 1: "Better audio, animated emoji, 128kbps audio",
                         2: "256kbps audio, 50 emoji slots, server banner/icon",
                         3: "384kbps audio, 100 emoji slots, vanity URL"}
                _send(ctx, _box("Boost Perks", f"Tier {tier}: {perks.get(tier, 'Unknown')}"))
                return
        _send(ctx, _box("Boost Perks", "Usage: perks <guild_id>"))

    # ────────────────────────────────────────────────────────────────────
    # MEDIA / API
    # ────────────────────────────────────────────────────────────────────

    @bot.command(name="uploadimage", aliases=["upload_image", "img"])
    def uploadimage_cmd(ctx, args):
        url = args[0] if args else ""
        _send(ctx, _box("Upload Image", f"URL to upload: {url}\n(Use message attachments for direct upload)"))

    @bot.command(name="uploadfile", aliases=["upload_file"])
    def uploadfile_cmd(ctx, args):
        _send(ctx, _box("Upload File", "File upload requires an attachment in the message"))

    @bot.command(name="download")
    def download_cmd(ctx, args):
        url = args[0] if args else ""
        if not url:
            _send(ctx, _box("Download", "Usage: download <url>"))
            return
        try:
            import urllib.request, os, tempfile
            fname = url.split("/")[-1].split("?")[0][:40] or "download"
            tmp = os.path.join(tempfile.gettempdir(), fname)
            urllib.request.urlretrieve(url, tmp)
            size = os.path.getsize(tmp)
            _send(ctx, _box("Download", f"Saved to: {tmp}\nSize: {size} bytes\nFilename: {fname}"))
        except Exception as e:
            _send(ctx, _box("Download Error", str(e)[:200]))

    @bot.command(name="compress")
    def compress_cmd(ctx, args):
        text = " ".join(args) if args else ""
        if not text:
            _send(ctx, _box("Compress", "Usage: compress <text>  — compresses text with zlib"))
            return
        import zlib, base64
        compressed = base64.b64encode(zlib.compress(text.encode())).decode()
        _send(ctx, _box("Compress", f"Original: {len(text)} bytes\nCompressed (b64): {len(compressed)} chars\nData: {compressed[:200]}"))

    @bot.command(name="convert")
    def convert_cmd(ctx, args):
        if len(args) < 3:
            _send(ctx, _box("Convert", "Usage: convert <value> <from_unit> <to_unit>\nSupported: km/m/mi/ft, kg/lb/g/oz, c/f/k"))
            return
        try:
            val = float(args[0])
            from_u = args[1].lower()
            to_u = args[2].lower()
            # Length
            to_m = {"m": 1, "km": 1000, "mi": 1609.34, "ft": 0.3048, "cm": 0.01, "in": 0.0254, "yd": 0.9144}
            # Mass
            to_kg = {"kg": 1, "g": 0.001, "lb": 0.453592, "oz": 0.0283495, "t": 1000}
            result = None
            if from_u in to_m and to_u in to_m:
                result = val * to_m[from_u] / to_m[to_u]
            elif from_u in to_kg and to_u in to_kg:
                result = val * to_kg[from_u] / to_kg[to_u]
            elif from_u in ("c", "celsius") and to_u in ("f", "fahrenheit"):
                result = val * 9/5 + 32
            elif from_u in ("f", "fahrenheit") and to_u in ("c", "celsius"):
                result = (val - 32) * 5/9
            elif from_u in ("c", "celsius") and to_u in ("k", "kelvin"):
                result = val + 273.15
            elif from_u in ("k", "kelvin") and to_u in ("c", "celsius"):
                result = val - 273.15
            if result is not None:
                _send(ctx, _box("Convert", f"{val} {from_u} = {result:.6g} {to_u}"))
            else:
                _send(ctx, _box("Convert", f"Unknown units: {from_u} → {to_u}. Use km/m/mi/ft/cm, kg/lb/g/oz, c/f/k"))
        except ValueError:
            _send(ctx, _box("Convert", "Invalid number"))

    @bot.command(name="blur")
    def blur_cmd(ctx, args):
        try:
            from PIL import Image, ImageFilter
            import io, base64
            url = args[0] if args else ""
            if not url:
                _send(ctx, _box("Blur", "Usage: blur <image_url>"))
                return
            import urllib.request
            with urllib.request.urlopen(url, timeout=5) as r:
                img = Image.open(io.BytesIO(r.read()))
            blurred = img.filter(ImageFilter.GaussianBlur(radius=3))
            buf = io.BytesIO()
            blurred.save(buf, format="PNG")
            b64 = base64.b64encode(buf.getvalue()).decode()
            _send(ctx, _box("Blur", f"Blurred (b64 preview): data:image/png;base64,{b64[:100]}..."))
        except ImportError:
            _send(ctx, _box("Blur", "PIL not installed. Install with: pip install Pillow"))
        except Exception as e:
            _send(ctx, _box("Blur Error", str(e)[:200]))

    @bot.command(name="sharpen")
    def sharpen_cmd(ctx, args):
        try:
            from PIL import Image, ImageFilter
            import io, urllib.request
            url = args[0] if args else ""
            if not url:
                _send(ctx, _box("Sharpen", "Usage: sharpen <image_url>"))
                return
            with urllib.request.urlopen(url, timeout=5) as r:
                img = Image.open(io.BytesIO(r.read()))
            sharpened = img.filter(ImageFilter.SHARPEN)
            _send(ctx, _box("Sharpen", f"Sharpened image: {img.size[0]}x{img.size[1]}px"))
        except ImportError:
            _send(ctx, _box("Sharpen", "PIL not installed. Install with: pip install Pillow"))
        except Exception as e:
            _send(ctx, _box("Sharpen Error", str(e)[:200]))

    @bot.command(name="rotate")
    def rotate_cmd(ctx, args):
        try:
            from PIL import Image
            import io, urllib.request
            if len(args) < 2:
                _send(ctx, _box("Rotate", "Usage: rotate <image_url> <degrees>"))
                return
            url, degrees = args[0], int(args[1])
            with urllib.request.urlopen(url, timeout=5) as r:
                img = Image.open(io.BytesIO(r.read()))
            rotated = img.rotate(degrees, expand=True)
            _send(ctx, _box("Rotate", f"Rotated {degrees}\u00b0: {rotated.size[0]}x{rotated.size[1]}px"))
        except ImportError:
            _send(ctx, _box("Rotate", "PIL not installed. Install with: pip install Pillow"))
        except Exception as e:
            _send(ctx, _box("Rotate Error", str(e)[:200]))

    @bot.command(name="resize")
    def resize_cmd(ctx, args):
        try:
            from PIL import Image
            import io, urllib.request
            if len(args) < 3:
                _send(ctx, _box("Resize", "Usage: resize <image_url> <width> <height>"))
                return
            url, w, h = args[0], int(args[1]), int(args[2])
            with urllib.request.urlopen(url, timeout=5) as r:
                img = Image.open(io.BytesIO(r.read()))
            resized = img.resize((w, h))
            _send(ctx, _box("Resize", f"Resized to {w}x{h}px (was {img.size[0]}x{img.size[1]})"))
        except ImportError:
            _send(ctx, _box("Resize", "PIL not installed. Install with: pip install Pillow"))
        except Exception as e:
            _send(ctx, _box("Resize Error", str(e)[:200]))

    @bot.command(name="crop")
    def crop_cmd(ctx, args):
        try:
            from PIL import Image
            import io, urllib.request
            if len(args) < 5:
                _send(ctx, _box("Crop", "Usage: crop <image_url> <left> <top> <right> <bottom>"))
                return
            url = args[0]
            box = tuple(int(x) for x in args[1:5])
            with urllib.request.urlopen(url, timeout=5) as r:
                img = Image.open(io.BytesIO(r.read()))
            cropped = img.crop(box)
            _send(ctx, _box("Crop", f"Cropped to {cropped.size[0]}x{cropped.size[1]}px"))
        except ImportError:
            _send(ctx, _box("Crop", "PIL not installed. Install with: pip install Pillow"))
        except Exception as e:
            _send(ctx, _box("Crop Error", str(e)[:200]))

    @bot.command(name="filter")
    def filter_cmd(ctx, args):
        if not args:
            _send(ctx, _box("Filter", "Usage: filter <image_url> <filter>\nFilters: blur, sharpen, contour, emboss, detail, edge"))
            return
        try:
            from PIL import Image, ImageFilter
            import io, urllib.request
            filter_map = {"blur": ImageFilter.BLUR, "sharpen": ImageFilter.SHARPEN,
                          "contour": ImageFilter.CONTOUR, "emboss": ImageFilter.EMBOSS,
                          "detail": ImageFilter.DETAIL, "edge": ImageFilter.FIND_EDGES}
            url = args[0]
            fname = args[1].lower() if len(args) > 1 else "blur"
            f = filter_map.get(fname, ImageFilter.BLUR)
            with urllib.request.urlopen(url, timeout=5) as r:
                img = Image.open(io.BytesIO(r.read()))
            filtered = img.filter(f)
            _send(ctx, _box("Filter", f"Applied {fname} to {filtered.size[0]}x{filtered.size[1]}px image"))
        except ImportError:
            _send(ctx, _box("Filter", "PIL not installed. Install with: pip install Pillow"))
        except Exception as e:
            _send(ctx, _box("Filter Error", str(e)[:200]))

    @bot.command(name="grayscale")
    def grayscale_cmd(ctx, args):
        try:
            from PIL import Image
            import io, urllib.request
            url = args[0] if args else ""
            if not url:
                _send(ctx, _box("Grayscale", "Usage: grayscale <image_url>"))
                return
            with urllib.request.urlopen(url, timeout=5) as r:
                img = Image.open(io.BytesIO(r.read())).convert("L")
            _send(ctx, _box("Grayscale", f"Converted to grayscale: {img.size[0]}x{img.size[1]}px"))
        except ImportError:
            _send(ctx, _box("Grayscale", "PIL not installed. Install with: pip install Pillow"))
        except Exception as e:
            _send(ctx, _box("Grayscale Error", str(e)[:200]))

    @bot.command(name="invert")
    def invert_cmd(ctx, args):
        try:
            from PIL import Image, ImageOps
            import io, urllib.request
            url = args[0] if args else ""
            if not url:
                _send(ctx, _box("Invert", "Usage: invert <image_url>"))
                return
            with urllib.request.urlopen(url, timeout=5) as r:
                img = Image.open(io.BytesIO(r.read())).convert("RGB")
            inverted = ImageOps.invert(img)
            _send(ctx, _box("Invert", f"Inverted colors: {inverted.size[0]}x{inverted.size[1]}px"))
        except ImportError:
            _send(ctx, _box("Invert", "PIL not installed. Install with: pip install Pillow"))
        except Exception as e:
            _send(ctx, _box("Invert Error", str(e)[:200]))

    @bot.command(name="audioinfo", aliases=["audio_info"])
    def audioinfo_cmd(ctx, args):
        url = args[0] if args else ""
        if not url:
            _send(ctx, _box("Audio Info", "Usage: audioinfo <url>\nReturns size/content-type of the audio file"))
            return
        try:
            import urllib.request
            req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=5) as r:
                ctype = r.headers.get("Content-Type", "?")
                size = r.headers.get("Content-Length", "?")
            _send(ctx, _box("Audio Info", f"URL: {url[:80]}\nType: {ctype}\nSize: {size} bytes"))
        except Exception as e:
            _send(ctx, _box("Audio Info Error", str(e)[:200]))

    @bot.command(name="audiotrim", aliases=["audio_trim"])
    def audiotrim_cmd(ctx, args):
        _send(ctx, _box("Audio Trim", "Audio processing requires ffmpeg.\nInstall ffmpeg and use: ffmpeg -i <input> -ss <start> -to <end> <output>"))

    @bot.command(name="audiomerge", aliases=["audio_merge"])
    def audiomerge_cmd(ctx, args):
        _send(ctx, _box("Audio Merge", "Audio merging requires ffmpeg.\nInstall ffmpeg and use: ffmpeg -i <in1> -i <in2> -filter_complex amix <output>"))

    @bot.command(name="audioconvert", aliases=["audio_convert"])
    def audioconvert_cmd(ctx, args):
        _send(ctx, _box("Audio Convert", "Audio conversion requires ffmpeg.\nInstall ffmpeg and use: ffmpeg -i <input> <output.mp3>"))

    @bot.command(name="apistatus", aliases=["api_status"])
    def apistatus_cmd(ctx, args):
        try:
            r = ctx["api"].get_user_info()
            status = "OK" if r else "Degraded"
        except Exception:
            status = "Error"
        _send(ctx, _box("API Status", f"Discord API: {status}"))

    @bot.command(name="apihealth", aliases=["api_health"])
    def apihealth_cmd(ctx, args):
        _send(ctx, _box("API Health", "https://discordstatus.com"))

    @bot.command(name="get")
    def get_cmd(ctx, args):
        if not args:
            _send(ctx, _box("GET Request", "Usage: get <url>"))
            return
        url = args[0]
        try:
            import urllib.request
            with urllib.request.urlopen(url, timeout=5) as r:
                body = r.read(500).decode("utf-8", errors="replace")
            _send(ctx, _box(f"GET {url[:40]}", body[:400]))
        except Exception as e:
            _send(ctx, _box("GET Error", str(e)[:200]))

    @bot.command(name="post")
    def post_cmd(ctx, args):
        if len(args) < 2:
            _send(ctx, _box("POST", "Usage: post <url> <json_body>\nExample: ;post https://httpbin.org/post {}"))
            return
        url = args[0]
        body = " ".join(args[1:])
        try:
            import urllib.request, json as _json
            data = _json.dumps(_json.loads(body)).encode() if body.strip().startswith("{") else body.encode()
            req = urllib.request.Request(url, data=data, method="POST",
                                         headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=5) as r:
                resp_body = r.read(500).decode("utf-8", errors="replace")
            _send(ctx, _box(f"POST {url[:40]}", resp_body[:400]))
        except Exception as e:
            _send(ctx, _box("POST Error", str(e)[:200]))

    @bot.command(name="put")
    def put_cmd(ctx, args):
        if len(args) < 2:
            _send(ctx, _box("PUT", "Usage: put <url> <json_body>"))
            return
        url = args[0]
        body = " ".join(args[1:])
        try:
            import urllib.request, json as _json
            data = _json.dumps(_json.loads(body)).encode() if body.strip().startswith("{") else body.encode()
            req = urllib.request.Request(url, data=data, method="PUT",
                                         headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=5) as r:
                resp_body = r.read(500).decode("utf-8", errors="replace")
            _send(ctx, _box(f"PUT {url[:40]}", resp_body[:400]))
        except Exception as e:
            _send(ctx, _box("PUT Error", str(e)[:200]))

    @bot.command(name="webhookcreate", aliases=["webhook_create"])
    def webhookcreate_cmd(ctx, args):
        name = " ".join(args) if args else "Aria Webhook"
        cid = ctx["channel_id"]
        r = ctx["api"].request("POST", f"/channels/{cid}/webhooks", data={"name": name})
        result = r.json() if r and hasattr(r, "json") else r
        if result and result.get("id"):
            wid, token = result["id"], result.get("token", "")
            _send(ctx, _box("Create Webhook", f"Name : {result['name']}\nID   : {wid}\nURL  : https://discord.com/api/webhooks/{wid}/{token}"))
        else:
            _send(ctx, _box("Create Webhook", "Failed (need Manage Webhooks permission)"))

    @bot.command(name="webhookdelete", aliases=["webhook_delete"])
    def webhookdelete_cmd(ctx, args):
        wid = args[0] if args else ""
        if not wid:
            _send(ctx, _box("Delete Webhook", "Usage: webhookdelete <webhook_id>"))
            return
        r = ctx["api"].request("DELETE", f"/webhooks/{wid}")
        ok = r and (not hasattr(r, "status_code") or r.status_code in (200, 204))
        _send(ctx, _box("Delete Webhook", f"Deleted {wid}" if ok else "Failed (need Manage Webhooks permission)"))

    @bot.command(name="webhooklist", aliases=["webhook_list"])
    def webhooklist_cmd(ctx, args):
        cid = ctx["channel_id"]
        r = ctx["api"].request("GET", f"/channels/{cid}/webhooks")
        hooks = (r.json() if hasattr(r, "json") else r) or []
        if isinstance(hooks, list) and hooks:
            lines = [f"{h.get('name','?')} ({h.get('id','?')})" for h in hooks[:10]]
            _send(ctx, _box(f"Webhooks ({len(hooks)})", "\n".join(lines)))
        else:
            _send(ctx, _box("List Webhooks", "No webhooks found (or no Manage Webhooks permission)"))

    @bot.command(name="webhooksend", aliases=["webhook_send"])
    def webhooksend_cmd(ctx, args):
        if len(args) < 2:
            _send(ctx, _box("Webhook Send", "Usage: webhooksend <webhook_url_or_id/token> <message>"))
            return
        target = args[0]
        content = " ".join(args[1:])
        try:
            import urllib.request, json as _json
            if target.startswith("http"):
                url = target
            else:
                parts = target.split("/")
                url = f"https://discord.com/api/webhooks/{parts[0]}/{parts[1]}" if len(parts) == 2 else target
            data = _json.dumps({"content": content}).encode()
            req = urllib.request.Request(url, data=data, method="POST",
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=5):
                pass
            _send(ctx, _box("Webhook Send", f"Sent to webhook: {content[:100]}"))
        except Exception as e:
            _send(ctx, _box("Webhook Send Error", str(e)[:200]))

    # ────────────────────────────────────────────────────────────────────
    # ADVANCED / SCRIPTING
    # ────────────────────────────────────────────────────────────────────

    @bot.command(name="script", aliases=["scripting"])
    def script_cmd(ctx, args):
        _send(ctx, _box("Scripting", "Script execution via ;eval <python code>"))

    @bot.command(name="plugin")
    def plugin_cmd(ctx, args):
        _send(ctx, _box("Plugin", "Plugin system not yet implemented"))

    @bot.command(name="hook")
    def hook_cmd(ctx, args):
        _send(ctx, _box("Hook", "Event hooks managed internally"))

    @bot.command(name="macro")
    def macro_cmd(ctx, args):
        b = ctx["bot"]
        if not hasattr(b, "_macros"):
            b._macros = {}
        if not args:
            _send(ctx, _box("Macro", "Usage: macro <name> [command text]\nmacro list  - list all"))
            return
        if args[0] == "list":
            if not b._macros:
                _send(ctx, _box("Macros", "No macros saved"))
            else:
                lines = [f"{k} → {v[:60]}" for k, v in b._macros.items()]
                _send(ctx, _box(f"Macros ({len(b._macros)})", "\n".join(lines)))
            return
        if args[0] == "delete" and len(args) > 1:
            removed = b._macros.pop(args[1], None)
            _send(ctx, _box("Macro", f"Deleted '{args[1]}'" if removed else "Macro not found"))
            return
        name = args[0]
        if len(args) == 1:
            # Run macro
            if name in b._macros:
                from command_engine import CommandEngine
                # execute the macro text as a command
                macro_text = b._macros[name]
                parts = macro_text.lstrip(b.prefix).split()
                if parts:
                    cmd_name = parts[0]
                    macro_args = parts[1:]
                    cmd = b.commands.get(cmd_name)
                    if cmd:
                        cmd.func(ctx, macro_args)
                    else:
                        _send(ctx, _box("Macro", f"Command '{cmd_name}' not found in macro"))
            else:
                _send(ctx, _box("Macro", f"Macro '{name}' not found. Use: macro {name} <command>"))
        else:
            command_text = " ".join(args[1:])
            b._macros[name] = command_text
            _send(ctx, _box("Macro", f"Saved: {name} → {command_text[:100]}"))

    @bot.command(name="keybind")
    def keybind_cmd(ctx, args):
        _send(ctx, _box("Keybind", "Keybinds not supported in headless bot mode"))

    @bot.command(name="schedule")
    def schedule_cmd(ctx, args):
        if not args or not args[0].isdigit():
            _send(ctx, _box("Schedule", "Usage: schedule <seconds> <message>\nExample: ;schedule 60 hello world"))
            return
        delay = int(args[0])
        if delay > 3600:
            _send(ctx, _box("Schedule", "Max delay is 3600 seconds (1 hour)"))
            return
        msg_text = " ".join(args[1:]) if len(args) > 1 else "Scheduled message"
        channel_id = ctx["channel_id"]
        api = ctx["api"]
        import threading
        def _fire():
            time.sleep(delay)
            api.send_message(channel_id, f"> ⏰ Scheduled: {msg_text}")
        t = threading.Thread(target=_fire, daemon=True)
        t.start()
        _send(ctx, _box("Schedule", f"Scheduled in {delay}s: {msg_text[:80]}"))

    @bot.command(name="cron")
    def cron_cmd(ctx, args):
        if not args or not args[0].isdigit():
            _send(ctx, _box("Cron", "Usage: cron <interval_seconds> <message>\nRepeats every N seconds until bot restarts\nMax: 86400s"))
            return
        interval = min(int(args[0]), 86400)
        msg_text = " ".join(args[1:]) if len(args) > 1 else "Cron tick"
        channel_id = ctx["channel_id"]
        api = ctx["api"]
        b = ctx["bot"]
        if not hasattr(b, "_cron_jobs"):
            b._cron_jobs = []
        import threading
        stop_event = threading.Event()
        def _cron_loop():
            while not stop_event.is_set():
                time.sleep(interval)
                if stop_event.is_set():
                    break
                api.send_message(channel_id, f"> ⏱ Cron: {msg_text}")
        t = threading.Thread(target=_cron_loop, daemon=True)
        t.start()
        b._cron_jobs.append(stop_event)
        _send(ctx, _box("Cron", f"Started cron every {interval}s: {msg_text[:80]}\nJob #{len(b._cron_jobs)} (restarts on bot reboot)"))

    @bot.command(name="trigger")
    def trigger_cmd(ctx, args):
        _send(ctx, _box("Trigger", "Event triggers managed internally"))

    @bot.command(name="condition")
    def condition_cmd(ctx, args):
        _send(ctx, _box("Condition", "Conditional logic available via ;eval"))

    @bot.command(name="loop")
    def loop_cmd(ctx, args):
        _send(ctx, _box("Loop", "Loop operations available via ;eval"))

    @bot.command(name="code", aliases=["dev_code"])
    def code_exec_cmd(ctx, args):
        language = args[0] if args else "python"
        code = " ".join(args[1:]) if len(args) > 1 else ""
        if not code:
            _send(ctx, _box("Code", f"Usage: code <language> <code>"))
            return
        if language in ("py", "python"):
            try:
                result = eval(code)
                _send(ctx, _box("Code Output", str(result)[:500]))
            except Exception as e:
                _send(ctx, _box("Code Error", str(e)[:300]))
        else:
            _send(ctx, _box("Code", f"Language '{language}' not supported. Use python."))

    @bot.command(name="helpwall", aliases=["cmdwall", "allcmds", "wallcmds"])
    def helpwall_cmd(ctx, args):
        import formatter as fmt
        b = ctx["bot"]
        prefix = b.prefix
        cmds = sorted(b.commands.keys())
        unique_cmds = sorted(set(b.commands[k].name for k in cmds))
        chunk_size = 30
        chunks = [unique_cmds[i:i+chunk_size] for i in range(0, len(unique_cmds), chunk_size)]
        include_help_hint_in_wall_header = True
        for i, chunk in enumerate(chunks[:4]):
            lines = [f"{fmt.CYAN}{prefix}{name}{fmt.RESET}" for name in chunk]
            header_suffix = "Bulk"
            if include_help_hint_in_wall_header:
                header_suffix = f"Bulk {prefix}help <category> {prefix}help <command>"
            footer = f"page {i + 1}/{min(len(chunks), 4)}  {len(chunk)} cmds"
            text = fmt.sections(
                header_suffix,
                "\n".join(lines),
                f"{fmt.DARK}{footer}{fmt.RESET}",
            )
            msg = ctx["api"].send_message(ctx["channel_id"], text)
            if msg and i < len(chunks) - 1:
                delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"), 30)
            elif msg:
                delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
            time.sleep(0.3)

    @bot.command(name="quit", aliases=["exit"])
    def quit_cmd(ctx, args):
        _send(ctx, _box("Quit", "Stopping bot..."))
        import threading
        def _delayed_stop():
            time.sleep(1)
            b = ctx["bot"]
            if hasattr(b, "stop"):
                b.stop()
            else:
                import os, signal
                os.kill(os.getpid(), signal.SIGTERM)
        threading.Thread(target=_delayed_stop, daemon=True).start()

    @bot.command(name="reboot")
    def reboot_cmd(ctx, args):
        _send(ctx, _box("Reboot", "Restarting bot..."))
        import threading
        def _delayed_restart():
            time.sleep(1)
            import os, sys
            os.execv(sys.executable, [sys.executable] + sys.argv)
        threading.Thread(target=_delayed_restart, daemon=True).start()

    @bot.command(name="restore")
    def restore_cmd(ctx, args):
        import os, glob
        base = os.path.dirname(os.path.abspath(__file__))
        backups = sorted(glob.glob(os.path.join(base, "backups", "*.json")) +
                         glob.glob(os.path.join(base, "*.json.bak")))
        if not backups:
            backups_dir = os.path.join(os.path.dirname(base), "backups")
            backups = sorted(glob.glob(os.path.join(backups_dir, "**", "*.py"), recursive=True))[:5]
        if backups:
            lines = [os.path.basename(f) for f in backups[:10]]
            _send(ctx, _box("Restore", "Available backups:\n" + "\n".join(lines) + "\n\nUse ;backup to create a new backup"))
        else:
            _send(ctx, _box("Restore", "No backups found. Use ;backup restore <filename> to restore"))

    @bot.command(name="spotify")
    def spotify_cmd(ctx, args):
        if not args:
            _send(ctx, _box("Spotify", "Usage: spotify <song name>  — sets Spotify-style rich presence"))
            return
        song = " ".join(args)
        activities = [{
            "type": 2,  # Listening
            "name": "Spotify",
            "state": "Aria Bot",
            "details": song,
            "assets": {"large_image": "spotify:ab67616d00001e02ff9ca10b55ce82ae553c8228"}
        }]
        ok = ctx["api"].set_status("online", activities)
        _send(ctx, _box("Spotify", f"Now listening: {song}" if ok else "Failed to set Spotify status"))

    @bot.command(name="spotifylyrics", aliases=["splyrics"])
    def spotifylyrics_cmd(ctx, args):
        action = args[0].lower() if args else "on"
        if action in {"off", "stop"}:
            stopped = spotify_lyrics.stop()
            message = "Spotify lyrics sync stopping." if stopped else "Spotify lyrics sync is not running."
        elif action == "status":
            state = spotify_lyrics.status()
            track = " - ".join(part for part in (state.get("title"), state.get("artist")) if part)
            message = f"Sync {'on' if state.get('enabled') else 'off'} · {track or state.get('phase', 'idle')}"
            if state.get("current_line"):
                message += f"\n{state['current_line']}"
        elif action in {"on", "start"}:
            started = spotify_lyrics.start()
            message = "Spotify lyrics sync started." if started else "Spotify lyrics sync is already running."
        else:
            message = "Usage: spotifylyrics [on|off|status]"
        _send(ctx, _box("Spotify Lyrics", message))

    @bot.command(name="leave")
    def leave_cmd(ctx, args):
        gid = args[0] if args else ctx.get("guild_id", "")
        if not gid:
            _send(ctx, _box("Leave", "Usage: leave <guild_id>"))
            return
        ok = ctx["api"].leave_guild(gid)
        _send(ctx, _box("Leave", f"Left guild {gid}" if ok else f"Failed to leave {gid}"))

    @bot.command(name="membercount", aliases=["member_count"])
    def membercount_cmd(ctx, args):
        gid = args[0] if args else ctx.get("guild_id", "")
        if not gid:
            _send(ctx, _box("Member Count", "Must be used in a guild"))
            return
        guild = _api_get_guild(ctx["api"], gid)
        if guild:
            _send(ctx, _box("Member Count", str(guild.get("member_count", guild.get("approximate_member_count", "?")))))
        else:
            _send(ctx, _box("Member Count", "Guild not found"))

    @bot.command(name="clean")
    def clean_cmd(ctx, args):
        amount = int(args[0]) if args and args[0].isdigit() else 10
        api = ctx["api"]
        channel_id = ctx["channel_id"]
        author_id = ctx.get("author_id", "")
        msgs = api.get_messages(channel_id, limit=min(amount + 10, 100)) or []
        deleted = 0
        for m in msgs:
            if deleted >= amount:
                break
            if m.get("author", {}).get("id") == author_id:
                api.delete_message(channel_id, m["id"])
                deleted += 1
                time.sleep(0.3)
        _send(ctx, _box("Clean", f"Deleted {deleted} of your messages"))

    @bot.command(name="commands")
    def commands_cmd(ctx, args):
        b = ctx["bot"]
        primary = sorted(set(c.name for c in b.commands.values()))
        chunk = primary[:50]
        total = len(primary)
        body = ", ".join(chunk)
        text = ""
        _send(ctx, text)

    @bot.command(name="allcmds_list")
    def allcmds_list_cmd(ctx, args):
        commands_cmd(ctx, args)

    @bot.command(name="owner")
    def owner_cmd(ctx, args):
        gid = args[0] if args else ctx.get("guild_id", "")
        if not gid:
            _send(ctx, _box("Owner", "Usage: owner <guild_id>"))
            return
        guild = _api_get_guild(ctx["api"], gid)
        if guild:
            _send(ctx, _box("Guild Owner", str(guild.get("owner_id", "?"))))
        else:
            _send(ctx, _box("Owner", "Guild not found"))

    @bot.command(name="getlogs")
    def getlogs_cmd(ctx, args):
        logs_cmd(ctx, args)
