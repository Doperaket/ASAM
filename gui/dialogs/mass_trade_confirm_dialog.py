import tkinter as tk
from tkinter import ttk, messagebox
import threading


class MassTradeConfirmDialog:
    def __init__(self, parent, accounts, trade_manager):
        self.accounts = accounts
        self.trade_manager = trade_manager
        self.selected_accounts = {}
        self.result = None
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Массовое подтверждение трейдов")
        self.dialog.geometry("600x500")
        self.dialog.resizable(True, True)
        
        from . import set_dialog_icon
        set_dialog_icon(self.dialog)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() - self.dialog.winfo_width()) // 2
        y = (self.dialog.winfo_screenheight() - self.dialog.winfo_height()) // 2
        self.dialog.geometry(f"+{x}+{y}")
        
        self.create_interface()
    
    def create_interface(self):
        header_frame = ttk.Frame(self.dialog)
        header_frame.pack(fill="x", padx=15, pady=15)
        
        ttk.Label(header_frame, text="Массовое подтверждение трейдов", 
                 font=("Helvetica", 16, "bold")).pack()
        ttk.Label(header_frame, text="Выберите аккаунты для подтверждения всех трейдов", 
                 font=("Helvetica", 10)).pack(pady=(5, 0))
        
        select_all_frame = ttk.Frame(self.dialog)
        select_all_frame.pack(fill="x", padx=15, pady=(0, 10))
        
        self.select_all_var = tk.BooleanVar()
        ttk.Checkbutton(select_all_frame, text="Выбрать все аккаунты", 
                       variable=self.select_all_var,
                       command=self.toggle_all_accounts).pack(anchor="w")
        
        accounts_frame = ttk.LabelFrame(self.dialog, text="Выбор аккаунтов", padding=10)
        accounts_frame.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        
        canvas = tk.Canvas(accounts_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(accounts_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        for login, data in self.accounts.items():
            display_name = data.get('display_name', login)
            var = tk.BooleanVar()
            
            frame = ttk.Frame(scrollable_frame)
            frame.pack(fill="x", pady=2)
            
            checkbox = ttk.Checkbutton(frame, text=display_name, variable=var)
            checkbox.pack(side="left")
            
            status_label = ttk.Label(frame, text="", foreground="gray")
            status_label.pack(side="right")
            
            self.selected_accounts[login] = {
                'var': var,
                'display_name': display_name,
                'status_label': status_label
            }
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        buttons_frame = ttk.Frame(self.dialog)
        buttons_frame.pack(fill="x", padx=15, pady=15)
        
        ttk.Button(buttons_frame, text="Проверить подтверждения", 
                  command=self.check_confirmations,
                  style="info.TButton").pack(side="left", padx=(0, 10))
        
        ttk.Button(buttons_frame, text="Подтвердить выбранные", 
                  command=self.confirm_selected,
                  style="success.TButton").pack(side="left", padx=(0, 10))
        
        ttk.Button(buttons_frame, text="Отмена", 
                  command=self.dialog.destroy,
                  style="secondary.TButton").pack(side="right")
        
        progress_frame = ttk.Frame(self.dialog)
        progress_frame.pack(fill="x", padx=15, pady=(0, 15))
        
        self.progress_var = tk.StringVar(value="Готов к работе")
        self.status_label = ttk.Label(progress_frame, textvariable=self.progress_var)
        self.status_label.pack()
        
        self.progress_bar = ttk.Progressbar(progress_frame, mode="determinate")
        self.progress_bar.pack(fill="x", pady=(5, 0))
    
    def toggle_all_accounts(self):
        select_all = self.select_all_var.get()
        for account_data in self.selected_accounts.values():
            account_data['var'].set(select_all)
    
    def check_confirmations(self):
        selected = [login for login, data in self.selected_accounts.items() 
                   if data['var'].get()]
        
        if not selected:
            messagebox.showwarning("Внимание", "Выберите хотя бы один аккаунт")
            return
        
        thread = threading.Thread(target=self.check_confirmations_thread, args=(selected,))
        thread.daemon = True
        thread.start()
    
    def confirm_selected(self):
        selected = [login for login, data in self.selected_accounts.items() 
                   if data['var'].get()]
        
        if not selected:
            messagebox.showwarning("Внимание", "Выберите хотя бы один аккаунт")
            return
        
        confirm = messagebox.askyesno("Подтверждение", 
                                     f"Подтвердить все трейды для {len(selected)} аккаунтов?")
        if not confirm:
            return
        
        thread = threading.Thread(target=self.confirm_trades_thread, args=(selected,))
        thread.daemon = True
        thread.start()
    
    def check_confirmations_thread(self, selected_accounts):
        try:
            total = len(selected_accounts)
            
            for i, login in enumerate(selected_accounts):
                display_name = self.selected_accounts[login]['display_name']
                status_label = self.selected_accounts[login]['status_label']
                
                self.dialog.after(0, lambda p=f"Проверка {i+1}/{total}: {display_name}": 
                                 self.progress_var.set(p))
                self.dialog.after(0, lambda v=(i+1)*100//total: 
                                 self.progress_bar.config(value=v))
                
                try:
                    result = self.trade_manager.get_trade_confirmations(login)
                    
                    if result["success"]:
                        count = len(result["confirmations"])
                        status_text = f"{count} подтв."
                        color = "orange" if count > 0 else "green"
                    else:
                        status_text = "Ошибка"
                        color = "red"
                    
                    self.dialog.after(0, lambda l=status_label, t=status_text, c=color: 
                                     (l.config(text=t, foreground=c)))
                
                except Exception as e:
                    self.dialog.after(0, lambda l=status_label: 
                                     l.config(text="Ошибка", foreground="red"))
            
            self.dialog.after(0, lambda: self.progress_var.set("Проверка завершена"))
            self.dialog.after(0, lambda: self.progress_bar.config(value=0))
                
        except Exception as e:
            self.dialog.after(0, lambda: messagebox.showerror("Ошибка", f"Ошибка проверки:\n{str(e)}"))
    
    def confirm_trades_thread(self, selected_accounts):
        try:
            total = len(selected_accounts)
            success_count = 0
            
            for i, login in enumerate(selected_accounts):
                display_name = self.selected_accounts[login]['display_name']
                status_label = self.selected_accounts[login]['status_label']
                
                self.dialog.after(0, lambda p=f"Подтверждение {i+1}/{total}: {display_name}": 
                                 self.progress_var.set(p))
                self.dialog.after(0, lambda v=(i+1)*100//total: 
                                 self.progress_bar.config(value=v))
                
                try:
                    result = self.trade_manager.confirm_all_trades(login)
                    
                    if result["success"]:
                        confirmed_count = result["confirmed_count"]
                        status_text = f"✅ {confirmed_count}"
                        color = "green"
                        success_count += 1
                    else:
                        status_text = "❌ Ошибка"
                        color = "red"
                    
                    self.dialog.after(0, lambda l=status_label, t=status_text, c=color: 
                                     (l.config(text=t, foreground=c)))
                
                except Exception as e:
                    self.dialog.after(0, lambda l=status_label: 
                                     l.config(text="❌ Ошибка", foreground="red"))
            
            final_message = f"Завершено: {success_count}/{total} аккаунтов"
            self.dialog.after(0, lambda m=final_message: self.progress_var.set(m))
            self.dialog.after(0, lambda: self.progress_bar.config(value=0))
            
            self.dialog.after(0, lambda: messagebox.showinfo("Завершено", 
                f"Массовое подтверждение завершено!\n\nУспешно: {success_count} из {total} аккаунтов"))
                
        except Exception as e:
            self.dialog.after(0, lambda: messagebox.showerror("Ошибка", f"Ошибка подтверждения:\n{str(e)}"))
