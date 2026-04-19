import time
import json
import re
import base64
from typing import Optional, Dict, Any


def _clean_captcha_messages(raw_value: Any) -> list[str]:
    if isinstance(raw_value, list):
        return [str(item).strip() for item in raw_value if str(item).strip()]
    if isinstance(raw_value, str) and raw_value.strip():
        return [raw_value.strip()]
    return []

# Try to import twocaptcha, but make it optional
try:
    from twocaptcha import TwoCaptcha
    TWOCAPTCHA_AVAILABLE = True
except ImportError:
    TWOCAPTCHA_AVAILABLE = False
    TwoCaptcha = None

# Try to import capsolver
try:
    import capsolver
    CAPSOLVER_AVAILABLE = True
except ImportError:
    capsolver = None
    CAPSOLVER_AVAILABLE = False

# Try to import requests for direct 2captcha API fallback
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    requests = None
    REQUESTS_AVAILABLE = False

class CaptchaSolver:
    """Comprehensive captcha solver for Discord API captcha challenges"""
    _missing_config_logged = False

    def __init__(self, api_key: str = "", service: str = "2captcha"):
        self.api_key = api_key
        self.service = service.lower() if isinstance(service, str) else service
        self.solver = None
        self.last_solve_time = 0
        self.session = requests.Session() if REQUESTS_AVAILABLE else None
        # Spoof/rotation fallback is always allowed if no key is set
        self.spoof_only = (not api_key) or self.service in {"spoof", "none"}

        if api_key and self.service == "2captcha":
            if TWOCAPTCHA_AVAILABLE and TwoCaptcha:
                try:
                    print(f"[DEBUG] Initializing TwoCaptcha with API key: {api_key[:4]}...{api_key[-4:]}")
                    self.solver = TwoCaptcha(api_key)
                    print("[DEBUG] TwoCaptcha initialized successfully.")
                except Exception as e:
                    print(f"[ERROR] TwoCaptcha initialization failed: {e}")
                    self.solver = None
            elif REQUESTS_AVAILABLE:
                self.solver = None
            else:
                print("[ERROR] 2captcha support requires either twocaptcha or requests.")
        elif api_key and self.service == "capsolver":
            if CAPSOLVER_AVAILABLE:
                capsolver.api_key = api_key
                print("[DEBUG] CapSolver library initialized.")
            elif REQUESTS_AVAILABLE:
                print("[DEBUG] CapSolver support enabled using requests fallback.")
            else:
                print("[ERROR] CapSolver support requires capsolver library or requests.")
        elif self.spoof_only:
            # Only print debug if no key is present
            if not api_key:
                print("[DEBUG] Captcha spoof/rotation fallback enabled; no solver key required.")
        else:
            if not CaptchaSolver._missing_config_logged:
                print("[DEBUG] Captcha support not configured or API key missing.")
                CaptchaSolver._missing_config_logged = True

    def is_enabled(self) -> bool:
        """Check if captcha solving is enabled"""
        return bool(self.spoof_only or (self.api_key and (self.solver is not None or REQUESTS_AVAILABLE)))

    def can_bypass_with_spoof(self) -> bool:
        if self.spoof_only:
            print("[CAPTCHA] No captcha key set or spoof mode enabled. Using header rotation/client transfer fallback.")
        return self.spoof_only

    def _build_captcha_response(self, response_data: Dict[str, Any], **values: Any) -> Dict[str, Any]:
        result = {key: value for key, value in values.items() if value not in (None, "", [])}

        captcha_messages = _clean_captcha_messages(response_data.get('captcha_key'))
        if captcha_messages:
            result['messages'] = captcha_messages
            result['requires_client_refresh'] = any(
                'update your app' in message.lower() for message in captcha_messages
            )

        rqdata = response_data.get('captcha_rqdata')
        if rqdata:
            result['rqdata'] = rqdata

        rqtoken = response_data.get('captcha_rqtoken')
        if rqtoken:
            result['rqtoken'] = rqtoken

        session_id = response_data.get('captcha_session_id')
        if session_id:
            result['session_id'] = session_id

        service = response_data.get('captcha_service') or result.get('service')
        if service:
            result['service'] = str(service)

        return result

    def solve_hcaptcha(self, site_key: str, url: str, invisible: bool = False,
                       rqdata: str = "") -> Optional[str]:
        if not self.is_enabled():
            print("[DEBUG] CAPTCHA solving is not enabled.")
            return None

        # 1. Try CapSolver library if available and selected
        if CAPSOLVER_AVAILABLE and self.service == "capsolver" and self.api_key:
            try:
                print(f"[DEBUG] Solving hCaptcha with CapSolver library for site_key: {site_key}, url: {url}")
                task = {
                    "type": "HCaptchaTaskProxyLess",
                    "websiteURL": "https://discord.com",
                    "websiteKey": site_key,
                }
                if rqdata:
                    task["isEnterprise"] = True
                    task["enterprisePayload"] = {"rqdata": rqdata}
                solution = capsolver.solve(task)
                token = solution.get("gRecaptchaResponse")
                if token:
                    self.last_solve_time = time.time()
                    print("[DEBUG] hCaptcha solved successfully with CapSolver.")
                    return token
            except Exception as e:
                print(f"[ERROR] Failed to solve hCaptcha with CapSolver library: {e}")

        # 2. Try generic solver (e.g., TwoCaptcha) if available and key is set
        if self.solver and self.api_key:
            try:
                print(f"[DEBUG] Solving hCaptcha for site_key: {site_key}, url: {url}")
                solver_kwargs = {
                    "site_key": site_key,
                    "page_url": url,
                }
                if rqdata:
                    solver_kwargs["data"] = rqdata
                    solver_kwargs["enterprise"] = 1
                result = self.solver.solve_captcha(**solver_kwargs)
                self.last_solve_time = time.time()
                print("[DEBUG] hCaptcha solved successfully.")
                return result
            except Exception as e:
                print(f"[ERROR] Failed to solve hCaptcha with TwoCaptcha library: {e}")

        # 3. Try HTTP fallback for 2captcha/capsolver if key is set
        if self.api_key:
            if self.service == "2captcha":
                token = self._solve_via_2captcha("hcaptcha", site_key, url, invisible, rqdata=rqdata)
                if token:
                    return token
            if self.service == "capsolver":
                token = self._solve_via_capsolver("hcaptcha", site_key, url, invisible, rqdata=rqdata)
                if token:
                    return token

        # 4. Fallback: spoof/rotate if all else fails
        print("[CAPTCHA] All real captcha solvers failed or not configured. Using spoof/rotation fallback.")
        return None

    def solve_recaptcha(self, site_key: str, url: str, version: str = "v2") -> Optional[str]:
        """Solve reCAPTCHA challenge"""
        if not self.is_enabled():
            print("[DEBUG] CAPTCHA solving is not enabled.")
            return None

        if self.solver:
            try:
                print(f"[DEBUG] Solving reCAPTCHA for site_key: {site_key}, url: {url}, version: {version}")
                result = self.solver.solve_captcha(
                    site_key=site_key,
                    page_url=url
                )
                self.last_solve_time = time.time()
                print("[DEBUG] reCAPTCHA solved successfully.")
                return result
            except Exception as e:
                print(f"[ERROR] Failed to solve reCAPTCHA with TwoCaptcha library: {e}")

        if self.service == "2captcha":
            return self._solve_via_2captcha("userrecaptcha", site_key, url)
        if self.service == "capsolver":
            return self._solve_via_capsolver("recaptcha", site_key, url, invisible=False)
        return None

    def solve_turnstile(self, site_key: str, url: str) -> Optional[str]:
        """Solve Cloudflare Turnstile challenge"""
        if not self.is_enabled():
            print("[DEBUG] CAPTCHA solving is not enabled.")
            return None

        if self.solver:
            try:
                print(f"[DEBUG] Solving Turnstile CAPTCHA for site_key: {site_key}, url: {url}")
                result = self.solver.solve_captcha(
                    site_key=site_key,
                    page_url=url
                )
                self.last_solve_time = time.time()
                print("[DEBUG] Turnstile CAPTCHA solved successfully.")
                return result
            except Exception as e:
                print(f"[ERROR] Failed to solve Turnstile with TwoCaptcha library: {e}")

        if self.service == "2captcha":
            return self._solve_via_2captcha("turnstile", site_key, url)
        if self.service == "capsolver":
            return self._solve_via_capsolver("turnstile", site_key, url)

        return None

    def solve_kre(self, site_key: str, url: str, invisible: bool = False) -> Optional[str]:
        """Solve KRE-style CAPTCHA challenges."""
        if not self.is_enabled():
            print("[DEBUG] CAPTCHA solving is not enabled.")
            return None

        if self.solver:
            try:
                print(f"[DEBUG] Solving KRE for site_key: {site_key}, url: {url}")
                result = self.solver.solve_captcha(
                    site_key=site_key,
                    page_url=url
                )
                self.last_solve_time = time.time()
                print("[DEBUG] KRE solved successfully.")
                return result
            except Exception as e:
                print(f"[ERROR] Failed to solve KRE with TwoCaptcha library: {e}")

        if self.service == "2captcha":
            return self._solve_via_2captcha("turnstile", site_key, url)
        if self.service == "capsolver":
            return self._solve_via_capsolver("kre", site_key, url, invisible)
        return None

    def _extract_capsolver_solution(self, solution: Any) -> Optional[str]:
        if solution is None:
            return None
        if isinstance(solution, str):
            return solution
        if isinstance(solution, dict):
            for key in [
                'gRecaptchaResponse', 'token', 'response', 'captcha',
                'challenge', 'solution', 'data'
            ]:
                if key in solution and solution[key]:
                    return str(solution[key])
            values = [str(v) for v in solution.values() if v]
            if values:
                return values[0]
        return None

    def _solve_via_2captcha(self, task_type: str, site_key: str, url: str,
                            invisible: bool = False, rqdata: str = "") -> Optional[str]:
        if not self.api_key or not REQUESTS_AVAILABLE:
            print("[ERROR] Cannot solve captcha via 2captcha: missing API key or requests.")
            return None

        submit_payload = {
            'key': self.api_key,
            'method': task_type,
            'sitekey': site_key,
            'pageurl': url,
            'json': 1,
        }

        if task_type == 'hcaptcha':
            submit_payload['invisible'] = 1 if invisible else 0
            if rqdata:
                submit_payload['data'] = rqdata
                submit_payload['rqdata'] = rqdata
                submit_payload['enterprise'] = 1

        try:
            response = requests.post('https://2captcha.com/in.php', data=submit_payload, timeout=30)
            data = response.json()
        except Exception as e:
            print(f"[ERROR] 2captcha submission failed: {e}")
            return None

        if data.get('status') != 1:
            print(f"[ERROR] 2captcha submission error: {data.get('request')}")
            return None

        request_id = data.get('request')
        if not request_id:
            print("[ERROR] 2captcha did not return a request id.")
            return None

        for attempt in range(1, 25):
            time.sleep(5)
            try:
                result = requests.get(
                    'https://2captcha.com/res.php',
                    params={
                        'key': self.api_key,
                        'action': 'get',
                        'id': request_id,
                        'json': 1,
                    },
                    timeout=30,
                ).json()
            except Exception as e:
                print(f"[ERROR] 2captcha retrieval failed: {e}")
                continue

            if result.get('status') == 1:
                self.last_solve_time = time.time()
                return str(result.get('request') or '') or None

            if result.get('request') != 'CAPCHA_NOT_READY':
                print(f"[ERROR] 2captcha result error: {result.get('request')}")
                return None

            print(f"[DEBUG] 2captcha task {request_id} pending ({attempt}/24)")

        print("[ERROR] 2captcha solve timed out.")
        return None

    def _solve_via_capsolver(self, task_type: str, site_key: str, url: str,
                             invisible: bool = False, rqdata: str = "") -> Optional[str]:
        if not self.api_key or not REQUESTS_AVAILABLE:
            print("[ERROR] Cannot solve captcha via CapSolver: missing API key or requests.")
            return None

        caps_task_map = {
            'hcaptcha': 'HCaptchaTaskProxyLess',
            'recaptcha': 'ReCaptchaV2TaskProxyLess',
            'recaptcha_v3': 'ReCaptchaV3TaskProxyLess',
            'turnstile': 'AntiTurnstileTaskProxyLess',
            'kre': 'AntiTurnstileTaskProxyLess',
            'cloudflare': 'AntiCloudflareTask',
            'geetest': 'GeeTestTaskProxyLess',
        }

        task_name = caps_task_map.get(task_type.lower())
        if not task_name:
            print(f"[ERROR] CapSolver does not support type: {task_type}")
            return None

        task_payload = {
            'type': task_name,
            'websiteURL': 'https://discord.com',
            'websiteKey': site_key,
        }

        if task_name == 'HCaptchaTaskProxyLess':
            task_payload['isInvisible'] = invisible
            if rqdata:
                task_payload['isEnterprise'] = True
                task_payload['enterprisePayload'] = {'rqdata': rqdata}
        elif task_name == 'ReCaptchaV2TaskProxyLess' and invisible:
            task_payload['isInvisible'] = True
        elif task_name == 'AntiTurnstileTaskProxyLess':
            task_payload['metadata'] = {'action': 'verify'}

        create_payload = {
            'clientKey': self.api_key,
            'task': task_payload
        }

        headers = {'Content-Type': 'application/json'}
        create_url = 'https://api.capsolver.com/createTask'

        try:
            print(f"[DEBUG] Submitting captcha to CapSolver: type={task_name}, site_key={site_key}")
            response = requests.post(create_url, json=create_payload, headers=headers, timeout=30)
            data = response.json()
        except Exception as e:
            print(f"[ERROR] CapSolver submission failed: {e}")
            return None

        if data.get('errorId', 0) != 0:
            print(f"[ERROR] CapSolver submission error: {data.get('errorDescription') or data.get('errorMessage')}")
            return None

        task_id = data.get('taskId')
        if not task_id:
            print("[ERROR] CapSolver did not return a task ID.")
            return None

        result_url = 'https://api.capsolver.com/getTaskResult'
        polls = 20
        for attempt in range(1, polls + 1):
            time.sleep(5)
            try:
                response = requests.post(result_url, json={
                    'clientKey': self.api_key,
                    'taskId': task_id,
                }, headers=headers, timeout=30)
                result = response.json()
            except Exception as e:
                print(f"[ERROR] CapSolver retrieval failed: {e}")
                continue

            if result.get('errorId', 0) != 0:
                print(f"[ERROR] CapSolver result error: {result.get('errorDescription') or result.get('errorMessage')}")
                return None

            if result.get('status') == 'ready':
                solution = result.get('solution')
                return self._extract_capsolver_solution(solution)

            print(f"[DEBUG] CapSolver task {task_id} pending ({attempt}/{polls})")

        print("[ERROR] CapSolver solve timed out.")
        return None

    def extract_captcha_from_headers(self, headers: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """Extract captcha info from response headers"""
        # Check for X-Captcha-Key or similar headers Discord might send
        for header_key in headers:
            if 'captcha' in header_key.lower():
                try:
                    if header_key.lower() == 'x-captcha-key':
                        return {'site_key': headers[header_key], 'service': 'hcaptcha'}
                except:
                    pass
        return None

    def detect_captcha_type(self, response_data: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """Detect captcha type from Discord response - handles multiple formats"""
        if not isinstance(response_data, dict):
            return None

        # Format 1: Direct captcha field (standard format)
        captcha = response_data.get('captcha', {})
        if isinstance(captcha, dict) and captcha:
            captcha_type = str(captcha.get('type', '')).lower()
            site_key = captcha.get('site_key', '')
            service = captcha.get('service', 'hcaptcha')
            
            if site_key:
                return self._build_captcha_response(
                    response_data,
                    type=captcha_type or 'hcaptcha',
                    site_key=site_key,
                    service=service
                )

        # Format 2: Nested in captcha_sitekey
        if 'captcha_sitekey' in response_data:
            return self._build_captcha_response(
                response_data,
                type='hcaptcha',
                site_key=response_data['captcha_sitekey'],
                service='hcaptcha'
            )

        # Format 3: In captcha_key
        if isinstance(response_data.get('captcha_key'), str) and response_data.get('captcha_key'):
            return self._build_captcha_response(
                response_data,
                type='hcaptcha',
                site_key=response_data['captcha_key'],
                service='hcaptcha'
            )

        # Format 4: reCAPTCHA v2
        if response_data.get('captcha_type') == 'recaptcha_v2':
            return self._build_captcha_response(
                response_data,
                type='recaptcha',
                site_key=response_data.get('recaptcha_key', ''),
                service='recaptcha'
            )

        # Format 5: Turnstile
        if response_data.get('captcha_type') == 'turnstile':
            return self._build_captcha_response(
                response_data,
                type='turnstile',
                site_key=response_data.get('turnstile_key', ''),
                service='turnstile'
            )

        if response_data.get('captcha_type') == 'kre' or response_data.get('service') == 'kre':
            return self._build_captcha_response(
                response_data,
                type='kre',
                site_key=response_data.get('kre_key', response_data.get('site_key', '')),
                service='kre'
            )

        if 'kre_key' in response_data:
            return self._build_captcha_response(
                response_data,
                type='kre',
                site_key=response_data.get('kre_key', ''),
                service='kre'
            )

        return None

    def solve_captcha_challenge(self, captcha_info: Dict[str, str], url: str) -> Optional[str]:
        """Solve captcha based on detected type"""
        if not captcha_info:
            return None

        captcha_type = str(captcha_info.get('type', 'hcaptcha')).lower()
        site_key = captcha_info.get('site_key', '')
        
        if not site_key:
            return None

        print(f"[CAPTCHA] Detecting type: {captcha_type}, solving...")

        if captcha_type == 'hcaptcha':
            return self.solve_hcaptcha(site_key, url, rqdata=str(captcha_info.get('rqdata', '') or ''))
        elif captcha_type == 'recaptcha':
            return self.solve_recaptcha(site_key, url, version='v2')
        elif captcha_type == 'turnstile':
            return self.solve_turnstile(site_key, url)
        elif captcha_type == 'kre':
            return self.solve_kre(site_key, url)

        return None

    def get_captcha_ratelimit_key(self) -> Optional[str]:
        """Get the appropriate field name for captcha token based on service"""
        # Discord generically accepts "captcha_key" for most services
        return "captcha_key"