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

    # Fallback para outros formatos
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

    # --- Processa via Groq API ---
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
