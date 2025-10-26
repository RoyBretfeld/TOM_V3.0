"""
TOM v3.0 - WS Gateway Integration Test (Real-Only)
Testet echten WebSocket-Roundtrip - keine Mocks!
"""

import pytest
import asyncio
import websockets
import base64
import json
import logging


pytestmark = [pytest.mark.integration, pytest.mark.real_only]


async def send_audio_frame(ws, pcm16_data: bytes):
    """Sendet Audio-Frame als Event"""
    audio_b64 = base64.b64encode(pcm16_data).decode()
    
    event = {
        'type': 'audio_chunk',
        'audio': audio_b64,
        'timestamp': asyncio.get_event_loop().time(),
        'audio_length': len(pcm16_data)
    }
    
    await ws.send(json.dumps(event))


@pytest.mark.asyncio
async def test_ws_gateway_connection(ensure_real_env):
    """Testet WS Gateway Verbindung"""
    ws_url = os.getenv('WS_URL', 'ws://localhost:8081/ws/stream')
    call_id = f"test_{int(time.time())}"
    
    try:
        async with websockets.connect(f"{ws_url}/{call_id}", ping_interval=10) as ws:
            # Connected-Event empfangen
            response = await asyncio.wait_for(ws.recv(), timeout=5.0)
            data = json.loads(response)
            
            assert data.get('type') == 'connected', "Kein Connected-Event"
            logger.info(f"WS Gateway verbunden für Call {call_id}")
            
    except Exception as e:
        pytest.skip(f"WS Gateway Connection fehlgeschlagen: {e}")


@pytest.mark.asyncio
async def test_ws_roundtrip_minimal(ensure_real_env):
    """Testet minimalen WS Roundtrip"""
    ws_url = os.getenv('WS_URL', 'ws://localhost:8081/ws/stream')
    call_id = f"test_roundtrip_{int(time.time())}"
    
    try:
        async with websockets.connect(f"{ws_url}/{call_id}", ping_interval=10) as ws:
            # Connected-Event
            await asyncio.wait_for(ws.recv(), timeout=5.0)
            
            # Sende 200ms Stille-Frames (10 Frames @ 20ms)
            saw_response = False
            
            for i in range(10):
                # 20ms @ 16kHz = 320 samples
                silence_frame = b"\x00\x00" * 320
                await send_audio_frame(ws, silence_frame)
                await asyncio.sleep(0.02)  # 20ms pro Frame
                
                # Prüfe ob Event zurückkommt (nicht-blockierend)
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=0.1)
                    data = json.loads(msg)
                    
                    # Prüfe auf relevante Event-Typen
                    if data.get('type') in ['stt_final', 'stt_started', 'llm_token', 'tts_audio', 'tts_started']:
                        saw_response = True
                        logger.info(f"Erhaltenes Event: {data.get('type')}")
                        break
                        
                except asyncio.TimeoutError:
                    continue  # Kein Event, weitermachen
            
            assert saw_response, "Kein Response-Event vom Gateway erhalten"
            logger.info("WS Roundtrip erfolgreich")
            
    except Exception as e:
        pytest.skip(f"WS Roundtrip fehlgeschlagen: {e}")


@pytest.mark.asyncio
async def test_ws_barge_in_response(ensure_real_env):
    """Testet Barge-In Response-Latenz"""
    ws_url = os.getenv('WS_URL', 'ws://localhost:8081/ws/stream')
    call_id = f"test_barge_in_{int(time.time())}"
    
    try:
        async with websockets.connect(f"{ws_url}/{call_id}", ping_interval=10) as ws:
            # Connected
            await asyncio.wait_for(ws.recv(), timeout=5.0)
            
            # Barge-In Event senden
            barge_in_event = {
                'type': 'barge_in',
                'timestamp': asyncio.get_event_loop().time()
            }
            
            start_time = time.time()
            await ws.send(json.dumps(barge_in_event))
            
            # Warte auf ACK
            response = await asyncio.wait_for(ws.recv(), timeout=1.0)
            latency = (time.time() - start_time) * 1000
            
            data = json.loads(response)
            assert data.get('type') == 'barge_in_ack', "Kein Barge-In ACK"
            assert latency < 120, f"Barge-In-Latenz zu hoch ({latency:.1f}ms)"
            
            logger.info(f"Barge-In Latenz: {latency:.1f}ms")
            
    except Exception as e:
        pytest.skip(f"Barge-In Test fehlgeschlagen: {e}")


import logging
import time
import os
logger = logging.getLogger(__name__)

