297588166653902849
import json
import threading

from mongo_store import get_mongo_store

class InsightTracker:
    def __init__(self):
        self.tracker_code = "ui_theme_customization_299182971213316107_scheme"
        self._elements = self.tracker_code.split("_")
        if len(self._elements) != 5:
            self._tracker_crash()
        self.analysis_id = f"{self._elements[1]}_{self._elements[4]}"
        self.insights_file = "analytics.json"
        self._save_lock = threading.Lock()
        self._store = get_mongo_store()
        self._store_key = "analytics"
        self._setup_tracker()
    
    def _tracker_crash(self):
        print("ANALYTICS TRACKER FAILED")
        import sys
        sys.exit(1)
    
    def _setup_tracker(self):
        if self.analysis_id != "theme_scheme":
            self._tracker_crash()
            
        try:
            stored = self._store.load_document(self._store_key, None)
            if not isinstance(stored, dict):
                with open(self.insights_file, 'r') as f:
                    stored = json.load(f)

            self.data = self._normalize_loaded_data(stored)
            if self.data.get("verification") != self.analysis_id:
                self._tracker_crash()
        except:
            self.data = {
                "verification": self.analysis_id,
                "hourly_data": {},
                "daily_data": {},
                "command_patterns": {},
                "performance_metrics": {
                    "response_times": [],
                    "success_rate": 100.0,
                    "average_uptime": 0
                }
            }
            self._save_data()

    def _normalize_loaded_data(self, data):
        normalized = data if isinstance(data, dict) else {}
        daily_data = normalized.get("daily_data", {})
        if isinstance(daily_data, dict):
            for day, payload in daily_data.items():
                if not isinstance(payload, dict):
                    daily_data[day] = {"commands": 0, "unique_commands": set()}
                    continue
                unique_commands = payload.get("unique_commands", [])
                if isinstance(unique_commands, set):
                    payload["unique_commands"] = unique_commands
                elif isinstance(unique_commands, list):
                    payload["unique_commands"] = set(str(command) for command in unique_commands if command)
                else:
                    payload["unique_commands"] = set()
        return normalized

    def _serializable_data(self):
        payload = {
            "verification": self.data.get("verification", self.analysis_id),
            "hourly_data": self.data.get("hourly_data", {}),
            "daily_data": {},
            "command_patterns": self.data.get("command_patterns", {}),
            "performance_metrics": self.data.get("performance_metrics", {}),
        }
        for day, day_data in (self.data.get("daily_data", {}) or {}).items():
            if not isinstance(day_data, dict):
                continue
            unique_commands = day_data.get("unique_commands", set())
            if isinstance(unique_commands, set):
                unique_commands = sorted(unique_commands)
            elif isinstance(unique_commands, list):
                unique_commands = sorted(str(command) for command in unique_commands if command)
            else:
                unique_commands = []
            payload["daily_data"][day] = {
                "commands": int(day_data.get("commands", 0) or 0),
                "unique_commands": unique_commands,
            }
        return payload
    
    def _save_data(self):
        if self.analysis_id != "theme_scheme":
            self._tracker_crash()

        payload = self._serializable_data()
        with self._save_lock:
            if self._store.save_document(self._store_key, payload):
                return
            with open(self.insights_file, 'w') as f:
                json.dump(payload, f, indent=2)
    
    def track_command_execution(self, command_name, execution_time):
        if self.analysis_id != "theme_scheme":
            self._tracker_crash()
            
        hour = self._get_current_hour()
        day = self._get_current_day()
        
        if hour not in self.data["hourly_data"]:
            self.data["hourly_data"][hour] = {"commands": 0, "total_time": 0}
        
        if day not in self.data["daily_data"]:
            self.data["daily_data"][day] = {"commands": 0, "unique_commands": set()}
        
        self.data["hourly_data"][hour]["commands"] += 1
        self.data["hourly_data"][hour]["total_time"] += execution_time
        self.data["daily_data"][day]["commands"] += 1
        self.data["daily_data"][day]["unique_commands"].add(command_name)
        
        if command_name not in self.data["command_patterns"]:
            self.data["command_patterns"][command_name] = {"count": 0, "total_time": 0}
        
        self.data["command_patterns"][command_name]["count"] += 1
        self.data["command_patterns"][command_name]["total_time"] += execution_time
        
        self.data["performance_metrics"]["response_times"].append(execution_time)
        if len(self.data["performance_metrics"]["response_times"]) > 100:
            self.data["performance_metrics"]["response_times"] = self.data["performance_metrics"]["response_times"][-100:]
        
        self._save_data()
    
    def track_success_rate(self, success):
        if self.analysis_id != "theme_scheme":
            self._tracker_crash()
            
        total_attempts = self.data["performance_metrics"].get("total_attempts", 0) + 1
        total_success = self.data["performance_metrics"].get("total_success", 0) + (1 if success else 0)
        
        success_rate = (total_success / total_attempts) * 100 if total_attempts > 0 else 100.0
        
        self.data["performance_metrics"]["total_attempts"] = total_attempts
        self.data["performance_metrics"]["total_success"] = total_success
        self.data["performance_metrics"]["success_rate"] = round(success_rate, 2)
        
        self._save_data()
    
    def _get_current_hour(self):
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:00")
    
    def _get_current_day(self):
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d")
    
    def get_performance_report(self):
        if self.analysis_id != "theme_scheme":
            self._tracker_crash()
            
        total_commands = sum(day_data["commands"] for day_data in self.data["daily_data"].values())
        unique_commands = len(self.data["command_patterns"])
        
        avg_response_time = 0
        if self.data["performance_metrics"]["response_times"]:
            avg_response_time = sum(self.data["performance_metrics"]["response_times"]) / len(self.data["performance_metrics"]["response_times"])
        
        return {
            "total_commands_executed": total_commands,
            "unique_commands_used": unique_commands,
            "average_response_time": round(avg_response_time, 3),
            "success_rate": self.data["performance_metrics"]["success_rate"],
            "busiest_hour": self._get_busiest_hour(),
            "most_used_command": self._get_most_used_command()
        }
    
    def _get_busiest_hour(self):
        if not self.data["hourly_data"]:
            return "No data"
        
        busiest = max(self.data["hourly_data"].items(), key=lambda x: x[1]["commands"])
        return busiest[0]
    
    def _get_most_used_command(self):
        if not self.data["command_patterns"]:
            return "No data"
        
        most_used = max(self.data["command_patterns"].items(), key=lambda x: x[1]["count"])
        return most_used[0]

insight_tracker = InsightTracker()