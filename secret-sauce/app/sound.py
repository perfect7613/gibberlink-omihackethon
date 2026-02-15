"""ggwave encode/decode wrapper with chunking for 140-byte payload limit."""

import math
import struct

import ggwave

CHUNK_SIZE = 130  # leave room for 4-byte header (chunk_idx + total_chunks) + margin
PROTOCOL_ID = 1   # audible fastest
VOLUME = 20


def encode(payload: str, protocol_id: int = PROTOCOL_ID, volume: int = VOLUME) -> list[bytes]:
    """Encode a string into one or more ggwave waveforms.

    Returns a list of raw PCM waveform bytes (mono, 48kHz, float32).
    If payload > CHUNK_SIZE, it's split into numbered chunks.
    """
    data = payload.encode()
    if len(data) <= CHUNK_SIZE + 4:
        # Single chunk — no header needed
        inst = ggwave.init()
        try:
            waveform = ggwave.encode(payload, protocolId=protocol_id, volume=volume, instance=inst)
            return [waveform]
        finally:
            ggwave.free(inst)

    # Multi-chunk: prepend 2-byte index + 2-byte total
    total = math.ceil(len(data) / CHUNK_SIZE)
    waveforms = []
    inst = ggwave.init()
    try:
        for i in range(total):
            chunk = data[i * CHUNK_SIZE : (i + 1) * CHUNK_SIZE]
            header = struct.pack("BB", i, total)
            frame = header + chunk
            wf = ggwave.encode(frame.decode("latin-1"), protocolId=protocol_id, volume=volume, instance=inst)
            waveforms.append(wf)
    finally:
        ggwave.free(inst)
    return waveforms


def decode(waveform: bytes) -> str | None:
    """Decode a single ggwave waveform back to string. Returns None on failure."""
    inst = ggwave.init()
    try:
        result = ggwave.decode(inst, waveform)
        if result is None:
            return None
        if isinstance(result, bytes):
            return result.decode()
        return result
    finally:
        ggwave.free(inst)

