import os
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
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
}

def enviar_telegram(texto):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("Faltan credenciales de Telegram.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": texto}, timeout=10)
    except Exception as e:
        print(f"Error enviando a Telegram: {e}")

def extraer_precio(soup):
    selectores = [
        ("span", {"class": "price-item--sale"}),
        ("span", {"class": "price-item--regular"}),
        ("span", {"class": "money"}),
        ("span", {"itemprop": "price"}),
        ("span", {"class": "current-price-value"}),
    ]
    for tag, attrs in selectores:
        el = soup.find(tag, attrs)
        if el:
            texto = el.get_text(strip=True)
            if any(c.isdigit() for c in texto):
                return texto
    return None

def main():
    for modelo, url in URLS.items():
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(resp.text, "html.parser")
            precio = extraer_precio(soup)
            print(f"Revisado {modelo}: {precio}")
        except Exception as e:
            print(f"Error al conectar con {modelo}: {e}")

if __name__ == "__main__":
    main()
