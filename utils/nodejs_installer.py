import os
import sys
import zipfile
import shutil
from pathlib import Path
import subprocess
import tempfile

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    print("⚠️ requests не найден. Автоматическая загрузка Node.js недоступна.")


def get_application_path():
    if getattr(sys, 'frozen', False):
        application_path = os.path.dirname(sys.executable)
    else:
        application_path = os.path.dirname(os.path.abspath(__file__))
        application_path = os.path.dirname(application_path)

    return Path(application_path)


class NodeJSInstaller:

    def __init__(self):
        self.app_dir = get_application_path()
        self.node_dir = self.app_dir / "node"

    def is_nodejs_available(self) -> bool:
        portable_node = self.node_dir / "node.exe"
        if portable_node.exists():
            try:
                result = subprocess.run([str(portable_node), '--version'], 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    print(f"Найден портативный Node.js: {result.stdout.strip()}")
                    return True
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass

        try:
            result = subprocess.run(['node', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                print(f"Найден системный Node.js: {result.stdout.strip()}")
                return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        return False

    def get_nodejs_download_url(self) -> str:
        version = "v20.11.0"
        if os.name == 'nt':
            if sys.maxsize > 2**32:
                return f"https://nodejs.org/dist/{version}/node-{version}-win-x64.zip"
            else:
                return f"https://nodejs.org/dist/{version}/node-{version}-win-x86.zip"
        else:
            return None

    def download_nodejs_portable(self) -> bool:
        if not HAS_REQUESTS:
            print("❌ requests недоступен. Не удается загрузить Node.js автоматически.")
            print("Установите Node.js вручную с https://nodejs.org/")
            return False

        download_url = self.get_nodejs_download_url()
        if not download_url:
            print("Загрузка Node.js для данной ОС не поддерживается")
            return False

        try:
            print("📥 Загрузка портативной версии Node.js...")

            with tempfile.TemporaryDirectory() as temp_dir:
                zip_path = Path(temp_dir) / "nodejs.zip"

                response = requests.get(download_url, stream=True)
                response.raise_for_status()

                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0

                with open(zip_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total_size > 0:
                                progress = (downloaded / total_size) * 100
                                print(f"\r📥 Загрузка: {progress:.1f}%", end='', flush=True)

                print("\n📦 Распаковка...")

                self.node_dir.mkdir(exist_ok=True)

                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    names = zip_ref.namelist()
                    root_folder = names[0].split('/')[0] if names else ""

                    for member in zip_ref.infolist():
                        if member.filename.startswith(root_folder + '/'):
                            member.filename = member.filename[len(root_folder) + 1:]
                            if member.filename:
                                zip_ref.extract(member, self.node_dir)

                print(f"📁 Node.js установлен в: {self.node_dir}")

                node_exe = self.node_dir / "node.exe"
                if node_exe.exists():
                    result = subprocess.run([str(node_exe), '--version'], 
                                          capture_output=True, text=True)
                    if result.returncode == 0:
                        print(f"✅ Node.js успешно установлен: {result.stdout.strip()}")
                        return True
                    else:
                        print("❌ Ошибка: Node.js не работает корректно")
                        return False
                else:
                    print("❌ Ошибка: node.exe не найден после распаковки")
                    return False

        except Exception as e:
            print(f"❌ Ошибка при загрузке Node.js: {e}")
            return False

    def install_npm_packages(self) -> bool:
        try:
            if getattr(sys, 'frozen', False):
                steam_api_dir = Path(sys.executable).parent / "steam_api"
            else:
                steam_api_dir = self.app_dir / "steam_api"

            steam_api_dir.mkdir(exist_ok=True)

            package_json = steam_api_dir / "package.json"
            node_modules = steam_api_dir / "node_modules"

            if node_modules.exists():
                required_packages = ["express", "steamcommunity", "steam-totp", "body-parser"]
                missing = []
                for pkg in required_packages:
                    if not (node_modules / pkg).exists():
                        missing.append(pkg)

                if not missing:
                    print("✅ npm пакеты уже установлены")
                    return True
                else:
                    print(f"⚠️ Отсутствуют пакеты: {missing}, переустанавливаем...")

            print("📦 Установка npm пакетов...")
            print(f"📁 Папка установки: {steam_api_dir}")

            node_exe = self.node_dir / "node.exe"

            if not node_exe.exists():
                print("❌ Node.js не найден для установки npm пакетов")
                return False

            package_content = {
                "name": "steam-confirmations-bridge",
                "version": "1.0.0",
                "description": "Node.js мост для работы с подтверждениями Steam через Python",
                "main": "steam_bridge.js",
                "dependencies": {
                    "body-parser": "^1.20.2",
                    "express": "^4.18.2",
                    "request": "^2.88.2",
                    "steam-totp": "^2.1.1",
                    "steam-tradeoffer-manager": "^2.12.2",
                    "steamcommunity": "^3.49.0"
                }
            }

            import json
            with open(package_json, 'w', encoding='utf-8') as f:
                json.dump(package_content, f, indent=2)

            print("✅ package.json создан")

            npm_dir = self.node_dir / "node_modules" / "npm"
            if not npm_dir.exists():
                print("📦 Установка npm...")
                self._install_npm_globally()

            env = os.environ.copy()
            env['PATH'] = str(self.node_dir) + os.pathsep + env.get('PATH', '')
            env['NODE_PATH'] = str(steam_api_dir / "node_modules")

            success = False

            npm_cmd = self.node_dir / "npm.cmd"
            if npm_cmd.exists():
                print("🔧 Установка через npm.cmd...")
                result = subprocess.run([str(npm_cmd), 'install', '--no-audit', '--no-fund'], 
                                      cwd=steam_api_dir, env=env, 
                                      capture_output=True, text=True, timeout=300)
                if result.returncode == 0:
                    success = True
                else:
                    print(f"⚠️ npm.cmd не сработал: {result.stderr}")

            if not success:
                print("🔧 Установка через npx...")
                result = subprocess.run([str(node_exe), str(self.node_dir / "npx.cmd"), 'npm', 'install'], 
                                      cwd=steam_api_dir, env=env,
                                      capture_output=True, text=True, timeout=300)
                if result.returncode == 0:
                    success = True
                else:
                    print(f"⚠️ npx не сработал: {result.stderr}")

            if not success:
                print("🔧 Установка пакетов по отдельности...")
                success = self._install_packages_individually(steam_api_dir, node_exe, env)

            if success:
                print("✅ npm пакеты успешно установлены")
                
                self._copy_js_files_to_working_dir(steam_api_dir)
                
                return True
            else:
                print("❌ Не удалось установить npm пакеты")
                return False

        except subprocess.TimeoutExpired:
            print("❌ Таймаут при установке npm пакетов")
            return False
        except Exception as e:
            print(f"❌ Ошибка при установке npm пакетов: {e}")
            return False

    def _install_npm_globally(self):
        try:
            print("📦 Проверка npm...")
            node_exe = self.node_dir / "node.exe"
            
            result = subprocess.run([str(node_exe), '-e', 'console.log(process.version)'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✅ Node.js работает: {result.stdout.strip()}")
            
        except Exception as e:
            print(f"⚠️ Ошибка проверки npm: {e}")
    
    def _copy_js_files_to_working_dir(self, steam_api_dir):
        try:
            if getattr(sys, 'frozen', False):
                import tempfile
                temp_steam_api = Path(sys._MEIPASS) / "steam_api"
                
                if temp_steam_api.exists():
                    for js_file in temp_steam_api.glob("*.js"):
                        target = steam_api_dir / js_file.name
                        if not target.exists():
                            import shutil
                            shutil.copy2(js_file, target)
                            print(f"📄 Скопирован: {js_file.name}")
                            
        except Exception as e:
            print(f"⚠️ Ошибка копирования JS файлов: {e}")
    
    def _install_packages_individually(self, steam_api_dir, node_exe, env):
        packages = [
            "express@^4.18.2",
            "body-parser@^1.20.2", 
            "steam-totp@^2.1.1",
            "steamcommunity@^3.49.0",
            "steam-tradeoffer-manager@^2.12.2",
            "request@^2.88.2"
        ]
        
        success_count = 0
        
        simple_package = {
            "name": "steam-bridge",
            "version": "1.0.0",
            "dependencies": {}
        }
        
        import json
        package_json_path = steam_api_dir / "package.json"
        with open(package_json_path, 'w', encoding='utf-8') as f:
            json.dump(simple_package, f, indent=2)
        
        for package in packages:
            try:
                print(f"📦 Установка {package}...")
                
                install_script = f"""
                const {{ execSync }} = require('child_process');
                try {{
                    execSync('npm install {package}', {{stdio: 'inherit', cwd: '{steam_api_dir}'}});
                    console.log('Успешно установлен {package}');
                }} catch (e) {{
                    console.error('Ошибка установки {package}:', e.message);
                    process.exit(1);
                }}
                """
                
                script_path = steam_api_dir / f"install_{package.split('@')[0].replace('-', '_')}.js"
                with open(script_path, 'w', encoding='utf-8') as f:
                    f.write(install_script)
                
                result = subprocess.run(
                    [str(node_exe), str(script_path)],
                    cwd=steam_api_dir,
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=180
                )
                
                script_path.unlink()
                
                if result.returncode == 0:
                    success_count += 1
                    print(f"✅ {package} установлен успешно")
                else:
                    print(f"❌ Ошибка установки {package}: {result.stderr}")
                    
            except Exception as e:
                print(f"❌ Исключение при установке {package}: {e}")
                
        return success_count






