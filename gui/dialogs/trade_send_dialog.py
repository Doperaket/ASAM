
import tkinter as tk
from tkinter import messagebox
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import threading
import time


class TradeProgressDialog:
    
    def __init__(self, parent, title="Отправка трейда"):
        self.parent = parent
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("400x200")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (400 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (200 // 2)
        self.dialog.geometry(f"400x200+{x}+{y}")
        
        self.dialog.configure(bg='#2b2b2b')
        
        self.set_progress_dialog_icon()
        
        self.create_widgets()
    
    def set_progress_dialog_icon(self):
        from . import set_dialog_icon
        set_dialog_icon(self.dialog)
        
    def create_widgets(self):
        main_frame = ttk.Frame(self.dialog, style='Dark.TFrame', padding=20)
        main_frame.pack(fill=BOTH, expand=True)
        
        self.icon_label = ttk.Label(main_frame, text="🔄", font=("Arial", 24))
        self.icon_label.pack(pady=(0, 10))
        
        self.title_label = ttk.Label(main_frame, text="Отправка трейда", 
                                    font=("Arial", 14, "bold"), style='Inverse.TLabel')
        self.title_label.pack(pady=(0, 5))
        
        self.status_label = ttk.Label(main_frame, text="Инициализация...", 
                                     font=("Arial", 10), style='Inverse.TLabel')
        self.status_label.pack(pady=(0, 15))
        
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate', 
                                       style='success.Horizontal.TProgressbar')
        self.progress.pack(fill=X, pady=(0, 15))
        self.progress.start(10)
        
        self.cancel_button = ttk.Button(main_frame, text="Отмена", 
                                       command=self.cancel, style='secondary.TButton')
        self.cancel_button.pack()
        
        self.cancelled = False
        
    def update_status(self, status_text):
        if hasattr(self, 'status_label'):
            self.status_label.config(text=status_text)
            
    def update_icon(self, icon_text):
        if hasattr(self, 'icon_label'):
            self.icon_label.config(text=icon_text)
    
    def show_success(self, message):
        self.progress.stop()
        self.update_icon("✅")
        self.update_status("Трейд отправлен успешно!")
        self.cancel_button.config(text="Закрыть")
        
        self.dialog.after(3000, self.close)
        
    def show_error(self, message):
        self.progress.stop()
        self.update_icon("❌")
        self.update_status(f"Ошибка: {message}")
        self.cancel_button.config(text="Закрыть")
        
    def cancel(self):
        self.cancelled = True
        self.close()
        
    def close(self):
        if hasattr(self, 'dialog') and self.dialog:
            self.dialog.destroy()


class TradeSendDialog:
    
    def __init__(self, parent, status_callback=None, inventory_data=None):
        self.parent = parent
        self.status_callback = status_callback
        self.inventory_data = inventory_data or []
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Отправка трейда - Steam API")
        self.dialog.geometry("900x700")
        self.dialog.resizable(True, True)
        
        self.set_window_icon()
        
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self.sender_var = tk.StringVar()
        self.receiver_var = tk.StringVar()
        self.partner_steamid_var = tk.StringVar()
        self.message_var = tk.StringVar()
        self.selected_items = []
        
        self.create_interface()
        
        self.dialog.focus_set()
    
    def set_window_icon(self):
        from . import set_dialog_icon
        set_dialog_icon(self.dialog)
    
    def create_interface(self):
        main_frame = ttk.Frame(self.dialog, padding=10)
        main_frame.pack(fill="both", expand=True)
        
        title_label = ttk.Label(main_frame, text="🔄 Отправка трейдов через Steam API", font=("Arial", 14, "bold"))
        title_label.pack(pady=(0, 10))
        
        settings_frame = ttk.LabelFrame(main_frame, text="Настройки трейда", padding=10)
        settings_frame.pack(fill="x", pady=(0, 10))
        
        sender_frame = ttk.Frame(settings_frame)
        sender_frame.pack(fill="x", pady=2)
        ttk.Label(sender_frame, text="Отправитель:", width=15).pack(side="left")
        
        sender_combo = ttk.Combobox(sender_frame, textvariable=self.sender_var, state="readonly")
        sender_combo.pack(side="left", fill="x", expand=True, padx=(5, 0))
        
        self.load_accounts(sender_combo)
        
        sender_combo.bind('<<ComboboxSelected>>', self.on_sender_changed)
        
        receiver_frame = ttk.Frame(settings_frame)
        receiver_frame.pack(fill="x", pady=2)
        ttk.Label(receiver_frame, text="Trade URL получ.:", width=15).pack(side="left")
        
        tradeurl_entry = ttk.Entry(receiver_frame, textvariable=self.partner_steamid_var)
        tradeurl_entry.pack(side="left", fill="x", expand=True, padx=(5, 0))
        from utils.tk_clipboard_patch import patch_entry_clipboard
        patch_entry_clipboard(tradeurl_entry)
        
        get_url_button = ttk.Button(receiver_frame, text="🔗", width=3, 
                                   command=self.open_trade_url_page,
                                   style="Accent.TButton")
        get_url_button.pack(side="right", padx=(5, 0))
        
        def create_tooltip(widget, text):
            def on_enter(event):
                widget.config(cursor="hand2")
            def on_leave(event):
                widget.config(cursor="")
            widget.bind("<Enter>", on_enter)
            widget.bind("<Leave>", on_leave)
        
        create_tooltip(get_url_button, "Открыть страницу для получения Trade URL")
        
        def add_placeholder(entry, placeholder_text):
            def on_focus_in(event):
                if entry.get() == placeholder_text:
                    entry.delete(0, tk.END)
                    
            def on_focus_out(event):
                if not entry.get():
                    entry.insert(0, placeholder_text)
                    
            if not entry.get():
                entry.insert(0, placeholder_text)
                
            entry.bind('<FocusIn>', on_focus_in)
            entry.bind('<FocusOut>', on_focus_out)
            
        add_placeholder(tradeurl_entry, "https://steamcommunity.com/tradeoffer/new/?partner=XXXXXX&token=XXXXXXXX")
        
        hint_label = ttk.Label(receiver_frame, text="💡", font=("Arial", 8))
        hint_label.pack(side="right", padx=(5, 0))
        
        msg_frame = ttk.Frame(settings_frame)
        msg_frame.pack(fill="x", pady=2)
        ttk.Label(msg_frame, text="Сообщение:", width=15).pack(side="left")
        
        msg_entry = ttk.Entry(msg_frame, textvariable=self.message_var)
        msg_entry.pack(side="left", fill="x", expand=True, padx=(5, 0))
        
        
        items_frame = ttk.LabelFrame(main_frame, text="Предметы для отправки", padding=10)
        items_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        selection_frame = ttk.Frame(items_frame)
        selection_frame.pack(fill="x", pady=(0, 5))
        
        ttk.Button(selection_frame, text="Выбрать все", 
                  command=self.select_all_items, bootstyle="info").pack(side="left", padx=(0, 5))
        ttk.Button(selection_frame, text="Отменить все", 
                  command=self.deselect_all_items, bootstyle="secondary").pack(side="left", padx=(0, 5))
        
        tree_frame = ttk.Frame(items_frame)
        tree_frame.pack(fill="both", expand=True)
        
        columns = ("Аккаунт", "Предмет", "Количество", "Цена", "Выбрать")
        self.items_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=10)
        
        for col in columns:
            self.items_tree.heading(col, text=col)
            self.items_tree.column(col, width=120)
        
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.items_tree.yview)
        self.items_tree.configure(yscrollcommand=scrollbar.set)
        
        self.items_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        self.load_inventory_data()
        
        self.items_tree.bind("<Double-1>", self.toggle_item_selection)
        
        stats_frame = ttk.LabelFrame(main_frame, text="Статистика", padding=5)
        stats_frame.pack(fill="x", pady=(0, 10))
        
        stats_text_frame = ttk.Frame(stats_frame)
        stats_text_frame.pack(fill="x")
        
        self.stats_label = ttk.Label(stats_text_frame, text=self.get_stats_text())
        self.stats_label.pack(side="left")
        
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x")
        
        ttk.Button(button_frame, text="🔄 Обновить инвентарь", 
                   command=self.refresh_inventory, bootstyle="info").pack(side="left")
        
        ttk.Button(button_frame, text="🚀 Отправить трейд", 
                   command=self.send_trade, bootstyle="success").pack(side="left", padx=(5, 0))
        
        ttk.Button(button_frame, text="❌ Закрыть", 
                   command=self.close_dialog, bootstyle="secondary").pack(side="right")
    
    def load_accounts(self, combo_widget):
        try:
            from core.settings_manager import settings_manager
            accounts = settings_manager.get_accounts()
            account_names = list(accounts.keys())
            combo_widget['values'] = account_names
            if account_names:
                combo_widget.set(account_names[0])
        except Exception as e:
            print(f"Ошибка загрузки аккаунтов: {e}")
    
    def load_inventory_data(self):
        self.filter_inventory_by_sender()
    
    def filter_inventory_by_sender(self):
        for item in self.items_tree.get_children():
            self.items_tree.delete(item)
        
        selected_account = self.sender_var.get()
        if selected_account:
            self.selected_items = [item for item in self.selected_items 
                                 if item.get('account') == selected_account]
        
        if not self.inventory_data:
            self.items_tree.insert('', 'end', values=(
                "📋 Нет данных",
                "Сначала проанализируйте инвентарь во вкладке 'Инвентарь'",
                "0",
                "$0.00",
                "ℹ️"
            ))
            return
        
        filtered_data = self.inventory_data
        if selected_account:
            filtered_data = [item for item in self.inventory_data 
                           if item.get('account') == selected_account]
        
        if not filtered_data and selected_account:
            self.items_tree.insert('', 'end', values=(
                selected_account,
                "Нет предметов для этого аккаунта",
                "0",
                "$0.00",
                ""
            ))
            return
        
        for item_data in filtered_data:
            account = item_data.get('account', 'Unknown')
            name = item_data.get('name', 'Unknown Item')  
            amount = item_data.get('quantity', item_data.get('amount', 1))
            price = item_data.get('price', 0.0)
            
            price_str = f"${price:.2f}" if isinstance(price, (int, float)) else str(price)
            
            item_key = f"{account}_{name}"
            selected_keys = [f"{item['account']}_{item['name']}" for item in self.selected_items]
            checkbox = "☑" if item_key in selected_keys else "☐"
            
            self.items_tree.insert('', 'end', values=(
                account,
                name,
                amount,
                price_str,
                checkbox
            ))
    
    def on_sender_changed(self, event=None):
        self.filter_inventory_by_sender()
        if hasattr(self, 'stats_label'):
            self.stats_label.config(text=self.get_stats_text())
    
    def select_all_items(self):
        selected_account = self.sender_var.get()
        
        filtered_data = self.inventory_data
        if selected_account:
            filtered_data = [item for item in self.inventory_data 
                           if item.get('account') == selected_account]
        
        if selected_account:
            self.selected_items = [item for item in self.selected_items 
                                 if item.get('account') != selected_account]
        else:
            self.selected_items = []
        
        for item_data in filtered_data:
            if item_data not in self.selected_items:
                self.selected_items.append(item_data)
        
        self.filter_inventory_by_sender()
        if hasattr(self, 'stats_label'):
            self.stats_label.config(text=self.get_stats_text())
    
    def deselect_all_items(self):
        selected_account = self.sender_var.get()
        
        if selected_account:
            self.selected_items = [item for item in self.selected_items 
                                 if item.get('account') != selected_account]
        else:
            self.selected_items = []
        
        self.filter_inventory_by_sender()
        if hasattr(self, 'stats_label'):
            self.stats_label.config(text=self.get_stats_text())
    
    def toggle_item_selection(self, event):
        selection = self.items_tree.selection()
        if not selection:
            return
        
        item_id = selection[0]
        item_values = self.items_tree.item(item_id)['values']
        
        if not item_values or item_values[0] == "Нет данных":
            messagebox.showinfo("Информация", 
                "Сначала проанализируйте инвентарь во вкладке 'Инвентарь'.\n\n"
                "1. Перейдите во вкладку 'Инвентарь'\n"
                "2. Выберите нужные аккаунты\n"
                "3. Нажмите 'Анализировать инвентарь'\n"
                "4. После завершения анализа вернитесь к отправке трейда")
            return
        
        account = item_values[0]
        name = item_values[1]
        
        selected_asset_ids = {item.get('asset_id') for item in self.selected_items if item.get('asset_id')}
        
        found_item = None
        for original_item in self.inventory_data:
            if (original_item.get('account') == account and 
                original_item.get('name') == name and
                original_item.get('asset_id') not in selected_asset_ids):
                found_item = original_item
                break
        
        if not found_item:
            messagebox.showwarning("Внимание", "Предмет недоступен или уже выбран")
            return
        
        if not found_item.get('asset_id'):
            messagebox.showwarning("Внимание", f"У предмета '{name}' отсутствует asset_id. Возможно, инвентарь не был корректно проанализирован.")
            return
        
        item_data = {
            'account': found_item.get('account'),
            'name': found_item.get('name'),
            'amount': found_item.get('amount', 1),
            'price': found_item.get('price', '$0.00'),
            'app_id': found_item.get('app_id', 730),
            'context_id': found_item.get('context_id', '2'),
            'asset_id': found_item.get('asset_id'),
            'item_id': item_id
        }
        
        item_key = found_item.get('asset_id', f"{account}_{name}")
        existing_keys = [item.get('asset_id', f"{item['account']}_{item['name']}") for item in self.selected_items]
        
        if item_key in existing_keys:
            self.selected_items = [item for item in self.selected_items 
                                 if item.get('asset_id', f"{item['account']}_{item['name']}") != item_key]
            new_values = list(item_values)
            new_values[4] = "☐"
            self.items_tree.item(item_id, values=new_values)
        else:
            self.selected_items.append(item_data)
            new_values = list(item_values)
            new_values[4] = "☑"
            self.items_tree.item(item_id, values=new_values)
            
            if not self.sender_var.get():
                self.sender_var.set(item_data['account'])
        
        if hasattr(self, 'stats_label'):
            self.stats_label.config(text=self.get_stats_text())
    
    def get_stats_text(self):
        if not self.inventory_data:
            return "Данные инвентаря не загружены"
        
        selected_account = self.sender_var.get()
        if selected_account:
            filtered_items = [item for item in self.inventory_data 
                            if item.get('account') == selected_account]
            total_items = len(filtered_items)
            account_text = f"для {selected_account}"
        else:
            total_items = len(self.inventory_data)
            accounts = set(item.get('account', '') for item in self.inventory_data)
            account_text = f"из {len(accounts)} аккаунтов"
        
        selected_count = len(self.selected_items)
        
        return f"Предметов: {total_items} | Выбрано: {selected_count} | {account_text}"
    
    def update_stats(self):
        self.stats_label.config(text=self.get_stats_text())
    
    def refresh_inventory(self):
        selected_account = self.sender_var.get()
        if not selected_account:
            return
            
        def refresh_thread():
            try:
                from steam.steam_inventory_parser import SteamInventoryParser
                
                parser = SteamInventoryParser()
                
                game_id = 730
                currency = "USD"
                
                inventory_result = parser.analyze_account_inventory(selected_account, game_id, currency)
                
                if inventory_result['success']:
                    account_items = inventory_result['items']
                    
                    self.inventory_data = [item for item in self.inventory_data 
                                         if item.get('account') != selected_account]
                    
                    for item in account_items:
                        item['account'] = selected_account
                        self.inventory_data.append(item)
                    
                    self.dialog.after(0, lambda: self.filter_inventory_by_sender())
                
            except Exception:
                pass
        
        threading.Thread(target=refresh_thread, daemon=True).start()
    
    def send_trade(self):
        sender = self.sender_var.get()
        trade_url = self.partner_steamid_var.get()
        message = self.message_var.get()
        
        if not sender:
            messagebox.showerror("Ошибка", "Выберите аккаунт отправителя")
            return
        
        if not trade_url or trade_url == "https://steamcommunity.com/tradeoffer/new/?partner=XXXXXX&token=XXXXXXXX":
            messagebox.showerror("Ошибка", "Введите Trade URL получателя")
            return
            
        if not trade_url.startswith("https://steamcommunity.com/tradeoffer/new/"):
            messagebox.showerror("Ошибка", 
                "Неверный формат Trade URL.\n\n"
                "Должен быть: https://steamcommunity.com/tradeoffer/new/?partner=XXXXXX&token=XXXXXXXX")
            return
        
        if not self.selected_items:
            messagebox.showerror("Ошибка", "Выберите хотя бы один предмет для отправки")
            return
        
        selected_names = [item['name'] for item in self.selected_items]
        items_text = "\\n".join(selected_names[:5])
        if len(selected_names) > 5:
            items_text += f"\\n... и еще {len(selected_names) - 5} предметов"
        
        confirm_text = (f"Отправить трейд?\\n\\n"
                       f"От: {sender}\\n"
                       f"Кому: {trade_url}\\n"
                       f"Предметов: {len(self.selected_items)}\\n\\n"
                       f"Предметы:\\n{items_text}")
        
        if not messagebox.askyesno("Подтверждение", confirm_text):
            return
        
        thread = threading.Thread(target=self._send_trade_thread, 
                                 args=(sender, trade_url, message))
        thread.daemon = True
        thread.start()
    
    def _send_trade_thread(self, sender, trade_url, message):
        if not self.inventory_data:
            self.dialog.after(0, lambda: messagebox.showwarning("Внимание", 
                "Нет данных инвентаря для отправки трейда.\n\n"
                "Сначала проанализируйте инвентарь во вкладке 'Инвентарь'."))
            return
        
        progress_dialog = None
        
        def create_progress():
            nonlocal progress_dialog
            progress_dialog = TradeProgressDialog(self.dialog)
            
        self.dialog.after(0, create_progress)
        time.sleep(0.1)
        
        try:
            
            def update_progress(status):
                if progress_dialog:
                    progress_dialog.update_status(status)
            
            self.dialog.after(0, lambda: update_progress("Загрузка данных аккаунта..."))
            
            from steam.steam_integration import steam_trade_manager
            from core.settings_manager import settings_manager
            
            accounts = settings_manager.get_accounts()
            if sender not in accounts:
                self.dialog.after(0, lambda: progress_dialog.show_error(f"Аккаунт {sender} не найден") if progress_dialog else None)
                return
            
            password = settings_manager.get_account_password(sender)
            if not password:
                self.dialog.after(0, lambda: progress_dialog.show_error(f"Пароль для {sender} не найден") if progress_dialog else None)
                return
            
            if progress_dialog and progress_dialog.cancelled:
                return
                
            self.dialog.after(0, lambda: update_progress("Авторизация в Steam..."))
            time.sleep(0.5)
            
            session_id = steam_trade_manager.login_account(sender, password)
            if not session_id:
                self.dialog.after(0, lambda: progress_dialog.show_error("Не удалось авторизоваться в Steam") if progress_dialog else None)
                return
            
            if progress_dialog and progress_dialog.cancelled:
                return
            
            self.dialog.after(0, lambda: update_progress("Подготовка предметов для трейда..."))
            time.sleep(0.3)
            
            items_to_send = []
            
            if not self.selected_items:
                self.dialog.after(0, lambda: progress_dialog.show_error("Нет выбранных предметов для отправки") if progress_dialog else None)
                return
            
            for selected_item in self.selected_items:
                asset_id = selected_item.get('asset_id')
                if not asset_id:
                    item_keys = list(selected_item.keys())
                    error_msg = f"Отсутствует asset_id для предмета: {selected_item.get('name', 'Unknown')}\n\nЭто означает, что предмет не был правильно проанализирован.\nПопробуйте повторить анализ инвентаря."
                    self.dialog.after(0, lambda: progress_dialog.show_error(error_msg) if progress_dialog else None)
                    return
                
                item_data = {
                    'appid': int(selected_item.get('app_id', 730)),
                    'contextid': str(selected_item.get('context_id', '2')),
                    'assetid': str(asset_id)
                }
                
                items_to_send.append(item_data)
            
            if progress_dialog and progress_dialog.cancelled:
                return
                
            self.dialog.after(0, lambda: update_progress("Отправка трейда..."))
            time.sleep(0.5)
            
            offer_id = steam_trade_manager.create_trade_offer(
                login=sender,
                trade_url=trade_url,
                items_from_me=items_to_send,
                message=message
            )
            
            if offer_id:
                success_msg = f"Трейд отправлен успешно!\nOffer ID: {offer_id}"
                self.dialog.after(0, lambda: progress_dialog.show_success(success_msg) if progress_dialog else None)
            else:
                self.dialog.after(0, lambda: progress_dialog.show_error("Не удалось отправить трейд") if progress_dialog else None)
            
        except ImportError:
            error_msg = ("Steam API модуль недоступен.\n\n"
                        "Для работы трейдов необходимо:\n"
                        "1. Установить Node.js\n"
                        "2. Выполнить 'npm install' в папке steam_api")
            self.dialog.after(0, lambda: progress_dialog.show_error(error_msg) if progress_dialog else None)
        except Exception as e:
            error_msg = f"Ошибка отправки трейда: {str(e)}"
            self.dialog.after(0, lambda: progress_dialog.show_error(error_msg) if progress_dialog else None)
    
    def refresh_inventory(self):
        selected_account = self.sender_var.get()
        if not selected_account:
            return
            
        def refresh_thread():
            try:
                from steam.steam_inventory_parser import SteamInventoryParser
                
                parser = SteamInventoryParser()
                
                game_id = 730
                currency = "USD"
                
                inventory_result = parser.analyze_account_inventory(selected_account, game_id, currency)
                
                if inventory_result['success']:
                    account_items = inventory_result['items']
                    
                    self.inventory_data = [item for item in self.inventory_data 
                                         if item.get('account') != selected_account]
                    
                    for item in account_items:
                        item['account'] = selected_account
                        self.inventory_data.append(item)
                    
                    self.dialog.after(0, lambda: self.filter_inventory_by_sender())
                
            except Exception:
                pass
        
        threading.Thread(target=refresh_thread, daemon=True).start()
    
    def open_trade_url_page(self):
        import webbrowser
        try:
            webbrowser.open("https://steamcommunity.com/my/tradeoffers/privacy")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть браузер: {str(e)}")
    
    def close_dialog(self):
        self.dialog.destroy()
