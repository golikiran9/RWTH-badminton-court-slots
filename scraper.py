import os
import requests
from bs4 import BeautifulSoup

# ==========================================
# CONFIGURATION: Update target schedule here
# ==========================================
CONFIG = {
    # Match the column header language on the RWTH site:
    # Options: 'MontagMonday', 'DienstagTuesday', 'MittwochWednesday', 
    #          'DonnerstagThursday', 'FreitagFriday', 'SamstagSaturday', 'SonntagSunday'
    #'TARGET_WEEKDAY': 'MittwochWednesday',
    'TARGET_WEEKDAY': 'MontagMonday',
    
    # Target time slot format (e.g., '18:00', '19:30', '09:00')
    #'TARGET_TIME': '18:00',
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
    weekday = CONFIG['TARGET_WEEKDAY']
    time_slot = CONFIG['TARGET_TIME']
    
    if CONFIG['DEBUG_NOTIFY']:
        send_telegram_message(f"🔄 *Scraper Executed*\nChecking slots for {weekday} at {time_slot}...")

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
            
        columns = [col.text.strip() for col in first_row.find_all(['th', 'td'])]
        
        # Locate the specified target weekday column
        if weekday in columns:
            day_idx = columns.index(weekday)
            
            for row in table.find_all('tr')[1:]:
                cells = row.find_all(['th', 'td'])
                if not cells:
                    continue
                
                row_time = cells[0].text.strip()
                
                # Match the target time slot
                if time_slot in row_time and len(cells) > day_idx:
                    slot_status = cells[day_idx].text.strip()
                    
                    # Any value other than "keine Buchung" or empty string indicates an available slot
                    if 'keine Buchung' not in slot_status and slot_status != '':
                        available_courts.append(f"• {court_name} ({slot_status})")

    if available_courts:
        courts_list = "\n".join(available_courts)
        day_display = weekday.replace("Wednesday", "").replace("Monday", "").replace("Tuesday", "").replace("Thursday", "").replace("Friday", "").replace("Saturday", "").replace("Sunday", "")
        
        message = (
            f"🏸 *Badminton Court Alert!*\n\n"
            f"Slots available for **{day_display} at {time_slot}**:\n"
            f"{courts_list}\n\n"
            f"Book immediately here:\n{URL}"
        )
        send_telegram_message(message)
        print(f"Slots found for {weekday} at {time_slot}! Telegram notification sent.")
    else:
        print(f"No slots available for {weekday} at {time_slot} across any court.")

if __name__ == "__main__":
    main()
