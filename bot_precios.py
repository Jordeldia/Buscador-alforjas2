import os
import re
import requests

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
SERPER_API_KEY = os.environ.get("SERPER_API_KEY")

# Artículos que buscamos
BUSQUEDAS_TIENDAS = [
    {"nombre": "Mosko Moto Reckless 40L", "query": "Mosko Moto Reckless 40L alforjas moto", "min_precio": 450.0},
    {"nombre": "Enduristan Blizzard 2.25", "query": "Enduristan Blizzard 2.25 alforjas", "min_precio": 180.0},
    {"nombre": "Kriega OS-Base 701", "query": "Kriega OS-Base Husqvarna 701", "min_precio": 150.0},
    {"nombre": "Kriega Bolsa OS-18", "query": "Kriega OS-18 Adventure Pack", "min_precio": 120.0},
]

BUSQUEDAS_SEGUNDA_MANO = [
    {"nombre": "Mosko Moto Reckless 40L", "query": "site:wallapop.com Mosko Reckless OR Mosko Moto", "min_precio": 250.0},
    {"nombre": "Enduristan Blizzard 2.25", "query": "site:wallapop.com Enduristan Blizzard", "min_precio": 100.0},
    {"nombre": "Kriega OS-Base 701", "query": "site:wallapop.com Kriega OS Base 701", "min_precio": 80.0},
    {"nombre": "Kriega Bolsa OS-18", "query": "site:wallapop.com Kriega OS 18", "min_precio": 60.0},
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

def consultar_google(query, min_precio, excluir_webs=False):
    url = "https://google.serper.dev/search" # Usamos búsqueda web general para indexar bien Wallapop
    headers = {
        "X-API-KEY": SERPER_API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "q": query,
        "gl": "es",
        "hl": "es",
        "num": 20
    }
    
    resp = requests.post(url, headers=headers, json=payload, timeout=15)
    resp.raise_for_status()
    # Serper devuelve 'organic' para búsquedas web generales
    resultados = resp.json().get("organic", [])
    
    mejor_oferta = None
    
    for item in resultados:
        titulo = item.get("title", "").lower()
        enlace = item.get("link", "").lower()
        snippet = item.get("snippet", "").lower()
        
        # Filtrado según lo que busquemos
        if excluir_webs:
            if not any(sitio in enlace for sitio in ["wallapop.com", "ebay.es", "milanuncios.com"]):
                continue
        else:
            if any(bad in enlace for bad in ["wallapop", "milanuncios", "ebay"]):
                continue
                
        # Intentar extraer precio del texto o del snippet (Google a veces lo incluye)
        texto_completo = f"{titulo} {snippet}"
        match_precio = re.search(r"(\d{2,4})[,\.]\d{2}\s*€|€\s*(\d{2,4})", texto_completo)
        
        precio = None
        if match_precio:
            precio_str = match_precio.group(1) or match_precio.group(2)
            precio = limpiar_precio(precio_str)
        
        # Si no lo saca del texto, miramos si viene en formato shopping por si acaso
        if not precio:
            continue
            
        if precio and min_precio <= precio <= 1500:
            if mejor_oferta is None or precio < mejor_oferta["precio"]:
                fuente = "Wallapop" if "wallapop" in enlace else ("eBay" if "ebay" in enlace else "Particular")
                mejor_oferta = {
                    "precio": precio,
                    "tienda": fuente,
                    "enlace": item.get("link", ""),
                    "titulo": item.get("title", "")
                }
                
    return mejor_oferta

def main():
    if not SERPER_API_KEY:
        enviar_telegram("⚠️ Falta configurar `SERPER_API_KEY` en los secretos de GitHub.")
        return

    mensaje = "🏍️ *Radar Dual: Tiendas & Segunda Mano* 🏍️\n\n"
    
    # 1. BLOQUE TIENDAS PROFESIONALES
    mensaje += "🏪 *— OFERTAS EN TIENDAS —*\n"
    for item in BUSQUEDAS_TIENDAS:
        try:
            # Usamos shopping para tiendas
            url_shop = "https://google.serper.dev/shopping"
            headers = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
            resp = requests.post(url_shop, headers=headers, json={"q": item["query"], "gl": "es", "hl": "es", "num": 20}, timeout=15)
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
                mensaje += f"• *{item['nombre']}*: `{mejor['precio']:.2f} €` ({mejor['tienda']})\n  [Ver oferta]({mejor['enlace']})\n"
            else:
                mensaje += f"• *{item['nombre']}*: Sin stock web óptimo\n"
        except Exception:
            pass

    mensajeING = "\n🔄 *— WALLAPOP / SEGUNDA MANO —*\n"
    # 2. BLOQUE SEGUNDA MANO (Wallapop)
    for item in BUSQUEDAS_SEGUNDA_MANO:
        try:
            oferta_sm = consultar_google(item["query"], item["min_precio"], excluir_webs=True)
            if oferta_sm:
                mensajeING += f"• *{item['nombre']}*: `{oferta_sm['precio']:.2f} €` ([{oferta_sm['tienda']}]({oferta_sm['enlace']}))\n"
            else:
                mensajeING += f"• *{item['nombre']}*: Sin anuncios destacados\n"
        except Exception:
            pass

    enviar_telegram(mensaje + mensajeING)

if __name__ == "__main__":
    main()
