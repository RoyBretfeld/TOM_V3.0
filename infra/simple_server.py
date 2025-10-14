#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TOM v3.0 - Einfacher Mock WebSocket Server
"""

import asyncio
import websockets
import json
from datetime import datetime

async def handle_client(websocket):
    print(f'Client connected: {websocket.remote_address}')
    
    try:
        # Sende connected Event
        await websocket.send(json.dumps({
            'type': 'connected',
            'timestamp': datetime.now().isoformat()
        }))
        
        async for message in websocket:
            try:
                data = json.loads(message)
                print(f'Received: {data.get("type", "unknown")}')
                
                if data.get('type') == 'audio_chunk':
                    print('Processing audio chunk...')
                    
                    # Mock STT (100ms delay)
                    await asyncio.sleep(0.1)
                    await websocket.send(json.dumps({
                        'type': 'stt_final',
                        'text': 'Hallo, das ist ein Test!',
                        'confidence': 0.95,
                        'timestamp': datetime.now().isoformat()
                    }))
                    print('STT result sent')
                    
                    # Mock LLM (200ms delay)
                    await asyncio.sleep(0.2)
                    await websocket.send(json.dumps({
                        'type': 'llm_token',
                        'text': 'Das ist eine simulierte Antwort vom Language Model.',
                        'timestamp': datetime.now().isoformat()
                    }))
                    print('LLM response sent')
                    
                    # Mock TTS (300ms delay)
                    await asyncio.sleep(0.3)
                    await websocket.send(json.dumps({
                        'type': 'tts_audio',
                        'audio': 'mock_audio_data',
                        'timestamp': datetime.now().isoformat()
                    }))
                    print('TTS audio sent')
                    
                    # Turn end
                    await websocket.send(json.dumps({
                        'type': 'turn_end',
                        'timestamp': datetime.now().isoformat()
                    }))
                    print('Turn completed')
                    
            except json.JSONDecodeError as e:
                print(f'JSON Error: {e}')
            except Exception as e:
                print(f'Message Error: {e}')
                
    except websockets.exceptions.ConnectionClosed:
        print(f'Client disconnected: {websocket.remote_address}')
    except Exception as e:
        print(f'Connection Error: {e}')

async def main():
    print('Starting Simple Mock WebSocket Server...')
    print('URL: ws://localhost:8080/')
    print('Waiting for connections...')
    
    # Einfacher Server ohne Subprotocol
    start_server = websockets.serve(handle_client, 'localhost', 8080)
    await start_server
    
    print('Server running on port 8080')
    await asyncio.Future()  # Run forever

if __name__ == '__main__':
    asyncio.run(main())
