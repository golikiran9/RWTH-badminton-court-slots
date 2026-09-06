import os
import re
import requests
from bs4 import BeautifulSoup

# ==========================================
# CONFIGURATION: Read target schedule from env
# ==========================================
CONFIG = {
    # Simple day name: 'Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag', 'Sonntag'
    'TARGET_WEEKDAY': os.environ.get('TARGET_WEEKDAY', 'Mittwoch'),
    
    # Target time slot format (e.g., '18:00', '19:30', '07:30')
    'TARGET_TIME': os.environ.get('TARGET_TIME', '18:00'),
    
    # Set to True if you want a heartbeat ping every time GitHub Actions runs
    'DEBUG_NOTIFY': False 
}

TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')
EVENT_NAME = os.environ.get('GITHUB_EVENT_NAME', '')  # Set by GitHub Actions workflow
URL = "https://buchung.hsz.rwth-aachen.de/angebote/Sommersemester/_Badmintoncourt_Einzelterminbuchung.html"

def send_telegram_message(message):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("Telegram token or Chat ID missing. Skipping message dispatch.")
        return
    
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    requests.post(url, data=payload)

def get_clean_court_name(table_elem, index):
    """Extracts exact court name (e.g. 'Badmintoncourt 1') avoiding duplicated generic titles."""
    prev_node = table_elem.find_previous(['h2', 'h3', 'div', 'b'])
    while prev_node:
        text = prev_node.text.strip()
        match = re.search(r'Badmintoncourt\s*\d+.*', text, re.IGNORECASE)
        if match:
            return match.group(0)
        prev_node = prev_node.find_previous(['h2', 'h3', 'div', 'b'])
        
    return f"Badmintoncourt {index}"

def main():
    target_day = CONFIG['TARGET_WEEKDAY'].strip().lower()
    time_slot = CONFIG['TARGET_TIME'].strip()
    
    if CONFIG['DEBUG_NOTIFY']:
        send_telegram_message(f"🔄 *Scraper Executed*\nChecking slots for {CONFIG['TARGET_WEEKDAY']} at {time_slot}...")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    
    try:
        response = requests.get(URL, headers=headers)
        response.raise_for_status()
    except Exception as e:
        error_msg = f"⚠️ Failed to fetch RWTH website: {e}"
        print(error_msg)
        if EVENT_NAME == 'workflow_dispatch':
            send_telegram_message(error_msg)
        return
        
    soup = BeautifulSoup(response.text, 'html.parser')
    available_now = []
    opening_soon = []
    
    tables = soup.find_all('table')
    for idx, table in enumerate(tables, start=1):
        first_row = table.find('tr')
        if not first_row:
            continue
            
        columns = [col.text.strip().lower() for col in first_row.find_all(['th', 'td'])]
        
        # Locate target weekday column
        day_idx = -1
        for col_i, col in enumerate(columns):
            if target_day in col:
                day_idx = col_i
                break
                
        if day_idx != -1:
            court_name = get_clean_court_name(table, idx)

            for row in table.find_all('tr')[1:]:
                cells = row.find_all(['th', 'td'])
                if not cells:
                    continue
                
                row_time = cells[0].text.strip()
                
                if time_slot in row_time and len(cells) > day_idx:
                    target_cell = cells[day_idx]
                    cell_text = target_cell.text.strip()
                    
                    # Check for active 'buchen' inputs
                    inputs = target_cell.find_all('input')
                    input_values = [inp.get('value', '').lower() for inp in inputs if inp.get('value')]
                    has_buchen_btn = any('buchen' in val for val in input_values) or 'buchen' in cell_text.lower()
                    
                    # 1. Slot is available right now
                    if has_buchen_btn:
                        available_now.append(f"• **{court_name}**: Available Now! (buchen)")
                    
                    # 2. Slot opens in advance (e.g., "ab 09.09., 18:00")
                    elif 'ab ' in cell_text.lower() and 'keine buchung' not in cell_text.lower():
                        opening_soon.append(f"• **{court_name}**: Opens at `{cell_text}`")

    # --- Notification Logic ---
    if available_now or opening_soon:
        msg_parts = [f"🏸 *Badminton Court Alert!*\n\nTarget: **{CONFIG['TARGET_WEEKDAY']} at {time_slot}**\n"]
        
        if available_now:
            msg_parts.append("*Ready to Book Now:*\n" + "\n".join(available_now) + "\n")
            
        if opening_soon:
            msg_parts.append("*Upcoming Booking Releases (24h Window):*\n" + "\n".join(opening_soon) + "\n")
            
        msg_parts.append(f"Book immediately here:\n{URL}")
        
        send_telegram_message("\n".join(msg_parts))
        print("Alert sent to Telegram!")

    # If no slots found AND execution was manually triggered via /check
    elif EVENT_NAME == 'workflow_dispatch':
        no_slots_msg = f"❌ No slots available for **{CONFIG['TARGET_WEEKDAY']} at {time_slot}**."
        send_telegram_message(no_slots_msg)
        print(f"No slots available. Sent manual trigger response to Telegram.")
        
    else:
        print(f"No active or upcoming slots found for {CONFIG['TARGET_WEEKDAY']} at {time_slot}.")

if __name__ == "__main__":
    main()
