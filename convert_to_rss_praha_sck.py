import requests
from feedgen.feed import FeedGenerator
import datetime
import json

URL_API = "https://portal.dtm-praha-sck.cz/backend/select/aktuality"
URL_PORTAL = "https://portal.dtm-praha-sck.cz/archiv-zprav"

def parse_date(date_str):
    try:
        # Format: 2024-04-14T00:00:00.000Z
        return datetime.datetime.fromisoformat(date_str.replace('Z', '+00:00'))
    except Exception:
        return datetime.datetime.now(datetime.timezone.utc)

def generate_rss_portal():
    try:
        print(f"Stahuji aktuality z Portálu DTM: {URL_API}")
        response = requests.get(URL_API, timeout=20)
        response.raise_for_status()
        data = response.json()
        
        # Seřadíme zprávy podle ID nebo data, abychom zajistili konzistenci
        # Na webu jsou asi seřazeny podle data (OD) sestupně.
        # Feedgen přidává položky v pořadí, v jakém je voláme.
        # RSS čtečky obvykle berou poslední přidané jako nejnovější, 
        # ale technicky záleží na pubDate.
        # Původní skripty dělají reverse(), aby nejnovější byly "poslední" v seznamu 
        # (protože feedgen.add_entry() přidává na konec XML a některé čtečky to tak mají radši).
        
        # Seřadíme podle data OD vzestupně, aby nejnovější byly na konci XML
        data.sort(key=lambda x: x.get('OD', ''))

        fg = FeedGenerator()
        fg.id(URL_PORTAL)
        fg.title('Portál DTM Praha a SČK - Aktuality')
        fg.link(href=URL_PORTAL, rel='alternate')
        fg.description('Novinky z Portálu DTM pro Prahu a Středočeský kraj.')
        fg.language('cs')

        for item in data:
            title = item.get('TEXT', 'Bez názvu')
            item_id = item.get('ID')
            pub_date = parse_date(item.get('OD'))
            
            link = item.get('ODKAZ')
            if not link:
                link = f"{URL_PORTAL}/{item_id}"
            
            description = item.get('DETAIL', '')

            fe = fg.add_entry()
            fe.id(str(item_id))
            fe.title(title)
            fe.link(href=link)
            fe.description(description)
            fe.pubDate(pub_date)
            fe.updated(pub_date)

        fg.rss_file('feed_portal.xml', pretty=True)

    except Exception as e:
        pass

if __name__ == "__main__":
    generate_rss_portal()
