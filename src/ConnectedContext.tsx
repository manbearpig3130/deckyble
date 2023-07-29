
import { useState, createContext } from "react";

export const ConnectionContext = createContext<{connected: boolean, setConnected: React.Dispatch<React.SetStateAction<boolean>>}>({
    connected: false,
    setConnected: () => {}
  });

export const ConnectionProvider = ({ children }: any ) => {
    const [connected, setConnected] = useState(false);
  
    return (
      <ConnectionContext.Provider value={{ connected, setConnected }}>
        {children}
      </ConnectionContext.Provider>
    );
  };