import pymumble_py3 as pymumble
import asyncio, websockets, threading, json, queue, os, decky_plugin, time, datetime, sys
os.environ["XDG_RUNTIME_DIR"] = "/run/user/1000"
os.environ["DBUS_SESSION_BUS_ADDRESS"] = "unix:path=/run/user/1000/bus"
import sounddevice as sd
from settings import SettingsManager
from functools import partial
import numpy

from steam_deck_input import SteamDeckInput
from mumble_client import CustomMumble
from mumble_ping import mumble_ping


settingsDir = os.environ["DECKY_PLUGIN_SETTINGS_DIR"]
deckyHomeDir = os.environ["DECKY_HOME"]
loggingDir = "/home/deck/homebrew/logs/mumble/"


async def send_update(websocket, path, thing=None):
    Plugin.clients.setdefault('default', set()).add(websocket)
    decky_plugin.logger.info(f"SCKETS??? {websocket} - {path} - {thing}")
    decky_plugin.logger.info(f"SCKETS FAAAART??? {Plugin.clients}")
    try:
        while True:  # Keep listening for messages
            message = await websocket.recv()
            data = json.loads(message)
            decky_plugin.logger.info(f"GOT A TERGID UPDATE!!! {message}")
            if data['type'] == 'join':  # If the client wants to join a channel
                decky_plugin.logger.info(f"JOINED THE TERGID CHANNEL!!! {data['type']} - {data['channel']}")
                Plugin.clients.setdefault(data['channel'], set()).add(websocket)
                decky_plugin.logger.info(f"SOCKETS TEALC {Plugin.clients}")
    except websockets.ConnectionClosed as e:
        decky_plugin.logger.info(f"CLOSED THE TERGIDS {e}")
    finally:
        for clients in Plugin.clients.values():
            clients.discard(websocket)
        decky_plugin.logger.info(f"SOCKETS ARSE {Plugin.clients}")


class Plugin:
    server_stop_event = asyncio.Event()

    def catch_errors(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                decky_plugin.logger.error(f"Error in {func.__name__}: {e}")
        return wrapper
    
        # Asyncio-compatible long-running code, executed in a task when the plugin is loaded
    async def _main(self):
        #nump = self.import_or_install("numpy")
        #decky_plugin.logger.info(f"import/install numpy: {nump}")
        decky_plugin.logger.info(f"PYTHONPATH: {os.environ.get('PYTHONPATH')}")
        decky_plugin.logger.info(f"PATH: {os.environ.get('PATH')}")
        decky_plugin.logger.info(f"Dir: {os.listdir()}")
        decky_plugin.logger.info(f"CWD: {os.getcwd()}")
        
        self.logger = decky_plugin.logger
        self.server_stop_event = asyncio.Event()
        self.clients = {}
        self.settings = SettingsManager(name='settings', settings_directory=settingsDir)
        self.settings.read()
        self.mumble = None
        self.muted = False
        self.deafened = False
        self.connected = False
        self.stream = None
        self.audio_queue = queue.Queue()
        self.savedServers = self.settings.getSetting("savedServers", [])
        decky_plugin.logger.info(f"saved servers: {self.savedServers}")
        self.messages = []
        self.selected_recipient = { 'ID': 0, 'name': "Channel" }
        self.probe = None
        self.probing = False
        self.broadcastAfter = self.settings.getSetting("broadcastAfter", 50)
        self.silenceBelow = self.settings.getSetting("silenceBelow", 20)
        self.transmit_mode = self.settings.getSetting("transmitMode", 0)   ## 'always-on' or 'push-to-talk' or 'activity'
        self.broadcast_timer = None
        self.BROADCAST_TIMEOUT = self.settings.getSetting("BROADCAST_TIMEOUT", 5)  # Timeout in seconds
        self.selected_input_device = sd.default.device[0]
        self.selected_output_device = sd.default.device[1]
        self.selected_api_input = sd.query_hostapis()[sd.default.hostapi]
        self.selected_api_input['index'] = sd.default.hostapi
        self.selected_api_output = sd.query_hostapis()[sd.default.hostapi]
        self.selected_api_output['index'] = sd.default.hostapi
        self.apis = sd.query_hostapis()
        devices = sd.query_devices()
        self.allDevices = devices
        self.inlist = [dev for dev in devices if dev['max_input_channels'] > 0]
        self.outlist = [dev for dev in devices if dev['max_output_channels'] > 0]
        self.input_handler = None
        self.ptt_key = 'R5'
        self.ig_ptt_key = 'Up'
        self.ptt_enabled = False
        if self.transmit_mode == 1:
            self.transmitting = False
        else:
            self.transmitting = True
        
        self.side_loop = threading.Thread(target=self.sideloop, args=(self,))
        self.side_loop.start()
        
        try:
            async with websockets.serve(lambda websocket, path: send_update(websocket, path, thing=self), "localhost", 8765):
                await Plugin.server_stop_event.wait()
        except Exception as e:
            decky_plugin.logger.info("Failed to start websocket server")
            decky_plugin.logger.info(e)
            return
    
    @catch_errors
    def sideloop(self):
        decky_plugin.logger.info("STARTED SIDE TERGISON LLOOOOPP")
        while True:
            if self.input_handler is not None:
                if self.transmit_mode == 1 and self.ptt_enabled:
                    if self.input_handler.update() == self.ptt_key and self.ptt_enabled:
                        self.transmitting = True
                    else:
                        self.transmitting = False
                
                elif self.transmit_mode == 1 and self.ptt_enabled == False and self.input_handler is not None:
                    self.input_handler.close()
                    self.input_handler = None
            elif self.input_handler is None and self.ptt_enabled:
                if self.transmit_mode == 1:
                    self.input_handler = SteamDeckInput()

            if 'audio_level' in self.clients:
                if len(self.clients['audio_level']) > 0:
                    self.probing = True
                else:
                    self.probing = False
                    if self.probe:
                        self.probe.stop()
                    self.probe = None
            if self.probing:         
                if 'audio_level' in self.clients:
                    if not self.probe:
                        self.logger.info("ALIEN PROBE?")
                        self.open_probing_stream(self)
            
            time.sleep(0.01)

    @catch_errors
    async def broadcast_update(self, channel='default', reason='Turds', data=None):
        decky_plugin.logger.info(f"TERGID UPDATE?? {channel} - {reason}")
        decky_plugin.logger.info(f"TERGID clients?? {self.clients}")
        for websocket in self.clients.get(channel, []):
            try:
                response = await websocket.send(json.dumps({'type': 'update', 'reason': reason}))
                decky_plugin.logger.info(f"TERGID RESPONSE?? {response}")
            except Exception as e:
                decky_plugin.logger.info("Failed to send update")
                decky_plugin.logger.info(e)

    @catch_errors
    async def broadcast_message(self, message, channel='default' ):
        for websocket in self.clients.get(channel, []):
            try:
                await websocket.send(json.dumps({'type': 'message', 'actor': self.mumble.users[message.actor]['name'], 'message': message.message, 'time': str(datetime.datetime.now().strftime("%H:%M:%S"))}))
            except Exception as e:
                decky_plugin.logger.info("Failed to send message")
                decky_plugin.logger.info(e)

    @catch_errors
    async def send_text_message_to_server(self, msg=None):
        if msg is not None:
            self.mumble.my_channel().send_text_message(msg)

    @catch_errors
    async def send_text_message_to_user(self, usersession=None, msg=None):
        decky_plugin.logger.info(f"FUCKTARD MCJUICE, {usersession}, {msg}")
        if msg is not None:
            self.mumble.users[usersession].send_text_message(msg)
            self.messages.append(json.dumps({'type': 'message', 'actor': self.name, 'message': msg, 'time': str(datetime.datetime.now().strftime("%H:%M:%S"))}))

    async def connect_server(self):
        if not self.connected:
            decky_plugin.logger.info(f"Connecting to server")
            try:
                self.open_audio_stream(self)
                self.host = await self.settings_getSetting(self, key="address", defaults="localhost")
                self.port = await self.settings_getSetting(self, key="port", defaults=64738)
                self.name = await self.settings_getSetting(self, key="username", defaults="Decky")
                self.password = await self.settings_getSetting(self, key="password", defaults="")
                decky_plugin.logger.info(f"Connecting to server: {str(self.host)}:{self.port}")
                self.mumble = CustomMumble(self.host, self.name, port=int(self.port), certfile=None, keyfile=None, password=self.password)
                self.mumble.set_receive_sound(True)
                self.messages = []

                loop = asyncio.get_running_loop()
                self.mumble.set_application_string("Steam Deck Mumble Plugin")
                await loop.run_in_executor(None, self.mumble.start)

                self.mumble.is_ready()
                if self.muted:
                    self.mumble.users.myself.mute()
                if self.deafened:
                    self.mumble.users.myself.deafen()
                decky_plugin.logger.info(f"Connected")
                channels_and_users = await self.get_channels_and_users(self)
                decky_plugin.logger.info(f"{self.mumble.users}")
                decky_plugin.logger.info(f"{channels_and_users}")
                self.connected = True
                decky_plugin.logger.info("Welcome message:")
                decky_plugin.logger.info(self.mumble.server_sync_message.welcome_text)
                self.messages.append(json.dumps({'type': 'message', 'actor': 'Server', 'message': str(self.mumble.server_sync_message.welcome_text), 'time': str(datetime.datetime.now().strftime("%H:%M:%S"))}))
                self.mumble.callbacks.add_callback(pymumble.constants.PYMUMBLE_CLBK_SOUNDRECEIVED, partial(self.sound_received_handler, self))
                self.mumble.callbacks.add_callback(pymumble.constants.PYMUMBLE_CLBK_USERCREATED, partial(self.user_added_handler, self))
                self.mumble.callbacks.add_callback(pymumble.constants.PYMUMBLE_CLBK_USERUPDATED, partial(self.user_updated_handler, self))
                self.mumble.callbacks.add_callback(pymumble.constants.PYMUMBLE_CLBK_USERREMOVED, partial(self.user_removed_handler, self))
                self.mumble.callbacks.add_callback(pymumble.constants.PYMUMBLE_CLBK_CHANNELCREATED, partial(self.channel_added_handler, self))
                self.mumble.callbacks.add_callback(pymumble.constants.PYMUMBLE_CLBK_CHANNELUPDATED, partial(self.channel_updated_handler, self))
                self.mumble.callbacks.add_callback(pymumble.constants.PYMUMBLE_CLBK_CHANNELREMOVED, partial(self.channel_removed_handler, self))
                self.mumble.callbacks.add_callback(pymumble.constants.PYMUMBLE_CLBK_TEXTMESSAGERECEIVED, partial(self.message_received_handler, self))
                self.mumble.callbacks.add_callback(pymumble.constants.PYMUMBLE_CLBK_DISCONNECTED, partial(self.disconnected_handler, self))
                
                await self.broadcast_update(self, reason="Connected to server")

                return channels_and_users
            except Exception as e:
                decky_plugin.logger.info("Failed to connect to server")
                decky_plugin.logger.info(e)
                users = []
                return users
        else:
            decky_plugin.logger.info(f"Already connected")
            channels_and_users = await self.get_channels_and_users(self)
            return channels_and_users

    @catch_errors
    def audio_playback_thread(self):
        try:
            device_info = sd.query_devices(self.selected_output_device, 'output')
            output_sample_rate = device_info['default_samplerate']
            self.logger.info(f"Tergis fart {self.selected_input_device}, {output_sample_rate}")
            with sd.OutputStream(samplerate=48000, device=self.selected_output_device, dtype=numpy.int16, channels=2, blocksize=32768) as stream:
                while True:
                    audio_data = self.audio_queue.get()
                    if audio_data is None:
                        break  # Exit the loop if we get a None item in the queue
                    stream.write(audio_data)
        except Exception as e:
            self.logger.info(f"Bad luck tergis {e}")

    def mono_to_stereo(data, channels=2):
        mono_audio_data = numpy.frombuffer(data, dtype=numpy.int16)  # Convert the data to a NumPy array
        stereo_array = numpy.vstack((mono_audio_data, mono_audio_data)).T
        return numpy.ascontiguousarray(stereo_array)

    async def send_transmitting_update(self, username):
        decky_plugin.logger.info(f"sending transmission data {username['name']}")
        for websocket in self.clients.get('default', []):
            try:
                await websocket.send(json.dumps({'type': 'user_transmitting', 'username': username['name']}))
            except Exception as e:
                decky_plugin.logger.error(f"Failed to send update: {e}")

    @catch_errors
    def sound_received_handler(self, user, soundchunk):
        decky_plugin.logger.info(f"Sound received {user}")
        try:
            if not self.deafened:
                asyncio.run(self.send_transmitting_update(self, user))
                device_info = sd.query_devices(self.selected_output_device, 'output')
                stereo_data = self.mono_to_stereo(soundchunk.pcm)
                self.audio_queue.put(stereo_data)

        except Exception as e:
            decky_plugin.logger.error(f"Failed to handle sound received: {e}")

    def user_added_handler(self, user):
        decky_plugin.logger.info(f"user added: {user}")
        self.messages.append(json.dumps({'type': 'message', 'actor': 'Server', 'message': f"{user['name']} joined", 'time': str(datetime.datetime.now().strftime("%H:%M:%S"))}))
        asyncio.run(self.broadcast_update(self, reason="User added"))

    def user_updated_handler(self, user, changes):
        decky_plugin.logger.info(f"user changed: {user} {changes}")
        asyncio.run(self.broadcast_update(self, reason="User updated"))

    def user_removed_handler(self, user, event):
        decky_plugin.logger.info(f"user removed: {user} {event}")
        self.messages.append(json.dumps({'type': 'message', 'actor': 'Server', 'message': f"{user['name']} left", 'time': str(datetime.datetime.now().strftime("%H:%M:%S"))}))
        if user['name'] == self.name:
            asyncio.run(self.broadcast_update(self, "Kicked"))
            asyncio.run(self.leave_server(self))
        asyncio.run(self.broadcast_update(self, reason="User removed"))


    def channel_added_handler(self, channel):
        decky_plugin.logger.info(f"channel added: {channel}")
        asyncio.run(self.broadcast_update(self, reason="Channel added"))

    def channel_updated_handler(self, channel, changes):
        decky_plugin.logger.info(f"channel updated: {channel} {changes}")
        asyncio.run(self.broadcast_update(self, reason="Channel updated"))
    
    def channel_removed_handler(self, channel):
        decky_plugin.logger.info(f"channel removed: {channel}")
        asyncio.run(self.broadcast_update(self, reason="Channel removed"))
    
    @catch_errors
    def message_received_handler(self, message):
        decky_plugin.logger.info(f"Received message: {message}")
        self.messages.append(json.dumps({'type': 'message', 'actor': self.mumble.users[message.actor]['name'], 'message': message.message, 'time': str(datetime.datetime.now().strftime("%H:%M:%S"))}))
        decky_plugin.logger.info(f"messages array: {self.messages}")
        asyncio.run(self.broadcast_message(self, message))

    @catch_errors
    def disconnected_handler(self):
        decky_plugin.logger.info(f"Disconnected from server")
        asyncio.run(self.broadcast_update(self))
        asyncio.run(self.leave_server(self))

    @catch_errors
    def open_audio_stream(self):
        CHUNK = 1920
        CHANNELS = 1
        RATE = 48000
        frame_duration = CHUNK / RATE
        MAX_DATA_BYTES = 4000
        min_level = 175
        max_level = 500000

        def input_callback(in_data, frame_count, time_info, status):
            if self.transmit_mode == 0 and self.connected and not self.muted and self.transmitting:
                try:
                    # Directly send raw PCM audio data
                    self.mumble.sound_output.add_sound(in_data.tobytes())
                    asyncio.run(self.send_transmitting_update(self, self.mumble.users.myself))
                except Exception as e:
                    decky_plugin.logger.info(f"Failed to send audio: {e}")
            if self.transmit_mode == 1 and not self.muted and self.transmitting:
                try:
                    self.mumble.sound_output.add_sound(in_data.tobytes())
                    asyncio.run(self.send_transmitting_update(self, self.mumble.users.myself))
                except Exception as e:
                    decky_plugin.logger.info(f"Failed to send audio (PTT MODE): {e}")

            if self.transmit_mode == 2 and not self.muted and self.connected:
                try:
                    volume_norm = numpy.linalg.norm(in_data) * 10
                    volume_norm = numpy.clip(volume_norm, min_level, max_level)
                    volume_percent = ((volume_norm - min_level) / (max_level - min_level)) * 100
                    if volume_percent > self.broadcastAfter:
                        if volume_percent > self.silenceBelow:
                            decky_plugin.logger.info(f"Sending audio {volume_percent}")
                            self.mumble.sound_output.add_sound(in_data.tobytes())
                            asyncio.run(self.send_transmitting_update(self, self.mumble.users.myself))
                            self.broadcast_timer = time.time()  # Reset the timer
                    elif self.broadcast_timer is not None:
                        if time.time() - self.broadcast_timer > self.BROADCAST_TIMEOUT:
                            self.broadcast_timer = None  # Stop the timer
                        else:
                            # Keep broadcasting until the timer runs out
                            self.mumble.sound_output.add_sound(in_data.tobytes())
                            asyncio.run(self.send_transmitting_update(self, self.mumble.users.myself))
                    elif volume_percent < self.silenceBelow:
                        self.broadcast_timer = None  # Stop the timer immediately
                except Exception as e:
                    decky_plugin.logger.info(f"Failed to send audio (ACTIVITY MODE): {e}")

        
        try:
            self.stream = sd.InputStream(
                            channels=CHANNELS,
                            samplerate=RATE,
                            device=self.selected_input_device,
                            blocksize=CHUNK,
                            dtype='int16',
                            callback=input_callback)
            
            self.stream.start()
            self.playback_thread = threading.Thread(target=self.audio_playback_thread, args=(self,))
            self.playback_thread.start()
            self.logger.info("Started Audio")
        except Exception as e:
            self.logger.info(e)

    @catch_errors
    def open_probing_stream(self):
        if True:
            self.logger.info("PROBE NOT CONNECTED FART")
            def probe_callback(in_data, frame_count, time_info, status):
                min_level = 175
                max_level = 500000
                #self.volume_norm = np.linalg.norm(in_data) * 10
                self.volume_norm = numpy.linalg.norm(in_data) * 10
                self.volume_norm = numpy.clip(self.volume_norm, min_level, max_level)
                self.volume_percent = ((self.volume_norm - min_level) / (max_level - min_level)) * 100
                #decky_plugin.logger.info(f"SOUND!  {self.volume_norm} | {self.volume_percent}")
                asyncio.run(self.check_audio_level(self))
                #decky_plugin.logger.info(f"FISH TERGIDSON!{type(in_data)} {frame_count} {time_info} {status}, {in_data}")

            try:
                decky_plugin.logger.info("STARTING PROBER?! ")
                self.probe = sd.InputStream(channels=1, samplerate=48000, device=self.selected_input_device, blocksize=1920, dtype='int16', callback=probe_callback)
                self.probe.start()
                self.probing = True
                decky_plugin.logger.info(f"STARTed PROBER?! {self.probing}, {self.probe}")
            except Exception as e:
                self.logger.info(e)
    
    @catch_errors
    async def check_audio_level(self):
        if 'audio_level' in self.clients:
            if len(self.clients['audio_level']) > 0:
                for websocket in self.clients.get('audio_level', []):
                #await self.broadcast_update(self, reason='audio_level_update', data=self.volume_norm)
                    #decky_plugin.logger.info(f"ASS FETUS ON FIRE {int(self.volume_norm)}")
                    response = await websocket.send(json.dumps({'type': 'audio_level_update', 'data': int(self.volume_percent)}))
                    
    async def get_default_input(self):
        return {"ID": self.p.get_default_input_device_info()["index"], "name": self.p.get_default_input_device_info()["name"]}

    async def get_default_output(self):
        return {"ID": self.p.get_default_output_device_info()['index'], "name": self.p.get_default_output_device_info()['name']}
    
    async def get_transmit_mode(self):
        if self.transmit_mode == 0:
            return {'ID': self.transmit_mode, 'name': 'always-on'}
        if self.transmit_mode == 1:
            return {'ID': self.transmit_mode, 'name': 'push-to-talk'}
        if self.transmit_mode == 2:
            return {'ID': self.transmit_mode, 'name': 'activity'}
    
    async def set_transmit_mode(self, mode=0):
        decky_plugin.logger.info(f"set to {mode}")
        self.transmit_mode = mode
        if mode == 0:
            self.transmitting = True
        elif mode == 1:
            self.transmitting = False
        self.settings.setSetting("transmitMode", mode)
        #await self.broadcast_update(self)
        return self.transmit_mode

    async def get_users_list(self):
        decky_plugin.logger.info(f"Getting users list")
        users = [{'name': user['name'], 'muted': self.check_user_muted(self, user), 'ID': user['session']} for user in self.mumble.users.values()]
        decky_plugin.logger.info(f"Got users list: {users}")
        return users

    async def settings_read(self):
        decky_plugin.logger.info('Reading settings')
        return self.settings.read()
    
    async def settings_commit(self):
        decky_plugin.logger.info('Saving settings')
        return self.settings.commit()
    
    async def settings_getSetting(self, key: str, defaults):
        #decky_plugin.logger.info('Get {}'.format(key))
        return self.settings.getSetting(key, defaults)
    

    async def settings_setSetting(self, key: str, value):
       decky_plugin.logger.info(f"trying to fart: {key}, {value}")
       return self.settings.setSetting(key, value)
    
    @catch_errors
    async def saveServer(self, address, port, username, label, password):
        server = { 'address': address, 'port': port, 'username': username, 'label': label, 'password': password }
        for i in self.savedServers:
            if label in i['label']:
                self.logger.info(f"Already exists. updating...: {server}")
                self.savedServers.remove(i)
                self.savedServers.append(server)
                return self.settings.setSetting("savedServers", self.savedServers)
        self.logger.info(f"saving server: {server}")
        self.savedServers.append(server)
        return self.settings.setSetting("savedServers", self.savedServers)
    
    async def getServers(self):
        decky_plugin.logger.info(f"Get servers: {self.savedServers}")
        return self.savedServers
    
    @catch_errors
    async def pingServer(self, ip, port):
        ping = mumble_ping(str(ip), int(port))
        self.logger.info(f"ping: {str(ping)}")
        return ping
    
    @catch_errors
    async def deleteServer(self, serverLabel):
        decky_plugin.logger.info(f"Removing server: {serverLabel}")
        for i in self.savedServers:
            if serverLabel in i['label']:
                self.savedServers.remove(i)
                return True
        return False
    
    @catch_errors
    async def setCurrentServer(self, serverLabel):
        self.logger.info("Setting current server details")
        for i in self.savedServers:
            self.logger.info(f"i: {i}")
            self.logger.info(f"serverlabel: {serverLabel}")
            self.logger.info(i['label'])
            if serverLabel == i['label']:
                self.address = i['address']
                self.settings.setSetting("address", i['address'])
                self.logger.info(i['address'])
                self.logger.info(self.address)
                self.port = i['port']
                self.settings.setSetting("port", i['port'])
                self.logger.info(i['port'])
                self.username = i['username']
                self.settings.setSetting("username", i['username'])
                self.label = i['label']
                self.settings.setSetting("label", i['label'])
                self.logger.info(i['label'])
                self.password = i['password']
                self.settings.setSetting("password", i['password'])
                return True
        return False



    @catch_errors
    async def leave_server(self):
        decky_plugin.logger.info(f"leaving server")
        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self.mumble.stop)
            decky_plugin.logger.info(f"Left Server?")
            await self.broadcast_update(self)
            users=[]
            self.connected = False
            self.mumble.callbacks.reset_callback(pymumble.constants.PYMUMBLE_CLBK_SOUNDRECEIVED)
            self.mumble.callbacks.reset_callback(pymumble.constants.PYMUMBLE_CLBK_CHANNELCREATED)
            self.mumble.callbacks.reset_callback(pymumble.constants.PYMUMBLE_CLBK_CHANNELUPDATED)
            self.mumble.callbacks.reset_callback(pymumble.constants.PYMUMBLE_CLBK_CHANNELREMOVED)
            self.mumble.callbacks.reset_callback(pymumble.constants.PYMUMBLE_CLBK_USERCREATED)
            self.mumble.callbacks.reset_callback(pymumble.constants.PYMUMBLE_CLBK_USERUPDATED)
            self.mumble.callbacks.reset_callback(pymumble.constants.PYMUMBLE_CLBK_USERREMOVED)
            self.mumble.callbacks.reset_callback(pymumble.constants.PYMUMBLE_CLBK_TEXTMESSAGERECEIVED)
            self.mumble.callbacks.reset_callback(pymumble.constants.PYMUMBLE_CLBK_DISCONNECTED)
            #await self.broadcast_update(self)
            # self.outstream.stop()
            self.stream.stop()
            self.audio_queue.put(None)
            self.playback_thread.join()
            #self.p.terminate()
            return users
        except Exception as e:
            decky_plugin.logger.info(f"fucked")
            decky_plugin.logger.info(e)
            return False
    
    async def mute(self):
        decky_plugin.logger.info(f"Muting self")
        
        try:
            if self.connected:
                self.mumble.users.myself.mute()
                self.muted = True
                await self.broadcast_update(self)
            else:
                self.muted = True
        except Exception as e:
            decky_plugin.logger.info(f"Turgidson?")
            decky_plugin.logger.info(e)
        
        threads = threading.enumerate()
        decky_plugin.logger.info(f"Threads: {str(threads)}")
        await asyncio.sleep(0.1)
        for thread in threads:
            decky_plugin.logger.info(f"Thread name: {thread.getName()}, Thread ID: {thread.ident}")
        decky_plugin.logger.info(f"Connected: {self.connected}")
        decky_plugin.logger.info(f"Muted: {self.muted}")
        return True

    async def unmute(self):
        decky_plugin.logger.info(f"Unmuting self")
        try:
            if self.connected:
                self.mumble.users.myself.unmute()
                self.muted = False
                await self.broadcast_update(self)
            else:
                self.muted = False
        except Exception as e:
            decky_plugin.logger.info(f"Turgidson fart?")
            decky_plugin.logger.info(e)
        return True

    async def deafen(self):
        decky_plugin.logger.info(f"Deafening self")
        try:
            if self.connected:
                self.mumble.users.myself.deafen()
                self.deafened = True
                self.muted = True
                await self.broadcast_update(self)
                return True
            else:
                self.deafened = True
                self.muted = True
                return True
        except Exception as e:
            decky_plugin.logger.info(f"Turgidson?")
            decky_plugin.logger.info(e)

    async def undeafen(self):
        decky_plugin.logger.info(f"undeafening self")
        try:
            if self.connected:
                self.mumble.users.myself.undeafen()
                self.deafened = False
                await self.broadcast_update(self)
                return True
            else:
                self.deafened = False
                return True

        except Exception as e:
            decky_plugin.logger.info(f"Turgidson fart?")
            decky_plugin.logger.info(e)
    
    async def get_channels_and_users(self):
        channels_and_users = {}
        decky_plugin.logger.info(f"Connected: {self.connected}")

        if self.connected:
            for channel in self.mumble.channels:
                channel_obj = self.mumble.channels[channel]
                channels_and_users[channel_obj["name"]] = {
                    "users": {}
                }
                for user in channel_obj.get_users():
                    channels_and_users[channel_obj["name"]]["users"][user["name"]] = {
                        "muted": self.check_user_muted(self, user),
                        "ID": user['session']
                    }
            #decky_plugin.logger.info(f"Channels and users: {channels_and_users}")
            return channels_and_users
        else:
            return {}
            

        

    async def getConnected(self):
        return self.connected
    
    async def getDeafened(self):
        return self.deafened
    
    async def getMuted(self):
        return self.muted
    
    async def getUsername(self):
        return self.name
    
    @catch_errors
    async def getMessagesArray(self):
        self.logger.info(self.messages)
        return self.messages
    
    def check_user_muted(self, user):
        if 'self_mute' in user:
            return user['self_mute']
        else:
            return False
    
    def get_by_name(self, username):
        for user in self.mumble.users.values():
            if user['name'] == username:
                return user
    
    async def move_to_channel(self, channelName):
        decky_plugin.logger.info(f"Moving to channel {channelName}")
        try:
            c = self.get_channel_by_name(self, channelName)
            c.move_in()
            await self.broadcast_update(self)
            return True
        except Exception as e:
            decky_plugin.logger.info(f"Turgidson?")
            decky_plugin.logger.info(e)

    @catch_errors
    async def get_selected_recipient(self):
        decky_plugin.logger.info(f"Eatign a turd")
        return self.selected_recipient
    
    @catch_errors
    async def set_selected_recipient(self, ID=int, name=str):
        decky_plugin.logger.info(f"Eatign a cup of , {ID}, {name}")
        self.selected_recipient = { 'ID': ID, 'name': name }
        return True




    # Function called first during the unload process, utilize this to handle your plugin being removed
    async def _unload(self):
        decky_plugin.logger.info("Goodbye asshats!")
        if self.connected:
            self.leave_server()
        if self.input_handler is not None:
            self.input_handler.close()
            self.input_handler = None
        self.server_stop_event.set()
        self.side_loop.join()
        #self.stream_thread.join()
        # self.outstream.stop()
        if self.stream is not None:
            self.stream.stop()
        #self.p.terminate
        pass

    @catch_errors
    async def setBroadcastAfter(self, value=int):
        try:
            self.broadcastAfter = value
            decky_plugin.logger.info(value)
            self.settings.setSetting("broadcastAfter", value)
            for websocket in self.clients.get('audio_level', []):
                response = await websocket.send(json.dumps({'type': 'broadcastAfter_update', 'value': value }))

            return True
        except Exception as e:
            return False
    
    @catch_errors
    async def getbroadcastAfter(self):
        return self.broadcastAfter
    
    @catch_errors
    async def setTransmitting(self, value=True):
        self.transmitting = value
        return self.transmitting
    
    @catch_errors
    async def setsilenceBelow(self, value=int):
        try:
            self.silenceBelow = value
            decky_plugin.logger.info(value)
            self.settings.setSetting("silenceBelow", value)
            for websocket in self.clients.get('audio_level', []):
                response = await websocket.send(json.dumps({'type': 'silenceBelow_update', 'value': value }))

            return True
        except Exception as e:
            return False
    
    @catch_errors
    async def getTimeout(self):
        return self.BROADCAST_TIMEOUT
    
    @catch_errors
    async def setTimeout(self, value=int):
        try:
            self.BROADCAST_TIMEOUT = value
            decky_plugin.logger.info(value)
            self.settings.setSetting("BROADCAST_TIMEOUT", value)
            for websocket in self.clients.get('audio_level', []):
                response = await websocket.send(json.dumps({'type': 'timeout_update', 'value': value }))
            return True
        except Exception as e:
            return False
    
    @catch_errors
    async def getsilenceBelow(self):
        return self.silenceBelow
    
    @catch_errors
    async def setInputDevice(self, device=int):
        try:
            self.selected_input_device = device
            self.logger.info(f"Selected input device: {self.selected_input_device}")
            if self.probing:
                self.probing = False
                if self.probe:
                    self.probe.stop()
                self.probe = None
            return True
        except Exception as e:
            decky_plugin.logger.info(f"Error setting input device: {e}")
            return False

    @catch_errors
    async def setOutputDevice(self, device=int):
        try:
            self.selected_output_device = device
            decky_plugin.logger.info(f"Selected output device: {self.selected_output_device}")
            return True
        except Exception as e:
            decky_plugin.logger.info(f"Error setting output device: {e}")
            return False
        
    @catch_errors
    async def setAPI(self, api=int):
        try:
            self.selected_api_input = self.apis[api]
            self.selected_api_input['index'] = api
            decky_plugin.logger.info(f"Selected INPUT API: {self.selected_api_input}")
            return True
        except Exception as e:
            decky_plugin.logger.info(f"Error setting API device: {e}")
            return False
        
    @catch_errors
    async def setAPI_output(self, api=int):
        try:
            self.selected_api_output = self.apis[api]
            self.selected_api_output['index'] = api
            #decky_plugin.logger.info(f"Selected OUTPUT API: {self.selected_api_output}")
            return True
        except Exception as e:
            decky_plugin.logger.info(f"Error setting API device: {e}")
            return False
    
    @catch_errors
    async def get_api(self):
        #decky_plugin.logger.info(f"The Selected API FETUS is: {self.selected_api_input}")
        for index, i in enumerate(self.apis):
            if i['name'] == self.selected_api_input['name']:
                turdname = i['name']
                turddex = index
        return {'ID': turddex, 'name': turdname}
    
    @catch_errors
    async def get_api_output(self):
        decky_plugin.logger.info(f"The Selected API FETUS is: {self.selected_api_output}")
        for index, i in enumerate(self.apis):
            if i['name'] == self.selected_api_output['name']:
                turdname = i['name']
                turddex = index
        return {'ID': turddex, 'name': turdname}
    
    def get_channel_by_name(self, channel_name):
        for channel in self.mumble.channels:
            if self.mumble.channels[channel]["name"] == channel_name:
                return self.mumble.channels[channel]
        return None
    
    @catch_errors
    async def setPushToTalkKey(self, key="R5"):
        try:
            self.ptt_key = key
            decky_plugin.logger.info(f"Set ppt key {key}")
            return True
        except Exception as e:
            decky_plugin.logger.info(f"Error setting ptt key: {e}")
            return False
    
    @catch_errors
    async def getPushToTalkKey(self):
        decky_plugin.logger.info(f"TERDINOOS KEY IS {self.ptt_key}")
        if self.ptt_key == "R4":
            return {'ID': 0, 'name': 'R4'}
        if self.ptt_key == "L4":
            return {'ID': 1, 'name': 'L4'}
        if self.ptt_key == "R5":
            return {'ID': 2, 'name': 'R5'}
        if self.ptt_key == "L5":
            return {'ID': 3, 'name': 'L5'}
    
    @catch_errors
    async def setInGamePushToTalkKey(self, key="Up"):
        try:
            self.ig_ptt_key = key
            decky_plugin.logger.info(f"Set ppt key {key}")
            return True
        except Exception as e:
            decky_plugin.logger.info(f"Error setting ptt key: {e}")
            return False
    
    @catch_errors
    async def getInGamePushToTalkKey(self):
        decky_plugin.logger.info(f"TERDINOOS KEY IS {self.ig_ptt_key}")
        if self.ig_ptt_key == "A":
            return {'ID': 0, 'name': 'A'}
        if self.ig_ptt_key == "B":
            return {'ID': 1, 'name': 'B'}
        if self.ig_ptt_key == "X":
            return {'ID': 2, 'name': 'X'}
        if self.ig_ptt_key == "Y":
            return {'ID': 3, 'name': 'Y'}
        if self.ig_ptt_key == "L1":
            return {'ID': 4, 'name': 'L1'}
        if self.ig_ptt_key == "L2":
            return {'ID': 5, 'name': 'L2'}
        if self.ig_ptt_key == "L3":
            return {'ID': 6, 'name': 'L3'}
        if self.ig_ptt_key == "R1":
            return {'ID': 7, 'name': 'R1'}
        if self.ig_ptt_key == "R2":
            return {'ID': 8, 'name': 'R2'}
        if self.ig_ptt_key == "R3":
            return {'ID': 9, 'name': 'R3'}
        if self.ig_ptt_key == "Select":
            return {'ID': 10, 'name': 'Select'}
        if self.ig_ptt_key == "Start":
            return {'ID': 11, 'name': 'Start'}
        if self.ig_ptt_key == "Up":
            return {'ID': 12, 'name': 'Up'}
        if self.ig_ptt_key == "Down":
            return {'ID': 13, 'name': 'Down'}
        if self.ig_ptt_key == "Left":
            return {'ID': 14, 'name': 'Left'}
        if self.ig_ptt_key == "Right":
            return {'ID': 15, 'name': 'Right'}
    
    @catch_errors
    async def setPTTEnabled(self, value=True):
        try:
            self.ptt_enabled = value
            decky_plugin.logger.info(f"Set ppt {value}")
            return True
        except Exception as e:
            decky_plugin.logger.info(f"Error setting ptt: {e}")
            return False
    
    @catch_errors
    async def getPTTEnabled(self):
        return self.ptt_enabled

    
    async def get_input_devices(self):
        decky_plugin.logger.info(f"The inlist is here: {len(self.inlist)}")
        newlist = []
        for i in self.inlist:
            if i['hostapi'] == self.selected_api_input['index']:
                newlist.append(i)
        formatted_input_devices = [{'ID': device['index'], 'name': device['name']} for index, device in enumerate(newlist)]
        decky_plugin.logger.info(f"formatted_input_devices TERDS: {formatted_input_devices}")
        return formatted_input_devices
    
    @catch_errors
    async def get_apis(self):
        try:
            formatted_input_apis = [{'ID': index, 'name': api['name'] } for index, api in enumerate(self.apis)]
            return formatted_input_apis
        except Exception as e:
            decky_plugin.logger.info(f"CUPPA MCFUCKED {e}")
        
    
    async def get_output_devices(self):
        newlist = []
        for i in self.outlist:
            if i['hostapi'] == self.selected_api_output['index']:
                newlist.append(i)
        formatted_output_devices = [{'ID': device['index'], 'name': device['name']} for index, device in enumerate(newlist)]
        return formatted_output_devices
    
    @catch_errors
    async def get_selected_output(self):
        decky_plugin.logger.info(f"The Selected OUTPUT FETUS is: {self.selected_output_device}")
        for i in self.outlist:
            if i['index'] == self.selected_output_device:
                turdname = i['name']
        return {'ID': self.selected_output_device, 'name': turdname}
    
    @catch_errors
    async def get_selected_input(self):
        decky_plugin.logger.info(f"The Selected INPUT TERGINOOS is: {self.selected_input_device}")
        
        for i in self.inlist:
            if i['index'] == self.selected_input_device:
                turdname = i['name']
        decky_plugin.logger.info({'ID': self.selected_input_device, 'name': turdname})
        return {'ID': self.selected_input_device, 'name': turdname}

    # Migrations that should be performed before entering `_main()`.
    async def _migration(self):
        decky_plugin.logger.info("Migrating")
        decky_plugin.migrate_logs(os.path.join(decky_plugin.DECKY_USER_HOME,
                                               ".config", "decky-template", "template.log"))
        decky_plugin.migrate_settings(
            os.path.join(decky_plugin.DECKY_HOME, "settings", "template.json"),
            os.path.join(decky_plugin.DECKY_USER_HOME, ".config", "decky-template"))
        decky_plugin.migrate_runtime(
            os.path.join(decky_plugin.DECKY_HOME, "template"),
            os.path.join(decky_plugin.DECKY_USER_HOME, ".local", "share", "decky-template"))
