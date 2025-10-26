#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TOM v3.0 - Realtime Provider Adapter
Echte Verbindung zu Realtime-APIs (OpenAI, Azure, etc.)
"""

import asyncio
import json
import logging
import os
import time
from typing import AsyncIterator, Dict, Optional
import websockets
import aiohttp
from datetime import datetime

logger = logging.getLogger(__name__)

# Konfiguration
REALTIME_WS_URL = os.getenv('REALTIME_WS_URL', 'wss://api.openai.com/v1/realtime')
REALTIME_API_KEY = os.getenv('REALTIME_API_KEY')
REALTIME_MODEL = os.getenv('REALTIME_MODEL', 'gpt-4o-realtime-preview-2024-10-01')
REALTIME_LANGUAGE = os.getenv('REALTIME_LANGUAGE', 'de')

class RealtimeProvider:
    """Adapter für Realtime-APIs (OpenAI, Azure, etc.)"""
    
    def __init__(self):
        self.ws_url = REALTIME_WS_URL
        self.api_key = REALTIME_API_KEY
        self.model = REALTIME_MODEL
        self.language = REALTIME_LANGUAGE
        self.websocket = None
        self.session_id = None
        self.is_connected = False
        self.event_queue = asyncio.Queue()
        
    async def open(self) -> None:
        """WebSocket-Session zur Realtime-API öffnen"""
        if self.is_connected:
            return
            
        try:
            logger.info(f"Connecting to Realtime API: {self.ws_url}")
            
            # WebSocket-Verbindung mit Auth-Header
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'OpenAI-Beta': 'realtime=v1'
            }
            
            self.websocket = await websockets.connect(
                self.ws_url,
                extra_headers=headers,
                subprotocols=['realtime-v1']
            )
            
            # Session initialisieren
            await self._init_session()
            
            self.is_connected = True
            logger.info("Realtime API connected successfully")
            
        except Exception as e:
            logger.error(f"Failed to connect to Realtime API: {e}")
            raise
    
    async def _init_session(self):
        """Session mit Provider initialisieren"""
        # Session-Config senden
        config_message = {
            "type": "session.update",
            "session": {
                "modalities": ["text", "audio"],
                "instructions": f"You are a helpful German assistant. Respond in German.",
                "voice": "alloy",
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "input_audio_transcription": {
                    "model": "whisper-1"
                },
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.5,
                    "prefix_padding_ms": 300,
                    "silence_duration_ms": 500
                },
                "tools": [],
                "tool_choice": "auto",
                "temperature": 0.8,
                "max_response_output_tokens": 4096
            }
        }
        
        await self.websocket.send(json.dumps(config_message))
        
        # Response abwarten
        response = await self.websocket.recv()
        response_data = json.loads(response)
        
        if response_data.get('type') == 'session.created':
            self.session_id = response_data.get('session', {}).get('id')
            logger.info(f"Session created: {self.session_id}")
        else:
            raise Exception(f"Session initialization failed: {response_data}")
    
    async def send_audio(self, pcm16_bytes: bytes, timestamp: float) -> None:
        """Audio-Frame an Provider senden"""
        if not self.is_connected or not self.websocket:
            return
            
        try:
            # Audio-Frame im Provider-Format senden
            audio_message = {
                "type": "input_audio_buffer.append",
                "audio": pcm16_bytes.hex(),  # Hex-Encoding für Binärdaten
                "timestamp": timestamp
            }
            
            await self.websocket.send(json.dumps(audio_message))
            
        except Exception as e:
            logger.error(f"Failed to send audio: {e}")
            raise
    
    async def send_event(self, payload: dict) -> None:
        """Steuerkommandos an Provider senden"""
        if not self.is_connected or not self.websocket:
            return
            
        try:
            await self.websocket.send(json.dumps(payload))
        except Exception as e:
            logger.error(f"Failed to send event: {e}")
            raise
    
    async def recv(self) -> AsyncIterator[dict]:
        """Provider-Events lesen und mappen"""
        if not self.is_connected or not self.websocket:
            return
            
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    mapped_event = self._map_provider_event(data)
                    
                    if mapped_event:
                        yield mapped_event
                        
                except json.JSONDecodeError as e:
                    logger.warning(f"Invalid JSON from provider: {e}")
                except Exception as e:
                    logger.error(f"Event processing error: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info("Provider connection closed")
            self.is_connected = False
        except Exception as e:
            logger.error(f"Provider recv error: {e}")
            self.is_connected = False
    
    def _map_provider_event(self, provider_event: dict) -> Optional[dict]:
        """Provider-Events auf Standard-Format mappen"""
        event_type = provider_event.get('type')
        
        if event_type == 'conversation.item.input_audio_buffer.speech_started':
            return {
                'type': 'stt_started',
                'timestamp': datetime.now().isoformat(),
                'provider': 'realtime'
            }
            
        elif event_type == 'conversation.item.input_audio_buffer.speech_stopped':
            return {
                'type': 'stt_stopped',
                'timestamp': datetime.now().isoformat(),
                'provider': 'realtime'
            }
            
        elif event_type == 'conversation.item.input_audio_buffer.committed':
            # STT-Final
            transcript = provider_event.get('transcript', '')
            return {
                'type': 'stt_final',
                'text': transcript,
                'confidence': provider_event.get('confidence', 0.95),
                'timestamp': datetime.now().isoformat(),
                'provider': 'realtime'
            }
            
        elif event_type == 'conversation.item.participant.speech_started':
            # LLM-Antwort beginnt
            return {
                'type': 'llm_started',
                'timestamp': datetime.now().isoformat(),
                'provider': 'realtime'
            }
            
        elif event_type == 'conversation.item.participant.speech_stopped':
            # LLM-Antwort beendet
            return {
                'type': 'llm_complete',
                'timestamp': datetime.now().isoformat(),
                'provider': 'realtime'
            }
            
        elif event_type == 'conversation.item.participant.speech_delta':
            # LLM-Token
            delta = provider_event.get('delta', '')
            return {
                'type': 'llm_token',
                'text': delta,
                'timestamp': datetime.now().isoformat(),
                'provider': 'realtime'
            }
            
        elif event_type == 'conversation.item.participant.audio.delta':
            # TTS-Audio-Frame
            audio_data = provider_event.get('delta', '')
            return {
                'type': 'tts_audio',
                'audio': audio_data,
                'codec': 'pcm16',
                'timestamp': datetime.now().isoformat(),
                'provider': 'realtime'
            }
            
        elif event_type == 'session.updated':
            # Session-Update bestätigung
            return {
                'type': 'session_updated',
                'timestamp': datetime.now().isoformat(),
                'provider': 'realtime'
            }
            
        elif event_type == 'error':
            # Fehler-Event
            error_info = provider_event.get('error', {})
            return {
                'type': 'provider_error',
                'error': error_info.get('message', 'Unknown error'),
                'code': error_info.get('code', 'unknown'),
                'timestamp': datetime.now().isoformat(),
                'provider': 'realtime'
            }
        
        # Unbekannte Events ignorieren
        return None
    
    async def cancel(self) -> None:
        """Conversation/Response abbrechen (für Barge-In)"""
        if not self.is_connected or not self.websocket:
            return
            
        try:
            # Cancel-Message senden
            cancel_message = {
                "type": "conversation.item.participant.speech.interrupt"
            }
            
            await self.websocket.send(json.dumps(cancel_message))
            logger.info("Sent cancel signal to provider")
            
        except Exception as e:
            logger.error(f"Failed to cancel provider: {e}")
    
    async def close(self) -> None:
        """Session schließen"""
        try:
            if self.websocket and not self.websocket.closed:
                await self.websocket.close()
            
            self.is_connected = False
            self.session_id = None
            logger.info("Provider session closed")
            
        except Exception as e:
            logger.error(f"Error closing provider session: {e}")


class AzureRealtimeProvider(RealtimeProvider):
    """Azure Cognitive Services Realtime Provider"""
    
    def __init__(self):
        super().__init__()
        self.ws_url = os.getenv('AZURE_REALTIME_WS_URL', 'wss://speech.microsoft.com/speech/transcription/conversation/v1')
        self.api_key = os.getenv('AZURE_SPEECH_KEY')
        self.region = os.getenv('AZURE_SPEECH_REGION', 'westeurope')
    
    async def _init_session(self):
        """Azure-spezifische Session-Initialisierung"""
        # Azure hat anderes Protokoll
        config_message = {
            "type": "conversationUpdate",
            "conversationId": self.session_id or "default",
            "participantId": "user",
            "locale": self.language,
            "format": "detailed"
        }
        
        await self.websocket.send(json.dumps(config_message))


# Factory-Funktion
def create_provider() -> RealtimeProvider:
    """Provider basierend auf ENV-Variablen erstellen"""
    provider_type = os.getenv('REALTIME_PROVIDER', 'openai')
    
    if provider_type == 'azure':
        return AzureRealtimeProvider()
    else:
        return RealtimeProvider()
