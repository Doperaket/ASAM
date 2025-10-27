import tkinter as tk
from tkinter import ttk, messagebox
import threading
from core.settings_manager import settings_manager


class AccountSettingsDialog:
    def __init__(self, parent, account_login, account_display_name):
        self.account_login = account_login
        self.account_display_name = account_display_name
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"Настройки аккаунта - {account_display_name}")
        self.dialog.geometry("500x400")
        self.dialog.resizable(False, False)
        
        from . import set_dialog_icon
        set_dialog_icon(self.dialog)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (500 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (400 // 2)
        self.dialog.geometry(f"500x400+{x}+{y}")
        
        self.create_widgets()
    
    def create_widgets(self):
        title_frame = ttk.Frame(self.dialog)
        title_frame.pack(fill="x", padx=20, pady=(20, 10))
        
        ttk.Label(title_frame, text=f"Настройки аккаунта", 
                 font=("Helvetica", 14, "bold")).pack()
        ttk.Label(title_frame, text=f"{self.account_display_name} ({self.account_login})", 
                 font=("Helvetica", 10), foreground="gray").pack()
        
        password_frame = ttk.LabelFrame(self.dialog, text="Смена пароля", padding=15)
        password_frame.pack(fill="x", padx=20, pady=10)
        
        current_frame = ttk.Frame(password_frame)
        current_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(current_frame, text="Текущий пароль:").pack(side="left")
        current_password = settings_manager.get_account_password(self.account_login)
        masked_password = "*" * len(current_password) if current_password else "Не задан"
        ttk.Label(current_frame, text=masked_password, foreground="gray").pack(side="left", padx=(10, 0))
        
        new_password_frame = ttk.Frame(password_frame)
        new_password_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(new_password_frame, text="Новый пароль:", font=("Helvetica", 10, "bold")).pack(anchor="w")
        
        password_input_frame = ttk.Frame(new_password_frame)
        password_input_frame.pack(fill="x", pady=(5, 0))
        
        self.password_var = tk.StringVar()
        self.password_entry = ttk.Entry(password_input_frame, textvariable=self.password_var, 
                                       show="*", font=("Helvetica", 10))
        self.password_entry.pack(side="left", fill="x", expand=True)
        
        self.show_password_var = tk.BooleanVar()
        show_password_btn = ttk.Checkbutton(password_input_frame, text="👁", 
                                           variable=self.show_password_var, 
                                           command=self.toggle_password_visibility)
        show_password_btn.pack(side="right", padx=(5, 0))
        
        password_buttons_frame = ttk.Frame(password_frame)
        password_buttons_frame.pack(fill="x", pady=(10, 0))
        
        ttk.Button(password_buttons_frame, text="🎲 Сгенерировать случайный пароль", 
                  command=self.generate_random_password,
                  style="secondary.TButton").pack(side="left")
        
        ttk.Button(password_buttons_frame, text="🔑 Сменить в Steam", 
                  command=self.change_password_steam_api,
                  style="warning.TButton").pack(side="left", padx=(5, 0))
        
        ttk.Button(password_buttons_frame, text="💾 Сохранить пароль", 
                  command=self.save_password,
                  style="success.TButton").pack(side="right")
        
        info_frame = ttk.Frame(password_frame)
        info_frame.pack(fill="x", pady=(10, 0))
        
        info_text = ("💡 Инструкции:\n"
                    "• Введите новый пароль и нажмите '💾 Сохранить пароль' - сохранит только локально\n"
                    "• Введите новый пароль и нажмите '🔑 Сменить в Steam' - изменит пароль в Steam через API\n"
                    "• Используйте надежный пароль длиной 8-32 символа с буквами, цифрами и спецсимволами")
        ttk.Label(info_frame, text=info_text, foreground="gray", 
                 font=("Helvetica", 9)).pack(anchor="w")
        
        buttons_frame = ttk.Frame(self.dialog)
        buttons_frame.pack(fill="x", padx=20, pady=20)
        
        ttk.Button(buttons_frame, text="Закрыть", 
                  command=self.dialog.destroy,
                  style="secondary.TButton").pack(side="right")
    
    def toggle_password_visibility(self):
        if self.show_password_var.get():
            self.password_entry.config(show="")
        else:
            self.password_entry.config(show="*")
    
    def generate_random_password(self):
        import random
        import string
        
        lowercase = string.ascii_lowercase
        uppercase = string.ascii_uppercase  
        digits = string.digits
        special_chars = "!@#$%^&*"
        
        length = random.randint(8, 10)
        
        password = [
            random.choice(lowercase),
            random.choice(uppercase),
            random.choice(digits),
            random.choice(special_chars)
        ]
        
        all_chars = lowercase + uppercase + digits + special_chars
        for _ in range(length - 4):
            password.append(random.choice(all_chars))
        
        random.shuffle(password)
        generated_password = ''.join(password)
        
        self.password_var.set(generated_password)
        
        messagebox.showinfo("Пароль сгенерирован", 
                           f"Сгенерирован случайный пароль длиной {length} символов.\n"
                           f"Не забудьте сохранить его!")
    
    def save_password(self):
        new_password = self.password_var.get().strip()
        
        if not new_password:
            messagebox.showwarning("Внимание", "Введите новый пароль")
            return
        
        if len(new_password) < 4:
            messagebox.showwarning("Внимание", "Пароль должен содержать минимум 4 символа")
            return
        
        try:
            success = settings_manager.set_account_password(self.account_login, new_password)
            if success:
                messagebox.showinfo("Успех", "Пароль успешно изменен и сохранен!")
                self.password_var.set("")
            else:
                messagebox.showerror("Ошибка", "Не удалось сохранить новый пароль")
                
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка сохранения пароля: {str(e)}")

    def change_password_steam_api(self):
        try:
            from steam.steam_integration import change_password_sync, STEAM_MODULES_AVAILABLE
            
            if not STEAM_MODULES_AVAILABLE:
                messagebox.showerror("Ошибка", "Steam API модули недоступны.\nУстановите необходимые зависимости.")
                return
            
            current_password = settings_manager.get_account_password(self.account_login)
            if not current_password:
                messagebox.showwarning("Внимание", "Сначала установите текущий пароль в настройках аккаунта")
                return
            
            new_password = self.password_var.get().strip()
            if not new_password:
                messagebox.showwarning("Внимание", "Введите новый пароль в поле ввода")
                return
            
            if len(new_password) < 4:
                messagebox.showwarning("Внимание", "Пароль должен содержать минимум 4 символа")
                return
            
            if not messagebox.askyesno("Подтверждение", 
                                     f"Изменить пароль аккаунта {self.account_display_name} через Steam API?\n\n"
                                     f"Новый пароль: {new_password}\n\n"
                                     "Это операция изменит пароль в Steam и автоматически сохранит новый пароль локально.\n"
                                     "Убедитесь что Steam Guard настроен правильно."):
                return
            
            progress_dialog = tk.Toplevel(self.dialog)
            progress_dialog.title("Смена пароля")
            progress_dialog.geometry("300x100")
            progress_dialog.transient(self.dialog)
            progress_dialog.grab_set()
            
            progress_dialog.update_idletasks()
            x = (progress_dialog.winfo_screenwidth() // 2) - (300 // 2)
            y = (progress_dialog.winfo_screenheight() // 2) - (100 // 2)
            progress_dialog.geometry(f"300x100+{x}+{y}")
            
            ttk.Label(progress_dialog, text="Выполняется смена пароля...", 
                     font=("Helvetica", 10)).pack(pady=20)
            progress_bar = ttk.Progressbar(progress_dialog, mode='indeterminate')
            progress_bar.pack(pady=10, padx=20, fill="x")
            progress_bar.start()
            
            progress_dialog.update()
            
            def change_password_thread():
                try:
                    result = change_password_sync(self.account_login, current_password, new_password)
                    
                    progress_dialog.after(0, lambda: handle_password_change_result(result))
                except Exception as e:
                    progress_dialog.after(0, lambda: handle_password_change_error(str(e)))
            
            def handle_password_change_result(result):
                progress_dialog.destroy()
                
                if result["success"]:
                    used_password = result.get("new_password", new_password)
                    settings_manager.set_account_password(self.account_login, used_password)
                    self.password_var.set(used_password)
                    
                    messagebox.showinfo("Успех", 
                                      f"Пароль успешно изменен через Steam API!\n\n"
                                      f"Новый пароль: {used_password}\n\n"
                                      "Пароль автоматически сохранен в настройках аккаунта.")
                else:
                    messagebox.showerror("Ошибка", f"Не удалось изменить пароль:\n{result['error']}")
            
            def handle_password_change_error(error):
                progress_dialog.destroy()
                messagebox.showerror("Ошибка", f"Ошибка при смене пароля:\n{error}")
            
            thread = threading.Thread(target=change_password_thread)
            thread.daemon = True
            thread.start()
            
        except ImportError:
            messagebox.showerror("Ошибка", "Модуль steam_integration недоступен")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Произошла ошибка: {str(e)}")
