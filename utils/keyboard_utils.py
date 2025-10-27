import time
import pyautogui
import pyperclip
import tkinter as tk
from tkinter import messagebox
import locale
import ctypes
from ctypes import wintypes


def send_paste_command():
    try:
        VK_CONTROL = 0x11
        VK_V = ord('V')
        
        KEYEVENTF_KEYUP = 0x0002
        
        user32 = ctypes.windll.user32
        
        user32.keybd_event(VK_CONTROL, 0, 0, 0)
        time.sleep(0.01)
        
        user32.keybd_event(VK_V, 0, 0, 0)
        time.sleep(0.01)
        
        user32.keybd_event(VK_V, 0, KEYEVENTF_KEYUP, 0)
        time.sleep(0.01)
        
        user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)
        time.sleep(0.1)
        
        return True
    except Exception as e:
        print(f"❌ Ошибка отправки команды вставки: {e}")
        return False


def safe_clipboard_paste(text):
    try:
        old_clipboard = ""
        try:
            old_clipboard = pyperclip.paste()
        except:
            pass
        
        try:
            pyperclip.copy(text)
            time.sleep(0.1)
        except Exception as e:
            print(f"⚠️ Ошибка установки текста в буфер: {e}")
            return False
        
        try:
            check_text = pyperclip.paste()
            if check_text != text:
                print(f"⚠️ Предупреждение: текст в буфере не совпадает")
        except:
            pass
        
        success = send_paste_command()
        
        if success:
            time.sleep(0.2)
            
            try:
                if old_clipboard:
                    pyperclip.copy(old_clipboard)
                    time.sleep(0.05)
            except Exception as e:
                print(f"⚠️ Не удалось восстановить буфер: {e}")
        
        return success
        
    except Exception as e:
        print(f"❌ Ошибка в safe_clipboard_paste: {e}")
        return False


def safe_input_text(text):
    try:
        print(f"🔤 Вводим текст: '{text[:20]}{'...' if len(text) > 20 else ''}' ({len(text)} символов)")
        
        success = safe_clipboard_paste(text)
        
        if success:
            print(f"✅ Текст успешно введен")
            return True
        else:
            print(f"❌ Ошибка ввода, пробуем fallback...")
            return safe_input_fallback(text)
            
    except Exception as e:
        print(f"❌ Ошибка ввода текста: {e}")
        return safe_input_fallback(text)


def safe_input_fallback(text):
    try:
        print("🔄 Fallback: используем pyperclip + pyautogui...")
        
        old_clipboard = ""
        try:
            old_clipboard = pyperclip.paste()
        except:
            pass
        
        pyperclip.copy(text)
        time.sleep(0.1)
        
        pyautogui.hotkey('ctrl', 'v')
        time.sleep(0.2)
        
        try:
            if old_clipboard:
                pyperclip.copy(old_clipboard)
        except:
            pass
        
        print(f"✅ Fallback: текст введен")
        return True
        
    except Exception as e:
        print(f"❌ Критическая ошибка fallback: {e}")
        
        try:
            if all(ord(char) < 128 for char in text):
                print("🔄 Последняя попытка: прямой ввод...")
                pyautogui.write(text, interval=0.05)
                print(f"✅ Прямой ввод выполнен")
                return True
            else:
                print(f"❌ Прямой ввод невозможен: содержит non-ASCII символы")
                return False
        except Exception as e2:
            print(f"❌ Полный провал ввода: {e2}")
            return False


def get_keyboard_layout():
    try:
        user32 = ctypes.windll.user32
        
        hwnd = user32.GetForegroundWindow()
        thread_id = user32.GetWindowThreadProcessId(hwnd, 0)
        layout_id = user32.GetKeyboardLayout(thread_id)
        
        lang_id = layout_id & 0xFFFF
        
        if lang_id == 1049:
            return "RU"
        elif lang_id == 1033:
            return "EN"
        else:
            return f"OTHER({lang_id})"
            
    except Exception as e:
        print(f"⚠️ Не удалось определить раскладку: {e}")
        return "UNKNOWN"


def switch_to_english_layout():
    try:
        ENGLISH_LAYOUT = 0x04090409
        user32 = ctypes.windll.user32
        
        hwnd = user32.GetForegroundWindow()
        
        user32.PostMessageW(hwnd, 0x0050, 0, ENGLISH_LAYOUT)
        time.sleep(0.1)
        
        return True
    except Exception as e:
        print(f"⚠️ Не удалось переключить раскладку: {e}")
        return False


def safe_input_with_layout_check(text):
    try:
        current_layout = get_keyboard_layout()
        print(f"🔍 Текущая раскладка: {current_layout}")
        
        has_cyrillic = any(ord(char) >= 1024 and ord(char) <= 1279 for char in text)
        has_latin = any(ord(char) >= 65 and ord(char) <= 122 for char in text)
        
        if has_latin and not has_cyrillic and current_layout == "RU":
            print("🔄 Обнаружен латинский текст при русской раскладке")
        
        return safe_input_text(text)
        
    except Exception as e:
        print(f"❌ Ошибка при проверке раскладки: {e}")
        return safe_input_text(text)


def safe_type_login(text):
    print(f"🔑 Вводим логин...")
    return safe_input_with_layout_check(text)


def safe_type_password(text):
    print(f"🔒 Вводим пароль...")
    return safe_input_with_layout_check(text)


def safe_type_guard_code(text):
    print(f"🛡️ Вводим 2FA код: {text}")
    return safe_input_with_layout_check(text)


def initialize_keyboard():
    try:
        print("🎹 Инициализация клавиатуры...")
        
        layout = get_keyboard_layout()
        print(f"🔍 Обнаружена раскладка: {layout}")
        
        try:
            system_encoding = locale.getpreferredencoding()
            print(f"🔤 Системная кодировка: {system_encoding}")
        except:
            print("🔤 Не удалось определить системную кодировку")
        
        try:
            test_cyrillic = "тест"
            test_cyrillic.encode('utf-8')
            print("✅ Поддержка кириллицы: OK")
        except:
            print("❌ Проблемы с поддержкой кириллицы")
        
        try:
            original_clipboard = ""
            try:
                original_clipboard = pyperclip.paste()
            except:
                pass
            
            pyperclip.copy("test")
            test_result = pyperclip.paste()
            
            try:
                if original_clipboard:
                    pyperclip.copy(original_clipboard)
                else:
                    pyperclip.copy("")
            except:
                pass
                
            print("✅ pyperclip: OK")
        except Exception as e:
            print(f"❌ Проблемы с pyperclip: {e}")
        
        print("✅ Клавиатура инициализирована")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка инициализации клавиатуры: {e}")
        return False