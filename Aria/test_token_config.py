import json
import os
import tempfile
import unittest

import config
from token_encrypter import TokenEncrypter
from token_config import configure_token


class TokenConfigTests(unittest.TestCase):
    def test_remembered_token_is_encrypted_and_can_be_cleared(self):
        previous_encrypter = config._encrypter
        try:
            with tempfile.TemporaryDirectory() as directory:
                config._encrypter = TokenEncrypter(os.path.join(directory, ".aria_key"))
                config_path = os.path.join(directory, "config.json")

                configure_token("test-token", remember=True, config_path=config_path)

                with open(config_path, "r", encoding="utf-8") as handle:
                    saved = json.load(handle)["token"]
                self.assertTrue(saved.startswith("enc:"))
                self.assertEqual(config.Config(config_path).get("token"), "test-token")

                configure_token("test-token", remember=False, config_path=config_path)
                with open(config_path, "r", encoding="utf-8") as handle:
                    self.assertEqual(json.load(handle)["token"], "")
        finally:
            config._encrypter = previous_encrypter


if __name__ == "__main__":
    unittest.main()
