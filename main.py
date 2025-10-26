from fastapi import FastAPI, Request
import requests, os

# --- INFORMAÇÕES DE INICIALIZAÇÃO ---
print("🚀 Versão do Kauã Concierge: 1.4.0 — integração Groq + Z-API Cloud v2 (/send-text)")

app = FastAPI()

# --- VARIÁVEIS DE AMBIENTE ---
AUTHORIZED_NUMBER = os.getenv("AUTHORIZED_NUMBER", "")
ZAPI_ID = os.getenv("ZAPI_ID")
ZAPI_TOKEN = os.getenv("ZAPI_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME", "llama-3.1-8b-instant")

# ✅ ENDPOINT CORRETO PARA SUA INSTÂNCIA
ZAPI_URL = f"https://api.z-api.io/instances/{ZAPI_ID}/token/{ZAPI_TOKEN}/send-text"

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
        payload = {"phone": phone, "text": message}
        print(f"\n📤 Enviando mensagem para {phone}: '{message}'")
        print(f"🔗 POST {ZAPI_URL}")
        print(f"📨 Payload: {payload}")

        r = requests.post(ZAPI_URL, json=payload, timeout=15)
        print(f"📦 Resposta da Z-API ({r.status_code}): {r.text}")

        if r.status_code == 200 and "error" not in r.text.lower():
            print("✅ Mensagem enviada com sucesso pela Z-API")
        else:
            print(f"[ERRO] Falha ao enviar ({r.status_code}) — verifique ID/TOKEN ou payload.")
    except Exception as e:
        print(f"[ERRO] Exceção ao enviar mensagem via Z-API: {e}")

# --- FUNÇÃO PARA EXTRAIR TEXTO DO PAYLOAD ---
def extract_text(data: dict) -> str:
    """
    A Z-API envia diferentes formatos de JSON dependendo da configuração.
    Essa função cobre todos os padrões comuns.
    """
    if "text" in data and isinstance(data["text"], dict):
        return data["text"].get("message", "").strip()
    elif "message" in data and isinstance(data["message"], str):
        return data["message"].strip()
    elif "body" in data and isinstance(data["body"], str):
        return data["body"].strip()
    return ""

# --- WEBHOOK PRINCIPAL ---
@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    phone = data.get("phone")
    text = extract_text(data)

    print(f"\n📩 Mensagem recebida de {phone}: '{text}'")

    if not phone or not text:
        print("⚠️ Dados inválidos recebidos no webhook.")
        return {"status": "invalid"}

    if AUTHORIZED_NUMBER and phone != AUTHORIZED_NUMBER:
        print(f"🚫 Ignorando número não autorizado: {phone}")
        return {"status": "ignored"}

    # --- PEDIDO PARA ATENDENTE ---
    if any(word in text.lower() for word in ["atendente", "pessoa", "humano"]):
        send_message(phone, "Tudo bem 🌺! Já chamei nossa atendente pra falar com você!")
        send_message(AUTHORIZED_NUMBER, f"⚠️ Cliente {phone} pediu atendimento humano: '{text}'")
        return {"status": "human_mode_triggered"}

    # --- PROCESSAMENTO COM GROQ ---
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
        response.raise_for_status()
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
    return {"status": "ok", "message": "Kauã Concierge ativo 🌴 (Groq + Z-API Cloud v2)"}
