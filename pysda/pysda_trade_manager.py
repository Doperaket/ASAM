
import re
import time
import traceback
import os
import json
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from core.settings_manager import get_application_path
from datetime import datetime
from typing import List, Dict, Optional, Any, Union
from urllib.parse import unquote

try:
    from enum import Enum
except ImportError:
    class Enum:
        pass

from core.settings_manager import settings_manager

try:
    from utils.logger import logger, print_and_log
except ImportError:
    class SimpleLogger:
        @staticmethod
        def info(msg): print(f"[INFO] {msg}")
        @staticmethod
        def error(msg): print(f"[ERROR] {msg}")
        @staticmethod
        def warning(msg): print(f"[WARNING] {msg}")
        @staticmethod
        def debug(msg): print(f"[DEBUG] {msg}")
    
    logger = SimpleLogger()
    def print_and_log(msg): print(msg)


class TradeConfirmationManager:
    
    def __init__(self, username: str, mafile_path: str, api_key: Optional[str] = None):
        self.username = username
        self.mafile_path = mafile_path
        self._api_key = api_key
        
        try:
            self.steam_guard_data = self._load_steam_guard(mafile_path)
            logger.info(f"✅ Steam Guard данные загружены для {username}")
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки Steam Guard данных: {e}")
            raise
        
        self._steam_client = None
        self._initialize_steam_client()
        
        logger.info(f"🔄 Trade Confirmation Manager инициализирован для {username}")
    
    def _load_steam_guard(self, mafile_path: str) -> Dict[str, Any]:
        with open(mafile_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _initialize_steam_client(self):
        try:
            from pysda.steampy.client import SteamClient
            
            password = settings_manager.get_account_password(self.username)
            if not password:
                raise Exception(f"Пароль для {self.username} не найден")
            
            steam_id = None
            if 'Session' in self.steam_guard_data and 'SteamID' in self.steam_guard_data['Session']:
                steam_id = str(self.steam_guard_data['Session']['SteamID'])
            elif 'steamid' in self.steam_guard_data:
                steam_id = str(self.steam_guard_data['steamid'])
            
            sessions_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'sessions')
            os.makedirs(sessions_dir, exist_ok=True)
            session_path = os.path.join(sessions_dir, f"{self.username}.pkl")
            
            self._steam_client = SteamClient(
                username=self.username,
                password=password,
                steam_guard=self.mafile_path,
                steam_id=steam_id,
                session_path=session_path
            )
            
            logger.info(f"🔐 Выполняем вход для {self.username}")
            self._steam_client.login_if_need_to()
            
            logger.info(f"✅ Steam клиент инициализирован для {self.username}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации Steam клиента: {e}")
            raise
    
    def _get_steam_client(self):
        if not self._steam_client:
            self._initialize_steam_client()
        return self._steam_client
    
    def generate_guard_code(self) -> str:
        try:
            import sys
            import os
            current_dir = os.path.dirname(os.path.abspath(__file__))
            from pysda.steampy.guard import generate_one_time_code
            
            shared_secret = self.steam_guard_data.get('shared_secret')
            if not shared_secret:
                raise ValueError("shared_secret не найден в Steam Guard данных")
            
            code = generate_one_time_code(shared_secret)
            return code
        except Exception as e:
            logger.error(f"❌ Ошибка генерации Guard кода: {e}")
            raise
    
    def get_or_create_api_key(self) -> Optional[str]:
        try:
            steam_client = self._get_steam_client()
            
            logger.info("🔑 Проверяем наличие API ключа...")
            
            if self._api_key:
                logger.info(f"🔑 Используем API ключ из конфига: {self._api_key[:10]}...")
                steam_client._api_key = self._api_key
                return self._api_key
            
            if hasattr(steam_client, '_api_key') and steam_client._api_key:
                logger.info(f"🔑 Используем существующий API ключ: {steam_client._api_key[:10]}...")
                return steam_client._api_key
            
            logger.info("🔑 Получаем API ключ через веб-интерфейс...")
            api_key = self._get_api_key_from_web(steam_client)
            
            if api_key:
                steam_client._api_key = api_key
                self._api_key = api_key
                logger.info(f"✅ API ключ получен: {api_key[:10]}...")
                return api_key
            else:
                logger.error("❌ Не удалось получить или создать API ключ")
                return None
                
        except Exception as e:
            logger.error(f"❌ Ошибка получения API ключа: {e}")
            return None
    
    def _get_api_key_from_web(self, steam_client) -> Optional[str]:
        try:
            logger.info("🌐 Получаем API ключ через веб-интерфейс...")
            
            req = steam_client._session.get('https://steamcommunity.com/dev/apikey')
            
            if req.status_code != 200:
                logger.error(f"❌ Ошибка запроса к странице API ключа: {req.status_code}")
                return None
            
            if 'Sign In' in req.text and 'login' in req.url.lower():
                logger.error("❌ Перенаправление на страницу входа. Проверьте cookies.")
                return None
            
            api_key_pattern = r"([0-9A-F]{32})"
            data_apikey = re.findall(api_key_pattern, req.text, re.IGNORECASE)
            
            logger.info(f"🔍 Найдено потенциальных ключей: {len(data_apikey)}")
            
            valid_keys = []
            for key in data_apikey:
                if len(key) == 32 and all(c in '0123456789ABCDEF' for c in key.upper()):
                    valid_keys.append(key)
            
            if len(valid_keys) >= 1:
                apikey = valid_keys[0]
                steam_client._api_key = apikey
                logger.info(f"✅ API ключ найден: {apikey[:10]}...")
                return apikey
            else:
                logger.info("🔍 API ключ не найден, проверяем нужно ли его создать...")
                
                if 'You must have a validated email address' in req.text:
                    logger.error("❌ Для получения API ключа нужно подтвердить email")
                    return None
                elif 'Register for a Steam Web API Key' in req.text or 'domain name that will be using' in req.text:
                    logger.info("🆕 API ключ не создан, пробуем создать...")
                    return self._create_api_key(steam_client)
                else:
                    logger.warning("⚠️ Не удалось найти API ключ на странице")
                    logger.debug(f"Первые 500 символов страницы: {req.text[:500]}")
                    return None
                    
        except Exception as e:
            logger.error(f"❌ Ошибка получения API ключа через веб: {e}")
            return None
    
    def _create_api_key(self, steam_client) -> Optional[str]:
        try:
            logger.info("🆕 Создаем новый API ключ...")
            
            response = steam_client._session.get('https://steamcommunity.com/dev/apikey')
            
            sessionid_patterns = [
                r'g_sessionID = "([^"]+)"',
                r'sessionid":"([^"]+)"',
                r'sessionId":"([^"]+)"'
            ]
            
            sessionid = None
            for pattern in sessionid_patterns:
                sessionid_match = re.search(pattern, response.text)
                if sessionid_match:
                    sessionid = sessionid_match.group(1)
                    break
            
            if not sessionid:
                logger.error("❌ Не удалось найти sessionid для создания API ключа")
                return None
            
            logger.info(f"🔑 Найден sessionid: {sessionid[:10]}...")
            
            create_data = {
                'domain': f'autoLogin_{int(time.time())}',
                'agreeToTerms': 'agreed',
                'sessionid': sessionid,
                'Submit': 'Register'
            }
            
            logger.info("📤 Отправляем запрос на создание API ключа...")
            create_response = steam_client._session.post(
                'https://steamcommunity.com/dev/registerkey',
                data=create_data,
                headers={
                    'Referer': 'https://steamcommunity.com/dev/apikey'
                }
            )
            
            logger.info(f"📥 Ответ сервера: {create_response.status_code}")
            
            if create_response.status_code == 200:
                response_text = create_response.text.lower()
                success_indicators = [
                    'successful',
                    'created',
                    'registered',
                    'api key'
                ]
                
                if any(indicator in response_text for indicator in success_indicators):
                    logger.info("✅ API ключ успешно создан, получаем его...")
                    time.sleep(2)
                    return self._get_api_key_from_web(steam_client)
                else:
                    logger.error("❌ Не удалось создать API ключ")
                    logger.debug(f"Ответ сервера (первые 200 символов): {create_response.text[:200]}")
                    return None
            else:
                logger.error(f"❌ Ошибка создания API ключа: {create_response.status_code}")
                logger.debug(f"Ответ сервера: {create_response.text[:200]}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Ошибка создания API ключа: {e}")
            return None
    
    def validate_api_key(self, api_key: str) -> bool:
        try:
            if not api_key or len(api_key) != 32:
                return False
            
            steam_client = self._get_steam_client()
            
            test_params = {
                'key': api_key,
                'steamid': self.steam_id
            }
            
            response = steam_client._session.get(
                'http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/',
                params=test_params
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'response' in data and 'players' in data['response']:
                    logger.info("✅ API ключ валиден")
                    return True
            
            logger.error("❌ API ключ невалиден")
            return False
            
        except Exception as e:
            logger.error(f"❌ Ошибка валидации API ключа: {e}")
            return False
    
    def get_guard_confirmations(self) -> List[Dict[str, Any]]:
        try:
            steam_client = self._get_steam_client()
            
            logger.info("🔐 Получаем все подтверждения Guard...")
            
            if not hasattr(steam_client, 'steam_guard') or not steam_client.steam_guard:
                logger.warning("⚠️ Steam Guard не настроен, невозможно получить подтверждения")
                return []
            
            import sys
            import os
            current_dir = os.path.dirname(os.path.abspath(__file__))
            from pysda.steampy.confirmation import ConfirmationExecutor, Confirmation
            
            confirmation_executor = ConfirmationExecutor(
                identity_secret=steam_client.steam_guard['identity_secret'],
                my_steam_id=steam_client.steam_id,
                session=steam_client._session
            )
            
            confirmations_page = confirmation_executor._fetch_confirmations_page()
            confirmations_json = confirmations_page.json()
            
            if not confirmations_json.get('success'):
                logger.error("❌ Не удалось получить подтверждения")
                return []
            
            all_confirmations = confirmations_json.get('conf', [])
            
            if not all_confirmations:
                logger.info("ℹ️ Подтверждений Guard не найдено")
                return []
            
            logger.info(f"✅ Найдено {len(all_confirmations)} подтверждений Guard")
            
            detailed_confirmations = []
            for i, conf_data in enumerate(all_confirmations, 1):
                try:
                    confirmation_type = self._determine_confirmation_type_from_json(conf_data)
                    
                    conf = Confirmation(
                        data_confid=conf_data['id'],
                        nonce=conf_data['nonce'],
                        creator_id=int(conf_data['creator_id'])
                    )
                    
                    detailed_conf = {
                        'id': conf_data['id'],
                        'nonce': conf_data['nonce'],
                        'creator_id': int(conf_data['creator_id']),
                        'type': confirmation_type,
                        'description': conf_data.get('headline', f'Подтверждение
                        'confirmation': conf,
                        'executor': confirmation_executor
                    }
                    
                    detailed_confirmations.append(detailed_conf)
                    
                    logger.info(f"[{i}/{len(all_confirmations)}] {confirmation_type}: {detailed_conf['description']}")
                    
                except Exception as e:
                    logger.error(f"❌ Ошибка обработки подтверждения {i}: {e}")
                    continue
            
            return detailed_confirmations
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения подтверждений Guard: {e}")
            logger.debug(traceback.format_exc())
            return []
    
    def _determine_confirmation_type_from_json(self, conf_data: Dict[str, Any]) -> str:
        try:
            conf_type = conf_data.get('type', 'unknown')
            
            type_mapping = {
                '1': 'Trade',
                '2': 'Market Transaction', 
                '3': 'Account Recovery',
                '4': 'Phone Number Change',
                '5': 'Account Creation',
                '6': 'Store Transaction',
                '7': 'Market Listing',
                '8': 'Account Email Change',
                '9': 'Password Change',
                '10': 'API Key Access',
                '11': 'Steam Guard Change',
                '12': 'Community Market Purchase',
                '13': 'Steam Store Purchase',
                '14': 'Gift Purchase'
            }
            
            return type_mapping.get(str(conf_type), f'Unknown Type {conf_type}')
            
        except Exception as e:
            logger.error(f"Ошибка определения типа подтверждения: {e}")
            return 'Unknown'
    
    def confirm_guard_confirmation(self, confirmation_obj) -> bool:
        try:
            steam_client = self._get_steam_client()
            
            logger.info(f"🔑 Подтверждаем подтверждение Guard: {confirmation_obj.data_confid}")
            
            import sys
            import os
            current_dir = os.path.dirname(os.path.abspath(__file__))
            steampy_path = os.path.join(current_dir, 'steampy')
            from pysda.steampy.confirmation import ConfirmationExecutor
            
            confirmation_executor = ConfirmationExecutor(
                identity_secret=steam_client.steam_guard['identity_secret'],
                my_steam_id=steam_client.steam_id,
                session=steam_client._session
            )
            
            response = confirmation_executor._send_confirmation(confirmation_obj)
            
            if response and response.get('success'):
                logger.info(f"✅ Подтверждение {confirmation_obj.data_confid} успешно обработано")
                return True
            else:
                error_message = response.get('error', 'Unknown error') if response else 'No response'
                logger.error(f"❌ Ошибка подтверждения {confirmation_obj.data_confid}: {error_message}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Ошибка подтверждения Guard: {e}")
            logger.debug(traceback.format_exc())
            return False
    
    def process_free_trades(self, auto_accept: bool = True, auto_confirm: bool = True) -> Dict[str, int]:
        
            
        stats = {
            'found_free_trades': 0,
            'accepted_trades': 0,
            'confirmed_trades': 0,
            'errors': 0
        }
        
        try:
            logger.info("🎁 Ищем бесплатные трейды (подарки)...")
            
            steam_client = self._get_steam_client()
            
            logger.info("🔍 Получаем активные трейд офферы...")
            active_offers = steam_client.get_trade_offers(merge=False)
            
            if not active_offers:
                logger.info("ℹ️ Активные трейд офферы не получены")
                return stats
            
            free_trades = []
            received_offers = active_offers.get('trade_offers_received', [])
            
            for offer in received_offers:
                items_to_give = len(offer.get('items_to_give', []))
                items_to_receive = len(offer.get('items_to_receive', []))
                
                if items_to_give == 0 and items_to_receive > 0:
                    free_trades.append(offer)
                    logger.info(f"🎁 Найден бесплатный трейд: {offer['tradeofferid']} (получаем {items_to_receive} предметов)")
            
            stats['found_free_trades'] = len(free_trades)
            
            if not free_trades:
                logger.info("ℹ️ Бесплатных трейдов не найдено")
                return stats
            
            logger.info(f"🎁 Найдено {len(free_trades)} бесплатных трейдов")
            
            for offer in free_trades:
                try:
                    trade_id = offer['tradeofferid']
                    
                    if auto_accept:
                        logger.info(f"🌐 Принимаем бесплатный трейд: {trade_id}")
                        
                        if auto_confirm:
                            result = steam_client.accept_trade_offer_with_confirmation(trade_id)
                        else:
                            result = steam_client.accept_trade_offer(trade_id)
                        
                        if result and not result.get('strError'):
                            stats['accepted_trades'] += 1
                            logger.info(f"✅ Принят бесплатный трейд: {trade_id}")
                            
                            if auto_confirm and result.get('tradeid'):
                                stats['confirmed_trades'] += 1
                                logger.info(f"✅ Подтвержден бесплатный трейд: {trade_id}")
                        else:
                            error_msg = result.get('strError', 'Неизвестная ошибка') if result else 'Пустой ответ'
                            logger.error(f"❌ Не удалось принять бесплатный трейд {trade_id}: {error_msg}")
                            stats['errors'] += 1
                    else:
                        logger.info(f"ℹ️ Бесплатный трейд найден, но auto_accept отключен: {trade_id}")
                        
                except Exception as e:
                    logger.error(f"❌ Ошибка обработки трейда {offer.get('tradeofferid', 'unknown')}: {e}")
                    stats['errors'] += 1
                    
                time.sleep(1)
            
            logger.info(f"📊 Статистика обработки бесплатных трейдов:")
            logger.info(f"  - Найдено: {stats['found_free_trades']}")
            logger.info(f"  - Принято: {stats['accepted_trades']}")
            logger.info(f"  - Подтверждено: {stats['confirmed_trades']}")
            logger.info(f"  - Ошибок: {stats['errors']}")
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки бесплатных трейдов: {e}")
            logger.debug(traceback.format_exc())
            stats['errors'] += 1
            return stats

    def process_confirmation_needed_trades(self, auto_confirm: bool = True) -> Dict[str, int]:
        
            
        stats = {
            'found_confirmation_needed': 0,
            'confirmed_trades': 0,
            'errors': 0
        }
        
        try:
            logger.info("🔑 Ищем трейды, требующие подтверждения...")
            
            steam_client = self._get_steam_client()
            
            logger.info("🔍 Получаем все трейд офферы...")
            all_offers = steam_client.get_trade_offers(merge=False)
            
            if not all_offers:
                logger.info("ℹ️ Трейд офферы не получены")
                return stats
            
            confirmation_needed_trades = []
            
            for offer in all_offers.get('trade_offers_received', []):
                if offer.get('trade_offer_state') == 9:
                    confirmation_needed_trades.append(offer)
                    logger.info(f"🔑 Входящий трейд требует подтверждения: {offer['tradeofferid']}")
            
            for offer in all_offers.get('trade_offers_sent', []):
                if offer.get('trade_offer_state') == 9:
                    confirmation_needed_trades.append(offer)
                    logger.info(f"🔑 Исходящий трейд требует подтверждения: {offer['tradeofferid']}")
            
            stats['found_confirmation_needed'] = len(confirmation_needed_trades)
            
            if not confirmation_needed_trades:
                logger.info("ℹ️ Трейдов, требующих подтверждения, не найдено")
                return stats
            
            logger.info(f"🔑 Найдено {len(confirmation_needed_trades)} трейдов, требующих подтверждения")
            
            for offer in confirmation_needed_trades:
                try:
                    trade_id = offer['tradeofferid']
                    logger.info(f"🔑 Обрабатываем трейд: {trade_id}")
                    
                    if auto_confirm:
                        result = steam_client.confirm_accepted_trade_offer(trade_id)
                        
                        if result and not result.get('strError'):
                            stats['confirmed_trades'] += 1
                            logger.info(f"✅ Подтвержден трейд: {trade_id}")
                        else:
                            error_msg = result.get('strError', 'Неизвестная ошибка') if result else 'Пустой ответ'
                            logger.warning(f"⚠️ Не удалось подтвердить трейд {trade_id}: {error_msg}")
                            stats['errors'] += 1
                    else:
                        logger.info(f"ℹ️ Трейд требует подтверждения, но auto_confirm отключен: {trade_id}")
                        
                    time.sleep(1)
                        
                except Exception as e:
                    logger.error(f"❌ Ошибка обработки трейда {offer.get('tradeofferid', 'unknown')}: {e}")
                    stats['errors'] += 1
            
            logger.info(f"📊 Статистика подтверждения трейдов:")
            logger.info(f"  - Найдено требующих подтверждения: {stats['found_confirmation_needed']}")
            logger.info(f"  - Подтверждено: {stats['confirmed_trades']}")
            logger.info(f"  - Ошибок: {stats['errors']}")
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки трейдов, требующих подтверждения: {e}")
            logger.debug(traceback.format_exc())
            stats['errors'] += 1
            return stats


class IntegratedTradeManager:
    
    def __init__(self):
        self.managers = {}
    
    def _get_manager(self, username: str) -> TradeConfirmationManager:
        if username not in self.managers:
            mafile_path = os.path.join(get_application_path(), "data", "mafiles", f"{username}.maFile")
            if not os.path.exists(mafile_path):
                raise Exception(f"Файл {mafile_path} не найден")
            
            self.managers[username] = TradeConfirmationManager(
                username=username,
                mafile_path=mafile_path
            )
        
        return self.managers[username]
    
    def get_confirmations(self, username: str) -> Dict[str, Any]:
        try:
            manager = self._get_manager(username)
            confirmations = manager.get_guard_confirmations()
            
            return {
                "success": True,
                "confirmations": confirmations,
                "message": f"Получено {len(confirmations)} подтверждений для {username}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Ошибка получения подтверждений: {str(e)}"
            }
    
    def confirm_all(self, username: str) -> Dict[str, Any]:
        try:
            manager = self._get_manager(username)
            
            confirmations = manager.get_guard_confirmations()
            if not confirmations:
                return {
                    "success": True,
                    "confirmed_count": 0,
                    "message": f"Нет подтверждений для {username}"
                }
            
            confirmed_count = 0
            for conf in confirmations:
                try:
                    if manager.confirm_guard_confirmation(conf['confirmation']):
                        confirmed_count += 1
                except Exception as e:
                    logger.error(f"Ошибка подтверждения {conf['id']}: {e}")
                    continue
            
            return {
                "success": True,
                "confirmed_count": confirmed_count,
                "message": f"Подтверждено {confirmed_count} из {len(confirmations)} для {username}"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Ошибка подтверждения: {str(e)}"
            }
    
    def auto_accept_gifts(self, username: str) -> Dict[str, Any]:
        try:
            manager = self._get_manager(username)
            stats = manager.process_free_trades(auto_accept=True, auto_confirm=True)
            
            return {
                "success": True,
                "stats": stats,
                "message": f"Обработано {stats['found_free_trades']} бесплатных трейдов для {username}"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Ошибка автопринятия подарков: {str(e)}"
            }
    
    def auto_confirm_trades(self, username: str) -> Dict[str, Any]:
        try:
            manager = self._get_manager(username)
            stats = manager.process_confirmation_needed_trades(auto_confirm=True)
            
            return {
                "success": True,
                "stats": stats,
                "message": f"Обработано {stats['found_confirmation_needed']} трейдов для {username}"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Ошибка автоподтверждения: {str(e)}"
            }
