import tkinter as tk
from tkinter import ttk, messagebox
import threading
from core.settings_manager import settings_manager


class ConfirmationsDialog:
    def __init__(self, parent, account_login, account_display_name, trade_manager=None):
        self.account_login = account_login
        self.account_display_name = account_display_name
        self.trade_manager = trade_manager
        self.confirmations_data = {}
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"Steam Guard подтверждения - {account_display_name}")
        self.dialog.geometry("600x500")
        self.dialog.resizable(True, True)
        
        from . import set_dialog_icon
        set_dialog_icon(self.dialog)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (600 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (500 // 2)
        self.dialog.geometry(f"600x500+{x}+{y}")
        
        self.create_widgets()
        self.load_confirmations()
    
    def create_widgets(self):
        title_frame = ttk.Frame(self.dialog)
        title_frame.pack(fill="x", padx=20, pady=(20, 10))
        
        ttk.Label(title_frame, text=f"Steam Guard подтверждения", 
                 font=("Helvetica", 14, "bold")).pack()
        ttk.Label(title_frame, text=f"{self.account_display_name} ({self.account_login})", 
                 font=("Helvetica", 10), foreground="gray").pack()
        
        control_frame = ttk.Frame(self.dialog)
        control_frame.pack(fill="x", padx=20, pady=(0, 10))
        
        ttk.Button(control_frame, text="🔄 Обновить", 
                  command=self.load_confirmations,
                  style="info.TButton").pack(side="left")
        
        ttk.Button(control_frame, text="✅ Подтвердить все", 
                  command=self.confirm_all,
                  style="success.TButton").pack(side="left", padx=(10, 0))
        
        ttk.Button(control_frame, text="❌ Отклонить все", 
                  command=self.cancel_all,
                  style="danger.TButton").pack(side="left", padx=(10, 0))
        
        list_frame = ttk.LabelFrame(self.dialog, text="Активные подтверждения", padding=10)
        list_frame.pack(fill="both", expand=True, padx=20, pady=(0, 10))
        
        columns = ("Тип", "Описание", "Время", "Статус")
        self.confirmations_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=15)
        
        self.confirmations_tree.heading("Тип", text="Тип операции")
        self.confirmations_tree.heading("Описание", text="Описание")
        self.confirmations_tree.heading("Время", text="Время создания")
        self.confirmations_tree.heading("Статус", text="Статус")
        
        self.confirmations_tree.tag_configure("trade", background="#e8f5e8")
        self.confirmations_tree.tag_configure("market", background="#e8f0ff")
        self.confirmations_tree.tag_configure("selected", background="#d4edda")
        
        self.confirmations_tree.column("Тип", width=100)
        self.confirmations_tree.column("Описание", width=250)
        self.confirmations_tree.column("Время", width=120)
        self.confirmations_tree.column("Статус", width=80)
        
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.confirmations_tree.yview)
        self.confirmations_tree.configure(yscrollcommand=scrollbar.set)
        
        self.confirmations_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        self.create_context_menu()
        
        action_frame = ttk.Frame(self.dialog)
        action_frame.pack(fill="x", padx=20, pady=(0, 10))
        
        ttk.Button(action_frame, text="✅ Подтвердить выбранное", 
                  command=self.confirm_selected,
                  style="success.TButton").pack(side="left")
        
        ttk.Button(action_frame, text="❌ Отклонить выбранное", 
                  command=self.cancel_selected,
                  style="danger.TButton").pack(side="left", padx=(10, 0))
        
        help_frame = ttk.Frame(self.dialog)
        help_frame.pack(fill="x", padx=20, pady=(5, 10))
        
        help_text = "💡 Совет: Кликните на строку в списке для выбора, затем нажмите кнопку выше"
        ttk.Label(help_frame, text=help_text, font=("Arial", 9), foreground="gray").pack(side="left")
        
        buttons_frame = ttk.Frame(self.dialog)
        buttons_frame.pack(fill="x", padx=20, pady=20)
        
        ttk.Button(buttons_frame, text="Закрыть", 
                  command=self.dialog.destroy,
                  style="secondary.TButton").pack(side="right")
    
    def create_context_menu(self):
        self.context_menu = tk.Menu(self.dialog, tearoff=0)
        self.context_menu.add_command(label="✅ Подтвердить", command=self.confirm_selected)
        self.context_menu.add_command(label="❌ Отклонить", command=self.cancel_selected)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="📋 Копировать ID", command=self.copy_confirmation_id)
        
        self.confirmations_tree.bind("<Button-3>", self.show_context_menu)
        
        self.confirmations_tree.bind("<<TreeviewSelect>>", self.on_selection_change)
    
    def show_context_menu(self, event):
        try:
            self.context_menu.post(event.x_root, event.y_root)
        except Exception:
            pass
    
    def on_selection_change(self, event):
        selected = self.confirmations_tree.selection()
        if selected:
            item_data = self.confirmations_tree.item(selected[0])
            values = item_data['values']
            if values and len(values) >= 2:
                conf_type = values[0]
                conf_desc = values[1]
                self.dialog.title(f"Steam Guard подтверждения - {self.account_display_name} | Выбрано: {conf_type}")
        else:
            self.dialog.title(f"Steam Guard подтверждения - {self.account_display_name}")
    
    def load_confirmations(self):
        for item in self.confirmations_tree.get_children():
            self.confirmations_tree.delete(item)
        self.confirmations_data.clear()
        
        try:
            from pysda import SimpleTradeManager
            
            loading_item = self.confirmations_tree.insert("", "end", values=("🔄", "Загрузка подтверждений...", "—", "—"))
            self.confirmations_tree.update()
            
            def load_confirmations_thread():
                try:
                    trade_manager = SimpleTradeManager()
                    result = trade_manager.get_trade_confirmations(self.account_login)
                    self.dialog.after(0, lambda: self.handle_pysda_confirmations_loaded(result, loading_item))
                except Exception as e:
                    self.dialog.after(0, lambda: self.handle_confirmations_error(str(e), loading_item))
            
            thread = threading.Thread(target=load_confirmations_thread)
            thread.daemon = True
            thread.start()
                
        except ImportError:
            self.confirmations_tree.insert("", "end", values=("Ошибка", "Модуль steam_integration недоступен", "—", "—"))
        except Exception as e:
            self.confirmations_tree.insert("", "end", values=("Ошибка", f"Ошибка загрузки: {str(e)}", "—", "—"))
    
    def handle_trade_confirmations_loaded(self, result, loading_item):
        self.confirmations_tree.delete(loading_item)
        
        if result["success"]:
            confirmations = result.get("confirmations", [])
            if confirmations:
                for conf in confirmations:
                    self.confirmations_tree.insert("", "end", values=(
                        conf.get('type', 'Неизвестно'),
                        conf.get('description', 'Нет описания'),
                        conf.get('time', 'Неизвестно'),
                        "Ожидает"
                    ))
            else:
                self.confirmations_tree.insert("", "end", values=("—", "Нет активных подтверждений", "—", "—"))
        else:
            self.confirmations_tree.insert("", "end", values=("Ошибка", result.get("error", "Неизвестная ошибка"), "—", "—"))

    def handle_confirmations_loaded(self, confirmations, loading_item):
        self.confirmations_tree.delete(loading_item)
        
        if confirmations:
            for conf in confirmations:
                conf_type = conf.get('type', 'Unknown')
                type_mapping = {
                    '1': 'Трейд',
                    '2': 'Торговля',
                    '3': 'Продажа на рынке',
                    '4': 'Смена номера телефона',
                    '5': 'Создание аккаунта',
                    '6': 'Покупка в Store',
                    '7': 'Выставление на рынок',
                    '8': 'Смена email',
                    '9': 'Смена пароля',
                    '10': 'Доступ к API ключу',
                    '11': 'Изменение Steam Guard',
                    '12': 'Покупка в Community Market',
                    '13': 'Покупка в Steam Store',
                    '14': 'Покупка подарка'
                }
                type_text = type_mapping.get(str(conf_type), f"Тип {conf_type}")
                
                self.confirmations_tree.insert("", "end", values=(
                    type_text,
                    conf.get('description', 'Нет описания'),
                    conf.get('time', 'Неизвестно'),
                    "Ожидает"
                ), tags=(conf.get('id', ''), conf.get('key', '')))
        else:
            self.confirmations_tree.insert("", "end", values=("—", "Нет активных подтверждений", "—", "—"))
    
    def handle_confirmations_error(self, error, loading_item):
        self.confirmations_tree.delete(loading_item)
        
        self.confirmations_tree.insert("", "end", values=("Ошибка", f"Не удалось загрузить: {error}", "—", "—"))
    
    def handle_new_confirmations_loaded(self, confirmations, loading_item):
        self.confirmations_tree.delete(loading_item)
        
        if confirmations:
            for conf in confirmations:
                print(f"[DEBUG] Loading confirmation: {conf}")
                
                conf_type = conf.get('type', 'Unknown')
                type_mapping = {
                    1: 'Трейд',
                    2: 'Торговля',
                    3: 'Продажа на рынке',
                    4: 'Смена номера телефона',
                    5: 'Создание аккаунта',
                    6: 'Покупка в Store',
                    7: 'Выставление на рынок',
                    8: 'Смена email',
                    9: 'Смена пароля',
                    10: 'Доступ к API ключу',
                    11: 'Изменение Steam Guard',
                    12: 'Покупка в Community Market',
                    13: 'Покупка в Steam Store',
                    14: 'Покупка подарка'
                }
                type_text = type_mapping.get(conf_type, f"Тип {conf_type}")
                
                conf_id = conf.get('id', '')
                conf_key = conf.get('key', '')
                print(f"[DEBUG] Confirmation ID: {conf_id}, Key: {conf_key}")
                
                item_id = self.confirmations_tree.insert("", "end", values=(
                    type_text,
                    conf.get('title', conf.get('description', 'Нет описания')),
                    conf.get('time', 'Неизвестно'),
                    "Ожидает"
                ))
                
                self.confirmations_data[item_id] = {
                    'id': conf_id,
                    'key': conf_key,
                    'data': conf
                }
                print(f"[DEBUG] Saved confirmation data for item {item_id}: id={conf_id}, key={conf_key}")
        else:
            self.confirmations_tree.insert("", "end", values=("—", "Нет активных подтверждений", "—", "—"))
    
    def handle_pysda_confirmations_loaded(self, result, loading_item):
        try:
            self.confirmations_tree.delete(loading_item)
        except:
            pass
        
        if not result.get('success'):
            error_msg = result.get('error', 'Неизвестная ошибка')
            self.confirmations_tree.insert("", "end", values=("❌", f"Ошибка: {error_msg}", "—", "—"))
            return
        
        confirmations = result.get('confirmations', [])
        
        if not confirmations:
            self.confirmations_tree.insert("", "end", values=("📭", "Нет подтверждений", "—", "—"))
            return
        
        for conf in confirmations:
            conf_type = conf.get('type', 'Unknown')
            type_mapping = {
                1: 'Трейд',
                2: 'Торговля',
                3: 'Продажа на рынке',
                4: 'Смена номера телефона',
                5: 'Создание аккаунта',
                6: 'Покупка в Store',
                7: 'Выставление на рынок',
                8: 'Смена email',
                9: 'Смена пароля',
                10: 'Доступ к API ключу',
                11: 'Изменение Steam Guard',
                12: 'Покупка в Community Market',
                13: 'Покупка в Steam Store',
                14: 'Покупка подарка'
            }
            type_text = type_mapping.get(conf_type, f"Тип {conf_type}")
            
            conf_id = conf.get('confirmation_id', conf.get('id', ''))
            
            item_id = self.confirmations_tree.insert("", "end", values=(
                type_text,
                conf.get('description', 'Нет описания'),
                "Неизвестно",
                "Ожидает"
            ))
            
            self.confirmations_data[item_id] = {
                'id': conf_id,
                'confirmation_obj': conf.get('confirmation_obj'),
                'executor': conf.get('executor'),
                'data': conf,
                'type': 'pysda'
            }

    def confirm_selected(self):
        selected = self.confirmations_tree.selection()
        if not selected:
            messagebox.showwarning("Выбор не сделан", 
                                 "Сначала выберите строку в списке подтверждений,\n"
                                 "а затем нажмите кнопку 'Подтвердить выбранное'")
            return
        
        try:
            item_id = selected[0]
            
            if item_id not in self.confirmations_data:
                print(f"[DEBUG] Item {item_id} not found in confirmations_data")
                print(f"[DEBUG] Available items: {list(self.confirmations_data.keys())}")
                messagebox.showerror("Ошибка", f"Данные подтверждения не найдены для элемента {item_id}")
                return
                
            confirmation_data = self.confirmations_data[item_id]
            confirmation_id = confirmation_data['id']
            
            if confirmation_data.get('type') == 'pysda':
                confirmation_obj = confirmation_data.get('confirmation_obj')
                if not confirmation_obj:
                    messagebox.showwarning("Внимание", "Отсутствует объект подтверждения pySDA")
                    return
                
                def confirm_pysda_thread():
                    try:
                        from pysda import SimpleTradeManager
                        trade_manager = SimpleTradeManager()
                        result = trade_manager.confirm_trade(self.account_login, confirmation_obj)
                        self.dialog.after(0, lambda: self.handle_confirm_result(result.get('success', False), item_id))
                    except Exception as e:
                        self.dialog.after(0, lambda: self.handle_confirm_error(str(e)))
                
                thread = threading.Thread(target=confirm_pysda_thread)
                thread.daemon = True
                thread.start()
                return
            
            confirmation_key = confirmation_data.get('key')
            
            print(f"[DEBUG] Confirmation Key: {confirmation_key}")
            
            if not confirmation_id or not confirmation_key:
                messagebox.showwarning("Внимание", f"Неполные данные подтверждения. ID: {confirmation_id}, Key: {confirmation_key}")
                return
            
            from steam.steam_integration import steam_trade_manager
            
            password = settings_manager.get_account_password(self.account_login)
            if not password:
                messagebox.showerror("Ошибка", "Пароль аккаунта не установлен")
                return
            
            def confirm_thread():
                try:
                    session_id = steam_trade_manager.login_account(self.account_login, password)
                    if not session_id:
                        self.dialog.after(0, lambda: self.handle_confirm_error("Не удалось авторизоваться"))
                        return
                    
                    success = steam_trade_manager.confirm_confirmation(
                        self.account_login, 
                        confirmation_id, 
                        confirmation_key, 
                        accept=True
                    )
                    self.dialog.after(0, lambda: self.handle_confirm_result(success, selected[0]))
                except Exception as e:
                    self.dialog.after(0, lambda: self.handle_confirm_error(str(e)))
            
            thread = threading.Thread(target=confirm_thread)
            thread.daemon = True
            thread.start()
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка подтверждения: {str(e)}")
    
    def handle_confirm_result(self, success, item_id):
        if success:
            self.confirmations_tree.delete(item_id)
            if item_id in self.confirmations_data:
                del self.confirmations_data[item_id]
            messagebox.showinfo("Успех", "Подтверждение отправлено успешно!")
        else:
            messagebox.showerror("Ошибка", "Не удалось подтвердить операцию")
    
    def handle_confirm_error(self, error):
        messagebox.showerror("Ошибка", f"Ошибка при подтверждении: {error}")
    
    def cancel_selected(self):
        selected = self.confirmations_tree.selection()
        if not selected:
            messagebox.showwarning("Выбор не сделан", 
                                 "Сначала выберите строку в списке подтверждений,\n"
                                 "а затем нажмите кнопку 'Отклонить выбранное'")
            return
        
        messagebox.showinfo("Информация", "Функция отклонения пока недоступна.\nИспользуйте мобильное приложение Steam для отклонения.")
    
    def confirm_all(self):
        items = self.confirmations_tree.get_children()
        if not items:
            messagebox.showinfo("Информация", "Нет подтверждений для обработки")
            return
        
        real_confirmations = []
        for item in items:
            if item in self.confirmations_data:
                conf_data = self.confirmations_data[item]
                if conf_data['id'] and conf_data['key']:
                    real_confirmations.append((item, conf_data['id'], conf_data['key']))
        
        if not real_confirmations:
            messagebox.showinfo("Информация", "Нет подтверждений для обработки")
            return
        
        if not messagebox.askyesno("Подтверждение", 
                                 f"Подтвердить ВСЕ активные запросы? ({len(real_confirmations)} шт.)"):
            return
        
        try:
            def confirm_all_thread():
                try:
                    from pysda import SimpleTradeManager
                    trade_manager = SimpleTradeManager()
                    
                    result = trade_manager.confirm_all_trades(self.account_login)
                    
                    if result.get('success'):
                        confirmed_count = result.get('accepted', 0)
                        if confirmed_count > 0:
                            self.dialog.after(0, lambda: self.load_confirmations())
                        
                        self.dialog.after(0, lambda: messagebox.showinfo("Результат", 
                                                                        f"Подтверждено: {confirmed_count} подтверждений"))
                    else:
                        error_msg = result.get('error', 'Неизвестная ошибка')
                        self.dialog.after(0, lambda: messagebox.showerror("Ошибка", f"Не удалось подтвердить: {error_msg}"))
                
                except Exception as e:
                    self.dialog.after(0, lambda: messagebox.showerror("Ошибка", f"Ошибка при массовом подтверждении: {str(e)}"))
            
            thread = threading.Thread(target=confirm_all_thread)
            thread.daemon = True
            thread.start()
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка массового подтверждения: {str(e)}")
    
    def cancel_all(self):
        if messagebox.askyesno("Подтверждение", "Отклонить ВСЕ активные запросы?"):
            messagebox.showinfo("Информация", "Все подтверждения отклонены (демо)")
    
    def copy_confirmation_id(self):
        selected = self.confirmations_tree.selection()
        if not selected:
            messagebox.showwarning("Внимание", "Выберите подтверждение")
            return
        
        messagebox.showinfo("Информация", "ID скопирован в буфер обмена (демо)")
