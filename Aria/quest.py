import time
import random
import threading
from datetime import datetime, timezone

QUESTS_BASE = "https://discord.com/api/v9"


class QuestSystem:
    def __init__(self, api_client):
        self.api = api_client
        self.quests = {}          # quest_id (str) -> raw quest dict from API
        self.excluded = set()     # quest_ids to skip
        self.auto_complete = False
        self._task_thread = None
        self.last_fetch = 0
        self.refresh_interval = 5 * 60  # 5 minutes for quicker real-time pickup

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _headers(self):
        return self.api.header_spoofer.get_protected_headers(self.api.token)

    def _expired(self, iso) -> bool:
        if not iso:
            return False
        try:
            return datetime.now(timezone.utc) > datetime.fromisoformat(
                str(iso).replace("Z", "+00:00")
            )
        except Exception:
            return False

    def _tasks_map(self, q: dict) -> dict:
        config = q.get("config", {}) or {}
        # Discord may return snake_case or camelCase for task config keys.
        for key in ("task_config_v2", "taskConfigV2", "task_config", "taskConfig"):
            tc = config.get(key, {})
            if not isinstance(tc, dict):
                continue

            tasks = tc.get("tasks", {})
            if isinstance(tasks, dict) and tasks:
                return tasks

            # Some payloads store tasks directly at this level.
            looks_like_tasks = False
            for _, tv in tc.items():
                if isinstance(tv, dict) and (
                    "event_name" in tv
                    or "eventName" in tv
                    or "target" in tv
                ):
                    looks_like_tasks = True
                    break
            if looks_like_tasks:
                return tc
        return {}

    def _task_names(self, q: dict) -> list:
        """Collect all task/event identifiers in normalized lowercase form."""
        tasks = self._tasks_map(q)
        names = [str(k).lower() for k in tasks.keys()]
        for _, tv in tasks.items():
            if not isinstance(tv, dict):
                continue
            ev = str(tv.get("event_name") or tv.get("eventName") or "").lower().strip()
            if ev:
                names.append(ev)
        return names

    def _task_platforms(self, q: dict) -> set:
        """Infer target platforms from task names/events."""
        names = self._task_names(q)
        platforms = set()
        for n in names:
            if any(x in n for x in ("desktop", "pc", "windows", "mac", "linux")):
                platforms.add("desktop")
            if "mobile" in n:
                platforms.add("mobile")
            if "xbox" in n:
                platforms.add("xbox")
            if "playstation" in n or "ps5" in n or "ps4" in n:
                platforms.add("playstation")
            if "switch" in n or "nintendo" in n:
                platforms.add("switch")
        return platforms

    def _task_type(self, q: dict) -> str:
        names = self._task_names(q)
        if any(("watch" in n) or ("video" in n) for n in names):
            return "watch"
        if any(("play" in n) or ("gaming" in n) for n in names):
            return "play"
        if any("stream" in n for n in names):
            return "stream"
        return "unknown"

    def _quest_name(self, q: dict) -> str:
        config = q.get("config", {}) or {}
        msgs = config.get("messages", {}) or {}
        app = (config.get("application", {}) or {}).get("name", "Unknown")
        if self._task_type(q) == "watch":
            vm = config.get("video_metadata", {}) or {}
            title = (vm.get("messages", {}) or {}).get("video_title")
            if title:
                return title
        return msgs.get("quest_name") or msgs.get("game_title") or f"Quest by {app}"

    def _get_progress(self, q: dict):
        """Returns (event_name, done, total)."""
        tasks = self._tasks_map(q)
        progress = (q.get("user_status") or {}).get("progress") or {}
        done = 0
        event_name = None

        if isinstance(progress, dict):
            for _, val in progress.items():
                if not isinstance(val, dict):
                    continue
                v = int(float(val.get("value", 0) or 0))
                if v >= done:
                    done = v
                    event_name = val.get("event_name")

        total = 100
        if event_name:
            for _, task in tasks.items():
                if isinstance(task, dict) and task.get("event_name") == event_name:
                    total = int(float(task.get("target", 100) or 100))
                    break
        elif tasks:
            smallest = None
            for _, task in tasks.items():
                if isinstance(task, dict):
                    target = int(float(task.get("target", 100) or 100))
                    if smallest is None or target < smallest:
                        smallest = target
                        event_name = task.get("event_name") or event_name
            total = smallest if smallest is not None else 100

        return str(event_name or "Unknown"), max(0, done), max(1, total)

    def _is_enrollable(self, q: dict) -> bool:
        config = q.get("config", {}) or {}
        return not q.get("user_status") and not self._expired(config.get("expires_at"))

    def _is_completeable(self, q: dict) -> bool:
        config = q.get("config", {}) or {}
        status = q.get("user_status") or {}
        return bool(
            status
            and status.get("enrolled_at")
            and not status.get("completed_at")
            and not self._expired(config.get("expires_at"))
        )

    def _is_claimable(self, q: dict) -> bool:
        config = q.get("config", {}) or {}
        rewards_cfg = config.get("rewards_config", {}) or {}
        status = q.get("user_status") or {}
        return bool(
            status
            and status.get("completed_at")
            and not status.get("claimed_at")
            and not self._expired(config.get("expires_at"))
            and rewards_cfg.get("rewards_expire_at")
            and not self._expired(rewards_cfg.get("rewards_expire_at"))
        )

    def _is_worthy(self, q: dict) -> bool:
        config = q.get("config", {}) or {}
        if self._expired(config.get("expires_at")):
            return False
        rewards = (config.get("rewards_config", {}) or {}).get("rewards", []) or []
        return any(isinstance(r, dict) and r.get("type") in (3, 4) for r in rewards)

    def _reward_names(self, q: dict) -> list:
        rewards = ((q.get("config", {}) or {}).get("rewards_config", {}) or {}).get("rewards", []) or []
        names = []
        for r in rewards:
            if not isinstance(r, dict):
                continue
            label = ((r.get("messages", {}) or {}).get("name_with_article") or "").strip()
            if label:
                names.append(label.title())
        return names

    def _is_user_quest(self, q: dict) -> bool:
        """Identify if quest is explicitly user-made; avoid aggressive filtering."""
        config = q.get("config", {}) or {}
        grant_type = str(config.get("grant_type") or config.get("grantType") or "").upper()
        if grant_type == "USER_MADE":
            return True
        if bool(config.get("user_created") or config.get("userCreated")):
            return True
        return False

    # ------------------------------------------------------------------
    # API calls
    # ------------------------------------------------------------------

    def fetch_quests(self):
        """Fetch and cache quests, excluding user-owned quests. Returns (success, message)."""
        try:
            resp = self.api.request("GET", "/quests/@me")
            if not resp or resp.status_code != 200:
                return False, f"HTTP {resp.status_code if resp else 'No response'}"

            data = resp.json()
            blocked_until = None
            if isinstance(data, dict):
                blocked_until = data.get("quest_enrollment_blocked_until") or data.get("questEnrollmentBlockedUntil")
            if blocked_until:
                return False, f"Blocked until {blocked_until}"

            raw = []
            if isinstance(data, dict):
                raw = data.get("quests", []) or []
                for eq in (data.get("excluded_quests", []) or data.get("excludedQuests", []) or []):
                    eid = eq.get("id")
                    if eid:
                        self.excluded.add(str(eid))
            elif isinstance(data, list):
                raw = data

            self.quests = {}
            user_quests_skipped = 0
            
            for qd in raw:
                if not isinstance(qd, dict):
                    continue
                
                qid = str(qd.get("id", ""))
                if not qid or qid in self.excluded:
                    continue
                
                # Skip user-owned quests
                if self._is_user_quest(qd):
                    user_quests_skipped += 1
                    self.excluded.add(qid)
                    continue
                
                self.quests[qid] = qd

            self.last_fetch = time.time()
            msg = f"Fetched {len(self.quests)} quests"
            if user_quests_skipped > 0:
                msg += f" (skipped {user_quests_skipped} user-owned quests)"
            return True, msg
        except Exception as e:
            return False, str(e)

    def enroll(self, q: dict):
        """Enroll in a single quest. Returns updated user_status dict or None."""
        if not self._is_enrollable(q):
            return None
        qid = q.get("id")
        try:
            resp = self.api.request(
                "POST",
                f"/quests/{qid}/enroll",
                data={"is_targeted": False, "location": 11, "metadata_raw": None},
            )
            if resp and resp.status_code in (200, 201):
                body = resp.json() if resp.content else {}
                if isinstance(body, dict):
                    return body
                return q.get("user_status") or {}
            if resp and resp.status_code == 204:
                return q.get("user_status") or {"enrolled_at": datetime.now(timezone.utc).isoformat()}
        except Exception:
            pass
        return None

    def claim(self, q: dict) -> bool:
        qid = str(q.get("id", ""))
        if not qid or not self._is_claimable(q):
            return False
        endpoints = (
            f"/quests/{qid}/claim-reward",
            f"/quests/{qid}/claim_reward",
            f"/quests/{qid}/claim",
        )
        for ep in endpoints:
            try:
                resp = self.api.request("POST", ep, data={})
                if resp and resp.status_code in (200, 201, 204):
                    us = q.get("user_status") or {}
                    us["claimed_at"] = datetime.now(timezone.utc).isoformat()
                    q["user_status"] = us
                    return True
            except Exception:
                continue
        return False

    def _send_progress(self, q: dict):
        """Send one progress tick. Returns (success, completed, done, total)."""
        qid = str(q.get("id", ""))
        qtype = self._task_type(q)
        platforms = self._task_platforms(q)
        _, done, total = self._get_progress(q)

        try:
            if qtype == "watch":
                enrolled_raw = (q.get("user_status") or {}).get("enrolled_at")
                try:
                    enrolled_ts = datetime.fromisoformat(
                        str(enrolled_raw).replace("Z", "+00:00")
                    ).timestamp()
                except Exception:
                    enrolled_ts = datetime.now(timezone.utc).timestamp()

                max_allowed = int(datetime.now(timezone.utc).timestamp() - enrolled_ts) + 10
                speed = 7
                if max_allowed - done < speed:
                    return True, False, done, total

                new_val = min(done + speed + random.random(), max_allowed)
                resp = None
                watch_endpoints = (
                    f"/quests/{qid}/video-progress",
                    f"/quests/{qid}/video_progress",
                )
                watch_payloads = (
                    {"timestamp": new_val},
                    {"value": new_val},
                    {"seconds": new_val},
                )
                for ep in watch_endpoints:
                    for payload in watch_payloads:
                        resp = self.api.request("POST", ep, data=payload)
                        if resp and resp.status_code in (200, 204):
                            break
                    if resp and resp.status_code in (200, 204):
                        break
            elif qtype in ("play", "stream"):
                app_id = str(((q.get("config") or {}).get("application") or {}).get("id") or "")
                resp = None
                hb_endpoints = (
                    f"/quests/{qid}/heartbeat",
                    f"/quests/{qid}/heartbeats",
                )

                base_payload = {}
                if app_id:
                    base_payload["application_id"] = app_id

                # Try desktop-first for PC quests, then broad fallbacks for other platforms.
                terminal_candidates = [False, True]
                if "desktop" in platforms:
                    terminal_candidates = [True, False]

                platform_candidates = [None]
                if platforms:
                    platform_candidates = list(platforms) + [None]

                for ep in hb_endpoints:
                    for term in terminal_candidates:
                        for plat in platform_candidates:
                            hb_payload = dict(base_payload)
                            hb_payload["terminal"] = term
                            if plat:
                                hb_payload["platform"] = plat
                            resp = self.api.request("POST", ep, data=hb_payload)
                            if resp and resp.status_code in (200, 204):
                                break
                        if resp and resp.status_code in (200, 204):
                            break
                    if resp and resp.status_code in (200, 204):
                        break
            else:
                return False, False, done, total

            if not resp or resp.status_code not in (200, 204):
                if resp and resp.status_code in (401, 404):
                    self.excluded.add(qid)
                return False, False, done, total

            if resp.status_code == 204:
                return True, False, done, total

            rdata = resp.json() if resp.content else {}
            if not isinstance(rdata, dict):
                rdata = {}

            # Completed?
            if rdata.get("completed_at"):
                us = q.get("user_status") or {}
                us["completed_at"] = rdata["completed_at"]
                q["user_status"] = us
                return True, True, total, total

            # Parse updated progress
            prog = rdata.get("progress") or rdata.get("user_status", {}).get("progress") or {}
            for _, pv in prog.items():
                if isinstance(pv, dict):
                    try:
                        v = int(float(pv.get("value", done)))
                        if v > done:
                            done = v
                    except Exception:
                        pass
            sps = rdata.get("streamProgressSeconds")
            if sps is not None:
                try:
                    done = max(done, int(float(sps)))
                except Exception:
                    pass

            return True, False, done, total
        except Exception:
            return False, False, done, total

    # ------------------------------------------------------------------
    # Background runner
    # ------------------------------------------------------------------

    def _run_auto_complete(self):
        # Auto-enroll first
        for q in list(self.quests.values()):
            if not self.auto_complete:
                return
            if self._is_enrollable(q):
                status = self.enroll(q)
                if status:
                    q["user_status"] = status
                time.sleep(0.8)

        while self.auto_complete:
            try:
                if time.time() - self.last_fetch > self.refresh_interval:
                    self.fetch_quests()

                to_process = [
                    q for q in self.quests.values()
                    if self._is_completeable(q) and str(q.get("id", "")) not in self.excluded
                ]
                to_process.sort(key=lambda q: 0 if self._is_worthy(q) else 1)

                for q in to_process:
                    if not self.auto_complete:
                        break
                    self._send_progress(q)

                for q in list(self.quests.values()):
                    if not self.auto_complete:
                        break
                    if self._is_claimable(q):
                        self.claim(q)
                        time.sleep(0.6)

                time.sleep(random.randint(45, 60))
            except Exception:
                time.sleep(30)

    def start(self):
        if self.auto_complete:
            return False, "Already running"
        self.auto_complete = True
        # Fresh fetch so enroll loop has quests to work with immediately
        if not self.quests:
            self.fetch_quests()
        self._task_thread = threading.Thread(target=self._run_auto_complete, daemon=True)
        self._task_thread.start()
        return True, "Started"

    def stop(self):
        if not self.auto_complete:
            return False, "Not running"
        self.auto_complete = False
        self._task_thread = None
        return True, "Stopped"

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def get_summary(self):
        enrollable, completeable, claimable, completed, expired = [], [], [], [], []
        for q in self.quests.values():
            config = q.get("config", {}) or {}
            if self._expired(config.get("expires_at")):
                expired.append(q)
            elif self._is_claimable(q):
                claimable.append(q)
            elif self._is_completeable(q):
                completeable.append(q)
            elif self._is_enrollable(q):
                enrollable.append(q)
            else:
                completed.append(q)
        return {
            "running": self.auto_complete,
            "total": len(self.quests),
            "enrollable": enrollable,
            "completeable": completeable,
            "claimable": claimable,
            "completed": completed,
            "expired": expired,
            "last_fetch": self.last_fetch,
        }
