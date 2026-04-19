from pathlib import Path
import random
import requests
import time
from urllib.parse import urlparse

class ProxyManager:
    _local_load_logged = False
    _github_load_logged = False

    def __init__(self, proxy_list=None):
        self.proxies = []
        self.last_fetch = 0
        self.fetch_interval = 3600  # Refresh every hour
        self.local_proxy_file = Path(__file__).with_name("proxies.txt")

        # Only use proxies.txt, never fetch from GitHub
        self.proxies = self._load_local_proxies()

    def _normalize_proxy(self, proxy):
        entry = str(proxy or "").strip()
        if not entry or entry.startswith('#'):
            return None

        if entry.startswith(('http://', 'https://', 'socks4://', 'socks5://')):
            parsed = urlparse(entry)
            if not parsed.hostname or not parsed.port:
                return None

            scheme = (parsed.scheme or 'http').lower()
            # websocket-client only supports http, socks4, and socks5 proxy types.
            if scheme == 'https':
                scheme = 'http'
            if scheme not in {'http', 'socks4', 'socks5'}:
                return None

            auth = ""
            if parsed.username:
                auth = parsed.username
                if parsed.password:
                    auth += f":{parsed.password}"
                auth += "@"
            return f"{scheme}://{auth}{parsed.hostname}:{parsed.port}"

        parts = entry.split(':')
        if len(parts) == 2:
            host, port = parts
            return f"http://{host}:{port}"

        if len(parts) == 4:
            host, port, username, password = parts
            return f"http://{username}:{password}@{host}:{port}"

        return None

    def _normalize_proxies(self, proxy_list):
        normalized = []
        seen = set()
        for proxy in proxy_list:
            parsed = self._normalize_proxy(proxy)
            if parsed and parsed not in seen:
                normalized.append(parsed)
                seen.add(parsed)
        return normalized

    def _load_local_proxies(self):
        try:
            if not self.local_proxy_file.exists():
                return []
            lines = self.local_proxy_file.read_text(encoding="utf-8").splitlines()
            proxies = self._normalize_proxies(lines)
            if proxies and not ProxyManager._local_load_logged:
                print(f"[PROXY] Loaded {len(proxies)} proxies from {self.local_proxy_file.name}")
                ProxyManager._local_load_logged = True
            return proxies
        except Exception as e:
            print(f"[PROXY] Failed to load local proxies: {e}")
            return []
    
    # REMOVED: _fetch_from_github and refresh. Only proxies.txt is used.
    
    def get_random_proxy(self):
        """Return a random proxy from the loaded list, or empty dict if none."""
        if not self.proxies:
            self.proxies = self._load_local_proxies()
        if not self.proxies:
            return {}
        proxy = random.choice(self.proxies)
        return {"http": proxy, "https": proxy}
    
    def test_proxy(self, proxy):
        """Test if a proxy is working."""
        try:
            response = requests.get("https://httpbin.org/ip", proxies=proxy, timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def get_all_proxies(self):
        """Return all loaded proxies."""
        if not self.proxies:
            self.proxies = self._load_local_proxies()
        return list(self.proxies)