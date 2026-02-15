"""Secret Sauce — FastAPI backend for two-agent encrypted voice notes."""

import base64
import io
import os
import struct
import wave
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Query, Request
from fastapi.responses import FileResponse, JSONResponse, Response

from . import agents, crypto, omi, sound
from .models import AgentMessage, MemoryPayload

load_dotenv()

AES_KEY = os.environ.get("AES_KEY", crypto.generate_key())

app = FastAPI(title="Secret Sauce 🔐", version="0.1.0")

# In-memory state
conversation: list[dict] = []
latest_chirp_wav: bytes | None = None  # raw WAV bytes for serving

TASK_PREFIX = "TASK:"

WEB_DIR = Path(__file__).resolve().parent.parent / "web"


def _build_chirp_wav(payload: str) -> tuple[bytes, str, list]:
    """Encrypt payload → ggwave encode → WAV bytes. Returns (wav_bytes, encrypted, waveforms)."""
    encrypted = crypto.encrypt(payload, AES_KEY)
    waveforms = sound.encode(encrypted)
    pcm_float = struct.unpack(f"{len(waveforms[0]) // 4}f", waveforms[0])
    pcm_int16 = struct.pack(f"{len(pcm_float)}h", *[max(-32768, min(32767, int(s * 32767))) for s in pcm_float])
    wav_buf = io.BytesIO()
    with wave.open(wav_buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(48000)
        wf.writeframes(pcm_int16)
    return wav_buf.getvalue(), encrypted, waveforms


@app.get("/health")
async def health():
    return {"status": "ok", "agents": ["vault 🔒", "oracle 🔮"], "key_set": bool(os.environ.get("AES_KEY"))}


@app.post("/vault/memory-created")
async def vault_memory_created(request: Request, uid: str = Query("")):
    """Omi webhook: memory created → encrypt → encode to chirp → store."""
    global latest_chirp_wav

    body = await request.json()

    # Handle both payload formats from Omi:
    #   Direct: {id, transcript_segments, ...}
    #   Wrapped: {conversation: {id, transcript_segments, ...}}
    mem_data = body.get("conversation", body) if isinstance(body, dict) else body
    memory = MemoryPayload(**mem_data)

    if memory.discarded or not memory.full_text:
        return {"message": "⏭️ Skipped (empty or discarded)"}

    text = memory.full_text

    # 1-3. Encrypt → ggwave encode → WAV
    latest_chirp_wav, encrypted, waveforms = _build_chirp_wav(text)
    wav_b64 = base64.b64encode(latest_chirp_wav).decode()

    # 4. Agent persona response
    persona_line = agents.vault_response(text)

    # 5. Store encrypted version back to Omi (best-effort)
    vault_app_id, vault_api_key = omi.get_vault_config()
    if vault_app_id and vault_api_key and uid:
        try:
            await omi.store_memory(
                vault_app_id, uid, vault_api_key,
                f"🔒 Encrypted secret: {encrypted[:80]}...",
                tags=["secret-sauce", "encrypted"],
            )
        except Exception:
            pass  # best-effort

    # 6. Create action item on Device B (best-effort)
    _, dev_b_key = omi.get_dev_keys()
    if dev_b_key:
        try:
            await omi.create_action_item(
                dev_b_key,
                f"🔒 New encrypted secret from Vault — open dashboard to decode",
            )
        except Exception:
            pass

    # 7. Log to conversation
    msg = AgentMessage(
        agent="vault",
        persona_line=persona_line,
        original_text=text,
        encrypted=encrypted,
    )
    conversation.append(msg.model_dump())

    return {
        "message": f"🔒 Secret sealed! Open the dashboard to hear the chirp.",
        "status": "sealed",
        "persona": persona_line,
        "encrypted": encrypted,
        "chirp_wav_b64": wav_b64,
        "chunks": len(waveforms),
    }


@app.post("/oracle/decode")
async def oracle_decode(request: Request, uid: str = Query("")):
    """Receive encrypted token (from chirp decode) → decrypt → reveal."""
    body = await request.json()
    encrypted = body.get("encrypted", "")

    if not encrypted:
        return JSONResponse(status_code=400, content={"error": "missing 'encrypted' field"})

    try:
        decrypted = crypto.decrypt(encrypted, AES_KEY)
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": f"decryption failed: {e}"})

    persona_line = agents.oracle_response(decrypted)

    # Store decrypted version back to Omi (best-effort)
    oracle_app_id, oracle_api_key = omi.get_oracle_config()
    if oracle_app_id and oracle_api_key and uid:
        try:
            await omi.store_memory(
                oracle_app_id, uid, oracle_api_key,
                f"🔮 Revealed secret: {decrypted}",
                tags=["secret-sauce", "decrypted"],
            )
        except Exception:
            pass

    msg = AgentMessage(
        agent="oracle",
        persona_line=persona_line,
        decrypted=decrypted,
        encrypted=encrypted,
    )
    conversation.append(msg.model_dump())

    return {"status": "revealed", "persona": persona_line, "decrypted": decrypted}


@app.post("/realtime-processor")
async def realtime_processor(request: Request, uid: str = Query(""), session_id: str = Query("")):
    """Omi real-time transcript processor (Oracle listens)."""
    segments = await request.json()
    # For now, acknowledge — real-time decode happens via BLE listener
    return {"status": "listening", "segments_received": len(segments) if isinstance(segments, list) else 0}


@app.get("/conversation")
async def get_conversation():
    """Return the conversation log between Vault and Oracle."""
    return {"conversation": conversation}


@app.get("/vault/latest-chirp")
async def get_latest_chirp():
    """Serve the latest chirp as a downloadable WAV file."""
    if not latest_chirp_wav:
        return JSONResponse(status_code=404, content={"error": "no chirp yet"})
    return Response(content=latest_chirp_wav, media_type="audio/wav",
                    headers={"Content-Disposition": "inline; filename=chirp.wav"})


@app.post("/oracle/listen-audio")
async def oracle_listen_audio(request: Request, uid: str = Query("")):
    """Receive raw float32 PCM (48kHz mono) from browser mic → ggwave decode → decrypt → store."""
    audio_bytes = await request.body()

    if len(audio_bytes) < 4000:
        return JSONResponse(status_code=400, content={"error": "audio too short"})

    # Try ggwave decode on raw float32 PCM
    decoded = sound.decode(audio_bytes)

    if not decoded:
        return {"status": "no_chirp", "message": "🔮 No chirp detected — try again closer to the speaker"}

    # decoded should be the encrypted token
    try:
        decrypted = crypto.decrypt(decoded, AES_KEY)
    except Exception as e:
        return JSONResponse(status_code=400, content={
            "error": f"Chirp decoded but decryption failed: {e}",
            "raw_decoded": decoded,
        })

    # Check if this is a task or a regular secret
    is_task = decrypted.startswith(TASK_PREFIX)
    content = decrypted[len(TASK_PREFIX):] if is_task else decrypted

    persona_line = agents.oracle_response(f"[TASK] {content}" if is_task else content)

    _, dev_b_key = omi.get_dev_keys()

    if is_task:
        # Create action item on Device B
        if dev_b_key:
            try:
                await omi.create_action_item(dev_b_key, content)
            except Exception:
                pass

        msg = AgentMessage(
            agent="oracle",
            persona_line=persona_line,
            decrypted=f"📋 Task received: {content}",
            encrypted=decoded,
        )
        conversation.append(msg.model_dump())

        return {
            "message": f"🔮 Task received via chirp! Created on Device B.",
            "status": "task_received",
            "persona": persona_line,
            "decrypted": content,
            "is_task": True,
            "encrypted": decoded,
        }
    else:
        # Regular secret — existing flow
        oracle_app_id, oracle_api_key = omi.get_oracle_config()
        if oracle_app_id and oracle_api_key and uid:
            try:
                await omi.store_memory(
                    oracle_app_id, uid, oracle_api_key,
                    f"🔮 Revealed secret: {content}",
                    tags=["secret-sauce", "decrypted"],
                )
            except Exception:
                pass

        msg = AgentMessage(
            agent="oracle",
            persona_line=persona_line,
            decrypted=content,
            encrypted=decoded,
        )
        conversation.append(msg.model_dump())

        return {
            "message": f"🔮 Secret revealed! Check the dashboard.",
            "status": "revealed",
            "persona": persona_line,
            "decrypted": content,
            "is_task": False,
            "encrypted": decoded,
        }


# --- Action Items endpoints ---

@app.get("/action-items/{device}")
async def get_action_items(device: str):
    """Fetch action items for device_a or device_b."""
    dev_a_key, dev_b_key = omi.get_dev_keys()
    key = dev_a_key if device == "device_a" else dev_b_key
    if not key:
        return JSONResponse(status_code=400, content={"error": f"No API key for {device}"})
    try:
        items = await omi.get_action_items(key)
        return {"device": device, "action_items": items}
    except Exception as e:
        return JSONResponse(status_code=502, content={"error": str(e)})


@app.post("/vault/send-task")
async def vault_send_task(request: Request):
    """Encrypt a task description as TASK:... → generate chirp WAV.

    Phone A plays the chirp → Phone B mic captures → Oracle decodes → creates action item.
    Body: {"description": "..."}
    """
    global latest_chirp_wav

    body = await request.json()
    description = body.get("description", "")
    if not description:
        return JSONResponse(status_code=400, content={"error": "missing description"})

    # Prefix with TASK: so Oracle knows it's an action item
    payload = f"{TASK_PREFIX}{description}"
    latest_chirp_wav, encrypted, waveforms = _build_chirp_wav(payload)
    wav_b64 = base64.b64encode(latest_chirp_wav).decode()

    persona_line = agents.vault_response(f"[TASK] {description}")

    msg = AgentMessage(
        agent="vault",
        persona_line=persona_line,
        original_text=f"📋 Task: {description}",
        encrypted=encrypted,
    )
    conversation.append(msg.model_dump())

    return {
        "message": "🔒 Task encrypted into chirp! Play it for Device B.",
        "status": "task_sealed",
        "encrypted": encrypted,
        "chirp_wav_b64": wav_b64,
        "chunks": len(waveforms),
    }


@app.get("/")
async def dashboard():
    """Serve the test dashboard HTML page."""
    html_path = WEB_DIR / "index.html"
    if not html_path.exists():
        return JSONResponse(status_code=404, content={"error": "web/index.html not found"})
    return FileResponse(html_path, media_type="text/html")

