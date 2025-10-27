import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import time
from .base_tab import BaseTab
from core.settings_manager import settings_manager


class TradeTab(BaseTab):
    
    def __init__(self, notebook, main_window):
        self.trade_select_all_var = None
        self.trade_accounts_count_label = None
        self.trade_canvas = None
        self.trade_scrollable_frame = None
        self.trade_account_vars = {}
        self.currency_var = None
        self.game_var = None
        self.total_value_label = None
        self.items_count_label = None
        self.analyzed_accounts_label = None
        self.items_tree = None
        
        self.full_inventory_data = []
        
        super().__init__(notebook, main_window, "Инвентарь")

    def update_status(self, message):
        if hasattr(self.main_window, 'status_label'):
            self.main_window.status_label.config(text=message)
        else:
            print(f"Статус: {message}")

    def create_interface(self):
        main_paned = ttk.PanedWindow(self.frame, orient="horizontal")
        main_paned.pack(fill="both", expand=True)

        left_panel = ttk.Frame(main_paned)
        main_paned.add(left_panel, weight=1)

        right_panel = ttk.Frame(main_paned)
        main_paned.add(right_panel, weight=2)

        
        title_frame = ttk.Frame(left_panel)
        title_frame.pack(fill="x", pady=(0, 20))
        
        ttk.Label(title_frame, text="Анализ инвентарей", 
                 font=("Helvetica", 16, "bold")).pack()
        ttk.Label(title_frame, text="Выберите аккаунты для анализа предметов", 
                 font=("Helvetica", 10), foreground="gray").pack()

        accounts_frame = ttk.LabelFrame(left_panel, text="Выбор аккаунтов", padding=10)
        accounts_frame.pack(fill="both", expand=False, pady=(0, 15))

        select_all_frame = ttk.Frame(accounts_frame)
        select_all_frame.pack(fill="x", pady=(0, 10))

        self.trade_select_all_var = tk.BooleanVar()
        ttk.Checkbutton(select_all_frame, text="Выбрать все", 
                       variable=self.trade_select_all_var,
                       command=self.toggle_trade_select_all).pack(side="left")

        self.trade_accounts_count_label = ttk.Label(select_all_frame, text="(0 аккаунтов)", 
                                                   foreground="gray")
        self.trade_accounts_count_label.pack(side="left", padx=(10, 0))

        accounts_container = ttk.Frame(accounts_frame)
        accounts_container.pack(fill="both", expand=True, pady=(0, 0))
        accounts_container.configure(height=200)

        self.trade_canvas = tk.Canvas(accounts_container, highlightthickness=0, height=200)
        trade_scrollbar = ttk.Scrollbar(accounts_container, orient="vertical", command=self.trade_canvas.yview)
        self.trade_scrollable_frame = ttk.Frame(self.trade_canvas)

        self.trade_scrollable_frame.bind(
            "<Configure>",
            lambda e: self.trade_canvas.configure(scrollregion=self.trade_canvas.bbox("all"))
        )

        self.trade_canvas.create_window((0, 0), window=self.trade_scrollable_frame, anchor="nw")
        self.trade_canvas.configure(yscrollcommand=trade_scrollbar.set)

        self.trade_canvas.pack(side="left", fill="both", expand=True)
        trade_scrollbar.pack(side="right", fill="y")

        self.bind_mousewheel_to_trade_canvas()

        settings_frame = ttk.LabelFrame(left_panel, text="Настройки анализа", padding=10)
        settings_frame.pack(fill="x", expand=False, pady=(15, 0), side="bottom")

        currency_frame = ttk.Frame(settings_frame)
        currency_frame.pack(fill="x", pady=(0, 10))

        ttk.Label(currency_frame, text="Валюта:", font=("Helvetica", 10)).pack(side="left")
        
        self.currency_var = tk.StringVar(value="USD")
        currency_combo = ttk.Combobox(currency_frame, textvariable=self.currency_var, 
                                     values=["USD", "EUR", "RUB", "CNY", "GBP", "CAD", "AUD"], 
                                     state="readonly", width=8)
        currency_combo.pack(side="left", padx=(10, 0))

        game_frame = ttk.Frame(settings_frame)
        game_frame.pack(fill="x", pady=(0, 15))

        ttk.Label(game_frame, text="Игра:", font=("Helvetica", 10)).pack(side="left")
        
        self.game_var = tk.StringVar(value="730")
        game_combo = ttk.Combobox(game_frame, textvariable=self.game_var, 
                                 values=["730 (CS2)", "440 (TF2)", "570 (Dota 2)", "252490 (Rust)"], 
                                 state="readonly", width=15)
        game_combo.pack(side="left", padx=(10, 0))

        analyze_button = ttk.Button(settings_frame, text="🔍 Анализировать инвентари", 
                                   command=self.analyze_inventories,
                                   style="primary.TButton")
        analyze_button.pack(fill="x", pady=(15, 0), ipady=5)

        
        stats_frame = ttk.LabelFrame(right_panel, text="Общая статистика", padding=10)
        stats_frame.pack(fill="x", pady=(0, 15))

        stats_grid = ttk.Frame(stats_frame)
        stats_grid.pack(fill="x")

        ttk.Label(stats_grid, text="Общая стоимость:", font=("Helvetica", 12, "bold")).grid(row=0, column=0, sticky="w", padx=(0, 10))
        self.total_value_label = ttk.Label(stats_grid, text="$0.00", font=("Helvetica", 14, "bold"), foreground="#00ff00")
        self.total_value_label.grid(row=0, column=1, sticky="w")

        ttk.Label(stats_grid, text="Предметов:", font=("Helvetica", 10)).grid(row=1, column=0, sticky="w", padx=(0, 10))
        self.items_count_label = ttk.Label(stats_grid, text="0", font=("Helvetica", 10))
        self.items_count_label.grid(row=1, column=1, sticky="w")

        ttk.Label(stats_grid, text="Аккаунтов:", font=("Helvetica", 10)).grid(row=2, column=0, sticky="w", padx=(0, 10))
        self.analyzed_accounts_label = ttk.Label(stats_grid, text="0", font=("Helvetica", 10))
        self.analyzed_accounts_label.grid(row=2, column=1, sticky="w")

        results_frame = ttk.LabelFrame(right_panel, text="Результаты анализа", padding=10)
        results_frame.pack(fill="both", expand=True)

        columns = ("account", "item_name", "quantity", "status", "price", "total")
        self.items_tree = ttk.Treeview(results_frame, columns=columns, show="headings", height=15)

        self.items_tree.heading("account", text="Аккаунт")
        self.items_tree.heading("item_name", text="Предмет")
        self.items_tree.heading("quantity", text="Кол-во")
        self.items_tree.heading("status", text="Статус")
        self.items_tree.heading("price", text="Цена за шт.")
        self.items_tree.heading("total", text="Общая стоимость")

        self.items_tree.column("account", width=120, minwidth=100)
        self.items_tree.column("item_name", width=200, minwidth=150)
        self.items_tree.column("quantity", width=60, minwidth=50)
        self.items_tree.column("status", width=80, minwidth=70)
        self.items_tree.column("price", width=100, minwidth=80)
        self.items_tree.column("total", width=120, minwidth=100)

        items_scrollbar = ttk.Scrollbar(results_frame, orient="vertical", command=self.items_tree.yview)
        self.items_tree.configure(yscrollcommand=items_scrollbar.set)

        self.items_tree.pack(side="left", fill="both", expand=True)
        items_scrollbar.pack(side="right", fill="y")

        buttons_frame = ttk.Frame(right_panel)
        buttons_frame.pack(fill="x", pady=(15, 0))

        ttk.Button(buttons_frame, text="💾 Экспорт в CSV", 
                  command=self.export_inventory_csv,
                  style="info.TButton").pack(side="left", padx=(0, 10))

        ttk.Button(buttons_frame, text="🔄 Обновить цены", 
                  command=self.refresh_prices,
                  style="warning.TButton").pack(side="left", padx=(0, 10))

        ttk.Button(buttons_frame, text="🔗 Сменить валюту", 
                  command=self.change_currency,
                  style="info.TButton").pack(side="left", padx=(0, 10))

        ttk.Button(buttons_frame, text="🗑️ Очистить", 
                  command=self.clear_inventory_results,
                  style="secondary.TButton").pack(side="left")

        ttk.Button(buttons_frame, text="📤 Отправить трейд", 
                  command=self.open_trade_send_dialog,
                  style="success.TButton").pack(side="left", padx=(10, 0))

        self.refresh_trade_accounts()

    def bind_mousewheel_to_trade_canvas(self):
        def on_mousewheel(event):
            try:
                bbox = self.trade_canvas.bbox("all")
                if bbox and bbox[3] > self.trade_canvas.winfo_height():
                    if event.delta:
                        delta = event.delta
                    else:
                        delta = event.num
                        if delta == 4:
                            delta = 120
                        elif delta == 5:
                            delta = -120
                    
                    self.trade_canvas.yview_scroll(int(-1 * (delta / 120)), "units")
            except Exception as e:
                print(f"Ошибка прокрутки: {e}")
        
        self.trade_canvas.bind("<MouseWheel>", on_mousewheel)
        
        self.trade_canvas.bind("<Button-4>", on_mousewheel)
        self.trade_canvas.bind("<Button-5>", on_mousewheel)
        
        def bind_to_children(widget):
            widget.bind("<MouseWheel>", on_mousewheel)
            widget.bind("<Button-4>", on_mousewheel)
            widget.bind("<Button-5>", on_mousewheel)
            for child in widget.winfo_children():
                bind_to_children(child)
        
        bind_to_children(self.trade_scrollable_frame)
        
        def update_bindings():
            bind_to_children(self.trade_scrollable_frame)
        
        self.update_trade_mousewheel_bindings = update_bindings

    def refresh_trade_accounts(self):
        try:
            for widget in self.trade_scrollable_frame.winfo_children():
                widget.destroy()
            
            accounts = settings_manager.get_accounts()
            self.trade_account_vars.clear()
            
            if accounts:
                for login, account_data in accounts.items():
                    account_frame = ttk.Frame(self.trade_scrollable_frame)
                    account_frame.pack(fill="x", pady=2)
                    
                    var = tk.BooleanVar()
                    self.trade_account_vars[login] = var
                    
                    display_name = settings_manager.get_account_display_name(login)
                    
                    checkbox_text = f"{display_name} ({login})"
                    checkbox = ttk.Checkbutton(account_frame, text=checkbox_text, variable=var)
                    checkbox.pack(side="left", fill="x", expand=True)
                
                self.trade_accounts_count_label.config(text=f"({len(accounts)} аккаунтов)")
            else:
                self.trade_accounts_count_label.config(text="(0 аккаунтов)")
            
            if hasattr(self, 'update_trade_mousewheel_bindings'):
                self.update_trade_mousewheel_bindings()
                
        except Exception as e:
            print(f"Ошибка обновления списка аккаунтов для трейда: {e}")

    def toggle_trade_select_all(self):
        select_all = self.trade_select_all_var.get()
        for login, var in self.trade_account_vars.items():
            var.set(select_all)

    def analyze_inventories(self):
        selected = []
        for login, var in self.trade_account_vars.items():
            if var.get():
                selected.append(login)
        
        if not selected:
            messagebox.showwarning("Внимание", "Выберите хотя бы один аккаунт для анализа")
            return

        currency = self.currency_var.get()
        game_setting = self.game_var.get()
        game_id = game_setting.split()[0]
        
        if not messagebox.askyesno("Подтверждение анализа", 
                                  f"Начать анализ инвентарей?\n\n"
                                  f"Аккаунтов: {len(selected)}\n"
                                  f"Игра: {game_setting}\n"
                                  f"Валюта: {currency}\n\n"
                                  f"Операция может занять несколько минут."):
            return
        
        self.clear_inventory_results()
        
        thread = threading.Thread(target=self.analyze_inventories_thread, 
                                 args=(selected, game_id, currency))
        thread.daemon = True
        thread.start()

    def analyze_inventories_thread(self, selected_accounts, game_id, currency):
        try:
            self.main_window.root.after(0, lambda: self.update_status("Начинаем анализ инвентарей..."))
            
            try:
                from steam.steam_inventory_parser import SteamInventoryParser, format_price
                
                parser = SteamInventoryParser()
                
                total_items = 0
                total_value = 0.0
                
                for i, account_login in enumerate(selected_accounts):
                    status_text = f"Анализ {i+1}/{len(selected_accounts)}: {account_login}"
                    self.main_window.root.after(0, lambda t=status_text: self.update_status(t))
                    
                    try:
                        inventory_result = parser.analyze_account_inventory(account_login, game_id, currency)
                        
                        if not inventory_result['success']:
                            error_text = f"⚠️ {account_login}: {inventory_result.get('error', 'Неизвестная ошибка')}"
                            self.main_window.root.after(0, lambda t=error_text: self.update_status(t))
                            continue
                        
                        account_items = inventory_result['items']
                        account_value = inventory_result['total_value']
                        
                        for item in account_items:
                            total_items += item['amount']
                            item_value = item['total_price']
                            total_value += item_value
                            
                            def add_item(acc=account_login, it=item, val=item_value):
                                self.main_window.root.after(0, lambda: self.add_inventory_item(acc, it, val))
                            add_item()
                            
                    except Exception as account_error:
                        error_text = f"Ошибка анализа {account_login}: {account_error}"
                        self.main_window.root.after(0, lambda t=error_text: self.update_status(t))
                
                def update_totals():
                    symbol = self.get_currency_symbol()
                    self.total_value_label.config(text=f"{symbol}{total_value:.2f}")
                    self.items_count_label.config(text=str(total_items))
                    self.analyzed_accounts_label.config(text=str(len(selected_accounts)))
                    self.update_status(f"✅ Анализ завершен: {total_items} предметов, {symbol}{total_value:.2f}")
                
                self.main_window.root.after(0, update_totals)
                
            except ImportError:
                self.main_window.root.after(0, lambda: messagebox.showinfo("Информация", 
                    "Модуль steam_inventory_parser не найден.\n"
                    "Убедитесь что файл steam_inventory_parser.py находится в корне проекта."))
            
        except Exception as e:
            error_text = f"💥 Критическая ошибка анализа: {str(e)}"
            self.main_window.root.after(0, lambda t=error_text: self.update_status(t))

    def export_inventory_csv(self):
        try:
            import csv
            import time
            
            items = self.items_tree.get_children()
            if not items:
                messagebox.showwarning("Внимание", "Нет данных для экспорта")
                return
            
            filename = filedialog.asksaveasfilename(
                title="Сохранить результаты анализа",
                defaultextension=".csv",
                filetypes=[("CSV файлы", "*.csv"), ("Все файлы", "*.*")]
            )
            
            if not filename:
                return
            
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                
                current_currency = self.currency_var.get()
                current_game = self.game_var.get()
                writer.writerow([f"Анализ инвентарей - {current_game}"])
                writer.writerow([f"Валюта: {current_currency}"])
                writer.writerow([f"Дата: {time.strftime('%Y-%m-%d %H:%M:%S')}"])
                writer.writerow([])
                
                writer.writerow(["Аккаунт", "Предмет", "Количество", "Статус", "Цена за шт.", "Общая стоимость"])
                
                for item_id in items:
                    values = self.items_tree.item(item_id)['values']
                    writer.writerow(values)
                
                writer.writerow([])
                writer.writerow(["ИТОГО:", "", "", "", "", self.total_value_label.cget('text')])
                writer.writerow(["Всего предметов:", self.items_count_label.cget('text')])
                writer.writerow(["Аккаунтов проанализировано:", self.analyzed_accounts_label.cget('text')])
            
            messagebox.showinfo("Экспорт завершен", f"Результаты сохранены в:\n{filename}")
            
        except Exception as e:
            messagebox.showerror("Ошибка экспорта", f"Ошибка при экспорте: {str(e)}")

    def refresh_prices(self):
        messagebox.showinfo("Информация", "Обновление цен требует подключение к Steam Market API\nПока недоступно в данной версии")

    def change_currency(self):
        messagebox.showinfo("Информация", "Для смены валюты измените настройку и повторите анализ")

    def get_currency_symbol(self):
        symbols = {
            "USD": "$",
            "EUR": "€",
            "RUB": "₽",
            "CNY": "¥",
            "GBP": "£",
            "CAD": "$",
            "AUD": "$",
            "UAH": "₴"
        }
        return symbols.get(self.currency_var.get(), "$")

    def add_inventory_item(self, account_login, item, item_value):
        try:
            from core.settings_manager import settings_manager
            display_name = settings_manager.get_account_display_name(account_login)
            
            status = "Продаваемый" if item.get('marketable', False) else "Не продается"
            if not item.get('tradable', True):
                status = "Не обмениваемый"
            
            full_item_data = item.copy()
            full_item_data['account'] = account_login
            full_item_data['display_name'] = display_name 
            full_item_data['item_value'] = item_value
            full_item_data['status'] = status
            self.full_inventory_data.append(full_item_data)
            
            symbol = self.get_currency_symbol()
            self.items_tree.insert('', 'end', values=(
                display_name,
                item['name'],
                item['amount'],
                status,
                f"{symbol}{item['price']:.2f}",
                f"{symbol}{item_value:.2f}"
            ), tags=(item.get('market_name', item['name']),))
            
        except Exception as e:
            print(f"Ошибка добавления предмета: {e}")

    def clear_inventory_results(self):
        for item in self.items_tree.get_children():
            self.items_tree.delete(item)
        
        self.full_inventory_data = []
        
        symbol = self.get_currency_symbol()
        self.total_value_label.config(text=f"{symbol}0.00")
        self.items_count_label.config(text="0")
        self.analyzed_accounts_label.config(text="0")

    def open_trade_send_dialog(self):
        try:
            items = self.items_tree.get_children()
            if not items:
                messagebox.showwarning("Внимание", "Нет данных инвентаря для отправки трейда")
                return
            
            if not self.full_inventory_data:
                messagebox.showwarning("Внимание", "Нет полных данных инвентаря. Проведите анализ сначала.")
                return
            
            from ..dialogs.trade_send_dialog import TradeSendDialog
            dialog = TradeSendDialog(self.main_window.root, self.update_status, self.full_inventory_data)
            
        except ImportError:
            messagebox.showinfo("Информация", "Диалог отправки трейдов будет добавлен в следующей версии")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка открытия диалога отправки трейда: {str(e)}")
