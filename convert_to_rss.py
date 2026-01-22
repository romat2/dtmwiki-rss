import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
import datetime
import os
import re
import json
import hashlib

URL = "https://dtmwiki.cuzk.gov.cz/start"
CACHE_FILE = "news_cache.json"
INITIAL_FALLBACK_DATE = datetime.datetime(2025, 1, 1, 12, 0, tzinfo=datetime.timezone.utc)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

def parse_date(text):
    match = re.search(r'(\d{1,2})\.(\d{1,2})\.(\d{4})', text)
    if match:
        d, m, y = map(int, match.groups())
        try:
            return datetime.datetime(y, m, d, 12, 0, tzinfo=datetime.timezone.utc)
        except ValueError:
            pass
    return None

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

def generate_rss():
    try:
        cache = load_cache()
        new_cache = {}
        is_initial_run = not bool(cache)
        
        print(f"Stahuji DTMwiki: {URL}")
        response = requests.get(URL, headers=HEADERS, timeout=20)
        response.encoding = 'utf-8'
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        aktuality_p = soup.find(lambda tag: tag.name == "p" and "Aktuality:" in tag.text)
        
        if not aktuality_p:
            strong_tag = soup.find("strong", string=re.compile("Aktuality:"))
            if strong_tag:
                aktuality_p = strong_tag.find_parent("p")

        if not aktuality_p:
            print("Sekce Aktuality nenalezena.")
            return

        news_list = aktuality_p.find_next_sibling("ul")
        if not news_list:
            print("Seznam novinek nenalezen.")
            return

        fg = FeedGenerator()
        fg.id(URL)
        fg.title('DTM Wiki - Aktuality')
        fg.author({'name': 'DTM Wiki Monitor'})
        fg.link(href=URL, rel='alternate')
        fg.description('RSS kanál aktualit s nejnovějšími zprávami nahoře.')
        fg.language('cs')

        items = news_list.find_all("li")
        # Otočíme pořadí, aby nejnovější zprávy v XML byly nahoře (pokud jsou na webu přidávány dospod)
        items.reverse()

        for li in items:
            content_div = li.find("div", class_="li")
            text = content_div.get_text(strip=True) if content_div else li.get_text(strip=True)
            if not text:
                continue

            item_id = hashlib.md5(text.encode('utf-8')).hexdigest()
            pub_date = parse_date(text)
            
            if not pub_date:
                if item_id in cache:
                    pub_date = datetime.datetime.fromisoformat(cache[item_id])
                else:
                    pub_date = INITIAL_FALLBACK_DATE if is_initial_run else datetime.datetime.now(datetime.timezone.utc)
            
            new_cache[item_id] = pub_date.isoformat()

            fe = fg.add_entry()
            fe.id(item_id)
            fe.title(text)
            fe.link(href=URL)
            
            html_content = content_div.decode_contents() if content_div else li.decode_contents()
            fe.content(html_content, type='html')
            fe.pubDate(pub_date)
            fe.updated(pub_date)

        save_cache(new_cache)
        fg.rss_file('feed.xml', pretty=True)
        print("DTMwiki feed aktualizován (pořadí otočeno).")

    except Exception as e:
        print(f"Chyba: {e}")

if __name__ == "__main__":
    generate_rss()
