/**
 * Telemetry WebSocket client
 *
 * Wraps the raw WebSocket with:
 *  - Automatic reconnect (exponential backoff)
 *  - Inbound message routing to registered handlers
 *  - Outbound batching of MousePoints
 */

import type { MousePoint, TelemetryFrame, WebSocketMessage } from '@/types';

type MessageHandler = (msg: WebSocketMessage) => void;

const WS_BASE = '/ws/telemetry';
const MAX_RECONNECT_DELAY_MS = 16_000;

export class TelemetryClient {
  private sessionId: number;
  private ws: WebSocket | null = null;
  private handlers: MessageHandler[] = [];
  private reconnectDelay = 1000;
  private intentionallyClosed = false;

  constructor(sessionId: number) {
    this.sessionId = sessionId;
  }

  connect(): void {
    this.intentionallyClosed = false;
    this._open();
  }

  private _open(): void {
    const url = `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}${WS_BASE}/${this.sessionId}`;
    this.ws = new WebSocket(url);

    this.ws.onopen = () => {
      this.reconnectDelay = 1000;
    };

    this.ws.onmessage = (evt) => {
      try {
        const msg = JSON.parse(evt.data as string) as WebSocketMessage;
        this.handlers.forEach((h) => h(msg));
      } catch {
        // Malformed message — ignore
      }
    };

    this.ws.onclose = () => {
      if (!this.intentionallyClosed) {
        setTimeout(() => {
          this.reconnectDelay = Math.min(this.reconnectDelay * 2, MAX_RECONNECT_DELAY_MS);
          this._open();
        }, this.reconnectDelay);
      }
    };

    this.ws.onerror = () => {
      this.ws?.close();
    };
  }

  send(points: MousePoint[]): void {
    if (this.ws?.readyState !== WebSocket.OPEN || points.length === 0) return;
    const frame: TelemetryFrame = { session_id: this.sessionId, points };
    this.ws.send(JSON.stringify(frame));
  }

  onMessage(handler: MessageHandler): () => void {
    this.handlers.push(handler);
    return () => {
      this.handlers = this.handlers.filter((h) => h !== handler);
    };
  }

  disconnect(): void {
    this.intentionallyClosed = true;
    this.ws?.close();
    this.ws = null;
  }
}
