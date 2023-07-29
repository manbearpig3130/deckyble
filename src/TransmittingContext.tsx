import React, { useState, FC, useRef, useEffect, ReactNode } from 'react';
import { ServerAPI } from 'decky-frontend-lib';

type Message = {
  actor: string;
  message: string;
  time: string;
};

interface TransmittingProviderProps {
  children: ReactNode;
  serverAPI: ServerAPI;
}

interface PluginMethodResponse<T> {
  success: boolean;
  result: T;
}
  
export const TransmittingContext = React.createContext<{ 
  transmittingUsers: string[];
  setTransmittingUsers: React.Dispatch<React.SetStateAction<string[]>>;
  transmittingUsersRef: React.MutableRefObject<string[]>;
  messagesArray: Message[];
  setMessagesArray: React.Dispatch<React.SetStateAction<Message[]>>;
  fetchMessages: Function;
  //messagesArrayRef: React.MutableRefObject<Message[]>;
}>({ 
  transmittingUsers: [], 
  setTransmittingUsers: () => {},
  transmittingUsersRef: { current: [] },  // New
  messagesArray: [],
  setMessagesArray: () => {},
  fetchMessages: async () => {},
  //messagesArrayRef: { current: [] } 
});

  
export const TransmittingProvider: FC<TransmittingProviderProps> = ({ children, serverAPI }) => {
  const [transmittingUsers, setTransmittingUsers] = useState<string[]>([]);
  const transmittingUsersRef = useRef(transmittingUsers);  // New
  const userTimeoutsRef = useRef({});
  const [messagesArray, setMessagesArray] = useState<Message[]>([]);

  const fetchMessages = async () => {
    try {
      const messages = await serverAPI.callPluginMethod("getMessagesArray", {}) as PluginMethodResponse<string[]>;
      console.log("Trying message pARSE", messages.result);
      const parsedMessages = messages.result.map(messageString => JSON.parse(messageString));
      console.log("pARSED", parsedMessages);
      setMessagesArray(parsedMessages);
      return parsedMessages;
    } catch (error) {
      console.error("Failed to fetch messages:", error);
      return [];
    }
  };

  // Update your reference whenever the state changes
  useEffect(() => {
    transmittingUsersRef.current = transmittingUsers;
  }, [transmittingUsers]);

  useEffect(() => {
    const ws = new WebSocket("ws://localhost:8765");

    ws.addEventListener("open", async (event) => {
      console.log("WebSocket connection opened:", event);
    });

    ws.onmessage = (event) => {
      if (event.data){
        try{
          const data = JSON.parse(event.data);

          if (data && data.type === 'update') {
            console.log('re-rendering channelsandusers', data);
            setTransmittingUsers([...transmittingUsersRef.current]);
            if (data.reason === 'Kicked'){
              console.log("got kicked")
              serverAPI.toaster.toast({
                title: 'Disconnected',
                body: 'You got kicked',
                duration: 2500,
                critical: false
              });
            }
          }

          if (data && data.type === 'message') {
            console.log('Got message: ', data);
            serverAPI.toaster.toast({
              title: 'Received message from ' + data.actor,
              body: data.message,
              duration: 2500,
              critical: false
            });
            const newMessage = { actor: data.actor, message: data.message, time: data.time };
            setMessagesArray((prevMessages) => [...prevMessages, newMessage]);
          }
          
          if (data && data.type === 'user_transmitting') {
            console.log(data.username);

            // If there's an existing timeout for this user, clear it
            if (userTimeoutsRef.current[data.username]) {
              clearTimeout(userTimeoutsRef.current[data.username]);
            }

            // Add the user to the transmitting users list if they're not already there
            if (!transmittingUsersRef.current.includes(data.username)) {
              setTransmittingUsers((prevUsers) => [...prevUsers, data.username]);
            }

            userTimeoutsRef.current[data.username] = setTimeout(() => {
              setTransmittingUsers((prevUsers) => prevUsers.filter((user) => user !== data.username));
              delete userTimeoutsRef.current[data.username];
            }, 500);
          }
        } catch (e) {
          console.log("Couldn't process data", e);
        }
      } else {
        console.log("No data received")
      }
    };


    return () => {
      ws.close();
    };
  }, []);

  return (
    <TransmittingContext.Provider value={{ transmittingUsers, setTransmittingUsers, transmittingUsersRef, messagesArray, setMessagesArray, fetchMessages}}>
      {children}
    </TransmittingContext.Provider>
  );
};
