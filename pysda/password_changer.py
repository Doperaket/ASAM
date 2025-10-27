

import base64
import time
import urllib.parse
import re
from typing import Optional, Dict, Any, Union, List

from .utils.logger_setup import logger, print_and_log
from .utils.cookies_and_session import session_to_dict, extract_cookies_for_domain
from .steampy.client import SteamClient
from .steampy.confirmation import ConfirmationExecutor, Confirmation


class AccountContext:
    def __init__(self, account_name: str, password: str = None):
        self.account_name = account_name
        self.password = password
        self.username = account_name


class DisplayFormatter:
    def __init__(self):
        pass
    
    def format_message(self, message: str) -> str:
        return message


class Messages:
    PASSWORD_CHANGED_SUCCESSFULLY = "Пароль успешно изменен"
    INVALID_PASSWORD = "Неверный пароль"
    ERROR_OCCURRED = "Произошла ошибка"


class PasswordConstants:
    MIN_PASSWORD_LENGTH = 8
    STRONG_PASSWORD_LENGTH = 12
    SPECIAL_CHARS = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    MAX_POLL_ATTEMPTS = 10
    POLL_DELAY = 3
    MOBILE_CONFIRMATION_TYPE = 6
    MOBILE_CONFIRMATION_TYPE_NAME = 'Account details'
    RSA_ENCODING = 'ascii'
    RSA_ENCODING_UTF8 = 'utf8'

class HttpConstants:
    BROWSER_USER_AGENT = (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/'
        '537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36'
    )
    
    COMMON_HEADERS = {
        'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        'Connection': 'keep-alive',
        'User-Agent': BROWSER_USER_AGENT,
        'sec-ch-ua': '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"'
    }
    
    AJAX_HEADERS = {
        **COMMON_HEADERS,
        'Accept': '*/*',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
        'X-Requested-With': 'XMLHttpRequest'
    }
    
    FORM_HEADERS = {
        **COMMON_HEADERS,
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Origin': 'https://help.steampowered.com'
    }

class SteamUrls:
    HELP_CHANGE_PASSWORD = "https://help.steampowered.com/wizard/HelpChangePassword?redir=store/account/"
    ENTER_CODE = "https://help.steampowered.com/en/wizard/HelpWithLoginInfoEnterCode"
    SEND_RECOVERY_CODE = "https://help.steampowered.com/en/wizard/AjaxSendAccountRecoveryCode"
    POLL_CONFIRMATION = "https://help.steampowered.com/en/wizard/AjaxPollAccountRecoveryConfirmation"
    VERIFY_RECOVERY_CODE = "https://help.steampowered.com/en/wizard/AjaxVerifyAccountRecoveryCode"
    GET_NEXT_STEP = "https://help.steampowered.com/en/wizard/AjaxAccountRecoveryGetNextStep"
    VERIFY_PASSWORD = "https://help.steampowered.com/en/wizard/AjaxAccountRecoveryVerifyPassword/"
    CHANGE_PASSWORD = "https://help.steampowered.com/en/wizard/AjaxAccountRecoveryChangePassword/"
    GET_RSA_KEY = "https://help.steampowered.com/en/login/getrsakey/"
    CHECK_PASSWORD_AVAILABLE = "https://help.steampowered.com/en/wizard/AjaxCheckPasswordAvailable/"
    ACCOUNT_TEST = "https://store.steampowered.com/en/account/"

class HttpRequestHelper:
    
    @staticmethod
    def get_common_headers() -> Dict[str, str]:
        return HttpConstants.COMMON_HEADERS.copy()
    
    @staticmethod
    def get_ajax_headers() -> Dict[str, str]:
        return HttpConstants.AJAX_HEADERS.copy()
    
    @staticmethod
    def get_form_headers() -> Dict[str, str]:
        return HttpConstants.FORM_HEADERS.copy()
    
    @staticmethod
    def build_referer_url(base_url: str, params: Dict[str, str]) -> str:
        param_strings = [f"{k}={v}" for k, v in params.items()]
        return f"{base_url}?{'&'.join(param_strings)}"


class PasswordChanger:
    
    
    def __init__(self, account_context: AccountContext) -> None:
        
        self.account_context: AccountContext = account_context
        self.formatter: DisplayFormatter = DisplayFormatter()
        self.http_helper: HttpRequestHelper = HttpRequestHelper()
        self.username: str = account_context.account_name
        self.steam_client: Optional[SteamClient] = None
        
        self.recovery_params: Dict[str, str] = {}
    
    def change_password(self, account_context: AccountContext) -> bool:
        
            
        try:
            print_and_log(self.formatter.format_section_header("🔒 Смена пароля"))
            print_and_log("⚠️  ВНИМАНИЕ: Смена пароля может затронуть работу бота!")
            print_and_log("💡 Убедитесь, что у вас есть доступ к мобильному приложению Steam Guard")
            print_and_log("")
            
            return self.execute()
            
        except Exception as e:
            print_and_log(f"❌ Ошибка смены пароля: {e}", "ERROR")
            input("Нажмите Enter для продолжения...")
            return False
        
    def execute(self) -> bool:
        
        try:
            print_and_log(f"🔒 Начинаем смену пароля для аккаунта: {self.username}")
            print_and_log("")
            
            self.steam_client = self.account_context.cookie_manager.get_steam_client()
            if not self.steam_client:
                print_and_log("❌ Не удалось получить Steam клиент", "ERROR")
                return False
            
            if not self._verify_current_session():
                print_and_log("❌ Сессия неактивна, необходимо войти в аккаунт", "ERROR")
                return False
            
            if not self._verify_steam_guard_data():
                print_and_log("❌ Отсутствуют данные Steam Guard", "ERROR")
                return False
            
            new_password: Optional[str] = self._get_new_password()
            if not new_password:
                return False
            
            if not self._confirm_password_change():
                return False
            
            if self._change_password_full_process(new_password):
                if self._update_configuration(new_password):
                    print_and_log("✅ Пароль успешно изменен и сохранен в конфигурации!")
                    print_and_log("💡 Пароль изменен успешно!")
                    return True
                else:
                    print_and_log("❌ Ошибка при сохранении пароля в конфигурации!")
                    return False
            else:
                print_and_log("❌ Не удалось изменить пароль")
                return False
                
        except Exception as e:
            print_and_log(f"❌ Ошибка в процессе смены пароля: {e}", "ERROR")
            return False
    
    def _change_password_full_process(self, new_password: str) -> bool:
        
            
        try:
            print_and_log("🔄 Начинаем полный процесс смены пароля...")
            
            account_config = self.account_context.config_manager.accounts_settings.get(self.username, {})
            steam_id = account_config.get('steam_id', '')
            if not steam_id:
                print_and_log("❌ Не удалось получить steam_id из конфигурации")
                return False
            
            print_and_log("🔄 Получение параметров смены пароля...")
            if not self._initialize_recovery(steam_id):
                return False
            
            print_and_log("🔄 Переход к вводу кода...")
            if not self._goto_enter_code():
                return False
            
            print_and_log("🔄 Отправка запроса на восстановление...")
            if not self._send_recovery_request():
                return False
            
            print_and_log("🔄 Проверка подтверждения в мобильном приложении...")
            if not self.confirm_via_guard():
                return False
            
            print_and_log("📱 Ожидание подтверждения в мобильном приложении...")
            if not self._poll_confirmation():
                return False
            
            print_and_log("🔄 Верификация кода восстановления...")
            if not self._verify_recovery_code():
                return False
            
            print_and_log("🔄 Получение следующего шага...")
            if not self._get_next_step():
                return False
            
            print_and_log("🔄 Верификация старого пароля...")
            if not self._verify_old_password():
                return False
            
            print_and_log("🔐 Установка нового пароля...")
            if not self._set_new_password(new_password):
                return False
            
            print_and_log("✅ Пароль успешно изменен!")
            return True
            
        except Exception as e:
            print_and_log(f"❌ Ошибка в процессе смены пароля: {e}", "ERROR")
            return False
    
    def confirm_via_guard(self) -> bool:
        
        try:
            confirmation_executor = ConfirmationExecutor(
                identity_secret=self.account_context.cookie_manager.steam_client.steam_guard['identity_secret'],
                my_steam_id=self.account_context.cookie_manager.steam_client.steam_id,
                session=self.account_context.cookie_manager.steam_client._session
            )
            confirmations_page = confirmation_executor._fetch_confirmations_page()
            confirmations_json = confirmations_page.json()
            
            if not confirmations_json.get('success'):
                logger.error("❌ Не удалось получить мобильные подтверждения")
                return False

            all_confirmations = confirmations_json.get('conf', [])
            
            if len(all_confirmations) == 0:
                print_and_log("❌ Нет подтверждений в мобильном приложении")
                return False
            
            for confirmation in all_confirmations:
                if (confirmation.get('type_name', "") == PasswordConstants.MOBILE_CONFIRMATION_TYPE_NAME and 
                    confirmation.get('type', -1) == PasswordConstants.MOBILE_CONFIRMATION_TYPE):
                    print_and_log(f"✅ Найдено подтверждение для аккаунта: {confirmation}")
                    if confirmation.get('creator_id', "") == self.recovery_params["s"]:
                        print_and_log(f"✅ Найдено наше подтверждение для аккаунта на смену пароля: {confirmation}")
                        conf = Confirmation(
                            data_confid=confirmation['id'],
                            nonce=confirmation['nonce'],
                            creator_id=int(confirmation['creator_id'])
                        )
                        response = confirmation_executor._send_confirmation(conf)
                        if response and response.get('success'):
                            return True
                        else:
                            error_message = response.get('error', 'Unknown error') if response else 'No response'
                            logger.error(f"❌ Ошибка подтверждения: {error_message}")
                            return False
            
            else:
                print_and_log("❌ Не найдено подтверждение для аккаунта")
                return False
            
        except Exception as e:
            print_and_log(f"❌ Ошибка в процессе смены пароля (во время подтверждения в мобильном приложении): {e}", "ERROR")
            return False

    def _initialize_recovery(self, steam_id: str) -> bool:
        
        
            
        try:
            print_and_log(f"🔍 Начинаем инициализацию для Steam ID: {steam_id}")
    
            print_and_log("🔍 Отправляем запрос с куки от steamcommunity.com...")

            headers = {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'Referer': 'https://store.steampowered.com/',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'same-site',
                'Sec-Fetch-User': '?1',
                'Upgrade-Insecure-Requests': '1',
                **self.http_helper.get_common_headers()
            }
            
            response = self.steam_client._session.get(
                SteamUrls.HELP_CHANGE_PASSWORD,
                headers=headers,
                allow_redirects=True
            )
            
            print_and_log(f"🔍 Статус ответа: {response.status_code}")
            print_and_log(f"🔍 URL ответа: {response.url}")
            print_and_log(f"🔍 История редиректов: {len(response.history)} редиректов")
            
            if self.username.lower() in response.text.lower():
                print(f"✅ {self.username} найден в тексте - АВТОРИЗОВАН")
            else:
                print(f"❌ {self.username} НЕ найден в тексте - НЕ АВТОРИЗОВАН")
                return False

            if '/login' in response.url:
                print_and_log("❌ Steam снова перенаправил на страницу входа")
                print_and_log("💡 Возможные причины:")
                print_and_log("  • Сессия истекла")
                print_and_log("  • Нет авторизации для операций восстановления")
                print_and_log("  • Требуется повторный вход в аккаунт")
                return False
            
            if response.history:
                print_and_log("✅ Обнаружен редирект, извлекаем параметры из URL...")
                
                final_url = response.url
                parsed_url = urllib.parse.urlparse(final_url)
                query_params = urllib.parse.parse_qs(parsed_url.query)
                
                print_and_log(f"🔍 Финальный URL: {final_url}")
                print_and_log(f"🔍 Query параметры: {query_params}")
                
                try:
                    self.recovery_params = {
                        's': query_params.get('s', [None])[0],
                        'account': query_params.get('account', [None])[0],
                        'reset': query_params.get('reset', [None])[0],
                        'issueid': query_params.get('issueid', [None])[0],
                        'lost': query_params.get('lost', ['0'])[0]
                    }
                    
                    print_and_log(f"🔍 Извлеченные параметры: {self.recovery_params}")
                    
                    if all(v is not None for k, v in self.recovery_params.items() if k != 'lost'):
                        recovery_id = self.recovery_params['s']
                        print_and_log(f"✅ Процесс восстановления инициализирован. id восстановления: {recovery_id}")
                        return True
                    else:
                        print_and_log("❌ Не все обязательные параметры найдены в редиректе")
                        return False
                        
                except Exception as e:
                    print_and_log(f"❌ Ошибка извлечения параметров из редиректа: {e}")
                    return False
            
            html_content = response.text
            print_and_log("🔍 Редиректа не было, анализируем HTML...")
            
            error_patterns = [
                r'<div[^>]*id=["\']error_description["\'][^>]*>([^<]+)</div>',
                r'<div[^>]*class="[^"]*error[^"]*"[^>]*>([^<]+)</div>',
            ]
            
            for pattern in error_patterns:
                error_match = re.search(pattern, html_content, re.IGNORECASE)
                if error_match:
                    error_text = error_match.group(1).strip()
                    print_and_log(f"❌ Найдена ошибка Steam: {error_text}")
                    return False
            
            print_and_log("❌ Не удалось получить параметры смены пароля")
            print_and_log(f"🔍 Первые 500 символов HTML: {html_content[:500]}")
            return False
            
        except Exception as e:
            print_and_log(f"❌ Исключение в _initialize_recovery: {type(e).__name__}: {str(e)}", "ERROR")
            import traceback
            print_and_log(f"🔍 Трассировка: {traceback.format_exc()}", "ERROR")
            return False
    
    def _goto_enter_code(self) -> bool:
        
        try:
            print_and_log("🔍 Переход к странице ввода кода...")
            
            url = SteamUrls.ENTER_CODE
            params = {
                's': self.recovery_params['s'],
                'account': self.recovery_params['account'],
                'reset': self.recovery_params['reset'],
                'lost': self.recovery_params['lost'],
                'issueid': self.recovery_params['issueid'],
                'sessionid': self.steam_client._get_session_id(),
                'wizard_ajax': '1',
                'gamepad': '0'
            }
            
            print_and_log(f"🔍 URL: {url}")
            print_and_log(f"🔍 Параметры: {params}")
            
            headers = {
                **self.http_helper.get_ajax_headers(),
                'Referer': self.http_helper.build_referer_url(url, self.recovery_params)
            }
            
            response = self.steam_client._session.get(url, params=params, headers=headers)
            
            print_and_log(f"🔍 Статус ответа: {response.status_code}")
            
            if response.status_code == 200:
                content = response.text
                print_and_log(f"🔍 Длина содержимого: {len(content)}")
                print_and_log(f"🔍 Первые 300 символов: {content[:300]}")
                
                print_and_log("✅ Переход к вводу кода выполнен успешно")
                return True
            else:
                print_and_log(f"❌ HTTP ошибка: {response.status_code}")
                return False
                
        except Exception as e:
            print_and_log(f"❌ Ошибка перехода к вводу кода: {e}", "ERROR")
            return False
    
    def _send_recovery_request(self) -> bool:
        
        try:
            url = SteamUrls.SEND_RECOVERY_CODE
            data = {
                'sessionid': self.steam_client._get_session_id(),
                'wizard_ajax': '1',
                'gamepad': '0',
                's': self.recovery_params['s'],
                'method': '8',
                'link': '',
                'n': '1'
            }
            
            headers = {
                **self.http_helper.get_form_headers(),
                'Referer': self.http_helper.build_referer_url(SteamUrls.ENTER_CODE, self.recovery_params)
            }
            
            response = self.steam_client._session.post(url, data=data, headers=headers)
            if response.status_code == 200:
                try:
                    result = response.json()
                    logger.info(f"🔍 Результат отправки запроса: {result}")
                    if result.get('success'):
                        print_and_log("✅ Запрос на восстановление отправлен")
                        return True
                    else:
                        print_and_log(f"❌ Ошибка отправки запроса: {result.get('errorMsg', 'Unknown error')}")
                        return False
                except:
                    print_and_log("✅ Запрос отправлен (ответ не в JSON)")
                    return True
            
            print_and_log(f"❌ HTTP ошибка: {response.status_code}")
            return False
            
        except Exception as e:
            print_and_log(f"❌ Ошибка отправки запроса: {e}", "ERROR")
            return False
    
    def _poll_confirmation(self) -> bool:
        
        try:
            url = SteamUrls.POLL_CONFIRMATION
            data = {
                'sessionid': self.steam_client._get_session_id(),
                'wizard_ajax': '1',
                'gamepad': '0',
                's': self.recovery_params['s'],
                'reset': self.recovery_params['reset'],
                'lost': self.recovery_params['lost'],
                'method': '8',
                'issueid': self.recovery_params['issueid']
            }
            
            headers = {
                **self.http_helper.get_form_headers(),
                'Referer': self.http_helper.build_referer_url(SteamUrls.ENTER_CODE, self.recovery_params)
            }
            
            for attempt in range(PasswordConstants.MAX_POLL_ATTEMPTS):
                print_and_log(f"⏳ Попытка {attempt + 1}/{PasswordConstants.MAX_POLL_ATTEMPTS}")
                
                response = self.steam_client._session.post(url, data=data, headers=headers)
                
                if response.status_code == 200:
                    try:
                        result = response.json()
                        logger.info(f"🔍 Результат поллинга подтверждения: {result}")
                        if not result.get('errorMsg'):
                            print_and_log("✅ Подтверждение получено!")
                            return True
                        elif 'ожидание' in result.get('errorMsg', '').lower():
                            time.sleep(PasswordConstants.POLL_DELAY)
                            continue
                        else:
                            print_and_log(f"❌ Ошибка подтверждения: {result.get('errorMsg')}")
                            return False
                    except:
                        print_and_log("✅ Получен ответ (проверяем как успех)")
                        return True
                
                time.sleep(PasswordConstants.POLL_DELAY)
            
            print_and_log("❌ Подтверждение не получено в течение 3 минут")
            return False
            
        except Exception as e:
            print_and_log(f"❌ Ошибка поллинга: {e}", "ERROR")
            return False
    
    def _verify_recovery_code(self) -> bool:
        
        try:
            url = SteamUrls.VERIFY_RECOVERY_CODE
            params = {
                'code': '',
                's': self.recovery_params['s'],
                'reset': self.recovery_params['reset'],
                'lost': self.recovery_params['lost'],
                'method': '8',
                'issueid': self.recovery_params['issueid'],
                'sessionid': self.steam_client._get_session_id(),
                'wizard_ajax': '1',
                'gamepad': '0'
            }
            
            response = self.steam_client._session.get(url, params=params)
            if response.status_code == 200:
                try:
                    result = response.json()
                    logger.info(f"🔍 Результат верификации кода: {result}")
                    return not result.get('errorMsg')
                except:
                    return True
            
            return False
            
        except Exception as e:
            print_and_log(f"❌ Ошибка верификации кода: {e}", "ERROR")
            return False
    
    def _get_next_step(self) -> bool:
        
        try:
            url = SteamUrls.GET_NEXT_STEP
            data = {
                'sessionid': self.steam_client._get_session_id(),
                'wizard_ajax': '1',
                's': self.recovery_params['s'],
                'account': self.recovery_params['account'],
                'reset': self.recovery_params['reset'],
                'issueid': self.recovery_params['issueid'],
                'lost': '2'
            }
            
            response = self.steam_client._session.post(url, data=data)
            if response.status_code == 200:
                try:
                    result = response.json()
                    logger.info(f"🔍 Результат получения шага: {result}")
                    return not result.get('errorMsg')
                except:
                    return True
            
            return False
            
        except Exception as e:
            print_and_log(f"❌ Ошибка получения шага: {e}", "ERROR")
            return False
    
    def _verify_old_password(self) -> bool:
        
        try:
            account_config = self.account_context.config_manager.accounts_settings.get(self.username, {})
            current_password = account_config.get('password', '')
            if not current_password:
                print_and_log("❌ Не удалось получить текущий пароль")
                return False
            
            rsa_key = self._get_rsa_key()
            if not rsa_key:
                return False
            
            encrypted_password = self._encrypt_password(current_password, rsa_key)
            if not encrypted_password:
                return False
            
            url = SteamUrls.VERIFY_PASSWORD
            data = {
                'sessionid': self.steam_client._get_session_id(),
                's': self.recovery_params['s'],
                'lost': '2',
                'reset': '1',
                'password': encrypted_password,
                'rsatimestamp': rsa_key['timestamp']
            }
        
            response = self.steam_client._session.post(url, data=data)
            if response.status_code == 200:
                try:
                    result = response.json()
                    logger.info(f"🔍 Результат верификации пароля: {result}")
                    return not result.get('errorMsg')
                except:
                    return True
            
            return False
            
        except Exception as e:
            print_and_log(f"❌ Ошибка верификации пароля: {e}", "ERROR")
            return False
    
    def _set_new_password(self, new_password: str) -> bool:
        
            
        try:
            if not self._check_password_available(new_password):
                return False
            
            rsa_key = self._get_rsa_key()
            if not rsa_key:
                return False
            
            encrypted_password = self._encrypt_password(new_password, rsa_key)
            if not encrypted_password:
                return False
            
            url = SteamUrls.CHANGE_PASSWORD
            data = {
                'sessionid': self.steam_client._get_session_id(),
                'wizard_ajax': '1',
                's': self.recovery_params['s'],
                'account': self.recovery_params['account'],
                'password': encrypted_password,
                'rsatimestamp': rsa_key['timestamp']
            }
            
            response = self.steam_client._session.post(url, data=data)
            if response.status_code == 200:
                try:
                    result = response.json()
                    logger.info(f"🔍 Результат установки пароля: {result}")
                    if not result.get('errorMsg'):
                        print_and_log("✅ Новый пароль установлен")
                        return True
                    else:
                        print_and_log(f"❌ Ошибка установки пароля: {result.get('errorMsg')}")
                        return False
                except:
                    print_and_log("✅ Пароль установлен (ответ не в JSON)")
                    return True
            
            return False
            
        except Exception as e:
            print_and_log(f"❌ Ошибка установки пароля: {e}", "ERROR")
            return False
    
    def _get_rsa_key(self) -> Optional[Dict[str, str]]:
        
        try:
            url = SteamUrls.GET_RSA_KEY
            data = {
                'sessionid': self.steam_client._get_session_id(),
                'username': self.username
            }
            
            response = self.steam_client._session.post(url, data=data)
            if response.status_code == 200:
                result = response.json()
                if not result.get('errorMsg'):
                    return {
                        'mod': result.get('publickey_mod', ''),
                        'exp': result.get('publickey_exp', ''),
                        'timestamp': result.get('timestamp', '')
                    }
            
            return None
            
        except Exception as e:
            print_and_log(f"❌ Ошибка получения RSA ключа: {e}", "ERROR")
            return None
    
    def _encrypt_password(self, password: str, rsa_key: Dict[str, str]) -> str:
        
            
        try:
            import rsa
            
            publickey_exp = int(rsa_key['exp'], 16)
            publickey_mod = int(rsa_key['mod'], 16)
            public_key = rsa.PublicKey(n=publickey_mod, e=publickey_exp)
            
            encrypted_password = rsa.encrypt(
                message=password.encode(PasswordConstants.RSA_ENCODING),
                pub_key=public_key,
            )
            encrypted_password64 = base64.b64encode(encrypted_password)
            return str(encrypted_password64, PasswordConstants.RSA_ENCODING_UTF8)
            
        except ImportError:
            print_and_log("❌ Библиотека rsa не установлена", "ERROR")
            print_and_log("💡 Установите: pip install rsa")
            return ""
        except Exception as e:
            print_and_log(f"❌ Ошибка шифрования пароля: {e}", "ERROR")
            return ""
    
    def _check_password_available(self, password: str) -> bool:
        
            
        try:
            url = SteamUrls.CHECK_PASSWORD_AVAILABLE
            data = {
                'sessionid': self.steam_client._get_session_id(),
                'wizard_ajax': '1',
                'password': password
            }
            
            response = self.steam_client._session.post(url, data=data)
            if response.status_code == 200:
                result = response.json()
                logger.info(f"🔍 Результат проверки доступности пароля: {result}")
                if result.get('available'):
                    print_and_log("✅ Пароль доступен")
                    return True
                else:
                    print_and_log("❌ Пароль недоступен")
                    return False
            
            return False
            
        except Exception as e:
            print_and_log(f"❌ Ошибка проверки доступности пароля: {e}", "ERROR")
            return False
    
    def _update_configuration(self, new_password: str) -> bool:
        
            
        try:
            print_and_log("💾 Обновляем конфигурацию...")
            
            cookie_manager = self.account_context.cookie_manager
            
            cookie_manager.password = new_password
            
            print_and_log("✅ Конфигурация обновлена")
            return True
            
        except Exception as e:
            print_and_log(f"❌ Ошибка обновления конфигурации: {e}", "ERROR")
            return False

    def _get_new_password(self) -> Optional[str]:
        
        print_and_log("")
        print_and_log("📝 Введите новый пароль:")
        print_and_log("💡 Требования к паролю:")
        print_and_log("  • Минимум 8 символов")
        print_and_log("  • Должен содержать буквы и цифры")
        print_and_log("  • Рекомендуется использовать специальные символы")
        print_and_log("")
        
        while True:
            new_password: str = input("Новый пароль: ")
            
            if not new_password:
                print_and_log("❌ Пароль не может быть пустым", "ERROR")
                continue
            
            validation: Dict[str, Union[bool, int, List[str]]] = self.validate_password_strength(new_password)
            if not validation['is_valid']:
                print_and_log("❌ Пароль не соответствует требованиям:")
                for issue in validation['issues']:
                    print_and_log(f"  • {issue}")
                continue
            
            confirm_password: str = input("Подтвердите новый пароль: ")
            if new_password != confirm_password:
                print_and_log("❌ Пароли не совпадают", "ERROR")
                continue
            
            score: int = validation['score']
            if score >= 4:
                print_and_log("✅ Отличный пароль!")
            elif score >= 2:
                print_and_log("⚠️  Пароль средней надежности")
            else:
                print_and_log("⚠️  Слабый пароль, но соответствует минимальным требованиям")
            
            return new_password
    
    def _confirm_password_change(self) -> bool:
        
        print_and_log("")
        print_and_log("⚠️  ВНИМАНИЕ:")
        print_and_log("  • Смена пароля может затронуть работу бота")
        print_and_log("  • Убедитесь, что у вас есть доступ к мобильному приложению Steam Guard")
        print_and_log("  • После смены пароля может потребоваться повторная настройка")
        print_and_log("")
        
        while True:
            choice: str = input("Продолжить смену пароля? (y/N): ").lower().strip()
            if choice in ('y', 'yes', 'да', 'д'):
                return True
            elif choice in ('n', 'no', 'нет', 'н', ''):
                print_and_log("Отменено.")
                return False
            else:
                print_and_log("❌ Введите 'y' для продолжения или 'n' для отмены", "ERROR")
    
    def _verify_current_session(self) -> bool:
        
        try:
            print_and_log("🔍 Проверяем активность сессии...")
            
            if hasattr(self.steam_client, 'is_session_alive') and callable(self.steam_client.is_session_alive):
                if self.steam_client.is_session_alive():
                    print_and_log("✅ Сессия активна")
                    return True
                else:
                    print_and_log("❌ Сессия неактивна")
                    return False
            else:
                test_url = SteamUrls.ACCOUNT_TEST
                test_response = self.steam_client._session.get(test_url)
                if test_response.status_code == 200 and "account" in test_response.text.lower():
                    print_and_log("✅ Сессия активна (по тесту)")
                    return True
                else:
                    print_and_log("❌ Сессия неактивна (по тесту)")
                    return False
                    
        except Exception as e:
            print_and_log(f"❌ Ошибка проверки сессии: {e}", "ERROR")
            return False
    
    def _verify_steam_guard_data(self) -> bool:
        
        try:
            print_and_log("🔍 Проверяем данные Steam Guard...")
            
            if not self.steam_client.steam_guard:
                print_and_log("❌ Отсутствуют данные Steam Guard (mafile не загружен)")
                return False
            
            identity_secret = self.steam_client.steam_guard.get('identity_secret', '')
            account_config = self.account_context.config_manager.accounts_settings.get(self.username, {})
            steam_id = account_config.get('steam_id', '')
            
            if not identity_secret:
                print_and_log("❌ Отсутствует identity_secret в mafile")
                return False
            
            if not steam_id:
                print_and_log("❌ Отсутствует steamid в конфигурации")
                return False
            
            print_and_log("✅ Данные Steam Guard найдены")
            return True
                    
        except Exception as e:
            print_and_log(f"❌ Ошибка проверки Steam Guard данных: {e}", "ERROR")
            return False
    
    def validate_password_strength(self, password: str) -> Dict[str, Union[bool, int, List[str]]]:
        
            
        result: Dict[str, Union[bool, int, List[str]]] = {
            'is_valid': True,
            'score': 0,
            'issues': []
        }
        
        if len(password) < PasswordConstants.MIN_PASSWORD_LENGTH:
            result['issues'].append("Пароль должен содержать минимум 8 символов")
            result['is_valid'] = False
        
        if not any(c.isalpha() for c in password):
            result['issues'].append("Пароль должен содержать буквы")
            result['is_valid'] = False
        
        if not any(c.isdigit() for c in password):
            result['issues'].append("Пароль должен содержать цифры")
            result['is_valid'] = False
        
        if len(password) >= PasswordConstants.STRONG_PASSWORD_LENGTH:
            result['score'] += 2
        elif len(password) >= PasswordConstants.MIN_PASSWORD_LENGTH:
            result['score'] += 1
            
        if any(c.isupper() for c in password):
            result['score'] += 1
            
        if any(c.islower() for c in password):
            result['score'] += 1
            
        if any(c in PasswordConstants.SPECIAL_CHARS for c in password):
            result['score'] += 2
            
        return result
