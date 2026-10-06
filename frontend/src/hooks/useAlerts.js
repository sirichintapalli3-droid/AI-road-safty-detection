import { useEffect, useState } from "react";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000/api";
const ALERTS_URL = API_URL.replace(/^http/, "ws") + "/ws/alerts";

export function useAlerts() {
  const [connected, setConnected] = useState(false);
  const [alerts, setAlerts] = useState([]);

  useEffect(() => {
    let socket;
    let reconnectTimer;
    let stopped = false;

    function connect() {
      socket = new WebSocket(ALERTS_URL);
      socket.onopen = () => setConnected(true);
      socket.onmessage = (event) => {
        setAlerts((current) => [JSON.parse(event.data), ...current].slice(0, 20));
      };
      socket.onclose = () => {
        setConnected(false);
        if (!stopped) reconnectTimer = window.setTimeout(connect, 3000);
      };
      socket.onerror = () => socket.close();
    }

    connect();
    return () => {
      stopped = true;
      window.clearTimeout(reconnectTimer);
      socket?.close();
    };
  }, []);

  return { connected, alerts };
}
