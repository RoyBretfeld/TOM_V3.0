"""
Pydantic-Schemas für TOM v3.0 WebSocket Events
Validierung aller eingehenden und ausgehenden Nachrichten
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Union, Literal
from datetime import datetime


class AudioChunk(BaseModel):
    """Audio-Chunk von Client"""
    type: Literal["audio_chunk"] = "audio_chunk"
    ts: int = Field(..., description="Timestamp in ms")
    data: str = Field(..., description="Base64-kodierte PCM16-Daten")
    format: Literal["pcm16_16k"] = "pcm16_16k"
    
    @validator('data')
    def validate_base64(cls, v):
        import base64
        try:
            base64.b64decode(v)
            return v
        except Exception:
            raise ValueError('Invalid base64 data')


class STTPartial(BaseModel):
    """STT Partial-Ergebnis"""
    type: Literal["stt_partial"] = "stt_partial"
    text: str = Field(..., min_length=1, max_length=1000)
    ts: int = Field(..., description="Timestamp in ms")


class STTFinal(BaseModel):
    """STT Final-Ergebnis"""
    type: Literal["stt_final"] = "stt_final"
    text: str = Field(..., min_length=1, max_length=2000)
    ts: int = Field(..., description="Timestamp in ms")


class LLMToken(BaseModel):
    """LLM Token-Stream"""
    type: Literal["llm_token"] = "llm_token"
    text: str = Field(..., min_length=1, max_length=100)
    ts: int = Field(..., description="Timestamp in ms")


class TTSAudio(BaseModel):
    """TTS Audio-Frame"""
    type: Literal["tts_audio"] = "tts_audio"
    codec: Literal["pcm16"] = "pcm16"
    bytes: str = Field(..., description="Base64-kodierte Audio-Daten")
    ts: int = Field(..., description="Timestamp in ms")
    
    @validator('bytes')
    def validate_audio_base64(cls, v):
        import base64
        try:
            base64.b64decode(v)
            return v
        except Exception:
            raise ValueError('Invalid base64 audio data')


class TurnEnd(BaseModel):
    """Turn-Ende Signal"""
    type: Literal["turn_end"] = "turn_end"
    ts: int = Field(..., description="Timestamp in ms")


class Ping(BaseModel):
    """Ping-Nachricht"""
    type: Literal["ping"] = "ping"
    ts: int = Field(..., description="Timestamp in ms")


class Pong(BaseModel):
    """Pong-Antwort"""
    type: Literal["pong"] = "pong"
    ts: int = Field(..., description="Timestamp in ms")


class BargeIn(BaseModel):
    """Barge-In Signal"""
    type: Literal["barge_in"] = "barge_in"
    ts: int = Field(..., description="Timestamp in ms")


class Stop(BaseModel):
    """Stop-Signal"""
    type: Literal["stop"] = "stop"
    ts: int = Field(..., description="Timestamp in ms")


# Union aller möglichen Event-Typen
WSEvent = Union[
    AudioChunk,
    STTPartial,
    STTFinal,
    LLMToken,
    TTSAudio,
    TurnEnd,
    Ping,
    Pong,
    BargeIn,
    Stop
]


def validate_event(data: dict) -> WSEvent:
    """
    Validiert ein Event-Dictionary gegen die entsprechenden Schemas
    
    Args:
        data: Dictionary mit Event-Daten
        
    Returns:
        Validiertes Pydantic-Model
        
    Raises:
        ValueError: Bei ungültigen Event-Daten
    """
    if not isinstance(data, dict):
        raise ValueError("Event muss ein Dictionary sein")
    
    event_type = data.get('type')
    if not event_type:
        raise ValueError("Event muss ein 'type' Feld haben")
    
    # Mapping von Event-Typen zu Pydantic-Modellen
    event_models = {
        'audio_chunk': AudioChunk,
        'stt_partial': STTPartial,
        'stt_final': STTFinal,
        'llm_token': LLMToken,
        'tts_audio': TTSAudio,
        'turn_end': TurnEnd,
        'ping': Ping,
        'pong': Pong,
        'barge_in': BargeIn,
        'stop': Stop
    }
    
    if event_type not in event_models:
        raise ValueError(f"Unbekannter Event-Typ: {event_type}")
    
    try:
        model_class = event_models[event_type]
        return model_class(**data)
    except Exception as e:
        raise ValueError(f"Validierungsfehler für {event_type}: {str(e)}")


def create_mock_response(event_type: str, **kwargs) -> dict:
    """
    Erstellt Mock-Responses für Tests und Entwicklung
    
    Args:
        event_type: Typ des Events
        **kwargs: Zusätzliche Felder
        
    Returns:
        Dictionary mit Event-Daten
    """
    timestamp = kwargs.get('ts', int(datetime.now().timestamp() * 1000))
    
    mock_responses = {
        'stt_final': {
            'type': 'stt_final',
            'text': kwargs.get('text', 'Test erkannt'),
            'ts': timestamp
        },
        'llm_token': {
            'type': 'llm_token',
            'text': kwargs.get('text', 'Hallo, ich bin TOM.'),
            'ts': timestamp
        },
        'turn_end': {
            'type': 'turn_end',
            'ts': timestamp
        },
        'tts_audio': {
            'type': 'tts_audio',
            'codec': 'pcm16',
            'bytes': kwargs.get('bytes', 'UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQAAAAA='),  # 200ms Stille
            'ts': timestamp
        },
        'pong': {
            'type': 'pong',
            'ts': timestamp
        }
    }
    
    if event_type not in mock_responses:
        raise ValueError(f"Kein Mock für Event-Typ: {event_type}")
    
    return mock_responses[event_type]
