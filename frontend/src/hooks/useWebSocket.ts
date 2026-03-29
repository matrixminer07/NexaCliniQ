import { useEffect, useState } from 'react';
import { io } from 'socket.io-client';

const useWebSocket = () => {
  const [socket, setSocket] = useState<any>(null);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    const socketInstance = io('http://localhost:5000', {
      transports: ['websocket'],
      upgrade: true,
    });

    socketInstance.on('connect', () => {
      setConnected(true);
      console.log('WebSocket connected');
    });

    socketInstance.on('disconnect', () => {
      setConnected(false);
      console.log('WebSocket disconnected');
    });

    socketInstance.on('prediction_update', (data) => {
      console.log('Prediction update:', data);
    });

    socketInstance.on('financial_update', (data) => {
      console.log('Financial update:', data);
    });

    setSocket(socketInstance);
  }, []);

  return { socket, connected };
};

export default useWebSocket;
