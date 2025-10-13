"""
TOM v3.0 - TTS Streaming Adapter
Mock- und Piper-Modus für Text-to-Speech Integration
"""

import asyncio
import base64
import subprocess
import tempfile
import os
from typing import AsyncIterator, Optional
import logging
from .config import is_mock_mode, is_local_mode, RealtimeConfig

logger = logging.getLogger(__name__)


class TTSStreamAdapter:
    """Adapter für TTS-Streaming mit Mock- und Piper-Unterstützung"""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.TTSStreamAdapter")
    
    async def synth_stream(self, text: str, call_id: str) -> AsyncIterator[str]:
        """
        Synthetisiert Text zu Audio-Frames basierend auf der Konfiguration
        
        Args:
            text: Text zum Synthetisieren
            call_id: Call-ID für Logging
            
        Yields:
            str: Base64-kodierte Audio-Frames
        """
        if is_mock_mode('tts'):
            async for frame in self._mock_synth(text, call_id):
                yield frame
        elif is_local_mode('tts'):
            async for frame in self._piper_synth(text, call_id):
                yield frame
        else:
            self.logger.warning(f"[{call_id}] TTS nicht aktiviert")
            yield self._create_silence_frame()
    
    async def _mock_synth(self, text: str, call_id: str) -> AsyncIterator[str]:
        """Mock-Synthese für Entwicklung und Tests"""
        try:
            self.logger.info(f"[{call_id}] TTS Mock-Synthese gestartet für: {text[:50]}...")
            
            # Simuliere Synthese-Zeit
            if RealtimeConfig.DEV_MOCK_DELAYS:
                await asyncio.sleep(0.2)  # 200ms Synthese-Zeit
            
            # Generiere mehrere Audio-Frames (simuliert Streaming)
            frame_count = 10  # 10 Frames à 20ms = 200ms Audio
            
            for i in range(frame_count):
                if RealtimeConfig.DEV_MOCK_DELAYS:
                    await asyncio.sleep(0.02)  # 20ms zwischen Frames
                
                # Mock-Audio-Frame (200ms Stille als Base64)
                silence_frame = self._create_silence_frame()
                self.logger.debug(f"[{call_id}] Mock-Frame {i+1}/{frame_count}")
                yield silence_frame
            
            self.logger.info(f"[{call_id}] TTS Mock-Synthese beendet")
            
        except Exception as e:
            self.logger.error(f"[{call_id}] Mock-Synthese Fehler: {e}")
            yield self._create_silence_frame()
    
    async def _piper_synth(self, text: str, call_id: str) -> AsyncIterator[str]:
        """Piper-Synthese für lokale TTS-Verarbeitung"""
        try:
            self.logger.info(f"[{call_id}] Piper-Synthese gestartet für: {text[:50]}...")
            
            # Prüfe ob Piper verfügbar ist
            if not os.path.exists(RealtimeConfig.TTS_PIPER_PATH):
                self.logger.error(f"[{call_id}] Piper nicht gefunden: {RealtimeConfig.TTS_PIPER_PATH}")
                yield self._create_silence_frame()
                return
            
            # Erstelle temporäre Dateien
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as text_file:
                text_file.write(text)
                text_file_path = text_file.name
            
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as audio_file:
                audio_file_path = audio_file.name
            
            try:
                # Piper-Aufruf
                cmd = [
                    RealtimeConfig.TTS_PIPER_PATH,
                    '--model', RealtimeConfig.TTS_VOICE,
                    '--output_file', audio_file_path,
                    text_file_path
                ]
                
                self.logger.debug(f"[{call_id}] Piper-Kommando: {' '.join(cmd)}")
                
                # Asynchroner Prozess-Aufruf
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await process.communicate()
                
                if process.returncode != 0:
                    self.logger.error(f"[{call_id}] Piper-Fehler: {stderr.decode()}")
                    yield self._create_silence_frame()
                    return
                
                # Audio-Datei lesen und in Frames aufteilen
                if os.path.exists(audio_file_path):
                    async for frame in self._split_audio_to_frames(audio_file_path, call_id):
                        yield frame
                else:
                    self.logger.error(f"[{call_id}] Audio-Datei nicht erstellt")
                    yield self._create_silence_frame()
                
            finally:
                # Temporäre Dateien löschen
                try:
                    os.unlink(text_file_path)
                    os.unlink(audio_file_path)
                except OSError:
                    pass
            
            self.logger.info(f"[{call_id}] Piper-Synthese beendet")
            
        except Exception as e:
            self.logger.error(f"[{call_id}] Piper-Synthese Fehler: {e}")
            yield self._create_silence_frame()
    
    async def _split_audio_to_frames(self, audio_file_path: str, call_id: str) -> AsyncIterator[str]:
        """Teilt Audio-Datei in Streaming-Frames auf"""
        try:
            import wave
            
            with wave.open(audio_file_path, 'rb') as wav_file:
                # Audio-Parameter
                sample_rate = wav_file.getframerate()
                channels = wav_file.getnchannels()
                sample_width = wav_file.getsampwidth()
                
                self.logger.debug(f"[{call_id}] Audio: {sample_rate}Hz, {channels}ch, {sample_width}B")
                
                # Frame-Größe (20ms bei 16kHz)
                frame_size = int(sample_rate * 0.02)  # 20ms
                bytes_per_frame = frame_size * channels * sample_width
                
                # Audio-Daten lesen
                audio_data = wav_file.readframes(wav_file.getnframes())
                
                # In Frames aufteilen
                frame_count = 0
                for i in range(0, len(audio_data), bytes_per_frame):
                    frame_data = audio_data[i:i + bytes_per_frame]
                    
                    # Padding falls letzter Frame zu kurz
                    if len(frame_data) < bytes_per_frame:
                        frame_data += b'\x00' * (bytes_per_frame - len(frame_data))
                    
                    # Base64 kodieren
                    frame_b64 = base64.b64encode(frame_data).decode('utf-8')
                    
                    self.logger.debug(f"[{call_id}] Audio-Frame {frame_count + 1}: {len(frame_data)} bytes")
                    yield frame_b64
                    
                    frame_count += 1
                    
                    # Kleine Pause zwischen Frames
                    await asyncio.sleep(0.02)
                
                self.logger.info(f"[{call_id}] {frame_count} Audio-Frames generiert")
                
        except Exception as e:
            self.logger.error(f"[{call_id}] Audio-Frame-Aufteilung Fehler: {e}")
            yield self._create_silence_frame()
    
    def _create_silence_frame(self) -> str:
        """Erstellt einen Frame mit Stille (200ms PCM16 16kHz)"""
        # 200ms Stille bei 16kHz = 3200 Samples
        silence_samples = 3200
        silence_data = b'\x00\x00' * silence_samples  # 16-bit PCM silence
        
        return base64.b64encode(silence_data).decode('utf-8')


# Globale Instanz für einfachen Zugriff
tts_adapter = TTSStreamAdapter()


async def synth_tts(text: str, call_id: str) -> AsyncIterator[str]:
    """
    Convenience-Funktion für TTS-Synthese
    
    Args:
        text: Text zum Synthetisieren
        call_id: Call-ID für Logging
        
    Yields:
        str: Base64-kodierte Audio-Frames
    """
    async for frame in tts_adapter.synth_stream(text, call_id):
        yield frame
