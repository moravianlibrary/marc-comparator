type EventHandler = (data: unknown) => void;

class WSClient {
  private ws: WebSocket | null = null;
  private handlers = new Map<string, Set<EventHandler>>();
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private reconnectDelay = 1000;
  private closing = false;

  connect() {
    if (this.ws?.readyState === WebSocket.OPEN || this.ws?.readyState === WebSocket.CONNECTING) {
      return;
    }

    this.closing = false;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/api/ws`;

    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      console.debug('[ws] connected to', wsUrl);
      this.reconnectDelay = 1000;
    };

    this.ws.onmessage = event => {
      try {
        const message = JSON.parse(event.data);
        const { type, ...data } = message;
        console.debug('[ws] received', type, data);
        const typeHandlers = this.handlers.get(type);
        if (typeHandlers) {
          typeHandlers.forEach(handler => {
            handler(data);
          });
        }
      } catch (err) {
        console.warn('[ws] failed to handle message', err);
      }
    };

    this.ws.onclose = event => {
      console.debug('[ws] closed', event.code, event.reason);
      if (this.closing) {
        return;
      }
      // An auth failure is not something a retry fixes; the socket waits to be
      // told the session is good again (see reconnectNow). Blind retries here
      // only hammered the handshake with the same rejected cookie.
      if (event.code === 4001) {
        console.debug('[ws] not authenticated; waiting for a refreshed session');
        return;
      }
      this.scheduleReconnect();
    };

    this.ws.onerror = () => {
      this.ws?.close();
    };
  }

  /**
   * Reconnect immediately, discarding any pending backoff.
   *
   * Called when the session is known to be good again. The socket is the one
   * request that cannot refresh its own credentials mid-flight, so it has to be
   * told; otherwise it sits out the backoff with a cookie that would now work.
   */
  reconnectNow() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this.reconnectDelay = 1000;
    if (this.ws?.readyState === WebSocket.OPEN || this.ws?.readyState === WebSocket.CONNECTING) {
      return;
    }
    this.connect();
  }

  disconnect() {
    this.closing = true;
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this.ws?.close();
    this.ws = null;
  }

  on(type: string, handler: EventHandler) {
    if (!this.handlers.has(type)) {
      this.handlers.set(type, new Set());
    }
    this.handlers.get(type)!.add(handler);
    return () => {
      this.handlers.get(type)?.delete(handler);
    };
  }

  private scheduleReconnect() {
    this.reconnectTimer = setTimeout(() => {
      this.reconnectDelay = Math.min(this.reconnectDelay * 2, 30000);
      this.connect();
    }, this.reconnectDelay);
  }
}

export const wsClient = new WSClient();
