import os
import threading
import time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from .base_tab import BaseTab
from core.settings_manager import settings_manager, get_application_path
from core.helpers import kill_process, login

from ..dialogs import AddAccountDialog, EditAccountDialog, AccountSettingsDialog, ConfirmationsDialog


class AccountsTab(BaseTab):
    
    def __init__(self, notebook, main_window):
        self.account_var = main_window.account_var
        self.status_label = None
        self.accounts_combobox = None
        
        self.steam_guard_timer = None
        
        self.current_login = ""
        self.current_password = ""
        self.current_steamid64 = ""
        self.current_guard_code = ""
        
        self.account_name_label = None
        self.login_display = None
        self.password_display = None
        self.steamid64_display = None
        self.code_display = None
        self.time_progress = None
        self.time_label = None
        self.vac_status_display = None
        self.level_display = None
        self.games_display = None
        self.wallet_display = None
        
        super().__init__(notebook, main_window, "Управление аккаунтами")
    
    def create_interface(self):
        main_paned = ttk.PanedWindow(self.frame, orient="horizontal")
        main_paned.pack(fill="both", expand=True)

        left_panel = ttk.Frame(main_paned)
        main_paned.add(left_panel, weight=1)

        right_panel = ttk.Frame(main_paned)
        main_paned.add(right_panel, weight=1)

        self._create_left_panel(left_panel)
        self._create_right_panel(right_panel)
        
        self.update_account_info()

    def _create_left_panel(self, left_panel):
        login_section = ttk.LabelFrame(left_panel, text="Вход в Steam", padding=15)
        login_section.pack(fill="x", pady=(0, 15))

        ttk.Label(login_section, text="Выберите аккаунт:", 
                 font=("Helvetica", 12)).pack(anchor="w", pady=(0, 5))
        
        self.accounts_combobox = ttk.Combobox(login_section, textvariable=self.account_var, 
                                            state="readonly", font=("Helvetica", 11))
        self.accounts_combobox.pack(fill="x", pady=(0, 15))
        
        self.main_window.accounts_combobox = self.accounts_combobox
        
        self.accounts_combobox.bind("<<ComboboxSelected>>", self.on_account_selected)

        self.status_label = ttk.Label(login_section, text="Выберите аккаунт для входа", 
                                     font=("Helvetica", 10), wraplength=300)
        self.status_label.pack(pady=(0, 15))
        
        self.main_window.status_label = self.status_label

        steam_buttons_frame = ttk.Frame(login_section)
        steam_buttons_frame.pack(fill="x")

        ttk.Button(steam_buttons_frame, text="Войти в Steam", 
                  command=self.start_login,
                  style="primary.TButton", width=18).pack(side="left", padx=(0, 10))

        ttk.Button(steam_buttons_frame, text="Выйти из Steam", 
                  command=self.logout,
                  style="secondary.TButton", width=18).pack(side="left", padx=(0, 10))

        ttk.Button(steam_buttons_frame, text="Обновить список", 
                  command=self.manual_refresh_accounts,
                  style="info.TButton", width=18).pack(side="left")

        management_section = ttk.LabelFrame(left_panel, text="Управление аккаунтами", padding=15)
        management_section.pack(fill="x", pady=(15, 0))

        add_frame = ttk.LabelFrame(management_section, text="Добавление аккаунтов", padding=10)
        add_frame.pack(fill="x", pady=(0, 10))

        add_buttons_frame = ttk.Frame(add_frame)
        add_buttons_frame.pack(fill="x")

        ttk.Button(add_buttons_frame, text="Добавить аккаунт", 
                  command=self.add_single_account,
                  style="success.TButton", width=18).pack(pady=2, fill="x")

        ttk.Button(add_buttons_frame, text="Импорт .maFiles", 
                  command=self.mass_import_mafiles,
                  style="warning.TButton", width=18).pack(pady=2, fill="x")

        ttk.Button(add_buttons_frame, text="Импорт логинов/паролей", 
                  command=self.mass_import_accounts,
                  style="info.TButton", width=18).pack(pady=2, fill="x")

        edit_frame = ttk.LabelFrame(management_section, text="Редактирование аккаунтов", padding=10)
        edit_frame.pack(fill="x")

        edit_buttons_frame = ttk.Frame(edit_frame)
        edit_buttons_frame.pack(fill="x")

        ttk.Button(edit_buttons_frame, text="Редактировать выбранный", 
                  command=self.edit_account,
                  style="secondary.TButton", width=18).pack(pady=2, fill="x")

        ttk.Button(edit_buttons_frame, text="Удалить выбранный", 
                  command=self.delete_account,
                  style="danger.TButton", width=18).pack(pady=2, fill="x")

    def _create_right_panel(self, right_panel):
        account_info_section = ttk.LabelFrame(right_panel, text="Информация об аккаунте", padding=15)
        account_info_section.pack(fill="both", expand=True)

        self._create_account_header(account_info_section)
        self._create_account_details(account_info_section)
        self._create_account_status(account_info_section)
        self._create_steam_guard_section(account_info_section)
        self._create_trade_buttons(account_info_section)

    def _create_account_header(self, parent):
        account_name_frame = ttk.Frame(parent)
        account_name_frame.pack(fill="x", pady=(0, 15))
        
        ttk.Label(account_name_frame, text="Аккаунт:", font=("Helvetica", 11, "bold")).pack(side="left")
        self.account_name_label = ttk.Label(account_name_frame, text="Не выбран", 
                                           font=("Helvetica", 11), foreground="gray")
        self.account_name_label.pack(side="left", padx=(10, 0))
        
        account_buttons_frame = ttk.Frame(account_name_frame)
        account_buttons_frame.pack(side="right")
        
        self.steam_profile_button = ttk.Button(account_buttons_frame, text="🔗", 
                                              command=self.open_steam_profile,
                                              style="info.TButton", width=3)
        self.steam_profile_button.pack(side="right")
        
        self.account_settings_button = ttk.Button(account_buttons_frame, text="⚙️", 
                                                 command=self.open_account_settings,
                                                 style="secondary.TButton", width=3)
        self.account_settings_button.pack(side="right", padx=(0, 5))
        
        self.rename_button = ttk.Button(account_buttons_frame, text="Переименовать", 
                                       command=self.rename_account,
                                       style="secondary.TButton", width=15)
        self.rename_button.pack(side="right")

    def _create_account_details(self, parent):
        login_frame = ttk.Frame(parent)
        login_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(login_frame, text="Логин:", font=("Helvetica", 10, "bold")).pack(side="left")
        self.login_display = ttk.Label(login_frame, text="—", font=("Helvetica", 10))
        self.login_display.pack(side="left", padx=(10, 0))
        
        ttk.Button(login_frame, text="📋", command=self.copy_login,
                  style="info.TButton", width=3).pack(side="right")

        password_frame = ttk.Frame(parent)
        password_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(password_frame, text="Пароль:", font=("Helvetica", 10, "bold")).pack(side="left")
        self.password_display = ttk.Label(password_frame, text="—", font=("Helvetica", 10))
        self.password_display.pack(side="left", padx=(10, 0))
        
        ttk.Button(password_frame, text="📋", command=self.copy_password,
                  style="info.TButton", width=3).pack(side="right")

        steamid_frame = ttk.Frame(parent)
        steamid_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(steamid_frame, text="SteamID64:", font=("Helvetica", 10, "bold")).pack(side="left")
        self.steamid64_display = ttk.Label(steamid_frame, text="—", font=("Helvetica", 10))
        self.steamid64_display.pack(side="left", padx=(10, 0))
        
        ttk.Button(steamid_frame, text="📋", command=self.copy_steamid64,
                  style="info.TButton", width=3).pack(side="right")

    def _create_account_status(self, parent):
        status_frame = ttk.LabelFrame(parent, text="Статус аккаунта", padding=10)
        status_frame.pack(fill="x", pady=(0, 15))

        vac_frame = ttk.Frame(status_frame)
        vac_frame.pack(fill="x", pady=(0, 5))
        
        ttk.Label(vac_frame, text="VAC статус:", font=("Helvetica", 10, "bold")).pack(side="left")
        self.vac_status_display = ttk.Label(vac_frame, text="Неизвестно", font=("Helvetica", 10))
        self.vac_status_display.pack(side="left", padx=(10, 0))

        level_frame = ttk.Frame(status_frame)
        level_frame.pack(fill="x", pady=(0, 5))
        
        ttk.Label(level_frame, text="Уровень:", font=("Helvetica", 10, "bold")).pack(side="left")
        self.level_display = ttk.Label(level_frame, text="Неизвестно", font=("Helvetica", 10))
        self.level_display.pack(side="left", padx=(10, 0))

        games_frame = ttk.Frame(status_frame)
        games_frame.pack(fill="x", pady=(0, 5))
        
        ttk.Label(games_frame, text="Игр:", font=("Helvetica", 10, "bold")).pack(side="left")
        self.games_display = ttk.Label(games_frame, text="Неизвестно", font=("Helvetica", 10))
        self.games_display.pack(side="left", padx=(10, 0))

        wallet_frame = ttk.Frame(status_frame)
        wallet_frame.pack(fill="x", pady=(0, 5))
        
        ttk.Label(wallet_frame, text="Баланс:", font=("Helvetica", 10, "bold")).pack(side="left")
        self.wallet_display = ttk.Label(wallet_frame, text="Неизвестно", font=("Helvetica", 10))
        self.wallet_display.pack(side="left", padx=(10, 0))

        status_buttons_frame = ttk.Frame(status_frame)
        status_buttons_frame.pack(fill="x", pady=(10, 0))
        
        ttk.Button(status_buttons_frame, text="Обновить статус", 
                  command=self.refresh_account_status,
                  style="info.TButton", width=15).pack(side="left", padx=(0, 5))
        
        ttk.Button(status_buttons_frame, text="Очистить кеш", 
                  command=self.clear_status_cache,
                  style="secondary.TButton", width=15).pack(side="left")

    def _create_steam_guard_section(self, parent):
        ttk.Separator(parent, orient="horizontal").pack(fill="x", pady=(0, 15))

        guard_frame = ttk.LabelFrame(parent, text="Steam Guard", padding=10)
        guard_frame.pack(fill="x", pady=(0, 15))

        code_frame = ttk.Frame(guard_frame)
        code_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(code_frame, text="Код:", font=("Helvetica", 12, "bold")).pack(side="left")
        self.code_display = ttk.Label(code_frame, text="—————", 
                                     font=("Helvetica", 16, "bold"), foreground="#00ff00")
        self.code_display.pack(side="left", padx=(10, 0))
        
        guard_buttons_frame = ttk.Frame(code_frame)
        guard_buttons_frame.pack(side="right")
        
        ttk.Button(guard_buttons_frame, text="📋", command=self.copy_guard_code,
                  style="info.TButton", width=3).pack(side="right")

        progress_frame = ttk.Frame(guard_frame)
        progress_frame.pack(fill="x", pady=(0, 5))
        
        ttk.Label(progress_frame, text="Действителен:", font=("Helvetica", 10)).pack(side="left")
        self.time_progress = ttk.Progressbar(progress_frame, length=150, mode='determinate')
        self.time_progress.pack(side="left", padx=(10, 5), fill="x", expand=True)
        
        self.time_label = ttk.Label(progress_frame, text="—", font=("Helvetica", 10))
        self.time_label.pack(side="right")

        ttk.Button(guard_frame, text="Обновить код", 
                  command=self.refresh_steam_guard_code,
                  style="info.TButton").pack(pady=(10, 0))

    def _create_trade_buttons(self, parent):
        guard_frame = parent.winfo_children()[-1]
        
        ttk.Separator(guard_frame, orient="horizontal").pack(fill="x", pady=10)
        
        trades_label = ttk.Label(guard_frame, text="Управление трейдами:", 
                                font=("Helvetica", 10, "bold"))
        trades_label.pack(pady=(5, 10))
        
        ttk.Button(guard_frame, text="Показать подтверждения", 
                  command=self.show_account_confirmations_instant,
                  style="info.TButton").pack(pady=2, fill="x")

        ttk.Button(guard_frame, text="Принять все трейды", 
                  command=self.confirm_all_account_trades,
                  style="success.TButton").pack(pady=2, fill="x")

        ttk.Button(guard_frame, text="Массовое принятие", 
                  command=self.mass_confirm_trades,
                  style="warning.TButton").pack(pady=2, fill="x")


    def on_account_selected(self, event=None):
        self.stop_steam_guard_timer()
        self.update_account_info()
        self.start_steam_guard_timer()

    def update_account_info(self):
        selected_display_name = self.account_var.get()
        
        if not selected_display_name:
            if self.account_name_label:
                self.account_name_label.config(text="Не выбран", foreground="gray")
                self.login_display.config(text="—")
                self.password_display.config(text="—")
                self.steamid64_display.config(text="—")
                self.code_display.config(text="—————")
                self.time_label.config(text="—")
                self.time_progress['value'] = 0
                self.vac_status_display.config(text="Неизвестно", foreground="gray")
                self.level_display.config(text="Неизвестно", foreground="gray")
                self.games_display.config(text="Неизвестно", foreground="gray")
            if self.wallet_display:
                self.wallet_display.config(text="Неизвестно", foreground="gray")
            
            self.current_login = ""
            self.current_password = ""
            self.current_steamid64 = ""
            self.current_guard_code = ""
            return

        selected_account = settings_manager.get_login_by_display_name(selected_display_name)

        if self.account_name_label:
            self.account_name_label.config(text=selected_display_name, foreground="white")
        
        if self.login_display:
            self.login_display.config(text=selected_account)
        self.current_login = selected_account
        
        password = settings_manager.get_account_password(selected_account)
        if password:
            masked_password = "*" * len(password) if len(password) > 0 else "Не задан"
            if self.password_display:
                self.password_display.config(text=masked_password)
            self.current_password = password
        else:
            if self.password_display:
                self.password_display.config(text="Не задан")
            self.current_password = ""
        
        steamid64 = self.get_steamid64_for_account(selected_account)
        if steamid64:
            masked_steamid = "*" * len(steamid64) if len(steamid64) > 0 else "Не найден"
            if self.steamid64_display:
                self.steamid64_display.config(text=masked_steamid)
            self.current_steamid64 = steamid64
        else:
            if self.steamid64_display:
                self.steamid64_display.config(text="Не найден")
            self.current_steamid64 = ""
        
        self.update_account_status_display(selected_account)
        
        self.refresh_steam_guard_code()

    def refresh_accounts(self):
        try:
            display_names_dict = settings_manager.get_account_names_for_display()
            display_names = list(display_names_dict.keys())
            
            if display_names and self.accounts_combobox:
                self.accounts_combobox['values'] = display_names
                current_selection = self.account_var.get()
                current_login = settings_manager.get_login_by_display_name(current_selection)
                
                if current_login in settings_manager.get_accounts():
                    current_display = settings_manager.get_account_display_name(current_login)
                    if current_display in display_names:
                        self.account_var.set(current_display)
                    else:
                        self.account_var.set(display_names[0])
                elif not current_selection and display_names:
                    self.account_var.set(display_names[0])
                    
                self.update_status(f"Загружено аккаунтов: {len(display_names)}")
            else:
                if self.accounts_combobox:
                    self.accounts_combobox['values'] = []
                self.account_var.set("")
                self.update_status("Аккаунты не найдены. Добавьте аккаунт.")
                
        except Exception as e:
            self.update_status(f"Ошибка загрузки аккаунтов: {str(e)}")

    def manual_refresh_accounts(self):
        try:
            discovered = settings_manager.auto_discover_accounts(silent=False)
            self.refresh_accounts()
        except Exception as e:
            self.update_status(f"Ошибка при обновлении: {str(e)}")

    def get_steamid64_for_account(self, account_name):
        try:
            import json
            
            mafiles_dir = os.path.join(get_application_path(), "data", "mafiles")
            if not os.path.exists(mafiles_dir):
                return None
                
            mafile_path = None
            
            potential_paths = [
                os.path.join(mafiles_dir, f"{account_name}.maFile"),
            ]
            
            for path in potential_paths:
                if os.path.exists(path):
                    mafile_path = path
                    break
            
            if not mafile_path:
                for filename in os.listdir(mafiles_dir):
                    if filename.endswith('.maFile'):
                        file_path = os.path.join(mafiles_dir, filename)
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                data = json.load(f)
                                if data.get('account_name') == account_name:
                                    mafile_path = file_path
                                    break
                        except:
                            continue
            
            if mafile_path and os.path.exists(mafile_path):
                with open(mafile_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    steamid = data.get('Session', {}).get('SteamID') or data.get('steamid')
                    return str(steamid) if steamid else None
                    
        except Exception as e:
            print(f"Ошибка получения SteamID64 для {account_name}: {e}")
        
        return None

    
    def refresh_steam_guard_code(self):
        selected_display_name = self.account_var.get()
        
        if not selected_display_name:
            if self.code_display:
                self.code_display.config(text="—————")
                self.time_label.config(text="—")
                self.time_progress['value'] = 0
            return

        selected_account = settings_manager.get_login_by_display_name(selected_display_name)

        try:
            accounts = settings_manager.get_accounts()
            if selected_account not in accounts:
                if self.code_display:
                    self.code_display.config(text="НЕТ MAFILE")
                    self.time_label.config(text="—")
                    self.time_progress['value'] = 0
                return

            mafile_name = accounts[selected_account].get('mafile')
            if not mafile_name:
                if self.code_display:
                    self.code_display.config(text="НЕТ MAFILE")
                    self.time_label.config(text="—")
                    self.time_progress['value'] = 0
                return

            mafile_path = os.path.join(get_application_path(), "data", "mafiles", mafile_name)
            
            print(f"[DEBUG] Генерируем код Guard для: {mafile_name}")
            print(f"[DEBUG] Путь к mafile: {mafile_path}")
            print(f"[DEBUG] Файл существует: {os.path.exists(mafile_path)}")
            
            if not os.path.exists(mafile_path):
                if self.code_display:
                    self.code_display.config(text="ФАЙЛ НЕ НАЙДЕН")
                    self.time_label.config(text="—")
                    self.time_progress['value'] = 0
                return

            from steam.generate_2fa import generate_2fa_code
            
            code, time_remaining = generate_2fa_code(mafile_path)
            
            if code and self.code_display:
                self.code_display.config(text=code, foreground="#00ff00")
                self.update_time_display(time_remaining)
                self.current_guard_code = code
            else:
                if self.code_display:
                    self.code_display.config(text="ОШИБКА", foreground="#ff0000")
                    self.time_label.config(text="—")
                    self.time_progress['value'] = 0
                self.current_guard_code = ""

        except Exception as e:
            print(f"Ошибка генерации 2FA кода: {e}")
            if self.code_display:
                self.code_display.config(text="ОШИБКА", foreground="#ff0000")
                self.time_label.config(text="—")
                self.time_progress['value'] = 0

    def update_time_display(self, time_remaining):
        if time_remaining > 0 and self.time_progress and self.time_label and self.code_display:
            progress_percentage = (time_remaining / 30.0) * 100
            self.time_progress['value'] = progress_percentage
            
            self.time_label.config(text=f"{time_remaining}с")
            
            if time_remaining > 15:
                self.code_display.config(foreground="#00ff00")
            elif time_remaining > 5:
                self.code_display.config(foreground="#ffff00")
            else:
                self.code_display.config(foreground="#ff8000")
        else:
            if self.time_progress and self.time_label:
                self.time_progress['value'] = 0
                self.time_label.config(text="Истек")
            if self.code_display:
                self.code_display.config(foreground="#ff0000")

    def start_steam_guard_timer(self):
        if self.steam_guard_timer:
            self.main_window.root.after_cancel(self.steam_guard_timer)
        
        self.update_steam_guard_timer()

    def update_steam_guard_timer(self):
        selected_display_name = self.account_var.get()
        
        if not selected_display_name:
            return

        try:
            current_time = int(time.time())
            time_remaining = 30 - (current_time % 30)
            
            self.update_time_display(time_remaining)
            
            if time_remaining <= 1:
                self.refresh_steam_guard_code()
                self.steam_guard_timer = self.main_window.root.after(1000, self.update_steam_guard_timer)
            else:
                self.steam_guard_timer = self.main_window.root.after(1000, self.update_steam_guard_timer)
                
        except Exception as e:
            print(f"Ошибка таймера Steam Guard: {e}")
            self.steam_guard_timer = self.main_window.root.after(1000, self.update_steam_guard_timer)

    def stop_steam_guard_timer(self):
        if self.steam_guard_timer:
            self.main_window.root.after_cancel(self.steam_guard_timer)
            self.steam_guard_timer = None

    
    def update_account_status_display(self, login):
        try:
            status = settings_manager.get_account_status(login)
            
            vac_status = status.get('vac_status', 'Неизвестно')
            if self.vac_status_display:
                if vac_status == 'Чистый':
                    self.vac_status_display.config(text=vac_status, foreground="#00ff00")
                elif 'VAC Ban' in vac_status or 'Game Ban' in vac_status or 'Trade Ban' in vac_status:
                    self.vac_status_display.config(text=vac_status, foreground="#ff0000")
                else:
                    self.vac_status_display.config(text=vac_status, foreground="gray")
            
            level = status.get('level', 'Неизвестно')
            if self.level_display:
                if level != 'Неизвестно' and level.isdigit():
                    level_num = int(level)
                    if level_num >= 10:
                        self.level_display.config(text=level, foreground="#00ff00")
                    elif level_num >= 5:
                        self.level_display.config(text=level, foreground="#ffff00")
                    else:
                        self.level_display.config(text=level, foreground="#ff8000")
                else:
                    self.level_display.config(text=level, foreground="gray")
            
            games_count = status.get('games_count', 'Неизвестно')
            if self.games_display:
                if games_count.isdigit():
                    games_num = int(games_count)
                    if games_num >= 100:
                        self.games_display.config(text=games_count, foreground="#00ff00")
                    elif games_num >= 50:
                        self.games_display.config(text=games_count, foreground="#ffff00")
                    elif games_num >= 10:
                        self.games_display.config(text=games_count, foreground="#ff8000")
                    else:
                        self.games_display.config(text=games_count, foreground="gray")
                else:
                    self.games_display.config(text=games_count, foreground="gray")
            
            wallet_balance = status.get('wallet_balance', 'Неизвестно')
            if self.wallet_display:
                if isinstance(wallet_balance, dict):
                    formatted_balance = wallet_balance.get('formatted', f"{wallet_balance.get('balance', 0)} {wallet_balance.get('currency', 'USD')}")
                    balance_value = wallet_balance.get('balance', 0)
                    
                    if balance_value > 0:
                        self.wallet_display.config(text=formatted_balance, foreground="#00ff00")
                    else:
                        self.wallet_display.config(text=formatted_balance, foreground="gray")
                elif wallet_balance and wallet_balance != 'Неизвестно' and wallet_balance != 'Ошибка':
                    self.wallet_display.config(text=wallet_balance, foreground="#00ff00")
                else:
                    self.wallet_display.config(text=wallet_balance, foreground="gray")
                
        except Exception as e:
            print(f"Ошибка обновления статуса: {e}")
            if self.vac_status_display:
                self.vac_status_display.config(text="Ошибка", foreground="red")
            if self.level_display:
                self.level_display.config(text="Ошибка", foreground="red")
            if self.games_display:
                self.games_display.config(text="Ошибка", foreground="red")
            if self.wallet_display:
                self.wallet_display.config(text="Ошибка", foreground="red")

    def refresh_account_status(self):
        selected_display_name = self.account_var.get()
        if not selected_display_name:
            messagebox.showwarning("Предупреждение", "Выберите аккаунт")
            return
        
        if not self.main_window.steam_status_manager:
            messagebox.showwarning("Предупреждение", "Парсер статуса недоступен")
            return
        
        selected_account = settings_manager.get_login_by_display_name(selected_display_name)
        
        def update_thread():
            try:
                self.update_status(f"Обновление статуса для {selected_display_name}...")
                status = self.main_window.steam_status_manager.update_single_account(selected_account)
                
                if status:
                    self.main_window.root.after(0, lambda: self.update_account_status_display(selected_account))
                    self.main_window.root.after(0, lambda: self.update_status(f"Статус {selected_display_name} обновлен"))
                else:
                    self.main_window.root.after(0, lambda: self.update_status(f"Ошибка обновления статуса {selected_display_name}"))
            except Exception as e:
                self.main_window.root.after(0, lambda: self.update_status(f"Ошибка: {e}"))
        
        thread = threading.Thread(target=update_thread)
        thread.daemon = True
        thread.start()

    def clear_status_cache(self):
        if self.main_window.steam_status_manager:
            self.main_window.steam_status_manager.parser.clear_cache()
            self.update_status("Кеш статуса очищен")
        else:
            messagebox.showwarning("Предупреждение", "Парсер статуса недоступен")


    def start_login(self):
        selected_display_name = self.account_var.get()
        if not selected_display_name:
            messagebox.showwarning("Предупреждение", "Выберите аккаунт для входа!")
            return

        selected_account = settings_manager.get_login_by_display_name(selected_display_name)
        self.update_status(f"Вход в аккаунт {selected_display_name}...")
        
        thread = threading.Thread(target=self._login_thread, args=(selected_account,))
        thread.daemon = True
        thread.start()

    def _login_thread(self, account_name):
        try:
            password = settings_manager.get_account_password(account_name)
            if not password:
                self.update_status(f"Пароль для аккаунта {account_name} не найден!")
                return

            accounts = settings_manager.get_accounts()
            if account_name not in accounts:
                self.update_status(f"Аккаунт {account_name} не найден в настройках!")
                return

            mafile_name = accounts[account_name].get('mafile')
            if not mafile_name:
                self.update_status(f"MaFile для аккаунта {account_name} не найден!")
                return

            mafile_path = os.path.join(get_application_path(), "data", "mafiles", mafile_name)
            if not os.path.exists(mafile_path):
                self.update_status(f"Файл {mafile_name} не найден!")
                return
                
            try:
                import json
                with open(mafile_path, 'r', encoding='utf-8') as f:
                    mafile_data = json.load(f)
                shared_secret = mafile_data.get('shared_secret')
                if not shared_secret:
                    self.update_status(f"shared_secret не найден в {mafile_name}!")
                    return
            except Exception as e:
                self.update_status(f"Ошибка чтения {mafile_name}: {e}")
                return

            self.update_status("Подготовка к входу...")
            try:
                login(account_name, password, shared_secret, self.status_label, self.main_window.root)
                self.update_status(f"Успешный вход в аккаунт {account_name}!")
                
            except Exception as e:
                self.update_status(f"Ошибка входа в аккаунт {account_name}: {e}")
                
        except Exception as e:
            self.update_status(f"Ошибка: {str(e)}")

    def logout(self):
        try:
            self.update_status("Принудительное завершение всех Steam процессов...")
            
            steam_processes = [
                "steam",
                "steamwebhelper", 
                "steamservice",
                "steamerrorreporter",
                "gameoverlayui",
                "streaming_client"
            ]
            
            for process in steam_processes:
                try:
                    kill_process(process)
                except:
                    pass
            
            try:
                import subprocess
                
                commands = [
                    "taskkill /f /im steam*.exe /t",
                    "taskkill /f /fi \"IMAGENAME eq steam*\" /t"
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
            except:
                pass
            
            self.update_status("Все Steam процессы принудительно завершены")
        except Exception as e:
            self.update_status(f"Ошибка при выходе: {str(e)}")


    def add_single_account(self):
        from gui.dialogs.add_account_dialog import AddAccountDialog
        dialog = AddAccountDialog(self.main_window.root)
        self.main_window.root.wait_window(dialog.dialog)
        
        if dialog.result:
            self.refresh_accounts()
            if hasattr(self.main_window, 'trade_tab'):
                self.main_window.trade_tab.refresh_trade_accounts()

    def mass_import_mafiles(self):
        folder_path = filedialog.askdirectory(title="Выберите папку с .maFile файлами")
        if not folder_path:
            return

        try:
            imported_count = 0
            for filename in os.listdir(folder_path):
                if filename.lower().endswith('.mafile'):
                    source = os.path.join(folder_path, filename)
                    dest_dir = os.path.join(get_application_path(), "data", "mafiles")
                    os.makedirs(dest_dir, exist_ok=True)
                    dest = os.path.join(dest_dir, filename)
                    
                    import shutil
                    shutil.copy2(source, dest)
                    imported_count += 1
            
            settings_manager.auto_discover_accounts()
            self.refresh_accounts()
            if hasattr(self.main_window, 'trade_tab'):
                self.main_window.trade_tab.refresh_trade_accounts()
            
            self.update_status(f"Импортировано {imported_count} файлов")
            messagebox.showinfo("Импорт завершен", f"Импортировано {imported_count} .maFile файлов")
            
        except Exception as e:
            self.update_status(f"Ошибка импорта: {str(e)}")
            messagebox.showerror("Ошибка", f"Ошибка импорта: {str(e)}")

    def mass_import_accounts(self):
        filename = filedialog.askopenfilename(
            title="Выберите файл с аккаунтами",
            filetypes=[("Текстовые файлы", "*.txt"), ("Все файлы", "*.*")]
        )
        if not filename:
            return

        try:
            imported_count = 0
            with open(filename, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if ':' in line:
                        login, password = line.split(':', 1)
                        settings_manager.set_account_password(login.strip(), password.strip())
                        imported_count += 1
            
            self.refresh_accounts()
            if hasattr(self.main_window, 'trade_tab'):
                self.main_window.trade_tab.refresh_trade_accounts()
            
            self.update_status(f"Импортировано {imported_count} аккаунтов")
            messagebox.showinfo("Импорт завершен", f"Импортировано {imported_count} аккаунтов")
            
        except Exception as e:
            self.update_status(f"Ошибка импорта: {str(e)}")
            messagebox.showerror("Ошибка", f"Ошибка импорта: {str(e)}")

    def edit_account(self):
        selected_account = self.account_var.get()
        if not selected_account:
            messagebox.showwarning("Предупреждение", "Выберите аккаунт для редактирования!")
            return

        from gui.dialogs.edit_account_dialog import EditAccountDialog
        dialog = EditAccountDialog(self.main_window.root, selected_account)
        self.main_window.root.wait_window(dialog.dialog)
        
        if dialog.result:
            self.refresh_accounts()

    def delete_account(self):
        selected_account = self.account_var.get()
        if not selected_account:
            messagebox.showwarning("Предупреждение", "Выберите аккаунт для удаления!")
            return

        if messagebox.askyesno("Подтверждение удаления", 
                              f"Удалить аккаунт {selected_account}?\n\nЭто удалит пароль и .mafile файл."):
            try:
                settings_manager.remove_account_password(selected_account)
                
                accounts = settings_manager.get_accounts()
                if selected_account in accounts:
                    mafile_name = accounts[selected_account].get('mafile')
                    if mafile_name:
                        mafile_path = os.path.join(get_application_path(), "data", "mafiles", mafile_name)
                        if os.path.exists(mafile_path):
                            os.remove(mafile_path)
                
                settings_manager.remove_account(selected_account)
                
                self.refresh_accounts()
                if hasattr(self.main_window, 'trade_tab'):
                    self.main_window.trade_tab.refresh_trade_accounts()
                
                self.update_status(f"Аккаунт {selected_account} удален")
                messagebox.showinfo("Успех", f"Аккаунт {selected_account} удален успешно!")
                
            except Exception as e:
                self.update_status(f"Ошибка удаления: {str(e)}")
                messagebox.showerror("Ошибка", f"Ошибка удаления аккаунта: {str(e)}")

    def rename_account(self):
        selected_display_name = self.account_var.get()
        if not selected_display_name:
            messagebox.showwarning("Предупреждение", "Выберите аккаунт для переименования")
            return
            
        selected_account = settings_manager.get_login_by_display_name(selected_display_name)
        current_display_name = selected_display_name
        
        new_name = tk.simpledialog.askstring(
            "Переименовать аккаунт", 
            f"Введите новое имя для аккаунта '{selected_account}':",
            initialvalue=current_display_name
        )
        
        if new_name is not None and new_name.strip():
            new_name = new_name.strip()
            settings_manager.set_account_display_name(selected_account, new_name)
            self.refresh_accounts()
            if hasattr(self.main_window, 'trade_tab'):
                self.main_window.trade_tab.refresh_trade_accounts()
            
            self.update_account_info()
            self.update_status(f"Аккаунт переименован в '{new_name}'")


    def safe_copy_to_clipboard(self, text):
        try:
            has_cyrillic = any(ord(char) >= 1024 and ord(char) <= 1279 for char in text)
            
            if has_cyrillic:
                import tkinter as tk
                root = tk.Tk()
                root.withdraw()
                root.clipboard_clear()
                root.clipboard_append(text.encode('utf-8').decode('utf-8'))
                root.update()
                root.destroy()
            else:
                import pyperclip
                pyperclip.copy(text)
            
            return True
        except Exception as e:
            print(f"Ошибка копирования: {e}")
            try:
                import pyperclip
                pyperclip.copy(text)
                return True
            except:
                raise e

    def copy_login(self):
        if self.current_login:
            try:
                self.safe_copy_to_clipboard(self.current_login)
                self.update_status(f"Логин '{self.current_login}' скопирован в буфер обмена")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Ошибка копирования логина: {e}")
        else:
            messagebox.showwarning("Предупреждение", "Логин не выбран")

    def copy_password(self):
        if self.current_password:
            try:
                self.safe_copy_to_clipboard(self.current_password)
                self.update_status("Пароль скопирован в буфер обмена")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Ошибка копирования пароля: {e}")
        else:
            messagebox.showwarning("Предупреждение", "Пароль не найден")

    def copy_steamid64(self):
        if self.current_steamid64:
            try:
                self.safe_copy_to_clipboard(self.current_steamid64)
                self.update_status("SteamID64 скопирован в буфер обмена")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Ошибка копирования SteamID64: {e}")
        else:
            messagebox.showwarning("Предупреждение", "SteamID64 не найден")

    def copy_guard_code(self):
        if self.current_guard_code and self.current_guard_code != "—————":
            try:
                self.safe_copy_to_clipboard(self.current_guard_code)
                self.update_status(f"Steam Guard код '{self.current_guard_code}' скопирован в буфер обмена")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Ошибка копирования кода: {e}")
        else:
            messagebox.showwarning("Предупреждение", "Steam Guard код не сгенерирован")


    def show_account_confirmations_instant(self):
        selected_display_name = self.account_var.get()
        if not selected_display_name:
            messagebox.showwarning("Внимание", "Выберите аккаунт")
            return
        
        account_name = None
        for login, data in settings_manager.get_accounts().items():
            display_name = data.get('display_name', login)
            if display_name == selected_display_name:
                account_name = login
                break
        
        if not account_name:
            messagebox.showerror("Ошибка", "Аккаунт не найден")
            return
        
        from gui.dialogs.confirmations_dialog import ConfirmationsDialog
        dialog = ConfirmationsDialog(self.main_window.root, account_name, selected_display_name, self.main_window.trade_manager)

    def confirm_all_account_trades(self):
        selected_display_name = self.account_var.get()
        if not selected_display_name:
            messagebox.showwarning("Внимание", "Выберите аккаунт")
            return
        
        account_name = None
        for login, data in settings_manager.get_accounts().items():
            display_name = data.get('display_name', login)
            if display_name == selected_display_name:
                account_name = login
                break
        
        if not account_name:
            messagebox.showerror("Ошибка", "Аккаунт не найден")
            return
        
        confirm = messagebox.askyesno("Подтверждение", 
                                     f"Подтвердить все трейды для аккаунта {selected_display_name}?")
        if not confirm:
            return
        
        try:
            self.update_status(f"Подтверждение трейдов для {selected_display_name}...")
            
            result = self.main_window.trade_manager.confirm_all_trades(account_name)
            
            if result["success"]:
                confirmed_count = result["confirmed_count"]
                messagebox.showinfo("Успех", f"Подтверждено {confirmed_count} трейдов для {selected_display_name}")
                self.update_status(f"Подтверждено {confirmed_count} трейдов для {selected_display_name}")
            else:
                messagebox.showerror("Ошибка", f"Не удалось подтвердить трейды:\n{result['error']}")
                self.update_status("Ошибка подтверждения трейдов")
                
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка подтверждения трейдов:\n{str(e)}")
            self.update_status("Ошибка подтверждения трейдов")

    def mass_confirm_trades(self):
        accounts = settings_manager.get_accounts()
        if not accounts:
            messagebox.showwarning("Внимание", "Нет доступных аккаунтов")
            return
        
        from ..dialogs import MassTradeConfirmDialog
        dialog = MassTradeConfirmDialog(self.main_window.root, accounts, self.main_window.trade_manager)

    def open_steam_profile(self):
        selected_display_name = self.account_var.get()
        if not selected_display_name or selected_display_name == "Нет аккаунтов":
            messagebox.showwarning("Внимание", "Пожалуйста, выберите аккаунт")
            return
        
        selected_account = settings_manager.get_login_by_display_name(selected_display_name)
        if not selected_account:
            messagebox.showerror("Ошибка", "Аккаунт не найден")
            return
        
        steamid64 = self.get_steamid64_for_account(selected_account)
        if not steamid64:
            messagebox.showerror("Ошибка", "SteamID64 не найден для данного аккаунта")
            return
        
        try:
            profile_url = f"https://steamcommunity.com/profiles/{steamid64}/"
            
            import webbrowser
            webbrowser.open(profile_url)
            
            self.update_status(f"Открыт профиль Steam для аккаунта {selected_display_name}")
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть профиль Steam:\n{str(e)}")

    def open_account_settings(self):
        try:
            selected_display_name = self.account_var.get()
            if not selected_display_name or selected_display_name == "Нет аккаунтов":
                messagebox.showwarning("Внимание", "Пожалуйста, выберите аккаунт для настройки")
                return
            
            selected_account = settings_manager.get_login_by_display_name(selected_display_name)
            if not selected_account:
                messagebox.showerror("Ошибка", "Не удалось найти данные аккаунта")
                return
            
            from gui.dialogs.account_settings_dialog import AccountSettingsDialog
            dialog = AccountSettingsDialog(self.main_window.root, selected_account, selected_display_name)
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка открытия настроек: {str(e)}")

