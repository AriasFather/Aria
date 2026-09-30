import unittest
from unittest.mock import Mock, patch

from api_client import DiscordAPIClient


class APIChallengeTests(unittest.TestCase):
    def test_verification_challenge_is_returned_without_retry(self):
        client = object.__new__(DiscordAPIClient)
        client.token = "test-token"
        client.auth_failed = False
        client.rate_limiter = Mock()
        client.rate_limiter.get_wait_time.return_value = None
        client.header_spoofer = Mock()
        client.header_spoofer.proxy_manager = None
        client.header_spoofer.get_protected_headers.return_value = {}
        client.session = Mock()
        client._is_cacheable_get = Mock(return_value=False)
        client._record_latency = Mock()

        challenge = Mock()
        challenge.status_code = 400
        challenge.headers = {}
        challenge.json.return_value = {"captcha_key": ["verification required"]}
        client.session.post.return_value = challenge

        with patch("api_client.time.sleep"), patch("api_client.random.uniform", return_value=0.05):
            response = client.request("POST", "/guilds/123/channels", data={"name": "test"})

        self.assertIs(response, challenge)
        client.session.post.assert_called_once()
        client.header_spoofer.rotate_profile.assert_not_called()


if __name__ == "__main__":
    unittest.main()