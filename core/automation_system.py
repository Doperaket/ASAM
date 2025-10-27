import json
import time
import threading
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Any, Optional, List, Set
from datetime import datetime

from utils.logger import logger, print_and_log


@dataclass
class AutoSettings:
    check_interval: int = 60  
    enabled: bool = False  
    
    auto_accept_gifts: bool = False  
    auto_confirm_trades: bool = False  
    auto_confirm_market: bool = False  
    
    min_gift_value: float = 0.0  
    max_trade_value: float = 1000.0  
    
    max_trades_per_hour: int = 100  
    require_api_key: bool = True  
    
    last_modified: float = 0  
    created: float = 0  
    
    def __post_init__(self):
        if self.created == 0:
            self.created = time.time()
        self.last_modified = time.time()
    
    def update(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.last_modified = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AutoSettings':
        return cls(**data)
    
    def validate(self) -> List[str]:
        errors = []
        
        if self.check_interval < 10:
            errors.append("Интервал проверки не может быть меньше 10 секунд")
        elif self.check_interval > 3600:
            errors.append("Интервал проверки не может быть больше 1 часа")
            
        if self.min_gift_value < 0:
            errors.append("Минимальная стоимость подарка не может быть отрицательной")
            
        if self.max_trade_value <= 0:
            errors.append("Максимальная стоимость трейда должна быть положительной")
            
        if self.max_trades_per_hour < 1 or self.max_trades_per_hour > 1000:
            errors.append("Количество трейдов в час должно быть от 1 до 1000")
        
        return errors


class AutoSettingsManager:
    
    def __init__(self, settings_dir: str = "automation_settings"):
        self.settings_dir = Path(settings_dir)
        self.settings_dir.mkdir(exist_ok=True)
        self._settings_cache: Dict[str, AutoSettings] = {}
        self._lock = threading.Lock()
    
    def get_settings_file(self, account_name: str) -> Path:
        return self.settings_dir / f"{account_name}_auto_settings.json"
    
    def load_settings(self, account_name: str) -> AutoSettings:
        with self._lock:
            if account_name in self._settings_cache:
                return self._settings_cache[account_name]
            
            settings_file = self.get_settings_file(account_name)
            
            try:
                if settings_file.exists():
                    logger.info(f"Загружаем настройки автоматизации для {account_name}")
                    
                    with open(settings_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    settings_data = {k: v for k, v in data.items() if not k.startswith('_')}
                    settings = AutoSettings.from_dict(settings_data)
                    
                    errors = settings.validate()
                    if errors:
                        logger.warning(f"Найдены ошибки в настройках {account_name}: {errors}")
                        logger.info("Создаем новые настройки по умолчанию")
                        settings = AutoSettings()
                    
                    logger.info(f"Настройки автоматизации для {account_name} загружены")
                else:
                    logger.info(f"Создаем настройки по умолчанию для {account_name}")
                    settings = AutoSettings()
                
                self._settings_cache[account_name] = settings
                
                if not settings_file.exists():
                    self.save_settings(account_name, settings)
                
                return settings
                
            except json.JSONDecodeError as e:
                logger.error(f"Ошибка JSON в настройках {account_name}: {e}")
                settings = AutoSettings()
                self._settings_cache[account_name] = settings
                self.save_settings(account_name, settings)
                return settings
                
            except Exception as e:
                logger.error(f"Ошибка загрузки настроек {account_name}: {e}")
                settings = AutoSettings()
                self._settings_cache[account_name] = settings
                return settings
    
    def save_settings(self, account_name: str, settings: AutoSettings) -> bool:
        with self._lock:
            try:
                settings_file = self.get_settings_file(account_name)
                
                settings.last_modified = time.time()
                
                data = settings.to_dict()
                
                data['_info'] = {
                    'description': f'Настройки автоматизации для аккаунта {account_name}',
                    'version': '2.0',
                    'created_at': datetime.fromtimestamp(settings.created).isoformat(),
                    'modified_at': datetime.fromtimestamp(settings.last_modified).isoformat(),
                    'account_name': account_name
                }
                
                with open(settings_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=4, ensure_ascii=False)
                
                self._settings_cache[account_name] = settings
                
                logger.info(f"Настройки автоматизации для {account_name} сохранены")
                return True
                
            except Exception as e:
                logger.error(f"Ошибка сохранения настроек {account_name}: {e}")
                return False
    
    def update_settings(self, account_name: str, **kwargs) -> bool:
        settings = self.load_settings(account_name)
        settings.update(**kwargs)
        
        errors = settings.validate()
        if errors:
            logger.error(f"❌ Ошибки валидации настроек {account_name}: {errors}")
            return False
        
        return self.save_settings(account_name, settings)
    
    def get_enabled_accounts(self) -> List[str]:
        enabled = []
        
        for settings_file in self.settings_dir.glob("*_auto_settings.json"):
            account_name = settings_file.stem.replace("_auto_settings", "")
            settings = self.load_settings(account_name)
            
            if settings.enabled:
                enabled.append(account_name)
        
        return enabled
    
    def get_all_accounts(self) -> List[str]:
        accounts = []
        
        for settings_file in self.settings_dir.glob("*_auto_settings.json"):
            account_name = settings_file.stem.replace("_auto_settings", "")
            accounts.append(account_name)
        
        return accounts
    
    def delete_settings(self, account_name: str) -> bool:
        with self._lock:
            try:
                settings_file = self.get_settings_file(account_name)
                
                if settings_file.exists():
                    settings_file.unlink()
                    logger.info(f"🗑️ Настройки для {account_name} удалены")
                
                if account_name in self._settings_cache:
                    del self._settings_cache[account_name]
                
                return True
                
            except Exception as e:
                logger.error(f"❌ Ошибка удаления настроек {account_name}: {e}")
                return False
    
    def clear_cache(self):
        with self._lock:
            self._settings_cache.clear()
            logger.info("🧹 Кэш настроек автоматизации очищен")
    
    def get_summary(self) -> Dict[str, Any]:
        accounts = self.get_all_accounts()
        enabled_accounts = self.get_enabled_accounts()
        
        summary = {
            'total_accounts': len(accounts),
            'enabled_accounts': len(enabled_accounts),
            'disabled_accounts': len(accounts) - len(enabled_accounts),
            'accounts': {}
        }
        
        for account_name in accounts:
            settings = self.load_settings(account_name)
            summary['accounts'][account_name] = {
                'enabled': settings.enabled,
                'check_interval': settings.check_interval,
                'auto_accept_gifts': settings.auto_accept_gifts,
                'auto_confirm_trades': settings.auto_confirm_trades,
                'auto_confirm_market': settings.auto_confirm_market,
                'last_modified': datetime.fromtimestamp(settings.last_modified).isoformat()
            }
        return summary


@dataclass 
class AccountErrorTracker:
    error_counts: Dict[str, int] = None
    disabled_accounts: Set[str] = None
    last_success: Dict[str, float] = None
    max_errors: int = 3
    
    def __post_init__(self):
        if self.error_counts is None:
            self.error_counts = {}
        if self.disabled_accounts is None:
            self.disabled_accounts = set()
        if self.last_success is None:
            self.last_success = {}
    
    def record_error(self, account_name: str) -> bool:
        current_errors = self.error_counts.get(account_name, 0) + 1
        self.error_counts[account_name] = current_errors
        
        logger.warning(f"[{account_name}] Ошибка #{current_errors}")
        
        if current_errors >= self.max_errors:
            self.disabled_accounts.add(account_name)
            logger.error(f"[{account_name}] Достигнут лимит ошибок ({self.max_errors}). Аккаунт отключен.")
            return True
        
        return False
    
    def record_success(self, account_name: str):
        if account_name in self.error_counts and self.error_counts[account_name] > 0:
            old_count = self.error_counts[account_name]
            self.error_counts[account_name] = 0
            logger.info(f"[{account_name}] Ошибки сброшены после успешного выполнения (было {old_count})")
        
        self.last_success[account_name] = time.time()
    
    def reset_account(self, account_name: str):
        if account_name in self.error_counts:
            self.error_counts[account_name] = 0
        if account_name in self.disabled_accounts:
            self.disabled_accounts.remove(account_name)
        logger.info(f"[{account_name}] Аккаунт снова включен в автоматизацию")
    
    def is_disabled(self, account_name: str) -> bool:
        return account_name in self.disabled_accounts


class BackgroundAutomationService:
    
    def __init__(self):
        self.settings_manager = AutoSettingsManager()
        self.error_tracker = AccountErrorTracker()
        
        self.is_running = False
        self.is_paused = False
        self._stop_event = threading.Event()
        self._automation_thread = None
        
        self._last_check_times: Dict[str, float] = {}
        self._trade_managers: Dict[str, Any] = {}  
        self._stats = {
            'total_checks': 0,
            'successful_checks': 0,
            'failed_checks': 0,
            'gifts_accepted': 0,
            'trades_confirmed': 0,
            'start_time': None
        }
        
        logger.info("BackgroundAutomationService инициализирован")
    
    def start(self, selected_accounts: Optional[List[str]] = None) -> bool:
        if self.is_running:
            logger.warning("⚠️ Сервис автоматизации уже запущен")
            return False
        
        try:
            if selected_accounts:
                enabled_accounts = selected_accounts
                logger.info(f"Используем переданный список аккаунтов: {enabled_accounts}")
            else:
                logger.error("❌ Не передан список аккаунтов для автоматизации")
                return False
            
            if not enabled_accounts:
                logger.error("❌ Список аккаунтов пуст")
                return False
            
            logger.info(f"Запускаем автоматизацию для {len(enabled_accounts)} аккаунтов: {enabled_accounts}")
            
            self._stop_event.clear()
            self.is_running = True
            self.is_paused = False
            self._stats['start_time'] = time.time()
            
            self._automation_thread = threading.Thread(
                target=self._automation_loop, 
                args=(enabled_accounts,),
                daemon=True,
                name="AutomationService"
            )
            self._automation_thread.start()
            
            logger.info("✅ Фоновый сервис автоматизации запущен")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка запуска сервиса автоматизации: {e}")
            self.is_running = False
            return False
    
    def stop(self) -> bool:
        if not self.is_running:
            logger.warning("⚠️ Сервис автоматизации не запущен")
            return False
        
        try:
            logger.info("🛑 Останавливаем сервис автоматизации...")
            
            self._stop_event.set()
            self.is_running = False
            
            if self._automation_thread and self._automation_thread.is_alive():
                self._automation_thread.join(timeout=10)
                if self._automation_thread.is_alive():
                    logger.warning("⚠️ Поток автоматизации не завершился в течение 10 секунд")
            
            logger.info("✅ Сервис автоматизации остановлен")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка остановки сервиса: {e}")
            return False
    
    def pause(self):
        if self.is_running and not self.is_paused:
            self.is_paused = True
            logger.info("⏸️ Автоматизация приостановлена")
    
    def resume(self):
        if self.is_running and self.is_paused:
            self.is_paused = False
            logger.info("▶️ Автоматизация возобновлена")
    
    def _automation_loop(self, enabled_accounts: List[str]):
        logger.info(f"Запуск цикла автоматизации для аккаунтов: {enabled_accounts}")
        
        while not self._stop_event.is_set():
            try:
                if self.is_paused:
                    time.sleep(1)
                    continue
                
                current_time = time.time()
                processed_in_cycle = False
                
                active_accounts = [acc for acc in enabled_accounts 
                                 if not self.error_tracker.is_disabled(acc)]
                
                for account_name in active_accounts:
                    if self._stop_event.is_set():
                        break
                    
                    try:
                        settings = self.settings_manager.load_settings(account_name)
                        
                        last_check = self._last_check_times.get(account_name, 0)
                        if (current_time - last_check) >= settings.check_interval:
                            
                            logger.info(f"[{account_name}] 🔄 Время проверки (интервал: {settings.check_interval}с)")
                            
                            self._process_account_automation(account_name, settings)
                            
                            self._last_check_times[account_name] = time.time()
                            processed_in_cycle = True
                            
                            time.sleep(2)
                    
                    except Exception as e:
                        logger.error(f"[{account_name}] ❌ Ошибка обработки аккаунта: {e}")
                        self.error_tracker.record_error(account_name)
                        self._stats['failed_checks'] += 1
                
                if not processed_in_cycle:
                    time.sleep(5)
                else:
                    time.sleep(1)
                
                self._stats['total_checks'] += 1
                
            except Exception as e:
                logger.error(f"❌ Критическая ошибка в цикле автоматизации: {e}")
                time.sleep(10)  
        
        logger.info("🏁 Цикл автоматизации завершен")
    
    def _process_account_automation(self, account_name: str, settings: AutoSettings):
        try:
            trade_manager = self._get_trade_manager(account_name)
            if not trade_manager:
                logger.error(f"[{account_name}] ❌ Не удалось создать менеджер трейдов")
                self.error_tracker.record_error(account_name)
                return
            
            logger.info(f"[{account_name}] 🔍 Выполняем автоматизацию...")
            
            success_count = 0
            
            if settings.auto_accept_gifts:
                try:
                    result = trade_manager.auto_accept_gifts(account_name)
                    if result.get('status') == 'success':
                        gifts_count = result.get('accepted_count', 0)
                        if gifts_count > 0:
                            logger.info(f"[{account_name}] 🎁 Принято подарков: {gifts_count}")
                            self._stats['gifts_accepted'] += gifts_count
                        success_count += 1
                except Exception as e:
                    logger.error(f"[{account_name}] ❌ Ошибка принятия подарков: {e}")
            
            if settings.auto_confirm_trades:
                try:
                    result = trade_manager.auto_confirm_trades(account_name)
                    if result.get('status') == 'success':
                        trades_count = result.get('confirmed_count', 0)
                        if trades_count > 0:
                            logger.info(f"[{account_name}] 🔑 Подтверждено трейдов: {trades_count}")
                            self._stats['trades_confirmed'] += trades_count
                        success_count += 1
                except Exception as e:
                    logger.error(f"[{account_name}] ❌ Ошибка подтверждения трейдов: {e}")
            
            if success_count > 0:
                self.error_tracker.record_success(account_name)
                self._stats['successful_checks'] += 1
                logger.info(f"[{account_name}] ✅ Автоматизация выполнена успешно")
            else:
                logger.warning(f"[{account_name}] ⚠️ Ни одна операция не выполнена")
                
        except Exception as e:
            logger.error(f"[{account_name}] ❌ Ошибка автоматизации: {e}")
            self.error_tracker.record_error(account_name)
    
    def _get_trade_manager(self, account_name: str):
        try:
            if account_name in self._trade_managers:
                return self._trade_managers[account_name]
            
            from pysda.simple_integration import SimpleTradeManager
            trade_manager = SimpleTradeManager()
            
            self._trade_managers[account_name] = trade_manager
            
            logger.info(f"[{account_name}] ✅ Менеджер трейдов создан и закэширован")
            return trade_manager
            
        except Exception as e:
            logger.error(f"[{account_name}] ❌ Ошибка создания менеджера трейдов: {e}")
            return None
    
    def get_status(self) -> Dict[str, Any]:
        uptime = time.time() - self._stats['start_time'] if self._stats['start_time'] else 0
        
        return {
            'is_running': self.is_running,
            'is_paused': self.is_paused,
            'uptime_seconds': uptime,
            'enabled_accounts': [],  
            'disabled_accounts': list(self.error_tracker.disabled_accounts),
            'error_counts': dict(self.error_tracker.error_counts),
            'stats': self._stats.copy(),
            'last_check_times': dict(self._last_check_times)
        }
    
    def reset_account_errors(self, account_name: str):
        self.error_tracker.reset_account(account_name)
        logger.info(f"[{account_name}] 🔄 Ошибки сброшены, аккаунт включен")
    
    def get_account_status(self, account_name: str) -> Dict[str, Any]:
        settings = self.settings_manager.load_settings(account_name)
        last_check = self._last_check_times.get(account_name, 0)
        last_success = self.error_tracker.last_success.get(account_name, 0)
        
        return {
            'account_name': account_name,
            'enabled': settings.enabled,
            'check_interval': settings.check_interval,
            'auto_accept_gifts': settings.auto_accept_gifts,
            'auto_confirm_trades': settings.auto_confirm_trades,
            'error_count': self.error_tracker.error_counts.get(account_name, 0),
            'is_disabled': self.error_tracker.is_disabled(account_name),
            'last_check': datetime.fromtimestamp(last_check).isoformat() if last_check else None,
            'last_success': datetime.fromtimestamp(last_success).isoformat() if last_success else None,
            'next_check': datetime.fromtimestamp(last_check + settings.check_interval).isoformat() if last_check else None
        }


_automation_service = None

def get_automation_service() -> BackgroundAutomationService:
    global _automation_service
    if _automation_service is None:
        _automation_service = BackgroundAutomationService()
    return _automation_service


_settings_manager = None

def get_settings_manager() -> AutoSettingsManager:
    global _settings_manager
    if _settings_manager is None:
        _settings_manager = AutoSettingsManager()
    return _settings_manager
