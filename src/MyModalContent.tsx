import React, { useState, FC, useRef, useEffect, ReactNode, useContext, Fragment } from 'react';
import { ServerAPI, MenuItem, Menu, DropdownOption, SingleDropdownOption, Dropdown, ModalRoot, Field, ButtonItem, TextField } from 'decky-frontend-lib';
import { ModalContext } from './ModalContext';

type Message = {
    actor: string;
    message: string;
    time: string;
  };


  interface PluginMethodResponse<T> {
    success: boolean;
    result: T;
  }

export const MyModalContent: FC<{ closeModal: () => void }> = ({ closeModal }) => {
    const [value, setValue] = useState("");
    const [localMessagesArray, setLocalMessagesArray] = useState<Message[]>(
      []
    );
    const messagesEndRef = useRef<HTMLDivElement | null>(null);

    type RecipientDropdownProps = {
        selectedRecipient: { ID: number; name: string };
        setSelectedRecipient: React.Dispatch<
          React.SetStateAction<{ ID: number; name: string }>
        >;
      };

    const RecipientDropdown: FC<RecipientDropdownProps> = ({
        selectedRecipient,
        setSelectedRecipient,
      }) => {
        const [items, setItems] = useState<DropdownOption[]>([]);
    
        const handleRecipientChange = (selectedOption: SingleDropdownOption) => {
          setSelectedRecipient({
            ID: selectedOption.data as number,
            name: selectedOption.label as string,
          });
          console.log("Updated selectedRecipient state with:", selectedOption);
        };
    
        useEffect(() => {
          const fetchItems = async () => {
            const response = (await server.callPluginMethod(
              "get_users_list",
              {}
            )) as PluginMethodResponse<Array<{ ID: number; name: string }>>;
            console.log(
              "TERGIDSON FETUS MC DROPDOWN",
              response.result,
              response.success
            );
            if (response.success) {
              const mappedItems: DropdownOption[] = response.result.map((item) => ({
                data: item.ID,
                label: item.name,
              }));
    
              // Add channel option
              mappedItems.push({
                data: -1, // or whatever ID signifies "Channel" in your setup
                label: "Channel",
              });
    
              setItems(mappedItems);
              console.log("JOHNSON FETUS FISH", items);
            }
          };
    
          fetchItems();
          console.log("Recipient options refreshed");
        }, []);
    
        return (
          <Dropdown
            rgOptions={items}
            selectedOption={selectedRecipient}
            onChange={handleRecipientChange}
            strDefaultLabel={selectedRecipient.name || "Channel"}
            menuLabel={"Ass Cunt"}
          />
        );
      };

    const sendChatMsg = async (msg: any) => {
        console.log(msg);
        (await erverAPI.callPluginMethod("send_text_message_to_server", {
          msg,
        })) as PluginMethodResponse<any>;
      };
    
      const sendDM = async (usersession: number, msg: any) => {
        console.log("ASS FACE SENDING DM", usersession, msg);
        const result = (await server.callPluginMethod("send_text_message_to_user", {
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

    const handleSendButton = async (e) => {
      await sendChatMsg(value);
      setValue("");
      const newMessagesArray = await fetchMessages();
      setLocalMessagesArray(newMessagesArray);
      //fetchMessages();
      // closeModal();
    };

    const handleKeyPress = async (e) => {
      if (e.key === "Enter") {
        if (selectedRecipient.name == "Channel") {
          await sendChatMsg(value);
          console.log("TERDS");
          setValue("");
          const newMessagesArray = await fetchMessages();
          setLocalMessagesArray(newMessagesArray);
        } else {
          await sendDM(selectedRecipient.ID, value);
          console.log("DM TERDS", selectedRecipient.ID, value);
          setValue("");
          const newMessagesArray = await fetchMessages();
          setLocalMessagesArray(newMessagesArray);
        }
      }
    };

    const turd = (e) => {
      console.log("FUCKING ASS");
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
              onClick={(e) => turd(e)}
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
            <RecipientDropdown
              selectedRecipient={selectedRecipient}
              setSelectedRecipient={setSelectedRecipient}
            />
          </div>
        </div>

        <div style={{ display: "flex", justifyContent: "space-between" }}>
          <ButtonItem onClick={closeModal}>Close</ButtonItem>
          <ButtonItem onClick={handleSendButton}>Send</ButtonItem>
        </div>
      </ModalRoot>
    );
  };