"""
TOM v3.0 - LocalRealtimeSession
Lokale Session mit WhisperX/Ollama/Piper (on-prem)
"""

import asyncio
import base64
import logging
import time
from datetime import datetime
from typing import AsyncIterator, Optional

from .session import RealtimeSession
from .stt_whisperx import stt_streamer
from .llm_ollama import llm_streamer
from .tts_piper_realtime import piper_tts

logger = logging.getLogger(__name__)


class LocalRealtimeSession(RealtimeSession):
    """Lokale Realtime-Session mit WhisperX/Ollama/Piper"""
    
    def __init__(self, session_id: str):
        super().__init__(session_id)
        self.audio_buffer = []
        self.stt_task = None
        self.llm_task = None
        self.tts_task = None
        self.cancel_event = asyncio.Event()
        self.last_audio_time = 0
        self.vad_threshold = 0.5
        self.silence_duration_ms = 500
        
    async def open(self) -> None:
        """Session öffnen"""
        if self.is_connected:
            return
            
        logger.info(f"LocalRealtimeSession {self.session_id}: Opening session")
        self.is_connected = True
        self.cancel_event.clear()
        
        # Start VAD-Task
        self.vad_task = asyncio.create_task(self._vad_loop())
        
    async def close(self) -> None:
        """Session schließen"""
        if not self.is_connected:
            return
            
        logger.info(f"LocalRealtimeSession {self.session_id}: Closing session")
        
        # Tasks abbrechen
        if self.stt_task:
            self.stt_task.cancel()
        if self.llm_task:
            self.llm_task.cancel()
        if self.tts_task:
            self.tts_task.cancel()
        if hasattr(self, 'vad_task'):
            self.vad_task.cancel()
            
        self.is_connected = False
        
    async def send_audio(self, audio_bytes: bytes, timestamp: float) -> None:
        """Audio empfangen und buffern"""
        if not self.is_connected:
            return
            
        # Audio-Chunk hinzufügen
        self.audio_buffer.append({
            'audio': audio_bytes,
            'timestamp': timestamp
        })
        self.last_audio_time = time.time()
        
        # VAD prüfen (Voice Activity Detection)
        await self._check_vad()
        
    async def recv_events(self) -> AsyncIterator[dict]:
        """Events empfangen"""
        while self.is_connected:
            # STT-Events
            if self.stt_task and not self.stt_task.done():
                try:
                    # STT-Event abrufen
                    await asyncio.sleep(0.01)  # Nicht-blockierend
                except asyncio.CancelledError:
                    break
                    
            # LLM-Events
            if self.llm_task and not self.llm_task.done():
                try:
                    await asyncio.sleep(0.01)
                except asyncio.CancelledError:
                    break
                    
            # TTS-Events
            if self.tts_task and not self.tts_task.done():
                try:
                    await asyncio.sleep(0.01)
                except asyncio.CancelledError:
                    break
            
            await asyncio.sleep(0.01)
        
        yield {
            'type': 'session_closed',
            'timestamp': datetime.now().isoformat(),
            'session_id': self.session_id
        }
    
    async def cancel(self) -> None:
        """Laufende Antwort abbrechen (Barge-In)"""
        logger.info(f"LocalRealtimeSession {self.session_id}: Cancelling response")
        
        # Cancel-Event setzen
        self.cancel_event.set()
        
        # LLM-Task abbrechen
        if self.llm_task and not self.llm_task.done():
            self.llm_task.cancel()
            
        # TTS stoppen
        await piper_tts.stop()
        
        # Tasks zurücksetzen
        self.llm_task = None
        self.tts_task = None
        
        # Buffer leeren
        self.audio_buffer = []
        
        logger.info(f"LocalRealtimeSession {self.session_id}: Response cancelled")
    
    async def send_event(self, event: dict) -> None:
        """Steuerkommando senden"""
        event_type = event.get('type')
        
        if event_type == 'input_audio_buffer.commit':
            # STT auslösen
            await self._trigger_stt()
        elif event_type == 'response.create':
            # LLM+TTS auslösen
            await self._trigger_response()
    
    async def _vad_loop(self):
        """Voice Activity Detection Loop"""
        while self.is_connected and not self.cancel_event.is_set():
            await asyncio.sleep(0.1)  # 100ms Interval
            
            # Prüfe ob Stille erkannt wurde
            silence_duration = (time.time() - self.last_audio_time) * 1000
            
            if silence_duration > self.silence_duration_ms and len(self.audio_buffer) > 0:
                # VAD: Stille erkannt -> STT auslösen
                logger.info(f"VAD: Silence detected ({silence_duration:.0f}ms), triggering STT")
                await self._trigger_stt()
                
    async def _check_vad(self):
        """Prüft Voice Activity Detection"""
        # Einfache VAD: wenn Buffer groß genug und letzte Aktivität > threshold
        if len(self.audio_buffer) > 10:  # Mindestens 200ms Audio
            # Prüfe ob weitere Audio-Chunks kommen
            await asyncio.sleep(0.1)
            
            if time.time() - self.last_audio_time > 0.5:  # 500ms Stille
                # VAD: Stille erkannt -> STT auslösen
                await self._trigger_stt()
    
    async def _trigger_stt(self):
        """STT auslösen"""
        if self.stt_task and not self.stt_task.done():
            return  # Bereits aktiv
            
        logger.info(f"Triggering STT for session {self.session_id}")
        
        # Audio-Buffer konsolidieren
        audio_data = b''.join([chunk['audio'] for chunk in self.audio_buffer])
        self.audio_buffer = []  # Buffer leeren
        
        # STT-Task starten
        self.stt_task = asyncio.create_task(self._run_stt(audio_data))
        
    async def _run_stt(self, audio_data: bytes):
        """STT ausführen"""
        try:
            async for event in stt_streamer.process_audio_chunk(audio_data):
                # Event weitergeben
                yield event
                
        except asyncio.CancelledError:
            logger.info(f"STT task cancelled for session {self.session_id}")
        except Exception as e:
            logger.error(f"STT error: {e}")
            
    async def _trigger_response(self):
        """LLM+TTS Antwort auslösen"""
        if self.llm_task and not self.llm_task.done():
            return  # Bereits aktiv
            
        # Hier würde die LLM-TTS-Pipeline gestartet werden
        # Für jetzt nur Platzhalter
        pass
    
    async def _get_stt_text(self) -> Optional[str]:
        """Holt STT-Text von laufender STT-Task"""
        if not self.stt_task or self.stt_task.done():
            return None
            
        # STT-Task abrufen (vereinfacht)
        return None
    
    async def _run_llm_and_tts(self, stt_text: str):
        """LLM und TTS ausführen"""
        try:
            # Cancel prüfen
            if self.cancel_event.is_set():
                return
                
            # LLM-Tokens
            llm_response = ""
            async for event in llm_streamer.process_text(stt_text):
                if self.cancel_event.is_set():
                    break
                    
                if event.get('type') == 'llm_token':
                    llm_response += event.get('text', '')
                    yield event
                elif event.get('type') == 'llm_final':
                    llm_response = event.get('text', '')
                    
                    # TTS starten (falls nicht cancelled)
                    if not self.cancel_event.is_set():
                        async for audio_event in piper_tts.synthesize_text(llm_response):
                            yield audio_event
                    
        except asyncio.CancelledError:
            logger.info(f"LLM+TTS task cancelled for session {self.session_id}")
        except Exception as e:
            logger.error(f"LLM+TTS error: {e}")

