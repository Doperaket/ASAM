import tkinter as tk
from tkinter import ttk, messagebox


class TradeLinkEditDialog:
    
    def __init__(self, parent, title, name="", url=""):
        self.parent = parent
        self.result = None
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("500x250")
        self.dialog.resizable(False, False)
        
        from . import set_dialog_icon
        set_dialog_icon(self.dialog)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self.dialog.geometry("+%d+%d" % (parent.winfo_rootx() + 100, parent.winfo_rooty() + 100))
        
        self.create_interface(name, url)
    
    def create_interface(self, name, url):
        main_frame = ttk.Frame(self.dialog, padding=20)
        main_frame.pack(fill="both", expand=True)
        
        ttk.Label(main_frame, text="Название:", font=("Helvetica", 11)).pack(anchor="w", pady=(0, 5))
        
        self.name_var = tk.StringVar(value=name)
        name_entry = ttk.Entry(main_frame, textvariable=self.name_var, font=("Helvetica", 11))
        name_entry.pack(fill="x", pady=(0, 15))
        
        ttk.Label(main_frame, text="Трейд-ссылка:", font=("Helvetica", 11)).pack(anchor="w", pady=(0, 5))
        
        self.url_var = tk.StringVar(value=url)
        url_entry = ttk.Entry(main_frame, textvariable=self.url_var, font=("Helvetica", 11))
        url_entry.pack(fill="x", pady=(0, 15))
        
        hint_text = ("Пример: https://steamcommunity.com/tradeoffer/new/?partner=123456789&token=AbCdEfGh\n"
                    "Ссылку можно получить в настройках Steam → Конфиденциальность → URL для обмена")
        ttk.Label(main_frame, text=hint_text, font=("Helvetica", 9), 
                 foreground="gray", wraplength=450).pack(pady=(0, 15))
        
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill="x", pady=(15, 0))
        
        ttk.Button(buttons_frame, text="Сохранить", 
                  command=self.save,
                  style="primary.TButton", width=15).pack(side="left", padx=(0, 10))
        
        ttk.Button(buttons_frame, text="Отмена", 
                  command=self.cancel,
                  style="secondary.TButton", width=15).pack(side="left")
        
        if not name:
            name_entry.focus()
        else:
            url_entry.focus()
    
    def save(self):
        name = self.name_var.get().strip()
        url = self.url_var.get().strip()
        
        if not name:
            messagebox.showwarning("Внимание", "Введите название ссылки")
            return
        
        if not url:
            messagebox.showwarning("Внимание", "Введите URL трейд-ссылки")
            return
        
        if not ("steamcommunity.com/tradeoffer/new" in url and "partner=" in url and "token=" in url):
            messagebox.showwarning("Внимание", "Неверный формат трейд-ссылки.\n\nПравильный формат:\nhttps://steamcommunity.com/tradeoffer/new/?partner=XXXXXX&token=XXXXXXXX")
            return
        
        self.result = (name, url)
        self.dialog.destroy()
    
    def cancel(self):
        self.dialog.destroy()
