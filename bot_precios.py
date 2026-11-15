import os
import re
import time
import requests

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
SERPER_API_KEY = os.environ.get("SERPER_API_KEY")

BUSQUEDAS_TIENDAS = [
    {"nombre": "Mosko Moto Reckless 40L", "query": "Mosko Moto Reckless 40L alforjas moto", "min_precio": 450.0},
    {"nombre": "Enduristan Blizzard 2.25", "query": "Enduristan Blizzard 2.25 alforjas", "min_precio": 180.0},
    {"nombre": "Kriega OS-Base 701", "query": "Kriega OS-Base Husqvarna 701", "min_precio": 150.0},
    {"nombre": "Kriega Bolsa OS-18", "query": "Kriega OS-18 Adventure Pack", "min_precio": 120.0},
]

BUSQUEDAS_SEGUNDA_MANO = [
    {"nombre": "Mosko Moto Reckless 40L", "query": "site:wallapop.com Mosko Reckless", "min_precio": 200.0},
    {"nombre": "Enduristan Blizzard 2.25", "query": "site:wallapop.com Enduristan Blizzard", "min_precio": 80.0},
    {"nombre": "Kriega OS-Base 701", "query": "site:wallapop.com Kriega OS Base", "min_precio": 60.0},
    {"nombre": "Kriega Bolsa OS-18", "query": "site:wallapop.com Kriega OS 18", "min_precio": 50.0},
]

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

def limpiar_precio(texto):
    if not texto:
        return None
    limpio = re.sub(r"[^\d,\.]", "", str(texto))
    if "," in limpio and "." in limpio:
        limpio = limpio.replace(".", "").replace(",", ".")
    elif "," in limpio:
        limpio = limpio.replace(",", ".")
    try:
        return float(limpio)
    except ValueError:
        return None

def main():
    if not SERPER_API_KEY:
        enviar_telegram("⚠️ Falta configurar `SERPER_API_KEY` en los secretos de GitHub.")
        return

    mensaje = "🏍️ *Radar Dual: Tiendas & Segunda Mano* 🏍️\n\n"
    
    # 1. BLOQUE TIENDAS PROFESIONALES
    mensaje += "🏪 *— OFERTAS EN TIENDAS —*\n"
    for item in BUSQUEDAS_TIENDAS:
        try:
            url_shop = "https://google.serper.dev/shopping"
            headers = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
            resp = requests.post(url_shop, headers=headers, json={"q": item["query"], "gl": "es", "hl": "es", "num": 15}, timeout=10)
            resultados = resp.json().get("shopping", [])
            
            mejor = None
            for res in resultados:
                if any(bad in res.get("source","").lower() for bad in ["wallapop", "ebay"]): 
                    continue
                p = limpiar_precio(res.get("price"))
                if p and item["min_precio"] <= p <= 1500:
                    if not mejor or p < mejor["precio"]:
                        mejor = {"precio": p, "tienda": res.get("source"), "enlace": res.get("link")}
            
            if mejor:
                mensaje += f"• *{item['nombre']}*: `{mejor['precio']:.2f} €` ([{mejor['tienda']}]({mejor['enlace']}))\n"
            else:
                mensaje += f"• *{item['nombre']}*: Sin stock web óptimo\n"
            time.sleep(1) # Pausa breve para evitar bloqueos
        except Exception:
            mensaje += f"• *{item['nombre']}*: Error de lectura\n"

    mensaje += "\n🔄 *— WALLAPOP / SEGUNDA MANO —*\n"
    
    # 2. BLOQUE SEGUNDA MANO (Wallapop directo por búsqueda web)
    for item in BUSQUEDAS_SEGUNDA_MANO:
        try:
            url_web = "https://google.serper.dev/search"
            headers = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
            resp = requests.post(url_web, headers=headers, json={"q": item["query"], "gl": "es", "hl": "es", "num": 10}, timeout=10)
            resultados = resp.json().get("organic", [])
            
            mejor_sm = None
            for res in resultados:
                enlace = res.get("link", "")
                if "wallapop.com" not in enlace:
                    continue
                
                # Intentar buscar un patrón de precio en el título o descripción del snippet
                texto_analizar = res.get("title", "") + " " + res.get("snippet", "")
                match_precio = re.search(r"(\d{2,4})[,\.]?\d{0,2}\s*€", texto_analizar)
                if match_precio:
                    p = limpiar_precio(match_precio.group(0))
                    if p and item["min_precio"] <= p <= 1500:
                        if not mejor_sm or p < mejor_sm["precio"]:
                            mejor_sm = {"precio": p, "enlace": enlace}
            
            if mejor_sm:
                mensaje += f"• *{item['nombre']}*: `{mejor_sm['precio']:.2f} €` ([Ver en Wallapop]({mejor_sm['enlace']}))\n"
            else:
                mensaje += f"• *{item['nombre']}*: Sin anuncios activos hoy\n"
            time.sleep(1)
        except Exception:
            mensaje += f"• *{item['nombre']}*: Sin resultados\n"

    enviar_telegram(mensaje)

if __name__ == "__main__":
    main()
