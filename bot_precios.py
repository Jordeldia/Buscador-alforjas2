import os
import json
import requests
from bs4 import BeautifulSoup

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

# Enlaces directos a tiendas europeas fiables con precios accesibles
URLS = {
    "Mosko Reckless 40L (EU)": "https://moskomoto.eu/products/reckless-40l-v4",
    "Enduristan Blizzard 2.25": "https://www.motoblouz.es/alforjas-moto-enduristan-blizzard-bolsas-laterales-v3-138676-v.html",
    "Kriega OS-Base 701 (TwinTrail)": "https://www.twintrail.com/alforjas-y-bolsas-moto/1950-soporte-kriega-overlander-ktm-690-husq-701-gasgas-700.html",
    "Kriega Bolsa OS-18 (TwinTrail)": "https://www.twintrail.com/alforjas-y-bolsas-moto/1646-alforja-kriega-overlander-s-os-18.html",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8"
}

def enviar_telegram(texto):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={
        "chat_id": CHAT_ID,
        "text": texto,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }, timeout=10)

def extraer_precio(soup, url):
    # Si es Motoblouz o similar (PrestaShop / metadatos)
    meta_price = soup.find("meta", {"property": "og:price:amount"}) or soup.find("meta", {"property": "product:price:amount"})
    if meta_price and meta_price.get("content"):
        return f"{meta_price['content']} EUR"

    # Datos estructurados JSON-LD
    for script in soup.find_all("script", {"type": "application/ld+json"}):
        try:
            data = json.loads(script.string)
            if isinstance(data, list):
                data = data[0]
            offers = data.get("offers")
            if isinstance(offers, list):
                offers = offers[0]
            if isinstance(offers, dict):
                precio = offers.get("price") or offers.get("lowPrice")
                if precio:
                    return f"{precio} EUR"
        except Exception:
            pass

    # Selectores clásicos (PrestaShop / WooCommerce / Tiendas de trail)
    selectores = [
        ("span", {"class": "current-price-value"}),
        ("span", {"itemprop": "price"}),
        ("span", {"class": "price"}),
        ("span", {"class": "price-item--sale"}),
        ("span", {"class": "money"}),
    ]
    for tag, attrs in selectores:
        el = soup.find(tag, attrs)
        if el:
            texto = el.get_text(strip=True)
            if any(c.isdigit() for c in texto):
                return texto

    return "Consultar web"

def main():
    mensaje = "🏍️ *Monitoreo Alforjas Black Friday* 🏍️\n\n"
    for modelo, url in URLS.items():
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(resp.text, "html.parser")
            precio = extraer_precio(soup, url)
            mensaje += f"• *{modelo}*\n  Precio: `{precio}`\n  [Ver enlace]({url})\n\n"
        except Exception:
            mensaje += f"• *{modelo}*\n  Error de conexión\n\n"
    
    enviar_telegram(mensaje)

if __name__ == "__main__":
    main()
