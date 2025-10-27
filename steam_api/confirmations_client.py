
import requests
import subprocess
import time
import os
import signal
import json
from typing import Optional, List, Dict, Any
from pathlib import Path


class ConfirmationsAPIError(Exception):
    pass


class ConfirmationsClient:
    
        
        
        
        
    
    def __init__(self, host: str = "localhost", port: int = 3738, auto_start: bool = False):
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}/api"
        self.bridge_process: Optional[subprocess.Popen] = None
        
        if auto_start:
            self.start_bridge()
    
    def start_bridge(self, wait_time: int = 3) -> bool:
        
            
        if self.bridge_process and self.bridge_process.poll() is None:
            print("Confirmations Bridge уже запущен")
            return True
        
        script_dir = Path(__file__).parent
        bridge_script = script_dir / "confirmations_bridge.js"
        
        if not bridge_script.exists():
            raise ConfirmationsAPIError(f"Bridge script не найден: {bridge_script}")
        
        try:
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
            
            self.bridge_process = subprocess.Popen(
                ["node", str(bridge_script)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
            )
            
            print(f"Запуск Confirmations Bridge сервера (PID: {self.bridge_process.pid})...")
            time.sleep(wait_time)
            
            if self.is_alive():
                print(f"✓ Confirmations Bridge сервер запущен на {self.base_url}")
                return True
            else:
                raise ConfirmationsAPIError("Не удалось запустить bridge сервер")
                
        except Exception as e:
            raise ConfirmationsAPIError(f"Ошибка запуска bridge: {str(e)}")
    
    def stop_bridge(self) -> bool:
        
        if not self.bridge_process:
            print("Confirmations Bridge не запущен")
            return True
        
        try:
            if os.name == 'nt':
                os.kill(self.bridge_process.pid, signal.CTRL_BREAK_EVENT)
            else:
                self.bridge_process.terminate()
            
            self.bridge_process.wait(timeout=5)
            print("✓ Confirmations Bridge сервер остановлен")
            self.bridge_process = None
            return True
            
        except subprocess.TimeoutExpired:
            self.bridge_process.kill()
            self.bridge_process = None
            print("✓ Confirmations Bridge сервер принудительно остановлен")
            return True
        except Exception as e:
            print(f"Ошибка остановки bridge: {str(e)}")
            return False
    
    def is_alive(self) -> bool:
        
        try:
            response = requests.get(f"{self.base_url}/health", timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        
            
            
        url = f"{self.base_url}/{endpoint}"
        
        try:
            response = requests.request(method, url, **kwargs)
            data = response.json()
            
            if response.status_code >= 400:
                error_msg = data.get('error', 'Unknown error')
                raise ConfirmationsAPIError(f"API Error: {error_msg}")
            
            return data
            
        except requests.exceptions.RequestException as e:
            raise ConfirmationsAPIError(f"Request failed: {str(e)}")
        except ValueError as e:
            raise ConfirmationsAPIError(f"Invalid JSON response: {str(e)}")
    
    def login_with_mafile(
        self,
        mafile_path: str,
        password: str,
        session_id: Optional[str] = None
    ) -> str:
        
            
            
        mafile_path = Path(mafile_path)
        
        if not mafile_path.exists():
            raise ConfirmationsAPIError(f"maFile не найден: {mafile_path}")
        
        try:
            with open(mafile_path, 'r', encoding='utf-8') as f:
                mafile_data = json.load(f)
        except Exception as e:
            raise ConfirmationsAPIError(f"Ошибка чтения maFile: {str(e)}")
        
        required_fields = ['account_name', 'shared_secret', 'identity_secret']
        for field in required_fields:
            if field not in mafile_data:
                raise ConfirmationsAPIError(f"Отсутствует обязательное поле в maFile: {field}")
        
        data = {
            "maFileData": mafile_data,
            "password": password
        }
        
        if session_id:
            data["sessionId"] = session_id
        
        result = self._request("POST", "login-mafile", json=data)
        
        if not result.get("success"):
            raise ConfirmationsAPIError("Login failed")
        
        return result["sessionId"]
    
    def login_with_secrets(
        self,
        username: str,
        password: str,
        shared_secret: str,
        identity_secret: str,
        device_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> str:
        
            
        data = {
            "username": username,
            "password": password,
            "sharedSecret": shared_secret,
            "identitySecret": identity_secret
        }
        
        if device_id:
            data["deviceId"] = device_id
        
        if session_id:
            data["sessionId"] = session_id
        
        result = self._request("POST", "login-with-secrets", json=data)
        
        if not result.get("success"):
            raise ConfirmationsAPIError("Login with secrets failed")
        
        return result["sessionId"]
    
    def logout(self, session_id: str) -> bool:
        
            
        result = self._request("POST", "logout", json={"sessionId": session_id})
        return result.get("success", False)
    
    def get_confirmations(self, session_id: str) -> List[Dict[str, Any]]:
        
            
            
        result = self._request("GET", "confirmations", params={"sessionId": session_id})
        
        if not result.get("success"):
            raise ConfirmationsAPIError("Failed to get confirmations")
        
        return result.get("confirmations", [])
    
    def accept_confirmation(self, session_id: str, confirmation_id: str) -> bool:
        
            
        result = self._request(
            "POST",
            f"confirmations/{confirmation_id}/accept",
            json={"sessionId": session_id}
        )
        
        return result.get("success", False)
    
    def cancel_confirmation(self, session_id: str, confirmation_id: str) -> bool:
        
            
        result = self._request(
            "POST",
            f"confirmations/{confirmation_id}/cancel",
            json={"sessionId": session_id}
        )
        
        return result.get("success", False)
    
    def accept_all_confirmations(self, session_id: str) -> Dict[str, Any]:
        
            
        result = self._request(
            "POST",
            "confirmations/accept-all",
            json={"sessionId": session_id}
        )
        
        return result
    
    def cancel_all_confirmations(self, session_id: str) -> Dict[str, Any]:
        
            
        result = self._request(
            "POST",
            "confirmations/cancel-all",
            json={"sessionId": session_id}
        )
        
        return result
    
    def get_confirmation_details(
        self,
        session_id: str,
        confirmation_id: str
    ) -> Dict[str, Any]:
        
            
        result = self._request(
            "GET",
            f"confirmations/{confirmation_id}/details",
            params={"sessionId": session_id}
        )
        
        return result
    
    def __enter__(self):
        self.start_bridge()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop_bridge()
    
    def __del__(self):
        if self.bridge_process and self.bridge_process.poll() is None:
            self.stop_bridge()



def load_mafile(mafile_path: str) -> Dict[str, Any]:
    
        
    with open(mafile_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def extract_secrets_from_mafile(mafile_path: str) -> Dict[str, str]:
    
        
    mafile_data = load_mafile(mafile_path)
    
    return {
        "username": mafile_data.get("account_name"),
        "shared_secret": mafile_data.get("shared_secret"),
        "identity_secret": mafile_data.get("identity_secret"),
        "device_id": mafile_data.get("device_id")
    }


class ConfirmationType:
    GENERIC = 1
    TRADE = 2
    MARKET = 3
    FEATURE_OPT_OUT = 4
    PHONE_NUMBER_CHANGE = 5
    ACCOUNT_RECOVERY = 6
    
    @staticmethod
    def get_name(type_id: int) -> str:
        names = {
            1: "Generic",
            2: "Trade",
            3: "Market",
            4: "FeatureOptOut",
            5: "PhoneNumberChange",
            6: "AccountRecovery"
        }
        return names.get(type_id, "Unknown")
