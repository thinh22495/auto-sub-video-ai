import type { JobProgressEvent } from "./types";

const WS_BASE =
  process.env.NEXT_PUBLIC_WS_URL || `ws://${typeof window !== "undefined" ? window.location.hostname : "localhost"}:8000/api`;

type ProgressHandler = (event: JobProgressEvent) => void;

export class JobWebSocket {
  private ws: WebSocket | null = null;
  private jobId: string;
  private handler: ProgressHandler;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private closed = false;

  constructor(jobId: string, handler: ProgressHandler) {
    this.jobId = jobId;
    this.handler = handler;
  }

  connect() {
    if (this.closed) return;

    const url = `${WS_BASE}/ws/jobs/${this.jobId}`;
    this.ws = new WebSocket(url);

    this.ws.onmessage = (event) => {
      try {
        const data: JobProgressEvent = JSON.parse(event.data);
        this.handler(data);

        // Auto-close on terminal states
        if (["COMPLETED", "FAILED", "CANCELLED"].includes(data.status)) {
          this.close();
        }
      } catch (e) {
        console.error("Failed to parse WebSocket message:", e);
      }
    };

    this.ws.onclose = () => {
      if (!this.closed) {
        this.scheduleReconnect();
      }
    };

    this.ws.onerror = (err) => {
      console.error("WebSocket error:", err);
      this.ws?.close();
    };
  }

  private scheduleReconnect() {
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.reconnectTimer = setTimeout(() => {
      console.log(`Reconnecting WebSocket for job ${this.jobId}...`);
      this.connect();
    }, 3000);
  }

  close() {
    this.closed = true;
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}
