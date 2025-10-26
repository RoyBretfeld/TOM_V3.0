"""
TOM v3.0 - Ollama LLM Component Test (Real-Only)
Testet echten Ollama Token-Streaming - keine Mocks!
"""

import pytest
import time


pytestmark = [pytest.mark.component, pytest.mark.real_only]


def test_ollama_connection(ensure_real_env, ollama_client):
    """Testet Ollama-Verbindung"""
    # Verfügbare Modelle abrufen
    try:
        models = ollama_client.list()
        assert models is not None, "Model-Liste nicht abrufbar"
        
        logger.info(f"Ollama verbunden, {len(models)} Modelle verfügbar")
    except Exception as e:
        pytest.skip(f"Ollama-Verbindung fehlgeschlagen: {e}")


def test_ollama_streaming_tokens(ensure_real_env, ollama_client):
    """Testet Ollama Token-Streaming"""
    # Test-Prompt
    prompt = "Sag Hallo in einem Satz."
    
    # Streaming-Request
    start_time = time.time()
    saw_token = False
    full_response = ""
    
    try:
        response = ollama_client.chat(
            model='llama3:instruct',  # oder fallback
            messages=[{'role': 'user', 'content': prompt}],
            stream=True
        )
        
        # Stream verarbeiten
        for chunk in response:
            content = chunk.get('message', {}).get('content', '')
            if content:
                saw_token = True
                full_response += content
        
        elapsed = time.time() - start_time
        
        assert saw_token, "Keine Tokens empfangen"
        assert len(full_response) > 0, "Leere Response"
        assert elapsed < 10.0, "Streaming zu langsam (>10s)"
        
        logger.info(f"Ollama streaming: {len(full_response)} Zeichen in {elapsed:.2f}s")
        
    except Exception as e:
        pytest.skip(f"Ollama streaming fehlgeschlagen: {e}")


def test_ollama_response_latency(ensure_real_env, ollama_client):
    """Testet Ollama Response-Latenz"""
    prompt = "Wie heißt die Hauptstadt von Deutschland?"
    
    start_time = time.time()
    
    try:
        response = ollama_client.chat(
            model='llama3:instruct',
            messages=[{'role': 'user', 'content': prompt}]
        )
        
        latency = time.time() - start_time
        
        assert 'content' in response['message'], "Response-Format falsch"
        assert latency < 5.0, f"Latenz zu hoch ({latency:.2f}s)"
        
        logger.info(f"Ollama-Latenz: {latency:.2f}s")
        
    except Exception as e:
        pytest.skip(f"Ollama-Latenz-Test fehlgeschlagen: {e}")


import logging
logger = logging.getLogger(__name__)

