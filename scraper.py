import os
import requests
from bs4 import BeautifulSoup

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
    resp = requests.post(url, data=payload)
    print(f"Telegram API response status: {resp.status_code}")

def main():
    # Send a confirmation message that the script ran
    send_telegram_message("🔄 *Badminton Scraper Executed*\nChecking for open slots...")

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
    
    # Target time blocks present on the RWTH schedule: '09:00' or '10:30'
    TARGET_TIME = '09:00'
    
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
        
        if 'MittwochWednesday' in columns:
            wed_idx = columns.index('MittwochWednesday')
            
            for row in table.find_all('tr')[1:]:
                cells = row.find_all(['th', 'td'])
                if not cells:
                    continue
                
                time_text = cells[0].text.strip()
                
                if TARGET_TIME in time_text and len(cells) > wed_idx:
                    wed_status = cells[wed_idx].text.strip()
                    
                    if 'keine Buchung' not in wed_status and wed_status != '':
                        available_courts.append(f"• {court_name} ({wed_status})")

    if available_courts:
        courts_list = "\n".join(available_courts)
        message = (
            f"🏸 *Badminton Court Alert!*\n\n"
            f"Slots available for **Wednesday at {TARGET_TIME}**:\n"
            f"{courts_list}\n\n"
            f"Book immediately here:\n{URL}"
        )
        send_telegram_message(message)
        print("Slots found! Notification sent.")
    else:
        print(f"No slots available for Wednesday at {TARGET_TIME}.")

if __name__ == "__main__":
    main()
