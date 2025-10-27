import os
import json
import string
import sys


def get_application_path():
    if getattr(sys, 'frozen', False):
        application_path = os.path.dirname(sys.executable)
    else:
        application_path = os.path.dirname(os.path.abspath(__file__))
        application_path = os.path.dirname(application_path)
    
    return application_path


def debug_log(message):
    pass


class SettingsManager:
    def __init__(self):
        self.base_path = get_application_path()
        
        debug_log(f"=== Инициализация SettingsManager ===")
        debug_log(f"Базовый путь: {self.base_path}")
        debug_log(f"Запущено как exe: {getattr(sys, 'frozen', False)}")
        
        self.settings_file = os.path.join(self.base_path, "config", "settings.json")
        
        self.default_settings = {
            "steam_path": "",
            "accounts_dir": os.path.join(self.base_path, "data", "mafiles"),
            "accounts_file": os.path.join(self.base_path, "config", "accounts.txt"),
            "delay": 5,
            "auto_search_enabled": True,
            "account_passwords": {},
            "account_display_names": {},
            "theme": "darkly",
            "auto_status_enabled": False,
            "status_interval": 30,
            "account_status": {},
            "trade_links": {},
            "trade_protection_acknowledged": {}
        }
        
        debug_log(f"Файл настроек: {self.settings_file}")
        debug_log(f"Папка аккаунтов: {self.default_settings['accounts_dir']}")
        
        self._ensure_directories()
        
        self.settings = self.load_settings()
        self._ensure_accounts_dir()

    def _ensure_directories(self):
        directories = [
            os.path.join(self.base_path, "config"),
            os.path.join(self.base_path, "data"),
            os.path.join(self.base_path, "data", "mafiles"),
            os.path.join(self.base_path, "data", "sessions"),
        ]
        
        print(f"[DEBUG] Базовый путь приложения: {self.base_path}")
        
        for directory in directories:
            try:
                os.makedirs(directory, exist_ok=True)
                print(f"[DEBUG] Создана/проверена папка: {directory}")
            except Exception as e:
                print(f"[ERROR] Ошибка создания папки {directory}: {e}")

    def load_settings(self):
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    merged_settings = self.default_settings.copy()
                    merged_settings.update(settings)
                    return merged_settings
            except Exception as e:
                print(f"Ошибка при загрузке настроек: {e}")
        
        return self._migrate_from_old_config()

    def _migrate_from_old_config(self):
        settings = self.default_settings.copy()
        
        possible_files = [
            settings["accounts_file"],
            "logpass.txt"
        ]
        
        for accounts_file in possible_files:
            if os.path.exists(accounts_file):
                try:
                    with open(accounts_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            line = line.strip()
                            if ':' in line and not line.startswith('#') and line:
                                login, password = line.split(':', 1)
                                settings["account_passwords"][login.strip()] = password.strip()
                    print(f"✅ Пароли мигрированы из {accounts_file}")
                    break
                except Exception as e:
                    print(f"Ошибка при миграции паролей из {accounts_file}: {e}")
        
        return settings

    def save_settings(self):
        try:
            debug_log(f"=== save_settings ===")
            debug_log(f"Файл настроек: {self.settings_file}")
            
            config_dir = os.path.dirname(self.settings_file)
            os.makedirs(config_dir, exist_ok=True)
            
            debug_log(f"Папка config создана/проверена: {config_dir}")
            debug_log(f"Папка config существует: {os.path.exists(config_dir)}")
            
            print(f"[DEBUG] Сохраняем настройки в: {self.settings_file}")
            print(f"[DEBUG] Папка существует: {os.path.exists(config_dir)}")
            
            debug_log(f"Количество аккаунтов для сохранения: {len(self.settings.get('account_passwords', {}))}")
            
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=4, ensure_ascii=False)
            
            debug_log(f"Файл записан успешно")
            debug_log(f"Размер файла: {os.path.getsize(self.settings_file)} байт")
            
            print(f"[DEBUG] Настройки сохранены успешно")
            return True
        except Exception as e:
            debug_log(f"ОШИБКА сохранения: {e}")
            debug_log(f"Тип ошибки: {type(e).__name__}")
            
            print(f"[ERROR] Ошибка при сохранении настроек: {e}")
            print(f"[ERROR] Путь к файлу: {self.settings_file}")
            print(f"[ERROR] Базовый путь: {self.base_path}")
            import traceback
            traceback.print_exc()
            return False

    def _ensure_accounts_dir(self):
        accounts_dir = self.settings["accounts_dir"]
        os.makedirs(accounts_dir, exist_ok=True)

    def get_steam_path(self):
        if self.settings["steam_path"] and os.path.exists(self.settings["steam_path"]):
            return self.settings["steam_path"]
        
        if self.settings["auto_search_enabled"]:
            steam_path = self.find_steam_automatically()
            if steam_path:
                self.settings["steam_path"] = steam_path
                self.save_settings()
                return steam_path
        
        return self.settings["steam_path"]

    def find_steam_automatically(self):
        print("Ищем Steam автоматически...")
        
        possible_paths = [
            "Program Files (x86)\\Steam\\steam.exe",
            "Program Files\\Steam\\steam.exe", 
            "Steam\\steam.exe",
            "Games\\Steam\\steam.exe"
        ]
        
        drives = [f"{d}:\\" for d in string.ascii_uppercase if os.path.exists(f"{d}:\\")]
        
        for drive in drives:
            print(f"Ищем на диске {drive}")
            for path in possible_paths:
                full_path = os.path.join(drive, path)
                if os.path.exists(full_path):
                    print(f"Steam найден: {full_path}")
                    return full_path
        
        print("Steam не найден автоматически")
        return None

    def get_accounts_dir(self):
        accounts_dir = self.settings["accounts_dir"]
        
        try:
            if not os.path.exists(accounts_dir):
                os.makedirs(accounts_dir, exist_ok=True)
                debug_log(f"Папка аккаунтов создана: {accounts_dir}")
                print(f"[DEBUG] Папка аккаунтов создана: {accounts_dir}")
        except Exception as e:
            debug_log(f"ОШИБКА создания папки аккаунтов {accounts_dir}: {e}")
            print(f"[ERROR] Ошибка создания папки аккаунтов {accounts_dir}: {e}")
            
        return accounts_dir

    def get_accounts_file(self):
        return self.settings["accounts_file"]

    def get_delay(self):
        return self.settings["delay"]

    def get_action_delay(self):
        return self.get_delay()

    def set_action_delay(self, delay):
        return self.set_delay(delay)

    def set_steam_path(self, path):
        self.settings["steam_path"] = path
        return self.save_settings()

    def set_accounts_dir(self, path):
        old_path = self.settings["accounts_dir"]
        self.settings["accounts_dir"] = path
        os.makedirs(path, exist_ok=True)
        success = self.save_settings()
        
        if success and old_path != path:
            self.auto_discover_accounts()
        
        return success

    def set_accounts_file(self, filename):
        self.settings["accounts_file"] = filename
        return self.save_settings()

    def set_delay(self, delay):
        self.settings["delay"] = delay
        return self.save_settings()

    def set_auto_search(self, enabled):
        self.settings["auto_search_enabled"] = enabled
        return self.save_settings()

    def auto_discover_accounts(self, silent=False):
        accounts_dir = self.get_accounts_dir()
        discovered_accounts = []
        
        debug_log(f"=== auto_discover_accounts ===")
        debug_log(f"Ищем аккаунты в папке: {accounts_dir}")
        debug_log(f"Папка существует: {os.path.exists(accounts_dir)}")
        
        try:
            if os.path.exists(accounts_dir):
                files_in_dir = os.listdir(accounts_dir)
                debug_log(f"Файлы в папке: {files_in_dir}")
                
                for filename in files_in_dir:
                    debug_log(f"Проверяем файл: {filename}")
                    if filename.lower().endswith('.mafile'):
                        debug_log(f"Найден maFile: {filename}")
                        account_name = os.path.splitext(filename)[0]
                        
                        try:
                            mafile_path = os.path.join(accounts_dir, filename)
                            debug_log(f"Читаем maFile: {mafile_path}")
                            
                            with open(mafile_path, 'r', encoding='utf-8') as f:
                                mafile_data = json.load(f)
                                
                            login = None
                            if 'account_name' in mafile_data:
                                login = mafile_data['account_name']
                            elif 'AccountName' in mafile_data:
                                login = mafile_data['AccountName']
                            elif 'Steam' in mafile_data and 'Username' in mafile_data['Steam']:
                                login = mafile_data['Steam']['Username']
                            else:
                                login = account_name
                            
                            debug_log(f"Логин из maFile: {login}")
                            
                            discovered_accounts.append({
                                'filename': filename,
                                'account_name': account_name,
                                'login': login,
                                'has_password': login in self.settings["account_passwords"]
                            })
                            
                            debug_log(f"Аккаунт добавлен: {login} (пароль: {login in self.settings['account_passwords']})")
                            
                        except Exception as e:
                            debug_log(f"ОШИБКА при чтении {filename}: {e}")
                            print(f"Ошибка при чтении {filename}: {e}")
                            discovered_accounts.append({
                                'filename': filename,
                                'account_name': account_name,
                                'login': account_name,
                                'has_password': account_name in self.settings["account_passwords"]
                            })
                            debug_log(f"Аккаунт добавлен (имя файла): {account_name}")
            
            debug_log(f"ИТОГО обнаружено аккаунтов: {len(discovered_accounts)}")
            for acc in discovered_accounts:
                debug_log(f"  - {acc['login']} (файл: {acc['filename']}, пароль: {acc['has_password']})")
            
            if not silent:
                print(f"Обнаружено аккаунтов: {len(discovered_accounts)}")
            return discovered_accounts
            
        except Exception as e:
            debug_log(f"ОШИБКА в auto_discover_accounts: {e}")
            print(f"Ошибка при автообнаружении аккаунтов: {e}")
            return []

    def get_account_password(self, login):
        return self.settings["account_passwords"].get(login, "")

    def set_account_password(self, login, password):
        debug_log(f"=== set_account_password ===")
        debug_log(f"Логин: {login}")
        debug_log(f"Пароль задан: {bool(password)}")
        
        print(f"[DEBUG] Устанавливаем пароль для аккаунта: {login}")
        self.settings["account_passwords"][login] = password
        
        debug_log(f"Пароль добавлен в настройки")
        debug_log(f"Всего аккаунтов в настройках: {len(self.settings['account_passwords'])}")
        
        result = self.save_settings()
        debug_log(f"Результат сохранения: {result}")
        
        print(f"[DEBUG] Результат сохранения пароля: {result}")
        return result

    def remove_account_password(self, login):
        if login in self.settings["account_passwords"]:
            del self.settings["account_passwords"][login]
            return self.save_settings()
        return True

    def get_all_accounts_with_passwords(self):
        discovered = self.auto_discover_accounts(silent=True)
        return discovered

    def get_accounts(self):
        discovered = self.auto_discover_accounts(silent=True)
        accounts_dict = {}
        for account in discovered:
            login = account.get('login', account.get('account_name', ''))
            accounts_dict[login] = {
                'mafile': account.get('filename', ''),
                'has_password': account.get('has_password', False)
            }
        return accounts_dict

    def remove_account(self, login):
        if login in self.settings["account_passwords"]:
            del self.settings["account_passwords"][login]
        return self.save_settings()

    def add_account(self, login, mafile_name):
        self.auto_discover_accounts()
        return self.save_settings()

    def get_account_display_name(self, login):
        display_names = self.settings.get("account_display_names", {})
        return display_names.get(login, login)

    def set_account_display_name(self, login, display_name):
        if "account_display_names" not in self.settings:
            self.settings["account_display_names"] = {}
        
        if display_name == login:
            if login in self.settings["account_display_names"]:
                del self.settings["account_display_names"][login]
        else:
            self.settings["account_display_names"][login] = display_name
        
        return self.save_settings()

    def get_account_names_for_display(self):
        accounts = self.get_accounts()
        display_names = {}
        
        for login in accounts.keys():
            display_name = self.get_account_display_name(login)
            display_names[display_name] = login
        
        return display_names

    def get_login_by_display_name(self, display_name):
        display_names = self.get_account_names_for_display()
        return display_names.get(display_name, display_name)

    def get_theme(self):
        return self.settings.get("theme", "darkly")

    def set_theme(self, theme):
        self.settings["theme"] = theme
        return self.save_settings()

    def get_auto_status_enabled(self):
        return self.settings.get("auto_status_enabled", False)

    def set_auto_status_enabled(self, enabled):
        self.settings["auto_status_enabled"] = enabled
        return self.save_settings()

    def get_status_interval(self):
        return self.settings.get("status_interval", 30)

    def set_status_interval(self, interval):
        self.settings["status_interval"] = interval
        return self.save_settings()

    def get_account_status(self, login):
        account_status = self.settings.get("account_status", {})
        return account_status.get(login, {
            "vac_status": "Неизвестно",
            "last_update": None
        })

    def set_account_status(self, login, status_data=None, vac_status=None, level=None, games_count=None):
        if "account_status" not in self.settings:
            self.settings["account_status"] = {}
        
        if login not in self.settings["account_status"]:
            self.settings["account_status"][login] = {}
        
        import datetime
        current_time = datetime.datetime.now().isoformat()
        
        if status_data and isinstance(status_data, dict):
            for key, value in status_data.items():
                if key != 'last_update':
                    self.settings["account_status"][login][key] = value
        else:
            if vac_status is not None:
                self.settings["account_status"][login]["vac_status"] = vac_status
            if level is not None:
                self.settings["account_status"][login]["level"] = level
            if games_count is not None:
                self.settings["account_status"][login]["games_count"] = games_count
        
        self.settings["account_status"][login]["last_update"] = current_time
        return self.save_settings()

    def reset_settings(self):
        return self.reset_to_defaults()

    def reset_to_defaults(self):
        passwords_backup = self.settings.get("account_passwords", {})
        display_names_backup = self.settings.get("account_display_names", {})
        
        self.settings = self.default_settings.copy()
        self.settings["account_passwords"] = passwords_backup
        self.settings["account_display_names"] = display_names_backup
        
        return self.save_settings()

    def is_app_password_enabled(self):
        return bool(self.settings.get("app_password_hash")) and bool(self.settings.get("app_password_salt"))
    
    def set_app_password(self, password):
        if not password or len(password.strip()) < 3:
            return False, "Пароль должен содержать минимум 3 символа"
        
        import hashlib
        import secrets
        
        salt = secrets.token_hex(16)
        password_hash = hashlib.sha256((password + salt).encode('utf-8')).hexdigest()
        
        self.settings["app_password_hash"] = password_hash
        self.settings["app_password_salt"] = salt
        
        success = self.save_settings()
        return success, "Пароль успешно установлен" if success else "Ошибка сохранения пароля"
    
    def verify_app_password(self, password):
        if not self.is_app_password_enabled():
            return True
        
        import hashlib
        
        stored_hash = self.settings.get("app_password_hash")
        salt = self.settings.get("app_password_salt")
        
        if not stored_hash or not salt:
            return False
        
        password_hash = hashlib.sha256((password + salt).encode('utf-8')).hexdigest()
        
        return password_hash == stored_hash
    
    def remove_app_password(self):
        if "app_password_hash" in self.settings:
            del self.settings["app_password_hash"]
        if "app_password_salt" in self.settings:
            del self.settings["app_password_salt"]
        
        success = self.save_settings()
        return success, "Пароль успешно удален" if success else "Ошибка удаления пароля"

    def get_trade_links(self):
        return self.settings.get("trade_links", {})
    
    def add_trade_link(self, name, url):
        if "trade_links" not in self.settings:
            self.settings["trade_links"] = {}
        
        self.settings["trade_links"][name] = url
        return self.save_settings()
    
    def remove_trade_link(self, name):
        if "trade_links" in self.settings and name in self.settings["trade_links"]:
            del self.settings["trade_links"][name]
            return self.save_settings()
        return False
    
    def update_trade_link(self, old_name, new_name, new_url):
        if "trade_links" not in self.settings:
            self.settings["trade_links"] = {}
        
        if old_name != new_name and old_name in self.settings["trade_links"]:
            del self.settings["trade_links"][old_name]
        
        self.settings["trade_links"][new_name] = new_url
        return self.save_settings()
    
    def get_trade_link(self, name):
        return self.settings.get("trade_links", {}).get(name)
    
    def is_trade_protection_acknowledged(self, account_name):
        trade_protection = self.settings.get("trade_protection_acknowledged", {})
        return trade_protection.get(account_name, False)
    
    def set_trade_protection_acknowledged(self, account_name, acknowledged=True):
        if "trade_protection_acknowledged" not in self.settings:
            self.settings["trade_protection_acknowledged"] = {}
        
        self.settings["trade_protection_acknowledged"][account_name] = acknowledged
        self.save_settings()
    
    def get_trade_protection_status(self):
        return self.settings.get("trade_protection_acknowledged", {})


settings_manager = SettingsManager()

def get_steam_path():
    return settings_manager.get_steam_path()

def get_accounts_dir():
    return settings_manager.get_accounts_dir()

def get_accounts_file():
    return settings_manager.get_accounts_file()

def get_delay():
    return settings_manager.get_delay()
