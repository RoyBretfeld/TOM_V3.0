/**
 * TypeScript-Definitionen für TOM v3.0 Events
 */

export interface AudioChunk {
  type: 'audio_chunk';
  ts: number;
  data: string;
  format: 'pcm16_16k';
}

export interface STTPartial {
  type: 'stt_partial';
  text: string;
  ts: number;
}

export interface STTFinal {
  type: 'stt_final';
  text: string;
  ts: number;
}

export interface LLMToken {
  type: 'llm_token';
  text: string;
  ts: number;
}

export interface TTSAudio {
  type: 'tts_audio';
  codec: 'pcm16';
  bytes: string;
  ts: number;
}

export interface TurnEnd {
  type: 'turn_end';
  ts: number;
}

export interface Ping {
  type: 'ping';
  ts: number;
}

export interface Pong {
  type: 'pong';
  ts: number;
}

export interface BargeIn {
  type: 'barge_in';
  ts: number;
}

export interface Stop {
  type: 'stop';
  ts: number;
}

export type WSMessage = 
  | AudioChunk 
  | STTPartial 
  | STTFinal 
  | LLMToken 
  | TTSAudio 
  | TurnEnd 
  | Ping 
  | Pong 
  | BargeIn 
  | Stop;

export interface AudioDevice {
  deviceId: string;
  label: string;
}

export interface EventLogEntry {
  type: string;
  timestamp: string;
  data?: any;
}
