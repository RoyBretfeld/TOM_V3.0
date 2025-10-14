"""
TOM v3.0 - WhisperX STT Integration
Hochqualitative Speech-to-Text mit GPU-Beschleunigung
"""

import asyncio
import base64
import io
import logging
import tempfile
import os
from typing import AsyncGenerator, Optional
import whisperx
import torch
import numpy as np
from datetime import datetime

from .config import RealtimeConfig

logger = logging.getLogger(__name__)


class WhisperXStreamer:
    """WhisperX STT mit GPU-Beschleunigung und Word-level Timestamps"""
    
    def __init__(self):
        self.model = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.compute_type = "float16" if self.device == "cuda" else "int8"
        self._setup_model()
    
    def _setup_model(self):
        """Lädt WhisperX-Modell"""
        try:
            logger.info(f"Lade WhisperX-Modell auf {self.device}...")
            
            # WhisperX-Modell laden
            self.model = whisperx.load_model(
                "large-v3",  # Beste Qualität
                device=self.device,
                compute_type=self.compute_type,
                language="de"  # Deutsche Sprache
            )
            
            logger.info(f"WhisperX-Modell erfolgreich geladen auf {self.device}")
            
        except Exception as e:
            logger.error(f"Fehler beim Laden von WhisperX: {e}")
            self.model = None
    
    async def process_audio_chunk(self, audio_data: bytes) -> AsyncGenerator[dict, None]:
        """Verarbeitet Audio-Chunk mit WhisperX"""
        if not self.model:
            # Fallback zu Mock
            await asyncio.sleep(0.1)
            yield {
                'type': 'stt_final',
                'text': 'WhisperX nicht verfügbar - Mock-Antwort',
                'confidence': 0.5,
                'provider': 'mock_fallback',
                'timestamp': datetime.now().isoformat()
            }
            return
        
        try:
            # Audio-Daten dekodieren und verarbeiten
            audio_array = await self._decode_audio(audio_data)
            
            if audio_array is None:
                yield {
                    'type': 'stt_error',
                    'error': 'Audio-Dekodierung fehlgeschlagen',
                    'provider': 'whisperx',
                    'timestamp': datetime.now().isoformat()
                }
                return
            
            # WhisperX-Transkription
            result = await self._transcribe_audio(audio_array)
            
            if result:
                # Word-level Timestamps extrahieren
                words = result.get('word_segments', [])
                
                yield {
                    'type': 'stt_final',
                    'text': result.get('text', ''),
                    'confidence': result.get('confidence', 0.0),
                    'provider': 'whisperx',
                    'timestamp': datetime.now().isoformat(),
                    'words': words,  # Word-level Timestamps
                    'language': result.get('language', 'de')
                }
            else:
                yield {
                    'type': 'stt_final',
                    'text': '',
                    'confidence': 0.0,
                    'provider': 'whisperx',
                    'timestamp': datetime.now().isoformat(),
                    'error': 'Keine Transkription erhalten'
                }
                
        except Exception as e:
            logger.error(f"WhisperX Fehler: {e}")
            yield {
                'type': 'stt_error',
                'error': str(e),
                'provider': 'whisperx',
                'timestamp': datetime.now().isoformat()
            }
    
    async def _decode_audio(self, audio_data: bytes) -> Optional[np.ndarray]:
        """Dekodiert Audio-Daten"""
        try:
            # Base64 dekodieren falls nötig
            if isinstance(audio_data, str):
                audio_bytes = base64.b64decode(audio_data)
            else:
                audio_bytes = audio_data
            
            # Temporäre Datei erstellen
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_file.write(audio_bytes)
                temp_path = temp_file.name
            
            try:
                # Audio mit whisperx laden
                audio = whisperx.load_audio(temp_path)
                return audio
            finally:
                # Temporäre Datei löschen
                os.unlink(temp_path)
                
        except Exception as e:
            logger.error(f"Audio-Dekodierung fehlgeschlagen: {e}")
            return None
    
    async def _transcribe_audio(self, audio_array: np.ndarray) -> Optional[dict]:
        """Führt WhisperX-Transkription durch"""
        loop = asyncio.get_event_loop()
        
        def _transcribe():
            try:
                # Transkription durchführen
                result = self.model.transcribe(audio_array)
                
                # Word-level Alignment (falls verfügbar)
                try:
                    model_a, metadata = whisperx.load_align_model(
                        language_code="de", 
                        device=self.device
                    )
                    result = whisperx.align(
                        result["segments"], 
                        model_a, 
                        metadata, 
                        audio_array, 
                        self.device,
                        return_char_alignments=False
                    )
                except Exception as e:
                    logger.warning(f"Word-level Alignment fehlgeschlagen: {e}")
                
                return result
                
            except Exception as e:
                logger.error(f"Transkription fehlgeschlagen: {e}")
                return None
        
        return await loop.run_in_executor(None, _transcribe)
    
    def cleanup(self):
        """Räumt Ressourcen auf"""
        if self.model:
            del self.model
            torch.cuda.empty_cache() if torch.cuda.is_available() else None


class MockSTTStreamer:
    """Mock STT für Entwicklung und Fallback"""
    
    async def process_audio_chunk(self, audio_data: bytes) -> AsyncGenerator[dict, None]:
        """Mock STT-Verarbeitung"""
        await asyncio.sleep(0.1)  # Simuliere Verarbeitungszeit
        
        yield {
            'type': 'stt_final',
            'text': 'Hallo, das ist ein Mock-STT Test!',
            'confidence': 0.95,
            'provider': 'mock',
            'timestamp': datetime.now().isoformat(),
            'words': [
                {'word': 'Hallo', 'start': 0.0, 'end': 0.5},
                {'word': 'das', 'start': 0.5, 'end': 0.8},
                {'word': 'ist', 'start': 0.8, 'end': 1.0},
                {'word': 'ein', 'start': 1.0, 'end': 1.2},
                {'word': 'Test', 'start': 1.2, 'end': 1.8}
            ]
        }


def get_stt_streamer():
    """Factory für STT-Streamer basierend auf Konfiguration"""
    from .config import is_local_mode
    
    if is_local_mode('stt'):
        return WhisperXStreamer()
    else:
        return MockSTTStreamer()


# Globale Instanz
stt_streamer = get_stt_streamer()
