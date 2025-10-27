
import requests
import subprocess
import time
import os
import signal
import sys
from pathlib import Path

try:
    import requests
except ImportError:
    print("Внимание: библиотека requests не найдена. Некоторые функции могут не работать.")
    requests = None

from pathlib import Path
from typing import Optional, Dict, Any, List
from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path


class SteamAPIError(Exception):
    pass


class SteamClient:
    
        
        
        
    
    def __init__(self, host: str = "localhost", port: int = 3737, auto_start: bool = False):
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}/api"
        self.bridge_process: Optional[subprocess.Popen] = None
        
        if auto_start:
            self.start_bridge()
    
    def _find_node_executable(self) -> Optional[str]:
        
        import shutil
        
        try:
            script_dir = Path(__file__).parent.parent
            sys.path.append(str(script_dir / "utils"))
            from ..utils.nodejs_installer import get_application_path
            
            app_dir = get_application_path()
            
            portable_node_paths = [
                app_dir / "node" / "node.exe",
                app_dir / "nodejs" / "node.exe",
                script_dir / "node" / "node.exe",
            ]
            
            for path in portable_node_paths:
                if path.exists() and path.is_file():
                    try:
                        result = subprocess.run([str(path), '--version'], 
                                              capture_output=True, text=True, timeout=5)
                        if result.returncode == 0:
                            print(f"Найден портативный Node.js: {path} ({result.stdout.strip()})")
                            return str(path)
                    except Exception:
                        continue
            
        except Exception as e:
            print(f"Ошибка при поиске портативного Node.js: {e}")
        
        node_path = shutil.which('node')
        if node_path:
            print(f"Найден Node.js в PATH: {node_path}")
            return node_path
        
        if os.name == 'nt':
            possible_paths = [
                r"C:\Program Files\nodejs\node.exe",
                r"C:\Program Files (x86)\nodejs\node.exe",
                os.path.expanduser(r"~\AppData\Roaming\npm\node.exe"),
                r"C:\nodejs\node.exe",
                os.path.expanduser(r"~\AppData\Local\Programs\nodejs\node.exe"),
            ]
            
            for path in possible_paths:
                if os.path.isfile(path):
                    print(f"Найден Node.js в стандартном пути: {path}")
                    return path
        
        else:
            possible_paths = [
                "/usr/local/bin/node",
                "/usr/bin/node",
                "/opt/node/bin/node"
            ]
            
            for path in possible_paths:
                if os.path.isfile(path):
                    print(f"Найден Node.js в Unix пути: {path}")
                    return path
        
        print("Node.js не найден ни в одном из путей")
        return None
    
    def _check_npm_packages(self) -> bool:
        try:
            if getattr(sys, 'frozen', False):
                steam_api_dir = Path(sys.executable).parent / "steam_api"
            else:
                script_dir = Path(__file__).parent
                steam_api_dir = script_dir
            
            print(f"🔍 Проверка npm пакетов в: {steam_api_dir}")
            
            node_modules = steam_api_dir / "node_modules"
            if not node_modules.exists():
                print("📦 node_modules не найден")
                return False
            
            required_packages = [
                "express",
                "body-parser", 
                "steam-totp",
                "steamcommunity",
                "steam-tradeoffer-manager"
            ]
            
            missing_packages = []
            for package in required_packages:
                package_dir = node_modules / package
                if not package_dir.exists():
                    missing_packages.append(package)
            
            if missing_packages:
                print(f"📦 Отсутствуют пакеты: {', '.join(missing_packages)}")
                return False
            
            print("✅ Все npm пакеты найдены")
            return True
            
        except Exception as e:
            print(f"⚠️ Ошибка проверки npm пакетов: {e}")
            return False
    
    def _install_npm_packages(self) -> bool:
        try:
            script_dir = Path(__file__).parent.parent
            sys.path.append(str(script_dir / "utils"))
            from ..utils.nodejs_installer import NodeJSInstaller
            
            installer = NodeJSInstaller()
            return installer.install_npm_packages()
            
        except ImportError:
            print("❌ Не удалось импортировать nodejs_installer")
            return False
        except Exception as e:
            print(f"❌ Ошибка установки npm пакетов: {e}")
            return False
    
    def start_bridge(self, wait_time: int = 5) -> bool:
        
            
        if self.is_alive():
            print("Bridge уже запущен и отвечает")
            return True
            
        if self.bridge_process and self.bridge_process.poll() is None:
            print("Bridge процесс существует, но не отвечает. Перезапускаем...")
            self.stop_bridge()
        
        script_dir = Path(__file__).parent
        
        if getattr(sys, 'frozen', False):
            bridge_script = Path(sys.executable).parent / "steam_api" / "steam_bridge.js"
            if not bridge_script.exists():
                bridge_script = Path(sys._MEIPASS) / "steam_api" / "steam_bridge.js"
        else:
            bridge_script = script_dir / "steam_bridge.js"
        
        if not bridge_script.exists():
            if getattr(sys, 'frozen', False):
                working_dir = Path(sys.executable).parent / "steam_api"
                working_dir.mkdir(exist_ok=True)
                temp_bridge = Path(sys._MEIPASS) / "steam_api" / "steam_bridge.js"
                
                if temp_bridge.exists():
                    import shutil
                    target_bridge = working_dir / "steam_bridge.js"
                    shutil.copy2(temp_bridge, target_bridge)
                    bridge_script = target_bridge
                    print(f"📄 Скопирован bridge script: {bridge_script}")
            
            if not bridge_script.exists():
                raise SteamAPIError(f"Bridge script не найден: {bridge_script}")
        
        print(f"🌉 Используется bridge script: {bridge_script}")
        
        try:
            node_path = self._find_node_executable()
            if not node_path:
                error_message = (
                    "Node.js не найден!\n\n"
                    "Возможные решения:\n"
                    "1. Скачайте и установите Node.js с https://nodejs.org/\n"
                    "2. Перезапустите программу после установки\n"
                    "3. Если Node.js уже установлен, добавьте его в PATH\n"
                    "4. Обратитесь в поддержку для получения портативной версии\n\n"
                    "Программа ищет Node.js в следующих местах:\n"
                    "- В папке приложения (node/node.exe)\n"
                    "- В переменной PATH\n"
                    "- C:\\Program Files\\nodejs\\node.exe\n"
                    "- C:\\Program Files (x86)\\nodejs\\node.exe"
                )
                raise SteamAPIError(error_message)
            
            if not self._check_npm_packages():
                print("📦 Установка необходимых npm пакетов...")
                if not self._install_npm_packages():
                    raise SteamAPIError("Не удалось установить npm пакеты для Steam API")
            
            env = os.environ.copy()
            
            if getattr(sys, 'frozen', False):
                steam_api_dir = Path(sys.executable).parent / "steam_api"
            else:
                steam_api_dir = Path(__file__).parent
            
            node_modules_path = steam_api_dir / "node_modules"
            
            if node_modules_path.exists():
                env['NODE_PATH'] = str(node_modules_path)
                print(f"🔧 NODE_PATH установлен: {node_modules_path}")
            
            cwd = bridge_script.parent
            
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
            
            print(f"🚀 Запуск Node.js: {node_path} {bridge_script}")
            print(f"📁 Рабочая папка: {cwd}")
            
            self.bridge_process = subprocess.Popen(
                [node_path, str(bridge_script)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0,
                env=env,
                cwd=str(cwd)
            )
            
            print(f"Запуск Steam Bridge сервера (PID: {self.bridge_process.pid})...")
            
            for i in range(wait_time):
                time.sleep(1)
                if self.is_alive():
                    print(f"✓ Steam Bridge сервер запущен на {self.base_url}")
                    return True
                elif self.bridge_process.poll() is not None:
                    stdout, stderr = self.bridge_process.communicate()
                    error_msg = stderr.decode() if stderr else "Неизвестная ошибка"
                    raise SteamAPIError(f"Bridge процесс завершился: {error_msg}")
            
            raise SteamAPIError("Steam Bridge сервер не отвечает после запуска")
                
        except Exception as e:
            raise SteamAPIError(f"Ошибка запуска bridge: {str(e)}")
    
    def stop_bridge(self) -> bool:
        
        if not self.bridge_process:
            print("Bridge не запущен")
            return True
        
        try:
            if os.name == 'nt':
                os.kill(self.bridge_process.pid, signal.CTRL_BREAK_EVENT)
            else:
                self.bridge_process.terminate()
            
            self.bridge_process.wait(timeout=5)
            print("✓ Steam Bridge сервер остановлен")
            self.bridge_process = None
            return True
            
        except subprocess.TimeoutExpired:
            self.bridge_process.kill()
            self.bridge_process = None
            print("✓ Steam Bridge сервер принудительно остановлен")
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
                raise SteamAPIError(f"API Error: {error_msg}")
            
            return data
            
        except requests.exceptions.RequestException as e:
            raise SteamAPIError(f"Request failed: {str(e)}")
        except ValueError as e:
            raise SteamAPIError(f"Invalid JSON response: {str(e)}")
    
    def login(
        self, 
        username: str, 
        password: str, 
        shared_secret: Optional[str] = None,
        identity_secret: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> Tuple[str, Dict[str, Any]]:
        
            
            
        data = {
            "username": username,
            "password": password
        }
        
        if shared_secret:
            data["sharedSecret"] = shared_secret
            
        if identity_secret:
            data["identitySecret"] = identity_secret

        if session_id:
            data["sessionId"] = session_id
            
        result = self._request("POST", "login", json=data)
        
        if not result.get("success"):
            if result.get("requires2FA"):
                raise SteamAPIError("Требуется 2FA код. Используйте login_with_2fa()")
            raise SteamAPIError("Login failed")
        
        session_data = {
            'sessionId': result["sessionId"],
            'cookies': result.get('cookies', []),
            'identity_secret': result.get('identity_secret', ''),
            'steam_id': result.get('steamID', '')
        }
        
        return result["sessionId"], session_data
    
    def login_with_2fa(
        self,
        username: str,
        password: str,
        two_factor_code: str,
        session_id: Optional[str] = None
    ) -> Tuple[str, Dict[str, Any]]:
        
            
        data = {
            "username": username,
            "password": password,
            "twoFactorCode": two_factor_code
        }
        
        if session_id:
            data["sessionId"] = session_id
        
        result = self._request("POST", "login-2fa", json=data)
        
        if not result.get("success"):
            raise SteamAPIError("Login with 2FA failed")
        
        session_data = {
            'sessionId': result["sessionId"],
            'cookies': result.get('cookies', []),
            'identity_secret': result.get('identity_secret', ''),
            'steam_id': result.get('steamID', '')
        }
        
        return result["sessionId"], session_data
    
    def logout(self, session_id: str) -> bool:
        
            
        result = self._request("POST", "logout", json={"sessionId": session_id})
        return result.get("success", False)
    
    def acknowledge_trade_protection(self, session_id: str) -> Dict[str, Any]:
        
            
        result = self._request("POST", "acknowledge-trade-protection", json={"sessionId": session_id})
        return result
    
    def create_trade(
        self,
        session_id: str,
        partner_steam_id: Optional[str] = None,
        partner_trade_url: Optional[str] = None,
        items_from_me: Optional[List[Dict]] = None,
        items_from_them: Optional[List[Dict]] = None,
        message: Optional[str] = None,
        token: Optional[str] = None
    ) -> Dict[str, Any]:
        
            
            
        data = {
            "sessionId": session_id
        }
        
        if partner_trade_url:
            data["partnerTradeUrl"] = partner_trade_url
        elif partner_steam_id:
            data["partnerSteamId"] = partner_steam_id
        else:
            raise ValueError("Either partner_trade_url or partner_steam_id must be provided")
        
        if items_from_me:
            data["itemsFromMe"] = items_from_me
        
        if items_from_them:
            data["itemsFromThem"] = items_from_them
        
        if message:
            data["message"] = message
        
        if token:
            data["token"] = token
        
        return self._request("POST", "trade/create", json=data)
    
    def get_trade(self, session_id: str, offer_id: str) -> Dict[str, Any]:
        
            
        return self._request("GET", f"trade/{offer_id}", params={"sessionId": session_id})
    
    def accept_trade(self, session_id: str, offer_id: str) -> bool:
        
            
        result = self._request("POST", f"trade/{offer_id}/accept", json={"sessionId": session_id})
        return result.get("success", False)
    
    def decline_trade(self, session_id: str, offer_id: str) -> bool:
        
            
        result = self._request("POST", f"trade/{offer_id}/decline", json={"sessionId": session_id})
        return result.get("success", False)
    
    def cancel_trade(self, session_id: str, offer_id: str) -> bool:
        
            
        result = self._request("POST", f"trade/{offer_id}/cancel", json={"sessionId": session_id})
        return result.get("success", False)
    
    def get_trade_offers(
        self,
        session_id: str,
        filter_type: str = "active"
    ) -> Dict[str, List[Dict]]:
        
            
        return self._request(
            "GET",
            "trade/offers",
            params={"sessionId": session_id, "filter": filter_type}
        )
    
    def get_inventory(
        self,
        session_id: str,
        steam_id: str,
        app_id: int = 730,
        context_id: int = 2
    ) -> Dict[str, Any]:
        
            
        return self._request(
            "GET",
            f"inventory/{steam_id}/{app_id}/{context_id}",
            params={"sessionId": session_id}
        )
    
    def get_trade_url(self, session_id: str) -> Dict[str, str]:
        
            
        return self._request("GET", "trade-url", params={"sessionId": session_id})
    
    def get_wallet_balance(self, session_id: str) -> Dict[str, Any]:
        
            
        return self._request("GET", f"wallet/{session_id}")
    
    def get_incoming_trades(self, session_id: str) -> Dict[str, Any]:
        
            
        return self._request("GET", "trade/incoming", params={"sessionId": session_id})
    
    def auto_accept_trades(self, session_id: str, partner_steam_id: Optional[str] = None, 
                          accept_all: bool = False) -> Dict[str, Any]:
        
            
        data = {
            "sessionId": session_id,
            "acceptAll": accept_all
        }
        
        if partner_steam_id:
            data["partnerSteamId"] = partner_steam_id
        
        return self._request("POST", "trade/auto-accept", json=data)
    
    def accept_sent_trade(self, session_id: str, receiver_session_id: str, offer_id: str) -> Dict[str, Any]:
        
            
        data = {
            "sessionId": session_id,
            "receiverSessionId": receiver_session_id
        }
        
        return self._request("POST", f"trade/accept-sent/{offer_id}", json=data)
    
    def get_confirmations(self, session_id: str) -> Dict[str, Any]:
        
            
        return self._request("GET", f"confirmations/{session_id}")
    
    def confirm_confirmation(self, session_id: str, confirmation_id: str, 
                           confirmation_key: str, accept: bool = True) -> Dict[str, Any]:
        
            
        data = {
            "confirmationKey": confirmation_key,
            "accept": accept
        }
        
        return self._request("POST", f"confirmations/{session_id}/{confirmation_id}", json=data)
    
    def confirm_all_confirmations(self, session_id: str) -> Dict[str, Any]:
        
            
        return self._request("POST", f"confirmations/{session_id}/accept-all")
    
    def __enter__(self):
        self.start_bridge()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop_bridge()
    
    def __del__(self):
        if self.bridge_process and self.bridge_process.poll() is None:
            self.stop_bridge()



def generate_session_id() -> str:
    
    import uuid
    return f"session_{uuid.uuid4().hex}"


class SteamApps:
    CSGO = 730
    TF2 = 440
    DOTA2 = 570
    RUST = 252490
    PUBG = 578080
    
    @staticmethod
    def get_context_id(app_id: int) -> int:
        return 2
