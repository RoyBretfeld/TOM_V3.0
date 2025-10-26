"""
TOM v3.0 - RealtimeSession Interface
Einheitliches Interface für Local- und Provider-Sessions
"""

from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional
from enum import Enum


class RealtimeBackend(str, Enum):
    """Verfügbare Realtime-Backends"""
    LOCAL = "local"
    PROVIDER = "provider"


class RealtimeSession(ABC):
    """Abstraktes Interface für Realtime-Sessions"""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.is_connected = False
        
    @abstractmethod
    async def open(self) -> None:
        """Session öffnen"""
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Session schließen"""
        pass
    
    @abstractmethod
    async def send_audio(self, audio_bytes: bytes, timestamp: float) -> None:
        """Audio an Session senden"""
        pass
    
    @abstractmethod
    async def recv_events(self) -> AsyncIterator[dict]:
        """Events von Session empfangen"""
        pass
    
    @abstractmethod
    async def cancel(self) -> None:
        """Laufende Antwort abbrechen (Barge-In)"""
        pass
    
    @abstractmethod
    async def send_event(self, event: dict) -> None:
        """Steuerkommando an Session senden"""
        pass

