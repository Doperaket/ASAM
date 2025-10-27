import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from .base_tab import BaseTab
from core.settings_manager import settings_manager


class SettingsTab(BaseTab):
    
    def __init__(self, notebook, main_window):
        self.steam_path_var = tk.StringVar(value=settings_manager.get_steam_path())
        self.action_delay_var = tk.StringVar(value=str(settings_manager.get_action_delay()))
        self.theme_var = tk.StringVar(value=settings_manager.get_theme())
        self.auto_status_var = tk.BooleanVar(value=settings_manager.get_auto_status_enabled())
        self.status_interval_var = tk.StringVar(value=str(settings_manager.get_status_interval()))
        self.app_password_enabled_var = tk.BooleanVar(value=settings_manager.is_app_password_enabled())
        
        super().__init__(notebook, main_window, "Настройки")

    def on_password_enabled_changed(self):
        enabled = self.app_password_enabled_var.get()
        
        if not enabled and settings_manager.is_app_password_enabled():
            from tkinter import messagebox
            if messagebox.askyesno("Отключение пароля", 
                                   "Пароль установлен. Удалить его для отключения защиты?"):
                success, message = settings_manager.remove_app_password()
                if success:
                    self.password_status_label.config(text="✅ Пароль удален", foreground="green")
                else:
                    self.password_status_label.config(text="❌ Ошибка удаления", foreground="red")
                    self.app_password_enabled_var.set(True)
            else:
                self.app_password_enabled_var.set(True)
        
        self.update_password_fields()
    
    def toggle_password_visibility(self):
        if self.show_password_var.get():
            self.password_entry.config(show="")
        else:
            self.password_entry.config(show="*")
    
    def update_password_fields(self):
        enabled = self.app_password_enabled_var.get()
        if enabled:
            self.password_frame.pack(fill="x", pady=(0, 10))
            self.password_entry.config(state="normal")
            self.show_password_btn.config(state="normal")
            self.save_password_btn.config(state="normal")
            if settings_manager.is_app_password_enabled():
                self.remove_password_btn.config(state="normal")
                self.password_status_label.config(text="✅ Пароль установлен", foreground="green")
            else:
                self.remove_password_btn.config(state="disabled")
                self.password_status_label.config(text="❌ Пароль не установлен", foreground="orange")
        else:
            self.password_frame.pack_forget()
    
    def save_password(self):
        password = self.app_password_var.get().strip()
        
        if not password:
            self.password_status_label.config(text="❌ Введите пароль!", foreground="red")
            return
        
        success, message = settings_manager.set_app_password(password)
        
        if success:
            self.password_status_label.config(text="✅ " + message, foreground="green")
            self.app_password_var.set("")
            self.update_password_fields()
        else:
            self.password_status_label.config(text="❌ " + message, foreground="red")
    
    def remove_password(self):
        from tkinter import messagebox
        
        if messagebox.askyesno("Подтверждение", "Вы уверены, что хотите удалить пароль?"):
            success, message = settings_manager.remove_app_password()
            
            if success:
                self.password_status_label.config(text="✅ " + message, foreground="green")
                self.app_password_var.set("")
                self.update_password_fields()
            else:
                self.password_status_label.config(text="❌ " + message, foreground="red")

    def create_interface(self):
        steam_frame = ttk.LabelFrame(self.frame, text="Путь к Steam", padding=10)
        steam_frame.pack(fill="x", pady=(0, 15))

        steam_path_frame = ttk.Frame(steam_frame)
        steam_path_frame.pack(fill="x")

        steam_entry = ttk.Entry(steam_path_frame, textvariable=self.steam_path_var, 
                               font=("Helvetica", 10))
        steam_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        ttk.Button(steam_path_frame, text="Автопоиск", 
                  command=self.auto_find_steam).pack(side="right")

        delay_frame = ttk.LabelFrame(self.frame, text="Задержка между действиями", padding=10)
        delay_frame.pack(fill="x", pady=(0, 15))

        delay_inner_frame = ttk.Frame(delay_frame)
        delay_inner_frame.pack(fill="x")
        
        delay_entry = ttk.Entry(delay_inner_frame, textvariable=self.action_delay_var, 
                               width=10, font=("Helvetica", 10))
        delay_entry.pack(side="left", padx=(0, 5))
        
        ttk.Label(delay_inner_frame, text="секунд", 
                 font=("Helvetica", 10)).pack(side="left", padx=(0, 10))
        
        ttk.Label(delay_inner_frame, text="(время ожидания между кликами и вводом)", 
                 font=("Helvetica", 9), foreground="gray").pack(side="left")

        interface_frame = ttk.LabelFrame(self.frame, text="Настройки интерфейса", padding=10)
        interface_frame.pack(fill="x", pady=(0, 15))

        theme_frame = ttk.Frame(interface_frame)
        theme_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(theme_frame, text="Тема:", font=("Helvetica", 10)).pack(side="left")
        
        theme_combo = ttk.Combobox(theme_frame, textvariable=self.theme_var, 
                                  values=["darkly", "flatly", "cosmo", "journal", "litera", "lumen", "minty", "pulse", "sandstone", "united", "yeti"],
                                  state="readonly", width=15)
        theme_combo.pack(side="left", padx=(10, 10))
        
        ttk.Button(theme_frame, text="Применить тему", 
                  command=self.apply_theme,
                  style="info.TButton").pack(side="left")

        steam_status_frame = ttk.LabelFrame(self.frame, text="Steam статус", padding=10)
        steam_status_frame.pack(fill="x", pady=(0, 15))

        ttk.Checkbutton(steam_status_frame, text="Автоматически получать статус VAC аккаунтов",
                       variable=self.auto_status_var,
                       style="info.TCheckbutton").pack(anchor="w", pady=(0, 10))

        status_interval_frame = ttk.Frame(steam_status_frame)
        status_interval_frame.pack(fill="x")
        
        ttk.Label(status_interval_frame, text="Интервал обновления:", 
                 font=("Helvetica", 10)).pack(side="left")
        
        interval_entry = ttk.Entry(status_interval_frame, textvariable=self.status_interval_var, 
                                  width=5, font=("Helvetica", 10))
        interval_entry.pack(side="left", padx=(10, 5))
        
        ttk.Label(status_interval_frame, text="минут", 
                 font=("Helvetica", 10)).pack(side="left", padx=(0, 10))
        
        ttk.Label(status_interval_frame, text="(как часто обновлять статус аккаунтов)", 
                 font=("Helvetica", 9), foreground="gray").pack(side="left")

        security_frame = ttk.LabelFrame(self.frame, text="Безопасность", padding=10)
        security_frame.pack(fill="x", pady=(0, 15))

        self.app_password_enabled_var = tk.BooleanVar(value=settings_manager.is_app_password_enabled())
        ttk.Checkbutton(security_frame, text="Защитить приложение паролем",
                       variable=self.app_password_enabled_var,
                       command=self.on_password_enabled_changed,
                       style="info.TCheckbutton").pack(anchor="w", pady=(0, 10))

        self.password_frame = ttk.Frame(security_frame)
        self.password_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(self.password_frame, text="Пароль приложения:", 
                 font=("Helvetica", 10)).pack(anchor="w")
        
        password_input_frame = ttk.Frame(self.password_frame)
        password_input_frame.pack(fill="x", pady=(5, 0))
        
        self.app_password_var = tk.StringVar()
        self.password_entry = ttk.Entry(password_input_frame, textvariable=self.app_password_var,
                                       show="*", font=("Helvetica", 10), width=20)
        self.password_entry.pack(side="left", padx=(0, 10))
        
        self.show_password_var = tk.BooleanVar()
        self.show_password_btn = ttk.Checkbutton(password_input_frame, text="Показать",
                                                variable=self.show_password_var,
                                                command=self.toggle_password_visibility)
        self.show_password_btn.pack(side="left")
        
        password_button_frame = ttk.Frame(self.password_frame)
        password_button_frame.pack(fill="x", pady=(10, 0))
        
        self.save_password_btn = ttk.Button(password_button_frame, text="Сохранить пароль",
                                          command=self.save_password,
                                          style="success.TButton", width=18)
        self.save_password_btn.pack(side="left", padx=(0, 10))
        
        self.remove_password_btn = ttk.Button(password_button_frame, text="Удалить пароль",
                                            command=self.remove_password,
                                            style="danger.TButton", width=18)
        self.remove_password_btn.pack(side="left")
        
        self.password_status_label = ttk.Label(self.password_frame, text="", 
                                              font=("Helvetica", 9))
        self.password_status_label.pack(anchor="w", pady=(5, 0))
        
        self.update_password_fields()

        export_frame = ttk.LabelFrame(self.frame, text="Экспорт/Импорт данных", padding=10)
        export_frame.pack(fill="x", pady=(15, 0))

        export_buttons_frame = ttk.Frame(export_frame)
        export_buttons_frame.pack(fill="x")

        ttk.Button(export_buttons_frame, text="Экспорт аккаунтов", 
                  command=self.export_accounts,
                  style="info.TButton", width=18).pack(side="left", padx=(0, 10))

        ttk.Button(export_buttons_frame, text="Экспорт настроек", 
                  command=self.export_settings,
                  style="info.TButton", width=18).pack(side="left", padx=(0, 10))

        ttk.Button(export_buttons_frame, text="Импорт настроек", 
                  command=self.import_settings,
                  style="warning.TButton", width=18).pack(side="left")

        settings_buttons_frame = ttk.Frame(self.frame)
        settings_buttons_frame.pack(fill="x", pady=(20, 0))

        ttk.Button(settings_buttons_frame, text="Сохранить настройки", 
                  command=self.save_settings,
                  style="primary.TButton").pack(side="left", padx=(0, 10))

        ttk.Button(settings_buttons_frame, text="Сбросить настройки", 
                  command=self.reset_settings,
                  style="danger.TButton").pack(side="left")

    def auto_find_steam(self):
        self.update_status("Поиск Steam...")
        steam_path = settings_manager.find_steam_automatically()
        if steam_path:
            self.steam_path_var.set(steam_path)
            self.update_status(f"Steam найден: {steam_path}")
        else:
            self.update_status("Steam не найден автоматически")
            messagebox.showwarning("Steam не найден", "Steam не найден автоматически. Укажите путь вручную.")

    def save_settings(self):
        try:
            settings_manager.set_steam_path(self.steam_path_var.get())
            
            delay = float(self.action_delay_var.get())
            settings_manager.set_action_delay(delay)
            
            settings_manager.set_theme(self.theme_var.get())
            
            settings_manager.set_auto_status_enabled(self.auto_status_var.get())
            
            interval = int(self.status_interval_var.get())
            settings_manager.set_status_interval(interval)
            
            
            self.update_status("Настройки сохранены")
            messagebox.showinfo("Успех", "Настройки сохранены успешно!")
            
        except ValueError as e:
            if "delay" in str(e):
                messagebox.showerror("Ошибка", "Неверное значение задержки. Введите число.")
            else:
                messagebox.showerror("Ошибка", "Неверное значение интервала. Введите число.")
        except Exception as e:
            self.update_status(f"Ошибка сохранения: {str(e)}")
            messagebox.showerror("Ошибка", f"Ошибка сохранения настроек: {str(e)}")

    def apply_theme(self):
        try:
            new_theme = self.theme_var.get()
            settings_manager.set_theme(new_theme)
            
            messagebox.showinfo("Смена темы", 
                              f"Тема '{new_theme}' будет применена при следующем запуске программы.")
            self.update_status(f"Тема изменена на '{new_theme}' (требуется перезапуск)")
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка применения темы: {str(e)}")

    def reset_settings(self):
        if messagebox.askyesno("Подтверждение", "Сбросить все настройки к значениям по умолчанию?"):
            try:
                settings_manager.reset_settings()
                self.steam_path_var.set(settings_manager.get_steam_path())
                self.action_delay_var.set(str(settings_manager.get_action_delay()))
                self.theme_var.set(settings_manager.get_theme())
                self.auto_status_var.set(settings_manager.get_auto_status_enabled())
                self.status_interval_var.set(str(settings_manager.get_status_interval()))
                self.main_window.refresh_accounts()
                self.update_status("Настройки сброшены")
                messagebox.showinfo("Успех", "Настройки сброшены к значениям по умолчанию")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Ошибка сброса настроек: {str(e)}")

    def export_accounts(self):
        filename = filedialog.asksaveasfilename(
            title="Сохранить аккаунты",
            defaultextension=".txt",
            filetypes=[("Текстовые файлы", "*.txt"), ("Все файлы", "*.*")]
        )
        if not filename:
            return

        try:
            accounts = settings_manager.get_accounts()
            exported_count = 0
            with open(filename, 'w', encoding='utf-8') as f:
                for login, account_data in accounts.items():
                    password = settings_manager.get_account_password(login)
                    if password:
                        f.write(f"{login}:{password}\n")
                        exported_count += 1
                    else:
                        f.write(f"{login}:[НЕТ_ПАРОЛЯ]\n")
                        exported_count += 1
            self.update_status(f"Экспортировано {exported_count} аккаунтов")
            messagebox.showinfo("Экспорт завершен", f"Экспортировано {exported_count} аккаунтов в файл:\n{filename}")
        except Exception as e:
            self.update_status(f"Ошибка экспорта: {str(e)}")
            messagebox.showerror("Ошибка", f"Ошибка экспорта аккаунтов: {str(e)}")

    def export_settings(self):
        filename = filedialog.asksaveasfilename(
            title="Сохранить настройки",
            defaultextension=".json",
            filetypes=[("JSON файлы", "*.json"), ("Все файлы", "*.*")]
        )
        if not filename:
            return

        try:
            import json
            import datetime
            
            export_data = {
                "export_info": {
                    "app_name": "AcidSAM - Steam Account Manager",
                    "version": "2.2",
                    "export_date": datetime.datetime.now().isoformat(),
                    "description": "Резервная копия настроек AcidSAM"
                },
                "settings": settings_manager.settings.copy()
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            self.update_status("Настройки экспортированы")
            messagebox.showinfo("Экспорт завершен", f"Настройки сохранены в файл:\n{filename}")
            
        except Exception as e:
            self.update_status(f"Ошибка экспорта настроек: {str(e)}")
            messagebox.showerror("Ошибка", f"Ошибка экспорта настроек: {str(e)}")

    def import_settings(self):
        filename = filedialog.askopenfilename(
            title="Выберите файл настроек",
            filetypes=[("JSON файлы", "*.json"), ("Все файлы", "*.*")]
        )
        if not filename:
            return

        if not messagebox.askyesno("Подтверждение импорта", 
                                  "Импорт настроек заменит текущие настройки.\n\nПродолжить?"):
            return

        try:
            import json
            import datetime
            
            with open(filename, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            if "settings" in import_data:
                settings_data = import_data["settings"]
                app_info = import_data.get("export_info", {})
                source_app = app_info.get("app_name", "Неизвестно")
            else:
                settings_data = import_data
                source_app = "Неизвестно"
            
            backup_filename = f"settings_backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(backup_filename, 'w', encoding='utf-8') as f:
                json.dump(settings_manager.settings, f, indent=2, ensure_ascii=False)
            
            settings_manager.settings = settings_data
            settings_manager.save_settings()
            
            self.steam_path_var.set(settings_manager.get_steam_path())
            self.action_delay_var.set(str(settings_manager.get_action_delay()))
            self.main_window.refresh_accounts()
            
            self.update_status("Настройки импортированы")
            messagebox.showinfo("Импорт завершен", 
                              f"Настройки импортированы из: {source_app}\n\n"
                              f"Резервная копия сохранена как: {backup_filename}")
            
        except Exception as e:
            self.update_status(f"Ошибка импорта настроек: {str(e)}")
            messagebox.showerror("Ошибка", f"Ошибка импорта настроек: {str(e)}")
