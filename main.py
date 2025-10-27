import pyautogui
import sys
import os
from pathlib import Path

try:
    from utils import runtime_validator
except ImportError:
    pass

def check_and_setup_nodejs():
    try:
        from utils.nodejs_installer import NodeJSInstaller
        
        installer = NodeJSInstaller()
        
        if not installer.is_nodejs_available():
            print("📥 Node.js не найден. Установка портативной версии...")
            print("Это может занять несколько минут при первом запуске...")
            
            if installer.setup_nodejs():
                print("✅ Node.js успешно установлен")
                
                print("📦 Установка npm пакетов для Steam API...")
                if installer.install_npm_packages():
                    print("✅ npm пакеты установлены")
                else:
                    print("⚠️ Не удалось установить npm пакеты")
                
                return True
            else:
                print("❌ Не удалось установить Node.js автоматически")
                print("🔧 Установите Node.js вручную с https://nodejs.org/")
                return False
        else:
            print("✅ Node.js уже доступен")
            return True
            
    except ImportError:
        print("⚠️ Модуль установки Node.js недоступен")
        return False
    except Exception as e:
        print(f"⚠️ Ошибка при проверке Node.js: {e}")
        return False

from gui import SteamAutoLoginGUI


if __name__ == "__main__":
    pyautogui.FAILSAFE = True
    
    print("Проверка системных требований...")
    nodejs_ok = check_and_setup_nodejs()
    
    if not nodejs_ok:
        print("⚠️ Node.js недоступен. Некоторые функции (инвентарь, трейды) могут не работать.")
        print("Для полной функциональности установите Node.js с https://nodejs.org/")
    
    app = SteamAutoLoginGUI()
    app.run()
