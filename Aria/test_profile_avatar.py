import unittest
from unittest.mock import Mock, patch

from profile_avatar import MAX_AVATAR_BYTES, download_avatar_data_uri, image_to_data_uri


class ProfileAvatarTests(unittest.TestCase):
    def test_supported_image_signatures_choose_mime_type(self):
        samples = (
            (b"\x89PNG\r\n\x1a\nimage", "image/png"),
            (b"\xff\xd8\xffimage", "image/jpeg"),
            (b"GIF89aimage", "image/gif"),
            (b"RIFF0000WEBPimage", "image/webp"),
        )
        for data, mime_type in samples:
            with self.subTest(mime_type=mime_type):
                self.assertTrue(image_to_data_uri(data).startswith(f"data:{mime_type};base64,"))

    def test_rejects_empty_unknown_and_oversized_images(self):
        for data in (b"", b"not an image", b"x" * (MAX_AVATAR_BYTES + 1)):
            with self.subTest(length=len(data)):
                with self.assertRaises(ValueError):
                    image_to_data_uri(data)

    @patch("profile_avatar.requests.get")
    def test_download_uses_isolated_https_request_and_closes_response(self, get):
        response = Mock()
        response.status_code = 200
        response.headers = {"Content-Length": "11"}
        response.iter_content.return_value = [b"\x89PNG\r\n\x1a\nimage"]
        get.return_value = response

        data_uri = download_avatar_data_uri("https://images.example/avatar.png")

        self.assertTrue(data_uri.startswith("data:image/png;base64,"))
        get.assert_called_once()
        self.assertNotIn("Authorization", get.call_args.kwargs["headers"])
        self.assertFalse(get.call_args.kwargs["allow_redirects"])
        response.close.assert_called_once()

    @patch("profile_avatar.requests.get")
    def test_download_rejects_non_https_without_request(self, get):
        with self.assertRaisesRegex(ValueError, "HTTPS"):
            download_avatar_data_uri("http://images.example/avatar.png")
        get.assert_not_called()


if __name__ == "__main__":
    unittest.main()