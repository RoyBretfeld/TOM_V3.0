import React, { useState, useEffect, useRef } from 'react';
import { RealtimeWSClient } from '../lib/ws';
import { floatToPCM16_16k, createAudioChunk, getAudioLevel } from '../lib/audio';
import { audioPlayer } from '../lib/audioPlayer';
import { AudioDevice, WSMessage } from '../types/events';
import './MicControls.css';

interface MicControlsProps {
  onConnect: (connected: boolean) => void;
  onEvent: (type: string, data?: any) => void;
}

const MicControls: React.FC<MicControlsProps> = ({ onConnect, onEvent }) => {
  const [devices, setDevices] = useState<AudioDevice[]>([]);
  const [selectedDevice, setSelectedDevice] = useState<string>('');
  const [jwt, setJwt] = useState<string>('dev-no-jwt-needed');
  const [callId] = useState<string>(() => `call_${Date.now()}`);
  const [isConnected, setIsConnected] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [pipelineMode, setPipelineMode] = useState<'modular' | 'direct'>('modular');

  const switchMode = async (mode: 'modular' | 'direct') => {
    if (!wsClientRef.current) return;
    
    try {
      await wsClientRef.current.send(JSON.stringify({
        type: 'switch_mode',
        mode: mode
      }));
      console.log(`Pipeline-Modus gewechselt zu: ${mode}`);
    } catch (error) {
      console.error('Fehler beim Wechseln des Modus:', error);
    }
  };

  const wsClientRef = useRef<RealtimeWSClient | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const animationRef = useRef<number | null>(null);

  // Geräte auflisten
  useEffect(() => {
    const enumerateDevices = async () => {
      try {
        // Erst Mikrofon-Berechtigung anfordern
        await navigator.mediaDevices.getUserMedia({ audio: true });
        
        const deviceList = await navigator.mediaDevices.enumerateDevices();
        const audioInputs = deviceList
          .filter(device => device.kind === 'audioinput')
          .map(device => ({
            deviceId: device.deviceId,
            label: device.label || `Mikrofon ${device.deviceId.slice(0, 8)}`
          }));
        
        console.log('Audio-Geräte gefunden:', audioInputs);
        setDevices(audioInputs);
        
        if (audioInputs.length > 0) {
          setSelectedDevice(audioInputs[0].deviceId);
        } else {
          console.warn('Keine Audio-Eingabegeräte gefunden');
          // Fallback: Default-Gerät
          setDevices([{
            deviceId: 'default',
            label: 'Standard-Mikrofon'
          }]);
          setSelectedDevice('default');
        }
      } catch (error) {
        console.error('Fehler beim Auflisten der Geräte:', error);
        // Fallback: Default-Gerät
        setDevices([{
          deviceId: 'default',
          label: 'Standard-Mikrofon (Berechtigung erforderlich)'
        }]);
        setSelectedDevice('default');
      }
    };

    enumerateDevices();
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
    // JWT-Validierung für lokale Entwicklung deaktiviert
    // if (!jwt.trim()) {
    //   alert('Bitte JWT-Token eingeben');
    //   return;
    // }

    try {
        const wsClient = new RealtimeWSClient(
          callId,
          jwt,
          (message: WSMessage) => {
            onEvent(message.type, message);
            
            // Audio abspielen wenn TTS-Audio empfangen wird
            if ((message.type === 'tts_audio' || message.type === 'direct_response') && (message.data || message.audio)) {
              console.log('Spiele Audio ab...');
              const audioData = message.data || message.audio;
              if (audioData) {
                audioPlayer.queueAudio(audioData);
              }
            }
            
            // Pipeline-Modus aktualisieren
            if (message.type === 'mode_switched') {
              setPipelineMode(message.mode);
            }
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
      const audioConstraints = selectedDevice === 'default' 
        ? { audio: true }
        : {
            audio: {
              deviceId: selectedDevice,
              sampleRate: 48000,
              channelCount: 1
            }
          };

      console.log('Audio-Constraints:', audioConstraints);
      const stream = await navigator.mediaDevices.getUserMedia(audioConstraints);

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
          {devices.length === 0 ? (
            <option value="">Keine Geräte gefunden</option>
          ) : (
            devices.map(device => (
              <option key={device.deviceId} value={device.deviceId}>
                {device.label}
              </option>
            ))
          )}
        </select>
        {devices.length === 0 && (
          <div className="error-message">
            ⚠️ Keine Mikrofone gefunden. Bitte Browser-Berechtigung erteilen.
          </div>
        )}
      </div>

      <div className="control-group" style={{display: 'none'}}>
        <label htmlFor="jwt-input">JWT-Token (DEV-Modus deaktiviert):</label>
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

      <div className="control-group">
        <label>Pipeline-Modus:</label>
        <div className="mode-selector">
          <button 
            className={pipelineMode === 'modular' ? 'active' : ''}
            onClick={() => switchMode('modular')}
            disabled={!isConnected}
          >
            🔄 Modular (STT→LLM→TTS)
          </button>
          <button 
            className={pipelineMode === 'direct' ? 'active' : ''}
            onClick={() => switchMode('direct')}
            disabled={!isConnected}
          >
            ⚡ Direct (Speech-to-Speech)
          </button>
        </div>
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
          <button onClick={connect} disabled={false}>
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
