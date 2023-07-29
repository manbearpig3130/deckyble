// MyForm.tsx
import { useState, useEffect, useMemo, FC, useRef, CSSProperties } from 'react';
import { DropdownOption, Dropdown, ToggleField, SingleDropdownOption, Field, ControlsList, SliderField } from 'decky-frontend-lib';
import { ServerAPI } from "decky-frontend-lib";

interface AnotherFormProps {
  serverAPI: ServerAPI;
}

interface PluginMethodResponse<T> {
  success: boolean;
  result: T;
}

const AnotherForm = ({ serverAPI }: AnotherFormProps) => {
  const [APIChanged, setAPIChanged] = useState<{ ID: number; name: string }>({ID: 0, name: ""});
  const [OUTAPIChanged, setOUTAPIChanged] = useState<{ ID: number; name: string }>({ID: 0, name: ""});
  const [transmitChanged, settransmitChanged] = useState<{ ID: number; name: string }>({ID: 0, name: "always-on"});
  const [transmitName, setTransmitName] = useState<string>('always-on')


  useEffect(() => {
    const fetchItems = async () => {
      const response = await serverAPI.callPluginMethod("get_transmit_mode", {}) as PluginMethodResponse<{ ID: number; name: string; }>;     
      if (response.success) {
        setTransmitName(response.result.name);}
        settransmitChanged({ ID: response.result.ID, name: response.result.name })
      };
    fetchItems();
    console.log("GOT TRANSMIT TIPE", transmitName)
  }, []);

  useEffect(() => {
  }, [transmitName]);


  



  const AudioFeedbackBar = () => {
    const [audioLevel, setAudioLevel] = useState(0);
    const [broadcastAfter, setBroadcastAfter] = useState(50); // initial value
    const [silenceBelow, setsilenceBelow] = useState(20);

  
    useEffect(() => {
      const fetchItems = async () => {
        const response = await serverAPI.callPluginMethod("getsilenceBelow", {}) as PluginMethodResponse<number>;  
        const response2 = await serverAPI.callPluginMethod("getbroadcastAfter", {}) as PluginMethodResponse<number>;   
        if (response.success) {
          setsilenceBelow(response.result)
        }
        if (response2.success) {
          setBroadcastAfter(response2.result)
        }
        };
      fetchItems();
      console.log("FARETS refreshed")
    }, []);


    useEffect(() => {
      const ws = new WebSocket("ws://localhost:8765");
      console.log(ws)
  
      ws.addEventListener("open", async (event) => {
        console.log("SHOWING EVENT:", event);
      });

      ws.onopen = () => {
        console.log("WebSocket SETTINGS connection opened:");
        ws.send(JSON.stringify({type: 'join', channel: 'audio_level'}));
      };
  
      ws.onmessage = (event) => {
        if (event.data){
          try{
            const data = JSON.parse(event.data);
            if (data && data.type === 'audio_level_update') {
              //console.log('re-rendering FART?', data);
              setAudioLevel(data.data)
            }
            else if (data && data.type === 'broadcastAfter_update') {
              setBroadcastAfter(data.value)
            }
            else if (data && data.type === 'silenceBelow_update') {
              setsilenceBelow(data.value)
            }
          } catch (e) {
            console.log("Couldn't process data", e);
          }
        } else {
          console.log("No data received")
        }
      };
      ws.onclose = (event) => {
        console.log("WEBTERD HAS CLOSED!!!", event)
      }
      return () => {
        ws.close();
        console.log("Component is unmounting");
      };
    }, []);
  
    return (
      <div style={{width: "100%", height: "20px", backgroundColor: "#ccc", position: "relative"}}>
        <div style={{width: `${audioLevel}%`, height: "20px", backgroundColor: "green"}} />
        <div style={{
          height: "100%",
          width: "4px",
          backgroundColor: "yellow",
          position: "absolute",
          left: `${broadcastAfter}%`,
          top: "0"
        }} />
        <div style={{
          height: "100%",
          width: "4px",
          backgroundColor: "red",
          position: "absolute",
          left: `${silenceBelow}%`,
          top: "0"
        }} />
      </div>
    );
  };

  const InputDropDown: FC = () => {
  const items = useRef<DropdownOption[]>([]);
  const [selectedInputDevice, setSelectedInputDevice] = useState<{ ID: number; name: string }>({ID: 0, name: ""});

  const handleInputDeviceChange = async (selectedOption: SingleDropdownOption) => {
    setSelectedInputDevice({ID: selectedOption.data as number, name: selectedOption.label as string});
    console.log("Updating selectedInputDevice state with:", selectedOption);
    await serverAPI.callPluginMethod("setInputDevice", { device: selectedOption.data })
  };

  useEffect(() => {
    const fetchItems = async () => {
      const response = await serverAPI.callPluginMethod("get_input_devices", {}) as PluginMethodResponse<Array<{ ID: number; name: string; }>>;  
      const currentInput = await serverAPI.callPluginMethod("get_selected_input", {}) as PluginMethodResponse<{ID: number, name: string}>;    
      if (response.success) {
        const mappedItems: DropdownOption[] = response.result.map((item) => ({
          data: item.ID,
          label: item.name,
        }));  
        items.current = mappedItems;
      }
      if (currentInput.success) {setSelectedInputDevice({ID: currentInput.result.ID, name: currentInput.result.name});}
      };
    fetchItems();
    console.log("InputTurds refreshed")
  }, []);

  useEffect(() => {
  }, [APIChanged])

  return(
    <Field label="Input Device: ">
    <Dropdown
        menuLabel='Inputs'
        rgOptions={items.current}
        selectedOption={selectedInputDevice}
        onChange={handleInputDeviceChange}
        strDefaultLabel={selectedInputDevice.name || "FETUS"}
      />
    </Field>
  );
} 

const BroadcastAfterSlider: FC = () => {
  const [broadcastAfter, setBroadcastAfter] = useState(50); // initial value

  const handleSlidereChange = async (selected: number) => {
    setBroadcastAfter(selected);
    await serverAPI.callPluginMethod("setBroadcastAfter", { value: selected })
    console.log(selected)
  };

  useEffect(() => {
    const fetchItems = async () => {
      const response = await serverAPI.callPluginMethod("getbroadcastAfter", {}) as PluginMethodResponse<number>;    
      if (response.success) {
        console.log(response.result)
        setBroadcastAfter(response.result)
      }

      };
    fetchItems();
    console.log("Slider refreshed")
  }, []);

  return(
    <div>
    <SliderField 
      label={"Broadcast After: " + broadcastAfter + "%"}
      value={broadcastAfter}
      min={0}
      max={100}
      onChange={(value) => handleSlidereChange(value)}
      />
    </div>
  );
} 

const SilenceBelowSlider: FC = () => {
  const [silenceBelow, setsilenceBelow] = useState(50); // initial value

  const handleSlidereChange = async (selected: number) => {
    setsilenceBelow(selected);
    await serverAPI.callPluginMethod("setsilenceBelow", { value: selected })
    console.log(selected)
  };

  useEffect(() => {
    const fetchItems = async () => {
      const response = await serverAPI.callPluginMethod("getsilenceBelow", {}) as PluginMethodResponse<number>;    
      if (response.success) {
        console.log(response.result)
        setsilenceBelow(response.result)
      }

      };
    fetchItems();
    console.log("Slider refreshed")
  }, []);

  return(
    <div>
    <SliderField 
      label={"Silence Below: " + silenceBelow + "%"}
      value={silenceBelow}
      min={0}
      max={100}
      onChange={(value) => handleSlidereChange(value)}
      />
    </div>
  );
} 

const TimeoutSlider: FC = () => {
  const [timeout, setTimeout] = useState(5); // initial value

  const handleSlidereChange = async (selected: number) => {
    setTimeout(selected);
    await serverAPI.callPluginMethod("setTimeout", { value: selected })
    console.log(selected)
  };

  useEffect(() => {
    const fetchItems = async () => {
      const response = await serverAPI.callPluginMethod("getTimeout", {}) as PluginMethodResponse<number>;    
      if (response.success) {
        console.log(response.result)
        setTimeout(response.result)
      }
      };
    fetchItems();
    console.log("Slider refreshed")
  }, []);

  return(
    <div>
    <SliderField 
      label={"Timeout: " + timeout + 's'}
      value={timeout}
      min={0}
      max={2.5}
      step={0.01}
      onChange={(value) => handleSlidereChange(value)}
      />
    </div>
  );
} 

const OutputDropDown: FC = () => {
  const [selectedOutputDevice, setSelectedOutputDevice] = useState<{ ID: number; name: string }>({ID: 0, name: ""});
  const items = useRef<DropdownOption[]>([]);

  const handleOutputDeviceChange = async (selectedOption: SingleDropdownOption) => {
    console.log("Updating selectedOutputDevice state with:", selectedOption);
    setSelectedOutputDevice({ ID: selectedOption.data as number, name: selectedOption.label as string });
    await serverAPI.callPluginMethod("setOutputDevice", { device: selectedOption.data })
  };

  useEffect(() => {
    const fetchItems = async () => {
      const response = await serverAPI.callPluginMethod("get_output_devices", {}) as PluginMethodResponse<Array<{ ID: number; name: string; }>>;     
      const currentOutput = await serverAPI.callPluginMethod("get_selected_output", {}) as PluginMethodResponse<{ID: number, name: string}>; 
      if (response.success) {
        const mappedItems: DropdownOption[] = response.result.map((item) => ({
          data: item.ID,
          label: item.name,
        }));
        items.current = mappedItems;
      } 
      if (currentOutput.success) {setSelectedOutputDevice({ID: currentOutput.result.ID, name: currentOutput.result.name});}
      };
    fetchItems();
    console.log("outputdropdown refreshed")
    console.log(selectedOutputDevice)
  }, []);

  useEffect(() => {
  }, [OUTAPIChanged])


  return(
    <Field label="Output Device: ">
    <Dropdown
        menuLabel='Outputs'
        rgOptions={items.current}
        selectedOption={items.current}
        onChange={handleOutputDeviceChange}
        strDefaultLabel={selectedOutputDevice.name || "Tergidson"}
      />
    </Field>
  );
} 

const APIDropDown: FC = () => {
  const [selectedAPI, setSelectedAPI] = useState<{ ID: number; name: string }>({ID: 0, name: ""});
  const items = useRef<DropdownOption[]>([]);

  const handleAPIDeviceChange = async (selectedOption: SingleDropdownOption) => {
    console.log("Updating TERGIS MCFART state with:", selectedOption);
    setSelectedAPI({ ID: selectedOption.data as number, name: selectedOption.label as string });
    setAPIChanged({ ID: selectedOption.data as number, name: selectedOption.label as string })
    await serverAPI.callPluginMethod("setAPI", { api: selectedOption.data })
  };

  useEffect(() => {
    const fetchItems = async () => {
      const response = await serverAPI.callPluginMethod("get_apis", {}) as PluginMethodResponse<Array<{ ID: number; name: string; }>>;     
      console.log("FARTY MCDENSE! ", response.result);
      const currentApi = await serverAPI.callPluginMethod("get_api", {}) as PluginMethodResponse<{ID: number, name: string}>; 
      console.log("THE SELECTED API: ", currentApi);
      if (response.success) {
        const mappedItems: DropdownOption[] = response.result.map((item) => ({
          data: item.ID,
          label: item.name,
        }));
        items.current = mappedItems;
      } 
      if (currentApi.success) {setSelectedAPI({ID: currentApi.result.ID, name: currentApi.result.name});}
      };
    fetchItems();
    console.log("APIs refreshed")
    console.log(selectedAPI)
  }, []);



  return(
    <Field label="Input API: ">
    <Dropdown
        menuLabel='API'
        rgOptions={items.current}
        selectedOption={items.current}
        onChange={handleAPIDeviceChange}
        strDefaultLabel={selectedAPI.name || "Tergidson"}
      />
    </Field>
  );
} 

const OutputAPIDropDown: FC = () => {
  const [selectedOutputAPI, setSelectedOutputAPI] = useState<{ ID: number; name: string }>({ID: 0, name: ""});
  const items = useRef<DropdownOption[]>([]);

  const handleAPIDeviceChange = async (selectedOption: SingleDropdownOption) => {
    console.log("Updating TERGIS MCFART state with:", selectedOption);
    setSelectedOutputAPI({ ID: selectedOption.data as number, name: selectedOption.label as string });
    setOUTAPIChanged({ ID: selectedOption.data as number, name: selectedOption.label as string })
    await serverAPI.callPluginMethod("setAPI_output", { api: selectedOption.data })
  };

  useEffect(() => {
    const fetchItems = async () => {
      const response = await serverAPI.callPluginMethod("get_apis", {}) as PluginMethodResponse<Array<{ ID: number; name: string; }>>;     
      console.log("FARTY MCDENSE OUT! ", response.result);
      const currentApi = await serverAPI.callPluginMethod("get_api_output", {}) as PluginMethodResponse<{ID: number, name: string}>; 
      console.log("THE SELECTED OUT API: ", currentApi);
      if (response.success) {
        const mappedItems: DropdownOption[] = response.result.map((item) => ({
          data: item.ID,
          label: item.name,
        }));
        items.current = mappedItems;
      } 
      if (currentApi.success) {setSelectedOutputAPI({ID: currentApi.result.ID, name: currentApi.result.name});}
      };
    fetchItems();
    console.log("APIs refreshed tergis")
  }, []);

  return(
    <Field label="Output API: ">
    <Dropdown
        menuLabel='Output API'
        rgOptions={items.current}
        selectedOption={items.current}
        onChange={handleAPIDeviceChange}
        strDefaultLabel={selectedOutputAPI.name || "Tergidson"}
      />
    </Field>
  );
} 

const TransmitTypeDropdown: FC = () => {
  const [selectedTransmitType, setSelectedTransmitType] = useState<{ ID: number; name: string }>({ID: 0, name: "always-on"});
  const items = useRef<DropdownOption[]>([]);

  const handleTransmitChange = async (selectedOption: SingleDropdownOption) => {
    setSelectedTransmitType({ ID: selectedOption.data as number, name: selectedOption.label as string });
    settransmitChanged({ ID: selectedOption.data as number, name: selectedOption.label as string })
    await serverAPI.callPluginMethod("set_transmit_mode", { mode: selectedOption.data })
  };

  useEffect(() => {
    const fetchItems = async () => {
      const response = await serverAPI.callPluginMethod("get_transmit_mode", {}) as PluginMethodResponse<{ ID: number; name: string; }>;     
      if (response.success) {
        const mappedItems: DropdownOption[] = [
            {data: 0, label: 'always-on'},
            {data: 1, label: 'push-to-talk'},
            {data: 2, label: 'activity'}
        ]
        items.current = mappedItems
        setSelectedTransmitType({ID: response.result.ID, name: response.result.name});}
      };
    fetchItems();
    console.log("GOT TRANSMIT TIPE")
  }, []);

  useEffect(() => {
  }, [transmitChanged])

  return(
    <Field label="Transmit Type: ">
    <Dropdown
        menuLabel='Transmit Type'
        rgOptions={items.current}
        selectedOption={items.current}
        onChange={handleTransmitChange}
        strDefaultLabel={selectedTransmitType.name || "Tergidson"}
      />
    </Field>
  );
} 

const PttButtonDropdown: FC = () => {
  const [selectedButton, setSelectedButton] = useState<{ ID: number; name: string }>({ID: 0, name: "R5"});
  const items = useRef<DropdownOption[]>([]);

  const handlePttButtonChange = async (selectedOption: SingleDropdownOption) => {
    setSelectedButton({ ID: selectedOption.data as number, name: selectedOption.label as string });
    console.log(selectedOption.label);
    const r = await serverAPI.callPluginMethod('setPushToTalkKey', {key: selectedOption.label} );
    console.log(r.result)
  };

  useEffect(() => {
    const fetchItems = async () => {
      const response = await serverAPI.callPluginMethod("getPushToTalkKey", {}) as PluginMethodResponse<{ ID: number; name: string; }>;     
      if (response.success) {
        console.log(response.result)
        const mappedItems: DropdownOption[] = [
            {data: 0, label: 'R4'},
            {data: 1, label: 'L4'},
            {data: 2, label: 'R5'},
            {data: 3, label: 'L5'}
        ]
        items.current = mappedItems
        setSelectedButton({ID: response.result.ID, name: response.result.name});}
      };
    fetchItems();
    console.log("GOT PTT BUTTON")
  }, []);

  return(
    <Field label="Push-to-Talk Button: ">
    <Dropdown
        menuLabel='Push-To-Talk Button'
        rgOptions={items.current}
        selectedOption={items.current}
        onChange={handlePttButtonChange}
        strDefaultLabel={selectedButton.name || "Tergidson"}
      />
    </Field>
  );
} 


const InGamePttButtonDropdown: FC = () => {
  const [selectedButton, setSelectedButton] = useState<{ ID: number; name: string }>({ID: 0, name: "Up"});
  const items = useRef<DropdownOption[]>([]);

  const handlePttButtonChange = async (selectedOption: SingleDropdownOption) => {
    setSelectedButton({ ID: selectedOption.data as number, name: selectedOption.label as string });
    console.log(selectedOption.label);
    const r = await serverAPI.callPluginMethod('setInGamePushToTalkKey', {key: selectedOption.label} );
    console.log(r.result)
  };

  useEffect(() => {
    const fetchItems = async () => {
      const response = await serverAPI.callPluginMethod("getInGamePushToTalkKey", {}) as PluginMethodResponse<{ ID: number; name: string; }>;     
      if (response.success) {
        console.log(response.result)
        const mappedItems: DropdownOption[] = [
            {data: 0, label: 'A'},
            {data: 1, label: 'B'},
            {data: 2, label: 'X'},
            {data: 3, label: 'Y'},
            {data: 4, label: 'L1'},
            {data: 5, label: 'L2'},
            {data: 6, label: 'L3'},
            {data: 7, label: 'R1'},
            {data: 8, label: 'R2'},
            {data: 9, label: 'R3'},
            {data: 10, label: 'Select'},
            {data: 11, label: 'Start'},
            {data: 12, label: 'Up'},
            {data: 13, label: 'Down'},
            {data: 14, label: 'Left'},
            {data: 15, label: 'Right'},
        ]
        items.current = mappedItems
        setSelectedButton({ID: response.result.ID, name: response.result.name});}
      };
    fetchItems();
    console.log("GOT PTT BUTTON")
  }, []);

  return(
    <Field label="Ingame Push-to-Talk Button: ">
    <Dropdown
        menuLabel='Ingame Push-To-Talk Button'
        rgOptions={items.current}
        selectedOption={items.current}
        onChange={handlePttButtonChange}
        strDefaultLabel={selectedButton.name || "Tergidson"}
      />
    </Field>
  );
} 

const EnablePTTToggle: FC = () => {
  const [enabled, setEnabled] = useState(false);

  const getEnabled = async () => {
    const response = await serverAPI.callPluginMethod("getPTTEnabled", {}) as PluginMethodResponse<boolean>;
    setEnabled(response.result);
  }
  const handleEnable = async () => {
    await serverAPI.callPluginMethod("setPTTEnabled", { value: true })
    setEnabled(true);
    console.log("Set PTT ON.");
  };
  const handleDisable = async () => {
    await serverAPI.callPluginMethod("setPTTEnabled", { value: false })
    setEnabled(false);
    console.log("Disabled SteamOS PTT.");
  };
  useEffect(() => {
    getEnabled();
    console.log("Getting if PTT enabled out of game.");
  }, []);

  return(
    <ToggleField
          label="Enable Push-To-Talk in Steam Interface (Fucks some controls)"
          checked={enabled}
          onChange={(checked) => {
            if (checked) {
              handleEnable();
            } else {
              handleDisable();
            }
          }}
        />
  )
}


useEffect(() => {
}, [transmitChanged])

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between"}}>
      <APIDropDown/>
      <InputDropDown/>
      </div>
      <div style={{ display: "flex", justifyContent: "space-between"}}>
        <OutputAPIDropDown/>
      <OutputDropDown/>
      </div>
      <TransmitTypeDropdown/>
      {transmitChanged.name === 'activity' && (
        <p>
        <AudioFeedbackBar/>
        <p/>
        <SilenceBelowSlider/>
        <BroadcastAfterSlider/>
        <TimeoutSlider/>
        </p>
      )}
      {transmitChanged.name === 'push-to-talk' && (
        <div>
        <span style={{ color: "red" }}> Please note that Push to Talk is fucked.</span>
        <EnablePTTToggle/>
        <PttButtonDropdown/>
        <InGamePttButtonDropdown/>
      </div>
      )}
    </div>
  );
      }
export default AnotherForm;