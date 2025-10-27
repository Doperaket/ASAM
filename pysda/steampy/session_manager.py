
import argparse
import json
from pysda.utils.logger_setup import logger
import os
import sys
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, Any
import signal
import getpass
import traceback

import requests
from cryptography.fernet import Fernet
try:
    import keyring  # type: ignore
except ImportError:
    keyring = None

from .client import SteamClient
from .guard import generate_one_time_code, load_steam_guard
from .models import SteamUrl


class SecureSessionManager:
    
    def __init__(self, username: str, check_interval: int = 300):
        self.username = username
        self.check_interval = check_interval
        self.running = False
        self.client: Optional[SteamClient] = None
        self.monitor_thread: Optional[threading.Thread] = None
        self.last_check = datetime.now()
        
        self._setup_logging()
        
        self.data_dir = Path.home() / ".steampy" / "sessions"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.encryption_key = self._get_or_create_encryption_key()
        
    def _setup_logging(self):
        pass
    
    def _get_or_create_encryption_key(self) -> bytes:
        try:
            if keyring:
                key_str = keyring.get_password("steampy_session_manager", f"{self.username}_encryption_key")
                if key_str:
                    return key_str.encode()
                
                key = Fernet.generate_key()
                keyring.set_password("steampy_session_manager", f"{self.username}_encryption_key", key.decode())
                self.logger.info("Создан новый ключ шифрования")
                return key
            else:
                key = Fernet.generate_key()
                self.logger.info("Keyring недоступен, используется временный ключ")
                return key
            
        except Exception as e:
            self.logger.warning(f"Не удалось использовать системное хранилище ключей: {e}")
            key_file = self.data_dir / f"{self.username}.key"
            if key_file.exists():
                return key_file.read_bytes()
            
            key = Fernet.generate_key()
            key_file.write_bytes(key)
            key_file.chmod(0o600)
            return key
    
    def _encrypt_data(self, data: Dict[str, Any]) -> bytes:
        fernet = Fernet(self.encryption_key)
        json_data = json.dumps(data, default=str).encode()
        return fernet.encrypt(json_data)
    
    def _decrypt_data(self, encrypted_data: bytes) -> Dict[str, Any]:
        fernet = Fernet(self.encryption_key)
        json_data = fernet.decrypt(encrypted_data)
        return json.loads(json_data.decode())
    
    def _save_session_secure(self, session_data: Dict[str, Any]) -> None:
        try:
            session_file = self.data_dir / f"{self.username}.session"
            encrypted_data = self._encrypt_data({
                'cookies': session_data,
                'timestamp': datetime.now().isoformat(),
                'username': self.username
            })
            
            session_file.write_bytes(encrypted_data)
            session_file.chmod(0o600)
            self.logger.info("Сессия сохранена безопасно")
            
        except Exception as e:
            self.logger.error(f"Ошибка сохранения сессии: {e}")
    
    def _load_session_secure(self) -> Optional[Dict[str, Any]]:
        try:
            session_file = self.data_dir / f"{self.username}.session"
            if not session_file.exists():
                return None
            
            encrypted_data = session_file.read_bytes()
            data = self._decrypt_data(encrypted_data)
            
            session_time = datetime.fromisoformat(data['timestamp'])
            if datetime.now() - session_time > timedelta(hours=24):
                self.logger.warning("Сессия устарела (>24 часов)")
                return None
            
            return data['cookies']
            
        except Exception as e:
            self.logger.error(f"Ошибка загрузки сессии: {e}")
            return None
    
    def _get_credentials(self) -> tuple[str, str, str]:
        try:
            if keyring:
                password = keyring.get_password("steampy", f"{self.username}_password")
                api_key = keyring.get_password("steampy", f"{self.username}_api_key")
                guard_path = keyring.get_password("steampy", f"{self.username}_guard_path")
            else:
                return None, None, None
            
            if not all([password, api_key, guard_path]):
                raise ValueError("Credentials не найдены в системном хранилище")
            
            return password, api_key, guard_path
            
        except Exception as e:
            self.logger.error(f"Ошибка получения credentials: {e}")
            raise
    
    def store_credentials(self, password: str, api_key: str, guard_path: str) -> None:
        try:
            if keyring:
                keyring.set_password("steampy", f"{self.username}_password", password)
                keyring.set_password("steampy", f"{self.username}_api_key", api_key)
                keyring.set_password("steampy", f"{self.username}_guard_path", guard_path)
                self.logger.info("Credentials сохранены в системном хранилище")
            else:
                self.logger.warning("Keyring недоступен, credentials не сохранены")
            
        except Exception as e:
            self.logger.error(f"Ошибка сохранения credentials: {e}")
            raise
    
    def is_session_valid(self) -> bool:
        if not self.client:
            return False
        
        try:
            response = self.client._session.get(
                SteamUrl.COMMUNITY_URL,
                timeout=10,
                headers={'User-Agent': 'Steam Client'}
            )
            
            is_valid = (
                response.status_code == 200 and 
                self.username.lower() in response.text.lower()
            )
            
            if is_valid:
                self.logger.debug("Сессия актуальна")
            else:
                self.logger.warning("Сессия неактуальна")
            
            return is_valid
            
        except Exception as e:
            self.logger.error(f"Ошибка проверки сессии: {e}")
            return False
    
    def login(self, force_refresh: bool = False) -> bool:
        try:
            password, api_key, guard_path = self._get_credentials()
            
            session_data = None if force_refresh else self._load_session_secure()
            
            self.client = SteamClient(
                api_key=api_key,
                username=self.username,
                password=password,
                steam_guard=guard_path
            )
            
            if session_data:
                for name, value in session_data.items():
                    self.client._session.cookies[name] = value
                
                if self.is_session_valid():
                    self.logger.info("Сессия восстановлена из сохраненных данных")
                    return True
            
            self.logger.info("Создание новой сессии...")
            self.client.login_if_need_to()
            
            cookies = self.client._session.cookies.get_dict()
            self._save_session_secure(cookies)
            
            self.logger.info("Успешный вход в Steam")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка входа в Steam: {e}")
            return False
    
    def get_2fa_code(self) -> Optional[str]:
        try:
            _, _, guard_path = self._get_credentials()
            guard_data = load_steam_guard(guard_path)
            code = generate_one_time_code(guard_data['shared_secret'])
            self.logger.info("2FA код сгенерирован")
            return code
            
        except Exception as e:
            self.logger.error(f"Ошибка генерации 2FA кода: {e}")
            return None
    
    def get_current_cookies(self) -> Optional[Dict[str, str]]:
        if not self.client:
            session_data = self._load_session_secure()
            return session_data if session_data else None
        
        return self.client._session.cookies.get_dict()
    
    def refresh_session(self) -> bool:
        self.logger.info("Принудительное обновление сессии...")
        return self.login(force_refresh=True)
    
    def _monitor_session(self) -> None:
        while self.running:
            try:
                if not self.is_session_valid():
                    self.logger.warning("Сессия неактуальна, обновляем...")
                    if self.login():
                        self.logger.info("Сессия обновлена")
                    else:
                        self.logger.error("Не удалось обновить сессию")
                
                self.last_check = datetime.now()
                
                for _ in range(self.check_interval):
                    if not self.running:
                        break
                    time.sleep(1)
                    
            except Exception as e:
                self.logger.error(f"Ошибка в мониторинге сессии: {e}")
                time.sleep(60)
    
    def start_monitoring(self) -> None:
        if self.running:
            self.logger.warning("Мониторинг уже запущен")
            return
        
        if not self.login():
            raise RuntimeError("Не удалось войти в Steam")
        
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_session, daemon=True)
        self.monitor_thread.start()
        self.logger.info(f"Мониторинг сессии запущен (интервал: {self.check_interval}с)")
    
    def stop_monitoring(self) -> None:
        if not self.running:
            return
        
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        
        self.logger.info("Мониторинг сессии остановлен")
    
    def get_status(self) -> Dict[str, Any]:
        return {
            'username': self.username,
            'running': self.running,
            'check_interval': self.check_interval,
            'last_check': self.last_check.isoformat() if self.last_check else None,
            'session_valid': self.is_session_valid() if self.client else False,
            'has_saved_session': self._load_session_secure() is not None
        }


def create_cli() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Steam Session Manager - Безопасное управление Steam сессиями",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  %(prog)s --username myuser --setup-credentials
  %(prog)s --username myuser --get-2fa
  %(prog)s --username myuser --get-cookies
  %(prog)s --username myuser --refresh
  %(prog)s --username myuser --monitor --interval 300
  %(prog)s --username myuser --status
        """)
    
    parser.add_argument('--username', '-u', required=True, help='Steam username')
    parser.add_argument('--setup-credentials', action='store_true', help='Setup encrypted credentials')
    parser.add_argument('--get-2fa', action='store_true', help='Get 2FA code')
    parser.add_argument('--get-cookies', action='store_true', help='Get session cookies')
    parser.add_argument('--refresh', action='store_true', help='Refresh session')
    parser.add_argument('--monitor', action='store_true', help='Monitor session')
    parser.add_argument('--status', action='store_true', help='Check session status')
    parser.add_argument('--interval', '-i', type=int, default=300, help='Monitor interval in seconds')
    
    return parser    
    
    
    
    
    
    
    
    


    
        
        
        




    
    
        
        
            
                
                
                
            
            
                
                
            


