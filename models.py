import logging
import asyncio
import aiohttp
from config import (
    GROQ_API_KEY, GEMINI_API_KEY, GROQ_MODELS, GEMINI_MODELS,
    ALL_MODELS, SYSTEM_PROMPT, TEMP, MAX_TOKENS
)

async def ai_reply(messages, lang="en"):
    """Try all models in priority order"""
    for model in ALL_MODELS:
        try:
            logging.getLogger("mediassistant").debug("Trying %s...", model)
            
            if model in GROQ_MODELS:
                reply = await call_groq(messages, model)
            elif model in GEMINI_MODELS:
                reply = await call_gemini(messages, model, lang)
            else:
                print(f"Unknown model: {model}")
                continue
                
            if reply:
                logging.getLogger("mediassistant").info("AI reply succeeded via %s", model)
                return reply
            else:
                logging.getLogger("mediassistant").warning("%s returned empty response", model)
                
        except asyncio.TimeoutError:
            logging.getLogger("mediassistant").warning("%s timed out", model)
        except Exception as e:
            logging.getLogger("mediassistant").warning("%s failed: %s", model, e)
            
        await asyncio.sleep(0.5)
    
    logging.getLogger("mediassistant").error("All AI models failed")
    return None

async def call_groq(messages, model):
    """Call Groq API with specific model"""
    try:
        groq_messages = []
        for msg in messages:
            groq_messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "messages": groq_messages,
                    "temperature": TEMP,
                    "max_tokens": MAX_TOKENS
                },
                timeout=aiohttp.ClientTimeout(total=15)
            ) as response:
                
                if response.status == 200:
                    data = await response.json()
                    reply = data["choices"][0]["message"]["content"].strip()
                    logging.getLogger("mediassistant").debug("Groq (%s): %s...", model, reply[:50])
                    return reply
                else:
                    error_text = await response.text()
                    raise Exception(f"Groq API error {response.status}: {error_text}")
                    
    except Exception as e:
        raise

async def call_gemini(messages, model, lang):
    """Call Gemini API with specific model"""
    try:
        prompt_parts = []
                 
        for msg in messages:
            if msg["role"] == "system":
                prompt_parts.append(f"[System instructions: {msg['content']}]")
            elif msg["role"] == "user":
                prompt_parts.append(f"User: {msg['content']}")
            elif msg["role"] == "assistant":
                prompt_parts.append(f"Assistant: {msg['content']}")
        
        full_prompt = "\n".join(prompt_parts)
        if not full_prompt.endswith("Assistant:"):
            full_prompt += "\n\nAssistant:"
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}",
                headers={"Content-Type": "application/json"},
                json={
                    "contents": [{"parts": [{"text": full_prompt}]}],
                    "generationConfig": {
                        "temperature": TEMP,
                        "maxOutputTokens": MAX_TOKENS,
                        "stopSequences": []
                    }
                },
                timeout=aiohttp.ClientTimeout(total=15)
            ) as response:
                
                if response.status == 200:
                    data = await response.json()
                    reply = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                    
                    if reply.startswith("Assistant:"):
                        reply = reply[10:].strip()
                    
                    logging.getLogger("mediassistant").debug("Gemini (%s): %s...", model, reply[:50])
                    return reply
                else:
                    error_text = await response.text()
                    raise Exception(f"Gemini API error {response.status}: {error_text}")
                    
    except Exception as e:
        raise
