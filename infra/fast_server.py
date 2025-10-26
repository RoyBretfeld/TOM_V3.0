#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TOM v3.0 - Fast Real Hybrid WebSocket Server
ECHTE WhisperX + Ollama + Piper Pipeline - SCHNELL!
"""

import asyncio
import json
import logging
import sys
import os
import time
from datetime import datetime
import websockets
from websockets.server import WebSocketServerProtocol

# Lokale Services
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

logger = logging.getLogger(__name__)

class FastHybridServer:
    def __init__(self):
        logger.info("🚀 Initialisiere Fast Hybrid Server...")
        self.setup_components()
        self.audio_buffer = []  # Sammelt Audio-Chunks
        self.last_process_time = 0
        self.session_id = None  # Für Audio-Dateien
        self.audio_file_path = None  # Pfad zur aktuellen Audio-Datei
    
    def setup_components(self):
        """Lädt echte AI-Komponenten"""
        try:
            # Ollama LLM
            import ollama
            self.ollama_client = ollama.Client()
            models = self.ollama_client.list()
            self.model_name = models.models[0].model if models.models else "qwen3:14b"
            logger.info(f"✅ Ollama geladen: {self.model_name}")
            
            # Piper TTS (vereinfacht)
            try:
                import piper
                self.pipert_available = True
                logger.info("✅ Piper verfügbar")
            except ImportError:
                self.pipert_available = False
                logger.warning("⚠️ Piper nicht verfügbar")
            
            # WhisperX - ECHT LADEN!
            try:
                import whisperx
                import torch
                
                # Device bestimmen
                self.device = "cuda" if torch.cuda.is_available() else "cpu"
                self.compute_type = "float16" if self.device == "cuda" else "int8"
                
                logger.info(f"🎤 Lade WhisperX auf {self.device}...")
                
                # WhisperX-Modell laden
                self.whisperx_model = whisperx.load_model(
                    "large-v2", 
                    self.device, 
                    compute_type=self.compute_type,
                    language="de"  # Deutsch
                )
                
                # VAD-Modell für bessere Segmentierung (optional)
                try:
                    self.vad_model = whisperx.load_vad_model(self.device)
                    logger.info("✅ VAD-Modell geladen")
                except AttributeError:
                    logger.warning("⚠️ VAD-Modell nicht verfügbar - verwende ohne VAD")
                    self.vad_model = None
                
                self.whisperx_available = True
                logger.info("✅ WhisperX ECHT geladen!")
                
            except Exception as e:
                logger.error(f"❌ WhisperX Fehler: {e}")
                self.whisperx_available = False
                self.whisperx_model = None
                self.vad_model = None
                
        except Exception as e:
            logger.error(f"❌ Fehler beim Laden der Komponenten: {e}")
            raise
    
    async def handle_client(self, websocket: WebSocketServerProtocol):
        logger.info(f'🔌 Client connected: {websocket.remote_address}')
        
        # Neue Session starten
        self.session_id = f"session_{int(time.time())}"
        self.audio_buffer = []
        
        try:
            # Sende connected Event
            await websocket.send(json.dumps({
                'type': 'connected',
                'timestamp': datetime.now().isoformat(),
                'session_id': self.session_id,
                'components': {
                    'ollama': self.model_name,
                    'piper': self.pipert_available,
                    'whisperx': self.whisperx_available
                }
            }))
            
            async for message in websocket:
                try:
                    data = json.loads(message)
                    
                    if data.get('type') == 'audio_chunk':
                        await self.buffer_and_process_audio(websocket, data['audio'])
                    elif data.get('type') == 'audio_end':
                        await self.finalize_audio_processing(websocket)
                        
                except json.JSONDecodeError as e:
                    logger.error(f'❌ JSON Error: {e}')
                except Exception as e:
                    logger.error(f'❌ Message Error: {e}')
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info(f'🔌 Client disconnected: {websocket.remote_address}')
            self.cleanup_session()
        except Exception as e:
            logger.error(f'❌ Connection Error: {e}')
            self.cleanup_session()
    
    async def buffer_and_process_audio(self, websocket, audio_data):
        """Buffer Audio-Chunks und verarbeite sie"""
        current_time = time.time()
        
        # Rate Limiting: Max 1x pro Sekunde
        if current_time - self.last_process_time < 1.0:
            # Audio trotzdem buffern
            self.audio_buffer.extend(audio_data)
            logger.debug(f"🎤 Audio gebuffert: {len(audio_data)} bytes (Total: {len(self.audio_buffer)})")
            return
        
        self.last_process_time = current_time
        
        # Audio zu Buffer hinzufügen
        self.audio_buffer.extend(audio_data)
        logger.info(f"🎤 Audio gebuffert: {len(audio_data)} bytes (Total: {len(self.audio_buffer)})")
        
        # Wenn genug Audio vorhanden ist, verarbeite es
        if len(self.audio_buffer) > 16000:  # ~1 Sekunde bei 16kHz
            await self.process_buffered_audio(websocket)
    
    async def finalize_audio_processing(self, websocket):
        """Verarbeite restlichen Audio-Buffer"""
        if self.audio_buffer:
            logger.info(f"🎤 Finalisiere Audio-Verarbeitung: {len(self.audio_buffer)} bytes")
            await self.process_buffered_audio(websocket)
        else:
            logger.info("🎤 Kein Audio zu verarbeiten")
    
    async def process_buffered_audio(self, websocket):
        """Verarbeite gebuffertes Audio mit WhisperX"""
        if not self.audio_buffer:
            return
            
        logger.info(f"🎤 Verarbeite {len(self.audio_buffer)} Audio-Bytes mit WhisperX...")
        
        # Speichere Audio in temporärer Datei
        audio_file_path = await self.save_audio_to_file()
        
        stt_text = "Keine Spracherkennung verfügbar"
        
        if self.whisperx_available and self.whisperx_model and audio_file_path:
            try:
                # WhisperX-Transkription von Datei
                result = self.whisperx_model.transcribe(audio_file_path)
                
                if result and 'segments' in result and result['segments']:
                    # Alle Segmente zusammenfassen
                    texts = []
                    for segment in result['segments']:
                        text = segment.get('text', '').strip()
                        if text:
                            texts.append(text)
                    
                    stt_text = ' '.join(texts) if texts else "Audio erkannt, aber kein Text"
                    
                    logger.info(f"🎤 WhisperX erkannt: '{stt_text}'")
                else:
                    stt_text = "Audio erkannt, aber kein Text"
                    logger.warning("⚠️ WhisperX: Kein Text erkannt")
                    
            except Exception as e:
                logger.error(f"❌ WhisperX Fehler: {e}")
                stt_text = f"STT-Fehler: {e}"
        else:
            logger.warning("⚠️ WhisperX nicht verfügbar - verwende Fallback")
            stt_text = f"Audio empfangen ({len(self.audio_buffer)} bytes) - WhisperX nicht verfügbar"
        
        # Audio-Buffer leeren
        self.audio_buffer = []
        
        await websocket.send(json.dumps({
            'type': 'stt_final',
            'text': stt_text,
            'provider': 'whisperx_real' if self.whisperx_available else 'fallback',
            'audio_length': len(self.audio_buffer),
            'audio_file': audio_file_path,
            'timestamp': datetime.now().isoformat()
        }))
        
        # LLM-Verarbeitung
        await self.process_llm_response(websocket, stt_text)
    
    async def save_audio_to_file(self):
        """Speichere Audio-Buffer in temporärer Datei"""
        if not self.audio_buffer:
            return None
            
        try:
            # Erstelle Audio-Verzeichnis
            audio_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'audio')
            os.makedirs(audio_dir, exist_ok=True)
            
            # Generiere Dateiname
            timestamp = int(time.time())
            filename = f"{self.session_id}_{timestamp}.wav"
            audio_file_path = os.path.join(audio_dir, filename)
            
            # Konvertiere Audio-Buffer zu WAV-Datei
            import wave
            import numpy as np
            
            # Audio-Buffer zu numpy-Array
            audio_array = np.array(self.audio_buffer, dtype=np.int16)
            
            # WAV-Datei schreiben
            with wave.open(audio_file_path, 'wb') as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(16000)  # 16kHz
                wav_file.writeframes(audio_array.tobytes())
            
            logger.info(f"💾 Audio gespeichert: {audio_file_path}")
            return audio_file_path
            
        except Exception as e:
            logger.error(f"❌ Fehler beim Speichern von Audio: {e}")
            return None
    
    async def process_llm_response(self, websocket, stt_text):
        """Verarbeite LLM-Antwort"""
        logger.info(f"🤖 LLM: {stt_text}")
        
        try:
            response = self.ollama_client.chat(
                model=self.model_name,
                messages=[{'role': 'user', 'content': f"Antworte kurz auf Deutsch: {stt_text}"}]
            )
            
            llm_response = response['message']['content']
            logger.info(f"🤖 Response: {llm_response}")
            
            await websocket.send(json.dumps({
                'type': 'llm_complete',
                'text': llm_response,
                'provider': 'ollama',
                'model': self.model_name,
                'timestamp': datetime.now().isoformat()
            }))
                
        except Exception as e:
            logger.error(f"❌ Ollama Error: {e}")
            await websocket.send(json.dumps({
                'type': 'llm_complete',
                'text': f"Fehler: {e}",
                'provider': 'ollama_error',
                'timestamp': datetime.now().isoformat()
            }))
        
        # Pipeline beendet
        await websocket.send(json.dumps({
            'type': 'pipeline_complete',
            'timestamp': datetime.now().isoformat()
        }))
        
        logger.info("✅ Pipeline completed")
    
    def cleanup_session(self):
        """Räume Session auf"""
        if self.audio_file_path and os.path.exists(self.audio_file_path):
            try:
                os.remove(self.audio_file_path)
                logger.info(f"🗑️ Audio-Datei gelöscht: {self.audio_file_path}")
            except Exception as e:
                logger.error(f"❌ Fehler beim Löschen der Audio-Datei: {e}")
        
        self.audio_buffer = []
        self.session_id = None
        self.audio_file_path = None
    

async def main():
    # Konfiguriere Logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    server = FastHybridServer()
    logger.info('🚀 Starting Fast Hybrid WebSocket Server...')
    logger.info('🌐 URL: ws://localhost:8081/')
    logger.info('⚡ SCHNELLER MODUS - Rate Limited!')
    
    start_server = websockets.serve(server.handle_client, 'localhost', 8081)
    await start_server
    
    logger.info('✅ Fast Server running on port 8081')
    await asyncio.Future()  # Run forever

if __name__ == '__main__':
    asyncio.run(main())
