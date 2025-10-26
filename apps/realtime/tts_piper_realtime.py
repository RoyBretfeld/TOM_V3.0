#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TOM v3.0 - Piper TTS Realtime
Echter TTS-Betrieb ohne Mocks
"""

import asyncio
import logging
import os
import subprocess
import tempfile
import time
from typing import Optional, AsyncIterator
import numpy as np
import wave
from datetime import datetime

logger = logging.getLogger(__name__)

# Konfiguration
PIPER_VOICE = os.getenv('PIPER_VOICE', 'de-DE-thorsten-medium')
PIPER_PATH = os.getenv('PIPER_PATH', 'piper')
SAMPLE_RATE = 16000
FRAME_SIZE_MS = 20  # 20ms Frames
FRAME_SIZE_SAMPLES = int(SAMPLE_RATE * FRAME_SIZE_MS / 1000)

class PiperTTSRealtime:
    """Echter Piper TTS für Realtime-Betrieb"""
    
    def __init__(self):
        self.voice = PIPER_VOICE
        self.piper_path = PIPER_PATH
        self.current_process = None
        self.is_speaking = False
        self.text_buffer = ""
        self.audio_queue = asyncio.Queue()
        self.stop_event = asyncio.Event()
        
    async def synthesize_text(self, text: str) -> AsyncIterator[dict]:
        """Text zu Audio synthetisieren und streamen"""
        if not text.strip():
            return
            
        logger.info(f"Piper TTS: Synthesizing '{text[:50]}...'")
        
        try:
            # Stop vorherige Synthese
            await self.stop()
            
            # Text vorverarbeiten
            processed_text = self._preprocess_text(text)
            
            # Piper-Prozess starten
            await self._start_piper_process(processed_text)
            
            # Audio-Frames streamen
            async for frame in self._stream_audio_frames():
                yield frame
                
        except Exception as e:
            logger.error(f"Piper TTS synthesis error: {e}")
            yield {
                'type': 'tts_error',
                'error': str(e),
                'timestamp': datetime.now().isoformat(),
                'provider': 'piper'
            }
        finally:
            await self.stop()
    
    def _preprocess_text(self, text: str) -> str:
        """Text für Piper vorverarbeiten"""
        # Einfache Textbereinigung
        processed = text.strip()
        
        # Deutsche Sonderzeichen normalisieren
        replacements = {
            'ä': 'ae', 'ö': 'oe', 'ü': 'ue',
            'Ä': 'Ae', 'Ö': 'Oe', 'Ü': 'Ue',
            'ß': 'ss'
        }
        
        for old, new in replacements.items():
            processed = processed.replace(old, new)
        
        return processed
    
    async def _start_piper_process(self, text: str):
        """Piper-Prozess für Text-Synthese starten"""
        try:
            # Temporäre Dateien erstellen
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as text_file:
                text_file.write(text)
                text_file_path = text_file.name
            
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as audio_file:
                audio_file_path = audio_file.name
            
            # Piper-Kommando
            cmd = [
                self.piper_path,
                '--model', f'{self.voice}.onnx',
                '--config', f'{self.voice}.onnx.json',
                '--output_file', audio_file_path,
                text_file_path
            ]
            
            logger.info(f"Starting Piper process: {' '.join(cmd)}")
            
            # Prozess starten
            self.current_process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Warten auf Fertigstellung
            stdout, stderr = await self.current_process.communicate()
            
            if self.current_process.returncode != 0:
                raise Exception(f"Piper failed: {stderr.decode()}")
            
            # Audio-Datei laden
            await self._load_audio_file(audio_file_path)
            
            # Cleanup
            os.unlink(text_file_path)
            os.unlink(audio_file_path)
            
            self.is_speaking = True
            
        except Exception as e:
            logger.error(f"Failed to start Piper process: {e}")
            raise
    
    async def _load_audio_file(self, audio_file_path: str):
        """Audio-Datei laden und in Queue einreihen"""
        try:
            with wave.open(audio_file_path, 'rb') as wav_file:
                # Audio-Parameter prüfen
                if wav_file.getnchannels() != 1:
                    raise Exception("Piper must output mono audio")
                if wav_file.getsampwidth() != 2:
                    raise Exception("Piper must output 16-bit audio")
                if wav_file.getframerate() != SAMPLE_RATE:
                    raise Exception(f"Piper must output {SAMPLE_RATE}Hz audio")
                
                # Audio-Daten lesen
                audio_data = wav_file.readframes(wav_file.getnframes())
                audio_array = np.frombuffer(audio_data, dtype=np.int16)
                
                # In Frames aufteilen
                for i in range(0, len(audio_array), FRAME_SIZE_SAMPLES):
                    frame = audio_array[i:i + FRAME_SIZE_SAMPLES]
                    
                    # Frame auf Standard-Größe auffüllen
                    if len(frame) < FRAME_SIZE_SAMPLES:
                        frame = np.pad(frame, (0, FRAME_SIZE_SAMPLES - len(frame)), 'constant')
                    
                    await self.audio_queue.put(frame)
                
                logger.info(f"Loaded {len(audio_array)} samples in {self.audio_queue.qsize()} frames")
                
        except Exception as e:
            logger.error(f"Failed to load audio file: {e}")
            raise
    
    async def _stream_audio_frames(self) -> AsyncIterator[dict]:
        """Audio-Frames streamen"""
        frame_count = 0
        
        while not self.stop_event.is_set() and not self.audio_queue.empty():
            try:
                # Frame aus Queue holen
                frame = await asyncio.wait_for(
                    self.audio_queue.get(), 
                    timeout=0.1
                )
                
                # Base64 kodieren
                import base64
                frame_bytes = frame.tobytes()
                encoded_audio = base64.b64encode(frame_bytes).decode('utf-8')
                
                yield {
                    'type': 'tts_audio',
                    'audio': encoded_audio,
                    'codec': 'pcm16',
                    'sample_rate': SAMPLE_RATE,
                    'frame_size_ms': FRAME_SIZE_MS,
                    'frame_number': frame_count,
                    'timestamp': datetime.now().isoformat(),
                    'provider': 'piper'
                }
                
                frame_count += 1
                
                # Frame-Rate simulieren (20ms pro Frame)
                await asyncio.sleep(FRAME_SIZE_MS / 1000.0)
                
            except asyncio.TimeoutError:
                break
            except Exception as e:
                logger.error(f"Audio frame streaming error: {e}")
                break
        
        # TTS-Complete Event
        yield {
            'type': 'tts_complete',
            'total_frames': frame_count,
            'timestamp': datetime.now().isoformat(),
            'provider': 'piper'
        }
    
    async def stop(self):
        """TTS-Ausgabe stoppen"""
        try:
            # Stop-Event setzen
            self.stop_event.set()
            
            # Piper-Prozess beenden
            if self.current_process and self.current_process.returncode is None:
                self.current_process.terminate()
                try:
                    await asyncio.wait_for(self.current_process.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    self.current_process.kill()
                    await self.current_process.wait()
            
            # Audio-Queue leeren
            while not self.audio_queue.empty():
                try:
                    self.audio_queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
            
            self.is_speaking = False
            self.current_process = None
            
            # Stop-Event zurücksetzen
            self.stop_event.clear()
            
            logger.info("Piper TTS stopped")
            
        except Exception as e:
            logger.error(f"Error stopping Piper TTS: {e}")
    
    async def is_available(self) -> bool:
        """Prüfen ob Piper verfügbar ist"""
        try:
            # Piper-Version prüfen
            result = await asyncio.create_subprocess_exec(
                self.piper_path, '--version',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0:
                logger.info(f"Piper available: {stdout.decode().strip()}")
                return True
            else:
                logger.warning(f"Piper not available: {stderr.decode()}")
                return False
                
        except FileNotFoundError:
            logger.warning(f"Piper executable not found: {self.piper_path}")
            return False
        except Exception as e:
            logger.error(f"Error checking Piper availability: {e}")
            return False


# Globale Instanz
piper_tts = PiperTTSRealtime()
