"""
TOM v3.0 - RL Feedback Event Models
Pydantic-Modelle für Feedback-Events basierend auf feedback_event.json Schema
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum


class AgentType(str, Enum):
    """Verfügbare Agent-Typen"""
    TOM = "TOM"
    TOM_V1 = "TOM_v1"
    TOM_V2 = "TOM_v2"


class ProfileType(str, Enum):
    """Verfügbare Kundenprofile"""
    KFZ = "kfz"
    IT = "it"
    SALES = "sales"
    SUPPORT = "support"
    GENERAL = "general"


class FeedbackSignals(BaseModel):
    """Feedback-Signale für RL-Training"""
    
    # Erforderliche Felder
    resolution: bool = Field(..., description="Ziel erreicht/Problem gelöst")
    
    # Optionale Felder
    user_rating: Optional[int] = Field(None, ge=1, le=5, description="Benutzerbewertung 1-5")
    barge_in_count: Optional[int] = Field(0, ge=0, le=10, description="Anzahl Barge-Ins")
    handover: Optional[bool] = Field(False, description="Übergabe an menschlichen Agent")
    duration_sec: Optional[float] = Field(0.0, ge=0.0, le=3600.0, description="Gesprächsdauer in Sekunden")
    repeats: Optional[int] = Field(0, ge=0, le=5, description="Anzahl Wiederholungen")
    escalation: Optional[bool] = Field(False, description="Eskalation erforderlich")
    satisfaction: Optional[float] = Field(0.0, ge=-1.0, le=1.0, description="Zufriedenheitswert -1 bis +1")
    
    @field_validator('user_rating')
    @classmethod
    def validate_user_rating(cls, v):
        if v is not None and (v < 1 or v > 5):
            raise ValueError('user_rating muss zwischen 1 und 5 liegen')
        return v


class FeedbackEvent(BaseModel):
    """Hauptmodell für Feedback-Events"""
    
    call_id: str = Field(..., min_length=1, max_length=100, description="Eindeutige Call-ID")
    ts: float = Field(..., ge=0, description="Unix-Timestamp mit Millisekunden")
    agent: AgentType = Field(..., description="Agent-Name")
    profile: ProfileType = Field(..., description="Kundenprofil/Use-Case")
    policy_variant: str = Field(..., pattern=r'^v[0-9]+[a-z]$', description="Policy-Variante")
    signals: FeedbackSignals = Field(..., description="Feedback-Signale")
    
    @field_validator('call_id')
    @classmethod
    def validate_call_id(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('call_id darf nicht leer sein')
        return v.strip()
    
    @field_validator('policy_variant')
    @classmethod
    def validate_policy_variant(cls, v):
        if not v or not v.startswith('v'):
            raise ValueError('policy_variant muss mit "v" beginnen')
        return v
    
    model_config = {
        "use_enum_values": True,
        "validate_assignment": True,
        "extra": "forbid"
    }


def create_feedback_event(
    call_id: str,
    agent: str = "TOM",
    profile: str = "general",
    policy_variant: str = "v1a",
    **signals
) -> FeedbackEvent:
    """
    Convenience-Funktion zum Erstellen von Feedback-Events
    
    Args:
        call_id: Eindeutige Call-ID
        agent: Agent-Name
        profile: Kundenprofil
        policy_variant: Policy-Variante
        **signals: Feedback-Signale
        
    Returns:
        Validiertes FeedbackEvent
    """
    return FeedbackEvent(
        call_id=call_id,
        ts=datetime.now().timestamp(),
        agent=agent,
        profile=profile,
        policy_variant=policy_variant,
        signals=FeedbackSignals(**signals)
    )


def anonymize_feedback_event(event: FeedbackEvent) -> Dict[str, Any]:
    """
    Anonymisiert ein Feedback-Event für sichere Speicherung
    
    Args:
        event: FeedbackEvent zum Anonymisieren
        
    Returns:
        Anonymisiertes Dictionary
    """
    # Entferne/maskiere PII
    anonymized = event.model_dump()
    
    # Call-ID anonymisieren (nur Hash behalten)
    import hashlib
    call_id_hash = hashlib.sha256(event.call_id.encode()).hexdigest()[:16]
    anonymized['call_id'] = f"anon_{call_id_hash}"
    
    # Timestamp auf Stunde runden für Anonymität
    anonymized['ts'] = int(event.ts // 3600) * 3600
    
    return anonymized
