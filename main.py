from fastapi import FastAPI, Request
import requests, os, json

print("🚀 Versão do Kauã Concierge: 1.3.4 — modo debug ativo")

app = FastAPI()

# --- VARIÁVEIS DE AMBIENTE ---
AUTHORIZED_NUMBER = os.getenv("AUTHORIZED_NUMBER", "")
ZAPI_ID = os.getenv("ZAPI_ID")
ZAPI_TOKEN = os.getenv("ZAPI_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME", "llama3-8b-8192")

ZAPI_URL = f"https://api.z-api.io/instances/{ZAPI_ID}/token/{ZAPI_TOKEN}/send-message"


# --- PERSONALIDADE ---
AGENT_SYSTEM_PROMPT = """
Você é Kauã, o concierge digital da Ilha Azul 🌴.
Fale com simpatia, gírias leves e tom humano.
Ajude visitantes com reservas, dúvidas e sugestões.
Nunca diga que é uma IA.
Se alguém pedir para falar com atendente, chame a dona e pare de responder.
"""


# --- FUNÇÃO DE ENVIO ---
def send_message(phone: str, message: str):
    try:
        payload = {"phone": phone, "message": message}
        r = requests.post(ZAPI_URL, json=payload, timeout=10)
        if r.status_code != 200:
            print(f"[ERRO] Falha ao enviar mensagem ({r.status_code}): {r.text}")
    except Exception as e:
        print(f"[ERRO] Falha ao enviar mensagem: {e}")


# --- WEBHOOK ---
@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    print("\n===============================")
    print("📦 JSON RECEBIDO DA Z-API:")
    print(json.dumps(data, indent=2, ensure_ascii=False))
    print("===============================\n")

    phone = data.get("phone")
    text = None

    # Tentativa básica (para capturar qualquer estrutura)
    try:
        text = (
            data.get("message", {}).get("text")
            or data.get("message", {}).get("body")
            or data.get("message", {}).get("content", {}).get("body")
            or data.get("body")
            or data.get("text")
        )
    except Exception:
        text = None

    if not isinstance(text, str):
        text = str(text or "").strip()

    print(f"📩 Mensagem recebida de {phone}: '{text}'")

    if not phone or not text:
        print("⚠️ Dados inválidos recebidos no webhook.")
        return {"status": "invalid"}

    if AUTHORIZED_NUMBER and phone != AUTHORIZED_NUMBER:
        print(f"🚫 Ignorando número não autorizado: {phone}")
        return {"status": "ignored"}

    # Se chegar aqui, a Groq será chamada normalmente
    send_message(phone, f"✅ Recebi sua mensagem: {text}")
    return {"status": "ok", "message": text}


# --- HEALTH CHECK ---
@app.get("/")
def root():
    print("✅ Health check acessado.")
    return {"status": "ok", "message": "Kauã Concierge ativo 🌴 (modo debug)"}
