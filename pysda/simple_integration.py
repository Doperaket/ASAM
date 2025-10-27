import asyncio
import os
import json
from typing import Optional, Dict, Any, List
from core.settings_manager import settings_manager


class SimplePasswordChanger:
    
    def __init__(self):
        self.name = "Password Changer"
    
    def change_password_for_account(self, account_name: str, new_password: Optional[str] = None) -> Dict[str, Any]:
        
            
        try:
            accounts = settings_manager.get_accounts()
            if account_name not in accounts:
                return {
                    "success": False,
                    "error": f"Аккаунт {account_name} не найден"
                }
            
            if new_password is None:
                from steampassword.utils import generate_password
                new_password = generate_password()
            
            
            settings_manager.set_account_password(account_name, new_password)
            
            return {
                "success": True,
                "new_password": new_password,
                "message": f"Пароль для аккаунта {account_name} успешно изменен"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Ошибка смены пароля: {str(e)}"
            }
    
    def bulk_change_passwords(self, account_names: list) -> Dict[str, Dict[str, Any]]:
        
            
        results = {}
        
        for account_name in account_names:
            results[account_name] = self.change_password_for_account(account_name)
        
        return results


class SimpleTradeManager:
    
    _global_integrated_manager = None
    
    def __init__(self):
        self.name = "Trade Manager"
    
    def _get_integrated_manager(self):
        if SimpleTradeManager._global_integrated_manager is None:
            from .pysda_trade_manager import IntegratedTradeManager
            SimpleTradeManager._global_integrated_manager = IntegratedTradeManager()
        return SimpleTradeManager._global_integrated_manager
    

    
    def get_trade_confirmations(self, account_name: str) -> Dict[str, Any]:
        
            
        try:
            manager = self._get_integrated_manager()
            result = manager.get_confirmations(account_name)
            
            if not result["success"]:
                return result
            
            formatted_confirmations = []
            for conf in result["confirmations"]:
                formatted_confirmations.append({
                    'confirmation_id': conf['id'],
                    'id': conf['id'],
                    'type': conf['type'],
                    'description': conf['description'],
                    'creator_id': conf['creator_id'],
                    'nonce': conf['nonce'],
                    'confirmation_obj': conf['confirmation'],
                    'executor': conf.get('executor')
                })
            
            return {
                "success": True,
                "confirmations": formatted_confirmations,
                "message": f"Получено {len(formatted_confirmations)} подтверждений для {account_name} через pySDA"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Ошибка получения подтверждений через pySDA: {str(e)}"
            }
    
    def confirm_trade(self, account_name: str, confirmation_obj) -> Dict[str, Any]:
        
            
        try:
            manager = self._get_integrated_manager()
            
            account_manager = manager._get_manager(account_name)
            
            result = account_manager.confirm_guard_confirmation(confirmation_obj)
            
            return {
                "success": result,
                "message": "Подтверждение обработано" if result else "Не удалось подтвердить"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Ошибка подтверждения через pySDA: {str(e)}"
            }

    def accept_confirmation(self, account_name: str, confirmation_id: str) -> Dict[str, Any]:
        
            
        try:
            self._ensure_trade_protection_for_account(account_name)
            
            manager = self._get_integrated_manager()
            
            confirmations_result = manager.get_confirmations(account_name)
            if not confirmations_result["success"]:
                return confirmations_result
            
            confirmation_obj = None
            for conf in confirmations_result["confirmations"]:
                if str(conf['id']) == str(confirmation_id):
                    confirmation_obj = conf['confirmation']
                    break
            
            if confirmation_obj is None:
                return {
                    "success": False,
                    "error": f"Подтверждение с ID {confirmation_id} не найдено"
                }
            
            return self.confirm_trade(account_name, confirmation_obj)
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Ошибка принятия подтверждения: {str(e)}"
            }

    def confirm_all_trades(self, account_name: str) -> Dict[str, Any]:
        
            
        try:
            manager = self._get_integrated_manager()
            result = manager.confirm_all(account_name)
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Ошибка подтверждения трейдов через pySDA: {str(e)}"
            }
    
    def auto_accept_gifts(self, account_name: str) -> Dict[str, Any]:
        
            
        try:
            manager = self._get_integrated_manager()
            result = manager.auto_accept_gifts(account_name)
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Ошибка автопринятия подарков через pySDA: {str(e)}"
            }
    
    def auto_confirm_trades(self, account_name: str) -> Dict[str, Any]:
        
            
        try:
            manager = self._get_integrated_manager()
            result = manager.auto_confirm_trades(account_name)
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Ошибка автоподтверждения через pySDA: {str(e)}"
            }
    
    def bulk_confirm_trades(self, account_names: List[str]) -> Dict[str, Dict[str, Any]]:
        
            
        results = {}
        for account_name in account_names:
            results[account_name] = self.confirm_all_trades(account_name)
        return results
    
    def _ensure_trade_protection_for_account(self, account_name: str):
        try:
            from core.settings_manager import settings_manager
            
            if settings_manager.is_trade_protection_acknowledged(account_name):
                return
            
            try:
                from steam.steam_integration import steam_trade_manager
                
                password = settings_manager.get_account_password(account_name)
                if not password:
                    print(f"⚠️ {account_name}: нет пароля для подтверждения trade protection")
                    return
                
                if account_name not in steam_trade_manager.active_sessions:
                    print(f"🔑 {account_name}: вход в Steam для подтверждения trade protection...")
                    login_result = steam_trade_manager.login_account(account_name, password)
                    if not login_result:
                        print(f"❌ {account_name}: не удалось войти в Steam для trade protection")
                        return
                
                print(f"🔐 {account_name}: подтверждение trade protection...")
                result = steam_trade_manager.acknowledge_trade_protection_for_account(account_name)
                
                if result.get('success'):
                    if result.get('already_acknowledged'):
                        print(f"ℹ️ {account_name}: trade protection уже была подтверждена")
                    else:
                        print(f"✅ {account_name}: trade protection успешно подтверждена")
                else:
                    error_msg = result.get('error', 'Неизвестная ошибка')
                    print(f"⚠️ {account_name}: не удалось подтвердить trade protection - {error_msg}")
                
            except ImportError:
                print(f"⚠️ {account_name}: Steam API недоступен для trade protection")
            except Exception as e:
                print(f"⚠️ {account_name}: ошибка подтверждения trade protection - {e}")
                
        except Exception as e:
            print(f"⚠️ Ошибка в _ensure_trade_protection_for_account: {e}")
