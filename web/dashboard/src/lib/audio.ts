/**
 * Audio-Utilities für TOM v3.0 Realtime Dashboard
 * Resampling von 48kHz → 16kHz (mono, PCM16)
 */

export function floatToPCM16_16k(float32: Float32Array, inRate = 48000): Int16Array {
  const ratio = inRate / 16000;
  const outLen = Math.floor(float32.length / ratio);
  const out = new Int16Array(outLen);
  let o = 0, i = 0;
  
  while (o < outLen) {
    let sum = 0, cnt = 0;
    const next = Math.min((o + 1) * ratio, float32.length);
    
    for (; i < next; i++) { 
      sum += float32[i]; 
      cnt++; 
    }
    
    const s = Math.max(-1, Math.min(1, sum / cnt));
    out[o++] = s < 0 ? s * 0x8000 : s * 0x7FFF;
  }
  
  return out;
}

export function createAudioChunk(pcm16Data: Int16Array, timestamp: number): string {
  const base64 = btoa(String.fromCharCode(...new Uint8Array(pcm16Data.buffer)));
  return JSON.stringify({
    type: 'audio_chunk',
    ts: timestamp,
    data: base64,
    format: 'pcm16_16k'
  });
}

export function calculateRMS(buffer: Float32Array): number {
  let sum = 0;
  for (let i = 0; i < buffer.length; i++) {
    sum += buffer[i] * buffer[i];
  }
  return Math.sqrt(sum / buffer.length);
}

export function getAudioLevel(analyser: AnalyserNode): number {
  const bufferLength = analyser.frequencyBinCount;
  const dataArray = new Uint8Array(bufferLength);
  analyser.getByteFrequencyData(dataArray);
  
  let sum = 0;
  for (let i = 0; i < bufferLength; i++) {
    sum += dataArray[i];
  }
  return sum / bufferLength / 255; // Normalize to 0-1
}
