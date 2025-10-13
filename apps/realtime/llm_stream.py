"""
TOM v3.0 - LLM Streaming Adapter
Mock- und Provider-Modus für Language Model Integration
"""

import asyncio
import json
import time
from typing import AsyncIterator, List, Dict, Any, Optional
import logging
from .config import is_mock_mode, is_provider_mode, RealtimeConfig

logger = logging.getLogger(__name__)


class LLMStreamAdapter:
    """Adapter für LLM-Streaming mit Mock- und Provider-Unterstützung"""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.LLMStreamAdapter")
    
    async def stream(self, messages: List[Dict[str, str]], call_id: str) -> AsyncIterator[str]:
        """
        Streamt LLM-Tokens basierend auf der Konfiguration
        
        Args:
            messages: Liste von Nachrichten für den LLM
            call_id: Call-ID für Logging
            
        Yields:
            str: Einzelne Tokens
        """
        if is_mock_mode('llm'):
            async for token in self._mock_stream(messages, call_id):
                yield token
        elif is_provider_mode('llm'):
            async for token in self._provider_stream(messages, call_id):
                yield token
        else:
            self.logger.warning(f"[{call_id}] LLM nicht aktiviert")
            yield "LLM nicht verfügbar"
    
    async def _mock_stream(self, messages: List[Dict[str, str]], call_id: str) -> AsyncIterator[str]:
        """Mock-Streaming für Entwicklung und Tests"""
        try:
            self.logger.info(f"[{call_id}] LLM Mock-Stream gestartet")
            
            # Mock-Tokens mit realistischen Delays
            mock_tokens = [
                "Hallo,",
                " ich",
                " bin",
                " TOM.",
                " Wie",
                " kann",
                " ich",
                " Ihnen",
                " helfen?"
            ]
            
            for token in mock_tokens:
                if RealtimeConfig.DEV_MOCK_DELAYS:
                    await asyncio.sleep(RealtimeConfig.DEV_MOCK_DELAY_MS / 1000.0)
                
                self.logger.debug(f"[{call_id}] Mock-Token: {token}")
                yield token
            
            self.logger.info(f"[{call_id}] LLM Mock-Stream beendet")
            
        except Exception as e:
            self.logger.error(f"[{call_id}] Mock-Stream Fehler: {e}")
            yield f"Fehler: {e}"
    
    async def _provider_stream(self, messages: List[Dict[str, str]], call_id: str) -> AsyncIterator[str]:
        """Provider-Streaming für echte LLM-APIs"""
        try:
            self.logger.info(f"[{call_id}] LLM Provider-Stream gestartet")
            
            if not RealtimeConfig.LLM_PROVIDER_URL:
                self.logger.error(f"[{call_id}] LLM_PROVIDER_URL nicht konfiguriert")
                yield "LLM Provider nicht konfiguriert"
                return
            
            # TODO: Hier die echte Provider-Integration implementieren
            # Für jetzt: Fallback zu Mock
            self.logger.warning(f"[{call_id}] Provider-Integration noch nicht implementiert, verwende Mock")
            async for token in self._mock_stream(messages, call_id):
                yield token
            
        except Exception as e:
            self.logger.error(f"[{call_id}] Provider-Stream Fehler: {e}")
            yield f"Provider-Fehler: {e}"
    
    async def _call_openai_api(self, messages: List[Dict[str, str]], call_id: str) -> AsyncIterator[str]:
        """
        OpenAI API-Integration (Platzhalter)
        
        Args:
            messages: Nachrichten für den LLM
            call_id: Call-ID für Logging
            
        Yields:
            str: Streamed Tokens
        """
        try:
            import aiohttp
            
            headers = {
                "Authorization": f"Bearer {RealtimeConfig.LLM_PROVIDER_KEY}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": RealtimeConfig.LLM_MODEL,
                "messages": messages,
                "stream": True,
                "temperature": 0.7,
                "max_tokens": 150
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{RealtimeConfig.LLM_PROVIDER_URL}/v1/chat/completions",
                    headers=headers,
                    json=payload
                ) as response:
                    
                    if response.status != 200:
                        self.logger.error(f"[{call_id}] API-Fehler: {response.status}")
                        yield f"API-Fehler: {response.status}"
                        return
                    
                    async for line in response.content:
                        line = line.decode('utf-8').strip()
                        
                        if line.startswith('data: '):
                            data = line[6:]  # Remove 'data: ' prefix
                            
                            if data == '[DONE]':
                                break
                            
                            try:
                                chunk = json.loads(data)
                                if 'choices' in chunk and len(chunk['choices']) > 0:
                                    delta = chunk['choices'][0].get('delta', {})
                                    if 'content' in delta:
                                        token = delta['content']
                                        self.logger.debug(f"[{call_id}] Provider-Token: {token}")
                                        yield token
                            except json.JSONDecodeError:
                                continue
            
            self.logger.info(f"[{call_id}] Provider-Stream beendet")
            
        except Exception as e:
            self.logger.error(f"[{call_id}] OpenAI API Fehler: {e}")
            yield f"API-Fehler: {e}"


# Globale Instanz für einfachen Zugriff
llm_adapter = LLMStreamAdapter()


async def stream_llm(messages: List[Dict[str, str]], call_id: str) -> AsyncIterator[str]:
    """
    Convenience-Funktion für LLM-Streaming
    
    Args:
        messages: Nachrichten für den LLM
        call_id: Call-ID für Logging
        
    Yields:
        str: Streamed Tokens
    """
    async for token in llm_adapter.stream(messages, call_id):
        yield token
