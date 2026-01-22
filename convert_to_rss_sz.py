import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
import datetime
import re

URL = "https://www.spravazeleznic.cz/stavby-zakazky/podklady-pro-zhotovitele/digitalni-technicka-mapa-zeleznice-technicke-standardy/aktuality"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

def parse_cz_date(date_str):
    try:
        d, m, y = map(int, date_str.split('.'))
        return datetime.datetime(y, m, d, 12, 0, tzinfo=datetime.timezone.utc)
    except Exception:
        return datetime.datetime.now(datetime.timezone.utc)

def generate_rss_sz():
    try:
        print(f"Stahuji Správu železnic: {URL}")
        response = requests.get(URL, headers=HEADERS, timeout=20)
        response.encoding = 'utf-8'
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        entries = soup.select(".szdc--aggregator-entry")
        
        fg = FeedGenerator()
        fg.id(URL)
        fg.title('Správa železnic - DTM Aktuality')
        fg.link(href=URL, rel='alternate')
        fg.description('Novinky Správy železnic k DTM standardům.')
        fg.language('cs')

        # Na webu SZ jsou nejnovější nahoře, takže ponecháme pořadí (nebo pro jistotu také reverse, 
        # pokud by čtečka brala první položku v XML jako nejnovější bez ohledu na pubDate)
        # Necháme feedgen, ať je přidává v pořadí z webu.
        
        for entry in entries:
            link_tag = entry.select_one("a.szdc--article")
            if not link_tag: continue
            
            title_tag = link_tag.select_one(".szdc--title")
            title = title_tag.get_text(strip=True) if title_tag else "Bez názvu"
            
            link = link_tag.get('href', URL)
            if link.startswith('/'): link = "https://www.spravazeleznic.cz" + link
            
            date_tag = link_tag.select_one(".szdc--date")
            pub_date = parse_cz_date(date_tag.get_text(strip=True) if date_tag else "")
            
            perex_tag = entry.select_one(".szdc--perex")
            description = perex_tag.get_text(strip=True) if perex_tag else ""

            fe = fg.add_entry()
            fe.id(link or title)
            fe.title(title)
            fe.link(href=link)
            fe.description(description)
            fe.pubDate(pub_date)
            fe.updated(pub_date)

        fg.rss_file('feed_sz.xml', pretty=True)
        print("SZ feed hotov.")

    except Exception as e:
        print(f"Chyba SZ: {e}")

if __name__ == "__main__":
    generate_rss_sz()
