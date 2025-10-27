
import requests
import json
import time
import re
import sys
import os
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from core.settings_manager import get_application_path


@dataclass
class InventoryItem:
    name: str
    market_name: str
    app_id: str
    asset_id: str
    class_id: str
    instance_id: str
    amount: int
    tradable: bool
    marketable: bool
    icon_url: str
    name_color: str = ""
    type: str = ""
    rarity: str = ""
    price_usd: float = 0.0
    price_local: float = 0.0
    currency: str = "USD"


class SteamInventoryParser:
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        
        self.price_cache = {}
        
        self.currencies = {
            'USD': 1,
            'EUR': 3,
            'GBP': 2,
            'RUB': 5,
            'CNY': 23,
            'CAD': 20,
            'AUD': 21,
        }
        
        self.country_codes = {
            'USD': 'US',
            'EUR': 'DE', 
            'GBP': 'GB',
            'RUB': 'RU',
            'CNY': 'CN',
            'CAD': 'CA',
            'AUD': 'AU',
        }
    
    def get_inventory(self, steam_id: str, app_id: str = "730", context_id: str = "2") -> List[InventoryItem]:
        
        
        url = f"https://steamcommunity.com/inventory/{steam_id}/{app_id}/{context_id}"
        
        try:
            response = self.session.get(url, timeout=30)
            
            if response.status_code != 200:
                print(f"Ошибка получения инвентаря: HTTP {response.status_code}")
                return []
            
            data = response.json()
            
            if not data.get('success'):
                print(f"Инвентарь недоступен или пуст")
                return []
            
            assets = data.get('assets', [])
            descriptions = data.get('descriptions', [])
            
            desc_dict = {}
            for desc in descriptions:
                key = (desc['classid'], desc['instanceid'])
                desc_dict[key] = desc
            
            items = []
            for asset in assets:
                class_id = asset['classid']
                instance_id = asset['instanceid']
                key = (class_id, instance_id)
                
                if key in desc_dict:
                    desc = desc_dict[key]
                    
                    item = InventoryItem(
                        name=desc.get('name', ''),
                        market_name=desc.get('market_name', ''),
                        app_id=app_id,
                        asset_id=asset['assetid'],
                        class_id=class_id,
                        instance_id=instance_id,
                        amount=int(asset.get('amount', 1)),
                        tradable=bool(desc.get('tradable', 0)),
                        marketable=bool(desc.get('marketable', 0)),
                        icon_url=desc.get('icon_url', ''),
                        name_color=desc.get('name_color', ''),
                        type=desc.get('type', ''),
                    )
                    
                    tags = desc.get('tags', [])
                    for tag in tags:
                        if tag.get('category') == 'Rarity':
                            item.rarity = tag.get('localized_tag_name', '')
                            break
                    
                    items.append(item)
            
            return items
            
        except requests.exceptions.RequestException as e:
            print(f"Ошибка сети при получении инвентаря: {e}")
            return []
        except json.JSONDecodeError as e:
            print(f"Ошибка парсинга JSON: {e}")
            return []
        except Exception as e:
            print(f"Неожиданная ошибка: {e}")
            return []
    
    def get_item_price(self, market_name: str, app_id: str = "730", currency: str = "USD") -> Tuple[float, str]:
        
        
        cache_key = f"{market_name}_{app_id}_{currency}"
        if cache_key in self.price_cache:
            return self.price_cache[cache_key]
        
        if currency not in self.currencies:
            print(f"Неподдерживаемая валюта {currency}, используем USD")
            currency = "USD"
        
        currency_code = self.currencies[currency]
        country_code = self.country_codes[currency]
        
        url = "https://steamcommunity.com/market/priceoverview/"
        params = {
            'country': country_code,
            'currency': currency_code,
            'appid': app_id,
            'market_hash_name': market_name
        }
        
        try:
            response = self.session.get(url, params=params, timeout=15)
            
            if response.status_code == 429:
                print(f"Ограничение Steam API для {market_name}, ждем 5 секунд...")
                time.sleep(5)
                response = self.session.get(url, params=params, timeout=15)
            
            if response.status_code != 200:
                print(f"Ошибка получения цены для {market_name}: HTTP {response.status_code}")
                return 0.0, self.get_currency_symbol(currency)
            
            data = response.json()
            
            if not data.get('success'):
                return 0.0, self.get_currency_symbol(currency)
            
            lowest_price = data.get('lowest_price', '0')
            price = self.parse_price_string(lowest_price)
            
            if currency == 'RUB' and price > 0:
                print(f"Цена для {market_name}: '{lowest_price}' -> {price} {currency}")
            
            result = (price, self.get_currency_symbol(currency))
            self.price_cache[cache_key] = result
            
            time.sleep(0.2)
            
            return result
            
        except requests.exceptions.RequestException as e:
            print(f"Ошибка сети при получении цены для {market_name}: {e}")
            return 0.0, self.get_currency_symbol(currency)
        except Exception as e:
            print(f"Ошибка при получении цены для {market_name}: {e}")
            return 0.0, self.get_currency_symbol(currency)
    
    def parse_price_string(self, price_str: str) -> float:
        if not price_str:
            return 0.0
        
        cleaned = price_str.strip()
        
        if '₽' in cleaned or 'руб' in cleaned.lower() or 'pуб' in cleaned:
            cleaned = re.sub(r'[₽руб.pуб]', '', cleaned, flags=re.IGNORECASE)
            cleaned = cleaned.strip()
            cleaned = re.sub(r'(\d)\s+(\d)', r'\1\2', cleaned)
            cleaned = cleaned.replace(',', '.')
        else:
            cleaned = re.sub(r'[^\d.,]', '', cleaned)
            if ',' in cleaned and '.' in cleaned:
                cleaned = cleaned.replace('.', '')
                cleaned = cleaned.replace(',', '.')
            elif ',' in cleaned and '.' not in cleaned:
                cleaned = cleaned.replace(',', '.')
        
        if not cleaned:
            return 0.0
        
        try:
            return float(cleaned)
        except ValueError:
            print(f"Не удалось распарсить цену: '{price_str}' -> '{cleaned}'")
            return 0.0
    
    def get_currency_symbol(self, currency: str) -> str:
        symbols = {
            'USD': '$',
            'EUR': '€',
            'GBP': '£',
            'RUB': '₽',
            'CNY': '¥',
            'CAD': 'C$',
            'AUD': 'A$',
        }
        return symbols.get(currency, '$')
    
    def steam_id_to_steam_id64(self, steam_id: str) -> Optional[str]:
        if steam_id.isdigit() and len(steam_id) == 17:
            return steam_id
        
        match = re.match(r'\[U:1:(\d+)\]', steam_id)
        if match:
            account_id = int(match.group(1))
            steam_id64 = str(account_id + 76561197960265728)
            return steam_id64
        
        if 'steamcommunity.com' in steam_id:
            match = re.search(r'/profiles/(\d+)', steam_id)
            if match:
                return match.group(1)
            
            match = re.search(r'/id/([^/]+)', steam_id)
            if match:
                custom_id = match.group(1)
                return self.resolve_vanity_url(custom_id)
        
        if not steam_id.isdigit():
            return self.resolve_vanity_url(steam_id)
        
        return None
    
    def resolve_vanity_url(self, vanity_url: str) -> Optional[str]:
        print(f"Резолв кастомного URL {vanity_url} не поддерживается без Steam API ключа")
        return None
    
    def get_account_steam_id64_from_mafile(self, mafile_path: str) -> Optional[str]:
        try:
            with open(mafile_path, 'r', encoding='utf-8') as f:
                mafile_data = json.load(f)
            
            steam_id64 = mafile_data.get('Session', {}).get('SteamID')
            if steam_id64:
                return str(steam_id64)
            
            for field in ['SteamID', 'steamid', 'steam_id']:
                if field in mafile_data:
                    return str(mafile_data[field])
            
            return None
            
        except Exception as e:
            print(f"Ошибка чтения Steam ID из mafile {mafile_path}: {e}")
            return None
    
    def analyze_account_inventory(self, login: str, app_id: str = "730", currency: str = "USD") -> Dict:
        
        
        from core.settings_manager import settings_manager
        import os
        
        result = {
            'login': login,
            'success': False,
            'items': [],
            'total_value': 0.0,
            'total_items': 0,
            'currency': currency,
            'currency_symbol': self.get_currency_symbol(currency),
            'error': None
        }
        
        try:
            accounts = settings_manager.get_accounts()
            if login not in accounts:
                result['error'] = "Аккаунт не найден в настройках"
                return result
            
            account_data = accounts[login]
            mafile_name = account_data.get('mafile')
            
            if not mafile_name:
                result['error'] = "У аккаунта нет .mafile"
                return result
            
            mafile_path = os.path.join(get_application_path(), "data", "mafiles", mafile_name)
            steam_id64 = self.get_account_steam_id64_from_mafile(mafile_path)
            
            if not steam_id64:
                result['error'] = "Не удалось получить Steam ID из .mafile"
                return result
            
            print(f"Получение инвентаря для {login} (Steam ID: {steam_id64})")
            inventory_items = self.get_inventory(steam_id64, app_id)
            
            if not inventory_items:
                result['error'] = "Инвентарь пуст или недоступен"
                return result
            
            items_with_prices = []
            total_value = 0.0
            
            for item in inventory_items:
                price = 0.0
                currency_symbol = self.get_currency_symbol(currency)
                
                if item.marketable and item.market_name:
                    try:
                        price, currency_symbol = self.get_item_price(item.market_name, app_id, currency)
                        item.price_local = price
                        item.currency = currency
                        total_value += price * item.amount
                    except Exception as e:
                        print(f"Ошибка получения цены для {item.market_name}: {e}")
                        item.price_local = 0.0
                        item.currency = currency
                else:
                    item.price_local = 0.0
                    item.currency = currency
                
                items_with_prices.append({
                    'name': item.name,
                    'market_name': item.market_name,
                    'amount': item.amount,
                    'price': item.price_local,
                    'total_price': item.price_local * item.amount,
                    'tradable': item.tradable,
                    'marketable': item.marketable,
                    'rarity': item.rarity,
                    'type': item.type,
                    'icon_url': item.icon_url,
                    'name_color': item.name_color,
                    'asset_id': item.asset_id,
                    'app_id': item.app_id,
                    'context_id': '2'
                })
            
            result.update({
                'success': True,
                'items': items_with_prices,
                'total_value': total_value,
                'total_items': len(inventory_items),
                'steam_id64': steam_id64
            })
            
            return result
            
        except Exception as e:
            result['error'] = f"Ошибка анализа инвентаря: {str(e)}"
            return result


def format_price(price: float, currency_symbol: str) -> str:
    if price == 0:
        return "—"
    
    if currency_symbol == '₽' and price >= 10:
        return f"{currency_symbol}{price:.0f}"
    elif currency_symbol == '₽':
        return f"{currency_symbol}{price:.2f}"
    else:
        return f"{currency_symbol}{price:.2f}"


if __name__ == "__main__":
    parser = SteamInventoryParser()
    
    test_item = "AK-47 | Redline (Field-Tested)"
    price, symbol = parser.get_item_price(test_item, "730", "USD")
    print(f"Цена {test_item}: {symbol}{price:.2f}")
