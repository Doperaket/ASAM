import os
import sys
import pyperclip
from utils.hardware_id import get_hardware_id
import tkinter as tk
from tkinter import ttk, messagebox
from ttkbootstrap import Window

from core.settings_manager import settings_manager, get_application_path
from core.helpers import kill_process, login
from pysda import SimpleTradeManager

from .tabs.accounts_tab import AccountsTab
from .tabs.settings_tab import SettingsTab
from .tabs.trade_tab import TradeTab
from .tabs.automation_tab import AutomationTab
from .tabs.experimental_tab import ExperimentalTab

from .managers.auto_confirmation_manager import AutoConfirmationManager


class SteamAutoLoginGUI:
    def __init__(self):
        saved_theme = settings_manager.get_theme()
        
        self.root = Window(title="AcidSAM (v2)", themename=saved_theme)
        self.root.geometry("1200x900")
        self.root.resizable(True, True)
        
        self.set_window_icon(self.root)
        
        self.account_var = tk.StringVar()
        self.status_label = None
        self.accounts_combobox = None
        
        self.steam_guard_timer = None
        
        self.current_login = ""
        self.current_password = ""
        self.current_steamid64 = ""
        self.current_guard_code = ""
        
        self.steam_status_manager = None
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.initialize_keyboard()
        
        self.trade_manager = SimpleTradeManager()
        
        self.automation_manager = None
        self.automation_running = False
        self.automation_settings = None
        
        self.tabs = {}
        self.data_loaded = False

        self.create_interface()

    def set_window_icon(self, window):
        try:
            possible_paths = [
                os.path.join(get_application_path(), "assets", "logo.ico"),
                os.path.join(os.path.dirname(__file__), "..", "assets", "logo.ico"),
                "assets/logo.ico",
                "./assets/logo.ico"
            ]
            
            icon_path = None
            for path in possible_paths:
                if os.path.exists(path):
                    icon_path = path
                    break
            
            if icon_path:
                window.iconbitmap(icon_path)
            else:
                print("[DEBUG] Иконка не найдена ни по одному из путей")
        except:
            pass
    
    def get_icon_path(self):
        try:
            icon_path = os.path.join(get_application_path(), "assets", "logo.ico")
            if os.path.exists(icon_path):
                return icon_path
        except:
            pass
        return None

    def initialize_keyboard(self):
        try:
            from utils.keyboard_utils import initialize_keyboard
            initialize_keyboard()
        except Exception as e:
            print(f"⚠️ Ошибка инициализации клавиатуры: {e}")

    def create_interface(self):
        if settings_manager.is_app_password_enabled():
            self.create_login_interface()
        else:
            self.create_main_interface()
    
    def create_login_interface(self):
        self.login_frame = ttk.Frame(self.root, padding=50)
        self.login_frame.pack(expand=True, fill="both")

        title_label = ttk.Label(self.login_frame, text="🔐 AcidSAM (v2)", 
                               font=("Helvetica", 20, "bold"))
        title_label.pack(pady=(0, 30))

        desc_label = ttk.Label(self.login_frame, text="Введите пароль для входа в приложение:",
                              font=("Helvetica", 12))
        desc_label.pack(pady=(0, 20))

        password_frame = ttk.Frame(self.login_frame)
        password_frame.pack(pady=(0, 30))

        ttk.Label(password_frame, text="Пароль:", font=("Helvetica", 11)).pack(anchor="w")
        
        self.login_password_var = tk.StringVar()
        self.login_password_entry = ttk.Entry(password_frame, textvariable=self.login_password_var, 
                                             show="*", font=("Helvetica", 14), width=25)
        self.login_password_entry.pack(pady=(5, 10))
        
        self.login_status_label = ttk.Label(password_frame, text="", 
                                           font=("Helvetica", 10), foreground="red")
        self.login_status_label.pack()

        button_frame = ttk.Frame(self.login_frame)
        button_frame.pack()

        ttk.Button(button_frame, text="Войти", 
                  command=self.on_password_login,
                  style="success.TButton", width=15).pack(side="left", padx=(0, 10))
        
        ttk.Button(button_frame, text="Выход", 
                  command=self.root.quit, width=15).pack(side="left")

        self.login_password_entry.bind("<Return>", lambda e: self.on_password_login())
        
        self.root.after(100, self.login_password_entry.focus_set)

    def on_password_login(self):
        password = self.login_password_var.get()
        
        if not password:
            self.login_status_label.config(text="Введите пароль!")
            return
        
        if settings_manager.verify_app_password(password):
            self.login_frame.destroy()
            self.create_main_interface()
        else:
            self.login_status_label.config(text="Неверный пароль!")
            self.login_password_var.set("")
            self.login_password_entry.focus_set()

    def create_main_interface(self):
        main_frame = ttk.Frame(self.root, padding=20)
        main_frame.pack(expand=True, fill="both")

        title_label = ttk.Label(main_frame, text="AcidSAM (v2)", 
                               font=("Helvetica", 18, "bold"))
        title_label.pack(pady=(0, 20))

        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(expand=True, fill="both", pady=(0, 10))

        self.create_tabs()
        
        if not self.data_loaded:
            self.load_initial_data()
            self.data_loaded = True

    def create_tabs(self):
        self.tabs['accounts'] = AccountsTab(self.notebook, self)
        
        self.tabs['settings'] = SettingsTab(self.notebook, self)
        
        self.tabs['trade'] = TradeTab(self.notebook, self)
        self.trade_tab = self.tabs['trade']  
        
        self.tabs['automation'] = AutomationTab(self.notebook, self)
        
        self.tabs['experimental'] = ExperimentalTab(self.notebook, self)

    def load_initial_data(self):
        self.refresh_accounts()
        self.initialize_steam_status_manager()

    def initialize_steam_status_manager(self):
        try:
            from steam.steam_status_parser import SteamStatusManager
            self.steam_status_manager = SteamStatusManager(settings_manager)
            
            if settings_manager.get_auto_status_enabled():
                self.steam_status_manager.start_auto_update()
                self.update_status("Автоматическое обновление статуса запущено")
        except Exception as e:
            print(f"⚠️ Ошибка инициализации парсера статуса: {e}")
            self.steam_status_manager = None

    def refresh_accounts(self):
        if 'accounts' in self.tabs:
            self.tabs['accounts'].refresh_accounts()

    def update_status(self, message):
        if self.status_label:
            self.status_label.config(text=message)
        print(message)

    def start_global_automation(self, settings):
        try:
            if self.automation_manager:
                self.automation_manager.stop()
            
            self.automation_manager = AutoConfirmationManager(settings, self.update_automation_status)
            self.automation_settings = settings
            
            if self.automation_manager.start():
                self.automation_running = True
                self.update_automation_tab_status()
                return True
            return False
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось запустить автоматизацию: {e}")
            return False

    def stop_global_automation(self):
        try:
            if self.automation_manager:
                self.automation_manager.stop()
                self.automation_manager = None
            
            self.automation_running = False
            self.automation_settings = None
            self.update_automation_tab_status()
            return True
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка остановки автоматизации: {e}")
            return False

    def update_automation_status(self, message):
        if 'experimental' in self.tabs:
            self.tabs['experimental'].update_stats(f"[АВТО] {message}")
        self.update_automation_tab_status()

    def update_automation_tab_status(self):
        if 'automation' in self.tabs:
            self.tabs['automation'].update_status(self.automation_running, self.automation_settings)

    def on_closing(self):
        if self.steam_status_manager:
            self.steam_status_manager.stop_auto_update()
        
        if self.automation_manager:
            print("🛑 Остановка автоматизации перед закрытием...")
            self.automation_manager.stop()
        
        self.root.destroy()

    def cleanup(self):
        try:
            if hasattr(self, 'automation_tab') and hasattr(self.automation_tab, 'cleanup'):
                self.automation_tab.cleanup()
                
            from core.settings_manager import settings_manager
            settings_manager.save_settings()
            
            print("Ресурсы очищены")
        except Exception as e:
            print(f"Ошибка при очистке ресурсов: {e}")

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = SteamAutoLoginGUI()
    app.run()
