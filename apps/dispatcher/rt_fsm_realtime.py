#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TOM v3.0 - Realtime FSM ohne Mocks
Echte Zustandsmaschine für Realtime-Pipeline
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Dict, Optional
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)

class FSMState(Enum):
    """FSM-Zustände"""
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"
    BARRED = "barred"
    ERROR = "error"

@dataclass
class FSMEvent:
    """FSM-Event"""
    type: str
    timestamp: float
    data: Optional[dict] = None

class RealtimeFSM:
    """Realtime Finite State Machine ohne Mocks"""
    
    def __init__(self):
        self.sessions: Dict[str, 'SessionState'] = {}
        self.state_transitions = {
            FSMState.LISTENING: [FSMState.THINKING, FSMState.BARRED, FSMState.ERROR],
            FSMState.THINKING: [FSMState.SPEAKING, FSMState.BARRED, FSMState.ERROR],
            FSMState.SPEAKING: [FSMState.LISTENING, FSMState.BARRED, FSMState.ERROR],
            FSMState.BARRED: [FSMState.LISTENING, FSMState.ERROR],
            FSMState.ERROR: [FSMState.LISTENING]
        }
        
    def get_session(self, call_id: str) -> 'SessionState':
        """Session-State abrufen oder erstellen"""
        if call_id not in self.sessions:
            self.sessions[call_id] = SessionState(call_id)
        return self.sessions[call_id]
    
    async def process_audio_chunk(self, call_id: str, event) -> None:
        """Audio-Chunk verarbeiten"""
        session = self.get_session(call_id)
        
        if session.state == FSMState.LISTENING:
            # Audio sammeln
            session.audio_buffer.append(event.audio)
            session.last_audio_time = time.time()
            
            logger.debug(f"Session {call_id}: Audio chunk received ({len(session.audio_buffer)} chunks)")
            
        elif session.state == FSMState.BARRED:
            # Nach Barge-In: Audio ignorieren bis zu LISTENING zurück
            logger.debug(f"Session {call_id}: Ignoring audio chunk in BARRED state")
    
    async def process_stt_final(self, call_id: str, event) -> None:
        """STT-Final verarbeiten"""
        session = self.get_session(call_id)
        
        if session.state == FSMState.LISTENING:
            # Zu THINKING wechseln
            await self._transition_to(call_id, FSMState.THINKING, event)
            
            # STT-Text speichern
            session.stt_text = event.get('text', '')
            session.stt_confidence = event.get('confidence', 0.0)
            session.stt_timestamp = time.time()
            
            logger.info(f"Session {call_id}: STT final '{session.stt_text}' -> THINKING")
            
        else:
            logger.warning(f"Session {call_id}: STT final in unexpected state {session.state}")
    
    async def process_llm_token(self, call_id: str, event) -> None:
        """LLM-Token verarbeiten"""
        session = self.get_session(call_id)
        
        if session.state == FSMState.THINKING:
            # Ersten Token: zu SPEAKING wechseln
            if not session.llm_tokens:
                await self._transition_to(call_id, FSMState.SPEAKING, event)
                session.first_token_time = time.time()
                logger.info(f"Session {call_id}: First LLM token -> SPEAKING")
            
            # Token sammeln
            token = event.get('text', '')
            session.llm_tokens.append(token)
            session.llm_response += token
            
        elif session.state == FSMState.SPEAKING:
            # Weitere Tokens sammeln
            token = event.get('text', '')
            session.llm_tokens.append(token)
            session.llm_response += token
            
        else:
            logger.warning(f"Session {call_id}: LLM token in unexpected state {session.state}")
    
    async def process_llm_complete(self, call_id: str, event) -> None:
        """LLM-Complete verarbeiten"""
        session = self.get_session(call_id)
        
        if session.state == FSMState.SPEAKING:
            session.llm_complete_time = time.time()
            logger.info(f"Session {call_id}: LLM complete, ready for TTS")
            
        else:
            logger.warning(f"Session {call_id}: LLM complete in unexpected state {session.state}")
    
    async def process_tts_audio(self, call_id: str, event) -> None:
        """TTS-Audio verarbeiten"""
        session = self.get_session(call_id)
        
        if session.state == FSMState.SPEAKING:
            # Erstes Audio-Frame
            if not session.tts_frames:
                session.first_audio_time = time.time()
                logger.info(f"Session {call_id}: First TTS audio frame")
            
            # Audio-Frame sammeln
            session.tts_frames.append(event.get('audio', ''))
            
        else:
            logger.warning(f"Session {call_id}: TTS audio in unexpected state {session.state}")
    
    async def process_tts_complete(self, call_id: str, event) -> None:
        """TTS-Complete verarbeiten"""
        session = self.get_session(call_id)
        
        if session.state == FSMState.SPEAKING:
            # Zurück zu LISTENING
            await self._transition_to(call_id, FSMState.LISTENING, event)
            
            # Metriken berechnen
            await self._calculate_metrics(call_id)
            
            # Session zurücksetzen
            session.reset_for_next_turn()
            
            logger.info(f"Session {call_id}: TTS complete -> LISTENING")
            
        else:
            logger.warning(f"Session {call_id}: TTS complete in unexpected state {session.state}")
    
    async def process_barge_in(self, call_id: str, event) -> None:
        """Barge-In verarbeiten"""
        session = self.get_session(call_id)
        
        # Barge-In ist von jedem Zustand möglich
        await self._transition_to(call_id, FSMState.BARRED, event)
        
        # Barge-In-Zeit speichern
        session.barge_in_time = time.time()
        
        logger.info(f"Session {call_id}: Barge-in -> BARRED")
        
        # Nach kurzer Pause zurück zu LISTENING
        await asyncio.sleep(0.1)  # 100ms Pause
        await self._transition_to(call_id, FSMState.LISTENING, event)
        
        logger.info(f"Session {call_id}: Barge-in complete -> LISTENING")
    
    async def process_error(self, call_id: str, event) -> None:
        """Fehler verarbeiten"""
        session = self.get_session(call_id)
        
        await self._transition_to(call_id, FSMState.ERROR, event)
        
        # Fehler-Info speichern
        session.last_error = event.get('error', 'Unknown error')
        session.error_time = time.time()
        
        logger.error(f"Session {call_id}: Error '{session.last_error}' -> ERROR")
        
        # Nach 1 Sekunde zurück zu LISTENING
        await asyncio.sleep(1.0)
        await self._transition_to(call_id, FSMState.LISTENING, event)
        
        logger.info(f"Session {call_id}: Error recovery -> LISTENING")
    
    async def _transition_to(self, call_id: str, new_state: FSMState, event) -> None:
        """Zustandsübergang durchführen"""
        session = self.get_session(call_id)
        old_state = session.state
        
        # Übergang validieren
        if new_state not in self.state_transitions.get(old_state, []):
            logger.warning(f"Session {call_id}: Invalid transition {old_state} -> {new_state}")
            return
        
        # Zustand ändern
        session.state = new_state
        session.state_history.append({
            'from': old_state.value,
            'to': new_state.value,
            'timestamp': time.time(),
            'event_type': event.type if hasattr(event, 'type') else 'unknown'
        })
        
        logger.debug(f"Session {call_id}: {old_state.value} -> {new_state.value}")
    
    async def _calculate_metrics(self, call_id: str) -> None:
        """Latenz-Metriken berechnen"""
        session = self.get_session(call_id)
        
        if session.stt_timestamp and session.first_token_time:
            session.stt_to_llm_ms = (session.first_token_time - session.stt_timestamp) * 1000
        
        if session.first_token_time and session.first_audio_time:
            session.llm_to_tts_ms = (session.first_audio_time - session.first_token_time) * 1000
        
        if session.stt_timestamp and session.first_audio_time:
            session.e2e_ms = (session.first_audio_time - session.stt_timestamp) * 1000
        
        # Metriken loggen
        logger.info(f"Session {call_id} metrics:")
        logger.info(f"  STT->LLM: {session.stt_to_llm_ms:.1f}ms")
        logger.info(f"  LLM->TTS: {session.llm_to_tts_ms:.1f}ms")
        logger.info(f"  E2E: {session.e2e_ms:.1f}ms")
    
    def get_session_state(self, call_id: str) -> dict:
        """Session-State für Monitoring abrufen"""
        if call_id not in self.sessions:
            return {'state': 'unknown', 'call_id': call_id}
        
        session = self.sessions[call_id]
        return {
            'call_id': call_id,
            'state': session.state.value,
            'stt_text': session.stt_text,
            'llm_response': session.llm_response[:100] + '...' if len(session.llm_response) > 100 else session.llm_response,
            'metrics': {
                'stt_to_llm_ms': session.stt_to_llm_ms,
                'llm_to_tts_ms': session.llm_to_tts_ms,
                'e2e_ms': session.e2e_ms
            },
            'state_history': session.state_history[-5:],  # Letzte 5 Übergänge
            'last_error': session.last_error
        }
    
    def cleanup_session(self, call_id: str) -> None:
        """Session aufräumen"""
        if call_id in self.sessions:
            del self.sessions[call_id]
            logger.info(f"Cleaned up session {call_id}")


class SessionState:
    """Session-spezifischer Zustand"""
    
    def __init__(self, call_id: str):
        self.call_id = call_id
        self.state = FSMState.LISTENING
        self.state_history = []
        
        # Audio-Buffer
        self.audio_buffer = []
        self.last_audio_time = 0
        
        # STT
        self.stt_text = ""
        self.stt_confidence = 0.0
        self.stt_timestamp = 0
        
        # LLM
        self.llm_tokens = []
        self.llm_response = ""
        self.first_token_time = 0
        self.llm_complete_time = 0
        
        # TTS
        self.tts_frames = []
        self.first_audio_time = 0
        
        # Metriken
        self.stt_to_llm_ms = 0
        self.llm_to_tts_ms = 0
        self.e2e_ms = 0
        
        # Barge-In
        self.barge_in_time = 0
        
        # Fehler
        self.last_error = None
        self.error_time = 0
    
    def reset_for_next_turn(self):
        """Session für nächsten Turn zurücksetzen"""
        self.audio_buffer = []
        self.stt_text = ""
        self.llm_tokens = []
        self.llm_response = ""
        self.tts_frames = []
        self.stt_timestamp = 0
        self.first_token_time = 0
        self.first_audio_time = 0
        self.stt_to_llm_ms = 0
        self.llm_to_tts_ms = 0
        self.e2e_ms = 0


# Globale FSM-Instanz
realtime_fsm = RealtimeFSM()
