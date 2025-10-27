
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from core.settings_manager import get_application_path

def set_dialog_icon(dialog_window):
    try:
        possible_paths = [
            os.path.join(get_application_path(), "assets", "chatgpt_icon.ico"),
            os.path.join(os.path.dirname(__file__), "..", "..", "assets", "chatgpt_icon.ico"),
            "assets/chatgpt_icon.ico",
            "./assets/chatgpt_icon.ico"
        ]
        
        icon_path = None
        for path in possible_paths:
            if os.path.exists(path):
                icon_path = path
                break
        
        if icon_path:
            dialog_window.iconbitmap(icon_path)
    except:
        pass

from .add_account_dialog import AddAccountDialog
from .edit_account_dialog import EditAccountDialog  
from .mass_password_dialog import MassPasswordChangeDialog
from .account_settings_dialog import AccountSettingsDialog
from .confirmations_dialog import ConfirmationsDialog
from .trade_link_edit_dialog import TradeLinkEditDialog
from .mass_trade_confirm_dialog import MassTradeConfirmDialog