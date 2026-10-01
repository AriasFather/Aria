import os
import sys
import threading
import unittest
import asyncio
import json
from unittest.mock import patch
from unittest.mock import Mock

sys.path.insert(0, os.path.dirname(__file__))

from bot import DiscordBot
from async_gateway import AsyncDiscordGateway
from core.client.platform import CLIENT_PROFILES, build_identify_payload
from voice import SimpleVoice, VoiceClient


def make_bot():
    bot = object.__new__(DiscordBot)
    defaults = {
        "running": True,
        "connection_active": False,
        "identified": False,
        "_connection_lock": threading.Lock(),
        "_connecting": False,
        "_reconnect_guard": threading.Lock(),
        "_reconnect_signal": threading.Event(),
        "_reconnect_stop": threading.Event(),
        "_reconnect_thread": None,
        "_last_connection_attempt": 0.0,
        "_consecutive_failures": 0,
        "_max_consecutive_failures": 15,
        "_connection_quality_score": 100,
        "_network_stability_score": 100,
        "_connection_start_time": 0.0,
        "_reconnect_ready_timeout": 0.04,
        "_reconnect_backoff_base": 0.01,
    }
    for name, value in defaults.items():
        setattr(bot, name, value)
    return bot


class GatewayLifecycleTests(unittest.TestCase):
    def test_coalesces_triggers_and_retries_until_ready(self):
        bot = make_bot()
        first_attempt = threading.Event()
        attempts = []
        attempts_lock = threading.Lock()

        def connect():
            with attempts_lock:
                attempts.append(len(attempts) + 1)
                attempt_number = len(attempts)
            if attempt_number == 1:
                first_attempt.set()
                return
            bot.connection_active = True
            bot.identified = True

        bot._connect_gateway = connect
        self.assertTrue(bot._schedule_reconnect("socket close"))
        self.assertTrue(first_attempt.wait(1))
        self.assertFalse(bot._schedule_reconnect("socket error"))

        worker = bot._reconnect_thread
        worker.join(timeout=2)

        self.assertFalse(worker.is_alive())
        self.assertEqual(attempts, [1, 2])
        self.assertTrue(bot.connection_active)
        self.assertTrue(bot.identified)

    def test_stop_cancels_backoff(self):
        bot = make_bot()
        bot._reconnect_backoff_base = 10
        attempted = threading.Event()
        calls = []

        def fail_connect():
            calls.append(1)
            attempted.set()
            raise OSError("offline")

        bot._connect_gateway = fail_connect
        bot._schedule_reconnect("startup")
        self.assertTrue(attempted.wait(1))
        bot._reconnect_stop.set()

        worker = bot._reconnect_thread
        worker.join(timeout=1)

        self.assertFalse(worker.is_alive())
        self.assertEqual(len(calls), 1)

    def test_stop_closes_async_bridge_once(self):
        class Bridge:
            def __init__(self):
                self.stop_calls = 0
                self.close_calls = 0

            def stop(self):
                self.stop_calls += 1

            def close(self):
                self.close_calls += 1

        bot = make_bot()
        bridge = Bridge()
        bot.use_async_gateway = True
        bot.gateway_bridge = bridge
        bot.ws = bridge

        bot.stop()

        self.assertEqual(bridge.stop_calls, 1)
        self.assertEqual(bridge.close_calls, 0)

    def test_async_identify_uses_vr_profile(self):
        class Socket:
            def __init__(self):
                self.payload = None

            async def send(self, payload):
                self.payload = json.loads(payload)

        gateway = AsyncDiscordGateway("test-token", client_type="vr", compress=False)
        gateway.ws = Socket()
        asyncio.run(gateway._identify())

        payload = gateway.ws.payload
        self.assertEqual(payload["d"]["properties"], CLIENT_PROFILES["vr"])
        self.assertEqual(payload["d"]["token"], "test-token")

    def test_identify_payload_preserves_multiple_activities(self):
        activities = [{"type": 0, "name": "Game"}, {"type": 3, "name": "Show"}]
        payload = build_identify_payload("test-token", "web", activity=activities)
        self.assertEqual(payload["d"]["presence"]["activities"], activities)

    def test_set_activities_sends_multiple_activities_and_keeps_legacy_primary(self):
        bot = object.__new__(DiscordBot)
        class Socket:
            def __init__(self):
                self.payload = None
            def send(self, payload):
                self.payload = json.loads(payload)

        bot.ws = Socket()
        bot.identified = True
        bot.connection_active = True
        bot._current_status = "online"
        bot._last_activity_signature = None

        activities = [{"type": 0, "name": "Game"}, {"type": 3, "name": "Show"}]
        bot.set_activities(activities)

        self.assertEqual(bot.activity["name"], "Game")
        self.assertEqual([item["name"] for item in bot.activities], ["Game", "Show"])
        self.assertEqual(bot.ws.payload["d"]["activities"], bot.activities)

    def test_async_bridge_routes_dispatch_through_one_bot_callback(self):
        bot = make_bot()
        bot.config = {"gateway_compress": False}
        bot._client_type = "web"
        bot.token = "test-token"
        bot.can_resume = False
        bot.session_id = None
        bot.gateway_bridge = None
        bot._async_gateway_bridge_active = False

        with patch("gateway_bridge.GatewayBridge") as bridge_type:
            bridge = bridge_type.return_value
            bot._connect_gateway_bridge()

        bridge.on_ready.assert_not_called()
        bridge.on_message.assert_not_called()
        bridge.on_payload.assert_called_once_with(bot._on_bridge_payload)

    def test_async_gateway_reconnect_opcode_closes_socket_and_notifies_owner(self):
        class Socket:
            def __init__(self):
                self.closed = False

            async def close(self):
                self.closed = True

        gateway = AsyncDiscordGateway("test-token", compress=False)
        gateway.ws = Socket()
        gateway.connected = True
        close_events = []
        gateway.on_close = lambda code, reason: close_events.append((code, reason))

        asyncio.run(gateway._handle_message(json.dumps({"op": 7, "d": None})))

        self.assertTrue(gateway.ws.closed)
        self.assertFalse(gateway.connected)
        self.assertEqual(close_events, [(4000, "Gateway requested reconnect")])

    def test_selecting_current_vr_profile_is_a_noop(self):
        bot = object.__new__(DiscordBot)
        bot._client_type = "vr"
        self.assertTrue(bot.set_client_type("vr"))

    def test_voice_client_accepts_state_updates_without_user_id_for_current_channel(self):
        client = VoiceClient(bot_ws=Mock(), user_id="12345")
        client.guild_id = "guild-1"
        client.channel_id = "channel-1"

        client.on_voice_state_update({
            "channel_id": "channel-1",
            "guild_id": "guild-1",
            "session_id": "session-xyz",
        })

        self.assertEqual(client.session_id, "session-xyz")
        self.assertTrue(client._session_event.is_set())

    def test_voice_client_ignores_other_users_state_updates_in_same_guild(self):
        client = VoiceClient(bot_ws=Mock(), user_id="12345")
        client.guild_id = "guild-1"
        client.channel_id = "channel-1"

        client.on_voice_state_update({
            "user_id": "another-user",
            "channel_id": "channel-1",
            "guild_id": "guild-1",
            "session_id": "wrong-session",
        })

        self.assertIsNone(client.session_id)
        self.assertFalse(client._session_event.is_set())

    def test_voice_client_accepts_server_updates_for_current_channel_when_guild_id_absent(self):
        client = VoiceClient(bot_ws=Mock(), user_id="12345")
        client.guild_id = None
        client.channel_id = "channel-1"

        client.on_voice_server_update({
            "channel_id": "channel-1",
            "endpoint": "voice.discord.gg:443",
            "token": "token-123",
        })

        self.assertEqual(client.endpoint, "voice.discord.gg")
        self.assertEqual(client.voice_token, "token-123")
        self.assertTrue(client._server_event.is_set())

    def test_partial_voice_join_remains_leaveable_after_handshake_failure(self):
        class PartialClient:
            def __init__(self, bot_ws, user_id):
                self.gateway_joined = False
                self._ws_error = ""
                self.disconnect_calls = 0

            def connect(self, channel_id, guild_id, is_dm):
                self.gateway_joined = True
                self._ws_error = "Timeout waiting for VOICE_SERVER_UPDATE"
                return False

            def disconnect(self):
                self.disconnect_calls += 1
                self.gateway_joined = False

        api = Mock()
        api.request.return_value.status_code = 200
        api.request.return_value.json.return_value = {"type": 2, "guild_id": "456"}
        bot = Mock()
        bot.ws = Mock()
        bot.user_id = "789"
        bot._voice_client = None
        manager = SimpleVoice(api, "token", bot)

        with patch("voice.VoiceClient", PartialClient):
            self.assertFalse(manager.join_vc("123"))
            self.assertTrue(manager.is_in_voice())
            client = manager.active_connections["channel_123"]

            self.assertTrue(manager.leave_vc())

        self.assertEqual(client.disconnect_calls, 1)
        self.assertIsNone(bot._voice_client)


if __name__ == "__main__":
    unittest.main()