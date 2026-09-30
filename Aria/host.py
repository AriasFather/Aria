import json
import time
import threading
import subprocess
import os
import sys
import shutil
import logging
import signal
from datetime import datetime, timedelta

HOSTED_USERS_FILE = "hosted_users.json"
logger = logging.getLogger(__name__)


def _hosted_process_is_alive(pid, token_id):
    try:
        pid = int(pid)
        os.kill(pid, 0)
    except (OSError, TypeError, ValueError):
        return False

    if os.name == "posix":
        cmdline_path = f"/proc/{pid}/cmdline"
        if os.path.exists(cmdline_path):
            try:
                command_line = open(cmdline_path, "rb").read()
                if f"hosted_bot_{token_id}".encode() not in command_line:
                    return False
                stat = open(f"/proc/{pid}/stat", "r", encoding="utf-8").read()
                if stat.split(") ", 1)[-1].split()[0] == "Z":
                    return False
            except OSError:
                return False
    return True


class _AttachedHostedProcess:
    def __init__(self, pid, token_id):
        self.pid = int(pid)
        self.token_id = str(token_id)

    def poll(self):
        return None if _hosted_process_is_alive(self.pid, self.token_id) else 0

    def wait(self, timeout=None):
        deadline = None if timeout is None else time.monotonic() + timeout
        while self.poll() is None:
            if deadline is not None and time.monotonic() >= deadline:
                raise subprocess.TimeoutExpired(str(self.pid), timeout)
            time.sleep(0.05)
        return 0


class HostManager:
    def __init__(self):
        self.active_tokens = {}   # token_id -> runtime data
        self.processes = {}
        self.saved_users = {}     # token_id -> persisted settings
        self.lock = threading.Lock()
        self.hosting_enabled = True  # owner toggle — allows non-owners to use +host
        self._stop_events = {}    # token_id -> threading.Event for keepalive control
        self.rate_limits = {}     # owner_command -> datetime
        self._restore_lock = threading.Lock()
        self._restore_in_progress = False
        self._load_saved_users()
        # Removed: self._print_startup_summary()  <- This was causing duplicate loading

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load_saved_users(self):
        try:
            if os.path.exists(HOSTED_USERS_FILE):
                with open(HOSTED_USERS_FILE, "r") as f:
                    self.saved_users = json.load(f)
                    # Ensure UID is always present
                    for token_id, user_data in self.saved_users.items():
                        if "uid" not in user_data:
                            user_data["uid"] = "unknown"
        except Exception:
            self.saved_users = {}
    
    def print_loaded_users_summary(self):
        """
        Call this ONCE after all initialization is complete.
        This prevents duplicate user loading at startup.
        """
        total = len(self.saved_users)
        pass  # hosted user summary suppressed — hosted bots have their own logs

    def _save_users(self):
        try:
            with open(HOSTED_USERS_FILE, "w") as f:
                json.dump(self.saved_users, f, indent=4)
        except Exception as e:
            print(f"Host save error: {e}")

    def _remove_duplicate_saved_tokens_locked(self):
        """Drop duplicate saved entries that point to the same token."""
        seen = {}
        dup_ids = []
        for token_id, data in self.saved_users.items():
            token = str(data.get("token") or "").strip()
            if not token:
                continue
            if token in seen:
                dup_ids.append(token_id)
            else:
                seen[token] = token_id
        for token_id in dup_ids:
            self.saved_users.pop(token_id, None)
        return len(dup_ids)

    def _has_existing_token_locked(self, token):
        token = str(token or "").strip()
        if not token:
            return False
        for data in self.active_tokens.values():
            if str(data.get("token") or "").strip() == token:
                return True
        for data in self.saved_users.values():
            if str(data.get("token") or "").strip() == token:
                return True
        return False

    def _user_has_active_hosted_locked(self, owner_id):
        """Return True if this owner_id already has an active hosted entry."""
        owner_id = str(owner_id or "").strip()
        if not owner_id:
            return False
        for data in self.active_tokens.values():
            if str(data.get("owner") or "") == owner_id:
                return True
        return False

    def _attach_existing_process(self, token_id, data):
        pid = data.get("pid")
        if pid and _hosted_process_is_alive(pid, token_id):
            return _AttachedHostedProcess(pid, token_id)
        return None

    # ------------------------------------------------------------------

    def can_use_command(self, user_id):
        """Hosted users can only manage their own tokens, not other users' tokens"""
        user_id = str(user_id)
        for entry in self.saved_users.values():
            if str(entry.get("owner")) == user_id:
                return True
        return False

    def is_token_owner(self, user_id, token_id):
        """Check if user owns this token"""
        token_id = str(token_id)
        user_id = str(user_id)
        if token_id in self.saved_users:
            return str(self.saved_users[token_id].get("owner")) == user_id
        return False

    def is_rate_limited(self, user_id, command="host", cooldown_seconds=30):
        now = datetime.utcnow()
        key = f"{user_id}_{command}"
        last_used = self.rate_limits.get(key)
        if last_used and now - last_used < timedelta(seconds=cooldown_seconds):
            remaining = int((last_used + timedelta(seconds=cooldown_seconds) - now).total_seconds())
            return True, max(1, remaining)
        self.rate_limits[key] = now
        return False, 0

    def cleanup_old_rate_limits(self):
        cutoff = datetime.utcnow() - timedelta(hours=1)
        stale = [key for key, used_at in self.rate_limits.items() if used_at < cutoff]
        for key in stale:
            self.rate_limits.pop(key, None)

    def validate_token_api(self, token, session=None):
        if not token:
            return False, None
        try:
            headers = {
                "Authorization": token,
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Origin": "https://discord.com",
                "Referer": "https://discord.com/channels/@me",
                "Dnt": "1",
                "Connection": "keep-alive",
            }
            if session is not None:
                response = session.get(
                    "https://discord.com/api/v9/users/@me",
                    headers=headers,
                    timeout=12,
                )
            else:
                import requests

                response = requests.get(
                    "https://discord.com/api/v9/users/@me",
                    headers=headers,
                    timeout=12,
                )
            if response.status_code == 200:
                return True, response.json() or {}
            return False, None
        except Exception as exc:
            logger.error("Host token validation failed: %s", exc)
            return False, None

    def host_token(self, owner_id, token_input, prefix="$", user_id=None, username=None):
        if not token_input:
            return False, "No token"

        token = self._clean_token(token_input)
        if not token:
            return False, "Bad token"

        with self.lock:
            removed = self._remove_duplicate_saved_tokens_locked()
            if removed:
                self._save_users()

            if self._has_existing_token_locked(token):
                return False, "Already hosted"

            # Prevent same requester from hosting more than once
            if owner_id and self._user_has_active_hosted_locked(owner_id):
                return False, "Already hosting"

            token_id = str(int(time.time() * 1000))
            config_file = f"hosted_{token_id}.json"
            with open(config_file, "w") as f:
                json.dump({"token": token, "prefix": prefix}, f)

            process = self._run_their_bot(
                config_file,
                token,
                prefix=prefix,
                hosted_uid=token_id,
                owner_id=owner_id,
                user_id=user_id,
                username=username,
            )
            if not process:
                return False, "Start failed"

            entry = {
                "uid": token_id,
                "user_id": user_id or "",
                "username": username or "",
                "token": token,
                "prefix": prefix,
                "owner": owner_id,
                "config": config_file,
                "connected_at": int(time.time()),
                "pid": process.pid,
            }
            self.active_tokens[token_id] = entry
            self.processes[token_id] = process

            # Persist (no process handle)
            self.saved_users[token_id] = {k: v for k, v in entry.items() if k != "config"}
            self._save_users()

            logger.info("Hosted token created: owner=%s uid=%s user_id=%s username=%s", owner_id, token_id, user_id, username)

            pass  # hosted bot start suppressed — output goes to hosted log

        self._start_keepalive(token_id)
        return True, "Hosting token"
    
    def _clean_token(self, token_input):
        token_input = token_input.strip('"\' ')
        
        if token_input.startswith("{"):
            try:
                data = json.loads(token_input)
                return data.get("token", "")
            except:
                return token_input
        
        return token_input if "." in token_input else ""
    
    def _run_their_bot(self, config_file, token, prefix="$", hosted_uid=None, owner_id=None, user_id=None, username=None):
        try:
            project_root = os.path.dirname(os.path.abspath(__file__))
            config_source = os.path.abspath(config_file)
            runner_code = f"""
import sys, os, json, shutil

SOURCE_ROOT = {project_root!r}
SOURCE_CONFIG_FILE = {config_source!r}
TEMP_DIR = os.path.join(SOURCE_ROOT, "hosted_bot_{hosted_uid}")
SYNC_DIRS = ("cogs", "core", "static", "utils", "web_ui")
SYNC_FILE_SUFFIXES = (".py", ".html")
IGNORE_NAMES = {{"__pycache__", ".git", ".pytest_cache", ".mypy_cache", "hosted_logs", "dist"}}


def _should_copy_root_file(file_name):
    if file_name in {{
        "config.json",
        "runtime_state.json",
        "rpc_profiles.json",
        "hosted_users.json",
        "admin_users.json",
        "authed_users.json",
        "dashboard_users.json",
        "dashboard_authed_users.json",
        "dashboard_blocked_users.json",
    }}:
        return False
    if file_name.startswith("runner_") and file_name.endswith(".py"):
        return False
    if file_name.startswith("hosted_") and file_name.endswith((".json", ".log")):
        return False
    return file_name.endswith(SYNC_FILE_SUFFIXES)


def _copy_root_files():
    for file_name in os.listdir(SOURCE_ROOT):
        source_path = os.path.join(SOURCE_ROOT, file_name)
        dest_path = os.path.join(TEMP_DIR, file_name)
        if not os.path.isfile(source_path) or not _should_copy_root_file(file_name):
            continue
        try:
            shutil.copy2(source_path, dest_path)
        except Exception:
            pass


def _sync_directory_tree(directory_name):
    source_dir = os.path.join(SOURCE_ROOT, directory_name)
    dest_dir = os.path.join(TEMP_DIR, directory_name)
    if not os.path.isdir(source_dir):
        return
    try:
        shutil.copytree(
            source_dir,
            dest_dir,
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
        )
    except Exception:
        pass


def _sync_project_tree():
    os.makedirs(TEMP_DIR, exist_ok=True)
    stale_files = {{
        "hosted_users.json",
        "admin_users.json",
        "authed_users.json",
        "dashboard_users.json",
        "dashboard_authed_users.json",
        "dashboard_blocked_users.json",
    }}
    for file_name in os.listdir(TEMP_DIR):
        if file_name in stale_files or (file_name.startswith("hosted_") and file_name.endswith(".json")) or (file_name.startswith("runner_") and file_name.endswith(".py")):
            try:
                os.remove(os.path.join(TEMP_DIR, file_name))
            except OSError:
                pass
    _copy_root_files()
    for directory_name in SYNC_DIRS:
        _sync_directory_tree(directory_name)
    shutil.copy2(SOURCE_CONFIG_FILE, os.path.join(TEMP_DIR, "config.json"))


_sync_project_tree()

for path in (TEMP_DIR, SOURCE_ROOT):
    if path not in sys.path:
        sys.path.insert(0, path)

os.chdir(TEMP_DIR)

env = os.environ.copy()
existing_pythonpath = env.get("PYTHONPATH", "")
pythonpath_parts = [TEMP_DIR, SOURCE_ROOT]
if existing_pythonpath:
    pythonpath_parts.append(existing_pythonpath)
env["PYTHONPATH"] = os.pathsep.join(pythonpath_parts)
env["HOSTED_TOKEN"] = "true"
env["HOSTED_UID"] = {hosted_uid!r}
env["HOSTED_OWNER_ID"] = {owner_id!r}
env["HOSTED_USER_ID"] = {user_id!r}
env["HOSTED_USERNAME"] = {username!r}
env["HOSTED_COMMANDS_FILE"] = os.path.join(SOURCE_ROOT, "hosted_runtime", {("commands_" + str(hosted_uid) + ".json")!r})
env["HOSTED_RUNTIME_DIR"] = os.path.join(SOURCE_ROOT, "hosted_runtime", {str(hosted_uid)!r})

if getattr(sys, "frozen", False):
    os.execvpe(sys.executable, [sys.executable, "--aria-run-script", os.path.join(TEMP_DIR, "main.py")], env)
else:
    os.execvpe(sys.executable, [sys.executable, os.path.join(TEMP_DIR, "main.py")], env)
"""
            # Fixed runner filename per token so keepalive restarts work cleanly
            runner_file = os.path.join(project_root, f"runner_{hosted_uid}.py")
            with open(runner_file, "w") as f:
                f.write(runner_code)

            # Each hosted bot writes to its own log — keeps main console clean
            log_dir = os.path.join(project_root, "hosted_logs")
            os.makedirs(log_dir, exist_ok=True)
            log_path = os.path.join(log_dir, f"hosted_{hosted_uid}.log")
            log_file = open(log_path, "a")

            command = [sys.executable, runner_file]
            if getattr(sys, "frozen", False):
                command = [sys.executable, "--aria-run-script", runner_file]
            popen_kwargs = {
                "args": command,
                "stdout": log_file,
                "stderr": log_file,
                "stdin": subprocess.DEVNULL,
                "cwd": project_root,
            }
            if os.name == "nt":
                popen_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
            else:
                # Detach hosted instances from controller process group so they survive main shutdown.
                popen_kwargs["start_new_session"] = True

            process = subprocess.Popen(**popen_kwargs)
            log_file.close()  # parent closes; child keeps its own fd copy
            return process

        except Exception as e:
            logger.error("Host start error: %s", e)
            return None

    def _start_keepalive(self, token_id):
        """Spawn a daemon watchdog that auto-restarts a hosted bot when it crashes."""
        stop_event = threading.Event()
        self._stop_events[token_id] = stop_event

        def _monitor():
            restart_count = 0
            while not stop_event.is_set():
                time.sleep(5)
                if stop_event.is_set():
                    break

                with self.lock:
                    process = self.processes.get(token_id)
                if process is None:
                    break

                ret = process.poll()
                if ret is None:
                    # Still running — nothing to do
                    continue

                # Process exited
                if stop_event.is_set():
                    break

                restart_count += 1
                with self.lock:
                    saved = self.saved_users.get(token_id, {})
                uname = saved.get("username") or "unknown"
                uid = saved.get("uid") or token_id
                pass  # keepalive restart suppressed — output goes to hosted log
                time.sleep(5)
                if stop_event.is_set():
                    break

                with self.lock:
                    saved = self.saved_users.get(token_id)
                if not saved:
                    break
                token = saved.get("token")
                if not token:
                    break

                new_process = self._run_their_bot(
                    f"hosted_{token_id}.json",
                    token,
                    prefix=saved.get("prefix", "$"),
                    hosted_uid=token_id,
                    owner_id=saved.get("owner"),
                    user_id=saved.get("user_id"),
                    username=saved.get("username"),
                )
                if new_process and not stop_event.is_set():
                    with self.lock:
                        self.processes[token_id] = new_process
                        active = self.active_tokens.get(token_id)
                        if active is not None:
                            active["pid"] = new_process.pid
                        saved = self.saved_users.get(token_id)
                        if saved is not None:
                            saved["pid"] = new_process.pid
                            self._save_users()
                else:
                    break  # failed to restart — give up silently

        t = threading.Thread(target=_monitor, name=f"keepalive-{token_id}", daemon=True)
        t.start()
        self._stop_events[token_id] = stop_event
        self._keepalive_threads = getattr(self, '_keepalive_threads', {})
        self._keepalive_threads[token_id] = t

    @staticmethod
    def _terminate_process(process):
        if process is None:
            return
        process_id = getattr(process, "pid", None)
        if process_id:
            if os.name == "nt":
                try:
                    subprocess.run(
                        ["taskkill", "/PID", str(process_id), "/T", "/F"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        check=False,
                    )
                    return
                except Exception:
                    pass
            else:
                try:
                    os.killpg(process_id, signal.SIGTERM)
                    try:
                        process.wait(timeout=4)
                    except subprocess.TimeoutExpired:
                        pass
                    try:
                        os.killpg(process_id, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    return
                except (OSError, TypeError):
                    pass
        try:
            process.terminate()
            process.wait(timeout=4)
        except Exception:
            pass

    @staticmethod
    def _cleanup_hosted_instance_files(token_id):
        token_ref = str(token_id or "").strip()
        if not token_ref or any(char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for char in token_ref):
            return

        project_root = os.path.dirname(os.path.abspath(__file__))
        working_roots = {project_root, os.path.abspath(os.getcwd())}
        for root in working_roots:
            generated_dirs = (
                os.path.join(root, f"hosted_bot_{token_ref}"),
                os.path.join(root, "hosted_runtime", token_ref),
            )
            for path in generated_dirs:
                shutil.rmtree(path, ignore_errors=True)

            generated_files = (
                os.path.join(root, f"runner_{token_ref}.py"),
                os.path.join(root, f"hosted_{token_ref}.json"),
                os.path.join(root, "hosted_logs", f"hosted_{token_ref}.log"),
                os.path.join(root, "hosted_runtime", f"commands_{token_ref}.json"),
            )
            for path in generated_files:
                try:
                    os.remove(path)
                except OSError:
                    pass
    
    def stop_hosting(self, owner_id):
        # Join keepalive threads for this owner
        self._keepalive_threads = getattr(self, '_keepalive_threads', {})
        to_join = []
        with self.lock:
            for token_id, data in self.active_tokens.items():
                if str(data["owner"]) == str(owner_id):
                    t = self._keepalive_threads.pop(token_id, None)
                    if t and t.is_alive():
                        to_join.append(t)
        for t in to_join:
            t.join(timeout=5)
        with self.lock:
            to_stop = []
            for token_id, data in self.active_tokens.items():
                if str(data["owner"]) == str(owner_id):
                    to_stop.append((token_id, data))
            
            for token_id, data in to_stop:
                stop_event = self._stop_events.pop(token_id, None)
                if stop_event:
                    stop_event.set()
                if token_id in self.processes:
                    self._terminate_process(self.processes[token_id])
                    del self.processes[token_id]
                del self.active_tokens[token_id]
                # Remove from persistent store
                self.saved_users.pop(token_id, None)
                self._cleanup_hosted_instance_files(token_id)
                pass  # stop suppressed — hosted bots have their own logs
            self._save_users()

            if to_stop:
                return True, f"Stopped {len(to_stop)}"
            return False, "None"
    
    def stop_all(self):
        """Stop every hosted token regardless of owner."""
        with self.lock:
            count = len(self.active_tokens)
            for token_id in list(self.active_tokens.keys()):
                data = self.active_tokens[token_id]
                stop_event = self._stop_events.pop(token_id, None)
                if stop_event:
                    stop_event.set()
                if token_id in self.processes:
                    self._terminate_process(self.processes[token_id])
                    del self.processes[token_id]
                del self.active_tokens[token_id]
                self.saved_users.pop(token_id, None)
                self._cleanup_hosted_instance_files(token_id)
                pass  # force-stop suppressed
            self._save_users()
            return count

    def restart_all(self):
        """Restart all persisted hosted tokens without deleting saved entries."""
        with self.lock:
            saved_entries = [(token_id, data.copy()) for token_id, data in self.saved_users.items()]
            active_ids = list(self.active_tokens.keys())

        # Stop currently running processes first.
        for token_id in active_ids:
            stop_event = self._stop_events.pop(token_id, None)
            if stop_event:
                stop_event.set()
            proc = self.processes.get(token_id)
            if proc:
                self._terminate_process(proc)

        with self.lock:
            self.processes = {}
            self.active_tokens = {}

        restarted = 0
        for token_id, data in saved_entries:
            token = data.get("token")
            if not self._is_token_valid(token):
                continue

            prefix = data.get("prefix", "$")
            config_file = f"hosted_{token_id}.json"
            process = self._run_their_bot(
                config_file,
                token,
                prefix=prefix,
                hosted_uid=data.get("uid") or token_id,
                owner_id=data.get("owner"),
                user_id=data.get("user_id"),
                username=data.get("username"),
            )
            if not process:
                continue

            entry = {
                "uid": data.get("uid") or token_id,
                "user_id": data.get("user_id", ""),
                "username": data.get("username", ""),
                "token": token,
                "prefix": prefix,
                "owner": data.get("owner", ""),
                "config": config_file,
                "pid": process.pid,
            }

            with self.lock:
                self.active_tokens[token_id] = entry
                self.processes[token_id] = process
                saved = self.saved_users.get(token_id)
                if saved is not None:
                    saved["pid"] = process.pid
                    self._save_users()

            self._start_keepalive(token_id)
            restarted += 1

        return restarted

    def list_hosted(self, requester_id):
        """Return only entries owned by requester_id."""
        with self.lock:
            requester_id = str(requester_id)
            return [v for v in self.saved_users.values() if str(v.get("owner")) == requester_id]

    def list_hosted_entries(self, requester_id=None):
        """Return sorted (token_id, entry) pairs, optionally filtered by owner."""
        with self.lock:
            entries = []
            for token_id, data in self.saved_users.items():
                if requester_id is not None and str(data.get("owner")) != str(requester_id):
                    continue
                entry = data.copy()
                entry.setdefault("uid", token_id)
                entry["token_id"] = token_id
                entries.append((token_id, entry))

        entries.sort(key=lambda item: (
            str(item[1].get("username") or "").lower(),
            str(item[1].get("user_id") or ""),
            str(item[1].get("uid") or item[0]),
        ))
        return entries

    def remove_hosts(self, requester_id=None, selectors=None, all_hosts=False):
        """Remove hosted entries by index, uid, token_id, or user_id."""
        scoped_entries = self.list_hosted_entries(None if all_hosts else requester_id)
        if not scoped_entries:
            return 0

        selector_values = [str(sel).strip() for sel in (selectors or []) if str(sel).strip()]
        selected_ids = []

        if selector_values:
            for selector in selector_values:
                matched = False
                if selector.isdigit():
                    index = int(selector) - 1
                    if 0 <= index < len(scoped_entries):
                        selected_ids.append(scoped_entries[index][0])
                        matched = True
                if matched:
                    continue

                for token_id, entry in scoped_entries:
                    if selector in {
                        str(token_id),
                        str(entry.get("uid") or ""),
                        str(entry.get("user_id") or ""),
                    }:
                        selected_ids.append(token_id)
                        matched = True
                if matched:
                    continue
        else:
            selected_ids = [token_id for token_id, _ in scoped_entries]

        removed = 0
        with self.lock:
            for token_id in list(dict.fromkeys(selected_ids)):
                data = self.saved_users.get(token_id)
                if not data:
                    continue
                stop_event = self._stop_events.pop(token_id, None)
                if stop_event:
                    stop_event.set()
                proc = self.processes.pop(token_id, None)
                if proc:
                    self._terminate_process(proc)
                self.active_tokens.pop(token_id, None)
                self.saved_users.pop(token_id, None)
                self._cleanup_hosted_instance_files(token_id)
                removed += 1
            self._save_users()

        if removed:
            logger.info("Removed %s hosted entr%s for requester=%s", removed, "y" if removed == 1 else "ies", requester_id or "all")

        return removed

    def restart_hosts(self, requester_id=None, selectors=None, all_hosts=False):
        """Restart hosted entries by index, uid, token_id, or user_id without deleting saved entries."""
        scoped_entries = self.list_hosted_entries(None if all_hosts else requester_id)
        if not scoped_entries:
            return 0

        selector_values = [str(sel).strip() for sel in (selectors or []) if str(sel).strip()]
        selected_ids = []

        if selector_values:
            for selector in selector_values:
                matched = False
                if selector.isdigit():
                    index = int(selector) - 1
                    if 0 <= index < len(scoped_entries):
                        selected_ids.append(scoped_entries[index][0])
                        matched = True
                if matched:
                    continue

                for token_id, entry in scoped_entries:
                    if selector in {
                        str(token_id),
                        str(entry.get("uid") or ""),
                        str(entry.get("user_id") or ""),
                    }:
                        selected_ids.append(token_id)
                        matched = True
                if matched:
                    continue
        else:
            selected_ids = [token_id for token_id, _ in scoped_entries]

        restarted = 0
        for token_id in list(dict.fromkeys(selected_ids)):
            with self.lock:
                saved = (self.saved_users.get(token_id) or {}).copy()
                proc = self.processes.get(token_id)
                stop_event = self._stop_events.pop(token_id, None)

            if not saved:
                continue
            token = saved.get("token")
            if not self._is_token_valid(token):
                continue

            if stop_event:
                stop_event.set()
            if proc:
                self._terminate_process(proc)

            prefix = saved.get("prefix", "$")
            config_file = f"hosted_{token_id}.json"
            new_process = self._run_their_bot(
                config_file,
                token,
                prefix=prefix,
                hosted_uid=saved.get("uid") or token_id,
                owner_id=saved.get("owner"),
                user_id=saved.get("user_id"),
                username=saved.get("username"),
            )
            if not new_process:
                continue

            entry = {
                "uid": saved.get("uid") or token_id,
                "user_id": saved.get("user_id", ""),
                "username": saved.get("username", ""),
                "token": token,
                "prefix": prefix,
                "owner": saved.get("owner", ""),
                "config": config_file,
                "connected_at": int(time.time()),
                "pid": new_process.pid,
            }

            with self.lock:
                self.active_tokens[token_id] = entry
                self.processes[token_id] = new_process
                saved_entry = self.saved_users.get(token_id)
                if saved_entry is not None:
                    saved_entry["pid"] = new_process.pid
                    self._save_users()

            self._start_keepalive(token_id)
            restarted += 1

        return restarted

    def validate_hosted_tokens(self, requester_id=None, session=None):
        scoped_entries = self.list_hosted_entries(requester_id)
        if not scoped_entries:
            return []

        removed = []
        for token_id, entry in scoped_entries:
            is_valid, account = self.validate_token_api(entry.get("token"), session=session)
            if is_valid:
                continue

            with self.lock:
                stop_event = self._stop_events.pop(token_id, None)
                if stop_event:
                    stop_event.set()
                proc = self.processes.pop(token_id, None)
                if proc:
                    self._terminate_process(proc)
                self.active_tokens.pop(token_id, None)
                removed_entry = self.saved_users.pop(token_id, None) or entry
                self._cleanup_hosted_instance_files(token_id)
                self._save_users()

            removed.append({
                "token_id": token_id,
                "uid": str(removed_entry.get("uid") or token_id),
                "user_id": str(removed_entry.get("user_id") or ""),
                "username": str(removed_entry.get("username") or "Unknown"),
            })

        if removed:
            logger.warning("Removed %s invalid hosted tokens for requester=%s", len(removed), requester_id or "all")
        return removed

    def list_all_hosted(self):
        """Return all saved hosted-user dicts (owner-only view)."""
        with self.lock:
            return list(self.saved_users.values())

    def restore_hosted_users(self):
        """Restart persisted hosted users on startup in the main controller process."""
        with self._restore_lock:
            if self._restore_in_progress:
                return 0
            self._restore_in_progress = True

        try:
            with self.lock:
                removed = self._remove_duplicate_saved_tokens_locked()
                if removed:
                    self._save_users()
                saved_entries = [(token_id, data.copy()) for token_id, data in self.saved_users.items()]

            restored = 0

            for token_id, data in saved_entries:
                token = data.get("token")
                if not self._is_token_valid(token):
                    continue

                with self.lock:
                    if token_id in self.active_tokens:
                        continue
                    # Do not spawn if same token is already active under another ID.
                    token_active = any(
                        str(existing.get("token") or "").strip() == str(token or "").strip()
                        for existing in self.active_tokens.values()
                    )
                    if token_active:
                        continue

                prefix = data.get("prefix", "$")
                config_file = f"hosted_{token_id}.json"
                process = self._attach_existing_process(token_id, data)
                if process is None:
                    process = self._run_their_bot(
                        config_file,
                        token,
                        prefix=prefix,
                        hosted_uid=data.get("uid") or token_id,
                        owner_id=data.get("owner"),
                        user_id=data.get("user_id"),
                        username=data.get("username"),
                    )
                if not process:
                    continue

                entry = {
                    "uid": data.get("uid") or token_id,
                    "user_id": data.get("user_id", ""),
                    "username": data.get("username", ""),
                    "token": token,
                    "prefix": prefix,
                    "owner": data.get("owner", ""),
                    "config": config_file,
                    "connected_at": data.get("connected_at") or int(time.time()),
                    "pid": process.pid,
                }

                with self.lock:
                    self.active_tokens[token_id] = entry
                    self.processes[token_id] = process
                    saved = self.saved_users.get(token_id)
                    if saved is not None:
                        saved["pid"] = process.pid
                        self._save_users()

                self._start_keepalive(token_id)
                restored += 1

            if restored:
                pass  # restore count suppressed

            return restored
        finally:
            with self._restore_lock:
                self._restore_in_progress = False
    
    def _cleanup(self, runner_file, config_file, process):
        process.wait()
        try:
            if os.path.exists(runner_file):
                os.remove(runner_file)
            if os.path.exists(config_file):
                os.remove(config_file)
        except:
            pass
    
    def cleanup(self):
        with self.lock:
            for token_id in list(self.active_tokens.keys()):
                stop_event = self._stop_events.pop(token_id, None)
                if stop_event:
                    stop_event.set()
                if token_id in self.processes:
                    self._terminate_process(self.processes[token_id])
                    self.processes.pop(token_id, None)
                del self.active_tokens[token_id]

    def _remove_invalid_users(self):
        """Remove users with invalid tokens from the hosted list."""
        with self.lock:
            invalid_users = [tid for tid, data in self.saved_users.items() if not self._is_token_valid(data.get("token"))]
            for tid in invalid_users:
                del self.saved_users[tid]
            self._save_users()

    def _is_token_valid(self, token):
        """Check if a token is valid."""
        return token and len(token) > 10  # Example validation logic

    def rehost_user(self, user_id, username, uid):
        """Re-add a user to the hosted list if rehosted."""
        with self.lock:
            if user_id not in self.saved_users:
                self.saved_users[user_id] = {
                    "username": username,
                    "uid": uid,
                    "owner": user_id
                }
                self._save_users()

host_manager = HostManager()
