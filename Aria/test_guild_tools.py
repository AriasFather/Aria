import threading
import unittest
from types import SimpleNamespace

from guild_tools import GuildTools, setup_guild_commands


class FakeApi:
    def __init__(self):
        self.guilds = [{"id": "101", "name": "Alpha"}, {"id": "202", "name": "Beta"}]
        self.requests = []
        self.rotation_called = threading.Event()

    def get_guilds(self, force=False):
        return list(self.guilds)

    def request(self, method, endpoint, **kwargs):
        self.requests.append((method, endpoint, kwargs))
        self.rotation_called.set()
        return SimpleNamespace(status_code=200, json=lambda: {})


class GuildToolsTests(unittest.TestCase):
    def setUp(self):
        self.api = FakeApi()
        self.tools = GuildTools(self.api)

    def tearDown(self):
        self.tools.stop_rotation()

    def test_set_clan_requires_a_guild_on_the_account(self):
        self.assertEqual(self.tools.set_clan("999"), "That guild is not in your account's guild list.")
        self.assertEqual(self.api.requests, [])

        self.assertEqual(self.tools.set_clan("202"), "Clan tag set for guild 202.")
        self.assertEqual(self.api.requests[-1][1], "/users/@me/clan")
        self.assertEqual(self.api.requests[-1][2]["json"], {
            "identity_guild_id": "202",
            "identity_enabled": True,
        })

    def test_clear_clan_uses_disabled_null_identity(self):
        self.assertEqual(self.tools.clear_clan(), "Clan tag cleared.")
        self.assertEqual(self.api.requests[-1][2]["json"], {
            "identity_guild_id": None,
            "identity_enabled": False,
        })

    def test_rotation_starts_on_selected_guild_and_stops(self):
        self.assertIn("Rotating 2 clan tag(s)", self.tools.start_rotation("2 1 1 1m"))
        self.assertTrue(self.api.rotation_called.wait(1))
        self.assertEqual(self.api.requests[-1][2]["json"]["identity_guild_id"], "202")
        self.assertTrue(self.tools.rotation_running)
        self.assertTrue(self.tools.stop_rotation())
        self.assertFalse(self.tools.rotation_running)

    def test_rotation_rejects_invalid_indexes_and_intervals(self):
        self.assertIn("Usage:", self.tools.start_rotation("0 2"))
        self.assertIn("Usage:", self.tools.start_rotation("1 1441m"))
        self.assertFalse(self.tools.rotation_running)

    def test_setup_registers_commands_and_aliases(self):
        class DummyBot:
            def __init__(self):
                self.api = FakeApi()
                self.commands = {}

            def command(self, name=None, aliases=None):
                def register(function):
                    self.commands[name or function.__name__] = function
                    for alias in aliases or []:
                        self.commands[alias] = function
                    return function
                return register

        bot = DummyBot()
        setup_guild_commands(bot)
        self.assertIs(bot.commands["setclan"], bot.commands["settag"])
        self.assertIn("clearclan", bot.commands)
        self.assertIn("rotatetags", bot.commands)
        self.assertIn("stoprotatetags", bot.commands)


if __name__ == "__main__":
    unittest.main()