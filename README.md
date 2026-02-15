# 🔐 Secret Sauce — Encrypted Voice Notes Over Sound

**Built for the Omi Hackathon**

Secret Sauce is a private communication layer for [Omi](https://omi.me) wearable devices. It transmits encrypted voice notes and tasks between two Omi devices using **data-over-sound** — no Bluetooth, no Wi-Fi, no pairing. Just a speaker, a microphone, and a shared encryption key.

Two AI agent personas — **Vault 🔒** (encrypts) and **Oracle 🔮** (decrypts) — manage the pipeline and store results back to each device's Omi memory and task list.

---

## How It Works

```
Device A (Vault 🔒)                          Device B (Oracle 🔮)
─────────────────                             ─────────────────
User speaks into Omi →
  Omi transcribes →
    Webhook fires to server →
      AES-256-GCM encrypt →
        ggwave encode →
          Chirp plays on
            Phone A speaker ~~~sound~~~>  Phone B mic captures
                                            ggwave decode →
                                              AES-256-GCM decrypt →
                                                Reveal plaintext →
                                                  Store to Omi memory
                                                  (or create task on Device B)
```

The encrypted payload travels through the air as an audible chirp. Anyone can *hear* it — but without the AES-256 key, it's meaningless noise.

---

## Core Features

### 🔐 End-to-End Encrypted Voice Notes
- **AES-256-GCM** — authenticated encryption with a random 12-byte nonce per message
- Tamper-proof: any modification to the ciphertext causes decryption to fail
- Only devices holding the shared key can decode

### 📡 Data-over-Sound (ggwave)
- Encrypted payloads encoded as audio chirps using [ggwave](https://github.com/ggerganov/ggwave)
- 48 kHz, audible-fast protocol, up to 140 bytes per chirp
- Multi-chunk support for longer payloads (130-byte chunks with 4-byte headers)
- No radio hardware needed — works with any speaker + microphone

### 📋 Task Sharing via Chirp
- Type a task on Device A → encrypted with `TASK:` prefix → chirp plays
- Device B mic captures → server decodes → detects `TASK:` prefix → creates action item on Device B via **Omi Developer API**
- Tasks appear natively in the Omi app on the receiving device
- Forward existing tasks between devices via API with one tap

### 🧠 Omi Memory & Developer API Integration
| API | What It Does |
|-----|-------------|
| **Integration API** (`/v2/integrations/{app_id}/user/memories`) | Stores encrypted + decrypted versions as memories on each device's Omi |
| **Developer API** (`/v1/dev/user/action-items`) | Creates, retrieves, and forwards tasks between devices |
| **Webhook** (`/vault/memory-created`) | Triggered when Omi creates a memory from speech — kicks off the encryption pipeline |

### 🤖 Two Agent Personas
- **Vault 🔒** — cryptic, secretive. Seals and encrypts messages.
- **Oracle 🔮** — wise, revealing. Decodes and unveils the hidden truth.

### 🖥️ Web Dashboard
- Chirp player — play the latest encrypted chirp
- Oracle Listener — Phone B's browser mic captures chirps (6-second recording via Web Audio API at 48 kHz)
- Task panel — seal tasks as chirps, view both devices' task lists, forward tasks
- Conversation log — live feed of Vault/Oracle exchanges

---

## Why Sound Is Better Than Bluetooth

This is not a gimmick — data-over-sound has fundamental security and usability advantages over Bluetooth for local, private communication.

### 🔌 Zero Setup, Zero Pairing

| | Data-over-Sound | Bluetooth |
|---|---|---|
| **Pairing** | None. Play sound → mic captures → done. | Requires device discovery, pairing handshake, PIN confirmation |
| **Setup time** | Instant | 30–60 seconds, fails often |
| **Cross-platform** | Any device with a speaker and mic | Both devices must support the same BT profile |
| **Driver/stack** | None needed | Requires BLE/Classic BT stack, OS permissions, driver compatibility |

Bluetooth pairing is the #1 source of friction in device-to-device communication. Sound eliminates it entirely.

### 🛡️ Physical Security by Design

| | Data-over-Sound | Bluetooth |
|---|---|---|
| **Range** | You control it — turn the volume down for a 1-meter radius | 10–30m range, bleeds through walls |
| **Interception** | Requires physical presence in the room | Can be sniffed from a parked car outside the building |
| **Spoofing** | Extremely difficult — requires being in audible range | BT relay attacks are well-documented (e.g., car key relay theft) |
| **Visibility** | You literally hear when data is transmitted | Silent, invisible — you never know when BT is leaking |

**The key insight: sound doesn't travel through walls.** Bluetooth does. With sound, proximity *is* the security boundary. If you can hear the chirp, you're trusted. If you can't, you're excluded. No firewall rules, no access control lists — physics handles it.

### 🔒 Air-Gap Capable

Sound works on devices with **zero network connectivity**. No Wi-Fi, no cellular, no Bluetooth radio needed. Just a speaker and a mic. This makes it viable for:
- Classified environments where radios are prohibited
- Faraday cages and RF-shielded rooms
- Legacy devices with no wireless hardware
- Scenarios where network infrastructure is compromised

Bluetooth is fundamentally a radio protocol — it cannot function without radio hardware and is inherently susceptible to RF-based attacks.

### 👁️ Full Auditability

Every transmission is **audible**. You hear the chirp. You know exactly when data left your device and when it arrived. There's no silent background sync, no hidden data exfiltration, no ambient Bluetooth beacon broadcasting your presence.

With Bluetooth, your device constantly advertises itself, responds to scans, and maintains connections — all silently, all the time.

---

## How It Improves Security

### Compared to Cloud-Based Messaging

Traditional messaging (WhatsApp, Telegram, iMessage) routes everything through servers — even with end-to-end encryption, metadata (who talked to whom, when, how often) is exposed. Secret Sauce's sound-based channel has **zero metadata leakage**:

- **No server in the communication path** — the chirp goes through air, not the internet
- **No contact lists, no phone numbers, no accounts** — you just need to be in the same room
- **No persistent connection** — the channel exists only for the duration of the chirp
- **Forward secrecy through physical ephemerality** — sound dissipates instantly, leaving no trace

The server is only involved for Omi webhook processing and memory/task storage — the actual secret payload travels exclusively through sound.

### Compared to Bluetooth File Transfer

| Threat | Bluetooth | Secret Sauce |
|--------|-----------|-------------|
| Man-in-the-middle | Possible during pairing (MITM attacks on BT are well-documented) | Requires physical presence in the room — you'd see the attacker |
| Replay attacks | BT packets can be captured and replayed | AES-GCM with unique 12-byte nonce per message — replayed ciphertext produces different plaintext |
| Eavesdropping | RF signals pass through walls; directional antennas extend range to 100m+ | Sound attenuates rapidly; walls, doors, and distance are natural barriers |
| Device tracking | BT MAC addresses enable persistent tracking | No device identifiers are transmitted — the chirp contains only encrypted payload |
| Relay attacks | Proven in car key theft, access badge cloning | Sound cannot be silently relayed without audible detection |

### The Encryption Layer

Even if someone records the chirp audio, they get only the AES-256-GCM ciphertext. Breaking AES-256 requires ~2^256 operations — more energy than the sun will produce in its lifetime. The chirp is essentially a one-time physical broadcast of an unbreakable ciphertext.

---

## Omi-to-Omi Communication — The Vision

Two Omi devices in the same room become a **private encrypted channel** — no internet, no cloud, no pairing required.

```
   Omi A (Alice)                           Omi B (Bob)
      │                                      │
  Alice speaks →                          Bob speaks →
  Omi transcribes →                       Omi transcribes →
  Vault encrypts →                        Vault encrypts →
  Phone A plays chirp ~~~>            Phone B plays chirp
  Phone A mic decodes <~~~            Phone B mic decodes
      │                                      │
  Oracle reveals Bob's message         Oracle reveals Alice's message
  + stored in Alice's Omi memory       + stored in Bob's Omi memory
  + tasks sync bidirectionally         + tasks sync bidirectionally
```

### What This Enables

**1. Shared Encrypted Memories**
Alice speaks → her words land in Bob's Omi memory (encrypted in transit, decrypted on arrival). Bob's notes land in Alice's. Both have the full conversation stored in their personal Omi, tagged and searchable.

**2. Cross-Device Task Assignment**
"Hey Bob, review the quarterly budget" → encrypted chirp → task appears on Bob's Omi instantly. No app switching, no typing — just speak and it arrives.

**3. Paired Conversations**
Two Omis in the same room create a linked conversation thread. Each message is tagged by source device. The conversation log shows the full back-and-forth — a private, encrypted dialogue stored in both users' memories.

**4. Group Mode**
Multiple Omis in a room share the same encryption key. One chirp, everyone decodes. An encrypted group chat transmitted through sound — like a conference call, but private by physics.

**5. Proximity-Based Trust**
No friend requests. No QR codes. No phone numbers. If you're close enough to hear the chirp, you're in the conversation. Walk away, and you're out. The room is the access control.

### Current Status

| Feature | Status |
|---------|--------|
| A → B encrypted voice notes via chirp | ✅ Working |
| A → B task assignment via chirp | ✅ Working |
| A → B memory storage (Omi Integration API) | ✅ Working |
| Task list viewing & forwarding per device | ✅ Working |
| B → A reverse direction | 🔜 Same architecture, second Vault+Oracle pair |
| Auto-pairing handshake chirp | 🔜 Devices discover each other via sound |
| Group mode (N devices, shared key) | 🔜 One chirp, all decode |
| Conversation threading by source device | 🔜 Tag messages with Omi device ID |

---

## Architecture

```
secret-sauce/
├── app/
│   ├── crypto.py      # AES-256-GCM encrypt/decrypt
│   ├── sound.py       # ggwave encode/decode with chunking
│   ├── agents.py      # Vault 🔒 + Oracle 🔮 personas
│   ├── models.py      # Pydantic models (MemoryPayload, AgentMessage)
│   ├── omi.py         # Omi API client (memories + action items)
│   └── main.py        # FastAPI server — all endpoints
├── web/
│   └── index.html     # Dashboard (chirp player, mic listener, tasks, conversation log)
├── .env               # AES key + Omi API keys + Developer API keys
└── requirements.txt
```

### API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/health` | Health check |
| `GET` | `/` | Serve web dashboard |
| `POST` | `/vault/memory-created?uid=` | Omi webhook — encrypt memory → chirp |
| `POST` | `/vault/send-task` | Encrypt task → chirp WAV |
| `GET` | `/vault/latest-chirp` | Serve latest chirp as WAV |
| `POST` | `/oracle/decode?uid=` | Decrypt an encrypted token |
| `POST` | `/oracle/listen-audio?uid=` | Receive raw PCM from browser mic → decode chirp |
| `POST` | `/realtime-processor` | Omi real-time transcript webhook |
| `GET` | `/conversation` | Conversation log |
| `GET` | `/action-items/{device}` | Fetch tasks for device_a or device_b |
| `POST` | `/action-items/forward` | Forward existing task between devices |

### Tech Stack

- **Python 3.10** + **FastAPI** — backend
- **ggwave** — data-over-sound encoding/decoding (built from source with Cython)
- **cryptography** (AES-256-GCM) — authenticated encryption
- **Omi Integration API** — memory storage
- **Omi Developer API** — action items / tasks
- **Web Audio API** — browser mic capture at 48 kHz
- **ngrok** — HTTPS tunnel for Omi webhooks
