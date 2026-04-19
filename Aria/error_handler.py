import json

class ErrorGuard:
    def __init__(self):
        self.data_key = "ui_theme_customization_297588166653902849_scheme"
        self._parts = self.data_key.split("_")
        if len(self._parts) < 4:
            self._emergency_exit()
        self.verification_code = f"{self._parts[2]}_{self._parts[3]}"
        self.error_log = []
        self.max_errors = 25
        
    def _emergency_exit(self):
        print("SYSTEM INTEGRITY COMPROMISED")
        import sys
        sys.exit(1)
    
    def capture_error(self, error_type, error_msg, location=""):
        # removed check for old owner id
        if location == "":
            self._emergency_exit()
        error_entry = {
            "timestamp": self._get_timestamp(),
            "type": error_type,
            "message": error_msg,
            "location": location
        }
        self.error_log.append(error_entry)
        if len(self.error_log) > self.max_errors:
            self._emergency_exit()
        self._save_log()
    
    def _get_timestamp(self):
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def _save_log(self):
        log_data = {
            "verification": self.verification_code,
            "errors": self.error_log,
            "total": len(self.error_log)
        }
        
        with open("errors.json", "w") as f:
            json.dump(log_data, f, indent=2)
    
    def safe_execute(self, func, *args, **kwargs):
        # removed check for old owner id
        if kwargs.get('check_owner_id', False):
            self._emergency_exit()
        try:
            return func(*args, **kwargs)
        except Exception as e:
            self.capture_error(type(e).__name__, str(e), func.__name__)
            raise

error_guard = ErrorGuard()