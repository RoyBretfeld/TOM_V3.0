"""
TOM v3.0 - Piper TTS Integration
Lokale Text-to-Speech mit deutschen Stimmen
"""

import asyncio
import base64
import io
import logging
import tempfile
import os
from typing import AsyncGenerator, Optional
import piper
from datetime import datetime

from .config import RealtimeConfig

logger = logging.getLogger(__name__)


class PiperTTSStreamer:
    """Piper TTS mit deutschen Stimmen"""
    
    def __init__(self):
        self.voice = None
        self.model_path = None
        self.config_path = None
        self._setup_piper()
    
    def _setup_piper(self):
        """Konfiguriert Piper TTS"""
        try:
            # Deutsche Stimme laden (Thorsten - männlich)
            voice_name = "de_DE-thorsten-medium"
            
            logger.info(f"Lade Piper-Stimme: {voice_name}")
            
            # Lokale Pfade zu den heruntergeladenen Modellen
            model_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'models', 'piper', f"{voice_name}.onnx")
            config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'models', 'piper', f"{voice_name}.onnx.json")
            
            logger.info(f"Modell-Pfad: {model_path}")
            logger.info(f"Config-Pfad: {config_path}")
            
            # Prüfen ob Dateien existieren
            if not os.path.exists(model_path) or not os.path.exists(config_path):
                logger.error(f"Piper-Modelle nicht gefunden: {model_path} oder {config_path}")
                self.voice = None
                return
            
            # Piper mit lokalen Dateien initialisieren
            self.voice = piper.PiperVoice.load(
                model_path=model_path,
                config_path=config_path
            )
            
            logger.info("Piper TTS erfolgreich geladen")
            
        except Exception as e:
            logger.error(f"Fehler beim Laden von Piper: {e}")
            # Fallback zu einfachem Piper
            try:
                self.voice = piper.PiperVoice.load(
                    model_path="en_US-lessac-medium",
                    config_path="en_US-lessac-medium.json"
                )
                logger.info("Piper Fallback-Stimme geladen")
            except Exception as e2:
                logger.error(f"Piper Fallback fehlgeschlagen: {e2}")
                self.voice = None
    
    async def process_text(self, text: str) -> AsyncGenerator[dict, None]:
        """Verarbeitet Text mit Piper TTS"""
        if not self.voice:
            # Fallback zu Mock
            await asyncio.sleep(0.3)
            yield {
                'type': 'tts_audio',
                'audio': 'mock_audio_data',
                'provider': 'mock_fallback',
                'timestamp': datetime.now().isoformat()
            }
            return
        
        try:
            # Text vorverarbeiten
            processed_text = self._preprocess_text(text)
            
            # Audio generieren
            audio_data = await self._synthesize_speech(processed_text)
            
            if audio_data:
                # Base64 kodieren für WebSocket-Übertragung
                audio_b64 = base64.b64encode(audio_data).decode('utf-8')
                
                yield {
                    'type': 'tts_audio',
                    'audio': audio_b64,
                    'provider': 'piper',
                    'timestamp': datetime.now().isoformat(),
                    'text': processed_text,
                    'duration': len(audio_data) / 16000  # Geschätzte Dauer
                }
            else:
                yield {
                    'type': 'tts_error',
                    'error': 'Audio-Generierung fehlgeschlagen',
                    'provider': 'piper',
                    'timestamp': datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Piper TTS Fehler: {e}")
            yield {
                'type': 'tts_error',
                'error': str(e),
                'provider': 'piper',
                'timestamp': datetime.now().isoformat()
            }
    
    def _preprocess_text(self, text: str) -> str:
        """Vorverarbeitung des Textes für bessere TTS-Qualität"""
        # Entferne Sonderzeichen die Probleme verursachen
        processed = text.replace('"', '').replace("'", "")
        
        # Füge Pausen hinzu
        processed = processed.replace('.', '. ')
        processed = processed.replace(',', ', ')
        processed = processed.replace('!', '! ')
        processed = processed.replace('?', '? ')
        
        # Begrenze Länge für bessere Performance
        if len(processed) > 200:
            processed = processed[:200] + "..."
        
        return processed.strip()
    
    async def _synthesize_speech(self, text: str) -> Optional[bytes]:
        """Synthetisiert Sprache mit Piper"""
        try:
            loop = asyncio.get_event_loop()
            
            def _synthesize():
                # Audio generieren
                audio_bytes = io.BytesIO()
                self.voice.synthesize(text, audio_bytes)
                return audio_bytes.getvalue()
            
            return await loop.run_in_executor(None, _synthesize)
            
        except Exception as e:
            logger.error(f"Sprachsynthese fehlgeschlagen: {e}")
            return None
    
    def cleanup(self):
        """Räumt Ressourcen auf"""
        if self.voice:
            del self.voice


class MockTTSStreamer:
    """Mock TTS für Entwicklung und Fallback"""
    
    async def process_text(self, text: str) -> AsyncGenerator[dict, None]:
        """Mock TTS-Verarbeitung"""
        await asyncio.sleep(0.3)  # Simuliere Verarbeitungszeit
        
        # Mock-Audio-Daten (Base64 kodiert)
        mock_audio = base64.b64encode(b"mock_audio_data").decode('utf-8')
        
        yield {
            'type': 'tts_audio',
            'audio': mock_audio,
            'provider': 'mock',
            'timestamp': datetime.now().isoformat(),
            'text': text,
            'duration': 2.0
        }


def get_tts_streamer():
    """Factory für TTS-Streamer basierend auf Konfiguration"""
    from .config import is_local_mode
    
    if is_local_mode('tts'):
        return PiperTTSStreamer()
    else:
        return MockTTSStreamer()


# Globale Instanz
tts_streamer = get_tts_streamer()
