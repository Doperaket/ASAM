import requests
import threading
import time
import re
from datetime import datetime
from bs4 import BeautifulSoup
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from core.settings_manager import get_application_path


class SteamStatusParser:
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        self.cache = {}
        self.cache_timeout = 300
        
        self.steamcommunity_base = "https://steamcommunity.com"
        
    def clear_cache(self):
        self.cache.clear()
        print("🗑️ Кеш парсера статуса очищен")
    
    def _is_cache_valid(self, cache_entry):
        if not cache_entry:
            return False
        return (datetime.now() - cache_entry['timestamp']).seconds < self.cache_timeout
    
    def get_steam_id_from_mafile(self, login):
        try:
            from core.settings_manager import settings_manager
            accounts = settings_manager.get_accounts()
            
            if login not in accounts:
                print(f"❌ Аккаунт {login} не найден в настройках")
                return None
            
            mafile_name = accounts[login].get('mafile')
            if not mafile_name:
                print(f"❌ MaFile для аккаунта {login} не найден")
                return None
            
            import os
            import json
            mafile_path = os.path.join(get_application_path(), "data", "mafiles", mafile_name)
            
            if not os.path.exists(mafile_path):
                print(f"❌ Файл {mafile_name} не найден")
                return None
            
            with open(mafile_path, 'r', encoding='utf-8') as f:
                mafile_data = json.load(f)
            
            steam_id = mafile_data.get('Session', {}).get('SteamID')
            if not steam_id:
                steam_id = mafile_data.get('steamid')
                if not steam_id:
                    steam_id = mafile_data.get('account_name')
            
            if steam_id and str(steam_id).isdigit() and len(str(steam_id)) == 17:
                print(f"✅ SteamID из mafile для {login}: {steam_id}")
                return str(steam_id)
            
            print(f"❌ SteamID не найден в mafile для {login}")
            return None
            
        except Exception as e:
            print(f"❌ Ошибка получения SteamID из mafile для {login}: {e}")
            return None
    
    def get_steam_id_from_login(self, login):
        try:
            steam_id = self.get_steam_id_from_mafile(login)
            if steam_id:
                return steam_id
            
            print(f"🔍 Поиск SteamID через Steam Community для логина: {login}")
            
            direct_profile_url = f"{self.steamcommunity_base}/id/{login}"
            response = self.session.get(direct_profile_url, timeout=15, allow_redirects=True)
            
            if response.status_code == 200:
                final_url = response.url
                steam_id_match = re.search(r'/profiles/(\d{17})', final_url)
                if steam_id_match:
                    steam_id = steam_id_match.group(1)
                    print(f"✅ SteamID найден через прямой URL: {steam_id}")
                    return steam_id
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                script_tags = soup.find_all('script')
                for script in script_tags:
                    if script.string:
                        patterns = [
                            r'"steamid":"(\d{17})"',
                            r'g_steamID\s*=\s*["\'](\d{17})["\']',
                            r'steamid["\']?\s*:\s*["\'](\d{17})["\']',
                            r'UserSteamID["\']?\s*=\s*["\'](\d{17})["\']'
                        ]
                        
                        for pattern in patterns:
                            steam_id_match = re.search(pattern, script.string)
                            if steam_id_match:
                                steam_id = steam_id_match.group(1)
                                print(f"✅ SteamID найден в скрипте: {steam_id}")
                                return steam_id
            
            xml_url = f"{self.steamcommunity_base}/id/{login}?xml=1"
            response = self.session.get(xml_url, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'xml')
                steamid_tag = soup.find('steamID64')
                if steamid_tag and steamid_tag.text:
                    steam_id = steamid_tag.text.strip()
                    if steam_id.isdigit() and len(steam_id) == 17:
                        print(f"✅ SteamID найден через XML: {steam_id}")
                        return steam_id
            
            if login.isdigit() and len(login) == 17:
                profile_url = f"{self.steamcommunity_base}/profiles/{login}"
                response = self.session.get(profile_url, timeout=10)
                if response.status_code == 200:
                    print(f"✅ Логин уже является SteamID: {login}")
                    return login
            
            print(f"❌ SteamID для логина '{login}' не найден")
            return None
            
        except Exception as e:
            print(f"❌ Ошибка получения SteamID для {login}: {e}")
            return None
    
    def get_vac_status(self, steam_id):
        try:
            profile_url = f"{self.steamcommunity_base}/profiles/{steam_id}"
            
            response = self.session.get(profile_url, timeout=15)
            if response.status_code != 200:
                return "Ошибка доступа"
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            ban_selectors = [
                'div.profile_ban_status',
                'div.profile_ban',
                'div.profile_content_inner .profile_ban_status',
                '.profile_ban_status'
            ]
            
            for selector in ban_selectors:
                ban_info = soup.select_one(selector)
                if ban_info:
                    ban_text = ban_info.get_text(strip=True).lower()
                    
                    if 'vac ban' in ban_text:
                        days_match = re.search(r'(\d+)\s*day', ban_text)
                        if days_match:
                            days = days_match.group(1)
                            return f"VAC Ban ({days} дн.)"
                        return "VAC Ban"
                    elif 'game ban' in ban_text:
                        count_match = re.search(r'(\d+)\s*game ban', ban_text)
                        if count_match:
                            count = count_match.group(1)
                            return f"Game Ban ({count})"
                        return "Game Ban"
                    elif 'community ban' in ban_text:
                        return "Community Ban"
                    elif 'trade ban' in ban_text:
                        return "Trade Ban"
            
            page_text = response.text.lower()
            if 'vac ban' in page_text and 'no vac ban' not in page_text:
                return "VAC Ban"
            elif 'game ban' in page_text and 'no game ban' not in page_text:
                return "Game Ban"
            elif 'trade ban' in page_text:
                return "Trade Ban"
            
            return "Чистый"
            
        except Exception as e:
            print(f"❌ Ошибка получения VAC статуса: {e}")
            return "Ошибка"
    
    def get_account_level(self, steam_id):
        try:
            profile_url = f"{self.steamcommunity_base}/profiles/{steam_id}"
            
            response = self.session.get(profile_url, timeout=15)
            if response.status_code != 200:
                return "Неизвестно"
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            level_selectors = [
                'span.friendPlayerLevelNum',
                'span.profile_level_num',
                '.persona_level .friendPlayerLevelNum',
                '.friendPlayerLevel .friendPlayerLevelNum',
                '.profile_level .friendPlayerLevelNum'
            ]
            
            for selector in level_selectors:
                level_element = soup.select_one(selector)
                if level_element:
                    level_text = level_element.get_text(strip=True)
                    if level_text.isdigit():
                        return level_text
            
            script_tags = soup.find_all('script')
            for script in script_tags:
                if script.string:
                    level_patterns = [
                        r'"level":(\d+)',
                        r'level["\']?\s*:\s*(\d+)',
                        r'friendPlayerLevel["\']?\s*:\s*(\d+)'
                    ]
                    
                    for pattern in level_patterns:
                        level_match = re.search(pattern, script.string)
                        if level_match:
                            level = level_match.group(1)
                            if level.isdigit():
                                return level
            
            return "0"
            
        except Exception as e:
            print(f"❌ Ошибка получения уровня аккаунта: {e}")
            return "Ошибка"
    
    def get_account_games_count(self, steam_id):
        try:
            profile_url = f"{self.steamcommunity_base}/profiles/{steam_id}"
            response = self.session.get(profile_url, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                games_link = soup.find('a', href=re.compile(r'/games/'))
                if games_link:
                    games_text = games_link.get_text(strip=True)
                    count_match = re.search(r'(\d{1,3}(?:,\d{3})*|\d+)', games_text)
                    if count_match:
                        count_str = count_match.group(1).replace(',', '')
                        if count_str.isdigit():
                            print(f"✅ Игр найдено в профиле: {count_str}")
                            return count_str
                
                game_count_selectors = [
                    '.profile_count_link_total',
                    '.profile_summary .profile_count_link_total',
                    'span.profile_count_link_total'
                ]
                
                for selector in game_count_selectors:
                    count_elem = soup.select_one(selector)
                    if count_elem:
                        count_text = count_elem.get_text(strip=True)
                        count_match = re.search(r'(\d{1,3}(?:,\d{3})*|\d+)', count_text)
                        if count_match:
                            count_str = count_match.group(1).replace(',', '')
                            if count_str.isdigit():
                                print(f"✅ Игр найдено через селектор: {count_str}")
                                return count_str
            
            games_url = f"{self.steamcommunity_base}/profiles/{steam_id}/games/?tab=all"
            response = self.session.get(games_url, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                count_selectors = [
                    'span.profile_count_link_total',
                    '.profile_count_link_total',
                    '.games_list_tab .profile_count_link_total'
                ]
                
                for selector in count_selectors:
                    count_elem = soup.select_one(selector)
                    if count_elem:
                        count_text = count_elem.get_text(strip=True)
                        count_match = re.search(r'(\d{1,3}(?:,\d{3})*|\d+)', count_text)
                        if count_match:
                            count_str = count_match.group(1).replace(',', '')
                            if count_str.isdigit():
                                print(f"✅ Игр найдено на странице игр: {count_str}")
                                return count_str
                
                script_tags = soup.find_all('script')
                for script in script_tags:
                    if script.string:
                        patterns = [
                            r'rgGames.*?length["\']?\s*:\s*(\d+)',
                            r'game_count["\']?\s*:\s*(\d+)',
                            r'total_count["\']?\s*:\s*(\d+)'
                        ]
                        
                        for pattern in patterns:
                            games_count_match = re.search(pattern, script.string)
                            if games_count_match:
                                count = games_count_match.group(1)
                                print(f"✅ Игр найдено в JS: {count}")
                                return count
            
            print(f"⚠️ Количество игр для {steam_id} недоступно (приватный профиль)")
            return "Приватные"
            
        except Exception as e:
            print(f"❌ Ошибка получения количества игр: {e}")
            return "Ошибка"
    
    def get_profile_creation_date(self, steam_id):
        try:
            profile_url = f"{self.steamcommunity_base}/profiles/{steam_id}"
            
            response = self.session.get(profile_url, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                creation_date_elem = soup.find('div', class_='profile_summary')
                if creation_date_elem:
                    date_text = creation_date_elem.get_text()
                    date_patterns = [
                        r'Member since (\w+ \d{4})',
                        r'Участник с (\w+ \d{4})',
                        r'since (\d{1,2} \w+ \d{4})'
                    ]
                    
                    for pattern in date_patterns:
                        date_match = re.search(pattern, date_text)
                        if date_match:
                            return date_match.group(1)
            
            return "Неизвестна"
            
        except Exception as e:
            print(f"❌ Ошибка получения даты создания: {e}")
            return "Ошибка"
    
    def get_wallet_balance(self, login):
        try:
            from steam_api.steam_client import SteamClient
            from core.settings_manager import settings_manager
            
            password = settings_manager.get_account_password(login)
            if not password:
                print(f"❌ Пароль для аккаунта {login} не найден")
                return "Нет пароля"
            
            accounts = settings_manager.get_accounts()
            if login not in accounts:
                print(f"❌ Аккаунт {login} не найден")
                return "Аккаунт не найден"
            
            mafile_name = accounts[login].get('mafile')
            if not mafile_name:
                print(f"❌ MaFile для {login} не найден")
                return "Нет MaFile"
            
            import json
            import os
            mafile_path = os.path.join(get_application_path(), "data", "mafiles", mafile_name)
            
            if not os.path.exists(mafile_path):
                print(f"❌ MaFile не существует: {mafile_path}")
                return "MaFile не найден"
            
            with open(mafile_path, 'r', encoding='utf-8') as f:
                mafile_data = json.load(f)
            
            shared_secret = mafile_data.get('shared_secret')
            if not shared_secret:
                print(f"❌ shared_secret не найден в MaFile для {login}")
                return "Нет shared_secret"
            
            client = SteamClient(auto_start=True)
            
            try:
                print(f"🔑 Авторизация в Steam для {login}...")
                session_id, session_data = client.login(
                    username=login,
                    password=password,
                    shared_secret=shared_secret
                )
                
                if not session_id:
                    print(f"❌ Ошибка авторизации: не удалось получить session_id")
                    return "Ошибка авторизации"
                
                print(f"💰 Получение баланса для {login}...")
                balance_result = client.get_wallet_balance(session_id)
                
                if balance_result.get('success'):
                    balance = balance_result.get('balance', 0)
                    currency = balance_result.get('currency', 'USD')
                    formatted_balance = balance_result.get('formatted', f'{balance} {currency}')
                    
                    print(f"✅ Баланс {login}: {formatted_balance}")
                    return {
                        'balance': balance,
                        'currency': currency,
                        'formatted': formatted_balance
                    }
                else:
                    print(f"❌ Ошибка получения баланса: {balance_result.get('error')}")
                    return "Ошибка получения"
                    
            finally:
                try:
                    if 'session_id' in locals():
                        client.logout(session_id)
                except:
                    pass
                
        except Exception as e:
            print(f"❌ Ошибка получения баланса для {login}: {e}")
            return "Ошибка"
    
    def get_full_account_status(self, login):
        cache_key = f"status_{login}"
        if cache_key in self.cache and self._is_cache_valid(self.cache[cache_key]):
            print(f"🔄 Использую кешированные данные для {login}")
            return self.cache[cache_key]['data']
        
        try:
            print(f"🔍 Получение статуса для {login}...")
            
            steam_id = self.get_steam_id_from_login(login)
            if not steam_id:
                print(f"❌ Не удалось получить SteamID для {login}")
                return {
                    'vac_status': 'Профиль не найден',
                    'level': 'Неизвестно',
                    'games_count': 'Неизвестно',
                    'creation_date': 'Неизвестна',
                    'steam_id': None,
                    'status': 'error'
                }
            
            print(f"✅ SteamID для {login}: {steam_id}")
            
            vac_status = self.get_vac_status(steam_id)
            level = self.get_account_level(steam_id)
            games_count = self.get_account_games_count(steam_id)
            creation_date = self.get_profile_creation_date(steam_id)
            wallet_balance = self.get_wallet_balance(login)
            
            status_data = {
                'vac_status': vac_status,
                'level': level,
                'games_count': games_count,
                'creation_date': creation_date,
                'wallet_balance': wallet_balance,
                'steam_id': steam_id,
                'last_update': datetime.now().isoformat(),
                'status': 'success'
            }
            
            self.cache[cache_key] = {
                'data': status_data,
                'timestamp': datetime.now()
            }
            
            print(f"✅ Статус {login}: VAC={vac_status}, Level={level}, Games={games_count}")
            return status_data
            
        except Exception as e:
            print(f"❌ Ошибка получения статуса {login}: {e}")
            return {
                'vac_status': 'Ошибка подключения',
                'level': 'Ошибка',
                'games_count': 'Ошибка',
                'creation_date': 'Ошибка',
                'steam_id': None,
                'status': 'error'
            }


class SteamStatusManager:
    
    def __init__(self, settings_manager):
        self.settings_manager = settings_manager
        self.parser = SteamStatusParser()
        self.update_thread = None
        self.is_running = False
        
    def start_auto_update(self):
        if not self.settings_manager.get_auto_status_enabled():
            print("🔄 Автообновление статуса отключено")
            return
            
        if self.is_running:
            print("🔄 Автообновление статуса уже запущено")
            return
            
        self.is_running = True
        self.update_thread = threading.Thread(target=self._auto_update_loop, daemon=True)
        self.update_thread.start()
        print("🚀 Автообновление статуса запущено")
    
    def stop_auto_update(self):
        self.is_running = False
        if self.update_thread:
            self.update_thread.join(timeout=1.0)
        print("⏹️ Автообновление статуса остановлено")
    
    def _auto_update_loop(self):
        while self.is_running:
            try:
                if not self.settings_manager.get_auto_status_enabled():
                    break
                
                interval_minutes = self.settings_manager.get_status_interval()
                
                accounts = self.settings_manager.get_accounts()
                
                for login in accounts.keys():
                    if not self.is_running:
                        break
                    
                    try:
                        self.update_single_account(login)
                        time.sleep(2)
                    except Exception as e:
                        print(f"❌ Ошибка обновления {login}: {e}")
                
                for _ in range(interval_minutes * 60):
                    if not self.is_running:
                        break
                    time.sleep(1)
                    
            except Exception as e:
                print(f"❌ Ошибка в цикле автообновления: {e}")
                time.sleep(60)
    
    def update_single_account(self, login):
        try:
            print(f"🔄 Обновление статуса для {login}...")
            
            status = self.parser.get_full_account_status(login)
            
            if status and status.get('status') == 'success':
                self.settings_manager.set_account_status(login, status)
                print(f"✅ Статус {login} обновлен и сохранен")
                return status
            else:
                print(f"❌ Не удалось получить статус для {login}")
                return None
                
        except Exception as e:
            print(f"❌ Ошибка обновления статуса {login}: {e}")
            return None
