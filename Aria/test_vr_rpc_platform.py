import unittest

import vr_rpc


class VRRPCPlatformTests(unittest.TestCase):
    def test_platform_switching_uses_known_platforms(self):
        vr_rpc.set_active_platform("android")
        self.assertEqual(vr_rpc.get_active_platform(), "android")
        self.assertIn("android", vr_rpc._PLATFORM_PROPS)

        vr_rpc.set_active_platform("invalid-platform")
        self.assertEqual(vr_rpc.get_active_platform(), "off")


if __name__ == "__main__":
    unittest.main()
