import unittest
from unittest.mock import Mock

from api_client import DiscordAPIClient


class FakeResponse:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self.payload = payload

    def json(self):
        return self.payload


class AcknowledgeAllGuildsTests(unittest.TestCase):
    def setUp(self):
        self.client = object.__new__(DiscordAPIClient)
        self.client.request = Mock()

    def test_uses_channel_latest_message_and_continues_past_failed_guild(self):
        self.client.request.side_effect = [
            FakeResponse(200, [{"id": "guild-1"}, {"id": "guild-2"}]),
            FakeResponse(200, [
                {"id": "text-1", "type": 0, "last_message_id": "message-1"},
                {"id": "voice-1", "type": 2, "last_message_id": "message-2"},
                {"id": "empty-1", "type": 0, "last_message_id": None},
            ]),
            FakeResponse(204),
            FakeResponse(403),
        ]

        result = self.client.acknowledge_all_guilds()

        self.assertEqual(result["guilds"], 2)
        self.assertEqual(result["channels"], 1)
        self.assertEqual(result["acked"], 1)
        self.assertEqual(result["guilds_failed"], 1)
        self.assertEqual(result["channels_failed"], 0)
        self.assertFalse(any("/messages?limit=1" in call.args[1] for call in self.client.request.call_args_list))

    def test_counts_acknowledgement_failures(self):
        self.client.request.side_effect = [
            FakeResponse(200, [{"id": "guild-1"}]),
            FakeResponse(200, [{"id": "text-1", "type": 0, "last_message_id": "message-1"}]),
            FakeResponse(500),
        ]

        result = self.client.acknowledge_all_guilds()

        self.assertEqual(result["channels"], 1)
        self.assertEqual(result["acked"], 0)
        self.assertEqual(result["channels_failed"], 1)


if __name__ == "__main__":
    unittest.main()