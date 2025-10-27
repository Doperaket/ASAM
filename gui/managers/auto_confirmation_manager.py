import threading
import time
from core.settings_manager import settings_manager


class AutoConfirmationManager:
    
    def __init__(self, settings, log_callback):
        self.settings = settings
        self.log_callback = log_callback
        self.running = False
        self.thread = None
        self.stop_event = threading.Event()
        
        try:
            from pysda.simple_integration import SimpleTradeManager
            self.trade_manager = SimpleTradeManager()
        except ImportError as e:
            raise Exception(f"Не удалось импортировать pySDA: {e}")
    
    def start(self):
        print(f"🎯 AutoConfirmationManager.start() вызван")
        
        if self.running:
            print("⚠️ Автоматизация уже запущена")
            return False
        
        print(f"⚙️ Настройки автоматизации: {self.settings}")
        
        self.running = True
        self.stop_event.clear()
        
        self.thread = threading.Thread(target=self._automation_loop, daemon=True)
        self.thread.start()
        
        print("✅ Поток автоматизации запущен")
        return True
    
    def stop(self):
        if not self.running:
            return
        
        self.running = False
        self.stop_event.set()
        
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1)
    
    def _automation_loop(self):
        try:
            accounts = self.settings.get('enabled_accounts', [])
            check_interval = self.settings.get('interval', 300)
            
            print(f"🎯 _automation_loop запущен")
            print(f"📋 Аккаунты для мониторинга: {accounts}")
            print(f"⏰ Интервал проверки: {check_interval} сек")
            
            self.log_callback(f"🔄 Мониторинг запущен для {len(accounts)} аккаунтов")
            self.log_callback(f"⏰ Интервал проверки: {check_interval} сек")
            
            while self.running and not self.stop_event.is_set():
                try:
                    print(f"🔄 Начало цикла проверки аккаунтов...")
                    for account_login in accounts:
                        if not self.running or self.stop_event.is_set():
                            break
                        
                        print(f"🔍 Проверка аккаунта: {account_login}")
                        self._check_account(account_login)
                    
                    if self.running:
                        print(f"💤 Ожидание {check_interval} сек до следующей проверки...")
                        self.log_callback(f"💤 Ожидание {check_interval} сек до следующей проверки...")
                        self.stop_event.wait(timeout=check_interval)
                        
                except Exception as e:
                    self.log_callback(f"❌ Ошибка в цикле автоматизации: {e}")
                    time.sleep(60)
                    
        except Exception as e:
            self.log_callback(f"❌ Критическая ошибка автоматизации: {e}")
        finally:
            self.running = False
            self.log_callback("🛑 Автоматизация завершена")
    
    def _check_account(self, account_login):
        try:
            self.log_callback(f"🚀 Начало проверки аккаунта: {account_login}")
            
            accounts = settings_manager.get_accounts()
            if account_login not in accounts:
                self.log_callback(f"⚠️ Аккаунт {account_login} не найден")
                return
            
            account_data = accounts[account_login]
            mafile_name = account_data.get('mafile')
            
            if not mafile_name:
                self.log_callback(f"⚠️ У аккаунта {account_login} нет mafile")
                return
            
            display_name = account_data.get('display_name', account_login)
            
            mafile_basename = mafile_name
            if mafile_basename.endswith('.maFile'):
                mafile_basename = mafile_basename[:-7]
            
            self.log_callback(f"🔍 Проверка {display_name}...")
            self.log_callback(f"🔧 Получение подтверждений для {mafile_basename}...")
            
            result = self.trade_manager.get_trade_confirmations(mafile_basename)
            
            if not result['success']:
                self.log_callback(f"❌ {display_name}: {result.get('error', 'Неизвестная ошибка')}")
                return
            
            confirmations = result.get('confirmations', [])
            
            if not confirmations:
                self.log_callback(f"✅ {display_name}: нет ожидающих подтверждений")
                return
            
            self.log_callback(f"📋 {display_name}: найдено {len(confirmations)} подтверждений")
            
            accepted_count = 0
            
            for conf in confirmations:
                if not self.running or self.stop_event.is_set():
                    break
                
                conf_type = conf.get('type', 'неизвестно')
                conf_desc = conf.get('description', 'нет описания')
                self.log_callback(f"🔍 {display_name}: обработка подтверждения тип={conf_type} описание='{conf_desc}'")
                
                if self._should_accept_confirmation(conf):
                    self.log_callback(f"✅ {display_name}: подтверждение пройдет фильтр, принимаем...")
                    
                    self._ensure_trade_protection_acknowledged(account_login)
                    
                    accept_result = self.trade_manager.accept_confirmation(mafile_basename, conf['id'])
                    
                    if accept_result['success']:
                        accepted_count += 1
                        self.log_callback(f"✅ {display_name}: принято {conf_type}")
                    else:
                        error_msg = accept_result.get('error', 'Неизвестная ошибка')
                        self.log_callback(f"❌ {display_name}: ошибка принятия - {error_msg}")
                    
                    time.sleep(2)
                else:
                    self.log_callback(f"⏭️ {display_name}: пропущено {conf_type} (не соответствует фильтрам)")
            
            if accepted_count > 0:
                self.log_callback(f"🎉 {display_name}: принято {accepted_count} подтверждений")
                
        except Exception as e:
            self.log_callback(f"❌ Ошибка проверки {account_login}: {e}")
    
    def _should_accept_confirmation(self, confirmation):
        try:
            conf_type = confirmation.get('type', 0)
            
            numeric_type_categories = {
                1: 'trades',
                2: 'trades',
                3: 'market',
                6: 'store',
                7: 'market',
                12: 'market',
                13: 'store',
                14: 'gifts'
            }
            
            string_type_categories = {
                'Trade': 'trades',
                'Market Transaction': 'trades',
                'Market Listing': 'market',
                'Store Transaction': 'store',
                'Community Market Purchase': 'market',
                'Steam Store Purchase': 'store',
                'Gift Purchase': 'gifts'
            }
            
            if isinstance(conf_type, (int, float)):
                category = numeric_type_categories.get(conf_type, 'unknown')
            else:
                category = string_type_categories.get(str(conf_type), 'unknown')
            

            
            if category == 'trades' and not self.settings.get('accept_trades', True):
                return False
            elif category == 'market' and not self.settings.get('accept_market', True):  
                return False
            elif category == 'store' and not self.settings.get('accept_store', True):
                return False
            elif category == 'gifts' and not self.settings.get('accept_gifts', True):
                return False
            elif category == 'unknown':
                if not self.settings.get('accept_unknown', False):
                    return False
            
            max_value = self.settings.get('max_value', float('inf'))
            if max_value < float('inf'):
                pass
            
            if self.settings.get('friends_only', False):
                pass
            
            return True
            
        except Exception as e:
            self.log_callback(f"⚠️ Ошибка фильтрации подтверждения: {e}")
            return False
    
    def _ensure_trade_protection_acknowledged(self, account_login: str):
        try:
            from core.settings_manager import settings_manager
            
            if settings_manager.is_trade_protection_acknowledged(account_login):
                return
            
            try:
                from steam.steam_integration import steam_trade_manager
                
                password = settings_manager.get_account_password(account_login)
                if not password:
                    self.log_callback(f"⚠️ {account_login}: нет пароля для подтверждения trade protection")
                    return
                
                if account_login not in steam_trade_manager.active_sessions:
                    self.log_callback(f"🔑 {account_login}: вход в Steam для подтверждения trade protection...")
                    login_result = steam_trade_manager.login_account(account_login, password)
                    if not login_result:
                        self.log_callback(f"❌ {account_login}: не удалось войти в Steam для trade protection")
                        return
                
                self.log_callback(f"🔐 {account_login}: подтверждение trade protection...")
                result = steam_trade_manager.acknowledge_trade_protection_for_account(account_login)
                
                if result.get('success'):
                    if result.get('already_acknowledged'):
                        self.log_callback(f"ℹ️ {account_login}: trade protection уже была подтверждена")
                    else:
                        self.log_callback(f"✅ {account_login}: trade protection успешно подтверждена")
                else:
                    error_msg = result.get('error', 'Неизвестная ошибка')
                    self.log_callback(f"⚠️ {account_login}: не удалось подтвердить trade protection - {error_msg}")
                
            except ImportError:
                self.log_callback(f"⚠️ {account_login}: Steam API недоступен для trade protection")
            except Exception as e:
                self.log_callback(f"⚠️ {account_login}: ошибка подтверждения trade protection - {e}")
                
        except Exception as e:
            self.log_callback(f"⚠️ Ошибка в _ensure_trade_protection_acknowledged: {e}")
