import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
from datetime import datetime


class AutomationDialog:
    
    def __init__(self, parent, accounts, update_callback, main_gui=None):
        self.parent = parent
        self.accounts = accounts
        self.update_callback = update_callback
        self.main_gui = main_gui  
        
        if main_gui and hasattr(main_gui, 'automation_running'):
            self.running = main_gui.automation_running
            print(f"🔄 Диалог автоматизации: получено состояние running={self.running}")
        else:
            self.running = False
            print("⚠️ Диалог автоматизации: главное GUI недоступно, running=False")
        
        self.automation_manager = None
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Автоматизация подтверждений")
        self.dialog.geometry("800x700")
        self.dialog.resizable(True, True)
        
        from . import set_dialog_icon
        set_dialog_icon(self.dialog)
        
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self.dialog.geometry("+%d+%d" % (parent.winfo_rootx() + 50, parent.winfo_rooty() + 50))
        
        self.create_interface()
        
        self.dialog.protocol("WM_DELETE_WINDOW", self.on_close)
    
    def create_interface(self):
        canvas = tk.Canvas(self.dialog)
        scrollbar = ttk.Scrollbar(self.dialog, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        title_frame = ttk.Frame(scrollable_frame)
        title_frame.pack(fill="x", padx=20, pady=(20, 10))
        
        ttk.Label(title_frame, text="Автоматизация подтверждений Steam Guard", 
                 font=("Arial", 16, "bold")).pack()
        ttk.Label(title_frame, text="Настройте параметры автоматического подтверждения трейдов", 
                 font=("Arial", 10), foreground="gray").pack()
        
        global_frame = ttk.LabelFrame(scrollable_frame, text="🌐 Глобальные настройки", padding=15)
        global_frame.pack(fill="x", padx=20, pady=10)
        
        interval_frame = ttk.Frame(global_frame)
        interval_frame.pack(fill="x", pady=5)
        
        ttk.Label(interval_frame, text="Интервал проверки (сек):").pack(side="left")
        self.interval_var = tk.StringVar(value="300")  
        interval_spinbox = ttk.Spinbox(interval_frame, from_=60, to=3600, width=10, 
                                      textvariable=self.interval_var)
        interval_spinbox.pack(side="right")
        
        ttk.Label(global_frame, text="💡 Рекомендуется: 60-300 секунд (чтобы не превысить лимиты Steam API)", 
                 font=("Arial", 9), foreground="orange").pack(anchor="w", pady=(0, 10))
        
        attempts_frame = ttk.Frame(global_frame)
        attempts_frame.pack(fill="x", pady=5)
        
        ttk.Label(attempts_frame, text="Максимум попыток на подтверждение:").pack(side="left")
        self.attempts_var = tk.StringVar(value="3")
        attempts_spinbox = ttk.Spinbox(attempts_frame, from_=1, to=10, width=10,
                                      textvariable=self.attempts_var)
        attempts_spinbox.pack(side="right")
        
        ttk.Label(global_frame, text="ℹ️ Количество повторных попыток при ошибке подтверждения", 
                 font=("Arial", 9), foreground="gray").pack(anchor="w", pady=(0, 10))
        
        self.autostart_var = tk.BooleanVar()
        ttk.Checkbutton(global_frame, text="Автоматически запускать при старте приложения",
                       variable=self.autostart_var).pack(anchor="w", pady=5)
        
        self.notifications_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(global_frame, text="Показывать уведомления о подтверждениях",
                       variable=self.notifications_var).pack(anchor="w", pady=5)
        
        types_frame = ttk.LabelFrame(scrollable_frame, text="🎯 Типы подтверждений", padding=15)
        types_frame.pack(fill="x", padx=20, pady=10)
        
        self.accept_trades_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(types_frame, text="✅ Принимать трейды",
                       variable=self.accept_trades_var).pack(anchor="w", pady=2)
        
        self.accept_gifts_var = tk.BooleanVar(value=True)  
        ttk.Checkbutton(types_frame, text="🎁 Принимать подарки",
                       variable=self.accept_gifts_var).pack(anchor="w", pady=2)
        
        self.accept_market_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(types_frame, text="🛒 Принимать маркет листинги", 
                       variable=self.accept_market_var).pack(anchor="w", pady=2)
        
        accounts_frame = ttk.LabelFrame(scrollable_frame, text="👥 Аккаунты для автоматизации", padding=15)
        accounts_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        list_controls = ttk.Frame(accounts_frame)
        list_controls.pack(fill="x", pady=(0, 10))
        
        ttk.Button(list_controls, text="✅ Выбрать все", 
                  command=self.select_all_accounts).pack(side="left", padx=(0, 5))
        ttk.Button(list_controls, text="❌ Снять все", 
                  command=self.deselect_all_accounts).pack(side="left", padx=5)
        
        list_frame = ttk.Frame(accounts_frame)
        list_frame.pack(fill="both", expand=True)
        
        headers_frame = ttk.Frame(list_frame)
        headers_frame.pack(fill="x", pady=(0, 5))
        
        ttk.Label(headers_frame, text="Включить", width=10).pack(side="left", padx=5)
        ttk.Label(headers_frame, text="Логин", width=20).pack(side="left", padx=5)
        ttk.Label(headers_frame, text="Статус", width=15).pack(side="left", padx=5)
        ttk.Label(headers_frame, text="Последняя проверка", width=20).pack(side="left", padx=5)
        
        accounts_list_frame = ttk.Frame(list_frame)
        accounts_list_frame.pack(fill="both", expand=True)
        
        accounts_canvas = tk.Canvas(accounts_list_frame, height=200)
        accounts_scrollbar = ttk.Scrollbar(accounts_list_frame, orient="vertical", 
                                         command=accounts_canvas.yview)
        self.accounts_scrollable_frame = ttk.Frame(accounts_canvas)
        
        self.accounts_scrollable_frame.bind(
            "<Configure>",
            lambda e: accounts_canvas.configure(scrollregion=accounts_canvas.bbox("all"))
        )
        
        accounts_canvas.create_window((0, 0), window=self.accounts_scrollable_frame, anchor="nw")
        accounts_canvas.configure(yscrollcommand=accounts_scrollbar.set)
        
        def on_accounts_mousewheel(event):
            accounts_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        def bind_accounts_mousewheel(event):
            accounts_canvas.bind_all("<MouseWheel>", on_accounts_mousewheel)
        
        def unbind_accounts_mousewheel(event):
            accounts_canvas.unbind_all("<MouseWheel>")
        
        accounts_canvas.bind('<Enter>', bind_accounts_mousewheel)
        accounts_canvas.bind('<Leave>', unbind_accounts_mousewheel)
        self.accounts_scrollable_frame.bind('<Enter>', bind_accounts_mousewheel)
        self.accounts_scrollable_frame.bind('<Leave>', unbind_accounts_mousewheel)
        
        self.account_vars = {}
        for account_name, account_data in self.accounts.items():
            account_frame = ttk.Frame(self.accounts_scrollable_frame)
            account_frame.pack(fill="x", pady=2)
            
            var = tk.BooleanVar()
            self.account_vars[account_name] = var
            
            checkbox = ttk.Checkbutton(account_frame, variable=var, width=10)
            checkbox.pack(side="left", padx=5)
            
            label1 = ttk.Label(account_frame, text=account_name, width=20)
            label1.pack(side="left", padx=5)
            
            label2 = ttk.Label(account_frame, text="Готов", width=15, foreground="green")
            label2.pack(side="left", padx=5)
            
            label3 = ttk.Label(account_frame, text="Не проверялся", width=20, foreground="gray")
            label3.pack(side="left", padx=5)
            
            def bind_to_accounts_mousewheel(widget):
                widget.bind('<Enter>', bind_accounts_mousewheel)
                widget.bind('<Leave>', unbind_accounts_mousewheel)
            
            bind_to_accounts_mousewheel(account_frame)
            bind_to_accounts_mousewheel(checkbox)
            bind_to_accounts_mousewheel(label1)
            bind_to_accounts_mousewheel(label2)
            bind_to_accounts_mousewheel(label3)
        
        accounts_canvas.pack(side="left", fill="both", expand=True)
        accounts_scrollbar.pack(side="right", fill="y")
        
        status_frame = ttk.LabelFrame(scrollable_frame, text="📊 Статус автоматизации", padding=15)
        status_frame.pack(fill="x", padx=20, pady=10)
        
        self.status_label = ttk.Label(status_frame, text="Остановлена", foreground="red")
        self.status_label.pack(anchor="w")
        
        self.stats_label = ttk.Label(status_frame, text="Подтверждений обработано: 0", foreground="gray")
        self.stats_label.pack(anchor="w")
        
        buttons_frame = ttk.Frame(scrollable_frame)
        buttons_frame.pack(fill="x", padx=20, pady=20)
        
        self.start_button = ttk.Button(buttons_frame, text="🚀 Запустить автоматизацию", 
                                      command=self.start_automation, style="success.TButton")
        self.start_button.pack(side="left", padx=(0, 10))
        
        self.stop_button = ttk.Button(buttons_frame, text="⏹️ Остановить", 
                                     command=self.stop_automation, style="danger.TButton", 
                                     state="disabled")
        self.stop_button.pack(side="left", padx=10)
        
        ttk.Button(buttons_frame, text="💾 Сохранить настройки", 
                  command=self.save_settings).pack(side="left", padx=10)
        
        ttk.Button(buttons_frame, text="❌ Закрыть", 
                  command=self.on_close).pack(side="right")
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        self.load_settings()
        
        self.update_ui_state()
    
    def select_all_accounts(self):
        for var in self.account_vars.values():
            var.set(True)
    
    def deselect_all_accounts(self):
        for var in self.account_vars.values():
            var.set(False)
    
    def load_settings(self):
        try:
            if (self.main_gui and hasattr(self.main_gui, 'automation_settings') 
                and self.main_gui.automation_settings):
                
                settings = self.main_gui.automation_settings
                print(f"🔄 Загружаем настройки из главного GUI: {settings}")
                
                if hasattr(self, 'interval_var'):
                    self.interval_var.set(str(settings.get('interval', 300)))
                if hasattr(self, 'attempts_var'):
                    self.attempts_var.set(str(settings.get('max_attempts', 3)))
                if hasattr(self, 'notifications_var'):
                    self.notifications_var.set(settings.get('notifications', True))
                if hasattr(self, 'accept_trades_var'):
                    self.accept_trades_var.set(settings.get('accept_trades', True))
                if hasattr(self, 'accept_gifts_var'):
                    self.accept_gifts_var.set(settings.get('accept_gifts', True))
                if hasattr(self, 'accept_market_var'):
                    self.accept_market_var.set(settings.get('accept_market', True))
                
                enabled_accounts = settings.get('enabled_accounts', [])
                for account_name, var in self.account_vars.items():
                    var.set(account_name in enabled_accounts)
                    
                print(f"✅ Настройки загружены, активные аккаунты: {enabled_accounts}")
            else:
                print("ℹ️ Активной автоматизации нет, используем настройки по умолчанию")
                
        except Exception as e:
            print(f"Ошибка загрузки настроек автоматизации: {e}")
    
    def save_settings(self):
        try:
            settings = {
                'interval': int(self.interval_var.get()),
                'max_attempts': int(self.attempts_var.get()),
                'autostart': self.autostart_var.get(),
                'notifications': self.notifications_var.get(),
                'accept_trades': self.accept_trades_var.get(),
                'accept_gifts': self.accept_gifts_var.get(),
                'accept_market': self.accept_market_var.get(),
                'enabled_accounts': [name for name, var in self.account_vars.items() if var.get()]
            }
            
            messagebox.showinfo("Успех", "Настройки автоматизации сохранены")
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить настройки: {e}")
    
    def start_automation(self):
        try:
            enabled_accounts = [name for name, var in self.account_vars.items() if var.get()]
            
            if not enabled_accounts:
                messagebox.showwarning("Внимание", "Выберите хотя бы один аккаунт для автоматизации")
                return
            
            print(f"🚀 Запуск автоматизации для аккаунтов: {enabled_accounts}")
            
            settings = {
                'interval': int(self.interval_var.get()),
                'max_attempts': int(self.attempts_var.get()),
                'notifications': self.notifications_var.get(),
                'enabled_accounts': enabled_accounts,
                'accept_trades': self.accept_trades_var.get(),
                'accept_gifts': self.accept_gifts_var.get(), 
                'accept_market': self.accept_market_var.get()
            }
            
            print(f"⚙️ Настройки автоматизации: {settings}")
            
            if self.main_gui and hasattr(self.main_gui, 'start_global_automation'):
                print("🔗 Вызываем start_global_automation...")
                result = self.main_gui.start_global_automation(settings)
                print(f"📊 Результат запуска: {result}")
                
                if result:
                    self.running = True
                    self.update_ui_state()
                    self.status_label.config(text="Запущена", foreground="green")
                    messagebox.showinfo("Успех", f"Автоматизация запущена для {len(enabled_accounts)} аккаунтов\nИнтервал проверки: {settings['interval']} сек")
                else:
                    messagebox.showerror("Ошибка", "Не удалось запустить автоматизацию")
            else:
                print("❌ Нет доступа к main_gui или методу start_global_automation")
                messagebox.showerror("Ошибка", "Не удалось получить доступ к системе автоматизации")
                
        except Exception as e:
            print(f"❌ Ошибка запуска автоматизации: {e}")
            import traceback
            traceback.print_exc()
            messagebox.showerror("Ошибка", f"Ошибка запуска автоматизации: {e}")
    
    def stop_automation(self):
        try:
            if self.main_gui and hasattr(self.main_gui, 'stop_global_automation'):
                if self.main_gui.stop_global_automation():
                    self.running = False
                    self.update_ui_state()
                    self.status_label.config(text="Остановлена", foreground="red")
                    messagebox.showinfo("Успех", "Автоматизация остановлена")
                else:
                    messagebox.showerror("Ошибка", "Не удалось остановить автоматизацию")
            else:
                messagebox.showerror("Ошибка", "Не удалось получить доступ к системе автоматизации")
                
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка остановки автоматизации: {e}")
    
    def update_ui_state(self):
        print(f"🔄 Обновление UI диалога, running={self.running}")
        
        if self.running:
            self.start_button.config(state="disabled")
            self.stop_button.config(state="normal")
            if hasattr(self, 'status_label'):
                self.status_label.config(text="Запущена", foreground="green")
            print("✅ UI обновлен: автоматизация запущена")
        else:
            self.start_button.config(state="normal") 
            self.stop_button.config(state="disabled")
            if hasattr(self, 'status_label'):
                self.status_label.config(text="Остановлена", foreground="gray")
            print("⏹️ UI обновлен: автоматизация остановлена")
    
    def on_close(self):
        if self.running:
            from core.settings_manager import settings_manager
            
            if not settings_manager.settings.get('automation_background_info_shown', False):
                messagebox.showinfo("Работа в фоновом режиме", 
                                   "✅ Автоматизация будет продолжать работу в фоновом режиме.\n\n"
                                   "📍 Для управления автоматизацией используйте:\n"
                                   "• Вкладку 'Автоматизация' в главном окне\n"
                                   "• Или откройте этот диалог снова\n\n"
                                   "ℹ️ Это сообщение больше не будет показываться")
                
                settings_manager.settings['automation_background_info_shown'] = True
                settings_manager.save_settings()
        
        self.dialog.destroy()
