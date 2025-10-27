import json
import os
import time
import subprocess

import pyautogui

try:
    import pyperclip
except ImportError:
    pyperclip = None
    print("Warning: pyperclip не установлен, использование буфера обмена недоступно")

try:
    from colorama import Fore
except ImportError:
    class Fore:
        RED = ""
        GREEN = ""
        BLUE = ""
        CYAN = ""
        YELLOW = ""

from .settings_manager import get_steam_path, get_accounts_dir, get_delay, settings_manager
from steam.generate_2fa import generate_2fa


def load_mafile(account_name):
    accounts_dir = get_accounts_dir()
    path = os.path.join(accounts_dir, f"{account_name}.mafile")
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"{Fore.RED}❌ Ошибка при загрузке {path}: {e}")
        raise


def load_accounts():
    return settings_manager.settings.get("account_passwords", {})


def find_mafile_accounts():
    accounts_data = settings_manager.get_all_accounts_with_passwords()
    account_names = [acc['login'] for acc in accounts_data]
    print(f"{Fore.BLUE}[DEBUG] Найдено аккаунтов: {len(account_names)}")
    return account_names


def kill_process(name):
    print(f"{Fore.GREEN}[INFO] Принудительно закрываем процесс: {name}.exe")
    
    commands = [
        f"taskkill /f /im {name}.exe /t",
        f"taskkill /f /im {name} /t", 
        f"wmic process where \"name='{name}.exe'\" delete",
        f"pskill -f {name}.exe"
    ]
    
    for cmd in commands:
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            
            subprocess.run(cmd, shell=True, startupinfo=startupinfo, 
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except:
            pass
    
    time.sleep(0.5)


def clear_steam_auth_data():
    steam_path = get_steam_path()
    print(f"{Fore.GREEN}[INFO] Очищаем данные авторизации Steam...")
    kill_process("steam")
    
    if not steam_path or steam_path == r"Ваш путь до steam.exe":
        print(f"{Fore.YELLOW}[WARNING] Путь к Steam не настроен, пропускаем очистку кэша")
        return
        
    loginusers_path = os.path.join(os.path.dirname(steam_path), "config", "loginusers.vdf")
    try:
        if os.path.exists(loginusers_path):
            os.remove(loginusers_path)
            print(f"{Fore.GREEN}[INFO] Удален файл: {loginusers_path}")
        else:
            print(f"{Fore.GREEN}[INFO] Файл {loginusers_path} не найден")
    except Exception as e:
        print(f"{Fore.RED}[ERROR] Ошибка при удалении loginusers.vdf: {e}")
    cache_path = os.path.join(os.path.dirname(steam_path), "appcache")
    try:
        if os.path.exists(cache_path):
            for item in os.listdir(cache_path):
                item_path = os.path.join(cache_path, item)
                if os.path.isfile(item_path):
                    os.remove(item_path)
                    print(f"{Fore.GREEN}[INFO] Удален файл кэша: {item_path}")
    except Exception as e:
        print(f"{Fore.RED}[ERROR] Ошибка при очистке кэша: {e}")


def login(account, password, shared_secret, status_label, root):
    try:
        from steam.smart_steam_login import smart_steam_login
        
        steam_path = get_steam_path()
        
        if not steam_path or steam_path == r"Ваш путь до steam.exe":
            error_msg = "❌ Путь к Steam не настроен! Настройте его во вкладке 'Настройки'"
            try:
                status_label.config(text=error_msg)
            except:
                pass
            print(f"{Fore.RED}{error_msg}")
            return
            
        def update_status_gui(text):
            try:
                status_label.config(text=text)
                root.update_idletasks()
            except:
                pass
        
        print(f"{Fore.CYAN}🔐 Начинаем умный вход в аккаунт: {account}")
        
        success, message = smart_steam_login.smart_login(
            account=account,
            password=password, 
            shared_secret=shared_secret,
            steam_path=steam_path,
            update_status_callback=update_status_gui
        )
        
        if success:
            final_message = f"✅ {message}"
            update_status_gui(final_message)
            print(f"{Fore.GREEN}{final_message}")
        else:
            final_message = f"❌ {message}"
            update_status_gui(final_message)
            print(f"{Fore.RED}{final_message}")
            kill_process("steam")
        
    except Exception as e:
        error_msg = f"❌ Критическая ошибка: {str(e)}"
        try:
            status_label.config(text=error_msg)
        except:
            pass
        print(f"{Fore.RED}{error_msg}")
        kill_process("steam")
