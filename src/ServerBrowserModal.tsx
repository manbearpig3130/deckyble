import React, { useState, FC, useRef, useEffect, ReactNode, Fragment, useContext } from 'react';
import { ServerAPI, ModalRoot, Field, TextField, ButtonItem, Dropdown, SingleDropdownOption, DropdownOption, ShowModalProps, showModal } from 'decky-frontend-lib';
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


    useEffect(() => {
        fetchServers();
        const ws = new WebSocket("ws://localhost:8765");
    
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
    
    
        return () => {
            ws.close();
        };
        }, []);



    return (
      <ModalRoot closeModal={closeModal}>
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
                onClick={(e) => console.log(e)}
                key={index}
              />
            )
            })}
          <div ref={messagesEndRef} />
        </div>
        <div style={{ display: "flex", justifyContent: "space-between" }}>
          <ButtonItem onClick={closeModal}>Close</ButtonItem>
        </div>
      </ModalRoot>
    );
  };