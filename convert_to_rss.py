import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
import datetime
import os
import re

URL = "https://dtmwiki.cuzk.gov.cz/start"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

def parse_date(text):
    """
    Pokusí se extrahovat datum ve formátu D.M.RRRR ze začátku textu.
    """
    match = re.search(r'(\d{1,2})\.(\d{1,2})\.(\d{4})', text)
    if match:
        d, m, y = map(int, match.groups())
        try:
            # Vytvoříme datum v poledne UTC pro konzistenci
            return datetime.datetime(y, m, d, 12, 0, tzinfo=datetime.timezone.utc)
        except ValueError:
            pass
    return datetime.datetime.now(datetime.timezone.utc)

def generate_rss():
    print(f"Stahuji stránku: {URL}")
    response = requests.get(URL, headers=HEADERS)
    response.encoding = 'utf-8'
    response.raise_for_status()
    
    soup = BeautifulSoup(response.text, "html.parser")

    # 1. Najdeme nadpis Aktuality (odstavec obsahující "Aktuality:")
    aktuality_p = soup.find(lambda tag: tag.name == "p" and "Aktuality:" in tag.text)
    
    if not aktuality_p:
        # Zkusíme najít alternativně přes strong
        strong_tag = soup.find("strong", string=re.compile("Aktuality:"))
        if strong_tag:
            aktuality_p = strong_tag.find_parent("p")

    if not aktuality_p:
        print("CHYBA: Sekce 'Aktuality' nebyla na stránce nalezena.")
        return

    # 2. Seznam novinek je v hned následujícím <ul> (nebo dalším sourozenci)
    news_list = aktuality_p.find_next_sibling("ul")
    
    if not news_list:
        print("CHYBA: Seznam novinek (ul) nenalezen hned za odstavcem.")
        return

    # 3. Inicializace RSS feedu
    fg = FeedGenerator()
    fg.id(URL)
    fg.title('DTM Wiki - Aktuality')
    fg.author({'name': 'DTM Wiki Monitor'})
    fg.link(href=URL, rel='alternate')
    fg.description('Automaticky generovaný RSS kanál z odstavce Aktuality na DTM Wiki.')
    fg.language('cs')

    # 4. Extrakce položek (li)
    items = news_list.find_all("li")
    print(f"Nalezeno {len(items)} novinek.")

    for li in items:
        # DokuWiki často balí text do div.li
        content_div = li.find("div", class_="li")
        text = content_div.get_text(strip=True) if content_div else li.get_text(strip=True)
        
        if not text:
            continue

        fe = fg.add_entry()
        # Použijeme hash nebo text jako ID, aby se položky v RSS neopakovaly jako nové
        fe.id(text) 
        fe.title(text)
        fe.link(href=URL)
        
        # HTML obsah zachováme pro čtečky
        html_content = content_div.decode_contents() if content_div else li.decode_contents()
        fe.content(html_content, type='html')
        
        # Nastavení data
        pub_date = parse_date(text)
        fe.pubDate(pub_date)
        # updated by mělo být také nastaveno
        fe.updated(pub_date)

    # 5. Uložení feed.xml
    fg.rss_file('feed.xml', pretty=True)
    print("Soubor feed.xml byl úspěšně vytvořen.")

if __name__ == "__main__":
    generate_rss()
