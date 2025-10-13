import React, { useState, useEffect, useRef } from 'react';
import { RealtimeWSClient } from '../lib/ws';
import { floatToPCM16_16k, createAudioChunk, getAudioLevel } from '../lib/audio';
import { AudioDevice, WSMessage } from '../types/events';
import './MicControls.css';

interface MicControlsProps {
  onConnect: (connected: boolean) => void;
  onEvent: (type: string, data?: any) => void;
}

const MicControls: React.FC<MicControlsProps> = ({ onConnect, onEvent }) => {
  const [devices, setDevices] = useState<AudioDevice[]>([]);
  const [selectedDevice, setSelectedDevice] = useState<string>('');
  const [jwt, setJwt] = useState<string>('');
  const [callId] = useState<string>(() => `call_${Date.now()}`);
  const [isConnected, setIsConnected] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [audioLevel, setAudioLevel] = useState(0);

  const wsClientRef = useRef<RealtimeWSClient | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const animationRef = useRef<number | null>(null);

  // Geräte auflisten
  useEffect(() => {
    navigator.mediaDevices.enumerateDevices().then(deviceList => {
      const audioInputs = deviceList
        .filter(device => device.kind === 'audioinput')
        .map(device => ({
          deviceId: device.deviceId,
          label: device.label || `Mikrofon ${device.deviceId.slice(0, 8)}`
        }));
      setDevices(audioInputs);
      if (audioInputs.length > 0) {
        setSelectedDevice(audioInputs[0].deviceId);
      }
    });
  }, []);

  // Audio-Level-Animation
  const updateAudioLevel = () => {
    if (analyserRef.current) {
      const level = getAudioLevel(analyserRef.current);
      setAudioLevel(level);
    }
    animationRef.current = requestAnimationFrame(updateAudioLevel);
  };

  const connect = async () => {
    if (!jwt.trim()) {
      alert('Bitte JWT-Token eingeben');
      return;
    }

    try {
      const wsClient = new RealtimeWSClient(
        callId,
        jwt,
        (message: WSMessage) => {
          onEvent(message.type, message);
        },
        (error: string) => {
          onEvent('error', { error });
        },
        () => {
          setIsConnected(true);
          onConnect(true);
          onEvent('connected', { callId });
        },
        () => {
          setIsConnected(false);
          onConnect(false);
          onEvent('disconnected', {});
        }
      );

      await wsClient.connect();
      wsClientRef.current = wsClient;

      // Ping alle 30 Sekunden
      const pingInterval = setInterval(() => {
        if (wsClient.isConnected()) {
          wsClient.sendPing();
        } else {
          clearInterval(pingInterval);
        }
      }, 30000);

    } catch (error) {
      onEvent('error', { error: `Verbindungsfehler: ${error}` });
    }
  };

  const disconnect = () => {
    if (wsClientRef.current) {
      wsClientRef.current.disconnect();
      wsClientRef.current = null;
    }
    stopStreaming();
  };

  const startStreaming = async () => {
    if (!wsClientRef.current || !wsClientRef.current.isConnected()) {
      alert('Bitte zuerst verbinden');
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          deviceId: selectedDevice,
          sampleRate: 48000,
          channelCount: 1
        }
      });

      streamRef.current = stream;

      // AudioContext für Resampling
      const audioContext = new AudioContext({ sampleRate: 48000 });
      audioContextRef.current = audioContext;

      const source = audioContext.createMediaStreamSource(stream);
      const analyser = audioContext.createAnalyser();
      analyser.fftSize = 2048;
      analyser.smoothingTimeConstant = 0.8;
      analyserRef.current = analyser;

      source.connect(analyser);

      // Audio-Verarbeitung
      const processor = audioContext.createScriptProcessor(4096, 1, 1);
      processor.onaudioprocess = (event) => {
        if (!wsClientRef.current || !wsClientRef.current.isConnected()) return;

        const inputBuffer = event.inputBuffer.getChannelData(0);
        const pcm16Data = floatToPCM16_16k(inputBuffer);
        const chunk = createAudioChunk(pcm16Data, Date.now());
        
        wsClientRef.current.send(JSON.parse(chunk));
      };

      source.connect(processor);
      processor.connect(audioContext.destination);

      setIsStreaming(true);
      onEvent('streaming_started', { deviceId: selectedDevice });
      updateAudioLevel();

    } catch (error) {
      onEvent('error', { error: `Streaming-Fehler: ${error}` });
    }
  };

  const stopStreaming = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }

    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }

    if (animationRef.current) {
      cancelAnimationFrame(animationRef.current);
      animationRef.current = null;
    }

    analyserRef.current = null;
    setIsStreaming(false);
    setAudioLevel(0);
    onEvent('streaming_stopped', {});
  };

  return (
    <div className="mic-controls">
      <h2>Mikrofon-Steuerung</h2>
      
      <div className="control-group">
        <label htmlFor="device-select">Mikrofon:</label>
        <select 
          id="device-select"
          value={selectedDevice} 
          onChange={(e) => setSelectedDevice(e.target.value)}
          disabled={isStreaming}
        >
          {devices.map(device => (
            <option key={device.deviceId} value={device.deviceId}>
              {device.label}
            </option>
          ))}
        </select>
      </div>

      <div className="control-group">
        <label htmlFor="jwt-input">JWT-Token:</label>
        <input
          id="jwt-input"
          type="password"
          value={jwt}
          onChange={(e) => setJwt(e.target.value)}
          placeholder="JWT-Token eingeben..."
          disabled={isConnected}
        />
      </div>

      <div className="control-group">
        <label>Call-ID:</label>
        <span className="call-id">{callId}</span>
      </div>

      <div className="audio-level">
        <label>Pegel:</label>
        <div className="level-bar">
          <div 
            className="level-fill" 
            style={{ width: `${audioLevel * 100}%` }}
          />
        </div>
        <span className="level-text">{Math.round(audioLevel * 100)}%</span>
      </div>

      <div className="button-group">
        {!isConnected ? (
          <button onClick={connect} disabled={!jwt.trim()}>
            Verbinden
          </button>
        ) : (
          <>
            {!isStreaming ? (
              <button onClick={startStreaming}>
                Streaming Starten
              </button>
            ) : (
              <button onClick={stopStreaming}>
                Streaming Stoppen
              </button>
            )}
            <button onClick={disconnect}>
              Trennen
            </button>
          </>
        )}
      </div>

      <div className="status">
        <div className={`status-indicator ${isConnected ? 'connected' : 'disconnected'}`}>
          {isConnected ? '🟢 Verbunden' : '🔴 Getrennt'}
        </div>
        <div className={`status-indicator ${isStreaming ? 'streaming' : 'idle'}`}>
          {isStreaming ? '🎤 Streaming' : '⏸️ Pausiert'}
        </div>
      </div>
    </div>
  );
};

export default MicControls;
