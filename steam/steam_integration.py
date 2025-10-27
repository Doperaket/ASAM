import asyncio
import json
import os
from typing import List, Dict, Optional, Any
import traceback

try:
    from steampassword.chpassword import SteamPasswordChange
    from steampassword.steam import CustomSteam
    from steampassword.utils import generate_password
    from steamlib.api.trade import SteamTrade
    from steamlib.api.trade.exceptions import NotFoundMobileConfirmationError
    STEAM_MODULES_AVAILABLE = True
except ImportError as e:
    print(f"Steam API модули недоступны: {e}")
    STEAM_MODULES_AVAILABLE = False
    
    class CustomSteam:
        def __init__(self, *args, **kwargs):
            raise ImportError("Steam API модули недоступны")
    
    class SteamPasswordChange:
        def __init__(self, *args, **kwargs):
            raise ImportError("Steam API модули недоступны")
    
    class SteamTrade:
        def __init__(self, *args, **kwargs):
            raise ImportError("Steam API модули недоступны")
    
    class NotFoundMobileConfirmationError(Exception):
        pass
    
    def generate_password(*args, **kwargs):
        raise ImportError("Steam API модули недоступны")


class SteamAPIManager:
    
    def __init__(self):
        self.steam_instances = {}
    
    def _get_mafile_data(self, login: str) -> Optional[Dict[str, Any]]:
        try:
            import core.settings_manager
            accounts_dir = core.settings_manager.get_accounts_dir()
            
            for filename in os.listdir(accounts_dir):
                if filename.lower().endswith('.mafile'):
                    mafile_path = os.path.join(accounts_dir, filename)
                    with open(mafile_path, 'r', encoding='utf-8') as f:
                        mafile_data = json.load(f)
                    
                    account_name = None
                    if 'account_name' in mafile_data:
                        account_name = mafile_data['account_name']
                    elif 'AccountName' in mafile_data:
                        account_name = mafile_data['AccountName']
                    elif 'Steam' in mafile_data and 'Username' in mafile_data['Steam']:
                        account_name = mafile_data['Steam']['Username']
                    
                    if account_name == login:
                        return mafile_data
            return None
        except Exception as e:
            print(f"Ошибка при получении .mafile данных: {e}")
            return None
    
    def _create_steam_instance(self, login: str, password: str) -> Optional[CustomSteam]:
        if not STEAM_MODULES_AVAILABLE:
            return None
            
        try:
            mafile_data = self._get_mafile_data(login)
            if not mafile_data:
                print(f"Не найден .mafile для аккаунта {login}")
                return None
            
            shared_secret = mafile_data.get('shared_secret')
            identity_secret = mafile_data.get('identity_secret')
            device_id = mafile_data.get('device_id')
            
            steamid = None
            if 'Session' in mafile_data and 'SteamID' in mafile_data['Session']:
                steamid = int(mafile_data['Session']['SteamID'])
            elif 'steamid' in mafile_data:
                steamid = int(mafile_data['steamid'])
            
            if not all([shared_secret, identity_secret]):
                print(f"Неполные данные Steam Guard для аккаунта {login}")
                return None
            
            steam = CustomSteam(
                login=login,
                password=password,
                steamid=steamid,
                shared_secret=shared_secret,
                identity_secret=identity_secret,
                device_id=device_id
            )
            
            return steam
            
        except Exception as e:
            print(f"Ошибка при создании Steam экземпляра: {e}")
            traceback.print_exc()
            return None
    
    async def change_password(self, login: str, current_password: str, new_password: Optional[str] = None) -> Dict[str, Any]:
        if not STEAM_MODULES_AVAILABLE:
            return {"success": False, "error": "Steam API модули недоступны"}
        
        try:
            if not new_password:
                new_password = generate_password(min_length=12, max_length=16)
            
            steam = self._create_steam_instance(login, current_password)
            if not steam:
                return {"success": False, "error": "Не удалось создать Steam соединение"}
            
            password_changer = SteamPasswordChange(steam)
            await password_changer.change(new_password)
            
            return {
                "success": True, 
                "new_password": new_password,
                "message": "Пароль успешно изменен"
            }
            
        except Exception as e:
            error_msg = f"Ошибка при смене пароля: {e}"
            print(error_msg)
            traceback.print_exc()
            
            if "login" in str(e).lower() or "auth" in str(e).lower():
                error_msg = "Ошибка авторизации. Проверьте логин и пароль."
            elif "steam guard" in str(e).lower() or "2fa" in str(e).lower():
                error_msg = "Ошибка Steam Guard. Проверьте настройки двухфакторной аутентификации."
            elif "network" in str(e).lower() or "connection" in str(e).lower():
                error_msg = "Ошибка сети. Проверьте интернет-соединение."
            elif "rate limit" in str(e).lower():
                error_msg = "Превышен лимит запросов. Попробуйте позже."
            
            return {"success": False, "error": error_msg}
    
    async def get_confirmations(self, login: str, password: str) -> List[Dict[str, Any]]:
        if not STEAM_MODULES_AVAILABLE:
            return []
        
        try:
            steam = self._create_steam_instance(login, password)
            if not steam:
                print(f"Не удалось создать Steam соединение для {login}")
                return []
            
            steam_trade = SteamTrade(steam)
            confirmations = await steam_trade.get_mobile_confirmations()
            
            result = []
            for conf in confirmations:
                result.append({
                    "id": getattr(conf, 'id', 'N/A'),
                    "key": getattr(conf, 'key', 'N/A'),
                    "type": getattr(conf, 'type', 'Unknown'),
                    "creator": getattr(conf, 'creator', 'N/A'),
                    "description": getattr(conf, 'description', 'No description'),
                    "time": getattr(conf, 'time', 'N/A')
                })
            
            return result
            
        except NotFoundMobileConfirmationError:
            print(f"Нет подтверждений для аккаунта {login}")
            return []
        except Exception as e:
            error_str = str(e).lower()
            print(f"Ошибка при получении подтверждений: {e}")
            traceback.print_exc()
            
            if "login" in error_str or "auth" in error_str:
                print("Подсказка: Проверьте логин и пароль аккаунта")
            elif "steam guard" in error_str or "2fa" in error_str:
                print("Подсказка: Проверьте настройки Steam Guard в .mafile")
            elif "network" in error_str or "connection" in error_str:
                print("Подсказка: Проверьте интернет-соединение")
                
            return []
    
    async def confirm_trade(self, login: str, password: str, confirmation_id: str, confirmation_key: str) -> bool:
        if not STEAM_MODULES_AVAILABLE:
            return False
        
        try:
            steam = self._create_steam_instance(login, password)
            if not steam:
                return False
            
            steam_trade = SteamTrade(steam)
            await steam_trade.confirm_confirmation(confirmation_id, confirmation_key)
            return True
            
        except Exception as e:
            error_str = str(e).lower()
            print(f"Ошибка при подтверждении операции: {e}")
            
            if "not found" in error_str:
                print("Подсказка: Подтверждение уже обработано или не существует")
            elif "expired" in error_str:
                print("Подсказка: Время подтверждения истекло")
            elif "steam guard" in error_str:
                print("Подсказка: Проверьте настройки Steam Guard")
                
            return False


steam_api_manager = SteamAPIManager()


def change_password_sync(login: str, current_password: str, new_password: Optional[str] = None) -> Dict[str, Any]:
    return asyncio.run(steam_api_manager.change_password(login, current_password, new_password))


def get_confirmations_sync(login: str, password: str) -> List[Dict[str, Any]]:
    return asyncio.run(steam_api_manager.get_confirmations(login, password))


def confirm_trade_sync(login: str, password: str, confirmation_id: str, confirmation_key: str) -> bool:
    return asyncio.run(steam_api_manager.confirm_trade(login, password, confirmation_id, confirmation_key))


class SteamTradeManager:
    
    def __init__(self):
        self.steam_client = None
        self.active_sessions = {}
        self.session_data = {}
        
    def _get_mafile_data(self, login: str) -> Optional[Dict[str, Any]]:
        try:
            import core.settings_manager
            accounts_dir = core.settings_manager.get_accounts_dir()
            
            for filename in os.listdir(accounts_dir):
                if filename.lower().endswith('.mafile'):
                    mafile_path = os.path.join(accounts_dir, filename)
                    with open(mafile_path, 'r', encoding='utf-8') as f:
                        mafile_data = json.load(f)
                    
                    account_name = None
                    if 'account_name' in mafile_data:
                        account_name = mafile_data['account_name']
                    elif 'AccountName' in mafile_data:
                        account_name = mafile_data['AccountName']
                    elif 'Steam' in mafile_data and 'Username' in mafile_data['Steam']:
                        account_name = mafile_data['Steam']['Username']
                    
                    if account_name == login:
                        return mafile_data
            return None
        except Exception as e:
            print(f"Ошибка при получении .mafile данных: {e}")
            return None
        
    def _get_steam_client(self):
        if self.steam_client is None:
            try:
                from steam_api import SteamClient
                self.steam_client = SteamClient(auto_start=True)
                return self.steam_client
            except ImportError:
                print("Steam API модуль недоступен. Установите Node.js и выполните 'npm install' в папке steam_api")
                return None
            except Exception as e:
                print(f"Ошибка инициализации Steam клиента: {e}")
                return None
        return self.steam_client
        
    def login_account(self, login: str, password: str, shared_secret: Optional[str] = None) -> Optional[str]:
        
            
        client = self._get_steam_client()
        if not client:
            return None
            
        identity_secret = None
        if not shared_secret:
            mafile_data = self._get_mafile_data(login)
            if mafile_data:
                shared_secret = mafile_data.get('shared_secret')
                identity_secret = mafile_data.get('identity_secret')
                print(f"Получен shared_secret из .mafile для {login}")
            
        try:
            session_id, session_data = client.login(
                username=login,
                password=password,
                shared_secret=shared_secret,
                identity_secret=identity_secret
            )
            
            if identity_secret:
                session_data['identity_secret'] = identity_secret
            
            self.active_sessions[login] = session_id
            self.session_data[login] = session_data
            return session_id
        except Exception as e:
            print(f"Ошибка авторизации аккаунта {login}: {e}")
            return None
    
    def get_inventory(self, login: str, steam_id: str, app_id: str = "730") -> Optional[List[Dict]]:
        
            
        client = self._get_steam_client()
        session_id = self.active_sessions.get(login)
        
        if not client or not session_id:
            return None
            
        try:
            return client.get_inventory(session_id, steam_id, app_id)
        except Exception as e:
            print(f"Ошибка получения инвентаря {steam_id}: {e}")
            return None
    
    def create_trade_offer(self, login: str, trade_url: str, 
                          items_from_me: List[Dict], items_from_them: List[Dict] = None,
                          message: str = "") -> Optional[str]:
        
            
        client = self._get_steam_client()
        session_id = self.active_sessions.get(login)
        if not client or not session_id:
            print(f"[ERROR] Нет клиента или session_id для {login}: client={client}, session_id={session_id}")
            return None
        print(f"[DEBUG] create_trade_offer: login={login}, session_id={session_id}, client={client}")

        from core.settings_manager import settings_manager
        if not settings_manager.is_trade_protection_acknowledged(login):
            try:
                print(f"🔐 Подтверждаем защиту трейдов для {login}...")
                result = client.acknowledge_trade_protection(session_id)
                print(f"[DEBUG] acknowledge_trade_protection result: {result}")
                if result.get('success'):
                    print(f"✅ Защита трейдов подтверждена для {login}")
                    settings_manager.set_trade_protection_acknowledged(login, True)
                else:
                    print(f"⚠️ Не удалось подтвердить защиту трейдов для {login}: {result.get('error', 'Неизвестная ошибка')}")
            except Exception as e:
                print(f"⚠️ Ошибка при подтверждении защиты трейдов для {login}: {e}")

        print(f"[DEBUG] Перед отправкой трейда: login={login}, session_id={session_id}, client={client}")
        try:
            result = client.create_trade(
                session_id=session_id,
                partner_trade_url=trade_url,
                items_from_me=items_from_me or [],
                items_from_them=items_from_them or [],
                message=message
            )
            print(f"[DEBUG] create_trade result: {result}")
            offer_id = result.get('offerId') or result.get('tradeofferid')
            print(f"[DEBUG] Отправленный трейд offer_id: {offer_id}")

            if self.steam_client:
                print(f"[DEBUG] Останавливаем мост после отправки трейда для {login}")
                self.steam_client.stop_bridge()
                self.steam_client = None

            if offer_id:
                try:
                    print(f"[DEBUG] Начинаем поиск подтверждения для трейда {offer_id} после остановки моста")
                    
                    mafile_data = self._get_mafile_data(login)
                    if not mafile_data:
                        print(f"[ERROR] Не найден .mafile для аккаунта {login}")
                        return offer_id
                    
                    import core.settings_manager
                    accounts_dir = core.settings_manager.get_accounts_dir()
                    mafile_path = None
                    
                    for filename in os.listdir(accounts_dir):
                        if filename.lower().endswith('.mafile'):
                            test_path = os.path.join(accounts_dir, filename)
                            with open(test_path, 'r', encoding='utf-8') as f:
                                test_data = json.load(f)
                            
                            account_name = None
                            if 'account_name' in test_data:
                                account_name = test_data['account_name']
                            elif 'AccountName' in test_data:
                                account_name = test_data['AccountName']
                            elif 'Steam' in test_data and 'Username' in test_data['Steam']:
                                account_name = test_data['Steam']['Username']
                            
                            if account_name == login:
                                mafile_path = test_path
                                break
                    
                    if not mafile_path:
                        print(f"[ERROR] Не найден путь к .mafile для аккаунта {login}")
                        return offer_id
                    
                    from pysda.pysda_trade_manager import TradeConfirmationManager
                    confirmation_manager = TradeConfirmationManager(login, mafile_path)
                    
                    import time
                    time.sleep(3)
                    
                    confirmations = confirmation_manager.get_guard_confirmations()
                    print(f"[DEBUG] Найдено {len(confirmations)} подтверждений Guard")
                    
                    found = False
                    for conf in confirmations:
                        print(f"[DEBUG] Проверяем подтверждение: тип={conf['type']}, описание={conf['description']}, id={conf['id']}")
                        
                        if conf['type'] in ['Trade', 'Market Transaction']:
                            print(f"[DEBUG] Найдено подтверждение трейда: {conf['description']}")
                            print(f"[DEBUG] Подтверждаем подтверждение для трейда {offer_id}")
                            success = confirmation_manager.confirm_guard_confirmation(conf['confirmation'])
                            print(f"[DEBUG] Результат подтверждения трейда {offer_id}: {success}")
                            found = True
                            break
                    
                    if not found:
                        print(f"[WARN] Не найдено Guard-подтверждение для трейда {offer_id}")
                        
                except Exception as e:
                    print(f"[ERROR] Ошибка при поиске/подтверждении Guard-подтверждения для трейда {offer_id}: {e}")
                    traceback.print_exc()

            return offer_id
        except Exception as e:
            print(f"[ERROR] Ошибка создания трейда для {login}: {e}")
            return None
    
    def get_trade_offers(self, login: str, filter_type: str = "active") -> Optional[Dict]:
        
            
        client = self._get_steam_client()
        session_id = self.active_sessions.get(login)
        
        if not client or not session_id:
            return None
            
        try:
            return client.get_trade_offers(session_id, filter_type)
        except Exception as e:
            print(f"Ошибка получения трейдов для {login}: {e}")
            return None
    
    def accept_trade_offer(self, login: str, offer_id: str) -> bool:
        client = self._get_steam_client()
        session_id = self.active_sessions.get(login)
        
        if not client or not session_id:
            return False
            
        try:
            result = client.accept_trade(session_id, offer_id)
            return result.get('success', False)
        except Exception as e:
            print(f"Ошибка принятия трейда {offer_id}: {e}")
            return False
    
    def decline_trade_offer(self, login: str, offer_id: str) -> bool:
        client = self._get_steam_client()
        session_id = self.active_sessions.get(login)
        
        if not client or not session_id:
            return False
            
        try:
            result = client.decline_trade(session_id, offer_id)
            return result.get('success', False)
        except Exception as e:
            print(f"Ошибка отклонения трейда {offer_id}: {e}")
            return False
    
    def get_trade_url(self, login: str) -> Optional[str]:
        client = self._get_steam_client()
        session_id = self.active_sessions.get(login)
        
        if not client or not session_id:
            return None
            
        try:
            result = client.get_trade_url(session_id)
            return result.get('tradeUrl')
        except Exception as e:
            print(f"Ошибка получения Trade URL для {login}: {e}")
            return None
    
    def get_incoming_trades(self, login: str) -> Optional[List[Dict]]:
        
            
        client = self._get_steam_client()
        session_id = self.active_sessions.get(login)
        
        if not client or not session_id:
            return None
            
        try:
            result = client.get_incoming_trades(session_id)
            return result.get('offers', [])
        except Exception as e:
            print(f"Ошибка получения входящих трейдов для {login}: {e}")
            return None
    
    def auto_accept_trades_from_partner(self, login: str, partner_steam_id: str = None) -> Dict[str, Any]:
        
            
        client = self._get_steam_client()
        session_id = self.active_sessions.get(login)
        
        if not client or not session_id:
            return {"success": False, "error": "Нет активной сессии"}
            
        try:
            result = client.auto_accept_trades(
                session_id=session_id,
                partner_steam_id=partner_steam_id,
                accept_all=partner_steam_id is None
            )
            return result
        except Exception as e:
            error_msg = f"Ошибка автопринятия трейдов для {login}: {e}"
            print(error_msg)
            return {"success": False, "error": error_msg}
    
    def accept_sent_trade(self, sender_login: str, receiver_login: str, offer_id: str) -> Dict[str, Any]:
        
            
        client = self._get_steam_client()
        sender_session = self.active_sessions.get(sender_login)
        receiver_session = self.active_sessions.get(receiver_login)
        
        if not client or not sender_session:
            return {"success": False, "error": f"Нет активной сессии для отправителя {sender_login}"}
        
        target_session = receiver_session or sender_session
        
        try:
            result = client.accept_sent_trade(
                session_id=sender_session,
                receiver_session_id=target_session,
                offer_id=offer_id
            )
            return result
        except Exception as e:
            error_msg = f"Ошибка принятия отправленного трейда {offer_id}: {e}"
            print(error_msg)
            return {"success": False, "error": error_msg}
    
    def create_and_auto_accept_trade(self, sender_login: str, receiver_login: str, 
                                   trade_url: str, items_from_me: List[Dict], 
                                   message: str = "") -> Dict[str, Any]:
        
            
        offer_id = self.create_trade_offer(sender_login, trade_url, items_from_me, [], message)
        
        if not offer_id:
            return {"success": False, "error": "Не удалось создать трейд"}
        
        import time
        time.sleep(2)
        
        accept_result = self.accept_sent_trade(sender_login, receiver_login, offer_id)
        
        return {
            "success": True,
            "offer_id": offer_id,
            "auto_accept_result": accept_result,
            "message": "Трейд создан и автоматически принят" if accept_result.get("success") else "Трейд создан, но не удалось автоматически принять"
        }
    
    def logout_account(self, login: str) -> bool:
        client = self._get_steam_client()
        session_id = self.active_sessions.get(login)
        
        if not client or not session_id:
            return True
            
        try:
            client.logout(session_id)
            self.active_sessions.pop(login, None)
            return True
        except Exception as e:
            print(f"Ошибка выхода из аккаунта {login}: {e}")
            return False
    
    def get_confirmations(self, login: str) -> Optional[List[Dict]]:
        
            
        client = self._get_steam_client()
        session_id = self.active_sessions.get(login)
        
        if not client or not session_id:
            return None
            
        try:
            result = client.get_confirmations(session_id)
            if result.get('success'):
                return result.get('confirmations', [])
            return None
        except Exception as e:
            print(f"Ошибка получения подтверждений для {login}: {e}")
            return None
    
    def confirm_confirmation(self, login: str, confirmation_id: str, 
                           confirmation_key: str, accept: bool = True) -> bool:
        
            
        client = self._get_steam_client()
        session_id = self.active_sessions.get(login)
        
        if not client or not session_id:
            return False
            
        try:
            result = client.confirm_confirmation(session_id, confirmation_id, confirmation_key, accept)
            return result.get('success', False)
        except Exception as e:
            print(f"Ошибка подтверждения {confirmation_id} для {login}: {e}")
            return False
    
    def confirm_all_confirmations(self, login: str) -> Dict[str, Any]:
        
            
        client = self._get_steam_client()
        session_id = self.active_sessions.get(login)
        
        if not client or not session_id:
            return {"success": False, "error": "Нет активной сессии"}
            
        try:
            result = client.confirm_all_confirmations(session_id)
            return result
        except Exception as e:
            error_msg = f"Ошибка массового подтверждения для {login}: {e}"
            print(error_msg)
            return {"success": False, "error": error_msg}
    
    def acknowledge_trade_protection_for_account(self, login: str) -> Dict[str, Any]:
        
            
        from core.settings_manager import settings_manager
        
        if settings_manager.is_trade_protection_acknowledged(login):
            return {
                "success": True, 
                "message": f"Защита трейдов для {login} уже была подтверждена ранее",
                "already_acknowledged": True
            }
        
        client = self._get_steam_client()
        session_id = self.active_sessions.get(login)
        
        if not client or not session_id:
            return {"success": False, "error": "Нет активной сессии для аккаунта"}
            
        try:
            print(f"🔐 Подтверждение защиты трейдов для {login}...")
            result = client.acknowledge_trade_protection(session_id)
            
            if result.get('success'):
                settings_manager.set_trade_protection_acknowledged(login, True)
                print(f"✅ Защита трейдов успешно подтверждена для {login}")
                return {
                    "success": True,
                    "message": f"Защита трейдов успешно подтверждена для {login}",
                    "already_acknowledged": False
                }
            else:
                error_msg = result.get('error', 'Неизвестная ошибка')
                print(f"❌ Не удалось подтвердить защиту трейдов для {login}: {error_msg}")
                return {"success": False, "error": f"Ошибка подтверждения: {error_msg}"}
                
        except Exception as e:
            error_msg = f"Ошибка при подтверждении защиты трейдов для {login}: {e}"
            print(error_msg)
            return {"success": False, "error": error_msg}

    def cleanup(self):
        if self.steam_client:
            try:
                for login in list(self.active_sessions.keys()):
                    self.logout_account(login)
                
                self.steam_client.stop_bridge()
                self.steam_client = None
            except Exception as e:
                print(f"Ошибка очистки Steam Trade Manager: {e}")


steam_trade_manager = SteamTradeManager()
