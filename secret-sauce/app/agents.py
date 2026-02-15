"""Vault 🔒 and Oracle 🔮 agent personas."""

import random


# --- Vault 🔒 ---

VAULT_LINES = [
    "Your secret is sealed in sound. No one shall hear its truth.",
    "I have encrypted your words into chirps only the worthy can decode.",
    "The vault is locked. Your message travels as noise to all but one.",
    "Sealed. Even the air forgets what it carried.",
    "Your whisper is now a cipher. Only Oracle can unravel it.",
]

# --- Oracle 🔮 ---

ORACLE_LINES = [
    "The chirp speaks to me... I see your secret clearly now.",
    "Ah, the sound reveals its hidden truth. I have decoded your message.",
    "The frequencies align... your secret emerges from the noise.",
    "I heard the whisper in the static. Your words are restored.",
    "The cipher unravels before me. Your secret is safe — and understood.",
]


def vault_response(original_text: str) -> str:
    """Generate an in-character Vault 🔒 response."""
    line = random.choice(VAULT_LINES)
    return f"🔒 Vault: {line}"


def oracle_response(decrypted_text: str) -> str:
    """Generate an in-character Oracle 🔮 response."""
    line = random.choice(ORACLE_LINES)
    return f"🔮 Oracle: {line}\n\n📝 Revealed: \"{decrypted_text}\""

