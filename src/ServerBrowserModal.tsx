import React, { useState, FC, useRef, useEffect, ReactNode, Fragment, useContext } from 'react';
import { ServerAPI, Router, ModalRoot, showContextMenu, Menu, MenuItem, Field, TextField, ButtonItem, Dropdown, SingleDropdownOption, DropdownOption, ShowModalProps, showModal } from 'decky-frontend-lib';
import { TransmittingContext } from './TransmittingContext';

interface PluginMethodResponse<T> {
    success: boolean;
    result: T;
  }

  type serv = {
    name: string;
    ip: string;
    port: number;
    url: string;
    country: string;
    country_code: string;
    ping: number;
    users: number;
    max_users: number;
  };

  export const ServerModalContent: FC<{ closeModal: () => void, serverAPI: ServerAPI }> = ({ closeModal, serverAPI }) => {
    const messagesEndRef = useRef<HTMLDivElement | null>(null);
    const [serversArray, setServersArray] = useState<any[]>([]);
    const [pingedArray, setPingedArray] = useState<any[]>([]);
    const ws = new WebSocket("ws://localhost:8765");
    const [connected, setConnected] = useState<boolean>(false);

    const handleConnect = async () => {
      //const { setConnected } = useContext(ConnectionContext);
       
      const response = await serverAPI.callPluginMethod("connect_server", { }) as PluginMethodResponse<{[channelName: string]: {users: {[username: string]: {muted: boolean, ID: number}}}} | boolean>;
      if (response.success && response.result !== false) {
        serverAPI.toaster.toast({
          title: 'Success',
          body: "Connected",
          duration: 1000,
          critical: false
        });
        setConnected(true);
    
      } else if (!response.success) {
        console.error("Failed to connect ");
        console.error(response);
      }
    };

    const getConnected = async () => {
      const connectedResponse = await serverAPI.callPluginMethod("getConnected", {}) as PluginMethodResponse<boolean>;
      if (connectedResponse.success) setConnected(connectedResponse.result);
      return connectedResponse.result;
    }

      const fetchServers = async () => {
        try {
          console.log("CUP OF PUBIC SERVERS");
          const serversResponse = await serverAPI.callPluginMethod("getPublicServers", {}) as PluginMethodResponse<[]>;
          console.log("GOT SERVERS TURDS", serversResponse.result);
          setServersArray(serversResponse.result);
          return serversResponse.result;
        } catch (error) {
          console.error("Failed to fetch messages:", error);
          return [];
        }
      };
      
    // const CountriesDropDown: FC<{serverAPI: ServerAPI }> = ( { serverAPI } ) =>  {
    // return(
    //     <Dropdown
    //     rgOptions={countries}
    //     selectedOption={selectedCountry}
    //     onChange={handleCountryChange}
    //     strDefaultLabel={selectedRecipient.name}
    //   />
    // )
    // }
    const sendAndClose = () => {
      ws.send(JSON.stringify({ type: 'stopPinging' }));
      console.log("SENT CUP OF CLOSURE");
      ws.close();
      closeModal();
    }

    const ServerMenu = ({serverLabel, isCurrentlyConnected}: {serverLabel: string, isCurrentlyConnected: boolean}) => {
      
      const conServer = async ( serverToJoin: string ) => {
        console.log("CUP OF CONMAN", serverToJoin)
        await serverAPI.callPluginMethod("setCurrentServer", {serverLabel}) as PluginMethodResponse<any>;
        handleConnect();
        sendAndClose();
      }

      const addServer = async ( serverToAdd: string ) => {
        console.log("CUP OF addMAN", serverToAdd)
        await serverAPI.callPluginMethod("setCurrentServer", {serverLabel}) as PluginMethodResponse<any>;
        sendAndClose();
        //Router.CloseSideMenus();
        Router.Navigate("/deckmumble/settings/form1");
      }
      
      return (
      <Menu label={serverLabel}>
        {!isCurrentlyConnected && <MenuItem onClick={() => conServer(serverLabel)}>Connect</MenuItem>}
        <MenuItem onClick={() => addServer(serverLabel)}>Add to saved servers</MenuItem>
      </Menu>
      )
  };

  const handleServerClick = (serverLabel: string, event: any) => {
    const retardedConnected = async () => {
      const connectedResponse = await serverAPI.callPluginMethod("getConnected", {}) as PluginMethodResponse<boolean>;
      if (connectedResponse.success) {
        setConnected(connectedResponse.result);
        console.log("WHERE IS MY RETARDMENT? " + connectedResponse.result)
        if (connectedResponse.result) {
          showContextMenu(<ServerMenu serverLabel={serverLabel} isCurrentlyConnected={true} />, event.target);
        }
        else {
          showContextMenu(<ServerMenu serverLabel={serverLabel} isCurrentlyConnected={false} />, event.target);
        }
      }
    };
    console.log("ARSE TERGINOODLE: ", serverLabel, event);
    retardedConnected();
    //showContextMenu(<ServerMenu serverLabel={serverLabel} isCurrentlyConnected={connected} />, event.target);
    console.log(connected);
  };

    useEffect(() => {
        getConnected();
        fetchServers();
        
    
        ws.addEventListener("open", async (event) => {
            console.log("WebSocket connection opened:", event);
        });
    
        ws.onmessage = (event) => {
            if (event.data){
            try{
                const data = JSON.parse(event.data);
    
                if (data && data.type === 'pingupdate') {
                    console.log('CUPPA PINGERS!', data.data);
                    setPingedArray(prevPingedArray => [...prevPingedArray, data.data]);
                }
            } catch (e) {
                console.log("Couldn't process data", e);
            }
            } else {
            console.log("No data received")
            }
        };

        window.addEventListener('beforeunload', () => {
          ws.send(JSON.stringify({ type: 'stopPinging' }));
        });
    
    
        return () => {
            ws.close();
        };
        }, []);



    return (
      <ModalRoot closeModal={sendAndClose}>
        <div
          style={{
            maxHeight: "200px", // adjust as needed
            overflowY: "auto", // adds a vertical scrollbar
            width: "95%", // adjust as needed
            padding: "1rem", // adjust as needed
            border: "1px solid #ccc", // adjust as needed
            textAlign: "left",
          }}
        >
          {(pingedArray || []).filter((serv) => serv.ping !== '').map((serv: serv, index) => {

            let pingStyle = { color: 'black'};
            if (typeof serv.ping === 'number') { // make sure ping is a number
              if (serv.ping < 50) {
                pingStyle = { color: 'green'};
              } else if (serv.ping < 120) {
                pingStyle = { color: 'orange'};
              } else {
                pingStyle = { color: 'red' };
              }
            }

            return(
              <Field
                
                label={
                  <Fragment>
                    <div style={{ flex: 0.7, textAlign: 'left' }}><span id="thing1">{serv.name + " - " + serv.ip}</span></div>
                    <div style={{ flex: 0.3, textAlign: 'right' }}>{serv.users + "/" + serv.max_users + " - "}<span style={pingStyle} id="thing2">{serv.ping}</span></div>
                  </Fragment>
                }
                className="field-text-left"
                onClick={(e: any) => handleServerClick(serv.name, e)}
                key={index}
              />
            )
            })}
          <div ref={messagesEndRef} />
        </div>
        <div style={{ display: "flex", justifyContent: "space-between" }}>
          <ButtonItem onClick={sendAndClose}>Close</ButtonItem>
        </div>
      </ModalRoot>
    );
  };