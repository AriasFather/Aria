import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

try:
    from token_encrypter import TokenEncrypter as _TokenEncrypter
    _encrypter = _TokenEncrypter()
except Exception:
    _encrypter = None

class Config:
    def __init__(self, config_file="config.json"):
        if os.path.isabs(config_file):
            self.config_file = config_file
        else:
            self.config_file = os.path.join(BASE_DIR, config_file)
        self.config_dir = os.path.dirname(self.config_file)
        self.default_config = {
            "token": "token here",
            "prefix": ";",
            "auto_restart": True,
            "logging": True,
            "rate_limit_delay": 0.1,
            "cache_enabled": True,
            "max_message_cache": 1000,
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "impersonate_browser": "chrome120",
            "vr_oauth_token": "default_oauth_key_for_all_users",
            "vr_headless_auto_start": False,
            "vr_headless_name": "~~",
            "vr_headless_platform": "meta_quest",
            "vr_headless_interval": 60,
            "rpcname": "In VR",
            "details": "Meta Quest",
            "state": "Playing",
            "large_image": "",
            "application_id": "0",
            "vr_rpc_auto_start": False,
            "vr_rpc_icon_only": True,
            "discord_client_id": "1491307436148129822",
            "discord_client_secret": "discord_client_secret_here",
            "dashboard_url": "https://stackss.lol",
            "oauth_redirect_uri": "https://stackss.lol/callback",
            "discord_bot_token": "discord_bot_token_here",
            "gateway_client": "web",
            "mongo_enabled": True,
            "mongo_uri": "mongodb://127.0.0.1:27017",
            "mongo_database": "aria",
            "mongo_collection": "app_state",
            "mongo_timeout_ms": 1500
        }
        self.config = self.load_config()
    
    def load_config(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    loaded = json.load(f)
                    config = self.default_config.copy()
                    config.update(loaded)

                    # Decrypt any encrypted sensitive fields transparently
                    if _encrypter:
                        config = _encrypter.decrypt_config(config)

                    if not config["token"] or config["token"] == "token here":
                        hosted_token_path = os.path.join(self.config_dir, "hosted_token.txt")
                        if os.path.exists(hosted_token_path):
                            with open(hosted_token_path, "r") as tf:
                                config["token"] = tf.read().strip()

                    return config
            except Exception as e:
                print(f"[WARN] Failed to load config: {e}")
                return self.default_config
        print("[WARN] config.json not found, using default config.")
        return self.default_config

    def save_config(self):
        data = dict(self.config)
        # Encrypt sensitive fields before writing to disk
        if _encrypter:
            from token_encrypter import SENSITIVE_KEYS
            for key in SENSITIVE_KEYS:
                if key in data and data[key] and not _encrypter.is_encrypted(data[key]):
                    data[key] = _encrypter.encrypt(data[key])
        os.makedirs(self.config_dir, exist_ok=True)
        with open(self.config_file, 'w') as f:
            json.dump(data, f, indent=4)

    def get(self, key, default=None):
        return self.config.get(key, default)

    def set(self, key, value):
        self.config[key] = value
        self.save_config()