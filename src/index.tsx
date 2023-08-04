import {
  ButtonItem,
  definePlugin,
  Menu,
  MenuItem,
  PanelSection,
  PanelSectionRow,
  Router,
  ServerAPI,
  showContextMenu,
  staticClasses,
  Field,
  Tabs,
  ToggleField
} from "decky-frontend-lib";


import { FC, VFC, useState, useEffect, useRef, createContext, useContext, Fragment } from "react";
import React from 'react';
import { FaShip } from "react-icons/fa";
import { TransmittingContext, TransmittingProvider } from './TransmittingContext';
import { ModalContext, ModalContextProvider } from './ModalContext';
import { ConnectionContext, ConnectionProvider } from './ConnectedContext';
interface PluginMethodResponse<T> {
  success: boolean;
  result: T;
}
import SettingsPage from "./SettingsPage";

const Content: VFC<{ server: (ServerAPI) }> = ({server}) => {

//const [connected, setConnected] = useState(false);
const { setConnected } = useContext(ConnectionContext);

interface MuteContextData {
  muted: boolean;
  setMuted: React.Dispatch<React.SetStateAction<boolean>>;
}

const { transmittingUsers } = useContext(TransmittingContext);

const MuteContext = createContext<MuteContextData>({ muted:false, setMuted: () => {}});
const MuteProvider = ({ children }: any) => {
  const [muted, setMuted] = useState(false);

  return (
    <MuteContext.Provider value={{ muted, setMuted }}>
      {children}
    </MuteContext.Provider>
  );
};

useEffect(() => {
  const fetchInitialState = async () => {
    const connectedResponse = await server.callPluginMethod("getConnected", {}) as PluginMethodResponse<boolean>;
    if (connectedResponse.success) setConnected(connectedResponse.result);
  };
  fetchInitialState();
  console.log("got initial turd")
}, []);

useEffect(() => {
  console.log("TRANSMISSION")
  console.log(transmittingUsers);
  //transmittingUsersRef.current = transmittingUsers;
}, [transmittingUsers]);

interface IUserMenuProps {
  userID: number;
  userName: string;
}

useEffect(() => {
  const handleKeyDown = (event: any) => {
      console.log('A key was pressed', event.key);
  };

  window.addEventListener('keydown', handleKeyDown);

  return () => {
      // Don't forget to remove the event listener when the component unmounts
      window.removeEventListener('keydown', handleKeyDown);
  };
}, []);


const ChannelMenu = ({ channel }: any) => (
  <Menu label={channel}>
    <MenuItem onClick={() => moveChannel(channel)}>Join</MenuItem>
  </Menu>
);

const moveChannel = async (channelName: any) => {
  const response = await server.callPluginMethod("move_to_channel", { channelName })
  if (response.success) {
    server.toaster.toast({
      title: 'Moved to channel',
      body: channelName,
      duration: 1000,
      critical: false
    })
  } else{
    console.log("Where's my turgidson?")
    console.log(response)
    console.log(channelName)
    console.log(response.result)
}
};

const handleDisconnect = async () => {
  //const { setConnected } = useContext(ConnectionContext);

    const response = await server.callPluginMethod("leave_server", { })
    if (response.success) {
      server.toaster.toast({
        title: 'Disconnected',
        body: "farts",
        duration: 1000,
        critical: false
      })};
    setConnected(false);
  }

const handleConnect = async () => {
  //const { setConnected } = useContext(ConnectionContext);
   
  const response = await server.callPluginMethod("connect_server", { }) as PluginMethodResponse<{[channelName: string]: {users: {[username: string]: {muted: boolean, ID: number}}}} | boolean>;
  if (response.success && response.result !== false) {
    server.toaster.toast({
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


const handleSettingsClick = () => {
  Router.CloseSideMenus();
  Router.Navigate("/deckmumble/settings/form1");
};

const Tab1Component: FC = () => {
  const { messagesArray, fetchMessages } = useContext(TransmittingContext);
  const { handleOpenModal } = useContext(ModalContext);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  // const [selectedRecipient, setSelectedRecipient] = useState<{ ID: number; name: string }>({ID: 0, name: "Channel"});

  useEffect(() => {
    fetchMessages();
  }, []);

  return(
    <div>
    <PanelSection>
      <div style={{ 
          maxHeight: '220px', // adjust as needed
          overflowY: 'auto', // adds a vertical scrollbar
          width: '95%', // adjust as needed
          padding: '1rem', // adjust as needed
          textAlign: 'left'
        }}>
          {messagesArray.map((message, index) => (
            <PanelSectionRow>
            <Field 
            label={(
              <Fragment>
                <strong> <span style={{ color: "green" }}>{message.actor}</span>:</strong>
                &nbsp;
                <span id="thing1" dangerouslySetInnerHTML={{__html: message.message}}></span>
              </Fragment>
            )}
            className="field-text-left" 
            onClick={(e) => console.log(e)} 
            key={index}
          />
          </PanelSectionRow>
          ))}
          <div ref={messagesEndRef} />
        </div>
        </PanelSection>
        <PanelSection>
        <PanelSectionRow>
        <ButtonItem layout="below" onClick={handleOpenModal}>Send message</ButtonItem>
      </PanelSectionRow>
    </PanelSection>
    </div>
  );
};

const MuteToggle: FC = () => {
  const { muted, setMuted } = useContext(MuteContext);

  const getMutedStatus = async () => {
    const mutedResponse = await server.callPluginMethod("getMuted", {}) as PluginMethodResponse<boolean>;
    setMuted(mutedResponse.result);
  };
  const handleUnmute = async () => {
    await server.callPluginMethod("unmute", { })
    setMuted(false);
    console.log("unmuted.");
  };
  const handleMuteClick = async () => {
    await server.callPluginMethod("mute", { })
    console.log("muted.");
    setMuted(true);
  };
  useEffect(() => {
    getMutedStatus();
    console.log("mutetoggle ASSCUNT.");
  }, []);
  useEffect(() => {
    getMutedStatus();
    console.log("muted state FARTED");
  }, [muted]);

  return(
    <ToggleField
          label="Mute"
          checked={muted}
          onChange={(checked) => {
            if (checked) {
              handleMuteClick();
            } else {
              handleUnmute();
            }
          }}
        />
  )
}

const DeafToggle: FC = () => {
  const [deafened, setDeafened] = useState(false);
  const { setMuted } = useContext(MuteContext);

  const getDeafStatus = async () => {
    const deafResponse = await server.callPluginMethod("getDeafened", {}) as PluginMethodResponse<boolean>;
    setDeafened(deafResponse.result);
  }
  const handleUndeafen = async () => {
    await server.callPluginMethod("undeafen", { })
    setDeafened(false);
    console.log("undeafened.");
  };
  const handleDeafen = async () => {
    await server.callPluginMethod("deafen", { })
    setDeafened(true);
    setMuted(true);
    console.log("deafened.");
  };
  useEffect(() => {
    getDeafStatus();
    console.log("deaftoggle farts.");
  }, []);

  return(
    <ToggleField
          label="Deafen"
          checked={deafened}
          onChange={(checked) => {
            if (checked) {
              handleDeafen();
            } else {
              handleUndeafen();
            }
          }}
        />
  )
}

const ChannelsAndUsers: FC = () => {
  const { connected, setConnected } = useContext(ConnectionContext);
  const { handleOpenModal, setSelectedRecipient } = useContext(ModalContext);
  const { transmittingUsers } = useContext(TransmittingContext);
  const [channels, setChannels] = useState<{[channelName: string]: {users: {[username: string]: {muted: boolean, ID: number}}}}>({});
  const [users, setUsers] = useState<{[username: string]: {muted: boolean}}>({});
  const [serverName, setServerName] = useState("General Tergidson")


  const getSelectedServer = async () => {
    console.log("GETTING TERGIDSON NAME: ")
    //const serverNameResponse = await server.callPluginMethod("settings_getSetting", { key: "label", defaults: "None selected" }) as PluginMethodResponse<string>
    const currentServer = await server.callPluginMethod("getCurrentServer", {}) as PluginMethodResponse<{host: string, port: string, username: string, password: string, label: string}>;
    setServerName(currentServer.result.label)
    console.log("GOT TERGIDSON NAME: ", currentServer.result.label);
  }

  const fetchChannelsAndUsers = async () => {
    console.log("fetchChannelsAndUsers called");
    const isconnected = await server.callPluginMethod("getConnected", {}) as PluginMethodResponse<boolean>;
    const response = await server.callPluginMethod("get_channels_and_users", {}) as PluginMethodResponse<{[channelName: string]: {users: {[username: string]: {muted: boolean, ID: number}}}}>;
    console.log(response.result, response.success)
    if (response.success) {
      console.log("Received channels data:", response.result);
      setChannels(response.result);
      const userMuteStatus = Object.values(response.result).reduce((acc, channel) => {
        Object.entries(channel.users).forEach(([username, { muted }]) => {
          acc[username] = { muted };
        });
        return acc;
      }, {});
      setUsers(userMuteStatus);
    }
    if (isconnected.success) {
      //setCupoffart(isconnected.result)
      console.log(users);
      setConnected(isconnected.result);
    }
  };


const UserMenu: FC<IUserMenuProps> = ({ userID, userName }) => {
  
  console.log('Modal context:', handleOpenModal);
  
  return (
    <Menu label={userName}>
      <MenuItem onClick={() => console.log(`Mute user: ${userName}`)}>Local Mute</MenuItem>
      <MenuItem onClick={async () => {
        console.log("TRYING MODAL FART");
        console.log("handleOpenModal function: ", handleOpenModal);
        setSelectedRecipient({ ID: userID, name: userName });
        await server.callPluginMethod("set_selected_recipient", { ID: userID as number, name: userName as string })
        handleOpenModal();
        console.log("TERGINAL DENSE", userID, userName);
        }}>Send Message</MenuItem>
      <MenuItem onClick={() => console.log(`Kick user: ${userName}`)}>Kick</MenuItem>
    </Menu>
  );
};

  const handleUserClick = (username: string, userID: number, event: any) => {
    showContextMenu(<UserMenu userID={userID} userName={username} />, event.target);
  };
  
  const handleChannelClick = (channelName: string, event: any) => {
    showContextMenu(<ChannelMenu channel={channelName} />, event.target);
  };

  const fetchInitialData = async () => {
    const isconnected = await server.callPluginMethod("getConnected", {}) as PluginMethodResponse<boolean>;
    if (isconnected.result){
      console.log("Fetching initial channels and users");
      //setCupoffart(isconnected.result)
      setConnected(isconnected.result)
      fetchChannelsAndUsers();
      
    } else {
      setUsers({})
    }
  }
  const fetchconnected = async () => {
    const isconnected = await server.callPluginMethod("getConnected", {}) as PluginMethodResponse<boolean>;
    if (isconnected.result){
      console.log("CUPOF TERGISMENT");
      //setCupoffart(isconnected.result)
      setConnected(isconnected.result)
      return(isconnected.result);
    } else {
      return(false)
    }
  }


  useEffect(() => {
    fetchInitialData();
    getSelectedServer();
  }, []);

  useEffect(() => {
    fetchconnected()
    console.log("updating channels and users");
    fetchChannelsAndUsers();
    console.log("SHARTY PANTS");
    console.log(transmittingUsers)
  }, [connected, transmittingUsers]);

  return (
    
    <div>
      {connected ? (<div> {"Connected to " + serverName} </div>) : ( <div> {"Server: " + serverName} <br /> {"Not Connected"} </div> )}
    <div>
      {Object.entries(channels).map(([channelName, { users }], channelIndex) => (
        <Fragment key={`channel-${channelIndex}`}>
          <PanelSectionRow>
            <Field label={`-${channelName}`} onClick={(e) => handleChannelClick(channelName, e)} />
          </PanelSectionRow>
          {Object.entries(users).map(([username, user], userIndex) => (
            <PanelSectionRow>
              <div style={{ paddingLeft: '20px' }}>
                {user.muted ? (
                  <Field 
                  onClick={(e) => handleUserClick(username, user.ID, e)}
                  label={<span style={{ color: "red" }}>{username}</span>} 
                />
                ) : (
                  transmittingUsers.includes(username) ? (
                    <Field 
                      onClick={(e) => handleUserClick(username, user.ID, e)}
                      label={<span style={{ color: "green" }}>{username}</span>} 
                    />
                  ) : (
                  <Field label={username} key={`user-${userIndex}`} onClick={(e) => handleUserClick(username, user.ID, e)} />
                )
                )}
              </div>
            </PanelSectionRow>
            
          ))}
          
        </Fragment>
        
      ))}
    </div>
    <PanelSectionRow>
    <ConnectButton connected={connected}/>
  </PanelSectionRow>
  </div>
  );
};

const ConnectButton: FC<{ connected: boolean }> = ({connected}) => {
  useEffect(() => {
    console.log("Button has Fetussed.");
  }, []);

  useEffect(() => {
    console.log("Button has Fetussed again.");
  }, [connected]);

  return(
    <ButtonItem layout="below" onClick={connected ? handleDisconnect : handleConnect}>
        {connected ? "Disconnect" : "Connect"}
      </ButtonItem>
  )
}

const PTTButton: FC = () => {
  const handlePTT = async () => {
    console.log("PTT");
    const fart = await server.callPluginMethod("setTransmitting", { value: true })
    console.log(fart)
  }

  const handleNoPTT = async () => {
    console.log(" no PTT");
    const fart = await server.callPluginMethod("setTransmitting", { value: false })
    console.log(fart)
  }

  return( 
    <ButtonItem layout="below" onClick={handlePTT} onMouseDown={handlePTT} onTouchStart={handlePTT} onMouseUp={handleNoPTT} onTouchEnd={handleNoPTT}>
        {"PTT"}
      </ButtonItem>
  )
}

const Tab2Component: FC = () => {
  
  return(
    <div style={{ height: "100%", overflowY: "auto" }}>
    <MuteProvider>
    <PanelSection>
      <ChannelsAndUsers />
    </PanelSection>
    <PanelSection>


    <PanelSectionRow>
      <div style={{ display: "flex", justifyContent: "space-between"}}>
        <div>
        <MuteToggle/>
        </div>
        <div>
        <DeafToggle/>
        </div>
      </div>
    </PanelSectionRow>
    <PanelSectionRow>
      <ButtonItem layout="below" onClick={handleSettingsClick}>
        Settings
      </ButtonItem>
    </PanelSectionRow>
    

  </PanelSection>
  </MuteProvider>
  </div>
  )
};

const Tab3Component: FC = () => {

  const [pings, setPings] = useState({});
  //const [isConnected, setisConnected] = useState(false)
  const { setConnected } = useContext(ConnectionContext);
  const [focusedItem, setFocusedItem] = useState<number | null>(null);
  


  interface Server{
    host: string;
    port: string;
    label: string;
  }
  const [servers, setServers] = useState<Server[]>([]);

  const fetchPing = async (ip: string, port: string) => {
    console.log('pines', ip, port)
    const response = await server.callPluginMethod("pingServer", { ip, port }) as PluginMethodResponse<string>;
    console.log(response)
    console.log(response.result)
    console.log(response.success)
    if (response.success) {
      console.log("cup of ping")
      setPings(prevPings => ({ ...prevPings, [`${ip}:${port}`]: response.result }));
    }
  };

  const deleteServer = async (serverLabel: string ) => {
    console.log("removing server", serverLabel);
    const response = await server.callPluginMethod("deleteServer", {serverLabel}) as PluginMethodResponse<any>;
    console.log(response)
  };

  const editServer = async (serverLabel: string ) => {
    console.log("editing server", serverLabel);
    await server.callPluginMethod("setCurrentServer", {serverLabel}) as PluginMethodResponse<any>;

    Router.CloseSideMenus();
    Router.Navigate("/deckmumble/settings/form1");
  };

  const connectServer = async (serverLabel: string ) => {
    console.log("connecting to server", serverLabel);
    await server.callPluginMethod("setCurrentServer", {serverLabel}) as PluginMethodResponse<any>;
    handleConnect();
  };

  

  const fetchSavedServers = async () => {
    try {
      const response = await server.callPluginMethod("getServers", {}) as PluginMethodResponse<any>;
      console.log(response);
      console.log(response.result);
      console.log(response.success);
      if (response.success) {
        console.log("SERVERS ARE TERDS!")
        console.log(response.result);
        setServers(response.result);
      }
      else {
        console.log("SERVERS ARE NOT TERDS!")
        console.log(response.result);

      }
    } catch (e) { 
      console.log("AAAARSE");
      console.log(e);
    }
  };

  const ServerMenu = ({serverLabel, isCurrentlyConnected}: {serverLabel: string, isCurrentlyConnected: boolean}) => (
    <Menu label={serverLabel}>
      {!isCurrentlyConnected && <MenuItem onClick={() => connectServer(serverLabel)}>Connect</MenuItem>}
      <MenuItem onClick={() => editServer(serverLabel)}>Edit</MenuItem>
      <MenuItem onClick={() => deleteServer(serverLabel)}>Delete</MenuItem>
    </Menu>
  );
  
  const handleServerClick = (serverLabel: string, event: any) => {
    const retardedConnected = async () => {
      const connectedResponse = await server.callPluginMethod("getConnected", {}) as PluginMethodResponse<boolean>;
      if (connectedResponse.success) {
        //setisConnected(connectedResponse.result);
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
    retardedConnected();
  };

  useEffect(() => {
    console.log("Tab3Component Fetussed on the turds.");
    fetchSavedServers();
    console.log("SHART!!! ", focusedItem);
    
}, []);

  useEffect(() => {
    console.log("Tab3Component Fetussed.");
    servers.forEach(server => fetchPing(server.host, server.port));
    console.log("FECES! ",focusedItem);
  }, [servers]);

  const FocusableField = ({ onFocus, ...props }: any) => {
    return (
      <div onFocus={onFocus}>
        <Field {...props} />
      </div>
    );
  };

  return(
    <div>
      <PanelSection>
        <div style={{ 
          maxHeight: '220px', // adjust as needed
          overflowY: 'auto', // adds a vertical scrollbar
          width: '100%', // adjust as needed
          //padding: '1rem', // adjust as needed
          textAlign: 'left'
        }}>
        {servers.map((server, index) => {
          const pingInfo = pings[`${server.host}:${server.port}`] || {};
          const { ping = '', users = '', max_users = '' } = pingInfo;
          let pingStyle = { color: 'black'};
          if (typeof ping === 'number') { // make sure ping is a number
            if (ping < 50) {
              pingStyle = { color: 'green'};
            } else if (ping < 120) {
              pingStyle = { color: 'orange'};
            } else {
              pingStyle = { color: 'red' };
            }
          }
          return (
            <PanelSectionRow>
              <FocusableField onFocus={() => {console.log("CUP OF FOCUS?")}} onClick={(e: any) => handleServerClick(server.label, e)}  key={index} 
                label={
                  <Fragment >
                    <div style={{ flex: 0.7, textAlign: 'left' }}>{server.label}: {users}/{max_users}</div> 
                    <div style={{ flex: 0.3, textAlign: 'right' }}><span style={pingStyle}>{ping}ms</span></div>
                    </Fragment>
                } 
                
              />
            </PanelSectionRow>
          );
        })}
        </div>
      </PanelSection>
      <PanelSection>
        <PanelSectionRow>
          <ButtonItem layout="below" onClick={handleSettingsClick}>
            Settings
          </ButtonItem>
        </PanelSectionRow>
      </PanelSection>
    </div>
  )
};


const TabFart: FC = () => {
  const [currentTab, setCurrentTab] = useState<string>("Tab1");
  const { connected, setConnected } = useContext(ConnectionContext);

  useEffect(() => {
    console.log("TabFart EnFetinalized!");
    const fetchInitialState = async () => {
      const connectedResponse = await server.callPluginMethod("getConnected", {}) as PluginMethodResponse<boolean>;
      if (connectedResponse.success) setConnected(connectedResponse.result);
    };
    fetchInitialState();
  }, []);

  useEffect(() => {
    console.log("TabFart Fetussed, connected changed");
  }, [connected]);

  return(
    <Tabs
      title="Turgedson Fart"
      activeTab={currentTab}
      autoFocusContents={true}
      onShowTab={(tabID: string) => {
        setCurrentTab(tabID);
      }}
      tabs={[
      {
        title: "Server",
        content: <Tab2Component key="Tab1"/>,
        id: "Tab1",
      },
      ...(connected ? [{
        title: "Chat",
        content: <Tab1Component key="Tab2"/>,
        id: "Tab2",
      }] : []),
      {
        title: "Servers",
        content: <Tab3Component key="Tab3"/>,
        id: "Tab3",
      },
      ]}
    />
  );
};

return (
<div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between', height: '100%', minHeight: '600px' }}>
<ConnectionProvider>
<TransmittingProvider serverAPI={server}>
<ModalContextProvider serverAPI={server}>
  <TabFart/>
  </ModalContextProvider>
</TransmittingProvider>
</ConnectionProvider>
</div>
);
};




export default definePlugin((server: ServerAPI) => {
  server.routerHook.addRoute("/deckmumble/settings/form1", () => <SettingsPage serverAPI={server} />, {
    exact: true,
  });

  server.routerHook.addRoute("/deckmumble/settings/form2", () => <SettingsPage serverAPI={server} />, {
    exact: true,
  });



  return {
    title: <div className={staticClasses.Title}>Mumble</div>,
    content: <Content server={server} />,
    icon: <FaShip />,
    onDismount() {
      server.routerHook.removeRoute("/deckmumble/settings/form1");
      server.routerHook.removeRoute("/deckmumble/settings/form2");
    },
  };
});
