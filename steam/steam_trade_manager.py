
import requests
import json
from typing import Dict, List, Optional
from urllib.parse import parse_qs, urlparse


class SteamTradeManager:
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
    
    def parse_trade_url(self, trade_url: str) -> Optional[Dict[str, str]]:
        
            
        try:
            parsed_url = urlparse(trade_url)
            query_params = parse_qs(parsed_url.query)
            
            partner = query_params.get('partner', [None])[0]
            token = query_params.get('token', [None])[0]
            
            if partner and token:
                return {
                    'partner': partner,
                    'token': token
                }
            
            return None
            
        except Exception as e:
            print(f"Ошибка парсинга трейд-URL: {e}")
            return None
    
    def get_steam_login_data(self, mafile_path: str) -> Optional[Dict]:
        
            
        try:
            with open(mafile_path, 'r', encoding='utf-8') as f:
                mafile_data = json.load(f)
            
            session_data = mafile_data.get('Session', {})
            
            return {
                'steam_id': str(session_data.get('SteamID', '')),
                'session_id': session_data.get('SessionID', ''),
                'steam_login': session_data.get('SteamLogin', ''),
                'steam_login_secure': session_data.get('SteamLoginSecure', ''),
                'webcookie': session_data.get('WebCookie', ''),
                'oauth_token': session_data.get('OAuthToken', ''),
                'account_name': mafile_data.get('account_name', '')
            }
            
        except Exception as e:
            print(f"Ошибка чтения .mafile: {e}")
            return None
    
    def setup_session_cookies(self, login_data: Dict) -> bool:
        
            
        try:
            cookies = {
                'sessionid': login_data['session_id'],
                'steamLogin': login_data['steam_login'],
                'steamLoginSecure': login_data['steam_login_secure'],
            }
            
            if login_data['webcookie']:
                cookies['webTradeEligibility'] = login_data['webcookie']
            
            for name, value in cookies.items():
                self.session.cookies.set(name, value, domain='.steamcommunity.com')
            
            return True
            
        except Exception as e:
            print(f"Ошибка настройки cookies: {e}")
            return False
    
    def get_inventory_assets(self, steam_id: str, app_id: str = "730", context_id: str = "2") -> List[Dict]:
        
            
        try:
            url = f"https://steamcommunity.com/inventory/{steam_id}/{app_id}/{context_id}"
            
            response = self.session.get(url, timeout=30)
            
            if response.status_code != 200:
                print(f"Ошибка получения инвентаря: HTTP {response.status_code}")
                return []
            
            data = response.json()
            
            if not data.get('success'):
                print("Инвентарь недоступен")
                return []
            
            assets = data.get('assets', [])
            descriptions = data.get('descriptions', [])
            
            desc_dict = {}
            for desc in descriptions:
                key = (desc['classid'], desc['instanceid'])
                desc_dict[key] = desc
            
            inventory_items = []
            for asset in assets:
                class_id = asset['classid']
                instance_id = asset['instanceid']
                key = (class_id, instance_id)
                
                if key in desc_dict:
                    desc = desc_dict[key]
                    
                    if desc.get('tradable', 0) == 1:
                        item = {
                            'assetid': asset['assetid'],
                            'classid': class_id,
                            'instanceid': instance_id,
                            'amount': asset.get('amount', '1'),
                            'appid': app_id,
                            'contextid': context_id,
                            'name': desc.get('name', ''),
                            'market_name': desc.get('market_name', ''),
                            'tradable': desc.get('tradable', 0),
                            'marketable': desc.get('marketable', 0)
                        }
                        inventory_items.append(item)
            
            return inventory_items
            
        except Exception as e:
            print(f"Ошибка получения ассетов инвентаря: {e}")
            return []
    
    def create_trade_offer(self, login_data: Dict, trade_params: Dict, items_to_give: List[Dict], 
                          items_to_receive: List[Dict] = None, message: str = "") -> Optional[str]:
        
            
        try:
            if not self.setup_session_cookies(login_data):
                return None
            
            url = "https://steamcommunity.com/tradeoffer/new/send"
            
            trade_offer_create_params = {
                'newversion': True,
                'version': 4,
                'me': {
                    'assets': items_to_give,
                    'currency': [],
                    'ready': False
                },
                'them': {
                    'assets': items_to_receive or [],
                    'currency': [],
                    'ready': False
                }
            }
            
            form_data = {
                'sessionid': login_data['session_id'],
                'serverid': '1',
                'partner': trade_params['partner'],
                'tradeoffermessage': message,
                'json_tradeoffer': json.dumps(trade_offer_create_params),
                'captcha': '',
                'trade_offer_create_params': json.dumps({
                    'trade_offer_access_token': trade_params['token']
                })
            }
            
            response = self.session.post(url, data=form_data, timeout=30)
            
            if response.status_code != 200:
                print(f"Ошибка создания трейда: HTTP {response.status_code}")
                return None
            
            result = response.json()
            
            if result.get('strError'):
                print(f"Ошибка Steam API: {result['strError']}")
                return None
            
            trade_offer_id = result.get('tradeofferid')
            if trade_offer_id:
                print(f"Трейд успешно создан с ID: {trade_offer_id}")
                return str(trade_offer_id)
            
            print("Не удалось получить ID трейда из ответа")
            return None
            
        except Exception as e:
            print(f"Ошибка создания трейд-оффера: {e}")
            return None
    
    def send_trade_offer(self, mafile_path: str, trade_url: str, item_names: List[str] = None, 
                        send_all: bool = False, message: str = "") -> Dict:
        
            
        result = {
            'success': False,
            'trade_id': None,
            'error': None,
            'items_sent': 0
        }
        
        try:
            print(f"Начинаем отправку трейда...")
            
            trade_params = self.parse_trade_url(trade_url)
            if not trade_params:
                result['error'] = "Неверный формат трейд-ссылки"
                return result
            
            print(f"Трейд-параметры: partner={trade_params['partner']}")
            
            login_data = self.get_steam_login_data(mafile_path)
            if not login_data:
                result['error'] = "Не удалось загрузить данные авторизации из .mafile"
                return result
            
            print(f"Авторизация для аккаунта: {login_data['account_name']}")
            
            inventory_assets = self.get_inventory_assets(login_data['steam_id'])
            if not inventory_assets:
                result['error'] = "Инвентарь пуст или недоступен"
                return result
            
            print(f"Найдено {len(inventory_assets)} торгуемых предметов в инвентаре")
            
            items_to_send = []
            
            if send_all:
                items_to_send = inventory_assets
            elif item_names:
                for asset in inventory_assets:
                    if asset['name'] in item_names or asset['market_name'] in item_names:
                        items_to_send.append(asset)
            
            if not items_to_send:
                result['error'] = "Не найдено предметов для отправки"
                return result
            
            print(f"Отправляем {len(items_to_send)} предметов")
            
            trade_id = self.create_trade_offer(
                login_data=login_data,
                trade_params=trade_params,
                items_to_give=items_to_send,
                message=message
            )
            
            if trade_id:
                result['success'] = True
                result['trade_id'] = trade_id
                result['items_sent'] = len(items_to_send)
                print(f"Трейд успешно отправлен! ID: {trade_id}")
            else:
                result['error'] = "Не удалось создать трейд-оффер"
            
            return result
            
        except Exception as e:
            result['error'] = f"Критическая ошибка: {str(e)}"
            print(f"Ошибка отправки трейда: {e}")
            return result


def test_trade_manager():
    manager = SteamTradeManager()
    
    test_url = "https://steamcommunity.com/tradeoffer/new/?partner=123456789&token=AbCdEfGh"
    params = manager.parse_trade_url(test_url)
    print(f"Тест парсинга URL: {params}")
    
    print("Менеджер трейдов готов к работе!")


if __name__ == "__main__":
    test_trade_manager()
