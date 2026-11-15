import os
import re
import requests

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
SERPER_API_KEY = os.environ.get("SERPER_API_KEY")

# Búsquedas exactas y precio mínimo real para filtrar accesorios/correas
BUSQUEDAS = [
    {"nombre": "Mosko Moto Reckless 40L", "query": "Mosko Moto Reckless 40L", "min_precio": 350.0},
    {"nombre": "Enduristan Blizzard 2.25", "query": "Enduristan Blizzard 2.25 alforjas", "min_precio": 160.0},
    {"nombre": "Kriega OS-Base 701", "query": "Kriega OS-Base Husqvarna 701 KTM 690", "min_precio": 120.0},
    {"nombre": "Kriega Bolsa OS-18", "query": "Kriega OS-18 Adventure Pack", "min_precio": 100.0},
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

def buscar_mejor_oferta(query, min_precio):
    url = "https://google.serper.dev/shopping"
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
    resultados = resp.json().get("shopping", [])
    
    mejor_oferta = None
    
    for item in resultados:
        titulo = item.get("title", "").lower()
        # Descartar explícitamente fundas térmicas o accesorios sueltos
        if any(palabra in titulo for palabra in ["inferno", "heat shield", "protector", "correa", "strap", "recambio", "funda"]):
            continue
            
        precio = limpiar_precio(item.get("price"))
        if precio and min_precio <= precio <= 1500:
            if mejor_oferta is None or precio < mejor_oferta["precio"]:
                mejor_oferta = {
                    "precio": precio,
                    "tienda": item.get("source", "Tienda web"),
                    "enlace": item.get("link", ""),
                    "titulo": item.get("title", "")
                }
                
    return mejor_oferta

def main():
    if not SERPER_API_KEY:
        enviar_telegram("⚠️ Falta configurar `SERPER_API_KEY` en los secretos de GitHub.")
        return

    mensaje = "🏍️ *Radar Global Google Shopping (Black Friday)* 🏍️\n\n"
    
    for item in BUSQUEDAS:
        try:
            oferta = buscar_mejor_oferta(item["query"], item["min_precio"])
            if oferta:
                mensaje += (
                    f"• *{item['nombre']}*\n"
                    f"  Mínimo web: `{oferta['precio']:.2f} €` ({oferta['tienda']})\n"
                    f"  [Ver oferta]({oferta['enlace']})\n\n"
                )
            else:
                mensaje += f"• *{item['nombre']}*\n  Sin resultados válidos hoy\n\n"
        except Exception as e:
            mensaje += f"• *{item['nombre']}*\n  Error de consulta: `{str(e)}`\n\n"
            
    enviar_telegram(mensaje)

if __name__ == "__main__":
    main()
