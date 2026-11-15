import os
import re
import json
import requests
from bs4 import BeautifulSoup

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

CATALOGO = {
    "Mosko Reckless 40L": [
        ("Mosko EU", "https://moskomoto.eu/products/reckless-40l-v4"),
    ],
    "Enduristan Blizzard 2.25": [
        ("Enduristan EU", "https://www.enduristan.com/products/blizzard-2-saddle-bags"),
        ("TwinTrail", "https://www.twintrail.com/alforjas-y-bolsas-moto/420-alforjas-enduristan-blizzard.html"),
        ("FC-Moto", "https://www.fc-moto.de/es/Enduristan-Blizzard-2-Alforjas"),
    ],
    "Kriega OS-Base 701": [
        ("TwinTrail", "https://www.twintrail.com/alforjas-y-bolsas-moto/1950-soporte-kriega-overlander-ktm-690-husq-701-gasgas-700.html"),
        ("FC-Moto", "https://www.fc-moto.de/es/Kriega-OS-Base-KTM-690-Husqvarna-701-GasGas-700"),
    ],
    "Kriega Bolsa OS-18": [
        ("TwinTrail", "https://www.twintrail.com/alforjas-y-bolsas-moto/1646-alforja-kriega-overlander-s-os-18.html"),
        ("FC-Moto", "https://www.fc-moto.de/es/Kriega-OS-18-Adventure-Pack"),
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

def limpiar_numero(texto, minimo=110):
    if not texto:
        return None
    limpio = re.sub(r"[^\d,\.]", "", str(texto))
    if "," in limpio and "." in limpio:
        limpio = limpio.replace(".", "").replace(",", ".")
    elif "," in limpio:
        limpio = limpio.replace(",", ".")
    try:
        val = float(limpio)
        return val if minimo < val < 1500 else None
    except ValueError:
        return None

def extraer_shopify_json(url, minimo):
    # Endpoint directo de Shopify (.js) que devuelve precios reales de variantes en céntimos
    try:
        resp = requests.get(f"{url}.js", headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            precios = []
            for v in data.get("variants", []):
                # En Enduristan la variante 2.25 suele incluir "2.25" o "M" en el título
                titulo = v.get("title", "").lower()
                precio_eur = v.get("price", 0) / 100.0
                if "2.25" in titulo or "2,25" in titulo or len(data.get("variants", [])) == 1:
                    if minimo < precio_eur < 1500:
                        return precio_eur
                if minimo < precio_eur < 1500:
                    precios.append(precio_eur)
            if precios:
                return min(precios)
    except Exception:
        pass
    return None

def extraer_precio(url, resp_text, minimo):
    # 1. Si es tienda Shopify (Mosko o Enduristan), leer directamente su JSON interno
    if "enduristan.com" in url or "moskomoto.eu" in url:
        val_shopify = extraer_shopify_json(url, minimo)
        if val_shopify:
            return val_shopify

    soup = BeautifulSoup(resp_text, "html.parser")

    # 2. Metadatos OpenGraph
    meta_price = soup.find("meta", {"property": "og:price:amount"}) or soup.find("meta", {"property": "product:price:amount"})
    if meta_price and meta_price.get("content"):
        val = limpiar_numero(meta_price["content"], minimo)
        if val:
            return val

    # 3. Datos estructurados JSON-LD
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
                val = limpiar_numero(precio, minimo)
                if val:
                    return val
        except Exception:
            pass

    # 4. Selectores HTML habituales
    selectores = [
        ("span", {"class": "current-price-value"}),
        ("span", {"itemprop": "price"}),
        ("span", {"class": "price"}),
        ("span", {"class": "money"}),
    ]
    for tag, attrs in selectores:
        el = soup.find(tag, attrs)
        if el:
            val = limpiar_numero(el.get_text(strip=True), minimo)
            if val:
                return val

    return None

def main():
    mensaje = "🏍️ *Radar Multi-Tienda Black Friday* 🏍️\n\n"
    
    for modelo, fuentes in CATALOGO.items():
        # Para la Blizzard exigimos mínimo 160 € para evitar accesorios sueltos
        minimo_modelo = 160 if "Blizzard" in modelo else 110
        mejor_precio = None
        mejor_tienda = ""
        mejor_url = ""
        
        for tienda, url in fuentes:
            try:
                resp = requests.get(url, headers=HEADERS, timeout=12)
                if resp.status_code == 200:
                    precio = extraer_precio(url, resp.text, minimo_modelo)
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
