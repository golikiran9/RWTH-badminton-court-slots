import requests
from bs4 import BeautifulSoup
import os

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
    found_slots = False
    
    # Search through all booking tables on the page
    for table in soup.find_all('table'):
        first_row = table.find('tr')
        if not first_row:
            continue
            
        columns = [col.text.strip() for col in first_row.find_all(['th', 'td'])]
        
        # Check if this table has a Wednesday column
        if 'MittwochWednesday' in columns:
            wed_idx = columns.index('MittwochWednesday')
            
            # Check all time slots in this table
            for row in table.find_all('tr')[1:]:
                cells = row.find_all(['th', 'td'])
                if not cells:
                    continue
                
                time_text = cells[0].text.strip()
                
                # Look specifically for the 18:00 time block
                if '18:00' in time_text and len(cells) > wed_idx:
                    wed_status = cells[wed_idx].text.strip()
                    
                    # "keine Buchung" means the slot is unavailable or closed. 
                    # If the text is anything else (like a date or "Buchen"), a slot is open!
                    if 'keine Buchung' not in wed_status and wed_status != '':
                        found_slots = True

    if found_slots:
        message = f"🏸 *Badminton Court Alert!*\n\nA slot for **Wednesday at 18:00** is currently open!\n\nBook it immediately here:\n{URL}"
        send_telegram_message(message)
        print("Slot found, Telegram notification sent!")
    else:
        print("No slots available for Wednesday at 18:00 right now.")

if __name__ == "__main__":
    main()