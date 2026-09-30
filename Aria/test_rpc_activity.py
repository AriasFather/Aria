import unittest

from rpc_activity import (
    RPC_TYPE_ALIASES,
    RPC_TYPE_GROUPS,
    build_rpc_activity,
    parse_rpc_key_values,
)


class RpcActivityTests(unittest.TestCase):
    def test_parser_preserves_quoted_values_and_splits_button_lists(self):
        values = parse_rpc_key_values(
            'name="My Game" details="Ranked match" '
            'buttons=Website,Community button_urls=https://example.com,https://discord.com'
        )
        self.assertEqual(values["name"], "My Game")
        self.assertEqual(values["details"], "Ranked match")
        self.assertEqual(values["buttons"], ["Website", "Community"])
        self.assertEqual(values["button_urls"], ["https://example.com", "https://discord.com"])

    def test_watching_and_competing_build_generic_activities(self):
        watching = build_rpc_activity(
            "watching", {"name": "Arcane", "details": "Season 2"}, now_ms=1000
        )
        competing = build_rpc_activity(
            "competing", {"name": "Ranked tournament"}, now_ms=1000
        )
        self.assertEqual((watching["type"], watching["name"], watching["details"]), (3, "Arcane", "Season 2"))
        self.assertEqual((competing["type"], competing["name"]), (5, "Ranked tournament"))

    def test_custom_status_and_custom_activity(self):
        status = build_rpc_activity(
            "custom_status", {"text": "Taking a break", "emoji": "☕"}
        )
        custom = build_rpc_activity(
            "custom", {"activity_type": "0", "name": "My Activity", "details": "Working"}, now_ms=1000
        )
        self.assertEqual(status["type"], 4)
        self.assertEqual(status["state"], "Taking a break")
        self.assertEqual(status["emoji"]["name"], "☕")
        self.assertEqual((custom["type"], custom["name"], custom["details"]), (0, "My Activity", "Working"))

    def test_custom_stream_activity_accepts_twitch_com_and_rejects_unrelated_host(self):
        activity = build_rpc_activity(
            "custom", {"activity_type": 1, "name": "Live", "stream_url": "https://twitch.com/channel"}, now_ms=1000
        )
        self.assertEqual(activity["url"], "https://twitch.com/channel")
        with self.assertRaisesRegex(ValueError, "Twitch or YouTube"):
            build_rpc_activity(
                "custom", {"activity_type": 1, "name": "Live", "stream_url": "https://not-twitch.tv/channel"}, now_ms=1000
            )

    def test_alias_and_help_groups_separate_providers_from_activity_modes(self):
        self.assertEqual(RPC_TYPE_ALIASES["watch"], "watching")
        self.assertIn("competing", RPC_TYPE_GROUPS["activity"])
        self.assertNotIn("social", RPC_TYPE_GROUPS)
        removed_modes = {
            "youtube_music", "applemusic", "deezer", "tidal", "twitch", "kick",
            "netflix", "disneyplus", "primevideo", "plex", "jellyfin",
            "desktop", "mobile", "phone", "web",
        }
        configured_modes = {mode for group in RPC_TYPE_GROUPS.values() for mode in group}
        self.assertTrue(removed_modes.isdisjoint(configured_modes))


if __name__ == "__main__":
    unittest.main()
