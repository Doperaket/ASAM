import time
import ctypes
from ctypes import wintypes
import psutil
import subprocess
import pyautogui


class SteamWindowDetector:
    
    def __init__(self):
        self.user32 = ctypes.windll.user32
        self.kernel32 = ctypes.windll.kernel32
        
        self.steam_login_titles = [
            "Sign in to Steam",
            "Вход в Steam", 
            "Steam Login",
            "Войти в Steam",
            "Steam - Вход",
            "Steam Guard",
            "Steam - Sign In"
        ]
        
        self.steam_main_titles = [
            "Steam",
            "Friends List", 
            "Список друзей"
        ]
        
        self.steam_exclusions = [
            "acid steam",
            "steam account manager", 
            "manager",
            "sign in",
            "вход",
            "login",
            "guard"
        ]
        
    def get_all_windows(self):
        try:
            import pyautogui
            
            windows = []
            
            try:
                import win32gui
                
                def enum_handler(hwnd, windows):
                    if win32gui.IsWindowVisible(hwnd):
                        title = win32gui.GetWindowText(hwnd)
                        if title:
                            windows.append((hwnd, title))
                    return True
                
                win32gui.EnumWindows(enum_handler, windows)
                return windows
                
            except ImportError:
                return []
                
        except Exception as e:
            print(f"Ошибка получения окон: {e}")
            return []
    
    def find_steam_process(self):
        try:
            for proc in psutil.process_iter(['pid', 'name', 'exe']):
                if proc.info['name'] and 'steam.exe' in proc.info['name'].lower():
                    return proc.info
            return None
        except Exception as e:
            print(f"Ошибка поиска процесса Steam: {e}")
            return None
    
    def is_steam_running(self):
        return self.find_steam_process() is not None
    
    def find_login_window(self):
        try:
            try:
                import win32gui
                
                found_windows = []
                def enum_windows_callback(hwnd, windows):
                    if win32gui.IsWindowVisible(hwnd):
                        window_title = win32gui.GetWindowText(hwnd)
                        if window_title:
                            for login_title in self.steam_login_titles:
                                if login_title.lower() in window_title.lower():
                                    windows.append((hwnd, window_title))
                    return True
                
                win32gui.EnumWindows(enum_windows_callback, found_windows)
                
                if found_windows:
                    hwnd, title = found_windows[0]
                    
                    class WindowWrapper:
                        def __init__(self, hwnd, title):
                            self.hwnd = hwnd
                            self.title = title
                        def activate(self):
                            win32gui.SetForegroundWindow(self.hwnd)
                    
                    return WindowWrapper(hwnd, title), title
                    
            except ImportError:
                print("[ERROR] win32gui недоступен! Это критическая ошибка для exe.")
                return None, None
            except Exception as e:
                print(f"[ERROR] Ошибка при работе с win32gui: {e}")
                return None, None
            
            return None, None
            
        except Exception as e:
            print(f"[ERROR] Критическая ошибка поиска окна входа: {e}")
            return None, None
    
    def find_main_steam_window(self):
        try:
            try:
                import win32gui
                
                found_windows = []
                def enum_windows_callback(hwnd, windows):
                    if win32gui.IsWindowVisible(hwnd):
                        window_title = win32gui.GetWindowText(hwnd)
                        if window_title:
                            for main_title in self.steam_main_titles:
                                if main_title.lower() in window_title.lower():
                                    title_lower = window_title.lower()
                                    is_excluded = any(exclusion in title_lower for exclusion in self.steam_exclusions)
                                    
                                    if not is_excluded:
                                        windows.append((hwnd, window_title))
                    return True
                
                win32gui.EnumWindows(enum_windows_callback, found_windows)
                
                if found_windows:
                    hwnd, title = found_windows[0]
                    class WindowWrapper:
                        def __init__(self, hwnd, title):
                            self.hwnd = hwnd
                            self.title = title
                    
                    return WindowWrapper(hwnd, title), title
                    
            except ImportError:
                print("[ERROR] win32gui недоступен!")
                return None, None
            except Exception as e:
                print(f"[ERROR] Ошибка при поиске главного окна: {e}")
                return None, None
            
            return None, None
        except Exception as e:
            print(f"[ERROR] Критическая ошибка поиска главного окна: {e}")
            return None, None
    
    def wait_for_steam_start(self, timeout=60):
        print("⏳ Ожидаем запуск процесса Steam...")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if self.is_steam_running():
                print("✅ Процесс Steam запущен")
                return True
            time.sleep(0.5)
        
        print("❌ Таймаут ожидания запуска Steam")
        return False
    
    def wait_for_login_window(self, timeout=30):
        print("⏳ Ожидаем появление окна входа Steam...")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            window, title = self.find_login_window()
            if window:
                print(f"✅ Окно входа найдено: '{title}'")
                return window, title
            time.sleep(0.5)
        
        print("❌ Таймаут ожидания окна входа")
        return None, None
    
    def wait_for_main_window(self, timeout=45):
        print("⏳ Ожидаем успешный вход в Steam...")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            login_window, _ = self.find_login_window()
            if not login_window:
                main_window, title = self.find_main_steam_window()
                if main_window:
                    print(f"✅ Вход успешен! Найдено главное окно: '{title}'")
                    return True
            time.sleep(0.5)
        
        print("❌ Таймаут ожидания успешного входа")
        return False
    
    def activate_window(self, window):
        try:
            if hasattr(window, 'hwnd'):
                import win32gui
                win32gui.SetForegroundWindow(window.hwnd)
                return True
            elif hasattr(window, 'activate'):
                window.activate()
                return True
            elif hasattr(window, 'restore') and hasattr(window, 'maximize'):
                window.restore()
                window.activate()
                return True
            
            time.sleep(0.2)
            return True
        except Exception as e:
            print(f"Ошибка активации окна: {e}")
            return False
    
    def is_guard_field_ready(self, login_window):
        try:
            import win32gui
            import win32con
            import ctypes
            from ctypes import wintypes
            
            if not hasattr(login_window, 'hwnd'):
                return False
                
            hwnd = login_window.hwnd
            
            try:
                foreground_window = win32gui.GetForegroundWindow()
                if foreground_window == hwnd:
                    return True
            except:
                pass
            
            return True
            
        except Exception as e:
            return True
    
    def wait_for_guard_field(self, login_window, timeout=10):
        print("⏳ Ожидаем готовность поля для Guard кода...")
        start_time = time.time()
        
        print("⏳ Даем Steam время на обработку логина/пароля...")
        time.sleep(5)
        
        while time.time() - start_time < timeout:
            elapsed = time.time() - start_time
            
            if not self.is_window_exists(login_window):
                print("✅ Окно входа исчезло - возможно вход выполнен!")
                return "logged_in"
            
            main_window, main_title = self.find_main_steam_window()
            if main_window and main_title:
                if "steam" in main_title.lower() and all(exclusion not in main_title.lower() for exclusion in self.steam_exclusions):
                    print(f"✅ Найдено настоящее главное окно Steam - вход выполнен!")
                    return "logged_in"
            
            if elapsed >= 5:
                print("✅ Поле Guard готово для ввода!")
                return "ready"
            
            time.sleep(1)
        
        print("⚠️ Таймаут ожидания Guard поля, продолжаем...")
        return "timeout"
    
    def is_window_exists(self, window):
        try:
            if window is None or not hasattr(window, 'hwnd'):
                return False
                
            import win32gui
            try:
                return win32gui.IsWindow(window.hwnd) and win32gui.IsWindowVisible(window.hwnd)
            except:
                return False
        except:
            return False


class SmartSteamLogin:
    
    def __init__(self):
        self.detector = SteamWindowDetector()
        self.max_retries = 1
        
        self.guard_base_delay = 4.0
        self.guard_max_wait = 5.0
        self.guard_fallback_delay = 2.0
        self.guard_confirm_delay = 0.5
    
    def launch_steam(self, steam_path):
        try:
            print("🚀 Запускаем Steam...")
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            
            subprocess.Popen(steam_path, startupinfo=startupinfo)
            
            if not self.detector.wait_for_steam_start(timeout=30):
                return False, "Процесс Steam не запустился"
            
            return True, "Steam запущен успешно"
            
        except Exception as e:
            return False, f"Ошибка запуска Steam: {e}"
    
    def wait_and_login(self, account, password, shared_secret):
        try:
            from utils.keyboard_utils import safe_type_login, safe_type_password, safe_type_guard_code
            from .generate_2fa import generate_2fa
            import pyautogui
            
            login_hwnd, login_title = self.detector.wait_for_login_window(timeout=45)
            if not login_hwnd:
                return False, "Окно входа не появилось"
            
            if not self.detector.activate_window(login_hwnd):
                return False, "Не удалось активировать окно входа"
            
            print(f"🔑 Начинаем ввод данных в окно: '{login_title}'")
            
            time.sleep(1)
            
            print(f"📝 Вводим логин: {account}")
            if not safe_type_login(account):
                return False, "Ошибка ввода логина"
            
            pyautogui.press('tab')
            time.sleep(0.3)
            
            print("🔒 Вводим пароль")
            if not safe_type_password(password):
                return False, "Ошибка ввода пароля"
            
            pyautogui.press('enter')
            
            print("⏳ Ожидаем готовность поля для Guard кода...")
            guard_status = self.detector.wait_for_guard_field(login_hwnd, timeout=20)
            
            if guard_status == "logged_in":
                print("✅ Вход выполнен без Guard кода!")
                return True, "Быстрый вход без Guard кода"
            elif guard_status == "timeout":
                print("⚠️ Таймаут ожидания Guard поля, пробуем ввести код...")
            
            print("⏳ Дополнительная пауза перед вводом Guard кода...")
            time.sleep(2)
            
            print("🛡️ Генерируем 2FA код...")
            code = generate_2fa(shared_secret)
            print(f"🔐 Вводим 2FA код: {code}")
            
            if not safe_type_guard_code(code):
                return False, "Ошибка ввода 2FA кода"
            
            time.sleep(self.guard_confirm_delay)
            
            print("✅ Подтверждаем Guard код...")
            pyautogui.press('enter')
            
            if self.detector.wait_for_main_window(timeout=30):
                return True, f"Успешный вход! 2FA код: {code}"
            else:
                return False, "Таймаут ожидания входа в систему"
                
        except Exception as e:
            return False, f"Ошибка во время входа: {e}"
    
    def smart_login(self, account, password, shared_secret, steam_path, update_status_callback=None):
        def update_status(message, success=True):
            print(f"{'✅' if success else '❌'} {message}")
            if update_status_callback:
                try:
                    update_status_callback(message)
                except:
                    pass
        
        attempt = 0
        while attempt <= self.max_retries:
            if attempt > 0:
                update_status(f"Повторная попытка входа ({attempt}/{self.max_retries})", False)
            
            try:
                update_status("Подготовка к входу...")
                from core.helpers import clear_steam_auth_data, kill_process
                clear_steam_auth_data()
                kill_process("steam")
                time.sleep(2)
                
                update_status("Запускаем Steam...")
                success, message = self.launch_steam(steam_path)
                if not success:
                    update_status(f"Ошибка запуска: {message}", False)
                    attempt += 1
                    continue
                
                update_status("Ожидаем окно входа...")
                success, message = self.wait_and_login(account, password, shared_secret)
                
                if success:
                    update_status(message, True)
                    return True, message
                else:
                    update_status(f"Ошибка входа: {message}", False)
                    attempt += 1
                    
            except Exception as e:
                error_msg = f"Критическая ошибка: {e}"
                update_status(error_msg, False)
                attempt += 1
        
        final_error = f"Не удалось войти в Steam после {self.max_retries + 1} попыток"
        update_status(final_error, False)
        return False, final_error


smart_steam_login = SmartSteamLogin()