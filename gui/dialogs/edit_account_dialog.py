import tkinter as tk
from tkinter import ttk, messagebox
from core.settings_manager import settings_manager


class EditAccountDialog:
    def __init__(self, parent, account_name):
        self.result = None
        self.account_name = account_name
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"Редактировать аккаунт: {account_name}")
        self.dialog.geometry("400x200")
        self.dialog.resizable(False, False)
        
        from . import set_dialog_icon
        set_dialog_icon(self.dialog)
        
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self.dialog.geometry("+%d+%d" % (parent.winfo_rootx() + 50, parent.winfo_rooty() + 50))
        
        main_frame = ttk.Frame(self.dialog, padding=20)
        main_frame.pack(expand=True, fill="both")
        
        ttk.Label(main_frame, text="Логин Steam:").pack(anchor="w", pady=(0, 5))
        ttk.Label(main_frame, text=account_name, font=("Helvetica", 10, "bold")).pack(anchor="w", pady=(0, 10))
        
        ttk.Label(main_frame, text="Новый пароль:").pack(anchor="w", pady=(0, 5))
        self.password_var = tk.StringVar()
        current_password = settings_manager.get_account_password(account_name)
        if current_password:
            self.password_var.set(current_password)
        ttk.Entry(main_frame, textvariable=self.password_var, show="*").pack(fill="x", pady=(0, 15))
        
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill="x", pady=(10, 0))
        
        ttk.Button(buttons_frame, text="Сохранить", command=self.save_changes, style="primary.TButton").pack(side="left", padx=(0, 10))
        ttk.Button(buttons_frame, text="Отмена", command=self.cancel).pack(side="left")
    
    def save_changes(self):
        password = self.password_var.get().strip()
        
        if not password:
            messagebox.showerror("Ошибка", "Введите пароль!")
            return
        
        try:
            settings_manager.set_account_password(self.account_name, password)
            
            self.result = True
            messagebox.showinfo("Успех", f"Пароль для аккаунта {self.account_name} обновлен!")
            self.dialog.destroy()
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка обновления пароля: {str(e)}")
    
    def cancel(self):
        self.dialog.destroy()
