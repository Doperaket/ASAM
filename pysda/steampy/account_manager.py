
import asyncio
from pysda.utils.logger_setup import logger
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any
import concurrent.futures

from .client import SteamClient
from .config import ConfigManager, AccountConfig
from .session_manager import SecureSessionManager
from .models import TradeOfferState, GameOptions
from .exceptions import ApiException


class AccountManager:
    
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.session_managers: Dict[str, SecureSessionManager] = {}
        self.clients: Dict[str, SteamClient] = {}
        self.running_tasks: Dict[str, threading.Thread] = {}
        self.is_running = False
        
        self.logger = self._setup_logging()
        
        self._initialize_session_managers()
    
    def _setup_logging(self):
        return logger
    
    def _initialize_session_managers(self) -> None:
        for account_name, config in self.config_manager.get_all_accounts().items():
            session_manager = SecureSessionManager(
                username=account_name,
                check_interval=config.seconds_to_check_session
            )
            self.session_managers[account_name] = session_manager
            
            password, api_key = self.config_manager.get_sensitive_data(account_name)
            if password and api_key:
                try:
                    session_manager.store_credentials(password, api_key, config.mafile_path)
                except Exception as e:
                    self.logger.error(f"Ошибка настройки credentials для {account_name}: {e}")
    
    def add_account_from_config(self, account_name: str) -> None:
        
        if account_name in self.session_managers:
            self.logger.warning(f"Аккаунт {account_name} уже инициализирован")
            return
        
        config = self.config_manager.get_account(account_name)
        session_manager = SecureSessionManager(
            username=account_name,
            check_interval=config.seconds_to_check_session
        )
        self.session_managers[account_name] = session_manager
        
        password, api_key = self.config_manager.get_sensitive_data(account_name)
        if password and api_key:
            session_manager.store_credentials(password, api_key, config.mafile_path)
        
        self.logger.info(f"Добавлен аккаунт: {account_name}")
    
    def remove_account(self, account_name: str) -> None:
        
        self._stop_account_tasks(account_name)
        
        if account_name in self.session_managers:
            del self.session_managers[account_name]
        if account_name in self.clients:
            del self.clients[account_name]
        
        self.logger.info(f"Удален аккаунт: {account_name}")
    
    def login_account(self, account_name: str, force_refresh: bool = False) -> bool:
        
            
        if account_name not in self.session_managers:
            self.logger.error(f"Аккаунт {account_name} не найден")
            return False
        
        session_manager = self.session_managers[account_name]
        
        try:
            if session_manager.login(force_refresh):
                if session_manager.client:
                    self.clients[account_name] = session_manager.client
                    self.logger.info(f"Успешный вход для {account_name}")
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Ошибка входа для {account_name}: {e}")
            return False
    
    def logout_account(self, account_name: str) -> None:
        
        self._stop_account_tasks(account_name)
        
        if account_name in self.session_managers:
            self.session_managers[account_name].stop_monitoring()
        
        if account_name in self.clients:
            try:
                self.clients[account_name].logout()
            except Exception as e:
                self.logger.error(f"Ошибка выхода для {account_name}: {e}")
            finally:
                del self.clients[account_name]
        
        self.logger.info(f"Выход из аккаунта: {account_name}")
    
    def start_account_monitoring(self, account_name: str) -> None:
        
        if account_name not in self.session_managers:
            self.logger.error(f"Аккаунт {account_name} не найден")
            return
        
        config = self.config_manager.get_account(account_name)
        
        session_manager = self.session_managers[account_name]
        session_manager.start_monitoring()
        
        if config.allowed_to_check_and_accept_new_trades:
            self._start_trade_monitoring(account_name)
        
        self.logger.info(f"Запущен мониторинг для {account_name}")
    
    def stop_account_monitoring(self, account_name: str) -> None:
        
        self._stop_account_tasks(account_name)
        
        if account_name in self.session_managers:
            self.session_managers[account_name].stop_monitoring()
        
        self.logger.info(f"Остановлен мониторинг для {account_name}")
    
    def _start_trade_monitoring(self, account_name: str) -> None:
        
        if account_name in self.running_tasks:
            return
        
        def trade_monitor():
            config = self.config_manager.get_account(account_name)
            
            while self.is_running and account_name in self.running_tasks:
                try:
                    if account_name in self.clients:
                        self._check_and_process_trades(account_name)
                    
                    time.sleep(config.seconds_to_check_trades)
                    
                except Exception as e:
                    self.logger.error(f"Ошибка в мониторинге трейдов для {account_name}: {e}")
                    time.sleep(30)
        
        task_thread = threading.Thread(target=trade_monitor, name=f"trade_monitor_{account_name}")
        task_thread.daemon = True
        self.running_tasks[account_name] = task_thread
        task_thread.start()
    
    def _stop_account_tasks(self, account_name: str) -> None:
        
        if account_name in self.running_tasks:
            del self.running_tasks[account_name]
    
    def _check_and_process_trades(self, account_name: str) -> None:
        
        if account_name not in self.clients:
            return
        
        client = self.clients[account_name]
        config = self.config_manager.get_account(account_name)
        
        try:
            trades_response = client.get_trade_offers()
            received_offers = trades_response.get('response', {}).get('trade_offers_received', [])
            
            for offer in received_offers:
                if offer.get('trade_offer_state') != TradeOfferState.Active:
                    continue
                
                trade_id = offer.get('tradeofferid')
                if not trade_id:
                    continue
                
                should_accept = self._should_accept_trade(offer, config)
                
                if should_accept:
                    try:
                        result = client.accept_trade_offer(trade_id)
                        if result:
                            self.logger.info(f"Принят трейд {trade_id} для {account_name}")
                        else:
                            self.logger.warning(f"Не удалось принять трейд {trade_id} для {account_name}")
                    
                    except Exception as e:
                        self.logger.error(f"Ошибка принятия трейда {trade_id} для {account_name}: {e}")
        
        except Exception as e:
            self.logger.error(f"Ошибка получения трейдов для {account_name}: {e}")
    
    def _should_accept_trade(self, offer: Dict[str, Any], config: AccountConfig) -> bool:
        
            
        if config.accept_every_accepted_on_web_trade:
            pass
        
        if config.accept_every_free_trade:
            items_to_give = offer.get('items_to_give', [])
            if not items_to_give:
                return True
        
        return False
    
    def get_account_status(self, account_name: str) -> Dict[str, Any]:
        
            
        status = {
            'account_name': account_name,
            'session_valid': False,
            'monitoring_active': False,
            'trade_monitoring_active': False,
            'last_check': None,
            'config': None
        }
        
        try:
            config = self.config_manager.get_account(account_name)
            status['config'] = config.to_dict()
            
            if account_name in self.session_managers:
                session_status = self.session_managers[account_name].get_status()
                status.update(session_status)
            
            status['trade_monitoring_active'] = account_name in self.running_tasks
            
        except Exception as e:
            self.logger.error(f"Ошибка получения статуса для {account_name}: {e}")
            status['error'] = str(e)
        
        return status
    
    def get_all_statuses(self) -> Dict[str, Dict[str, Any]]:
        
        statuses = {}
        
        for account_name in self.config_manager.list_accounts():
            statuses[account_name] = self.get_account_status(account_name)
        
        return statuses
    
    def start_all_monitoring(self) -> None:
        self.is_running = True
        
        for account_name in self.config_manager.list_accounts():
            try:
                if self.login_account(account_name):
                    self.start_account_monitoring(account_name)
                else:
                    self.logger.error(f"Не удалось войти в аккаунт {account_name}")
            
            except Exception as e:
                self.logger.error(f"Ошибка запуска мониторинга для {account_name}: {e}")
    
    def stop_all_monitoring(self) -> None:
        self.is_running = False
        
        for account_name in list(self.session_managers.keys()):
            self.stop_account_monitoring(account_name)
        
        self.running_tasks.clear()
    
    def perform_action_on_account(self, account_name: str, action: Callable, *args, **kwargs) -> Any:
        
            
        if account_name not in self.clients:
            raise ValueError(f"Клиент для аккаунта {account_name} не активен")
        
        client = self.clients[account_name]
        
        try:
            return action(client, *args, **kwargs)
        except Exception as e:
            self.logger.error(f"Ошибка выполнения действия для {account_name}: {e}")
            raise
    
    def perform_action_on_all(self, action: Callable, *args, **kwargs) -> Dict[str, Any]:
        
            
        results = {}
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(self.clients)) as executor:
            future_to_account = {
                executor.submit(self.perform_action_on_account, account_name, action, *args, **kwargs): account_name
                for account_name in self.clients.keys()
            }
            
            for future in concurrent.futures.as_completed(future_to_account):
                account_name = future_to_account[future]
                try:
                    result = future.result()
                    results[account_name] = {'success': True, 'result': result}
                except Exception as e:
                    results[account_name] = {'success': False, 'error': str(e)}
        
        return results 
