
from bs4 import BeautifulSoup
from typing import Dict, Any
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


def determine_confirmation_type_from_json(conf_data: dict) -> str:
    
        
    try:
        confirmation_type = conf_data.get('type')
        
        if confirmation_type == 2:
            return 'trade_offer'
        elif confirmation_type == 3:
            return 'market_listing'
        elif confirmation_type == 12:
            return 'market_purchase'
        else:
            return 'unknown'
            
    except Exception as e:
        logger.warning(f"⚠️ Ошибка определения типа подтверждения из JSON: {e}")
        return 'unknown'


def extract_confirmation_info(conf_data: dict, confirmation_type: str) -> Dict[str, Any]:
    
        
    info = {}
    
    try:
        if confirmation_type == 'market_listing':
            item_name = conf_data.get('summary', ['Unknown Item'])[0] if conf_data.get('summary') else 'Unknown Item'
            price = conf_data.get('headline', 'Unknown Price')
            
            info['item_name'] = item_name
            info['price'] = price
            info['description'] = f"Market Listing: {item_name} → {price}"
            
        elif confirmation_type == 'market_purchase':
            info['description'] = "Market Purchase"
            
        elif confirmation_type == 'trade_offer':
            partner_name = conf_data.get('headline', 'Unknown Partner')
            summary_items = conf_data.get('summary', [])
            
            description_parts = [f"Trade Offer to {partner_name}"]
            for item in summary_items:
                description_parts.append(f"  • {item}")
            
            info['partner_name'] = partner_name
            info['summary_items'] = summary_items
            info['description'] = '\n'.join(description_parts)
            
        else:
            info['description'] = f"Unknown Confirmation Type ({confirmation_type})"
            
    except Exception as e:
        logger.warning(f"⚠️ Ошибка извлечения информации из подтверждения: {e}")
        info['description'] = "Error extracting details"
    
    return info 


if __name__ == "__main__":
    with open("debug_confirmations_page.txt", "r", encoding="utf-8") as f:
        details_html = f.read()
