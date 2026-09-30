import tempfile
import unittest
from pathlib import Path

from message_logger import MessageLogger


class MessageLoggerTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.logger = MessageLogger(str(Path(self.temp_dir.name) / "logger.json"), feed_limit=2)
        self.message = {
            "id": "1",
            "channel_id": "20",
            "guild_id": "30",
            "author": {"id": "40", "username": "Sender"},
            "content": "hello aria",
        }

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_disabled_by_default_and_scoped_keyword_capture(self):
        self.logger.on_message_create(self.message, owner_id="99")
        self.assertEqual(self.logger.state()["feed"], [])

        self.logger.update_config({"enabled": True, "keywords": ["Aria"], "scope": {"mode": "guild", "id": "30"}})
        self.logger.on_message_create(self.message, owner_id="99")
        self.assertEqual(self.logger.state()["feed"][0]["matched"], "Aria")

        outside_scope = {**self.message, "guild_id": "31"}
        self.logger.on_message_create(outside_scope, owner_id="99")
        self.assertEqual(len(self.logger.state()["feed"]), 1)

    def test_mention_edit_delete_and_bounded_feed(self):
        self.logger.update_config({"enabled": True})
        mentioned = {**self.message, "mentions": [{"id": "99"}]}
        self.logger.on_message_create(mentioned, owner_id="99")
        edited = {**self.message, "content": "edited text"}
        self.logger.on_message_update(edited, self.message, owner_id="99")
        self.logger.on_message_delete({"id": "1", "channel_id": "20", "guild_id": "30"}, self.message, owner_id="99")

        feed = self.logger.state()["feed"]
        self.assertEqual(len(feed), 2)
        self.assertEqual([item["kind"] for item in feed], ["delete", "edit"])

    def test_rejects_invalid_scope_and_ignores_own_messages(self):
        with self.assertRaises(ValueError):
            self.logger.update_config({"scope": {"mode": "channel", "id": ""}})
        self.logger.update_config({"enabled": True, "keywords": ["hello"]})
        self.logger.on_message_create(self.message, owner_id="40")
        self.assertEqual(self.logger.state()["feed"], [])


if __name__ == "__main__":
    unittest.main()