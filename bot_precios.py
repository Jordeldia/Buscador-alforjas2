import os
import requests
from bs4 import BeautifulSoup

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

# Ahora buscamos por términos de producto para comparar en tiendas de todo internet
BUSQUEDAS = {
    "Mosko Reckless 40L": "https://www.google.com/search?q=Mosko+Moto+Reckless+40L+precio&tbm=shop",
    "Enduristan Blizzard 2": "https://www.google.com/search?q=Enduristan+Blizzard+2+precio&tbm=shop",
    "Kriega OS-Base 701": "https://www.google.com/search?q=Kriega+OS-Base+701+precio&tbm=shop",
    "Kriega Bolsa OS-18": "https://www.google.com/search?q=Kriega+OS-18+precio&tbm=shop",
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

def extraer_precio_google(soup):
    # Buscar patrones de precios en los resultados de Google Shopping
    for span in soup.find_all("span", class_=lambda x: x and ('price' in x.lower() or 'amount' in x.lower())):
        texto = span.get_text(strip=True)
        if ("€" in texto or "EUR" in texto) and any(c.isdigit() for c in texto):
            if len(texto) < 12:
                return texto
    
    # Intento alternativo buscando símbolos de moneda en el texto general
    divs = soup.find_all(["div", "span"], string=lambda s: s and "€" in s and any(c.isdigit() for c in s))
    for d in divs:
        texto = d.get_text(strip=True)
        if len(texto) < 15:
            return texto

    return "Consultar en comparador"

def main():
    mensaje = "🏍️ *Buscador de Chollos (Black Friday)* 🏍️\n\n"
    for modelo, url in BUSQUEDAS.items():
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(resp.text, "html.param" if hasattr(BeautifulSoup, 'parser') else "html.parser")
            precio = extraer_precio_google(soup)
            mensaje += f"• *{modelo}*\n  Mejor precio aprox: `{precio}`\n  [Ver en Google Shopping]({url})\n\n"
        except Exception:
            mensaje += f"• *{modelo}*\n  Error al conectar\n\n"
    
    enviar_telegram(mensaje)

if __name__ == "__main__":
    main()
