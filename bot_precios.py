import os
import re
import json
import requests
from bs4 import BeautifulSoup

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

URLS = {
    "Mosko Reckless 40L (EU)": "https://moskomoto.eu/products/reckless-40l-v4",
    "Enduristan Blizzard 2 (2.25 / 2.35)": "https://www.enduristan.com/products/blizzard-2-saddle-bags",
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

def extraer_precio(soup, html_raw):
    # 1. Buscar en metadatos estándar (OpenGraph / Shopify)
    meta_price = soup.find("meta", {"property": "og:price:amount"}) or soup.find("meta", {"property": "product:price:amount"})
    meta_curr = soup.find("meta", {"property": "og:price:currency"}) or soup.find("meta", {"property": "product:price:currency"})
    if meta_price and meta_price.get("content"):
        moneda = meta_curr.get("content", "€") if meta_curr else "€"
        return f"{meta_price['content']} {moneda}"

    # 2. Buscar en datos estructurados JSON-LD (Google Shopping)
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
                moneda = offers.get("priceCurrency", "€")
                if precio:
                    return f"{precio} {moneda}"
        except Exception:
            pass

    # 3. Buscar en etiquetas HTML clásicas (TwinTrail / PrestaShop)
    selectores = [
        ("span", {"class": "current-price-value"}),
        ("span", {"itemprop": "price"}),
        ("span", {"class": "price-item--sale"}),
        ("span", {"class": "price-item--regular"}),
        ("span", {"class": "money"}),
    ]
    for tag, attrs in selectores:
        el = soup.find(tag, attrs)
        if el:
            texto = el.get_text(strip=True)
            if any(c.isdigit() for c in texto):
                return texto

    return "No disponible (requiere revisión manual)"

def main():
    mensaje = "🏍️ *Resumen Alforjas Moto* 🏍️\n\n"
    for modelo, url in URLS.items():
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(resp.text, "html.parser")
            precio = extraer_precio(soup, resp.text)
            mensaje += f"• *{modelo}*\n  Precio: `{precio}`\n  [Ver enlace]({url})\n\n"
        except Exception:
            mensaje += f"• *{modelo}*\n  Error al conectar\n\n"
    
    enviar_telegram(mensaje)

if __name__ == "__main__":
    main()
