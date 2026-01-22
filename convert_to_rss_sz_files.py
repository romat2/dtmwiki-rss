import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
import datetime
import os
import json
import hashlib

URL = "https://www.spravazeleznic.cz/stavby-zakazky/podklady-pro-zhotovitele/digitalne-technicka-mapa-zeleznice-technicke-standardy/datovy-model-dtmz"
CACHE_FILE = "files_cache.json"
# Fallback date for initial run to keep order but not flood as "new"
INITIAL_FALLBACK_DATE = datetime.datetime(2025, 1, 1, 12, 0, tzinfo=datetime.timezone.utc)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_cache(cache):
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

def generate_rss_sz_files():
    try:
        cache = load_cache()
        new_cache = {}
        is_initial_run = not bool(cache)
        
        print(f"Stahuji soubory SZ DTMZ: {URL}")
        response = requests.get(URL, headers=HEADERS, timeout=20)
        response.encoding = 'utf-8'
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        table = soup.select_one("table.szdc--attachments")
        if not table:
            print("CHYBA: Tabulka s přílohami nebyla nalezena.")
            return
            
        rows = table.select("tbody tr")
        print(f"Nalezeno {len(rows)} souborů.")

        # Otočíme pořadí řádků, aby nejnovější byl ve feedu přidán jako poslední
        rows.reverse()

        fg = FeedGenerator()
        fg.id(URL)
        fg.title('Správa železnic - DTMZ Datový model - Soubory')
        fg.link(href=URL, rel='alternate')
        fg.description('Nové soubory ke stažení z webu Správy železnic k datovému modelu DTMZ.')
        fg.language('cs')

        for row in rows:
            filename_cell = row.select_one("td.szdc--filename")
            link_cell = row.select_one("td.szdc--filetype a")
            
            if not filename_cell or not link_cell:
                continue
                
            title = filename_cell.get_text(strip=True)
            link = link_cell.get('href', "")
            if link.startswith('/'):
                link = "https://www.spravazeleznic.cz" + link
            
            item_id = hashlib.md5((link + title).encode('utf-8')).hexdigest()
            
            if item_id in cache:
                pub_date = datetime.datetime.fromisoformat(cache[item_id])
            else:
                if is_initial_run:
                    # Při prvním běhu dáme staré datum, ale každému jiné, aby se zachovalo pořadí
                    # (nejnovější na webu - nyní na konci seznamu rows - dostane nejvyšší čas)
                    idx = rows.index(row)
                    pub_date = INITIAL_FALLBACK_DATE + datetime.timedelta(minutes=idx)
                else:
                    pub_date = datetime.datetime.now(datetime.timezone.utc)
            
            new_cache[item_id] = pub_date.isoformat()

            fe = fg.add_entry()
            fe.id(link or item_id)
            fe.title(title)
            fe.link(href=link)
            fe.pubDate(pub_date)
            fe.updated(pub_date)

        save_cache(new_cache)
        fg.rss_file('feed_sz_files.xml', pretty=True)
        print(f"Feed souborů SZ aktualizován (pořadí otočeno).")

    except Exception as e:
        print(f"Chyba SZ soubory: {e}")

if __name__ == "__main__":
    generate_rss_sz_files()
