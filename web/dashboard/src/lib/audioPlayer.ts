/**
 * Audio Player für TOM v3.0 Realtime Dashboard
 * Spielt Base64-kodierte Audio-Daten ab
 */

export class AudioPlayer {
  private audioContext: AudioContext | null = null;
  private audioQueue: string[] = [];
  private isPlaying = false;

  constructor() {
    this.initAudioContext();
  }

  private async initAudioContext() {
    try {
      this.audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
      console.log('Audio Context initialisiert');
    } catch (error) {
      console.error('Fehler beim Initialisieren des Audio Context:', error);
    }
  }

  async playAudio(base64Audio: string): Promise<void> {
    if (!this.audioContext) {
      console.warn('Audio Context nicht verfügbar');
      return;
    }

    try {
      // Base64 zu ArrayBuffer dekodieren
      const binaryString = atob(base64Audio);
      const arrayBuffer = new ArrayBuffer(binaryString.length);
      const uint8Array = new Uint8Array(arrayBuffer);
      
      for (let i = 0; i < binaryString.length; i++) {
        uint8Array[i] = binaryString.charCodeAt(i);
      }

      // Audio-Daten dekodieren
      const audioBuffer = await this.audioContext.decodeAudioData(arrayBuffer);
      
      // Audio abspielen
      const source = this.audioContext.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(this.audioContext.destination);
      
      source.onended = () => {
        this.isPlaying = false;
        this.playNextInQueue();
      };

      this.isPlaying = true;
      source.start();
      
      console.log('Audio wird abgespielt:', audioBuffer.duration, 'Sekunden');
      
    } catch (error) {
      console.error('Fehler beim Abspielen von Audio:', error);
      this.isPlaying = false;
    }
  }

  queueAudio(base64Audio: string): void {
    this.audioQueue.push(base64Audio);
    if (!this.isPlaying) {
      this.playNextInQueue();
    }
  }

  private playNextInQueue(): void {
    if (this.audioQueue.length > 0 && !this.isPlaying) {
      const nextAudio = this.audioQueue.shift();
      if (nextAudio) {
        this.playAudio(nextAudio);
      }
    }
  }

  stop(): void {
    this.audioQueue = [];
    this.isPlaying = false;
  }

  resume(): void {
    if (this.audioContext && this.audioContext.state === 'suspended') {
      this.audioContext.resume();
    }
  }
}

// Singleton-Instanz
export const audioPlayer = new AudioPlayer();
