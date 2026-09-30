import tempfile
import unittest
from pathlib import Path

from rpc_profiles import RPCProfileStore


class RPCProfileStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.store = RPCProfileStore(str(Path(self.temp_dir.name) / "rpc_profiles.json"))

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_preset_round_trip_and_rotation(self):
        activity = {"type": 0, "name": "Aria Test", "details": "Build"}
        self.store.save_preset("Desk", activity)
        self.store.save_preset("Away", {"type": 3, "name": "Reading"})

        self.assertEqual(self.store.get_preset("Desk"), activity)
        self.assertEqual(list(self.store.list_presets()), ["Desk", "Away"])
        self.assertEqual(
            self.store.set_rotation(["Desk", "Away"], 45),
            {"presets": ["Desk", "Away"], "interval": 45},
        )
        self.assertEqual(self.store.get_rotation()["interval"], 45)
        self.store.clear_rotation()
        self.assertIsNone(self.store.get_rotation())

    def test_rejects_invalid_activities_and_rotations(self):
        with self.assertRaises(ValueError):
            self.store.save_preset("Bad", {"value": object()})
        with self.assertRaises(ValueError):
            self.store.set_rotation(["Missing", "Other"], 45)
        with self.assertRaises(ValueError):
            self.store.set_rotation(["Missing", "Other"], 2)

    def test_deleting_rotation_member_clears_invalid_rotation(self):
        self.store.save_preset("One", {"name": "one"})
        self.store.save_preset("Two", {"name": "two"})
        self.store.set_rotation(["One", "Two"], 30)

        self.assertTrue(self.store.delete_preset("One"))
        self.assertIsNone(self.store.get_rotation())
        self.assertFalse(self.store.delete_preset("One"))


if __name__ == "__main__":
    unittest.main()