import os
import tempfile
import unittest
from unittest.mock import patch

from panel_security import load_panel_secret_key


class PanelSecretKeyTests(unittest.TestCase):
    def test_key_is_random_persistent_and_private(self):
        with tempfile.TemporaryDirectory() as directory:
            first_key = load_panel_secret_key(directory)
            self.assertEqual(len(first_key), 32)
            self.assertEqual(load_panel_secret_key(directory), first_key)

            key_path = os.path.join(directory, ".aria_webpanel_secret")
            if os.name == "posix":
                self.assertEqual(os.stat(key_path).st_mode & 0o077, 0)

        with tempfile.TemporaryDirectory() as other_directory:
            self.assertNotEqual(load_panel_secret_key(other_directory), first_key)

    def test_environment_secret_takes_precedence(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {"ARIA_WEBPANEL_SECRET": "managed-secret"}):
                self.assertEqual(load_panel_secret_key(directory), "managed-secret")
            self.assertFalse(os.path.exists(os.path.join(directory, ".aria_webpanel_secret")))


if __name__ == "__main__":
    unittest.main()