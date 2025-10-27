
import sys
import argparse

def main():
    parser = argparse.ArgumentParser(
        description="SteamPy - Инструменты для работы с Steam API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Доступные модули:
  session-manager    Управление Steam сессиями
  
Примеры:
  python -m steampy session-manager --username myuser --get-2fa
  python -m steampy session-manager --username myuser --monitor
        """)
    
    parser.add_argument('module', nargs='?', help='Модуль для запуска')
    parser.add_argument('--username', help='Имя пользователя Steam')
    
    args = parser.parse_args()
    
    if args.module == 'session-manager':
        from .session_manager import SessionManager
        manager = SessionManager(args.username or "default")
        print("Session manager initialized")
    else:
        parser.print_help()

if __name__ == '__main__':
    main()