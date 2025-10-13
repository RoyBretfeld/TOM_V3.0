# TOM v3.0 - Realtime Dashboard

Ein React/Vite Frontend für den TOM v3.0 Realtime-Telefonassistenten.

## Features

- 🎤 Mikrofon-Auswahl und Audio-Streaming
- 📡 WebSocket-Verbindung mit JWT-Authentifizierung  
- 🔊 Live-Pegelanzeige
- 📊 Event-Log mit Echtzeit-Updates
- 🔄 Audio-Resampling (48kHz → 16kHz PCM16)

## Installation

```bash
cd web/dashboard
npm install
```

## Entwicklung

```bash
npm run dev
```

Das Dashboard läuft dann auf `http://localhost:3000`

## Verwendung

1. **JWT-Token eingeben**: Token für die WebSocket-Authentifizierung
2. **Mikrofon auswählen**: Verfügbare Audio-Eingabegeräte
3. **Verbinden**: WebSocket-Verbindung zu `/ws/stream/{call_id}`
4. **Streaming starten**: Audio-Chunks werden als Base64 gesendet
5. **Events beobachten**: Live-Log aller eingehenden Nachrichten

## Audio-Pipeline

1. `getUserMedia()` → 48kHz Stereo
2. Resampling → 16kHz Mono PCM16
3. Chunking → 20ms Frames
4. Base64-Encoding → JSON `{"type":"audio_chunk","ts":...}`
5. WebSocket → Backend

## Sicherheit

- JWT-Token wird nur im Memory-State gehalten
- Keine persistente Speicherung von Authentifizierungsdaten
- HTTPS erforderlich für Produktionsumgebung

## Backend-Anforderungen

- WebSocket-Server auf `ws://localhost:8080/ws/stream/{call_id}`
- JWT-Authentifizierung über Query-Parameter `?t=<jwt>`
- Unterstützung für Events: `audio_chunk`, `ping`, `pong`
