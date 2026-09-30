import hashlib
import tempfile
import unittest
from pathlib import Path

from flask import Flask

from message_logger import MessageLogger
from rpc_profiles import RPCProfileStore
from webpanel import WebPanel, _PANEL_MASTER_ID


class FakeBot:
    def __init__(self, directory):
        self.activity = {"type": 0, "name": "Initial"}
        self.message_logger = MessageLogger(str(Path(directory) / "logger.json"))
        self._rpc_rotation_state = {"running": False}
        self.connection_active = True
        self.identified = False
        self.gateway_latency_ms = 42
        self._consecutive_failures = 2
        self._connection_quality_score = 75
        self._network_stability_score = 80
        self.rotation_stopped = False
        self._rpc_apply_activity = self.apply_activity
        self._rpc_apply_preset = self.apply_preset
        self._rpc_start_rotation = self.start_rotation
        self._rpc_stop_rotation = self.stop_rotation

    def apply_activity(self, bot, activity, mode="dashboard"):
        self.activity = activity
        return True, activity

    def apply_preset(self, bot, name):
        activity = panel._rpc_profile_store.get_preset(name)
        if not activity:
            return False, "RPC preset was not found"
        self.activity = activity
        return True, activity

    def start_rotation(self, bot):
        self._rpc_rotation_state["running"] = True
        return True, "started"

    def stop_rotation(self, bot, resume_keepalive=False):
        self.rotation_stopped = True
        self._rpc_rotation_state["running"] = False
        return True

    def get_connection_diagnostics(self):
        return {
            "gateway_latency_ms": self.gateway_latency_ms,
            "consecutive_failures": self._consecutive_failures,
            "connection_quality": self._connection_quality_score,
            "network_stability": self._network_stability_score,
        }


class WebPanelControlTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        global panel
        panel = object.__new__(WebPanel)
        panel.app = Flask("aria-webpanel-control-test")
        panel.app.secret_key = "test-session-secret"
        panel._base_dir = self.temp_dir.name
        panel._start_time = 0
        panel.instance_id = "test"
        panel.owner_id = "test-owner"
        panel.bot = FakeBot(self.temp_dir.name)
        panel._rpc_profile_store = RPCProfileStore(str(Path(self.temp_dir.name) / "rpc.json"))
        self.authenticated = False
        panel._require_session = lambda: self.authenticated
        panel._setup_routes()
        self.client = panel.app.test_client()
        with self.client.session_transaction() as active_session:
            active_session["_csrf_token"] = "test-csrf-token"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_rpc_and_logger_mutations_require_authentication(self):
        self.assertEqual(self.client.get("/api/rpc").status_code, 403)
        self.assertEqual(self.client.post("/api/rpc", json={"activity": {"name": "No"}}).status_code, 403)
        self.assertEqual(self.client.get("/api/rpc/profiles").status_code, 403)
        self.assertEqual(self.client.get("/api/message-logger").status_code, 403)
        self.assertEqual(self.client.get("/api/config").status_code, 403)
        self.assertEqual(self.client.post("/api/client", json={"client_type": "vr"}).status_code, 403)
        self.assertEqual(self.client.post("/api/presence", json={"status": "online"}).status_code, 403)

    def test_rpc_set_uses_live_activity_callback(self):
        self.authenticated = True
        activity = {"type": 0, "name": "Preview matches payload"}
        response = self.client.post("/api/rpc", json={"action": "set", "activity": activity})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json["ok"])
        self.assertEqual(panel.bot.activity["name"], activity["name"])

    def test_overview_uses_ready_state_and_returns_gateway_health(self):
        data = panel._bot_data()
        self.assertFalse(data["connected"])
        self.assertFalse(data["identified"])
        self.assertEqual(data["gateway_latency_ms"], 42)
        self.assertEqual(data["reconnect_attempts"], 2)

        panel.bot.identified = True
        self.assertTrue(panel._bot_data()["connected"])

    def test_owner_summary_is_limited_to_master_owners(self):
        panel._load_dashboard_users = lambda: {
            "owner": {"role": "admin"},
            "member": {"role": "user"},
        }
        panel._load_access_requests = lambda: [{"status": "pending"}, {"status": "approved"}]
        panel._bot_data = lambda: {
            "connected": True,
            "gateway_latency_ms": 42,
            "username": "Aria",
            "user_id": "bot-id",
        }

        self.assertEqual(self.client.get("/api/owner/summary").status_code, 403)
        with self.client.session_transaction() as active_session:
            active_session["user_id"] = "delegated-admin"
        self.assertEqual(self.client.get("/api/owner/summary").status_code, 403)

        with self.client.session_transaction() as active_session:
            active_session["user_id"] = _PANEL_MASTER_ID
        response = self.client.get("/api/owner/summary")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["data"]["total_accounts"], 2)
        self.assertEqual(response.json["data"]["admin_accounts"], 1)
        self.assertEqual(response.json["data"]["pending_requests"], 1)

    def test_owner_summary_lists_names_and_reset_requests_without_passwords(self):
        panel._load_dashboard_users = lambda: {
            "account-secret-id": {"username": "aria-user", "role": "user", "password_hash": "must-not-leak"},
        }
        panel._load_access_requests = lambda: [{
            "id": "reset-request-id",
            "type": "password_reset",
            "user_id": "account-secret-id",
            "reason": "Lost access",
            "status": "pending",
        }]
        panel._bot_data = lambda: {}
        with self.client.session_transaction() as active_session:
            active_session["user_id"] = _PANEL_MASTER_ID

        response = self.client.get("/api/owner/summary")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["data"]["accounts"][0]["username"], "aria-user")
        self.assertNotIn("account-secret-id", str(response.json["data"]["accounts"]))
        self.assertNotIn("password_hash", str(response.json["data"]))
        self.assertEqual(response.json["data"]["password_reset_requests"][0]["username"], "aria-user")

    def test_password_reset_approval_is_owner_only_and_rotates_once(self):
        users = {"target-id": {"username": "aria-user", "password_hash": "old-hash"}}
        requests = [{"id": "reset-1", "type": "password_reset", "user_id": "target-id", "status": "pending"}]
        panel._require_admin = lambda: True
        panel._load_dashboard_users = lambda: dict(users)
        panel._save_dashboard_users = lambda updated: (users.clear(), users.update(updated))
        panel._load_access_requests = lambda: requests
        panel._save_access_requests = lambda updated: requests.__setitem__(slice(None), updated)
        panel._record_user_activity = lambda *args: None

        with self.client.session_transaction() as active_session:
            active_session["user_id"] = "delegated-admin"
        csrf_headers = {"X-CSRF-Token": "test-csrf-token"}
        denied = self.client.post("/api/dash/requests/reset-1/approve", json={}, headers=csrf_headers)
        self.assertEqual(denied.status_code, 403)

        with self.client.session_transaction() as active_session:
            active_session["user_id"] = _PANEL_MASTER_ID
        missing_csrf = self.client.post("/api/dash/requests/reset-1/approve", json={})
        self.assertEqual(missing_csrf.status_code, 403)
        approved = self.client.post("/api/dash/requests/reset-1/approve", json={}, headers=csrf_headers)

        self.assertEqual(approved.status_code, 200)
        temporary_password = approved.json["password"]
        self.assertTrue(panel._password_matches(temporary_password, users["target-id"]["password_hash"]))
        self.assertNotEqual(users["target-id"]["password_hash"], temporary_password)
        self.assertEqual(approved.json["password_delivery"], "show_once")
        self.assertEqual(self.client.post("/api/dash/requests/reset-1/approve", json={}, headers=csrf_headers).status_code, 409)

    def test_signup_then_username_login_redirects_to_instance_setup(self):
        users = {}
        panel._load_dashboard_users = lambda: dict(users)
        panel._save_dashboard_users = lambda updated: (users.clear(), users.update(updated))
        panel._configured_admin_ids = lambda: set()
        panel._mark_login_success = lambda *args: None
        panel._get_primary_user_instance = lambda user_id: None

        signup_response = self.client.post("/signup", data={
            "csrf_token": "test-csrf-token",
            "username": "aria-user",
            "password": "a strong passphrase",
            "confirm_password": "a strong passphrase",
            "accept_policy": "on",
        })

        self.assertEqual(signup_response.status_code, 302)
        self.assertEqual(signup_response.headers["Location"], "/login?created=1")
        self.assertEqual(len(users), 1)
        user_id, account = next(iter(users.items()))
        self.assertEqual(account["username"], "aria-user")
        self.assertEqual(account["role"], "user")
        self.assertEqual(account["instance_id"], panel.instance_id)
        self.assertNotEqual(account["password_hash"], "a strong passphrase")
        self.assertTrue(panel._password_matches("a strong passphrase", account["password_hash"]))

        login_response = self.client.post("/login", data={
            "csrf_token": "test-csrf-token",
            "username": "ARIA-USER",
            "password": "a strong passphrase",
            "next": "/dashboard",
        })

        self.assertEqual(login_response.status_code, 302)
        self.assertEqual(login_response.headers["Location"], "/connect-instance")
        with self.client.session_transaction() as active_session:
            self.assertEqual(active_session["user_id"], user_id)

    def test_signup_rejects_missing_csrf_without_creating_account(self):
        users = {}
        panel._load_dashboard_users = lambda: dict(users)
        panel._save_dashboard_users = lambda updated: (users.clear(), users.update(updated))

        response = self.client.post("/signup", data={
            "username": "aria-user",
            "password": "a strong passphrase",
            "confirm_password": "a strong passphrase",
            "accept_policy": "on",
        })

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/signup?error=invalid_form")
        self.assertEqual(users, {})

    def test_signup_features_and_legacy_access_routes(self):
        panel._read_raw_template = lambda name: f"template:{name}"

        signup_page = self.client.get("/signup")
        features_page = self.client.get("/features")
        legacy_request = self.client.get("/request-access")

        self.assertEqual(signup_page.status_code, 200)
        self.assertIn("template:signup_template.html", signup_page.get_data(as_text=True))
        self.assertEqual(features_page.status_code, 200)
        self.assertIn("template:features_template.html", features_page.get_data(as_text=True))
        self.assertEqual(legacy_request.status_code, 302)
        self.assertEqual(legacy_request.headers["Location"], "/signup")

    def test_public_activity_returns_only_safe_event_labels(self):
        panel._read_log_tail = lambda count: [
            "[CMD #1] [12:34:56] .secret-command | user=private-user | guild=private-guild | 4ms",
            "[NITRO] recovered token=private-token",
        ]

        response = self.client.get("/api/public/activity")
        serialized = str(response.json)

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["kind"] for item in response.json["events"]], ["WATCHER", "COMMAND"])
        self.assertNotIn("secret-command", serialized)
        self.assertNotIn("private-user", serialized)
        self.assertNotIn("private-guild", serialized)
        self.assertNotIn("private-token", serialized)

    def test_authenticated_login_rejects_protocol_relative_next_url(self):
        self.authenticated = True

        response = self.client.get("/login?next=//example.invalid")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/dashboard")

    def test_instance_link_rejects_missing_csrf_before_reading_token(self):
        self.authenticated = True
        panel._require_admin = lambda: False

        response = self.client.post("/connect-instance", data={"token": "must-not-be-processed"})

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/connect-instance?error=Session+expired")

    def test_password_reset_request_resolves_username_to_internal_user_id(self):
        requests = []
        panel._load_dashboard_users = lambda: {
            "internal-account-id": {"username": "aria-user"},
        }
        panel._load_access_requests = lambda: list(requests)
        panel._save_access_requests = lambda updated: requests.extend(updated)

        response = self.client.post("/reset-password", data={"csrf_token": "test-csrf-token", "username": "ARIA-USER"})

        self.assertEqual(response.status_code, 302)
        self.assertEqual(requests[0]["user_id"], "internal-account-id")

    def test_legacy_user_id_login_is_upgraded_to_salted_hash(self):
        users = {
            "legacy-id": {
                "username": "legacy-user",
                "password_hash": hashlib.sha256(b"legacy password").hexdigest(),
                "instance_id": panel.instance_id,
                "role": "user",
            }
        }
        panel._load_dashboard_users = lambda: dict(users)
        panel._save_dashboard_users = lambda updated: (users.clear(), users.update(updated))
        panel._configured_admin_ids = lambda: set()
        panel._mark_login_success = lambda *args: None
        panel._get_primary_user_instance = lambda user_id: None

        response = self.client.post("/login", data={"csrf_token": "test-csrf-token", "username": "legacy-id", "password": "legacy password"})

        self.assertEqual(response.headers["Location"], "/connect-instance")
        self.assertTrue(users["legacy-id"]["password_hash"].startswith(("pbkdf2:", "scrypt:")))
        self.assertTrue(panel._password_matches("legacy password", users["legacy-id"]["password_hash"]))

    def test_boost_api_keeps_counts_but_hides_server_identifiers(self):
        self.authenticated = True
        panel._boost_data = lambda: {
            "server_boosts": {"private-server-id": 2},
            "rotation_servers": ["private-server-id"],
            "live": {"boosted_servers": 1, "total_boosts": 2},
        }

        response = self.client.get("/api/boost")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["data"]["live"]["boosted_servers"], 1)
        self.assertNotIn("server_boosts", response.json["data"])
        self.assertNotIn("rotation_servers", response.json["data"])

    def test_command_catalog_reports_aliases_under_canonical_ping(self):
        command = type("Command", (), {"name": "ping", "aliases": ["ms", "latency", "lat"]})()
        panel.bot.commands = {name: command for name in ("ping", "ms", "latency", "lat")}
        panel._history_data = lambda: {"entries": []}

        result = panel._commands_data()["commands"]
        ping_rows = [row for row in result if row["name"] == "ping"]
        alias_rows = [row for row in result if row["name"] in {"ms", "latency", "lat"}]
        self.assertEqual(len(ping_rows), 1)
        self.assertEqual(ping_rows[0]["aliases"], ["lat", "latency", "ms"])
        self.assertEqual(alias_rows, [])

    def test_command_usage_removes_the_configured_prefix(self):
        command = type("Command", (), {"name": "ping", "aliases": []})()
        panel.bot.prefix = "+"
        panel.bot.commands = {"ping": command}
        panel._history_data = lambda: {"entries": [{"command": "+ping"}]}

        result = panel._commands_data()["commands"]

        self.assertEqual(result[0]["name"], "ping")
        self.assertEqual(result[0]["recent_usage"], 1)

    def test_command_log_parser_keeps_failed_commands_in_history(self):
        parsed = panel._parse_structured_logs([
            "[ERROR] [12:34:56] .ping | user=123 | 41ms | temporary failure"
        ])

        event = parsed["events"]["commands"][0]
        self.assertEqual(event["command"], ".ping")
        self.assertEqual(event["user"], "123")
        self.assertEqual(event["duration_ms"], 41.0)
        self.assertEqual(event["status"], "failed")

    def test_presets_rotation_and_logger_routes(self):
        self.authenticated = True
        self.assertTrue(self.client.post("/api/rpc/profiles/preset", json={"action": "save", "name": "Desk"}).json["ok"])
        panel.bot.activity = {"type": 3, "name": "Reading"}
        self.assertTrue(self.client.post("/api/rpc/profiles/preset", json={"action": "save", "name": "Away"}).json["ok"])
        self.assertTrue(self.client.post("/api/rpc/profiles/preset", json={"action": "load", "name": "Desk"}).json["ok"])
        self.assertEqual(self.client.post("/api/rpc/profiles/rotation", json={"action": "set", "presets": ["Desk", "Desk"], "interval": 30}).status_code, 400)
        self.assertTrue(self.client.post("/api/rpc/profiles/rotation", json={"action": "set", "presets": ["Desk", "Away"], "interval": 30}).json["ok"])
        self.assertTrue(self.client.post("/api/rpc/profiles/rotation", json={"action": "start"}).json["ok"])
        self.assertTrue(self.client.post("/api/rpc/profiles/preset", json={"action": "delete", "name": "Desk"}).json["ok"])
        self.assertTrue(panel.bot.rotation_stopped)

        self.assertTrue(self.client.post("/api/message-logger", json={"action": "config", "config": {"enabled": True}}).json["config"]["enabled"])
        self.assertEqual(self.client.post("/api/message-logger", json={"action": "keyword_add", "keyword": "aria"}).json["config"]["keywords"], ["aria"])


if __name__ == "__main__":
    unittest.main()