import os
import requests
from bs4 import BeautifulSoup

# ==========================================
# CONFIGURATION: Update target schedule here
# ==========================================
CONFIG = {
    # Simple day name: 'Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag', 'Sonntag'
    'TARGET_WEEKDAY': 'Montag',
    
    # Target time slot format (e.g., '18:00', '19:30', '07:30')
    'TARGET_TIME': '07:30',
    
    # Set to True if you want a heartbeat ping every time GitHub Actions runs
    'DEBUG_NOTIFY': False 
}

TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')
URL = "https://buchung.hsz.rwth-aachen.de/angebote/Sommersemester/_Badmintoncourt_Einzelterminbuchung.html"

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    requests.post(url, data=payload)

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
        print(f"Failed to fetch website: {e}")
        return
        
    soup = BeautifulSoup(response.text, 'html.parser')
    available_courts = []
    
    for bs_form in soup.find_all('form', class_='bs_form_angebot'):
        heading = bs_form.find(['h2', 'h3', 'div', 'span'], class_='bs_head')
        court_name = heading.text.strip() if heading else "Badmintoncourt"
        
        table = bs_form.find('table')
        if not table:
            continue
            
        first_row = table.find('tr')
        if not first_row:
            continue
            
        columns = [col.text.strip().lower() for col in first_row.find_all(['th', 'td'])]
        
        # Locate column matching the target weekday (e.g., 'montag')
        day_idx = -1
        for idx, col in enumerate(columns):
            if target_day in col:
                day_idx = idx
                break
                
        if day_idx != -1:
            for row in table.find_all('tr')[1:]:
                cells = row.find_all(['th', 'td'])
                if not cells:
                    continue
                
                row_time = cells[0].text.strip()
                
                if time_slot in row_time and len(cells) > day_idx:
                    target_cell = cells[day_idx]
                    
                    # Check for a 'buchen' input button inside the cell
                    buchen_input = target_cell.find('input', getattr={'value': lambda v: v and 'buchen' in v.lower()}) if hasattr(target_cell, 'find') else None
                    if not buchen_input:
                        buchen_input = target_cell.find('input', value=lambda v: v and 'buchen' in v.lower())
                    
                    cell_text = target_cell.text.strip()
                    
                    # Slot is available if it contains a 'buchen' button OR text other than 'keine Buchung'
                    is_buchen_button = buchen_input is not None or 'buchen' in cell_text.lower()
                    is_open_status = 'keine buchung' not in cell_text.lower() and cell_text != ''
                    
                    if is_buchen_button or is_open_status:
                        status_display = "buchen" if is_buchen_button else cell_text
                        available_courts.append(f"• {court_name} ({status_display})")

    if available_courts:
        courts_list = "\n".join(available_courts)
        message = (
            f"🏸 *Badminton Court Alert!*\n\n"
            f"Slots available for **{CONFIG['TARGET_WEEKDAY']} at {time_slot}**:\n"
            f"{courts_list}\n\n"
            f"Book immediately here:\n{URL}"
        )
        send_telegram_message(message)
        print(f"Slots found for {CONFIG['TARGET_WEEKDAY']} at {time_slot}! Telegram notification sent.")
    else:
        print(f"No slots available for {CONFIG['TARGET_WEEKDAY']} at {time_slot} across any court.")

if __name__ == "__main__":
    main()
