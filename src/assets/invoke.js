/**
 * PyFrame frontend connection bootstrap.
 *
 * Provides a Promise-based `invoke(cmd, args)` API that communicates
 * with the backend via PyFrameConnections (WebSocket).
 *
 * Features:
 *  - Auto reconnect with configurable interval.
 *  - Unique ID mapping for result/error callbacks.
 *  - Automatic cleanup of one-time callbacks.
 *  - Global `window.invoke` helper for command dispatch.
 */
(function () {
  // Configure automatic reconnect
  PyFrameConnections.configure({
    reconnectInterval: 5000,
    autoReconnect: true
  });

  // Start WebSocket connection
  PyFrameConnections.connect();

  /**
   * Generate a random unique identifier.
   * @returns {number} Unique 32-bit integer.
   */
  function uid() {
    return window.crypto.getRandomValues(new Uint32Array(1))[0];
  }

  /**
   * Register a callback bound to a unique window property.
   * Automatically cleans up if marked as `once`.
   *
   * @param {Function} callback - The callback function.
   * @param {boolean} once - Whether to remove callback after first call.
   * @returns {number} Unique identifier for callback.
   */
  function transformCallback(callback, once) {
    const identifier = uid();
    const prop = `_${identifier}`;
    Object.defineProperty(window, prop, {
      value: (result) => {
        if (once) Reflect.deleteProperty(window, prop);
        return callback && callback(result);
      },
      writable: false,
      configurable: true
    });
    return identifier;
  }

  /**
   * Invoke a backend command via PyFrameConnections.
   *
   * @param {string} cmd - Command name.
   * @param {any} [args] - Payload arguments (any serializable type).
   * @returns {Promise<any>} Resolves with result of any type, rejects with error.
   */
  function invoke(cmd, args) {
    return new Promise((resolve, reject) => {
      if (!PyFrameConnections.is_connected()) {
        reject(new Error("Socket is not connected or unavailable!"));
        return;
      }

      const result_id = transformCallback((result) => resolve(result), true);
      const error_id = transformCallback((error) => reject(error), true);

      const message = {
        cmd,
        result_id,
        error_id,
        payload: args
      };

      PyFrameConnections.send(message);
    });
  }

  // Listen for backend messages and dispatch to registered callbacks
  PyFrameConnections.on("message", (raw) => {
    try {
      console.log(raw);
      const data = JSON.parse(raw);
      const { result_id, error_id, result, error } = data;

      if (result_id) {
        const prop = `_${result_id}`;
        if (window[prop]) window[prop](result);
      }

      if (error_id) {
        const prop = `_${error_id}`;
        if (window[prop]) window[prop](error);
      }
    } catch (err) {
      console.warn("Invalid message received:", raw);
    }
  });

  // Expose invoke globally
  window.invoke = invoke;
})();
