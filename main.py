from fastapi import FastAPI, Request
import requests, os

print("🚀 Versão do Kauã Concierge: 1.4.4 — anti-loop real + client-token ativo")

app = FastAPI()

AUTHORIZED_NUMBER = os.getenv("AUTHORIZED_NUMBER", "")
ZAPI_ID = os.getenv("ZAPI_ID")
ZAPI_TOKEN = os.getenv("ZAPI_TOKEN")
ZAPI_CLIENT_TOKEN = os.getenv("ZAPI_CLIENT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME", "llama-3.1-8b-instant")

ZAPI_URL = f"https://api.z-api.io/instances/{ZAPI_ID}/token/{ZAPI_TOKEN}/send-text"

AGENT_SYSTEM_PROMPT = """
Você é Kauã, o concierge digital da Ilha Azul 🌴.
Fale de forma simpática e natural, sem parecer IA.
Ajude visitantes com reservas, dúvidas e sugestões.
Se pedirem para falar com atendente, encaminhe e pare de responder.
"""

def send_message(phone: str, message: str):
    try:
        headers = {
            "Content-Type": "application/json",
            "client-token": ZAPI_CLIENT_TOKEN or ""
        }
        payload = {"phone": phone, "message": message}

        print(f"\n📤 Enviando mensagem para {phone}: '{message}'")
        r = requests.post(ZAPI_URL, headers=headers, json=payload, timeout=15)
        print(f"💬 Resposta da Z-API ({r.status_code}): {r.text}")
    except Exception as e:
        print(f"[ERRO] Exceção ao enviar mensagem via Z-API: {e}")

def extract_text(data: dict) -> str:
    if "text" in data and isinstance(data["text"], dict):
        return data["text"].get("message", "").strip()
    if "message" in data and isinstance(data["message"], str):
        return data["message"].strip()
    if "body" in data and isinstance(data["body"], str):
        return data["body"].strip()
    return ""

@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    phone = data.get("phone")
    text = extract_text(data)

    print(f"\n📩 Mensagem recebida de {phone}: '{text}'")

    # 🧠 VERDADEIRO ANTI-LOOP — só ignora mensagens enviadas PELO BOT
    if data.get("fromMe"):
        print("🔁 Ignorado: mensagem enviada pelo próprio bot (evitando loop real).")
        return {"status": "self_message_ignored"}

    # Ignora mensagens sem texto
    if not phone or not text:
        print("⚠️ Dados inválidos recebidos no webhook.")
        return {"status": "invalid"}

    # Modo humano
    if any(word in text.lower() for word in ["atendente", "humano", "pessoa"]):
        send_message(phone, "Tudo bem 🌺! Já chamei nossa atendente pra falar com você!")
        send_message(AUTHORIZED_NUMBER, f"⚠️ Cliente {phone} pediu atendimento humano: '{text}'")
        return {"status": "human_mode_triggered"}

    # Geração de resposta (Groq)
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": AGENT_SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
    }

    try:
        response = requests.post("https://api.groq.com/openai/v1/chat/completions",
                                 headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        reply = response.json()["choices"][0]["message"]["content"]
        print(f"💬 Resposta gerada: {reply}")
    except Exception as e:
        print(f"[ERRO] Falha ao consultar Groq API: {e}")
        reply = "Desculpa 🌊, tive um probleminha técnico. Pode repetir sua mensagem?"

    send_message(phone, reply)
    return {"status": "ok", "reply": reply}

@app.get("/")
def root():
    print("✅ Health check acessado.")
    return {"status": "ok", "message": "Kauã Concierge ativo 🌴 (anti-loop real + client-token OK)"}
