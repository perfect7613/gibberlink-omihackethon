"""Pydantic models for Omi webhook payloads and agent messages."""

from __future__ import annotations

from pydantic import BaseModel, Field


# --- Omi Webhook Payloads ---


class TranscriptSegment(BaseModel):
    text: str
    speaker: str = "SPEAKER_00"
    speaker_id: int = Field(0, alias="speakerId")
    is_user: bool = False
    start: float = 0.0
    end: float = 0.0

    model_config = {"populate_by_name": True}


class ActionItem(BaseModel):
    description: str
    completed: bool = False


class Structured(BaseModel):
    title: str = ""
    overview: str = ""
    emoji: str = "🔐"
    category: str = "personal"
    action_items: list[ActionItem] = []
    events: list = []


class AppResponse(BaseModel):
    app_id: str
    content: str


class MemoryPayload(BaseModel):
    """Payload sent by Omi on memory-created webhook."""
    id: int | str = 0
    created_at: str = ""
    started_at: str = ""
    finished_at: str = ""
    transcript_segments: list[TranscriptSegment] = []
    photos: list = []
    structured: Structured = Structured()
    apps_response: list[AppResponse] = []
    discarded: bool = False

    @property
    def full_text(self) -> str:
        """Join all transcript segments into a single string."""
        return " ".join(seg.text for seg in self.transcript_segments).strip()


# --- Agent Messages ---


class AgentMessage(BaseModel):
    agent: str  # "vault" or "oracle"
    persona_line: str
    original_text: str = ""
    encrypted: str = ""
    decrypted: str = ""

