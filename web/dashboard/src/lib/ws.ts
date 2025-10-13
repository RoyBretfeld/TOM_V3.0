/**
 * WebSocket-Client für TOM v3.0 Realtime Dashboard
 * Verbindung zu /ws/stream/{call_id} mit JWT-Authentifizierung
 */

export interface WSMessage {
  type: string;
  ts?: number;
  data?: string;
  text?: string;
  codec?: string;
  bytes?: string;
}

export class RealtimeWSClient {
  private ws: WebSocket | null = null;
  private callId: string;
  private jwt: string;
  private onMessage: (message: WSMessage) => void;
  private onError: (error: string) => void;
  private onConnect: () => void;
  private onDisconnect: () => void;

  constructor(
    callId: string,
    jwt: string,
    onMessage: (message: WSMessage) => void,
    onError: (error: string) => void,
    onConnect: () => void,
    onDisconnect: () => void
  ) {
    this.callId = callId;
    this.jwt = jwt;
    this.onMessage = onMessage;
    this.onError = onError;
    this.onConnect = onConnect;
    this.onDisconnect = onDisconnect;
  }

  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        const wsUrl = `ws://localhost:8080/ws/stream/${this.callId}?t=${this.jwt}`;
        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
          this.onConnect();
          resolve();
        };

        this.ws.onmessage = (event) => {
          try {
            const message: WSMessage = JSON.parse(event.data);
            this.onMessage(message);
          } catch (error) {
            this.onError(`Fehler beim Parsen der Nachricht: ${error}`);
          }
        };

        this.ws.onerror = (error) => {
          this.onError(`WebSocket-Fehler: ${error}`);
          reject(error);
        };

        this.ws.onclose = () => {
          this.onDisconnect();
        };

      } catch (error) {
        reject(error);
      }
    });
  }

  send(message: WSMessage): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    } else {
      this.onError('WebSocket nicht verbunden');
    }
  }

  sendPing(): void {
    this.send({
      type: 'ping',
      ts: Date.now()
    });
  }

  disconnect(): void {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }
}
