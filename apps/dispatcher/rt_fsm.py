"""
TOM v3.0 - Dispatcher FSM mit RL Policy Router
FSM-basierte Anrufsteuerung mit Reinforcement Learning Policy-Auswahl
"""

import asyncio
import logging
from enum import Enum
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
import json

from apps.rl import select_policy, update_policy_reward, calc_reward, PolicyVariant


class CallState(Enum):
    """Zustände der FSM"""
    IDLE = "idle"
    RINGING = "ringing"
    CONNECTED = "connected"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"
    BARRED = "barred"
    ENDED = "ended"


class CallEvent(Enum):
    """Events für State-Transitions"""
    INCOMING_CALL = "incoming_call"
    CALL_ANSWERED = "call_answered"
    CALL_ENDED = "call_ended"
    AUDIO_START = "audio_start"
    AUDIO_STOP = "audio_stop"
    BARGE_IN = "barge_in"
    TIMEOUT = "timeout"
    ERROR = "error"


@dataclass
class CallContext:
    """Kontext für Policy-Auswahl"""
    call_id: str
    profile: str = "general"
    time_of_day: str = "business"
    call_duration: float = 0.0
    barge_in_count: int = 0
    repeat_count: int = 0
    user_rating: Optional[int] = None
    resolution: bool = False
    handover: bool = False


@dataclass
class CallSession:
    """Session-Daten für einen Call"""
    call_id: str
    state: CallState = CallState.IDLE
    context: CallContext = field(default_factory=lambda: CallContext(""))
    policy_variant: str = "v1a"
    start_time: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    events: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert Session zu Dictionary für Serialisierung"""
        return {
            "call_id": self.call_id,
            "state": self.state.value,
            "policy_variant": self.policy_variant,
            "context": {
                "profile": self.context.profile,
                "time_of_day": self.context.time_of_day,
                "call_duration": self.context.call_duration,
                "barge_in_count": self.context.barge_in_count,
                "repeat_count": self.context.repeat_count,
                "user_rating": self.context.user_rating,
                "resolution": self.context.resolution,
                "handover": self.context.handover
            },
            "start_time": self.start_time.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "events": self.events
        }


class RealtimeFSM:
    """FSM für Realtime-Anrufsteuerung mit RL Policy Router"""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.RealtimeFSM")
        self.sessions: Dict[str, CallSession] = {}
        
        # State-Transition-Matrix
        self.transitions = {
            CallState.IDLE: {
                CallEvent.INCOMING_CALL: CallState.RINGING
            },
            CallState.RINGING: {
                CallEvent.CALL_ANSWERED: CallState.CONNECTED,
                CallEvent.CALL_ENDED: CallState.ENDED,
                CallEvent.TIMEOUT: CallState.ENDED
            },
            CallState.CONNECTED: {
                CallEvent.AUDIO_START: CallState.LISTENING,
                CallEvent.CALL_ENDED: CallState.ENDED,
                CallEvent.ERROR: CallState.ENDED
            },
            CallState.LISTENING: {
                CallEvent.AUDIO_STOP: CallState.THINKING,
                CallEvent.BARGE_IN: CallState.LISTENING,
                CallEvent.CALL_ENDED: CallState.ENDED,
                CallEvent.ERROR: CallState.ENDED
            },
            CallState.THINKING: {
                CallEvent.AUDIO_START: CallState.SPEAKING,
                CallEvent.CALL_ENDED: CallState.ENDED,
                CallEvent.ERROR: CallState.ENDED
            },
            CallState.SPEAKING: {
                CallEvent.AUDIO_STOP: CallState.LISTENING,
                CallEvent.BARGE_IN: CallState.LISTENING,
                CallEvent.CALL_ENDED: CallState.ENDED,
                CallEvent.ERROR: CallState.ENDED
            },
            CallState.BARRED: {
                CallEvent.CALL_ENDED: CallState.ENDED,
                CallEvent.ERROR: CallState.ENDED
            },
            CallState.ENDED: {}  # Terminal state
        }
    
    async def create_session(self, call_id: str, profile: str = "general") -> CallSession:
        """
        Erstellt eine neue Call-Session mit Policy-Auswahl
        
        Args:
            call_id: Eindeutige Call-ID
            profile: Kundenprofil für Kontext
            
        Returns:
            Neue CallSession
        """
        # Erstelle Kontext für Policy-Auswahl
        context = CallContext(
            call_id=call_id,
            profile=profile,
            time_of_day=self._get_time_of_day()
        )
        
        # Wähle Policy-Variante basierend auf Kontext
        policy_variant = await self._select_policy(context)
        
        # Erstelle Session
        session = CallSession(
            call_id=call_id,
            context=context,
            policy_variant=policy_variant
        )
        
        self.sessions[call_id] = session
        
        self.logger.info(f"Session erstellt: {call_id} mit Policy {policy_variant}")
        return session
    
    async def handle_event(self, call_id: str, event: CallEvent, data: Optional[Dict[str, Any]] = None) -> bool:
        """
        Behandelt ein Event und führt State-Transition durch
        
        Args:
            call_id: Call-ID
            event: Event-Typ
            data: Event-Daten (optional)
            
        Returns:
            True wenn Transition erfolgreich
        """
        if call_id not in self.sessions:
            self.logger.error(f"Session nicht gefunden: {call_id}")
            return False
        
        session = self.sessions[call_id]
        current_state = session.state
        
        # Prüfe ob Transition erlaubt ist
        if event not in self.transitions.get(current_state, {}):
            self.logger.warning(f"Ungültige Transition: {current_state} -> {event}")
            return False
        
        # Führe Transition durch
        new_state = self.transitions[current_state][event]
        session.state = new_state
        session.last_activity = datetime.now()
        
        # Logge Event
        event_data = {
            "event": event.value,
            "from_state": current_state.value,
            "to_state": new_state.value,
            "timestamp": datetime.now().isoformat(),
            "data": data or {}
        }
        session.events.append(event_data)
        
        # Aktualisiere Kontext basierend auf Event
        await self._update_context(session, event, data)
        
        self.logger.info(f"Transition: {call_id} {current_state.value} -> {new_state.value} ({event.value})")
        
        # Spezielle Behandlung für bestimmte Events
        if event == CallEvent.CALL_ENDED:
            await self._handle_call_end(session)
        
        return True
    
    async def get_session(self, call_id: str) -> Optional[CallSession]:
        """Gibt Session für Call-ID zurück"""
        return self.sessions.get(call_id)
    
    async def get_policy_for_session(self, call_id: str) -> Optional[str]:
        """Gibt Policy-Variante für Session zurück"""
        session = self.sessions.get(call_id)
        return session.policy_variant if session else None
    
    async def update_session_context(self, call_id: str, **kwargs) -> bool:
        """
        Aktualisiert Session-Kontext
        
        Args:
            call_id: Call-ID
            **kwargs: Kontext-Updates
            
        Returns:
            True wenn erfolgreich
        """
        if call_id not in self.sessions:
            return False
        
        session = self.sessions[call_id]
        
        # Aktualisiere Kontext-Felder
        for key, value in kwargs.items():
            if hasattr(session.context, key):
                setattr(session.context, key, value)
        
        # Aktualisiere Call-Duration
        session.context.call_duration = (datetime.now() - session.start_time).total_seconds()
        
        return True
    
    async def _select_policy(self, context: CallContext) -> str:
        """
        Wählt Policy-Variante basierend auf Kontext
        
        Args:
            context: Call-Kontext
            
        Returns:
            Policy-Variante ID
        """
        try:
            # Konvertiere Kontext zu Dictionary für Bandit
            context_dict = {
                "profile": context.profile,
                "time_of_day": context.time_of_day,
                "call_duration": context.call_duration
            }
            
            # Wähle Policy über Bandit
            policy_variant = select_policy(context_dict)
            
            self.logger.debug(f"Policy ausgewählt: {policy_variant} für Kontext: {context_dict}")
            return policy_variant
            
        except Exception as e:
            self.logger.error(f"Fehler bei Policy-Auswahl: {e}")
            return "v1a"  # Fallback
    
    async def _update_context(self, session: CallSession, event: CallEvent, data: Optional[Dict[str, Any]]):
        """Aktualisiert Session-Kontext basierend auf Event"""
        if event == CallEvent.BARGE_IN:
            session.context.barge_in_count += 1
        elif event == CallEvent.CALL_ENDED:
            session.context.call_duration = (datetime.now() - session.start_time).total_seconds()
        
        # Aktualisiere Kontext mit Event-Daten
        if data:
            if "user_rating" in data:
                session.context.user_rating = data["user_rating"]
            if "resolution" in data:
                session.context.resolution = data["resolution"]
            if "handover" in data:
                session.context.handover = data["handover"]
            if "repeat_count" in data:
                session.context.repeat_count = data["repeat_count"]
    
    async def _handle_call_end(self, session: CallSession):
        """Behandelt Call-Ende und berechnet Reward"""
        try:
            # Berechne Reward aus Kontext
            signals = {
                "resolution": session.context.resolution,
                "user_rating": session.context.user_rating,
                "barge_in_count": session.context.barge_in_count,
                "handover": session.context.handover,
                "duration_sec": session.context.call_duration,
                "repeats": session.context.repeat_count
            }
            
            reward = calc_reward(signals)
            
            # Aktualisiere Policy-Bandit
            update_policy_reward(session.policy_variant, reward)
            
            self.logger.info(f"Call beendet: {session.call_id}, Reward: {reward:.3f}, Policy: {session.policy_variant}")
            
            # Optional: Session nach einer Weile löschen
            asyncio.create_task(self._cleanup_session(session.call_id, delay=300))  # 5 Minuten
            
        except Exception as e:
            self.logger.error(f"Fehler bei Call-Ende-Behandlung: {e}")
    
    async def _cleanup_session(self, call_id: str, delay: int = 300):
        """Löscht Session nach Verzögerung"""
        await asyncio.sleep(delay)
        if call_id in self.sessions:
            del self.sessions[call_id]
            self.logger.debug(f"Session gelöscht: {call_id}")
    
    def _get_time_of_day(self) -> str:
        """Bestimmt Tageszeit für Kontext"""
        hour = datetime.now().hour
        if 6 <= hour < 12:
            return "morning"
        elif 12 <= hour < 18:
            return "afternoon"
        elif 18 <= hour < 22:
            return "evening"
        else:
            return "night"
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Gibt Statistiken über alle Sessions zurück"""
        active_sessions = len(self.sessions)
        state_counts = {}
        
        for session in self.sessions.values():
            state = session.state.value
            state_counts[state] = state_counts.get(state, 0) + 1
        
        return {
            "active_sessions": active_sessions,
            "state_distribution": state_counts,
            "total_events": sum(len(session.events) for session in self.sessions.values())
        }


# Globale FSM-Instanz
rt_fsm = RealtimeFSM()


# Convenience-Funktionen
async def create_call_session(call_id: str, profile: str = "general") -> CallSession:
    """Convenience-Funktion zum Erstellen einer Call-Session"""
    return await rt_fsm.create_session(call_id, profile)


async def handle_call_event(call_id: str, event: CallEvent, data: Optional[Dict[str, Any]] = None) -> bool:
    """Convenience-Funktion zum Behandeln von Call-Events"""
    return await rt_fsm.handle_event(call_id, event, data)


async def get_call_policy(call_id: str) -> Optional[str]:
    """Convenience-Funktion zum Abrufen der Call-Policy"""
    return await rt_fsm.get_policy_for_session(call_id)


async def update_call_context(call_id: str, **kwargs) -> bool:
    """Convenience-Funktion zum Aktualisieren des Call-Kontexts"""
    return await rt_fsm.update_session_context(call_id, **kwargs)


if __name__ == "__main__":
    # Beispiel-Verwendung
    async def main():
        # Session erstellen
        session = await create_call_session("test_call_123", "kfz")
        print(f"Session erstellt: {session.policy_variant}")
        
        # Events behandeln
        await handle_call_event("test_call_123", CallEvent.INCOMING_CALL)
        await handle_call_event("test_call_123", CallEvent.CALL_ANSWERED)
        await handle_call_event("test_call_123", CallEvent.AUDIO_START)
        
        # Kontext aktualisieren
        await update_call_context("test_call_123", user_rating=4, resolution=True)
        
        # Call beenden
        await handle_call_event("test_call_123", CallEvent.CALL_ENDED)
        
        # Statistiken
        stats = rt_fsm.get_session_stats()
        print(f"Session-Statistiken: {stats}")
    
    asyncio.run(main())
