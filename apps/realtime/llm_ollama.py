"""
TOM v3.0 - Ollama LLM Integration
Lokales Language Model mit GPU-Beschleunigung
"""

import asyncio
import logging
from typing import AsyncGenerator, Optional
import ollama
from datetime import datetime

from .config import RealtimeConfig

logger = logging.getLogger(__name__)


class OllamaLLMStreamer:
    """Ollama LLM mit Streaming-Unterstützung"""
    
    def __init__(self):
        self.model_name = "qwen3:14b"  # Bestes verfügbares Modell
        self.client = None
        self._setup_client()
    
    def _setup_client(self):
        """Konfiguriert Ollama-Client"""
        try:
            # Ollama-Client initialisieren
            self.client = ollama.Client()
            
            # Verfügbare Modelle prüfen
            models = self.client.list()
            available_models = [model['name'] for model in models['models']]
            
            logger.info(f"Verfügbare Ollama-Modelle: {available_models}")
            
            # Bestes verfügbares Modell wählen
            preferred_models = ["qwen3:14b", "qwen2.5:14b", "llama3:latest", "llama2", "mistral"]
            for model in preferred_models:
                if model in available_models:
                    self.model_name = model
                    break
            
            logger.info(f"Verwende Ollama-Modell: {self.model_name}")
            
        except Exception as e:
            logger.error(f"Fehler bei Ollama-Setup: {e}")
            self.client = None
    
    async def process_text(self, text: str, context: Optional[dict] = None) -> AsyncGenerator[dict, None]:
        """Verarbeitet Text mit Ollama LLM"""
        if not self.client:
            # Fallback zu Mock
            await asyncio.sleep(0.2)
            yield {
                'type': 'llm_token',
                'text': 'Ollama nicht verfügbar - Mock-Antwort',
                'provider': 'mock_fallback',
                'timestamp': datetime.now().isoformat()
            }
            return
        
        try:
            # System-Prompt erstellen
            system_prompt = self._create_system_prompt(context)
            
            # Streaming-Response von Ollama
            async for chunk in self._stream_response(text, system_prompt):
                yield chunk
                
        except Exception as e:
            logger.error(f"Ollama LLM Fehler: {e}")
            yield {
                'type': 'llm_error',
                'error': str(e),
                'provider': 'ollama',
                'timestamp': datetime.now().isoformat()
            }
    
    def _create_system_prompt(self, context: Optional[dict] = None) -> str:
        """Erstellt System-Prompt basierend auf Kontext"""
        base_prompt = """Du bist ein hilfsamer deutscher Telefonassistent. 
        Antworte kurz, freundlich und präzise auf Deutsch.
        Halte deine Antworten unter 50 Wörtern."""
        
        if context:
            # Kontext-spezifische Anpassungen
            if context.get('time_of_day') == 'morning':
                base_prompt += " Es ist Morgen - sei besonders freundlich."
            elif context.get('time_of_day') == 'evening':
                base_prompt += " Es ist Abend - sei entspannt und hilfsbereit."
            
            if context.get('user_mood') == 'frustrated':
                base_prompt += " Der Nutzer scheint frustriert - sei besonders geduldig."
        
        return base_prompt
    
    async def _stream_response(self, text: str, system_prompt: str) -> AsyncGenerator[dict, None]:
        """Streamt Ollama-Response"""
        try:
            # Ollama-Streaming-Request
            response = self.client.chat(
                model=self.model_name,
                messages=[
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': text}
                ],
                stream=True
            )
            
            # Stream verarbeiten
            full_response = ""
            for chunk in response:
                if chunk.get('message', {}).get('content'):
                    content = chunk['message']['content']
                    full_response += content
                    
                    yield {
                        'type': 'llm_token',
                        'text': content,
                        'provider': 'ollama',
                        'timestamp': datetime.now().isoformat(),
                        'model': self.model_name
                    }
            
            # Finale Response
            yield {
                'type': 'llm_final',
                'text': full_response,
                'provider': 'ollama',
                'timestamp': datetime.now().isoformat(),
                'model': self.model_name
            }
            
        except Exception as e:
            logger.error(f"Ollama Streaming-Fehler: {e}")
            yield {
                'type': 'llm_error',
                'error': str(e),
                'provider': 'ollama',
                'timestamp': datetime.now().isoformat()
            }


class MockLLMStreamer:
    """Mock LLM für Entwicklung und Fallback"""
    
    async def process_text(self, text: str, context: Optional[dict] = None) -> AsyncGenerator[dict, None]:
        """Mock LLM-Verarbeitung"""
        await asyncio.sleep(0.2)  # Simuliere Verarbeitungszeit
        
        # Simuliere Streaming
        response_text = f"Das ist eine Mock-Antwort auf: '{text}'"
        words = response_text.split()
        
        for i, word in enumerate(words):
            await asyncio.sleep(0.05)  # Simuliere Token-für-Token
            yield {
                'type': 'llm_token',
                'text': word + " ",
                'provider': 'mock',
                'timestamp': datetime.now().isoformat()
            }
        
        yield {
            'type': 'llm_final',
            'text': response_text,
            'provider': 'mock',
            'timestamp': datetime.now().isoformat()
        }


def get_llm_streamer():
    """Factory für LLM-Streamer basierend auf Konfiguration"""
    from .config import is_local_mode
    
    if is_local_mode('llm'):
        return OllamaLLMStreamer()
    else:
        return MockLLMStreamer()


# Globale Instanz
llm_streamer = get_llm_streamer()
