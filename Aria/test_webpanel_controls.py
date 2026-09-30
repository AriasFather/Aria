import tempfile
import unittest
from pathlib import Path

from flask import Flask

from message_logger import MessageLogger
from rpc_profiles import RPCProfileStore
from webpanel import WebPanel


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