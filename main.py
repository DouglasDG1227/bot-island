from fastapi import FastAPI, Request
import requests, os

print("🚀 Versão do Kauã Concierge: 1.3.2 — integração Groq e Z-API OK")

# 🔹 Criação do app ANTES das rotas
app = FastAPI()

# --- VARIÁVEIS DE AMBIENTE ---
AUTHORIZED_NUMBER = os.getenv("AUTHORIZED_NUMBER", "")
ZAPI_ID = os.getenv("ZAPI_ID")
ZAPI_TOKEN = os.getenv("ZAPI_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME", "llama3-8b-8192")

ZAPI_URL = f"https://api.z-api.io/instances/{ZAPI_ID}/token/{ZAPI_TOKEN}/send-message"

# --- PERSONALIDADE DO AGENTE ---
AGENT_SYSTEM_PROMPT = """
Você é Kauã, o concierge digital da Ilha Azul 🌴.
Fale com simpatia, gírias leves e tom humano.
Ajude visitantes com reservas, dúvidas e sugestões.
Nunca diga que é uma IA.
Se alguém pedir para falar com atendente, chame a dona e pare de responder.
"""

# --- FUNÇÃO PARA ENVIAR MENSAGEM VIA Z-API ---
def send_message(phone: str, message: str):
    try:
        payload = {"phone": phone, "message": message}
        r = requests.post(ZAPI_URL, json=payload, timeout=10)
        if r.status_code != 200:
            print(f"[ERRO] Falha ao enviar mensagem ({r.status_code}): {r.text}")
    except Exception as e:
        print(f"[ERRO] Falha ao enviar mensagem: {e}")

# --- WEBHOOK PRINCIPAL ---
@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    phone = data.get("phone")

    # --- Captura o texto da mensagem, independente do formato ---
    text = ""
    message = data.get("message", {})

    if isinstance(message, dict):
        # Formato 1: {"message": {"text": "oi"}}
        if "text" in message:
            text = message["text"]

        # Formato 2: {"message": {"content": {"body": "oi"}}}
        elif "content" in message and isinstance(message["content"], dict):
            text = message["content"].get("body", "")

        # Formato 3: {"message": {"message": "oi"}}
        elif "message" in message and isinstance(message["message"], str):
            text = message["message"]

    # Fallback (mensagem direta)
    elif "text" in data:
        text = data.get("text", "")

    if not isinstance(text, str):
        text = str(text)
    text = text.strip()

    # --- Logs ---
    print(f"\n📩 Mensagem recebida de {phone}: '{text}'")

    if not phone or not text:
        print("⚠️ Dados inválidos recebidos no webhook.")
        return {"status": "invalid"}

    # --- Verifica número autorizado ---
    if AUTHORIZED_NUMBER and phone != AUTHORIZED_NUMBER:
        print(f"🚫 Ignorando número não autorizado: {phone}")
        return {"status": "ignored"}

    # --- Atendimento humano ---
    if any(word in text.lower() for word in ["atendente", "pessoa", "humano"]):
        send_message(phone, "Tudo bem 🌺! Já chamei nossa atendente pra falar com você!")
        send_message(AUTHORIZED_NUMBER, f"⚠️ Cliente {phone} pediu atendimento humano: '{text}'")
        return {"status": "human_mode_triggered"}

    # --- CHAMADA GROQ API ---
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": MODEL_NAME,
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
        if response.status_code != 200:
            print(f"[ERRO] Groq retornou {response.status_code}: {response.text}")
            raise Exception("Resposta inválida da Groq API")

        reply = response.json()["choices"][0]["message"]["content"]
        print(f"💬 Resposta gerada: {reply}")
    except Exception as e:
        print(f"[ERRO] Falha ao consultar Groq API: {e}")
        reply = "Desculpa 🌊, tive um probleminha técnico. Pode repetir sua mensagem?"

    send_message(phone, reply)
    return {"status": "ok", "reply": reply}

# --- HEALTH CHECK ---
@app.get("/")
def root():
    print("✅ Health check acessado.")
    return {"status": "ok", "message": "Kauã Concierge ativo 🌴 (Groq API)"}
