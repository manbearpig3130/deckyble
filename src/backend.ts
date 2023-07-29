import {ServerAPI} from "decky-frontend-lib"

var server: ServerAPI | undefined = undefined;

export function resolvePromise(promise: Promise<any>, callback: any) {
    (async function () {
        let data = await promise;
        if (data.success)
            callback(data.result);
    })();
}

export function callBackendFunction(promise: Promise<any>) {
    (async function () {
        await promise;
    })();
}

export function setServer(s: ServerAPI) {
    server = s;
}


export async function connectMumble(server: ServerAPI) {
    await server!.callPluginMethod("connect_server", {});
}

export function getButtonText(): Promise<any> {
    return server!.callPluginMethod("dense", {});
  }



export async function saveSetting(server: ServerAPI, key: string, value: string) {
    await server!.callPluginMethod("settings_setSetting", {key, value});
}

export async function commitSettings(server: ServerAPI) {
    await server!.callPluginMethod("settings_commit", {});
}

export async function getSetting(server: ServerAPI, key: string, defaultValue: string) {
    const response = await server!.callPluginMethod("settings_getSetting", {key, defaultValue});
    return response.result !== "error" ? response.result : "";
}