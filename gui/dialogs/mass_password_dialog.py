import tkinter as tk
from tkinter import ttk, messagebox
import threading
from core.settings_manager import settings_manager


class MassPasswordChangeDialog:
    def __init__(self, parent, accounts, stats_callback):
        self.accounts = accounts
        self.stats_callback = stats_callback
        self.selected_accounts = {}
        self.result = None
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Массовая смена паролей")
        self.dialog.geometry("700x600")
        self.dialog.resizable(True, True)
        
        from . import set_dialog_icon
        set_dialog_icon(self.dialog)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (700 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (600 // 2)
        self.dialog.geometry(f"700x600+{x}+{y}")
        
        self.create_widgets()
    
    def create_widgets(self):
        title_frame = ttk.Frame(self.dialog)
        title_frame.pack(fill="x", padx=20, pady=(20, 10))
        
        ttk.Label(title_frame, text="Массовая смена паролей", 
                 font=("Helvetica", 16, "bold")).pack()
        ttk.Label(title_frame, text="Выберите аккаунты и настройте параметры смены паролей", 
                 font=("Helvetica", 10), foreground="gray").pack()
        
        main_frame = ttk.Frame(self.dialog)
        main_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        left_frame = ttk.LabelFrame(main_frame, text="Выбор аккаунтов", padding=10)
        left_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        select_all_frame = ttk.Frame(left_frame)
        select_all_frame.pack(fill="x", pady=(0, 10))
        
        self.select_all_var = tk.BooleanVar()
        ttk.Checkbutton(select_all_frame, text="Выбрать все", 
                       variable=self.select_all_var,
                       command=self.toggle_select_all).pack(side="left")
        
        ttk.Label(select_all_frame, text=f"({len(self.accounts)} аккаунтов)", 
                 foreground="gray").pack(side="left", padx=(10, 0))
        
        accounts_container = ttk.Frame(left_frame)
        accounts_container.pack(fill="both", expand=True)
        
        canvas = tk.Canvas(accounts_container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(accounts_container, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        
        def bind_mousewheel(event):
            canvas.bind_all("<MouseWheel>", on_mousewheel)
            
        def unbind_mousewheel(event):
            canvas.unbind_all("<MouseWheel>")
        
        canvas.bind('<Enter>', bind_mousewheel)
        canvas.bind('<Leave>', unbind_mousewheel)
        self.scrollable_frame.bind('<Enter>', bind_mousewheel)
        self.scrollable_frame.bind('<Leave>', unbind_mousewheel)
        
        self.account_vars = {}
        for login, account_data in self.accounts.items():
            account_frame = ttk.Frame(self.scrollable_frame)
            account_frame.pack(fill="x", pady=2)
            
            var = tk.BooleanVar()
            self.account_vars[login] = var
            
            display_name = settings_manager.get_account_display_name(login)
            
            has_password = settings_manager.get_account_password(login)
            password_status = "✓" if has_password else "❌"
            
            checkbox_text = f"{display_name} ({login}) [{password_status}]"
            checkbox = ttk.Checkbutton(account_frame, text=checkbox_text, variable=var)
            checkbox.pack(side="left", fill="x", expand=True)
            
            if not has_password:
                checkbox.config(state="disabled")
                ttk.Label(account_frame, text="Нет пароля", 
                         foreground="red", font=("Helvetica", 8)).pack(side="right")
            
            def bind_to_mousewheel(widget):
                widget.bind('<Enter>', bind_mousewheel)
                widget.bind('<Leave>', unbind_mousewheel)
            
            bind_to_mousewheel(account_frame)
            bind_to_mousewheel(checkbox)
        
        right_frame = ttk.LabelFrame(main_frame, text="Настройки паролей", padding=10)
        right_frame.pack(side="right", fill="y", padx=(10, 0))
        
        password_type_frame = ttk.LabelFrame(right_frame, text="Тип пароля", padding=10)
        password_type_frame.pack(fill="x", pady=(0, 15))
        
        self.password_type_var = tk.StringVar(value="custom")
        ttk.Radiobutton(password_type_frame, text="Один пароль для всех", 
                       variable=self.password_type_var, value="custom",
                       command=self.on_password_type_change).pack(anchor="w", pady=2)
        ttk.Radiobutton(password_type_frame, text="Случайный для каждого", 
                       variable=self.password_type_var, value="random",
                       command=self.on_password_type_change).pack(anchor="w", pady=2)
        
        custom_password_frame = ttk.LabelFrame(right_frame, text="Новый пароль", padding=10)
        custom_password_frame.pack(fill="x", pady=(0, 15))
        
        self.custom_password_var = tk.StringVar()
        self.password_entry = ttk.Entry(custom_password_frame, 
                                       textvariable=self.custom_password_var,
                                       show="*", font=("Helvetica", 10))
        self.password_entry.pack(fill="x", pady=(0, 10))
        
        self.show_password_var = tk.BooleanVar()
        ttk.Checkbutton(custom_password_frame, text="Показать пароль", 
                       variable=self.show_password_var,
                       command=self.toggle_password_visibility).pack(anchor="w")
        
        random_password_frame = ttk.LabelFrame(right_frame, text="Настройки случайных паролей", padding=10)
        random_password_frame.pack(fill="x", pady=(0, 15))
        
        length_frame = ttk.Frame(random_password_frame)
        length_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(length_frame, text="Длина пароля:").pack(side="left")
        self.password_length_var = tk.StringVar(value="12")
        length_spinbox = ttk.Spinbox(length_frame, from_=8, to=32, width=5, 
                                    textvariable=self.password_length_var)
        length_spinbox.pack(side="right")
        
        self.include_special_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(random_password_frame, text="Включить спецсимволы", 
                       variable=self.include_special_var).pack(anchor="w")
        
        progress_frame = ttk.LabelFrame(right_frame, text="Прогресс", padding=10)
        progress_frame.pack(fill="x", pady=(15, 0))
        
        self.progress_var = tk.StringVar(value="Готов к запуску")
        ttk.Label(progress_frame, textvariable=self.progress_var, 
                 font=("Helvetica", 9), wraplength=200).pack()
        
        self.progress_bar = ttk.Progressbar(progress_frame, mode='determinate')
        self.progress_bar.pack(fill="x", pady=(10, 0))
        
        buttons_frame = ttk.Frame(self.dialog)
        buttons_frame.pack(fill="x", padx=20, pady=20)
        
        ttk.Button(buttons_frame, text="Начать смену паролей", 
                  command=self.start_password_change,
                  style="primary.TButton").pack(side="left", padx=(0, 10))
        
        ttk.Button(buttons_frame, text="Отмена", 
                  command=self.cancel,
                  style="secondary.TButton").pack(side="left")
        
        self.on_password_type_change()
    
    def toggle_select_all(self):
        select_all = self.select_all_var.get()
        for login, var in self.account_vars.items():
            if settings_manager.get_account_password(login):
                var.set(select_all)
    
    def on_password_type_change(self):
        password_type = self.password_type_var.get()
        
        if password_type == "custom":
            self.password_entry.config(state="normal")
        else:
            self.password_entry.config(state="disabled")
    
    def toggle_password_visibility(self):
        if self.show_password_var.get():
            self.password_entry.config(show="")
        else:
            self.password_entry.config(show="*")
    
    def start_password_change(self):
        selected = []
        for login, var in self.account_vars.items():
            if var.get():
                selected.append(login)
        
        if not selected:
            messagebox.showwarning("Внимание", "Выберите хотя бы один аккаунт")
            return
        
        password_type = self.password_type_var.get()
        if password_type == "custom":
            custom_password = self.custom_password_var.get().strip()
            if not custom_password:
                messagebox.showwarning("Внимание", "Введите новый пароль")
                return
            if len(custom_password) < 4:
                messagebox.showwarning("Внимание", "Пароль должен содержать минимум 4 символа")
                return
        
        confirm_text = f"Изменить пароли для {len(selected)} аккаунтов?\n\n"
        if password_type == "custom":
            confirm_text += f"Новый пароль: {self.custom_password_var.get()}"
        else:
            length = int(self.password_length_var.get())
            special = "с" if self.include_special_var.get() else "без"
            confirm_text += f"Случайные пароли длиной {length} символов ({special} спецсимволов)"
        
        if not messagebox.askyesno("Подтверждение", confirm_text):
            return
        
        self.dialog.config(cursor="wait")
        
        thread = threading.Thread(target=self.change_passwords_thread, args=(selected,))
        thread.daemon = True
        thread.start()
    
    def change_passwords_thread(self, selected_accounts):
        try:
            from steam.steam_integration import change_password_sync, STEAM_MODULES_AVAILABLE
            
            if not STEAM_MODULES_AVAILABLE:
                self.dialog.after(0, lambda: messagebox.showerror("Ошибка", "Steam API модули недоступны"))
                self.dialog.after(0, lambda: self.dialog.config(cursor=""))
                return
            
            total = len(selected_accounts)
            success_count = 0
            error_count = 0
            
            self.dialog.after(0, lambda: self.progress_bar.config(maximum=total, value=0))
            
            for i, login in enumerate(selected_accounts):
                try:
                    self.dialog.after(0, lambda l=login: self.progress_var.set(f"Обработка: {l}"))
                    self.dialog.after(0, lambda v=i: self.progress_bar.config(value=v))
                    
                    current_password = settings_manager.get_account_password(login)
                    if not current_password:
                        self.stats_callback(f"❌ {login}: Нет текущего пароля")
                        error_count += 1
                        continue
                    
                    password_type = self.password_type_var.get()
                    if password_type == "custom":
                        new_password = self.custom_password_var.get().strip()
                    else:
                        new_password = self.generate_random_password()
                    
                    self.stats_callback(f"🔄 {login}: Смена пароля...")
                    
                    result = change_password_sync(login, current_password, new_password)
                    
                    if result["success"]:
                        settings_manager.set_account_password(login, new_password)
                        self.stats_callback(f"✅ {login}: Пароль изменен успешно → {new_password}")
                        success_count += 1
                    else:
                        self.stats_callback(f"❌ {login}: {result['error']}")
                        error_count += 1
                    
                except Exception as e:
                    self.stats_callback(f"❌ {login}: Ошибка - {str(e)}")
                    error_count += 1
            
            self.dialog.after(0, lambda: self.progress_bar.config(value=total))
            self.dialog.after(0, lambda: self.progress_var.set("Завершено"))
            self.dialog.after(0, lambda: self.dialog.config(cursor=""))
            
            report = f"Смена паролей завершена!\n\nУспешно: {success_count}\nОшибок: {error_count}\nВсего: {total}"
            self.dialog.after(0, lambda: messagebox.showinfo("Результат", report))
            self.stats_callback(f"📊 Завершено: {success_count}/{total} успешно")
            
        except Exception as e:
            self.dialog.after(0, lambda: messagebox.showerror("Ошибка", f"Критическая ошибка: {str(e)}"))
            self.dialog.after(0, lambda: self.dialog.config(cursor=""))
            self.stats_callback(f"💥 Критическая ошибка: {str(e)}")
    
    def generate_random_password(self):
        import random
        import string
        
        length = int(self.password_length_var.get())
        include_special = self.include_special_var.get()
        
        chars = string.ascii_letters + string.digits
        if include_special:
            chars += "!@#$%^&*"
        
        password = ''.join(random.choice(chars) for _ in range(length))
        return password
    
    def cancel(self):
        self.dialog.destroy()
