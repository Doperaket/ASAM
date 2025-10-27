from .base_tab import BaseTab


class AutomationTab(BaseTab):
    
    def __init__(self, notebook, main_window):
        import time
        self.tab_id = f"AutomationTab_{int(time.time()*1000)}"
        super().__init__(notebook, main_window, "🤖 Автоматизация")
        self.automation_status_label = None
        self.stop_automation_button = None

    def create_interface(self):
        from tkinter import ttk
        
        title_label = ttk.Label(self.frame, text="Автоматизация подтверждений", 
                               font=("Helvetica", 16, "bold"))
        title_label.pack(pady=(0, 20))

        description_frame = ttk.Frame(self.frame)
        description_frame.pack(fill="x", pady=(0, 20))
        
        description_text = ("🔄 Автоматическое подтверждение трейдов в фоновом режиме\n"
                           "⚙️ Настраиваемые фильтры и условия принятия\n" 
                           "📊 Мониторинг и статистика работы")
        ttk.Label(description_frame, text=description_text, 
                 font=("Helvetica", 11), foreground="gray").pack(anchor="w")

        main_button_frame = ttk.Frame(self.frame)
        main_button_frame.pack(pady=(20, 0))

        automation_button = ttk.Button(main_button_frame, 
                                      text="⚙️ Настроить автоподтверждение", 
                                      command=self.open_automation_settings,
                                      style="success.TButton")
        automation_button.pack(pady=10)

        self.automation_status_frame = ttk.Frame(self.frame)
        self.automation_status_frame.pack(fill="x", pady=(20, 0))
        
        self.automation_status_label = ttk.Label(self.automation_status_frame, 
                                                text="🔴 Автоматизация не запущена", 
                                                font=("Helvetica", 10), 
                                                foreground="gray")
        self.automation_status_label.pack(pady=(0, 10))
        
        self._status_widget = self.automation_status_label
        
        self.stop_automation_button = ttk.Button(self.automation_status_frame, 
                                               text="⏹️ Остановить автоматизацию", 
                                               command=self.stop_automation,
                                               style="danger.TButton")
        self._stop_button_widget = self.stop_automation_button
        
        self.update_status(False, None)

    def open_automation_settings(self):
        try:
            from core.settings_manager import settings_manager
            accounts = settings_manager.get_accounts()
            if not accounts:
                from tkinter import messagebox
                messagebox.showwarning("Внимание", "Нет доступных аккаунтов для автоматизации")
                return

            from gui.dialogs.automation_dialog import AutomationDialog
            dialog = AutomationDialog(self.main_window.root, accounts, 
                                    self.main_window.update_automation_status, self.main_window)
            
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror("Ошибка", f"Ошибка открытия диалога автоматизации: {str(e)}")

    def stop_automation(self):
        self.main_window.stop_global_automation()

    def update_status(self, automation_running, automation_settings):
        try:
            status_widget = getattr(self, '_status_widget', None)
            stop_button_widget = getattr(self, '_stop_button_widget', None)
            
            if status_widget:
                if automation_running and automation_settings:
                    accounts_count = len(automation_settings.get('enabled_accounts', []))
                    interval = automation_settings.get('interval', 300)
                    
                    status_text = f"🟢 Автоматизация активна\nАккаунтов: {accounts_count} | Интервал: {interval} сек"
                    status_widget.config(text=status_text, foreground="green")
                    
                    if stop_button_widget:
                        stop_button_widget.pack(pady=5)
                else:
                    status_widget.config(
                        text="🔴 Автоматизация не запущена", 
                        foreground="gray"
                    )
                    
                    if stop_button_widget:
                        stop_button_widget.pack_forget()
                        
        except Exception as e:
            print(f"Ошибка обновления статуса автоматизации: {e}")
