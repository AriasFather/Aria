import hashlib
import json
import threading
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from flask import Flask

from message_logger import MessageLogger
from rpc_profiles import RPCProfileStore
from hosted_command_registry import write_command_registry
from hosted_rpc_bridge import dispatch_hosted_rpc, start_hosted_rpc_worker
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
        with self.client.session_transaction() as active_session:
            active_session["user_id"] = _PANEL_MASTER_ID
        activity = {"type": 0, "name": "Preview matches payload"}
        response = self.client.post("/api/rpc", json={"action": "set", "activity": activity})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json["ok"])
        self.assertEqual(panel.bot.activity["name"], activity["name"])

    def test_hosted_rpc_uses_child_and_instance_specific_profile_store(self):
        self.authenticated = True
        instance_dir = Path(self.temp_dir.name) / "hosted_bot_client-123"
        control_dir = Path(self.temp_dir.name) / "hosted_runtime" / "client-123"
        instance_dir.mkdir()
        target = {
            "token_id": "client-123",
            "instance_dir": str(instance_dir),
            "control_dir": str(control_dir),
            "active": True,
        }
        panel._current_hosted_rpc_target = lambda: target
        current_activity = {"type": 0, "name": "Hosted profile", "application_id": "app-12"}
        (instance_dir / "runtime_state.json").write_text(
            json.dumps({"rpc": {"activity": current_activity, "mode": "saved", "saved_at": 42}}),
            encoding="utf-8",
        )
        hosted_profile_path = instance_dir / "rpc_profiles.json"
        dispatch_result = {"ok": True, "activity": current_activity}

        with patch("hosted_rpc_bridge.dispatch_hosted_rpc", return_value=dispatch_result) as dispatch:
            rpc_state = self.client.get("/api/rpc")
            set_response = self.client.post("/api/rpc", json={"activity": current_activity})
            save_response = self.client.post("/api/rpc/profiles/preset", json={"action": "save", "name": "Hosted"})
            second_save_response = self.client.post("/api/rpc/profiles/preset", json={"action": "save", "name": "Hosted backup"})
            rotation_set = self.client.post("/api/rpc/profiles/rotation", json={"action": "set", "presets": ["Hosted", "Hosted backup"], "interval": 30})
            rotation_start = self.client.post("/api/rpc/profiles/rotation", json={"action": "start"})
            rotation_stop = self.client.post("/api/rpc/profiles/rotation", json={"action": "stop"})
            profiles_response = self.client.get("/api/rpc/profiles")

        self.assertEqual(rpc_state.json["activity"]["name"], "Hosted profile")
        self.assertTrue(set_response.json["ok"])
        self.assertEqual(save_response.status_code, 200)
        self.assertEqual(second_save_response.status_code, 200)
        self.assertTrue(rotation_set.json["ok"])
        self.assertTrue(rotation_start.json["ok"])
        self.assertTrue(rotation_stop.json["ok"])
        self.assertEqual(profiles_response.json["presets"], ["Hosted", "Hosted backup"])
        self.assertEqual(panel.bot.activity["name"], "Initial")
        self.assertEqual(panel._rpc_profile_store.list_presets(), {})
        self.assertTrue(hosted_profile_path.exists())
        dispatch.assert_any_call(str(control_dir), "set", current_activity)
        dispatch.assert_any_call(str(control_dir), "rotation_start", None)
        dispatch.assert_any_call(str(control_dir), "rotation_stop", None)

    def test_overview_uses_ready_state_and_returns_gateway_health(self):
        data = panel._bot_data()
        self.assertFalse(data["connected"])
        self.assertFalse(data["identified"])
        self.assertEqual(data["gateway_latency_ms"], 42)
        self.assertEqual(data["reconnect_attempts"], 2)

        panel.bot.identified = True
        self.assertTrue(panel._bot_data()["connected"])

    def test_public_stats_count_only_live_hosted_processes(self):
        panel._load_dashboard_users = lambda: {"registered": {}}
        live_process = Mock()
        live_process.poll.return_value = None
        stopped_process = Mock()
        stopped_process.poll.return_value = 1
        manager = SimpleNamespace(
            lock=threading.RLock(),
            saved_users={"live": {}, "stopped": {}},
            active_tokens={"live": {}, "stopped": {}},
            processes={"live": live_process, "stopped": stopped_process},
        )
        status_path = Path(self.temp_dir.name) / "hosted_runtime" / "live" / "rpc_status.json"
        status_path.parent.mkdir(parents=True)
        status_path.write_text(json.dumps({"connected": True, "identified": True, "updated_at": int(time.time())}), encoding="utf-8")
        self.assertTrue(panel._hosted_gateway_status("live")["connected"])

        with patch("host.host_manager", manager):
            response = self.client.get("/api/public/stats")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["stats"]["total_hosted"], 2)
        self.assertEqual(response.json["stats"]["connected_count"], 1)
        self.assertEqual(response.json["stats"]["total_registered"], 1)

    def test_public_stats_are_zero_without_registered_or_running_users(self):
        panel._load_dashboard_users = lambda: {}
        manager = SimpleNamespace(
            lock=threading.RLock(),
            saved_users={},
            active_tokens={},
            processes={},
        )

        with patch("host.host_manager", manager):
            response = self.client.get("/api/public/stats")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["stats"]["total_hosted"], 0)
        self.assertEqual(response.json["stats"]["connected_count"], 0)
        self.assertEqual(response.json["stats"]["total_registered"], 0)

    def test_hosted_list_limits_delegated_admins_to_owned_instances(self):
        self.authenticated = True
        panel._require_admin = lambda: True
        panel._is_owner_session = lambda: False
        with self.client.session_transaction() as active_session:
            active_session["user_id"] = "delegated-admin"
        manager = SimpleNamespace(
            lock=threading.RLock(),
            saved_users={
                "owned-token": {"owner": "delegated-admin", "username": "Mine"},
                "other-token": {"owner": "another-user", "username": "Not mine"},
            },
            active_tokens={},
        )

        with patch("host.host_manager", manager):
            response = self.client.get("/api/hosted")

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["token_ref"] for item in response.json["hosted"]], ["owned-token"])
        self.assertFalse(response.json["is_owner"])

    def test_hosted_disconnect_is_authenticated_and_owner_scoped(self):
        self.authenticated = True
        panel._require_admin = lambda: True
        panel._is_owner_session = lambda: False
        with self.client.session_transaction() as active_session:
            active_session["user_id"] = "delegated-admin"
        remove_hosts = Mock(return_value=1)
        manager = SimpleNamespace(
            lock=threading.RLock(),
            saved_users={
                "owned-token": {"owner": "delegated-admin"},
                "other-token": {"owner": "another-user"},
            },
            remove_hosts=remove_hosts,
        )

        with patch("host.host_manager", manager):
            forbidden = self.client.post("/api/hosted/disconnect", json={"token_id": "other-token"})
            self.assertEqual(forbidden.status_code, 403)
            remove_hosts.assert_not_called()

            disconnected = self.client.post("/api/hosted/disconnect", json={"token_id": "owned-token"})

        self.assertEqual(disconnected.status_code, 200)
        remove_hosts.assert_called_once_with(
            requester_id="delegated-admin",
            selectors=["owned-token"],
            all_hosts=False,
        )

    def test_hosted_disconnect_rejects_unauthenticated_requests(self):
        self.authenticated = False
        remove_hosts = Mock(return_value=1)
        manager = SimpleNamespace(remove_hosts=remove_hosts)

        with patch("host.host_manager", manager):
            response = self.client.post("/api/hosted/disconnect", json={"token_id": "owned-token"})

        self.assertEqual(response.status_code, 403)
        remove_hosts.assert_not_called()

    def test_hosted_restart_is_authenticated_and_owner_scoped(self):
        self.authenticated = True
        with self.client.session_transaction() as active_session:
            active_session["user_id"] = "delegated-admin"
        panel._is_owner_session = lambda: False
        restart_hosts = Mock(return_value=1)
        manager = SimpleNamespace(
            lock=threading.RLock(),
            saved_users={
                "owned-token": {"owner": "delegated-admin"},
                "other-token": {"owner": "another-user"},
            },
            restart_hosts=restart_hosts,
        )

        with patch("host.host_manager", manager):
            forbidden = self.client.post("/api/hosted/restart", json={"token_id": "other-token"})
            self.assertEqual(forbidden.status_code, 403)
            restart_hosts.assert_not_called()

            restarted = self.client.post("/api/hosted/restart", json={"token_id": "owned-token"})

        self.assertEqual(restarted.status_code, 200)
        restart_hosts.assert_called_once_with(
            requester_id="delegated-admin",
            selectors=["owned-token"],
            all_hosts=False,
        )

    def test_hosted_runner_uses_project_root_without_embedding_token(self):
        import ast
        import os

        from host import HostManager

        original_cwd = os.getcwd()
        os.chdir(self.temp_dir.name)
        token = "fake.token-value"
        project_root = Path(__file__).resolve().parent
        runner_path = project_root / "runner_test-id.py"
        Path("hosted_test.json").write_text(json.dumps({"token": token, "prefix": "$"}), encoding="utf-8")
        try:
            with patch("host.subprocess.Popen", return_value=Mock()):
                manager = HostManager.__new__(HostManager)
                manager._run_their_bot("hosted_test.json", token, hosted_uid="test-id")

            runner = runner_path.read_text(encoding="utf-8")
            project_root_text = str(project_root)
            self.assertIn(f"SOURCE_ROOT = {project_root_text!r}", runner)
            self.assertIn(str(Path(self.temp_dir.name, "hosted_test.json")), runner)
            self.assertNotIn(token, runner)
            self.assertTrue(Path(project_root, "main.py").is_file())
            runner_ast = ast.parse(runner)
            copy_filter = next(
                node for node in runner_ast.body
                if isinstance(node, ast.FunctionDef) and node.name == "_should_copy_root_file"
            )
            filter_module = ast.Module(body=[copy_filter], type_ignores=[])
            filter_namespace = {"SYNC_FILE_SUFFIXES": (".py", ".html")}
            exec(compile(filter_module, "hosted-runner-filter", "exec"), filter_namespace)
            should_copy = filter_namespace["_should_copy_root_file"]
            self.assertTrue(should_copy("hosted_command_registry.py"))
            self.assertTrue(should_copy("hosted_rpc_bridge.py"))
            self.assertTrue(should_copy("main.py"))
            self.assertFalse(should_copy("hosted_users.json"))
            self.assertFalse(should_copy("hosted_123456.json"))
            self.assertFalse(should_copy("runner_123456.py"))
            self.assertFalse(should_copy("account_stats.json"))
        finally:
            runner_path.unlink(missing_ok=True)
            os.chdir(original_cwd)

    def test_frozen_entrypoint_dispatches_hosted_script(self):
        import os
        import sys

        import aria_entry

        script_path = str(Path(self.temp_dir.name) / "runner.py")
        with patch.object(sys, "frozen", True, create=True), \
                patch.object(sys, "_MEIPASS", self.temp_dir.name, create=True), \
                patch.object(sys, "argv", ["Aria.exe", "--aria-run-script", script_path]), \
                patch("aria_entry.os.chdir"), \
                patch("aria_entry.runpy.run_path") as run_path:
            aria_entry.main()

        run_path.assert_called_once_with(os.path.abspath(script_path), run_name="__main__")

    def test_restore_reattaches_to_surviving_hosted_process(self):
        from host import HostManager

        manager = HostManager.__new__(HostManager)
        manager._restore_lock = threading.Lock()
        manager._restore_in_progress = False
        manager.lock = threading.RLock()
        manager.saved_users = {
            "host-id": {"uid": "host-id", "token": "fake.token-value", "owner": "owner", "pid": 4321}
        }
        manager.active_tokens = {}
        manager.processes = {}
        manager._stop_events = {}
        manager._is_token_valid = lambda token: True
        attached_process = Mock(pid=4321)
        manager._attach_existing_process = Mock(return_value=attached_process)
        manager._run_their_bot = Mock()
        manager._start_keepalive = Mock()
        manager._save_users = Mock()

        restored = manager.restore_hosted_users()

        self.assertEqual(restored, 1)
        self.assertIs(manager.processes["host-id"], attached_process)
        self.assertEqual(manager.active_tokens["host-id"]["pid"], 4321)
        manager._run_their_bot.assert_not_called()
        manager._start_keepalive.assert_called_once_with("host-id")

    def test_friend_directory_requires_authentication_and_account_identity(self):
        scraper = SimpleNamespace(
            get_all_friend_ids=Mock(return_value=["friend-id"]),
            get_all_friend_details=Mock(return_value={"friend-id": {"username": "Friend"}}),
        )
        panel.bot.user_id = "bot-account"
        panel.bot.friend_scraper = scraper

        self.assertEqual(self.client.get("/api/friends").status_code, 403)

        self.authenticated = True
        with self.client.session_transaction() as active_session:
            active_session["user_id"] = "other-account"
        self.assertEqual(self.client.get("/api/friends").status_code, 403)

        with self.client.session_transaction() as active_session:
            active_session["user_id"] = "bot-account"
        response = self.client.get("/api/friends")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["friends"][0]["user_id"], "friend-id")
        scraper.get_all_friend_ids.assert_called_once_with(force_refresh=False)

    def test_self_hosted_list_is_owner_scoped_and_never_returns_tokens(self):
        self.authenticated = True
        with self.client.session_transaction() as active_session:
            active_session["user_id"] = "account-owner"
        manager = SimpleNamespace(
            registration_enabled=True,
            list_authorized_users=lambda: [],
            list_hosted_accounts=lambda owner_id: [
                {"user_id": "mine", "owner": "account-owner", "prefix": ";", "enabled": True, "registered_at": 1}
            ] if owner_id == "account-owner" else [],
        )
        panel.bot.self_hosting_manager = manager
        panel._is_owner_session = lambda: False

        response = self.client.get("/api/self-hosted")

        self.assertEqual(response.status_code, 200)
        self.assertEqual([account["user_id"] for account in response.json["accounts"]], ["mine"])
        self.assertNotIn("token", response.json["accounts"][0])

    def test_self_hosted_mutation_rejects_foreign_accounts(self):
        self.authenticated = True
        with self.client.session_transaction() as active_session:
            active_session["user_id"] = "requester"
        disable_account = Mock(return_value=(True, "disabled"))
        manager = SimpleNamespace(
            get_account=lambda user_id: {"owner": "another-user"},
            disable_account=disable_account,
        )
        panel.bot.self_hosting_manager = manager
        panel._is_owner_session = lambda: False

        response = self.client.post("/api/self-hosted", json={"action": "disable", "user_id": "foreign"})

        self.assertEqual(response.status_code, 403)
        disable_account.assert_not_called()

    def test_self_host_registration_and_allowlist_are_owner_only(self):
        self.authenticated = True
        with self.client.session_transaction() as active_session:
            active_session["user_id"] = "requester"
        set_registration_enabled = Mock(return_value=(True, "updated"))
        authorize_user = Mock(return_value=(True, "authorized"))
        manager = SimpleNamespace(
            set_registration_enabled=set_registration_enabled,
            authorize_user=authorize_user,
        )
        panel.bot.self_hosting_manager = manager
        panel._is_owner_session = lambda: False

        disabled = self.client.post("/api/self-hosted", json={"action": "registration", "enabled": False})
        authorized = self.client.post("/api/self-hosted", json={"action": "authorize", "user_id": "new-user"})
        self.assertEqual(disabled.status_code, 403)
        self.assertEqual(authorized.status_code, 403)
        set_registration_enabled.assert_not_called()
        authorize_user.assert_not_called()

        panel._is_owner_session = lambda: True
        owner_result = self.client.post("/api/self-hosted", json={"action": "authorize", "user_id": "123456789012345678"})
        invalid_user_id = self.client.post("/api/self-hosted", json={"action": "authorize", "user_id": "not-a-snowflake"})
        self.assertEqual(owner_result.status_code, 200)
        self.assertEqual(invalid_user_id.status_code, 400)
        authorize_user.assert_called_once_with("123456789012345678")

    def test_self_hosted_mutations_require_authentication(self):
        manager = SimpleNamespace()
        panel.bot.self_hosting_manager = manager

        response = self.client.post("/api/self-hosted", json={"action": "disable", "user_id": "mine"})

        self.assertEqual(response.status_code, 403)

    def test_owner_can_view_and_remove_any_hosted_instance(self):
        self.authenticated = True
        panel._require_admin = lambda: True
        panel._is_owner_session = lambda: True
        with self.client.session_transaction() as active_session:
            active_session["user_id"] = _PANEL_MASTER_ID
        remove_hosts = Mock(return_value=1)
        manager = SimpleNamespace(
            lock=threading.RLock(),
            saved_users={
                "first-token": {"owner": "first-user", "username": "First"},
                "second-token": {"owner": "second-user", "username": "Second"},
            },
            active_tokens={},
            remove_hosts=remove_hosts,
        )

        with patch("host.host_manager", manager):
            listing = self.client.get("/api/hosted")
            removed = self.client.post("/api/hosted/disconnect", json={"token_id": "second-token"})

        self.assertEqual(listing.status_code, 200)
        self.assertTrue(listing.json["is_owner"])
        self.assertEqual(len(listing.json["hosted"]), 2)
        self.assertEqual(removed.status_code, 200)
        remove_hosts.assert_called_once_with(
            requester_id=None,
            selectors=["second-token"],
            all_hosts=True,
        )

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
        panel._list_user_hosted_entries = lambda user_id: []

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
            "discord_id": "123456789012345678",
            "password": "a strong passphrase",
            "next": "/dashboard",
        })

        self.assertEqual(login_response.status_code, 302)
        self.assertEqual(login_response.headers["Location"], "/connect-instance")
        with self.client.session_transaction() as active_session:
            self.assertEqual(active_session["user_id"], user_id)
            self.assertEqual(active_session["discord_user_id"], "123456789012345678")

    def test_login_selects_instance_matching_discord_id(self):
        users = {
            "account-id": {
                "username": "aria-user",
                "password_hash": panel._hash_pw("a strong passphrase"),
                "instance_id": panel.instance_id,
                "role": "user",
            }
        }
        panel._load_dashboard_users = lambda: users
        panel._configured_admin_ids = lambda: set()
        panel._mark_login_success = lambda *args: None
        panel._list_user_hosted_entries = lambda user_id: [
            ("token-123", {"user_id": "123456789012345678"}, True, {"process_running": True}),
            ("token-456", {"user_id": "987654321098765432"}, True, {"process_running": True}),
        ]

        response = self.client.post("/login", data={
            "csrf_token": "test-csrf-token",
            "username": "aria-user",
            "discord_id": "123456789012345678",
            "password": "a strong passphrase",
        })

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/dashboard")
        with self.client.session_transaction() as active_session:
            self.assertEqual(active_session["host_token_id"], "token-123")

    def test_login_rejects_discord_id_without_matching_connected_instance(self):
        users = {
            "account-id": {
                "username": "aria-user",
                "password_hash": panel._hash_pw("a strong passphrase"),
                "instance_id": panel.instance_id,
                "role": "user",
            }
        }
        panel._load_dashboard_users = lambda: users
        panel._configured_admin_ids = lambda: set()
        panel._mark_login_success = lambda *args: None
        panel._list_user_hosted_entries = lambda user_id: [
            ("token-123", {"user_id": "123456789012345678"}, True, {"process_running": True}),
        ]

        response = self.client.post("/login", data={
            "csrf_token": "test-csrf-token",
            "username": "aria-user",
            "discord_id": "987654321098765432",
            "password": "a strong passphrase",
        })

        self.assertEqual(response.status_code, 302)
        self.assertIn("No+connected+instance+matches", response.headers["Location"])

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

    def test_instance_link_rejects_token_for_different_discord_id(self):
        self.authenticated = True
        panel._require_admin = lambda: False
        with self.client.session_transaction() as active_session:
            active_session["user_id"] = "account-id"
            active_session["discord_user_id"] = "123456789012345678"

        with patch("host.host_manager.validate_token_api", return_value=(True, {"id": "987654321098765432"})), \
                patch("host.host_manager.host_token") as host_token:
            response = self.client.post("/connect-instance", data={
                "csrf_token": "test-csrf-token",
                "token": "validated-token",
            })

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/connect-instance?error=Token+does+not+match+your+Discord+ID")
        host_token.assert_not_called()

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
        panel._list_user_hosted_entries = lambda user_id: []

        response = self.client.post("/login", data={
            "csrf_token": "test-csrf-token",
            "username": "legacy-id",
            "discord_id": "123456789012345678",
            "password": "legacy password",
        })

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

    def test_commands_api_reads_the_signed_in_users_hosted_registry(self):
        self.authenticated = True
        panel._require_admin = lambda: False
        panel._session_hosted_live_context = lambda: {
            "primary": {
                "token_id": "client-123",
                "saved": {"prefix": "$"},
                "active": True,
            },
        }
        command = type("Command", (), {"name": "ping", "aliases": ["latency"], "description": "Check latency"})()
        registry_path = Path(self.temp_dir.name) / "hosted_runtime" / "commands_client-123.json"
        write_command_registry(SimpleNamespace(prefix="$", commands={"ping": command}), str(registry_path))

        response = self.client.get("/api/commands")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["data"]["prefix"], "$")
        self.assertEqual(response.json["data"]["total"], 1)
        self.assertEqual(response.json["data"]["commands"][0]["name"], "ping")
        self.assertEqual(response.json["data"]["commands"][0]["aliases"], ["latency"])

    def test_commands_api_requires_a_dashboard_session(self):
        self.authenticated = False

        response = self.client.get("/api/commands")

        self.assertEqual(response.status_code, 403)

    def test_hosted_rpc_bridge_applies_changes_to_the_child_client(self):
        hosted_bot = SimpleNamespace(
            activity=None,
            _rpc_rotation_state={"running": False},
            set_activity=lambda activity: setattr(hosted_bot, "activity", activity),
        )
        stop_event = start_hosted_rpc_worker(hosted_bot, self.temp_dir.name)
        try:
            activity = {"type": 0, "name": "Hosted client activity"}
            result = dispatch_hosted_rpc(self.temp_dir.name, "set", activity)

            self.assertTrue(result["ok"])
            self.assertEqual(hosted_bot.activity, activity)
            self.assertTrue(dispatch_hosted_rpc(self.temp_dir.name, "stop")["ok"])
            self.assertIsNone(hosted_bot.activity)
        finally:
            stop_event.set()

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
        with self.client.session_transaction() as active_session:
            active_session["user_id"] = _PANEL_MASTER_ID
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