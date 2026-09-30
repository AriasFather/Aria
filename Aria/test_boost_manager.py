import unittest

from boost_manager import BoostManager


class FakeResponse:
    def __init__(self, status_code):
        self.status_code = status_code


class FakeApi:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def request(self, method, endpoint, data=None):
        self.calls.append((method, endpoint, data))
        return self.response


class BoostManagerTests(unittest.TestCase):
    def test_boost_uses_the_available_slot_id(self):
        api = FakeApi(FakeResponse(204))
        manager = BoostManager(api)
        manager._get_cached_slots = lambda force=False: [{"id": "slot-actual-73"}]
        manager.save_state = lambda: None

        success, message = manager.boost_server("guild-42")

        self.assertTrue(success)
        self.assertEqual(message, "Boosted server guild-42")
        self.assertEqual(api.calls, [(
            "PUT",
            "/users/@me/guilds/premium/subscriptions/slot-actual-73",
            {"guild_id": "guild-42"},
        )])
        self.assertEqual(manager.available_boosts, 1)

    def test_boost_skips_slots_on_cooldown(self):
        api = FakeApi(FakeResponse(204))
        manager = BoostManager(api)
        manager._get_cached_slots = lambda force=False: [{
            "id": "slot-cooling",
            "cooldown_ends_at": "2999-01-01T00:00:00+00:00",
        }]

        success, message = manager.boost_server("guild-42")

        self.assertFalse(success)
        self.assertEqual(message, "No available boost slots")
        self.assertEqual(api.calls, [])


if __name__ == "__main__":
    unittest.main()