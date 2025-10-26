@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    phone = data.get("phone")
    text = extract_text(data)

    print(f"\n📩 Mensagem recebida de {phone}: '{text}'")

    if not phone or not text:
        print("⚠️ Dados inválidos recebidos no webhook.")
        return {"status": "invalid"}

    # 🚫 EVITA LOOP: se a mensagem for do próprio número, ignora
    if phone == AUTHORIZED_NUMBER:
        print("🔁 Ignorado: mensagem enviada pelo próprio bot (evitando loop).")
        return {"status": "self_message_ignored"}

    # --- continua normalmente ---
    if AUTHORIZED_NUMBER and phone != AUTHORIZED_NUMBER:
        print(f"🚫 Ignorando número não autorizado: {phone}")
        return {"status": "ignored"}

    # --- PEDIDO PARA ATENDENTE ---
    if any(word in text.lower() for word in ["atendente", "pessoa", "humano"]):
        send_message(phone, "Tudo bem 🌺! Já chamei nossa atendente pra falar com você!")
        send_message(AUTHORIZED_NUMBER, f"⚠️ Cliente {phone} pediu atendimento humano: '{text}'")
        return {"status": "human_mode_triggered"}

    # --- GERAÇÃO DE RESPOSTA COM GROQ ---
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
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
