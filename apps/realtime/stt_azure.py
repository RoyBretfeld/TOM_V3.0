"""
TOM v3.0 - Azure Speech Services STT Integration
Echte Speech-to-Text mit Azure Cognitive Services
"""

import asyncio
import base64
import io
import logging
from typing import AsyncGenerator, Optional
import azure.cognitiveservices.speech as speechsdk
from azure.cognitiveservices.speech import SpeechConfig, AudioConfig, SpeechRecognizer
from azure.cognitiveservices.speech.audio import AudioInputStream, PushAudioInputStream

from .config import RealtimeConfig

logger = logging.getLogger(__name__)


class AzureSTTStreamer:
    """Azure Speech Services STT mit Streaming-Unterstützung"""
    
    def __init__(self):
        self.speech_config = None
        self.audio_config = None
        self.recognizer = None
        self.audio_stream = None
        self._setup_azure_config()
    
    def _setup_azure_config(self):
        """Konfiguriert Azure Speech Services"""
        if not RealtimeConfig.AZURE_SPEECH_KEY or not RealtimeConfig.AZURE_SPEECH_REGION:
            logger.warning("Azure Speech Services nicht konfiguriert - verwende Mock")
            return
        
        try:
            # Speech Config
            self.speech_config = SpeechConfig(
                subscription=RealtimeConfig.AZURE_SPEECH_KEY,
                region=RealtimeConfig.AZURE_SPEECH_REGION
            )
            self.speech_config.speech_recognition_language = RealtimeConfig.AZURE_SPEECH_LANGUAGE
            
            # Audio Stream
            self.audio_stream = PushAudioInputStream()
            self.audio_config = AudioConfig(stream=self.audio_stream)
            
            # Recognizer
            self.recognizer = SpeechRecognizer(
                speech_config=self.speech_config,
                audio_config=self.audio_config
            )
            
            logger.info("Azure Speech Services STT konfiguriert")
            
        except Exception as e:
            logger.error(f"Fehler bei Azure STT Konfiguration: {e}")
            self.speech_config = None
    
    async def process_audio_chunk(self, audio_data: bytes) -> AsyncGenerator[dict, None]:
        """Verarbeitet Audio-Chunk mit Azure STT"""
        if not self.recognizer:
            # Fallback zu Mock
            await asyncio.sleep(0.1)
            yield {
                'type': 'stt_final',
                'text': 'Azure STT nicht verfügbar - Mock-Antwort',
                'confidence': 0.5,
                'provider': 'mock_fallback'
            }
            return
        
        try:
            # Audio-Daten in Stream schreiben
            self.audio_stream.write(audio_data)
            
            # STT-Ergebnis abwarten
            result = await self._recognize_once()
            
            if result.reason == speechsdk.ResultReason.RecognizedSpeech:
                yield {
                    'type': 'stt_final',
                    'text': result.text,
                    'confidence': result.properties.get(speechsdk.PropertyId.SpeechServiceResponse_JsonResult, '{}'),
                    'provider': 'azure'
                }
            elif result.reason == speechsdk.ResultReason.NoMatch:
                yield {
                    'type': 'stt_final',
                    'text': '',
                    'confidence': 0.0,
                    'provider': 'azure',
                    'error': 'No speech recognized'
                }
            else:
                yield {
                    'type': 'stt_error',
                    'error': f'STT failed: {result.reason}',
                    'provider': 'azure'
                }
                
        except Exception as e:
            logger.error(f"Azure STT Fehler: {e}")
            yield {
                'type': 'stt_error',
                'error': str(e),
                'provider': 'azure'
            }
    
    async def _recognize_once(self) -> speechsdk.SpeechRecognitionResult:
        """Führt einmalige Erkennung durch"""
        loop = asyncio.get_event_loop()
        
        def _recognize():
            return self.recognizer.recognize_once()
        
        return await loop.run_in_executor(None, _recognize)
    
    def cleanup(self):
        """Räumt Ressourcen auf"""
        if self.recognizer:
            self.recognizer.stop_continuous_recognition()
        if self.audio_stream:
            self.audio_stream.close()


class MockSTTStreamer:
    """Mock STT für Entwicklung und Fallback"""
    
    async def process_audio_chunk(self, audio_data: bytes) -> AsyncGenerator[dict, None]:
        """Mock STT-Verarbeitung"""
        await asyncio.sleep(0.1)  # Simuliere Verarbeitungszeit
        
        yield {
            'type': 'stt_final',
            'text': 'Hallo, das ist ein Mock-STT Test!',
            'confidence': 0.95,
            'provider': 'mock'
        }


def get_stt_streamer():
    """Factory für STT-Streamer basierend auf Konfiguration"""
    from .config import is_provider_mode
    
    if is_provider_mode('stt'):
        return AzureSTTStreamer()
    else:
        return MockSTTStreamer()


# Globale Instanz
stt_streamer = get_stt_streamer()
