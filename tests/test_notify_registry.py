import importlib.util
import unittest

REQUESTS_AVAILABLE = importlib.util.find_spec("requests") is not None

if REQUESTS_AVAILABLE:
    from rainyun.notify.registry import build_default_registry


@unittest.skipUnless(REQUESTS_AVAILABLE, "requests 未安装，跳过通知注册表测试")
class NotifyRegistryTests(unittest.TestCase):
    def test_registry_filters_channels(self):
        registry = build_default_registry()
        config = {
            "BARK_PUSH": "token",
            "CONSOLE": "true",
        }
        names = [notifier.name for notifier in registry.resolve(config)]

        self.assertIn("bark", names)
        self.assertIn("console", names)
        self.assertNotIn("dingding_bot", names)


if __name__ == "__main__":
    unittest.main()
