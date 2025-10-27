import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
from core.settings_manager import settings_manager


class AddAccountDialog:
    def __init__(self, parent):
        self.result = None
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Добавить аккаунт")
        self.dialog.geometry("400x300")
        self.dialog.resizable(True, True)
        
        from . import set_dialog_icon
        set_dialog_icon(self.dialog)
        
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self.dialog.geometry("+%d+%d" % (parent.winfo_rootx() + 50, parent.winfo_rooty() + 50))
        
        main_frame = ttk.Frame(self.dialog, padding=20)
        main_frame.pack(expand=True, fill="both")
        
        ttk.Label(main_frame, text="Логин Steam:").pack(anchor="w", pady=(0, 5))
        self.login_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.login_var).pack(fill="x", pady=(0, 10))
        
        ttk.Label(main_frame, text="Пароль:").pack(anchor="w", pady=(0, 5))
        self.password_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.password_var, show="*").pack(fill="x", pady=(0, 10))
        
        ttk.Label(main_frame, text="Файл .maFile:").pack(anchor="w", pady=(0, 5))
        mafile_frame = ttk.Frame(main_frame)
        mafile_frame.pack(fill="x", pady=(0, 15))
        
        self.mafile_var = tk.StringVar()
        ttk.Entry(mafile_frame, textvariable=self.mafile_var, state="readonly").pack(side="left", fill="x", expand=True, padx=(0, 10))
        ttk.Button(mafile_frame, text="Выбрать", command=self.browse_mafile).pack(side="right")
        
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill="x", pady=(10, 0))
        
        ttk.Button(buttons_frame, text="Сохранить", command=self.save_account, style="primary.TButton").pack(side="left", padx=(0, 10))
        ttk.Button(buttons_frame, text="Отмена", command=self.cancel).pack(side="left")
    
    def browse_mafile(self):
        filename = filedialog.askopenfilename(
            title="Выберите .maFile",
            filetypes=[("MaFile", "*.mafile"), ("Все файлы", "*.*")]
        )
        if filename:
            self.mafile_var.set(filename)
    
    def save_account(self):
        login = self.login_var.get().strip()
        password = self.password_var.get().strip()
        mafile_path = self.mafile_var.get().strip()
        
        if not login:
            messagebox.showerror("Ошибка", "Введите логин!")
            return
        if not password:
            messagebox.showerror("Ошибка", "Введите пароль!")
            return
        if not mafile_path:
            messagebox.showerror("Ошибка", "Выберите .maFile!")
            return
        
        try:
            from core.settings_manager import get_application_path
            dest_dir = os.path.join(get_application_path(), "data", "mafiles")
            os.makedirs(dest_dir, exist_ok=True)
            
            print(f"[DEBUG] Копируем mafile: {mafile_path}")
            print(f"[DEBUG] В папку: {dest_dir}")
            
            import shutil
            filename = os.path.basename(mafile_path)
            dest_path = os.path.join(dest_dir, filename)
            shutil.copy2(mafile_path, dest_path)
            
            print(f"[DEBUG] Файл скопирован: {dest_path}")
            print(f"[DEBUG] Файл существует: {os.path.exists(dest_path)}")
            
            settings_manager.set_account_password(login, password)
            settings_manager.add_account(login, filename)
            
            self.result = True
            messagebox.showinfo("Успех", f"Аккаунт {login} добавлен успешно!")
            self.dialog.destroy()
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка добавления аккаунта: {str(e)}")
    
    def cancel(self):
        self.dialog.destroy()
