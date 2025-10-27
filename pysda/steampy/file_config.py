
import argparse
import getpass
import json
import os
import shutil
from pysda.utils.logger_setup import logger
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import yaml

from .config import ConfigManager, AccountConfig
from .models import SteamUrl

DEFAULT_CONFIG = {}


@dataclass
class GlobalSettings:
    log_level: str = "INFO"
    log_dir: str = "~/.steampy/logs"
    config_dir: str = "~/.steampy/config"
    max_concurrent_sessions: int = 5
    default_session_timeout: int = 300
    enable_encryption: bool = True
    backup_configs: bool = True
    backup_interval_hours: int = 24


@dataclass
class MonitoringSettings:
    enable_global_monitoring: bool = True
    status_check_interval: int = 60
    health_check_interval: int = 300
    auto_restart_failed_sessions: bool = True


@dataclass
class TradeSettings:
    global_trade_enabled: bool = True
    max_trades_per_hour: int = 10
    trade_timeout_seconds: int = 30
    confirmation_retry_count: int = 3
    confirmation_retry_delay: int = 5
    blacklisted_partners: List[str] = None
    whitelisted_partners: List[str] = None
    auto_decline_items: List[str] = None
    
    def __post_init__(self):
        if self.blacklisted_partners is None:
            self.blacklisted_partners = []
        if self.whitelisted_partners is None:
            self.whitelisted_partners = []
        if self.auto_decline_items is None:
            self.auto_decline_items = ["Graffiti", "Sticker"]


class FileConfigManager:
    
    def __init__(self, config_file: Optional[str] = None):
        if config_file:
            self.config_file = Path(config_file)
        else:
            for ext in ['yaml', 'yml', 'json']:
                candidate = Path(f"config.{ext}")
                if candidate.exists():
                    self.config_file = candidate
                    break
            else:
                self.config_file = Path("config.yaml")
        
        self.is_yaml = self.config_file.suffix.lower() in ['.yaml', '.yml']
        
        if self.is_yaml:
            self.example_file = Path("config.example.yaml")
        else:
            self.example_file = Path("config.example.json")
        
        self._setup_logging()
        
        self.config_data: Dict[str, Any] = {}
        self._load_config()
        
        self.global_settings = self._load_global_settings()
        self.monitoring_settings = self._load_monitoring_settings()
        self.trade_settings = self._load_trade_settings()
        
        self.account_config_manager = self._create_account_manager()
    
    def _setup_logging(self):
        pass
    
    def _load_config(self) -> None:
        if not self.config_file.exists():
            self._create_config_from_example()
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                if self.is_yaml and yaml:
                    self.config_data = yaml.safe_load(f) or {}
                else:
                    self.config_data = json.load(f)
            
            self.logger.info(f"Конфигурация загружена из {self.config_file}")
            
        except Exception as e:
            self.logger.error(f"Ошибка загрузки конфигурации: {e}")
            self.config_data = {}
    
    def _create_config_from_example(self) -> None:
        if not self.example_file.exists():
            self.logger.warning(f"Файл примера {self.example_file} не найден")
            return
        
        try:
            shutil.copy2(self.example_file, self.config_file)
            self.logger.info(f"Создан конфигурационный файл {self.config_file} из примера")
            
            self._show_first_time_setup_instructions()
            
        except Exception as e:
            self.logger.error(f"Ошибка создания конфига из примера: {e}")
    
    def _show_first_time_setup_instructions(self) -> None:
        print("\n" + "="*60)
        print("🎉 ДОБРО ПОЖАЛОВАТЬ В STEAM ACCOUNT MANAGER!")
        print("="*60)
        print(f"Создан файл конфигурации: {self.config_file}")
        print("\n📝 ЧТО НУЖНО СДЕЛАТЬ ДАЛЬШЕ:")
        print(f"1. Отредактируйте {self.config_file} под свои нужды")
        print("2. Замените примеры аккаунтов на реальные данные")
        print("3. Сохраните пароли и API ключи с помощью команды:")
        print("   python -m steampy.file_config --setup-credentials")
        print("4. Запустите тестирование:")
        print("   python examples/account_manager_test.py")
        print("\n🔒 БЕЗОПАСНОСТЬ:")
        print(f"- Файл {self.config_file} НЕ добавляйте в git (уже в .gitignore)")
        print("- Пароли и API ключи сохраняются в системном хранилище")
        print("- Используйте только оригинальные .maFile файлы")
        print("\n" + "="*60)
    
    def _load_global_settings(self) -> GlobalSettings:
        settings_data = self.config_data.get('global_settings', {})
        
        if 'log_dir' in settings_data:
            settings_data['log_dir'] = str(Path(settings_data['log_dir']).expanduser())
        if 'config_dir' in settings_data:
            settings_data['config_dir'] = str(Path(settings_data['config_dir']).expanduser())
        
        return GlobalSettings(**settings_data)
    
    def _load_monitoring_settings(self) -> MonitoringSettings:
        monitoring_data = self.config_data.get('monitoring', {})
        return MonitoringSettings(**monitoring_data)
    
    def _load_trade_settings(self) -> TradeSettings:
        trade_data = self.config_data.get('trade_settings', {})
        return TradeSettings(**trade_data)
    
    def _create_account_manager(self) -> ConfigManager:
        account_manager = ConfigManager(config_dir=self.global_settings.config_dir)
        
        accounts_data = self.config_data.get('accounts', {})
        
        for account_name, account_config in accounts_data.items():
            try:
                account = self._convert_file_account_to_config(account_config)
                
                if account_name not in account_manager.list_accounts():
                    account_manager.add_account(account)
                    self.logger.info(f"Добавлен аккаунт из файла: {account_name}")
                else:
                    self._update_account_from_file(account_manager, account_name, account_config)
                    
            except Exception as e:
                self.logger.error(f"Ошибка загрузки аккаунта {account_name}: {e}")
        
        return account_manager
    
    def _convert_file_account_to_config(self, file_config: Dict[str, Any]) -> AccountConfig:
        basic_params = {
            'name': file_config['name'],
            'mafile_path': file_config.get('mafile_path', ''),
            'seconds_to_check_session': file_config.get('seconds_to_check_session', 300),
            'allowed_to_check_and_accept_new_trades': file_config.get('allowed_to_check_and_accept_new_trades', True),
            'seconds_to_check_trades': file_config.get('seconds_to_check_trades', 60),
            'accept_every_accepted_on_web_trade': file_config.get('accept_every_accepted_on_web_trade', False),
            'accept_every_free_trade': file_config.get('accept_every_free_trade', False)
        }
        
        return AccountConfig(**basic_params)
    
    def _update_account_from_file(self, account_manager: ConfigManager, 
                                  account_name: str, file_config: Dict[str, Any]) -> None:
        update_params = {}
        
        updatable_fields = [
            'mafile_path', 'seconds_to_check_session', 'allowed_to_check_and_accept_new_trades',
            'seconds_to_check_trades', 'accept_every_accepted_on_web_trade', 'accept_every_free_trade'
        ]
        
        for field in updatable_fields:
            if field in file_config:
                update_params[field] = file_config[field]
        
        if update_params:
            account_manager.update_account(account_name, **update_params)
            self.logger.info(f"Обновлен аккаунт: {account_name}")
    
    def get_account_custom_settings(self, account_name: str) -> Dict[str, Any]:
        accounts_data = self.config_data.get('accounts', {})
        account_data = accounts_data.get(account_name, {})
        return account_data.get('custom_settings', {})
    
    def update_account_custom_settings(self, account_name: str, settings: Dict[str, Any]) -> None:
        if 'accounts' not in self.config_data:
            self.config_data['accounts'] = {}
        
        if account_name not in self.config_data['accounts']:
            self.config_data['accounts'][account_name] = {'name': account_name}
        
        self.config_data['accounts'][account_name]['custom_settings'] = settings
        self.save_config()
    
    def get_enabled_accounts(self) -> List[str]:
        accounts_data = self.config_data.get('accounts', {})
        return list(accounts_data.keys())
    
    def save_config(self) -> None:
        try:
            if self.config_file.exists():
                backup_file = self.config_file.with_suffix(f'{self.config_file.suffix}.backup')
                shutil.copy2(self.config_file, backup_file)
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                if self.is_yaml and yaml:
                    yaml.safe_dump(self.config_data, f, default_flow_style=False, 
                                 allow_unicode=True, sort_keys=False)
                else:
                    json.dump(self.config_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Конфигурация сохранена в {self.config_file}")
            
        except Exception as e:
            self.logger.error(f"Ошибка сохранения конфигурации: {e}")
            raise
    
    def validate_config(self) -> Dict[str, List[str]]:
        errors = {}
        
        if 'accounts' not in self.config_data:
            errors.setdefault('config_structure', []).append("Отсутствует секция: accounts")
        
        account_errors = self.account_config_manager.validate_config()
        if account_errors:
            errors.update(account_errors)
        
        return errors
    
    def reset_to_example(self) -> None:
        if not self.example_file.exists():
            raise FileNotFoundError(f"Файл примера {self.example_file} не найден")
        
        if self.config_file.exists():
            backup_file = self.config_file.with_suffix(f'{self.config_file.suffix}.backup.{int(time.time())}')
            shutil.copy2(self.config_file, backup_file)
            self.logger.info(f"Создана резервная копия: {backup_file}")
        
        shutil.copy2(self.example_file, self.config_file)
        
        self._load_config()
        
        self.logger.info("Конфигурация сброшена к примеру")
    
    def get_config_summary(self) -> Dict[str, Any]:
        accounts_data = self.config_data.get('accounts', {})
        
        return {
            'config_file': str(self.config_file),
            'config_format': 'YAML' if self.is_yaml else 'JSON',
            'version': self.config_data.get('version', 'unknown'),
            'total_accounts': len(accounts_data),
            'enabled_accounts': len(accounts_data),
            'disabled_accounts': 0,
            'accounts_list': {
                'enabled': list(accounts_data.keys()),
                'disabled': []
            }
        }


def setup_credentials_interactive(file_config: FileConfigManager) -> None:
    print("\n🔑 НАСТРОЙКА УЧЕТНЫХ ДАННЫХ")
    print("="*50)
    
    enabled_accounts = file_config.get_enabled_accounts()
    
    if not enabled_accounts:
        print("❌ Нет аккаунтов для настройки")
        return
    
    print(f"Найдено {len(enabled_accounts)} аккаунтов:")
    for i, account_name in enumerate(enabled_accounts, 1):
        print(f"  {i}. {account_name}")
    
    account_manager = file_config.account_config_manager
    
    for account_name in enabled_accounts:
        print(f"\n--- Настройка {account_name} ---")
        
        password, api_key = account_manager.get_sensitive_data(account_name)
        
        if password and api_key:
            print("✓ Учетные данные уже сохранены")
            update = input("Обновить? (y/N): ").lower() == 'y'
            if not update:
                continue
        
        print(f"Введите данные для {account_name}:")
        new_password = getpass.getpass("Пароль: ")
        new_api_key = input("API ключ: ").strip()
        
        if new_password and new_api_key:
            try:
                account_manager.store_sensitive_data(account_name, new_password, new_api_key)
                print("✓ Данные сохранены")
            except Exception as e:
                print(f"❌ Ошибка сохранения: {e}")
        else:
            print("⚠️ Пропущен (не все данные введены)")
    
    print("\n✅ Настройка завершена!")


def main():
    parser = argparse.ArgumentParser(description="Управление файловой конфигурацией Steam Account Manager")
    parser.add_argument("--config", help="Путь к файлу конфигурации")
    parser.add_argument("--create", action="store_true", help="Создать конфиг из примера")
    parser.add_argument("--validate", action="store_true", help="Валидировать конфигурацию")
    parser.add_argument("--summary", action="store_true", help="Показать сводку по конфигурации")
    parser.add_argument("--setup-credentials", action="store_true", help="Настроить учетные данные")
    parser.add_argument("--reset", action="store_true", help="Сбросить к примеру")
    
    args = parser.parse_args()
    
    file_config = FileConfigManager(args.config)
    
    try:
        if args.create:
            file_config._create_config_from_example()
            
        elif args.validate:
            print("🔍 Валидация конфигурации...")
            errors = file_config.validate_config()
            
            if errors:
                print("❌ Найдены ошибки:")
                for section, section_errors in errors.items():
                    print(f"  {section}:")
                    for error in section_errors:
                        print(f"    - {error}")
            else:
                print("✅ Конфигурация валидна")
                
        elif args.summary:
            summary = file_config.get_config_summary()
            print("📊 СВОДКА ПО КОНФИГУРАЦИИ")
            print("="*40)
            print(f"Файл: {summary['config_file']}")
            print(f"Формат: {summary['config_format']}")
            print(f"Версия: {summary['version']}")
            print(f"Всего аккаунтов: {summary['total_accounts']}")
            
            if summary['accounts_list']['enabled']:
                print("\nАккаунты:")
                for account in summary['accounts_list']['enabled']:
                    print(f"  • {account}")
                
        elif args.setup_credentials:
            setup_credentials_interactive(file_config)
            
        elif args.reset:
            confirm = input("⚠️ Сбросить конфигурацию к примеру? (y/N): ")
            if confirm.lower() == 'y':
                file_config.reset_to_example()
                print("✅ Конфигурация сброшена")
            else:
                print("❌ Операция отменена")
                
        else:
            summary = file_config.get_config_summary()
            print(f"📁 Конфигурация: {summary['config_file']} ({summary['config_format']})")
            print(f"📊 Аккаунтов: {summary['total_accounts']}")
            print("\nДоступные команды:")
            print("  --summary          - Показать подробную сводку")
            print("  --validate         - Проверить конфигурацию")
            print("  --setup-credentials - Настроить пароли и API ключи")
            print("  --reset            - Сбросить к примеру")
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main()) 
