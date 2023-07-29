import React, { useState, FC, useRef, useEffect, ReactNode, Fragment, useContext } from 'react';
import { ServerAPI, ModalRoot, Field, TextField, ButtonItem, Dropdown, SingleDropdownOption, DropdownOption, ShowModalProps, showModal } from 'decky-frontend-lib';
import { TransmittingContext } from './TransmittingContext';

interface PluginMethodResponse<T> {
    success: boolean;
    result: T;
  }

  interface ModalProviderProps {
    children: ReactNode;
    serverAPI: ServerAPI;
  }

interface IModalContext {
    handleOpenModal: () => void;
    setSelectedRecipient: React.Dispatch<React.SetStateAction<{ID: number, name: string}>>
    selectedRecipient: { ID: number, name: string };
  }
  type Message = {
    actor: string;
    message: string;
    time: string;
  };

  export const ModalContext = React.createContext<IModalContext>({
    handleOpenModal: () => {},
    setSelectedRecipient: () => {},
    selectedRecipient: { ID: 0, name: "Channel" }
  });

  export const ModalContextProvider: FC<ModalProviderProps> = ({ children, serverAPI }) => {
    const { selectedRecipient, setSelectedRecipient } = useContext(ModalContext);
    const [closeModal, setCloseModal] = useState<(() => void) | null>(null);
    // const messagesArray = useContext(TransmittingContext)
    console.log('ModalContextProvider rendered, selectedRecipient:', selectedRecipient);

    const handleOpenModal = () => {
        console.log("CUP OF MODAL?");
        const modalProps: ShowModalProps = {
            strTitle: 'My Modal',
            bHideMainWindowForPopouts: false,
            fnOnClose: () => console.log("Modal closed")
        };
        const modalResult = showModal(<MyModalContent serverAPI={serverAPI} closeModal={() => closeModal?.()} />, undefined, modalProps);
        setCloseModal(() => modalResult.Close);
    };

    useEffect(() => {
        const getSelectedRecipientBackend = async () => {
          const response = await serverAPI.callPluginMethod("get_selected_recipient", {}) as PluginMethodResponse<Array<{ ID: number; name: string; }>>;    
          if (response.success) {
            console.log("BACKEDN TERGIS", response.result);
          }
          if (response.success) {setSelectedRecipient({ID: response.result['ID'], name: response.result['name']});}
          };
          getSelectedRecipientBackend();
      }, [selectedRecipient]);

    console.log("ModalProvider selectedRecipient:", selectedRecipient);
    // Provide the current state and functions to all children
    return (
      <ModalContext.Provider
        value={{
          handleOpenModal,
          setSelectedRecipient,
          selectedRecipient
        }}
      >
        {children}
      </ModalContext.Provider>
    );
  };


  const RecipientDropdown: FC<{serverAPI: ServerAPI }> = ( { serverAPI } ) =>  {
    // const { selectedRecipient, setSelectedRecipient } = useContext(ModalContext)
    const [items, setItems] = useState<DropdownOption[]>([]);
    const [selectedRecipient, setSelectedRecipient] = useState<{ ID: number; name: string }>({ID: 0, name: "Channel"})

    const handleRecipientChange = async (selectedOption: SingleDropdownOption) => {
        // setSelectedRecipient({ID: selectedOption.data as number, name: selectedOption.label as string});
        console.log("Updating selectedInputDevice state with:", selectedOption);
        await serverAPI.callPluginMethod("set_selected_recipient", { ID: selectedOption.data as number, name: selectedOption.label as string })
      };

      const getSelectedRecipientBackend = async () => {
        const response = await serverAPI.callPluginMethod("get_selected_recipient", {}) as PluginMethodResponse<Array<{ ID: number; name: string; }>>;    
        if (response.success) {
          console.log("BACKEDN TERGIS", response.result);
        }
        if (response.success) {setSelectedRecipient({ID: response.result['ID'], name: response.result['name']});}
        return {ID: response.result['ID'], name: response.result['name']}
        };

        const fetchItems = async (): Promise<DropdownOption[]> => {
            const response = await serverAPI.callPluginMethod(
              "get_users_list",
              {}
            ) as PluginMethodResponse<Array<{ ID: number; name: string }>>;
            if (response.success) {
              const mappedItems: DropdownOption[] = response.result.map((item) => ({
                data: item.ID,
                label: item.name,
              }));
              mappedItems.push({
                data: 0, 
                label: "Channel",
              });
              setItems(mappedItems)
              // Fetch and set the latest recipient from backend here
              await getSelectedRecipientBackend();
              return mappedItems;
            }
            return []; // return an empty array when response.success is false
        };
        

      useEffect(() => {
          fetchItems()
      }, []);

    useEffect(() => {
        console.log("Updated selectedRecipient state with A CUP OF TERGID!!:", selectedRecipient);
    }, [selectedRecipient]);


    return (
      <Dropdown
        rgOptions={items}
        selectedOption={selectedRecipient}
        onChange={handleRecipientChange}
        strDefaultLabel={selectedRecipient.name}
      />
    );
  };


  const MyModalContent: FC<{ closeModal: () => void, serverAPI: ServerAPI }> = ({ closeModal, serverAPI }) => {
    const [value, setValue] = useState("");
    const { messagesArray } = useContext(TransmittingContext);
    const { selectedRecipient, setSelectedRecipient }  = useContext(ModalContext);
    const [localMessagesArray, setLocalMessagesArray] = useState<Message[]>(
      []
    );
    const messagesEndRef = useRef<HTMLDivElement | null>(null);

      const fetchMessages = async () => {
        try {
            console.log("CUP OF ASS MODAL");
          const messages = await serverAPI.callPluginMethod("getMessagesArray", {}) as PluginMethodResponse<string[]>;
          const parsedMessages = messages.result.map(messageString => JSON.parse(messageString));
          console.log("FEETINOOS", messages.result);
          console.log(parsedMessages);
          setLocalMessagesArray(parsedMessages);
          return parsedMessages;
        } catch (error) {
          console.error("Failed to fetch messages:", error);
          return [];
        }
      };
    
      useEffect(() => {
        fetchMessages()
      }, [])


    const sendChatMsg = async (msg: any) => {
        console.log(msg);
        (await serverAPI.callPluginMethod("send_text_message_to_server", {
          msg,
        })) as PluginMethodResponse<any>;
      };
    
      const sendDM = async (usersession: number, msg: any) => {
        console.log("ASS FACE SENDING DM", usersession, msg);
        const result = (await serverAPI.callPluginMethod("send_text_message_to_user", {
          usersession,
          msg,
        })) as PluginMethodResponse<any>;
        console.log(result);
      };

    useEffect(() => {
      setLocalMessagesArray([...messagesArray]);
    }, [messagesArray]);

    useEffect(() => {
      const ws = new WebSocket("ws://localhost:8765");

      ws.addEventListener("open", async (event) => {
        console.log("WebSocket connection opened:", event);
      });

      ws.onmessage = (event) => {
        if (event.data) {
          try {
            const data = JSON.parse(event.data);

            if (data && data.type === "update") {
              console.log("re-rendering Modal Terd?", data);
            }

            if (data && data.type === "message") {
              console.log("Got message: ", data);
              const newMessage = {
                actor: data.actor,
                message: data.message,
                time: data.time,
              };
              setLocalMessagesArray((prevMessages) => [
                ...prevMessages,
                newMessage,
              ]);
            }
          } catch (e) {
            console.log("Couldn't process data", e);
          }
        } else {
          console.log("No data received");
        }
      };

      return () => {
        ws.close();
      };
    }, []);

    useEffect(() => {
      if (messagesEndRef.current) {
        messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
      }
    }, [localMessagesArray]);

    const handleSendButton = async (e: any) => {
        const response = await serverAPI.callPluginMethod("get_selected_recipient", {}) as PluginMethodResponse<Array<{ ID: number; name: string; }>>; 
        console.log(response.result, e)
        setSelectedRecipient({ ID: response.result['ID'], name: response.result['name']})
        console.log(selectedRecipient.name);
        if (response.result['name'] === "Channel") {
          await sendChatMsg(value);
          console.log("TERDS");
          setValue("");
          const newMessagesArray = await fetchMessages();
          setLocalMessagesArray(newMessagesArray);
        } else {
          console.log("Johnny Tergid?");
          await sendDM(response.result['ID'], value);
          console.log("DM TERDS", response.result['ID'], value);
          setValue("");
          const newMessagesArray = await fetchMessages();
          setLocalMessagesArray(newMessagesArray);
        }
    };

    const handleKeyPress = async (e: any) => {
      if (e.key === "Enter") {
        const response = await serverAPI.callPluginMethod("get_selected_recipient", {}) as PluginMethodResponse<Array<{ ID: number; name: string; }>>; 
        console.log(response.result)
        setSelectedRecipient({ ID: response.result['ID'], name: response.result['name']})
        console.log(selectedRecipient.name);
        if (response.result['name'] === "Channel") {
          await sendChatMsg(value);
          console.log("TERDS");
          setValue("");
          const newMessagesArray = await fetchMessages();
          setLocalMessagesArray(newMessagesArray);
        } else {
          console.log("Johnny Tergid?");
          await sendDM(response.result['ID'], value);
          console.log("DM TERDS", response.result['ID'], value);
          setValue("");
          const newMessagesArray = await fetchMessages();
          setLocalMessagesArray(newMessagesArray);
        }
      }
    };


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
          {localMessagesArray.map((message, index) => (
            <Field
              label={
                <Fragment>
                  {"[" + message.time + "] "}
                  &nbsp;
                  <strong>
                    {" "}
                    <span style={{ color: "green" }}>{message.actor}</span>:
                  </strong>
                  &nbsp;
                  <span
                    id="thing1"
                    dangerouslySetInnerHTML={{ __html: message.message }}
                  ></span>
                </Fragment>
              }
              className="field-text-left"
              onClick={(e) => console.log(e)}
              key={index}
            />
          ))}
          <div ref={messagesEndRef} />
        </div>

        <div style={{ display: "flex", justifyContent: "stretch" }}>
          <div style={{ flex: 1 }}>
            <TextField
              label="Enter Text"
              onChange={(e) => setValue(e.target.value)}
              value={value}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  handleKeyPress(e);
                }
              }}
            />
          </div>
          <div style={{ paddingTop: "23px" }}>
            <RecipientDropdown serverAPI={serverAPI} />
          </div>
        </div>

        <div style={{ display: "flex", justifyContent: "space-between" }}>
          <ButtonItem onClick={closeModal}>Close</ButtonItem>
          <ButtonItem onClick={handleSendButton}>Send</ButtonItem>
        </div>
      </ModalRoot>
    );
  };