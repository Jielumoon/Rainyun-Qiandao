import unittest

from rainyun.config import Config, DEFAULT_PUSH_CONFIG


class ConfigFromEnvTests(unittest.TestCase):
    def test_defaults(self) -> None:
        config = Config.from_env({})
        self.assertEqual(config.timeout, 15)
        self.assertEqual(config.max_delay, 90)
        self.assertFalse(config.debug)
        self.assertTrue(config.linux_mode)
        self.assertEqual(config.points_to_cny_rate, 2000)
        self.assertEqual(config.push_config["HITOKOTO"], DEFAULT_PUSH_CONFIG["HITOKOTO"])

    def test_bool_and_int_parsing(self) -> None:
        env = {
            "DEBUG": "1",
            "LINUX_MODE": "false",
            "CAPTCHA_RETRY_UNLIMITED": "true",
            "TIMEOUT": "20",
            "MAX_DELAY": "5",
        }
        config = Config.from_env(env)
        self.assertTrue(config.debug)
        self.assertFalse(config.linux_mode)
        self.assertTrue(config.captcha_retry_unlimited)
        self.assertEqual(config.timeout, 20)
        self.assertEqual(config.max_delay, 5)

    def test_invalid_int_fallback(self) -> None:
        env = {"RENEW_THRESHOLD_DAYS": "bad"}
        config = Config.from_env(env)
        self.assertEqual(config.renew_threshold_days, 7)

    def test_renew_product_ids(self) -> None:
        config = Config.from_env({"RENEW_PRODUCT_IDS": "1, 2,3"})
        self.assertEqual(config.renew_product_ids, [1, 2, 3])
        self.assertFalse(config.renew_product_ids_parse_error)

        config = Config.from_env({"RENEW_PRODUCT_IDS": "1,a"})
        self.assertEqual(config.renew_product_ids, [])
        self.assertTrue(config.renew_product_ids_parse_error)

    def test_url_trim(self) -> None:
        config = Config.from_env({"APP_BASE_URL": "https://example.com/"})
        self.assertEqual(config.app_base_url, "https://example.com")

    def test_push_config_override(self) -> None:
        env = {"PUSH_KEY": "abc", "HITOKOTO": "false"}
        config = Config.from_env(env)
        self.assertEqual(config.push_config["PUSH_KEY"], "abc")
        self.assertEqual(config.push_config["HITOKOTO"], "false")


if __name__ == "__main__":
    unittest.main()
