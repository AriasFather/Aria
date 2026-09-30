import json
import time
import threading
from datetime import datetime, timedelta

class BoostManager:
    def __init__(self, api_client):
        self.api = api_client
        self.boosted_servers = {}  # Bot's own boosts
        self.server_boosts = {}    # Real user boosts per server
        self.available_boosts = 2
        self.last_check = 0
        self.boost_thread = None
        self.running = False
        self.rotation_servers = []
        self.rotation_hours = 24
        self.rotation_thread = None
        self._guild_scan_cache = {"timestamp": 0.0, "ok": False}
        self._slots_cache = {"timestamp": 0.0, "data": None}

    def _get_cached_slots(self, force: bool = False):
        now = time.time()
        if not force and self._slots_cache["data"] is not None and now - self._slots_cache["timestamp"] < 120:
            return self._slots_cache["data"]

        response = self.api.request("GET", "/users/@me/guilds/premium/subscription-slots")
        if response and response.status_code == 200:
            slots = response.json()
            self._slots_cache = {"timestamp": now, "data": slots}
            return slots
        return None
        
    def load_state(self):
        try:
            with open('boost_state.json', 'r') as f:
                data = json.load(f)
                self.boosted_servers = data.get('boosted_servers', {})
                self.server_boosts = data.get('server_boosts', {})
                self.available_boosts = data.get('available_boosts', 2)
                self.rotation_servers = data.get('rotation_servers', [])
                self.rotation_hours = data.get('rotation_hours', 24)
        except FileNotFoundError:
            self.boosted_servers = {}
            self.server_boosts = {}
            self.available_boosts = 2
            self.rotation_servers = []
            self.rotation_hours = 24
        except Exception:
            self.boosted_servers = {}
            self.server_boosts = {}
            self.available_boosts = 2
            self.rotation_servers = []
            self.rotation_hours = 24
    
    def save_state(self):
        try:
            data = {
                'boosted_servers': self.boosted_servers,
                'server_boosts': self.server_boosts,
                'available_boosts': self.available_boosts,
                'rotation_servers': self.rotation_servers,
                'rotation_hours': self.rotation_hours,
                'last_saved': time.time()
            }
            with open('boost_state.json', 'w') as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass
    
    def check_boost_status(self):
        try:
            slots = self._get_cached_slots()
            if slots is not None:
                current_time = time.time()
                available = 0
                for slot in slots:
                    cooldown_ends_at = slot.get("cooldown_ends_at")
                    if cooldown_ends_at is None:
                        available += 1
                    else:
                        # Parse the ISO timestamp and check if cooldown has expired
                        try:
                            from datetime import datetime
                            cooldown_time = datetime.fromisoformat(cooldown_ends_at.replace('Z', '+00:00')).timestamp()
                            if current_time >= cooldown_time:
                                available += 1
                        except:
                            # If parsing fails, assume it's not available
                            pass
                self.available_boosts = available
                return available
        except Exception as e:
            print(f"Error checking boost status: {e}")
        return 0
    
    def update_server_boosts(self, server_id, boost_count):
        """Update the boost count for a server when we detect a change"""
        previous_count = self.server_boosts.get(server_id, 0)
        self.server_boosts[server_id] = boost_count
        
        if boost_count != previous_count:
            delta = boost_count - previous_count
            delta_symbol = "↑" if delta > 0 else "↓"
            delta_color = "\033[1;32m" if delta > 0 else "\033[1;31m"
            print(
                f"\033[1;36m[BOOST]\033[0m {delta_color}{delta_symbol}\033[0m {previous_count:3} → {boost_count:3} [{server_id}]"
            )
            self.save_state()
    
    def get_server_boost_count(self, server_id):
        """Get the current boost count for a server"""
        return self.server_boosts.get(server_id, 0)
    
    def get_total_boost_slots(self):
        """Get the total number of boost slots the user has"""
        try:
            slots = self._get_cached_slots()
            if slots is not None:
                return len(slots)
        except Exception as e:
            print(f"Error getting total boost slots: {e}")
        return 0
    
    def get_detailed_boost_info(self):
        """Get detailed information about all boost slots"""
        try:
            slots = self._get_cached_slots()
            if slots is not None:
                current_time = time.time()
                available = 0
                used = 0
                cooldowns = []
                
                for slot in slots:
                    cooldown_ends_at = slot.get("cooldown_ends_at")
                    is_premium = slot.get("premium_guild_subscription") is not None
                    
                    if is_premium:
                        used += 1
                    elif cooldown_ends_at is None:
                        available += 1
                    else:
                        # Check if cooldown has expired
                        try:
                            from datetime import datetime
                            cooldown_time = datetime.fromisoformat(cooldown_ends_at.replace('Z', '+00:00')).timestamp()
                            if current_time >= cooldown_time:
                                available += 1
                            else:
                                # Still on cooldown
                                cooldowns.append({
                                    'ends_at': cooldown_ends_at,
                                    'remaining_seconds': int(cooldown_time - current_time)
                                })
                        except:
                            # If parsing fails, assume it's not available
                            cooldowns.append({
                                'ends_at': cooldown_ends_at,
                                'remaining_seconds': -1
                            })
                
                return {
                    'total_slots': len(slots),
                    'available': available,
                    'used': used,
                    'on_cooldown': len(cooldowns),
                    'cooldowns': cooldowns
                }
        except Exception as e:
            print(f"Error getting detailed boost info: {e}")
        return {
            'total_slots': 0,
            'available': 0,
            'used': 0,
            'on_cooldown': 0,
            'cooldowns': []
        }
    
    def get_total_server_boosts(self):
        """Get total boosts across all servers"""
        return sum(self.server_boosts.values())
    
    def fetch_server_boosts(self):
        """Fetch current boost counts for all servers the bot is in"""
        try:
            now = time.time()
            if now - self._guild_scan_cache["timestamp"] < 300:
                return self._guild_scan_cache["ok"]

            guilds = self.api.get_guilds(force=False)
            if guilds:
                self._guild_scan_cache = {"timestamp": now, "ok": True}
                print(f"\033[1;36m[BOOST]\033[0m Scanning {len(guilds)} guilds...")
                
                for guild in guilds:
                    guild_id = guild.get("id")
                    guild_name = guild.get("name", "Unknown")
                    # Truncate long guild names
                    display_name = (guild_name[:30] + "...") if len(guild_name) > 30 else guild_name
                    
                    # Get detailed guild info to get boost count
                    detail_response = self.api.request("GET", f"/guilds/{guild_id}")
                    if detail_response and detail_response.status_code == 200:
                        detail_data = detail_response.json()
                        boost_count = detail_data.get("premium_subscription_count", 0)
                        print(f"\033[1;36m[BOOST]\033[0m {display_name:33} {boost_count:3} boosts")
                        self.update_server_boosts(guild_id, boost_count)
                    else:
                        print(f"\033[1;31m[BOOST]\033[0m {display_name:33} ERROR (HTTP {detail_response.status_code if detail_response else '?'})")
                        # Keep existing count if we can't fetch new data
                        pass
                        
                return True
            self._guild_scan_cache = {"timestamp": now, "ok": False}
        except Exception as e:
            print(f"Error fetching server boosts: {e}")
        return False
    
    def can_boost(self, server_id):
        current_time = time.time()
        if current_time - self.last_check > 300:
            self.check_boost_status()
            self.last_check = current_time
        
        return self.available_boosts > 0
    
    def boost_server(self, server_id):
        try:
            slots = self._get_cached_slots(force=True)
            if slots is None:
                return False, "Unable to fetch boost slots"

            from datetime import datetime, timezone
            now = datetime.now(timezone.utc)
            target_id = str(server_id)
            for slot in slots:
                if not isinstance(slot, dict):
                    continue
                slot_id = str(slot.get("id") or "").strip()
                if not slot_id:
                    continue

                subscription = slot.get("premium_guild_subscription")
                if isinstance(subscription, dict) and str(subscription.get("guild_id") or "") == target_id:
                    return True, f"Server {target_id} is already boosted"

                cooldown_ends_at = slot.get("cooldown_ends_at")
                if cooldown_ends_at:
                    try:
                        cooldown = datetime.fromisoformat(str(cooldown_ends_at).replace("Z", "+00:00"))
                        if cooldown > now:
                            continue
                    except (TypeError, ValueError):
                        continue

                response = self.api.request(
                    "PUT",
                    f"/users/@me/guilds/premium/subscriptions/{slot_id}",
                    data={"guild_id": target_id},
                )
                if response and response.status_code in (200, 204):
                    self.boosted_servers[target_id] = time.time()
                    self.available_boosts = max(0, int(self.available_boosts) - 1)
                    self._slots_cache = {"timestamp": 0.0, "data": None}
                    self.save_state()
                    return True, f"Boosted server {target_id}"
                status = response.status_code if response else "No response"
                if status == 403:
                    return False, "No permission to boost"
                if status == 404:
                    return False, "Server not found"
                return False, f"Failed: {status}"

            return False, "No available boost slots"
        except Exception as e:
            return False, f"Error: {str(e)[:50]}"
    
    def transfer_boost(self, from_server_id, to_server_id):
        try:
            response = self.api.request(
                "DELETE",
                f"/guilds/{from_server_id}/premium/subscriptions"
            )
            
            if response and response.status_code in [200, 204]:
                time.sleep(1)
                success, message = self.boost_server(to_server_id)
                if success:
                    if from_server_id in self.boosted_servers:
                        del self.boosted_servers[from_server_id]
                    self.save_state()
                    return True, f"Transferred boost from {from_server_id} to {to_server_id}"
        except Exception as e:
            return False, f"Transfer error: {str(e)[:50]}"
        
        return False, "Transfer failed"

    def transfer_boost_slots(self, to_server_id):
        """Transfer all available boost slots to a server using subscription-slots API.
        Returns (results_list, success_count) where each result is a dict."""
        results = []
        success_count = 0
        try:
            slots = self._get_cached_slots(force=True)
            if slots is None:
                return [], 0
            if not slots:
                return [], 0

            from datetime import datetime, timezone
            now = datetime.now(timezone.utc)

            for slot in slots:
                slot_id = slot.get("id")
                cooldown_ends_at = slot.get("cooldown_ends_at")
                sub = slot.get("premium_guild_subscription")

                # Already boosting target guild — skip
                if sub and sub.get("guild_id") == str(to_server_id):
                    continue

                # Still on cooldown — skip
                if cooldown_ends_at:
                    try:
                        cooldown_dt = datetime.fromisoformat(
                            cooldown_ends_at.replace("Z", "+00:00")
                        )
                        if cooldown_dt > now:
                            continue
                    except Exception:
                        continue

                # Transfer this slot
                try:
                    resp = self.api.request(
                        "PUT",
                        f"/users/@me/guilds/premium/subscriptions/{slot_id}",
                        data={"guild_id": str(to_server_id)}
                    )
                    time.sleep(0.8)
                    if resp and resp.status_code in (200, 204):
                        self.boosted_servers[to_server_id] = time.time()
                        success_count += 1
                        results.append({"slot_id": slot_id, "ok": True, "message": f"Boosted {to_server_id}"})
                    else:
                        code = resp.status_code if resp else "no response"
                        results.append({"slot_id": slot_id, "ok": False, "message": f"HTTP {code}"})
                except Exception as e:
                    results.append({"slot_id": slot_id, "ok": False, "message": str(e)[:60]})

            if success_count:
                self._slots_cache = {"timestamp": 0.0, "data": None}
                self.save_state()
        except Exception as e:
            print(f"[BoostManager] transfer_boost_slots error: {e}")
        return results, success_count
    
    def auto_boost_servers(self, server_list):
        if not server_list:
            return False, "No servers provided"
        
        boosted_count = 0
        for server_id in server_list:
            if self.can_boost(server_id):
                success, message = self.boost_server(server_id)
                if success:
                    boosted_count += 1
                else:
                    return False, f"Failed to boost {server_id}: {message}"
            else:
                return False, "No boosts available"
        
        self.save_state()
        return True, f"Successfully boosted {boosted_count} server(s)"
    
    def start_rotation(self, server_list, hours=24):
        if not server_list or len(server_list) < 2:
            return False, "Need at least 2 servers for rotation"
        
        if self.rotation_thread and self.running:
            return False, "Rotation already running"
        
        self.rotation_servers = server_list
        self.rotation_hours = hours
        self.running = True
        
        self.rotation_thread = threading.Thread(target=self._rotation_worker)
        self.rotation_thread.start()
        
        self.save_state()
        return True, f"Started rotation for {len(server_list)} servers (every {hours} hours)"
    
    def _rotation_worker(self):
        while self.running:
            try:
                for server_id in self.rotation_servers:
                    if not self.running:
                        break
                    
                    if server_id in self.boosted_servers:
                        self.api.request(
                            "DELETE",
                            f"/guilds/{server_id}/premium/subscriptions"
                        )
                        if server_id in self.boosted_servers:
                            del self.boosted_servers[server_id]
                        time.sleep(2)
                    
                    success, _ = self.boost_server(server_id)
                    if success:
                        pass
                    
                    for _ in range(self.rotation_hours * 3600 // 10):
                        if not self.running:
                            break
                        time.sleep(10)
                    
            except Exception:
                time.sleep(60)
    
    def stop_rotation(self):
        if not self.running:
            return False, "No rotation running"
        
        self.running = False
        self.rotation_servers = []
        
        if self.rotation_thread:
            self.rotation_thread.join(timeout=5)
            self.rotation_thread = None
        
        self.save_state()
        return True, "Stopped boost rotation"
    
    def get_boosted_servers(self):
        return list(self.boosted_servers.keys())
    
    def clear_expired_boosts(self):
        current_time = time.time()
        expired = []
        
        for server_id, boost_time in list(self.boosted_servers.items()):
            if current_time - boost_time > 30 * 24 * 3600:
                expired.append(server_id)
        
        for server_id in expired:
            del self.boosted_servers[server_id]
        
        if expired:
            self.save_state()
        
        return len(expired)