import datetime
import tkinter as tk
from .base_tab import BaseTab

from ..dialogs import MassPasswordChangeDialog


class ExperimentalTab(BaseTab):
    
    def __init__(self, notebook, main_window):
        super().__init__(notebook, main_window, "Эксп. функции")
        self.stats_text = None

    def create_interface(self):
        from tkinter import ttk
        
        title_label = ttk.Label(self.frame, text="Экспериментальные функции", 
                               font=("Helvetica", 16, "bold"))
        title_label.pack(pady=(0, 20))

        warning_frame = ttk.Frame(self.frame)
        warning_frame.pack(fill="x", pady=(0, 20))
        
        warning_text = ("⚠️ Внимание: Эти функции используют Steam API и могут потребовать времени для выполнения.\n"
                       "Убедитесь что у всех аккаунтов правильно настроены .mafile и пароли.")
        warning_label = ttk.Label(warning_frame, text=warning_text, 
                                 font=("Helvetica", 10), foreground="orange", 
                                 wraplength=600, justify="left")
        warning_label.pack()

        passwords_frame = ttk.LabelFrame(self.frame, text="Массовая смена паролей", padding=15)
        passwords_frame.pack(fill="x", pady=(0, 20))

        desc_text = ("Изменение паролей для выбранных аккаунтов через Steam API.\n"
                    "Выберите аккаунты и установите новые пароли.")
        ttk.Label(passwords_frame, text=desc_text, 
                 font=("Helvetica", 10), foreground="gray", 
                 wraplength=600).pack(pady=(0, 15))

        ttk.Button(passwords_frame, text="🔑 Массовая смена паролей", 
                  command=self.open_mass_password_change,
                  style="warning.TButton", width=30).pack(pady=10)

        stats_frame = ttk.LabelFrame(self.frame, text="Статистика операций", padding=15)
        stats_frame.pack(fill="both", expand=True, pady=(0, 20))

        self.stats_text = tk.Text(stats_frame, height=8, width=70, 
                                 font=("Consolas", 9), state="disabled",
                                 bg="#2b2b2b", fg="#ffffff")
        self.stats_text.pack(fill="both", expand=True)

        ttk.Button(stats_frame, text="Очистить статистику", 
                  command=self.clear_stats,
                  style="secondary.TButton").pack(pady=(10, 0))

        self.update_stats("Готов к работе. Выберите функцию для выполнения.")

    def update_stats(self, message):
        try:
            if self.stats_text:
                self.stats_text.config(state="normal")
                timestamp = datetime.datetime.now().strftime("%H:%M:%S")
                self.stats_text.insert(tk.END, f"[{timestamp}] {message}\n")
                self.stats_text.see(tk.END)
                self.stats_text.config(state="disabled")
        except:
            pass

    def clear_stats(self):
        try:
            if self.stats_text:
                self.stats_text.config(state="normal")
                self.stats_text.delete(1.0, tk.END)
                self.stats_text.config(state="disabled")
                self.update_stats("Статистика очищена.")
        except:
            pass

    def open_mass_password_change(self):
        try:
            from core.settings_manager import settings_manager
            accounts = settings_manager.get_accounts()
            if not accounts:
                from tkinter import messagebox
                messagebox.showwarning("Внимание", "Нет доступных аккаунтов для смены паролей")
                return

            from gui.dialogs.mass_password_dialog import MassPasswordChangeDialog
            dialog = MassPasswordChangeDialog(self.main_window.root, accounts, self.update_stats)
            
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror("Ошибка", f"Ошибка открытия диалога: {str(e)}")
