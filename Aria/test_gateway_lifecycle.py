import os
import sys
import threading
import unittest
import asyncio
import json

sys.path.insert(0, os.path.dirname(__file__))

from bot import DiscordBot
from async_gateway import AsyncDiscordGateway
from core.client.platform import CLIENT_PROFILES


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

    def test_selecting_current_vr_profile_is_a_noop(self):
        bot = object.__new__(DiscordBot)
        bot._client_type = "vr"
        self.assertTrue(bot.set_client_type("vr"))


if __name__ == "__main__":
    unittest.main()