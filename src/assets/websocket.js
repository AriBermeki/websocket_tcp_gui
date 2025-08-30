/**
 * PyFrameConnections - WebSocket connection manager for PyFrame.
 *
 * Features:
 *  - Auto-reconnect with configurable interval
 *  - Event listener system (`on`, `off`, `offAll`)
 *  - JSON-encoded message sending
 *  - Connection status helpers (`is_connected`, `is_disconnected`)
 *
 * Usage example:
 *
 * ```js
 * window.socket_url = "ws://localhost:8765";
 * PyFrameConnections.configure({ autoReconnect: true, reconnectInterval: 5000 });
 * PyFrameConnections.on("open", () => console.log("Connected!"));
 * PyFrameConnections.connect();
 * ```
 */
(function () {
  var PyFrameConnections = {};
  var ws = null;
  var config = {
    protocols: [],
    reconnectInterval: 3000,
    autoReconnect: true
  };

  var eventListeners = {};
  var reconnectTimer = null;
  var shouldReconnect = true;

  // === Event Handling ===

  /**
   * Register an event listener.
   * @param {string} event - Event name (open, message, error, close).
   * @param {Function} listener - Callback to invoke when event fires.
   */
  function addEventListener(event, listener) {
    if (!eventListeners[event]) {
      eventListeners[event] = [];
    }
    eventListeners[event].push(listener);
  }

  /**
   * Remove a specific event listener.
   * @param {string} event - Event name.
   * @param {Function} listener - The listener to remove.
   */
  function removeEventListener(event, listener) {
    if (!eventListeners[event]) return;
    eventListeners[event] = eventListeners[event].filter(l => l !== listener);
  }

  /**
   * Remove all event listeners for an event.
   * @param {string} event - Event name.
   */
  function removeAllEventListeners(event) {
    if (eventListeners[event]) {
      eventListeners[event] = [];
    }
  }

  /**
   * Dispatch an event to all registered listeners.
   * @param {string} event - Event name.
   * @param {*} data - Payload to pass to listeners.
   */
  function dispatchEvent(event, data) {
    if (eventListeners[event]) {
      eventListeners[event].forEach(listener => listener(data));
    }
  }

  // === Core API ===

  /**
   * Configure connection options.
   * @param {Object} options
   * @param {string[]} [options.protocols] - Optional WebSocket subprotocols.
   * @param {number} [options.reconnectInterval] - Reconnect delay in ms.
   * @param {boolean} [options.autoReconnect] - Whether to auto-reconnect.
   */
  PyFrameConnections.configure = function (options) {
    config.protocols = options.protocols || config.protocols;
    config.reconnectInterval = options.reconnectInterval || config.reconnectInterval;
    config.autoReconnect = options.autoReconnect !== undefined ? options.autoReconnect : config.autoReconnect;
  };

  /**
   * Establish a WebSocket connection.
   * Requires `window.socket_url` to be set.
   */
  PyFrameConnections.connect = function () {
    if (!window.socket_url) {
      console.error("PyFrameConnections: No URL configured.");
      return;
    }

    shouldReconnect = config.autoReconnect;

    ws = new WebSocket(window.socket_url, config.protocols);

    ws.onopen = function (e) {
      dispatchEvent('open', e);
    };

    ws.onmessage = function (e) {
      console.log(e.data);
      dispatchEvent('message', e.data);
    };

    ws.onerror = function (e) {
      dispatchEvent('error', e);
    };

    ws.onclose = function (e) {
      dispatchEvent('close', e);
      if (shouldReconnect) {
        reconnectTimer = setTimeout(PyFrameConnections.connect, config.reconnectInterval);
      }
    };
  };

  /**
   * Send a JSON-encoded message to the server.
   * @param {Object} data - Payload to send.
   */
  PyFrameConnections.send = function (data) {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(data));
    } else {
      console.warn("PyFrameConnections: Connection not open.");
    }
  };

  /**
   * Close the WebSocket connection.
   * @param {number} [code=1000] - WebSocket close code.
   * @param {string} [reason="Normal Closure"] - Reason for closure.
   */
  PyFrameConnections.close = function (code = 1000, reason = "Normal Closure") {
    shouldReconnect = false;
    clearTimeout(reconnectTimer);
    if (ws) {
      ws.close(code, reason);
    }
  };

  // === Status Methods ===

  /**
   * Check if the connection is open.
   * @returns {boolean} True if connected.
   */
  PyFrameConnections.is_connected = function () {
    return ws && ws.readyState === WebSocket.OPEN;
  };

  /**
   * Check if the connection is closed.
   * @returns {boolean} True if disconnected.
   */
  PyFrameConnections.is_disconnected = function () {
    return !ws || ws.readyState === WebSocket.CLOSED;
  };

  // === Event API Shortcuts ===
  PyFrameConnections.on = addEventListener;
  PyFrameConnections.off = removeEventListener;
  PyFrameConnections.offAll = removeAllEventListeners;
  // Ensure window object exists in restricted environments
  if (!window) {
    window = {};
  }

  // Export to global scope
  window.PyFrameConnections = PyFrameConnections;
})();
