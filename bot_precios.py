import os
import re
import json
import requests
from bs4 import BeautifulSoup

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

# Lista de múltiples tiendas/comparadores por producto
# El bot comprobará todas las URLs de cada grupo y te dará el precio más bajo
CATALOGO = {
    "Mosko Reckless 40L": [
        ("Mosko EU", "https://moskomoto.eu/products/reckless-40l-v4"),
    ],
    "Enduristan Blizzard 2.25": [
        ("FC-Moto", "https://www.fc-moto.de/es/Enduristan-Blizzard-2-Alforjas"),
        ("Idealo ES", "https://www.idealo.es/precios/202149546/enduristan-blizzard.html"),
        ("TwinTrail", "https://www.twintrail.com/alforjas-y-bolsas-moto/420-alforjas-enduristan-blizzard.html"),
    ],
    "Kriega OS-Base 701": [
        ("TwinTrail", "https://www.twintrail.com/alforjas-y-bolsas-moto/1950-soporte-kriega-overlander-ktm-690-husq-701-gasgas-700.html"),
        ("FC-Moto", "https://www.fc-moto.de/es/Kriega-OS-Base-KTM-690-Husqvarna-701-GasGas-700"),
        ("Motocard", "https://www.motocard.com/bolsas/kriega-os_base_ktm_690_husqvarna_701_gasgas_700.aspx"),
    ],
    "Kriega Bolsa OS-18": [
        ("TwinTrail", "https://www.twintrail.com/alforjas-y-bolsas-moto/1646-alforja-kriega-overlander-s-os-18.html"),
        ("FC-Moto", "https://www.fc-moto.de/es/Kriega-OS-18-Adventure-Pack"),
        ("Motocard", "https://www.motocard.com/bolsas/kriega-os_18.aspx"),
    ]
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

def limpiar_numero(texto):
    # Convierte "199,90 €" o "555.0 EUR" en un float 199.90 para poder comparar cuál es menor
    if not texto:
        return None
    limpio = re.sub(r"[^\d,\.]", "", texto)
    if "," in limpio and "." in limpio:
        limpio = limpio.replace(".", "").replace(",", ".")
    elif "," in limpio:
        limpio = limpio.replace(",", ".")
    try:
        val = float(limpio)
        return val if 30 < val < 1500 else None # Filtro anti-falsos positivos
    except ValueError:
        return None

def extraer_precio(soup):
    # 1. Metadatos OpenGraph / Shopify
    meta_price = soup.find("meta", {"property": "og:price:amount"}) or soup.find("meta", {"property": "product:price:amount"})
    if meta_price and meta_price.get("content"):
        val = limpiar_numero(meta_price["content"])
        if val:
            return val

    # 2. Datos estructurados JSON-LD
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
                val = limpiar_numero(str(precio))
                if val:
                    return val
        except Exception:
            pass

    # 3. Selectores HTML habituales (PrestaShop, Idealo, FC-Moto, Motocard)
    selectores = [
        ("span", {"class": "current-price-value"}),
        ("span", {"itemprop": "price"}),
        ("div", {"class": "productOffers-listItemOfferPrice"}), # Idealo
        ("span", {"class": "price"}),
        ("span", {"class": "money"}),
    ]
    for tag, attrs in selectores:
        el = soup.find(tag, attrs)
        if el:
            val = limpiar_numero(el.get_text(strip=True))
            if val:
                return val

    return None

def main():
    mensaje = "🏍️ *Radar Multi-Tienda Black Friday* 🏍️\n\n"
    
    for modelo, fuentes in CATALOGO.items():
        mejor_precio = None
        mejor_tienda = ""
        mejor_url = ""
        
        for tienda, url in fuentes:
            try:
                resp = requests.get(url, headers=HEADERS, timeout=12)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    precio = extraer_precio(soup)
                    if precio is not None:
                        if mejor_precio is None or precio < mejor_precio:
                            mejor_precio = precio
                            mejor_tienda = tienda
                            mejor_url = url
            except Exception:
                continue
        
        if mejor_precio is not None:
            mensaje += f"• *{modelo}*\n  Mejor oferta: `{mejor_precio:.2f} €` ({mejor_tienda})\n  [Ir a la oferta]({mejor_url})\n\n"
        else:
            mensaje += f"• *{modelo}*\n  Sin lectura automática hoy\n\n"
            
    enviar_telegram(mensaje)

if __name__ == "__main__":
    main()
