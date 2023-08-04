// MyForm.tsx
import { useState, useEffect } from 'react';
import { TextField, ButtonItem } from 'decky-frontend-lib';
import { ServerAPI } from "decky-frontend-lib";

interface MyFormProps {
  serverAPI: ServerAPI;
}

interface PluginMethodResponse<T> {
  success: boolean;
  result: T;
}


const MyForm = ({ serverAPI }: MyFormProps) => {
  const [address, setAddress] = useState('');
  const [port, setPort] = useState('');
  const [username, setUsername] = useState('');
  const [label, setLabel] = useState('');
  const [password, setPassword] = useState('');

  const handleResponse = (response: any) => {
    if (response.result !== 'error') {
      return response.result;
    }
    return '';
  };

  useEffect(() => {
    const fetchSettings = async () => {
      // const savedAddress = handleResponse(await serverAPI.callPluginMethod("settings_getSetting", { key: "address", defaults: "" }));
      // const savedPort =  handleResponse(await serverAPI.callPluginMethod("settings_getSetting", { key: "port", defaults: "" }));
      // const savedUsername =  handleResponse(await serverAPI.callPluginMethod("settings_getSetting", { key: "username", defaults: "" }));
      // const savedLabel =  handleResponse(await serverAPI.callPluginMethod("settings_getSetting", { key: "label", defaults: "" }));
      // const savedPassword =  handleResponse(await serverAPI.callPluginMethod("settings_getSetting", { key: "password", defaults: "" }));

      const currentServer = await serverAPI.callPluginMethod("getCurrentServer", {}) as PluginMethodResponse<{host: string, port: string, username: string, password: string, label: string}>;
      console.log("currentServer", currentServer);

      setAddress(currentServer.result.host);
      setPort(currentServer.result.port);
      setUsername(currentServer.result.username);
      setLabel(currentServer.result.label);
      setPassword(currentServer.result.password);
    };
    fetchSettings();
  }, [serverAPI]);
  
  const handleSubmit = async () => {
    let error;
    try {
      // await serverAPI.callPluginMethod("settings_setSetting", { key: "address", value: address });
      // await serverAPI.callPluginMethod("settings_setSetting", { key: "port", value: port });
      // await serverAPI.callPluginMethod("settings_setSetting", { key: "username", value: username });
      // await serverAPI.callPluginMethod("settings_setSetting", { key: "label", value: label });
      // await serverAPI.callPluginMethod("settings_setSetting", { key: "password", value: password });
      console.log("terd", { address: address, port: port, username: username, label: label, password: password });
      const arse = await serverAPI.callPluginMethod("saveServer", { address: address, port: port, username: username, label: label, password: password || '' });
      console.log("arse", arse);
      serverAPI.toaster.toast({
        title: 'Success',
        body: "Settings saved",
        duration: 5000,
        critical: false
      });
    } catch (e) {
      error = e;
      serverAPI.toaster.toast({
        title: 'Error',
        body: error,
        duration: 5000,
        critical: true
      });
    }
  };


  return (
    <div>
  <div style={{ display: "flex"}}>
    <div style={{ flex: 1, margin: "0 8px" }}>
      <TextField 
        label="Address" 
        value={address} 
        onChange={e => setAddress(e.target.value)} 
        style={{ width: "100%" }}
      />
    </div>
    <div style={{ flex: 1, margin: "0 8px" }}>
      <TextField 
        label="Port" 
        value={port} 
        onChange={e => setPort(e.target.value)} 
        style={{ width: "100%" }}
      />
    </div>
  </div>
  <div style={{ display: "flex"}}>
    <div style={{ flex: 1, margin: "0 8px" }}>
      <TextField 
        label="Username" 
        value={username} 
        onChange={e => setUsername(e.target.value)} 
        style={{ width: "100%" }}
      />
    </div>
    <div style={{ flex: 1, margin: "0 8px" }}>
      <TextField 
        label="Server Name" 
        value={label} 
        onChange={e => setLabel(e.target.value)} 
        style={{ width: "100%" }}
      />
    </div>
  </div>
  <TextField label="Password" value={password} onChange={e => setPassword(e.target.value)} />
  <ButtonItem onClick={handleSubmit}>Save</ButtonItem>
</div>

  );
};

export default MyForm;