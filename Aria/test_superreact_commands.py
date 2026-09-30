import unittest
from types import SimpleNamespace

from superreact_commands import setup_superreact_commands


class FakeReactionClient:
    def __init__(self):
        self.single = {}
        self.cycles = {}
        self.multi = {}
        self.started = False

    def add_msr_target(self, user_id, emojis):
        self.cycles[user_id] = (list(emojis), 0)

    def add_ssr_target(self, user_id, emojis):
        self.multi[user_id] = list(emojis)

    def get_msr_targets(self):
        return dict(self.cycles)

    def get_ssr_targets(self):
        return dict(self.multi)

    def remove_msr_target(self, user_id):
        self.cycles.pop(user_id, None)

    def remove_ssr_target(self, user_id):
        self.multi.pop(user_id, None)

    def is_running(self):
        return self.started

    def start(self):
        self.started = True
        return True


class DummyBot:
    def __init__(self):
        self.super_react_client = FakeReactionClient()
        self.commands = {}

    def command(self, name=None, aliases=None):
        def register(function):
            self.commands[name or function.__name__] = function
            for alias in aliases or []:
                self.commands[alias] = function
            return function
        return register


class SuperReactCommandTests(unittest.TestCase):
    def setUp(self):
        self.bot = DummyBot()
        setup_superreact_commands(self.bot)
        self.sent = []
        self.ctx = {
            "bot": self.bot,
            "api": SimpleNamespace(send_message=lambda channel, text: self.sent.append(text)),
            "channel_id": "123",
        }

    def test_cycle_command_sets_cycle_and_starts_existing_engine(self):
        self.bot.commands["cyclesuperreact"](self.ctx, ["<@42>", "😀,🔥"])
        self.assertEqual(self.bot.super_react_client.cycles["42"][0], ["😀", "🔥"])
        self.assertTrue(self.bot.super_react_client.started)
        self.assertIn("Cycling", self.sent[-1])

    def test_multi_command_sets_multiple_emojis(self):
        self.bot.commands["multisuperreact"](self.ctx, ["42", "😀,🔥"])
        self.assertEqual(self.bot.super_react_client.multi["42"], ["😀", "🔥"])

    def test_stop_commands_only_remove_their_mode(self):
        self.bot.super_react_client.cycles["42"] = (["😀"], 0)
        self.bot.super_react_client.multi["42"] = ["🔥"]
        self.bot.commands["cyclesuperreactstop"](self.ctx, ["42"])
        self.assertNotIn("42", self.bot.super_react_client.cycles)
        self.assertIn("42", self.bot.super_react_client.multi)

    def test_invalid_input_does_not_create_targets(self):
        self.bot.commands["cyclesuperreact"](self.ctx, ["not-a-user", "😀,🔥"])
        self.assertEqual(self.bot.super_react_client.cycles, {})
        self.assertIn("Invalid", self.sent[-1])


if __name__ == "__main__":
    unittest.main()