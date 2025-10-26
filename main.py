from fastapi import FastAPI, Request
import requests, os

app = FastAPI()

# --- VARIÁVEIS DE AMBIENTE ---
AUTHORIZED_NUMBER = os.getenv("AUTHORIZED_NUMBER", "")
ZAPI_ID = os.getenv("ZAPI_ID")
ZAPI_TOKEN = os.getenv("ZAPI_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

ZAPI_URL = f"https://api.z-api.io/instances/{ZAPI_ID}/token/{ZAPI_TOKEN}/send-message"

# --- PERSONALIDADE DO AGENTE ---
AGENT_SYSTEM_PROMPT = """
Você é Kauã, o concierge digital da Ilha Azul 🌴.
Fale com simpatia, gírias leves e tom humano.
Ajude visitantes com reservas, dúvidas e sugestões.
Nunca diga que é uma IA.
Se alguém pedir para falar com atendente, chame a dona e pare de responder.
"""

# --- FUNÇÃO AUXILIAR ---
def send_message(phone: str, message: str):
    try:
        payload = {"phone": phone, "message": message}
        requests.post(ZAPI_URL, json=payload, timeout=10)
    except Exception as e:
        print(f"Erro ao enviar mensagem: {e}")

# --- WEBHOOK ---
@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    phone = data.get("phone")
    text = data.get("text", "").strip()

    if not phone or not text:
        return {"status": "invalid"}

    # Autoriza apenas o número configurado
    if AUTHORIZED_NUMBER and phone != AUTHORIZED_NUMBER:
        print(f"Ignorando número não autorizado: {phone}")
        return {"status": "ignored"}

    # Atendimento humano
    if any(word in text.lower() for word in ["atendente", "pessoa", "humano"]):
        send_message(phone, "Tudo bem 🌺! Já chamei nossa atendente pra falar com você!")
        send_message(AUTHORIZED_NUMBER, f"⚠️ Cliente {phone} pediu atendimento humano: '{text}'")
        return {"status": "human_mode_triggered"}

    # --- PROCESSA VIA GROQ API ---
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "llama3-8b-8192",
        "messages": [
            {"role": "system", "content": AGENT_SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
    }

    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        reply = response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"Erro ao consultar Groq API: {e}")
        reply = "Desculpa 🌊, tive um probleminha técnico. Pode repetir sua mensagem?"

    send_message(phone, reply)
    return {"status": "ok", "reply": reply}

# --- HEALTH CHECK ---
@app.get("/")
def root():
    return {"status": "ok", "message": "Kauã Concierge ativo 🌴 (Groq API)"}
